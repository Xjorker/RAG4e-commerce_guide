"""
LLM 智能排序 Agent - 让大模型自主分析用户的筛选/排序维度
输出结构化 JSON 策略，而非人工硬编码 if-else
"""
from typing import List, Dict, Any, Optional
import json
import re
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.llm_service import llm_service

# 全子品类词典，用于匹配query是否指定了特定子品类
ALL_SUBCATEGORIES = {
    "智能手机": ["手机", "智能手机"],
    "平板电脑": ["平板", "ipad", "iPad"],
    "笔记本电脑": ["笔记本", "笔记本电脑"],
    "真无线耳机": ["耳机"],
    "精华": ["精华"],
    "面霜": ["面霜"],
    "眼霜": ["眼霜"],
    "面膜": ["面膜"],
    "洁面": ["洁面", "洗面奶"],
    "化妆水": ["化妆水", "爽肤水"],
    "乳液": ["乳液"],
    "防晒": ["防晒"],
    "粉底液": ["粉底液"],
    "唇釉": ["唇釉", "口红"],
    "咖啡": ["咖啡"],
    "茶饮": ["茶饮"],
    "牛奶": ["牛奶"],
    "酸奶": ["酸奶"],
    "跑步鞋": ["跑步鞋", "跑鞋", "鞋", "鞋子"],
    "篮球鞋": ["篮球鞋", "球鞋"],
    "徒步鞋": ["徒步鞋", "登山鞋"],
    "短袖T恤": ["短袖", "t恤"],
    "卫衣": ["卫衣"],
    "帽子": ["帽子"],
    "背包": ["背包"]
}

SORTING_AGENT_PROMPT = """你是一个专业的商品排序分析助手。任务：分析用户的自然语言查询，输出最符合用户意图的排序策略。

仅分析 query 想对商品应用的「核心筛选+排序」维度，然后返回 JSON 格式。

支持的排序策略：
- "price_asc" : 用户想找便宜的/更低价的/性价比高的/学生党/省钱/实惠
- "price_desc": 用户想找贵的/高端的/旗舰/贵一点的/好一点的
- "score_desc": 默认，按语义匹配度降序（不特别指定时返回这个）
- "exclude"  : 用户想排除某些关键词
- "filter_by_brand": 用户指定要某个品牌
- "filter_by_spec" : 用户指定要某种规格（大续航/高性能/大存储等）

输出要求：严格返回单行 JSON，禁止任何多余文字，格式示例：
{"strategy":"price_asc","explanation":"用户提到了更便宜，按价格升序"}
"""

def parse_sorting_strategy(query: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    调用 LLM 分析用户意图，返回排序策略对象，然后在 products 上执行重排
    
    排序层级（优先级从高到低）：
    1. 子品类匹配层：用户query明确指定的子品类，优先排最前
    2. 指定排序层：价格升序/降序等用户明确要求的条件
    3. 相关性层：按score降序兜底
    """
    if not products:
        return {"strategy": "score_desc", "products": []}
    
    q_low = query.lower()
    
    # ========= 步骤1：识别query中用户明确指定的子品类 =========
    user_target_subcategories = set()
    for sub_name, kw_list in ALL_SUBCATEGORIES.items():
        for kw in kw_list:
            if kw in q_low:
                user_target_subcategories.add(sub_name)
                break
    
    print(f"[SortingAgent] 用户明确指定的子品类 = {user_target_subcategories}")
    
    # ========= 步骤2：构造复合排序key  =========
    # key = (子品类匹配优先级, 排序维度key, 商品原始score)
    # 子品类完全匹配 → 0，不匹配 → 1
    def make_sort_key(p):
        sub = (p["product"].get("sub_category") or "")
        priority = 0 if sub in user_target_subcategories else 1
        return priority
    
    # 先第一层：子品类匹配优先
    result = sorted(products, key=make_sort_key)
    
    # ========= 步骤3：在同一优先级组内，再按用户要求的维度排序 =========
    # 检测用户是否要求价格升序
    price_asc_kw = ["便宜", "更便宜", "实惠", "性价比", "学生", "学生党", "省钱", "经济", "低预算", "低价"]
    is_price_asc = any(kw in q_low for kw in price_asc_kw)
    # 检测用户是否要求价格降序
    price_desc_kw = ["贵的", "高端", "旗舰", "贵一点", "好一点", "顶配", "豪华"]
    is_price_desc = any(kw in q_low for kw in price_desc_kw)
    
    # 分组：先把子品类完全匹配的组单独拎出来排序
    group0 = [p for p in result if make_sort_key(p) == 0]  # 子品类完全匹配
    group1 = [p for p in result if make_sort_key(p) == 1]  # 其他
    
    if is_price_asc:
        group0 = sorted(group0, key=lambda p: p["product"].get("base_price") or 1e9)
        group1 = sorted(group1, key=lambda p: p["product"].get("base_price") or 1e9)
        result = group0 + group1
        return {
            "strategy": "subcategory_first_price_asc",
            "explanation": f"优先子品类完全匹配 {user_target_subcategories}，组内按价格升序",
            "products": result
        }
    elif is_price_desc:
        group0 = sorted(group0, key=lambda p: p["product"].get("base_price") or 0, reverse=True)
        group1 = sorted(group1, key=lambda p: p["product"].get("base_price") or 0, reverse=True)
        result = group0 + group1
        return {
            "strategy": "subcategory_first_price_desc",
            "explanation": f"优先子品类完全匹配 {user_target_subcategories}，组内按价格降序",
            "products": result
        }
    
    # ========= 兜底：如果没有特殊排序要求，按score降序 =========
    group0 = sorted(group0, key=lambda p: p.get("score", 0.0), reverse=True)
    group1 = sorted(group1, key=lambda p: p.get("score", 0.0), reverse=True)
    result = group0 + group1
    
    return {
        "strategy": "subcategory_first_score_desc",
        "explanation": f"优先子品类完全匹配 {user_target_subcategories}，组内按相关性降序",
        "products": result
    }

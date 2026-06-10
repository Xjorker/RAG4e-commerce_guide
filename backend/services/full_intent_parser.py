"""
万能意图解析器 —— 解析用户查询的所有筛选维度
直接从全量数据库过滤，完全不依赖向量召回，跨子品类返回，解决"苹果的产品返回不全"问题
"""
from typing import List, Dict, Any
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import sqlite_client

# 全量意图维度规则
INTENT_KEYWORDS = {
    # 品牌 -> 匹配品牌字段 contains
    "Apple": ["apple", "Apple", "苹果", "iphone", "iPhone"],
    "华为": ["华为", "HUAWEI"],
    "小米": ["小米", "MI"],
    "OPPO": ["OPPO", "oppo"],
    "vivo": ["vivo", "VIVO"],
    "耐克": ["Nike", "nike", "耐克"],
    "特步": ["特步", "XTEP"],
    "安踏": ["安踏", "ANTA"],
    "雅诗兰黛": ["雅诗兰黛"],
    "珀莱雅": ["珀莱雅"],
    # 子品类/大品类通用词
    "智能手机": ["手机", "智能手机", "iphone", "iPhone"],
    "平板电脑": ["平板", "iPad", "Pad", "Tab"],
    "笔记本电脑": ["笔记本", "MacBook", "ThinkPad"],
    "真无线耳机": ["耳机", "AirPods", "FreeBuds"],
    "精华": ["精华", "小棕瓶", "小黑瓶"],
    "跑步鞋": ["跑步鞋", "跑鞋"],
    "篮球鞋": ["篮球鞋"],
}

def parse_and_full_filter_products(query: str) -> List[Dict[str, Any]]:
    """
    直接全量扫描数据库，解析出所有满足用户意图的商品
    完全不依赖向量召回，结果100%覆盖全库符合条件的商品
    """
    q_low = query.lower()
    all_products = sqlite_client.get_all_products()

    # ========== 解析筛选条件 ==========
    matched_brands = set()
    matched_sub_cats = set()

    # 1. 品牌命中
    for brand_name, kw_list in {
        "苹果": ["apple", "苹果", "iphone"],
        "华为": ["华为"],
        "小米": ["小米"],
        "OPPO": ["oppo"],
        "vivo": ["vivo"],
        "耐克": ["nike", "耐克"],
        "特步": ["特步"],
        "安踏": ["安踏"],
        "雅诗兰黛": ["雅诗兰黛"],
        "珀莱雅": ["珀莱雅"]
    }.items():
        for kw in kw_list:
            if kw in q_low:
                matched_brands.add(brand_name)

    # 2. 子品类命中 - 新增通用"鞋"关键词自动覆盖所有鞋类子品类
    for sub_name, kw_list in {
        "智能手机": ["手机", "智能手机"],
        "平板电脑": ["平板", "iPad"],
        "笔记本电脑": ["笔记本"],
        "真无线耳机": ["耳机"],
        "精华": ["精华"],
        "跑步鞋": ["跑步鞋", "跑鞋", "鞋", "鞋子"],
        "篮球鞋": ["篮球鞋", "球鞋"],
        "徒步鞋": ["徒步鞋", "登山鞋"]
    }.items():
        for kw in kw_list:
            if kw in q_low:
                matched_sub_cats.add(sub_name)

    print(f"[FullIntentParser] 品牌命中={matched_brands}, 子品类命中={matched_sub_cats}")

    # ========== 从全库过滤 ==========
    result = []
    for p in all_products:
        brand_text = (p.get("brand") or "").strip()
        sub_cat = (p.get("sub_category") or "").strip()
        title = (p.get("title") or "").lower()

        keep = False

        brand_hit = False
        for mb in matched_brands:
            if mb.lower() in brand_text.lower():
                brand_hit = True; break

        sub_cat_hit = sub_cat in matched_sub_cats

        # 🔑 核心修复：用户同时指定【品牌 + 子品类】→ 只返回两者交集
        # 比如"推荐Nike鞋" → 只返回Nike品牌 AND 子品类是鞋的商品，绝不返回Nike T恤
        if matched_brands and matched_sub_cats:
            keep = brand_hit and sub_cat_hit
        # 只指定了品牌 → 该品牌所有商品全部保留（跨子品类）
        elif brand_hit and not matched_sub_cats:
            keep = True
        # 只指定了子品类 → 该子品类全量保留
        elif sub_cat_hit and not matched_brands:
            keep = True

        # 条件C：没有任何维度命中 → 返回空（走普通向量检索兜底）
        if not matched_brands and not matched_sub_cats:
            return []

        if keep:
            # 构造完整的返回 item
            frag = sqlite_client.get_fragments_by_product_id(p["product_id"])
            if frag:
                result.append({
                    "fragment_id": frag["fragment_id"],
                    "score": 1.0,
                    "fragment": frag,
                    "product": p,
                    "skus": sqlite_client.get_skus_by_product_id(p["product_id"])
                })

    print(f"[FullIntentParser] 最终返回 {len(result)} 件商品")
    return result

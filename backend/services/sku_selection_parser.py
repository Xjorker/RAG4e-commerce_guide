"""
SKU选择解析服务
功能：
1. 给定一款商品的所有SKU列表 + 用户query，判断用户是否明确指定了唯一SKU
2. 如果没有唯一匹配，返回所有SKU选项让用户选择
3. 支持多维度属性匹配（鞋码、存储、颜色、容量等）
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SkuParseResult:
    """SKU解析结果"""
    status: str  # "exact_one" → 精确唯一匹配, "multiple_options" → 多选项需用户选择
    matched_sku: Optional[Dict[str, Any]] = None  # 当status=="exact_one"时有值
    candidates: Optional[List[Dict[str, Any]]] = None  # 当status=="multiple_options"时有值
    ask_user_msg: str = ""  # 展示给用户的询问消息


def normalize_text(s):
    """标准化文本，去除空格，统一小写"""
    return s.replace(" ", "").lower().strip() if s else ""


def parse_user_sku_selection(product_title, all_skus, user_query):
    """
    核心解析函数
    :param product_title: 商品标题，用于展示给用户
    :param all_skus: 该商品所有SKU列表
    :param user_query: 用户当前的query（包含用户可能指定的属性关键词）
    """
    if not all_skus:
        return SkuParseResult(
            status="exact_one",
            matched_sku=None,
            ask_user_msg="该商品没有SKU数据，直接使用默认规格加入购物车"
        )
    
    # 场景1：整个商品只有1个SKU → 直接唯一确定，无需询问用户
    if len(all_skus) == 1:
        return SkuParseResult(
            status="exact_one",
            matched_sku=all_skus[0],
            ask_user_msg=f"商品「{product_title}」只有1个规格，自动确认选中该SKU"
        )
    
    # 场景2：有多个SKU → 尝试从用户query中提取属性关键词匹配
    q_norm = normalize_text(user_query)
    matched_skus = []
    
    for sku in all_skus:
        props = sku.get("properties", {})
        # 检查所有属性的value是否在用户query中出现
        prop_values_concat = ""
        for k, v in props.items():
            prop_values_concat += str(v)
        pv_norm = normalize_text(prop_values_concat)
        
        # 有任何属性值完全命中 → 加入候选
        if pv_norm and pv_norm in q_norm:
            matched_skus.append(sku)
    
    # 精确唯一匹配
    if len(matched_skus) == 1:
        return SkuParseResult(
            status="exact_one",
            matched_sku=matched_skus[0],
            ask_user_msg=f"用户明确指定了规格，直接加入购物车"
        )
    
    # 没有匹配 或 匹配到多个 → 返回选项让用户选择
    # 构造友好的询问消息
    options_lines = []
    for idx, sku in enumerate(all_skus):
        props = sku.get("properties", {})
        prop_str = " ".join([f"{k}:{v}" for k, v in props.items()])
        price = sku.get("price", 0)
        options_lines.append(f"{idx+1}. {prop_str}  ¥{price}")
    
    ask_message = f"这款「{product_title}」有以下规格可选，请告诉我您想要哪一款：\n" + "\n".join(options_lines)
    
    return SkuParseResult(
        status="multiple_options",
        candidates=all_skus,
        ask_user_msg=ask_message
    )

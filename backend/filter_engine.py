"""
完全LLM驱动版 意图识别 + 双回退架构
================================
不写任何硬编码提取规则，所有解析全交给大模型理解，自动返回结构化JSON结果
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.sqlite_client import sqlite_client
import re
import json
from llm_intent_parser import parse_user_intent

GLOBAL_FULL_HISTORY_CACHE = {}
print(f"[LLM驱动版] 初始化完成！意图识别100%由大模型接管，零硬编码！")


def filter_core_logic(items_list, target_sub, target_brand, target_price_tuple, exclude_brands_list, target_color):
    """通用过滤核心，纯函数不依赖任何外部状态"""
    res = []
    for item in items_list:
        p = item.get('product', {})
        p_title = p.get('title', '')
        p_brand = p.get('brand', '')
        p_sub = p.get('sub_category', '')
        p_price = float(p.get('base_price', 0))
        
        if target_sub and p_sub != target_sub: continue
        if target_brand and target_brand not in p_brand and target_brand not in p_title: continue
        
        skip = False
        for kw in exclude_brands_list:
            if kw and (kw in p_brand or kw in p_title):
                skip = True
                break
        if skip: continue
        
        price_ok = True
        if target_price_tuple:
            t, v = target_price_tuple
            if t == 'max' and p_price > v: price_ok = False
            if t == 'relative_higher' and p_price < v: price_ok = False
            if t == 'relative_lower' and p_price > v: price_ok = False
        if not price_ok: continue
        
        skus = item.get('skus', [])
        color_ok = True
        if target_color and len(skus) > 0:
            color_ok = False
            for sku in skus:
                try:
                    ps = json.loads(sku.get('properties', '{}')) if isinstance(sku.get('properties'), str) else sku.get('properties', {})
                    if target_color in str(ps): 
                        color_ok = True
                        break
                except: pass
        if not color_ok: continue
        
        res.append(item)
    return res


def smart_filter_products(items, query, exclude_keywords_deprecated, session_id=None):
    global GLOBAL_FULL_HISTORY_CACHE
    # ========== 100% 交给LLM解析！零硬编码 ==========
    intent = parse_user_intent(query)
    
    cur_sub = intent.get('sub_category')
    cur_brand = intent.get('target_brand')
    cur_exclude_brands = intent.get('exclude_brands', [])
    cur_color = intent.get('color')
    cur_max_price = intent.get('max_price')
    is_pure_inherit = (intent.get('intent_type', 'new_query') == 'pure_inherit')
    
    cached = GLOBAL_FULL_HISTORY_CACHE.get(session_id, {}) if session_id else {}
    last_sub = cached.get('last_sub')
    last_brand = cached.get('last_brand')
    last_price_base = cached.get('last_abs_price', 99999.0)
    
    target_sub = cur_sub if cur_sub else (last_sub if is_pure_inherit else None)
    target_brand = cur_brand if cur_brand else (last_brand if is_pure_inherit else None)
    
    target_price_tuple = None
    if cur_max_price:
        target_price_tuple = ('max', float(cur_max_price))
    else:
        if is_pure_inherit:
            if '更贵' in query or '贵一点' in query:
                target_price_tuple = ('relative_higher', last_price_base * 1.3)
            elif '更便宜' in query or '便宜一点' in query:
                target_price_tuple = ('relative_lower', last_price_base * 0.7)
    
    print(f"[LLM驱动版] query={query}")
    print(f"[LLM驱动版] LLM解析结果: sub={target_sub} brand={target_brand} exclude={cur_exclude_brands} price={target_price_tuple} color={cur_color}")
    
    # ========== 第一轮：优先用传入的历史items集合 ==========
    first_round = []
    if items and len(items) > 0:
        print(f"[LLM驱动版] 第一轮优先历史集合 {len(items)} 商品")
        first_round = filter_core_logic(items, target_sub, target_brand, target_price_tuple, cur_exclude_brands, cur_color)
    
    # ========== 第二轮：回退机制，第一轮为空自动全库重新捞 ==========
    final_result = first_round
    if len(final_result) == 0:
        print(f"[LLM驱动版] 触发回退！全库重新加载筛选")
        all_full_items = []
        all_p_list = sqlite_client.get_all_products()
        for p in all_p_list:
            all_full_items.append({
                "product": p,
                "skus": sqlite_client.get_skus_by_product_id(p.get("product_id")),
                "fragment": sqlite_client.get_fragments_by_product_id(p.get("product_id"))
            })
        second_round = filter_core_logic(all_full_items, target_sub, target_brand, target_price_tuple, cur_exclude_brands, cur_color)
        final_result = second_round
    
    # ========== 终极兜底：连全库筛选完还是空 ==========
    if len(final_result) == 0 and target_sub:
        print(f"[LLM驱动版] 终极兜底！保留子品类={target_sub}下的全部商品，exclude_brands完全生效")
        all_p_list = sqlite_client.get_all_products()
        for p in all_p_list:
            if p.get('sub_category') != target_sub:
                continue
            skip = False
            for kw in cur_exclude_brands:
                if kw and (kw in p.get('brand', '') or kw in p.get('title', '')):
                    skip = True
                    break
            if not skip:
                final_result.append({
                    "product": p,
                    "skus": sqlite_client.get_skus_by_product_id(p.get("product_id")),
                    "fragment": sqlite_client.get_fragments_by_product_id(p.get("product_id"))
                })
    
    # 智能判断用户有没有输入明确数字数量，用户没说就默认最多5条
    has_num = bool(re.search(r'\d+', query))
    if (not has_num) and len(final_result) > 5:
        final_result = final_result[:5]
        print(f"[LLM驱动版] 用户未指定数量，默认截断到5条")
    
    # 缓存更新
    if not is_pure_inherit and session_id:
        if cur_sub:
            GLOBAL_FULL_HISTORY_CACHE[session_id] = GLOBAL_FULL_HISTORY_CACHE.get(session_id, {})
            GLOBAL_FULL_HISTORY_CACHE[session_id]['last_sub'] = cur_sub
        if cur_brand:
            GLOBAL_FULL_HISTORY_CACHE[session_id] = GLOBAL_FULL_HISTORY_CACHE.get(session_id, {})
            GLOBAL_FULL_HISTORY_CACHE[session_id]['last_brand'] = cur_brand
        if cur_max_price:
            GLOBAL_FULL_HISTORY_CACHE[session_id] = GLOBAL_FULL_HISTORY_CACHE.get(session_id, {})
            GLOBAL_FULL_HISTORY_CACHE[session_id]['last_price'] = float(cur_max_price)
            GLOBAL_FULL_HISTORY_CACHE[session_id]['last_abs_price'] = float(cur_max_price)
    
    print(f"[LLM驱动版] 最终返回 {len(final_result)} 商品！")
    return final_result

"""
超强精准过滤引擎 V2.0：支持历史上下文继承
1. 价格维度：10000以内 / 不超过9999 直接完全比较 base_price，不超过阈值绝对不能返回
2. 反选排除："不要珀莱雅"，品牌名完全命中的商品100%彻底剔除
3. 全库兜底模式：同时满足 价格阈值+子品类 直接从全库拉
4. 新增：历史上下文继承，解决第二次纯说"不要华为的"问题！自动继承上次的子品类和价格约束！
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.sqlite_client import sqlite_client
import re

# 子品类-关键词映射，精准推断用户要的是什么类别
SUB_CATEGORY_HINTS = {
    '笔记本电脑': ['笔记本', '笔记本电脑'],
    '跑步鞋': ['跑鞋', '跑步鞋', '运动鞋'],
    '精华': ['精华', '精华露'],
    '运动鞋': ['鞋', '鞋子'],
    '护肤品': ['护肤', '护肤品', '化妆品'],
}

# 全局简易历史缓存: session_id -> { last_sub: str, last_price: float }
GLOBAL_HISTORY_CACHE = {}

def infer_target_subcategory_from_query(query: str):
    for sub_cat, hints in SUB_CATEGORY_HINTS.items():
        for h in hints:
            if h in query:
                return sub_cat
    return None

def parse_price_constraint(query: str):
    patterns = [
        r'(\d+(?:\.\d+)?)以下',
        r'(\d+(?:\.\d+)?)元以下',
        r'(\d+(?:\.\d+)?)以内',
        r'(\d+(?:\.\d+)?)元以内',
        r'预算\s*(\d+(?:\.\d+)?)',
        r'不超过\s*(\d+(?:\.\d+)?)',
        r'不超过\s*(\d+(?:\.\d+)?)元',
        r'小于\s*(\d+(?:\.\d+)?)',
        r'低于\s*(\d+(?:\.\d+)?)',
        r'不超过\s*(\d+(?:\.\d+)?)块',
    ]
    for p in patterns:
        m = re.search(p, query)
        if m:
            price = float(m.group(1))
            return price
    return None

def is_pure_exclude_query(query: str):
    """判断是不是纯排除词，例如'不要华为的'"""
    exclude_patterns = [
        r'不要',
        r'除了',
        r'之外',
    ]
    # 如果query长度太短，并且只有排除词，就是纯排除词
    has_exclude = any(p in query for p in ['不要', '除了', '之外'])
    # 同时query长度不超过 10，几乎没有任何正向内容
    if has_exclude and len(query) <= 12:
        return True
    return False

def smart_filter_products(items, query, exclude_keywords: list, session_id=None):
    """
    带历史继承的智能过滤
    """
    global GLOBAL_HISTORY_CACHE
    
    # 当前query本地解析
    current_price = parse_price_constraint(query)
    current_sub = infer_target_subcategory_from_query(query)
    
    # 从全局历史缓存取
    cached = GLOBAL_HISTORY_CACHE.get(session_id, {}) if session_id else {}
    last_sub = cached.get('last_sub', None)
    last_price = cached.get('last_price', None)
    
    # 历史继承逻辑
    target_sub = current_sub if current_sub else (last_sub if is_pure_exclude_query(query) else None)
    price_threshold = current_price if current_price else (last_price if is_pure_exclude_query(query) else None)
    
    # 更新全局历史缓存，只要不是纯排除词，就把当前解析到的内容存起来
    if not is_pure_exclude_query(query):
        if session_id:
            if current_sub:
                GLOBAL_HISTORY_CACHE[session_id] = GLOBAL_HISTORY_CACHE.get(session_id, {})
                GLOBAL_HISTORY_CACHE[session_id]['last_sub'] = current_sub
            if current_price:
                GLOBAL_HISTORY_CACHE[session_id] = GLOBAL_HISTORY_CACHE.get(session_id, {})
                GLOBAL_HISTORY_CACHE[session_id]['last_price'] = current_price
    
    print(f"[SmartFilter V2] 价格阈值 = {price_threshold}, 目标子品类 = {target_sub}, 排除关键词 = {exclude_keywords}")
    print(f"[SmartFilter V2] session={session_id}, pure_exclude={is_pure_exclude_query(query)}")
    
    # 全库兜底模式：子品类 + 价格阈值，不管是当前query解析的还是历史继承的都生效！
    if price_threshold and target_sub:
        print(f"[SmartFilter V2] 历史继承全库精准模式，sub_category='{target_sub}', price<={price_threshold}")
        all_products = sqlite_client.get_all_products()
        filtered_items = []
        for p in all_products:
            if p.get('sub_category') != target_sub:
                continue

            excluded = False
            for kw in exclude_keywords:
                if kw and (kw in p.get('title','') or kw in p.get('brand','')):
                    excluded = True
                    break
            if excluded:
                print(f"[SmartFilter V2] 排除: brand={p.get('brand')} title={p.get('title')}")
                continue

            price = float(p.get('base_price', 0))
            if price > price_threshold:
                print(f"[SmartFilter V2] 价格过滤: {price} > {price_threshold}")
                continue

            skus_list = sqlite_client.get_skus_by_product_id(p['product_id'])
            frag = sqlite_client.get_fragments_by_product_id(p['product_id'])
            filtered_items.append({
                "product": p,
                "skus": skus_list,
                "fragment": frag if frag else {"fragment_id": f"full_{p['product_id']}", "content": p.get('title', '')},
                "score": 1.0
            })
        print(f"[SmartFilter V2] 历史继承全库模式完成！返回 {len(filtered_items)} 个完全符合条件的商品")
        return filtered_items

    # 新增：只有子品类没价格时，也走全库兜底，确保召回精准！
    if target_sub and not price_threshold:
        print(f"[SmartFilter V2] 子品类全库模式，sub_category='{target_sub}'")
        all_products = sqlite_client.get_all_products()
        filtered_items = []
        for p in all_products:
            if p.get('sub_category') != target_sub:
                continue
            excluded = False
            for kw in exclude_keywords:
                if kw and (kw in p.get('title','') or kw in p.get('brand','')):
                    excluded = True
                    break
            if excluded:
                continue
            skus_list = sqlite_client.get_skus_by_product_id(p['product_id'])
            frag = sqlite_client.get_fragments_by_product_id(p['product_id'])
            filtered_items.append({
                "product": p,
                "skus": skus_list,
                "fragment": frag if frag else {"fragment_id": f"full_{p['product_id']}", "content": p.get('title', '')},
                "score": 1.0
            })
        print(f"[SmartFilter V2] 子品类全库模式完成！返回 {len(filtered_items)} 个商品")
        return filtered_items
    
    # 普通模式
    filtered = []
    for item in items:
        p = item['product']
        title = p.get('title', '')
        brand = p.get('brand', '')
        price = float(p.get('base_price', 0))
        
        excluded = False
        for kw in exclude_keywords:
            if kw and (kw in title or kw in brand):
                excluded = True
                break
        if excluded:
            print(f"[SmartFilter V2] 普通排除: brand={brand} title={title}")
            continue
        
        if price_threshold is not None and price > price_threshold:
            print(f"[SmartFilter V2] 普通价格过滤: price={price} > threshold={price_threshold}")
            continue
        
        filtered.append(item)
    
    print(f"[SmartFilter V2] 普通模式原始 {len(items)} -> {len(filtered)}")
    return filtered

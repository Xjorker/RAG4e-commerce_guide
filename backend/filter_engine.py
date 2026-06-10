"""
超强精准过滤引擎 V4.1：修正排除逻辑+宽松功能属性模式
1. 修复反选逻辑："不要华为" → 品牌=华为 从结果中排除华为，其他全部保留
2. 宽松功能属性模式：功能属性没有命中不直接清空结果，只是打印日志，返回所有子品类商品
3. 确保如果过滤后结果为空，返回空列表，不会让大模型瞎编不存在的商品
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.sqlite_client import sqlite_client
import re
import json

COLOR_KEYWORDS = [
    "红", "红色", "蓝", "蓝色", "绿", "绿色", "黑", "黑色", "白", "白色",
    "紫", "紫色", "橙", "橙色", "黄", "黄色", "粉", "粉色", "灰", "灰色",
    "深空黑", "远峰蓝", "宇宙橙", "银色", "金色", "陶瓷黑", "陶瓷白", "星云紫"
]

SUB_CATEGORY_FULL_MAP = {
    '笔记本电脑': ['笔记本', '笔记本电脑', '电脑', '笔记本游戏本'],
    '智能手机': ['手机', '智能手机', '5G手机', '旗舰手机'],
    '平板电脑': ['平板', '平板电脑', 'iPad'],
    '精华': ['精华', '精华露', '精华液'],
    '跑步鞋': ['跑鞋', '跑步鞋', '运动鞋'],
    '篮球鞋': ['篮球鞋', '实战篮球鞋'],
    '登山鞋': ['登山鞋', '徒步鞋', '户外鞋'],
    'T恤': ['T恤', '短袖', '体恤'],
    '卫衣': ['卫衣', '连帽卫衣'],
    '运动长裤': ['长裤', '运动裤', '紧身裤'],
    '帽子': ['帽子', '棒球帽'],
    '速干衣': ['速干衣'],
    '咖啡': ['咖啡', '速溶咖啡'],
    '饮料': ['饮料', '气泡水', '矿泉水', '乌龙茶'],
    '牛奶酸奶': ['牛奶', '酸奶', '纯牛奶', '酸牛奶'],
    '零食糕点': ['零食', '坚果', '糕点', '牛肉干'],
    '方便面': ['方便面', '泡面', '桶面']
}

FUNCTION_ATTRIBUTE_MAP = {
    "鞋子减震": {
        "category": "跑鞋",
        "keywords": ["减震", "缓震", "气垫", "回弹", "弹性", "缓冲", "zoom", "boost", "碳板", "氮气"]
    },
    "护肤品抗衰老": {
        "category": "护肤品",
        "keywords": ["抗衰老", "抗初老", "紧致", "淡纹", "抗皱", "修护", "抗老"]
    },
    "护肤品保湿": {
        "category": "护肤品",
        "keywords": ["保湿", "补水", "滋润", "润肤", "补水保湿", "舒缓", "特护", "敏感肌"]
    },
    "食品辣": {
        "category": "食品",
        "keywords": ["辣", "辣味", "麻辣", "香辣", "爆辣", "特辣"]
    },
    "食品不辣": {
        "category": "食品",
        "keywords": ["不辣", "原味", "清淡", "不辣的", "清汤", "原味"]
    },
    "防晒": {
        "category": "防晒",
        "keywords": ["防晒", "高倍防晒", "SPF", "隔离紫外线"]
    },
    "控油": {
        "category": "彩妆",
        "keywords": ["控油", "持妆", "散粉", "定妆", "不脱妆"]
    }
}

GLOBAL_FULL_HISTORY_CACHE = {}

def extract_all_brands_from_db():
    brands = set()
    all_products = sqlite_client.get_all_products()
    for p in all_products:
        b = p.get('brand', '')
        if b and len(b) > 0:
            brands.add(b)
            if ' ' in b:
                for part in b.split():
                    if len(part) > 1:
                        brands.add(part)
    return list(brands)

ALL_DB_BRANDS = extract_all_brands_from_db()
print(f"[Filter V4.1] 初始化完成: 品牌库={len(ALL_DB_BRANDS)} 功能属性={len(FUNCTION_ATTRIBUTE_MAP)}")

def infer_target_subcategory_from_query(query: str):
    for sub_cat, hints in SUB_CATEGORY_FULL_MAP.items():
        for h in hints:
            if h in query:
                return sub_cat
    return None

def parse_price_constraint_v3(query: str, last_base_price: float = None):
    absolute_patterns = [
        (r'(\d+(?:\.\d+)?)以下', lambda x: float(x)),
        (r'(\d+(?:\.\d+)?)元以下', lambda x: float(x)),
        (r'(\d+(?:\.\d+)?)以内', lambda x: float(x)),
        (r'(\d+(?:\.\d+)?)元以内', lambda x: float(x)),
        (r'预算\s*(\d+(?:\.\d+)?)', lambda x: float(x)),
        (r'不超过\s*(\d+(?:\.\d+)?)', lambda x: float(x)),
        (r'不超过\s*(\d+(?:\.\d+)?)元', lambda x: float(x)),
        (r'小于\s*(\d+(?:\.\d+)?)', lambda x: float(x)),
        (r'低于\s*(\d+(?:\.\d+)?)', lambda x: float(x)),
        (r'不超过\s*(\d+(?:\.\d+)?)块', lambda x: float(x)),
    ]
    
    for p, handler in absolute_patterns:
        m = re.search(p, query)
        if m:
            price_val = handler(m.group(1))
            return ('max', price_val)
    
    if last_base_price is not None:
        if '更贵' in query or '贵一点' in query or '贵一些' in query:
            return ('relative_higher', last_base_price * 1.3)
        if '更便宜' in query or '便宜一点' in query or '便宜一些' in query:
            return ('relative_lower', last_base_price * 0.7)
    
    return None

def extract_brand_from_query(query: str):
    for b in ALL_DB_BRANDS:
        if b in query:
            return b
    return None

def extract_color_from_query(query: str):
    for c in COLOR_KEYWORDS:
        if c in query:
            return c
    return None

def extract_function_attribute_from_query(query: str):
    matched_funcs = []
    for func_name, func_info in FUNCTION_ATTRIBUTE_MAP.items():
        kw_list = func_info['keywords']
        hit_count = 0
        for kw in kw_list:
            if kw in query:
                hit_count += 1
        if hit_count >= 1:
            matched_funcs.append(func_name)
    return matched_funcs

def is_pure_inherit_query(query: str):
    no_new_brand = extract_brand_from_query(query) is None
    no_new_sub = infer_target_subcategory_from_query(query) is None
    return no_new_brand and no_new_sub

def is_exclude_brand_query(query: str, brand_name: str):
    """判断是不是要排除某个品牌（比如不要华为的）"""
    exclude_patterns = ['不要', '别', '不含', '除了', '不是']
    for p in exclude_patterns:
        if p in query and brand_name in query:
            return True
    return False

def smart_filter_products(items, query, exclude_keywords: list, session_id=None):
    """
    V4.1 修复版
    """
    global GLOBAL_FULL_HISTORY_CACHE
    
    current_price_tuple = parse_price_constraint_v3(query)
    current_sub = infer_target_subcategory_from_query(query)
    current_brand = extract_brand_from_query(query)
    current_color = extract_color_from_query(query)
    current_func_attrs = extract_function_attribute_from_query(query)
    
    cached = GLOBAL_FULL_HISTORY_CACHE.get(session_id, {}) if session_id else {}
    last_sub = cached.get('last_sub', None)
    last_brand = cached.get('last_brand', None)
    last_abs_price_base = cached.get('last_abs_price_base', 99999.0)
    last_func_attrs = cached.get('last_func_attrs', [])
    last_exclude_brand = cached.get('last_exclude_brand', None)
    
    is_pure_inherit = is_pure_inherit_query(query)
    target_sub = current_sub if current_sub else (last_sub if is_pure_inherit else None)
    target_price_tuple = current_price_tuple
    if is_pure_inherit and target_price_tuple is None:
        target_price_tuple = parse_price_constraint_v3(query, last_abs_price_base)
    
    # ========= 修复品牌逻辑！支持"不要华为"反选 =========
    target_exclude_brand = None
    target_include_brand = None  # 提前初始化，避免未定义
    if current_brand:
        if is_exclude_brand_query(query, current_brand):
            # 排除模式：不要这个品牌
            target_exclude_brand = current_brand
            print(f"[Filter V4.1] 识别到排除品牌模式: 不要 {current_brand}")
        else:
            # 正常模式：要这个品牌
            target_include_brand = current_brand
    else:
        target_include_brand = last_brand if is_pure_inherit else None
    if not target_exclude_brand and last_exclude_brand and is_pure_inherit:
        target_exclude_brand = last_exclude_brand
    
    target_func_attrs = current_func_attrs if len(current_func_attrs) > 0 else (last_func_attrs if is_pure_inherit else [])
    
    print(f"[Filter V4.1] ================= 解析结果 ===================")
    print(f"[Filter V4.1]  query={query}")
    print(f"[Filter V4.1]  子品类={target_sub} 包含品牌={target_include_brand} 排除品牌={target_exclude_brand}")
    print(f"[Filter V4.1]  价格={target_price_tuple} 颜色={current_color} 功能属性={target_func_attrs}")
    
    # 更新历史缓存
    if not is_pure_inherit and session_id:
        if current_sub:
            GLOBAL_FULL_HISTORY_CACHE[session_id] = GLOBAL_FULL_HISTORY_CACHE.get(session_id, {})
            GLOBAL_FULL_HISTORY_CACHE[session_id]['last_sub'] = current_sub
        if current_brand and not is_exclude_brand_query(query, current_brand):
            GLOBAL_FULL_HISTORY_CACHE[session_id] = GLOBAL_FULL_HISTORY_CACHE.get(session_id, {})
            GLOBAL_FULL_HISTORY_CACHE[session_id]['last_brand'] = current_brand
        if target_exclude_brand:
            GLOBAL_FULL_HISTORY_CACHE[session_id] = GLOBAL_FULL_HISTORY_CACHE.get(session_id, {})
            GLOBAL_FULL_HISTORY_CACHE[session_id]['last_exclude_brand'] = target_exclude_brand
        if target_price_tuple and target_price_tuple[0] in ['max', 'relative_higher', 'relative_lower']:
            val = target_price_tuple[1]
            GLOBAL_FULL_HISTORY_CACHE[session_id] = GLOBAL_FULL_HISTORY_CACHE.get(session_id, {})
            GLOBAL_FULL_HISTORY_CACHE[session_id]['last_price'] = val
            GLOBAL_FULL_HISTORY_CACHE[session_id]['last_abs_price_base'] = val
        if len(current_func_attrs) > 0:
            GLOBAL_FULL_HISTORY_CACHE[session_id] = GLOBAL_FULL_HISTORY_CACHE.get(session_id, {})
            GLOBAL_FULL_HISTORY_CACHE[session_id]['last_func_attrs'] = current_func_attrs
    
    all_products = sqlite_client.get_all_products()
    result = []
    
    for p in all_products:
        p_id = p.get('product_id')
        p_title = p.get('title','')
        p_brand = p.get('brand','')
        p_sub = p.get('sub_category','')
        p_price = float(p.get('base_price', 0))
        
        # 维度1：子品类过滤
        if target_sub and p_sub != target_sub:
            continue
        
        # 维度2：包含品牌 过滤（正常模式）
        if target_include_brand and target_include_brand not in p_brand and target_include_brand not in p_title:
            continue
        
        # 维度3：排除品牌 过滤（反选模式：不要华为）
        if target_exclude_brand and (target_exclude_brand in p_brand or target_exclude_brand in p_title):
            print(f"[Filter V4.1] 排除品牌商品: {p_title} (命中不要 {target_exclude_brand})")
            continue
        
        # 维度4：普通排除关键词
        excluded = False
        for kw in exclude_keywords:
            if kw and (kw in p_title or kw in p_brand):
                excluded = True
                break
        if excluded:
            print(f"[Filter V4.1] 排除关键词: {p_title}")
            continue
        
        # 维度5：价格过滤
        price_ok = True
        if target_price_tuple:
            price_type, price_val = target_price_tuple
            if price_type == 'max' and p_price > price_val:
                price_ok = False
            if price_type == 'relative_higher' and p_price < price_val:
                price_ok = False
            if price_type == 'relative_lower' and p_price > price_val:
                price_ok = False
        if not price_ok:
            continue
        
        skus_list = sqlite_client.get_skus_by_product_id(p_id)
        
        # 维度6：颜色过滤
        if current_color and len(skus_list) > 0:
            has_color_sku = False
            for sku in skus_list:
                try:
                    props = json.loads(sku.get('properties', '{}')) if isinstance(sku.get('properties'), str) else sku.get('properties', {})
                    props_str = str(props)
                    if current_color in props_str:
                        has_color_sku = True
                        break
                except:
                    pass
            if not has_color_sku:
                continue
        
        # V4.1 宽松功能属性模式：只打日志，不清空结果！
        # 这样就不会出现"来点辣的方便面"返回0的问题
        func_attr_ok = True
        if len(target_func_attrs) > 0:
            frag = sqlite_client.get_fragments_by_product_id(p_id)
            all_content_to_check = p_title + " " + (frag.get('content','') if frag else "")
            matched_any_func = False
            for fname in target_func_attrs:
                func_info = FUNCTION_ATTRIBUTE_MAP.get(fname, {})
                for kw in func_info.get('keywords', []):
                    if kw in all_content_to_check:
                        matched_any_func = True
                        break
                if matched_any_func:
                    break
            if not matched_any_func:
                print(f"[Filter V4.1] 提示: 商品[{p_title}]未命中功能属性约束，但仍然保留（宽松模式）")
        
        # 所有检查通过！加入结果
        frag_final = sqlite_client.get_fragments_by_product_id(p_id)
        result.append({
            "product": p,
            "skus": skus_list,
            "fragment": frag_final if frag_final else {"fragment_id": f"full_{p_id}", "content": p_title},
            "score": 1.0
        })
    
    print(f"[Filter V4.1] 过滤完成！最终返回 {len(result)} 个商品")
    return result

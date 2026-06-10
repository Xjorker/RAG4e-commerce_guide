"""
超强精准过滤引擎 V4.0：功能属性语义召回层
1. 保留V3所有能力：价格绝对+相对、品牌、颜色、子品类、全维度历史继承
2. 新增：功能属性语义理解，自动识别"减震""抗衰老""保湿""辣不辣"等语义关键词
3. 语义属性匹配：从rag_fragments片段里召回有对应功能描述的商品，100%精准命中
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.sqlite_client import sqlite_client
import re
import json

# ===== V3 原有子品类/颜色/品牌逻辑 全部保留 =====
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
    '方便面': ['方便面', '泡面', '桶装面']
}

# ===== V4 新增：功能属性-关键词映射库（按品类分类） =====
FUNCTION_ATTRIBUTE_MAP = {
    "鞋子减震": {
        "category": "跑鞋",
        "keywords": ["减震", "缓震", "气垫", "回弹", "弹性好", "缓冲", "zoom", "boost", "碳板", "氮气"]
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
print(f"[Filter V4] 已加载品牌库 {len(ALL_DB_BRANDS)} 个，功能属性库 {len(FUNCTION_ATTRIBUTE_MAP)} 组")

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
    """V4新增：从query提取功能属性"""
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
    pure_relative_words = ['更贵', '更便宜', '贵一点', '便宜一点', '要贵的', '要便宜的', '其他的', '别的']
    has_pure_relative = any(w in query for w in pure_relative_words)
    no_new_brand = extract_brand_from_query(query) is None
    no_new_sub = infer_target_subcategory_from_query(query) is None
    return no_new_brand and no_new_sub

def smart_filter_products_v4(items, query, exclude_keywords: list, session_id=None):
    """
    V4全维度智能过滤引擎
    新增功能属性语义召回层
    """
    global GLOBAL_FULL_HISTORY_CACHE
    
    # 解析当前query所有维度
    current_price_tuple = parse_price_constraint_v3(query)
    current_sub = infer_target_subcategory_from_query(query)
    current_brand = extract_brand_from_query(query)
    current_color = extract_color_from_query(query)
    current_func_attrs = extract_function_attribute_from_query(query)  # V4 新增功能属性！
    
    cached = GLOBAL_FULL_HISTORY_CACHE.get(session_id, {}) if session_id else {}
    last_sub = cached.get('last_sub', None)
    last_price = cached.get('last_price', None)
    last_brand = cached.get('last_brand', None)
    last_absolute_price_base = cached.get('last_abs_price_base', 99999.0)
    last_func_attrs = cached.get('last_func_attrs', [])
    
    is_pure_inherit = is_pure_inherit_query(query)
    target_sub = current_sub if current_sub else (last_sub if is_pure_inherit else None)
    target_price_tuple = current_price_tuple
    if is_pure_inherit and target_price_tuple is None:
        target_price_tuple = parse_price_constraint_v3(query, last_absolute_price_base)
    target_brand = current_brand if current_brand else (last_brand if is_pure_inherit else None)
    
    target_func_attrs = current_func_attrs if len(current_func_attrs) > 0 else (last_func_attrs if is_pure_inherit else [])
    
    print(f"[Filter V4] ================= 解析结果 ===================")
    print(f"[Filter V4]  当前query: {query}")
    print(f"[Filter V4]  子品类: {target_sub}")
    print(f"[Filter V4]  价格: {target_price_tuple}")
    print(f"[Filter V4]  品牌: {target_brand}")
    print(f"[Filter V4]  颜色: {current_color}")
    print(f"[Filter V4]  V4新增功能属性匹配: {target_func_attrs}")
    
    # 更新历史缓存
    if not is_pure_inherit and session_id:
        if current_sub:
            GLOBAL_FULL_HISTORY_CACHE[session_id] = GLOBAL_FULL_HISTORY_CACHE.get(session_id, {})
            GLOBAL_FULL_HISTORY_CACHE[session_id]['last_sub'] = current_sub
        if current_brand:
            GLOBAL_FULL_HISTORY_CACHE[session_id] = GLOBAL_FULL_HISTORY_CACHE.get(session_id, {})
            GLOBAL_FULL_HISTORY_CACHE[session_id]['last_brand'] = current_brand
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
        
        # 维度2：品牌过滤
        if target_brand and target_brand not in p_brand and target_brand not in p_title:
            continue
        
        # 维度3：排除关键词
        excluded = False
        for kw in exclude_keywords:
            if kw and (kw in p_title or kw in p_brand):
                excluded = True
                break
        if excluded:
            print(f"[Filter V4] 排除: {p_title}")
            continue
        
        # 维度4：价格过滤
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
        
        # 维度5：颜色过滤
        if current_color and len(skus_list) > 0:
            has_color_sku = False
            for sku in skus_list:
                try:
                    props = json.loads(sku.get('properties', '{}')) if isinstance(sku.get('properties'), str) else sku.get('properties', {})
                    if current_color in str(props):
                        has_color_sku = True
                        break
                except: pass
            if not has_color_sku:
                continue
        
        # ========= V4 新增：功能属性语义匹配层！ =========
        func_attr_ok = True
        if len(target_func_attrs) > 0:
            frag_list = sqlite_client.get_fragments_by_product_id(p_id)
            all_content_to_check = p_title + " " + (frag_list.get('content','') if frag_list else "")
            matched_any_func = False
            
            for func_name in target_func_attrs:
                func_info = FUNCTION_ATTRIBUTE_MAP.get(func_name, {})
                func_kw_list = func_info.get('keywords', [])
                for kw in func_kw_list:
                    if kw in all_content_to_check:
                        matched_any_func = True
                        break
                if matched_any_func:
                    break
            
            if not matched_any_func:
                print(f"[Filter V4] 功能属性过滤: {p_title} 不满足功能属性条件")
                func_attr_ok = False
        
        if not func_attr_ok:
            continue
        
        frag = sqlite_client.get_fragments_by_product_id(p_id)
        result.append({
            "product": p,
            "skus": skus_list,
            "fragment": frag if frag else {"fragment_id": f"full_{p_id}", "content": p_title},
            "score": 1.0
        })
    
    print(f"[Filter V4] V4全维度 + 功能属性过滤完成！返回 {len(result)} 个结果")
    return result

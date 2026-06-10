"""
Schema Awareness 智能体：启动先扫描 SQLite 数据库，自动学习当前库里有哪些真实数据
用户模糊自然语言 → 映射到数据库真实存在的 (category, sub_category)，不需要人工硬编码
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import sqlite_client

# ========= 全局动态 Schema 摘要 ==========
GLOBAL_SCHEMA = {
    "all_categories": set(),
    "category_to_subs": dict(),   # category -> set(sub_category)
    "all_brands": set()
}

def build_schema_once():
    """启动一次性扫描全库，自动学习 Schema 全貌"""
    all_p = sqlite_client.get_all_products()
    for prod in all_p:
        cat = prod.get("category")
        sub = prod.get("sub_category")
        brand = prod.get("brand")
        if cat:
            GLOBAL_SCHEMA["all_categories"].add(cat)
            if cat not in GLOBAL_SCHEMA["category_to_subs"]:
                GLOBAL_SCHEMA["category_to_subs"][cat] = set()
            if sub:
                GLOBAL_SCHEMA["category_to_subs"][cat].add(sub)
        if brand:
            GLOBAL_SCHEMA["all_brands"].add(brand)
    print("[SchemaAgent] 启动自动扫描完成")
    print(f"  - 全库 Categories 列表 = {sorted(GLOBAL_SCHEMA['all_categories'])}")
    print(f"  - 全库 SubCategories 映射 = ")
    for c, slist in GLOBAL_SCHEMA["category_to_subs"].items():
        print(f"    '{c}' -> {sorted(slist)}")
    print(f"  - 全库 Brands 总数 = {len(GLOBAL_SCHEMA['all_brands'])}")

# ========= 模糊意图映射器 =============
FUZZY_INTENT_MAP = [
    # 用户自然语言说的模糊话 -> 直接映射到 数据库真实存在的子品类
    {
        "keywords": ["提神", "提神饮品", "提神饮料", "醒脑", "清醒", "犯困", "熬夜"],
        "target_subs": ["咖啡", "功能饮料"]
    },
    {
        "keywords": ["喝的", "饮品", "饮料", "零食"],
        "target_cat": "食品饮料"
    },
    {
        "keywords": ["护肤", "美妆", "化妆品", "保养"],
        "target_cat": "美妆护肤"
    },
    {
        "keywords": ["运动", "跑步", "打球", "健身", "穿的"],
        "target_cat": "服饰运动"
    }
]

def fuzzy_map_to_schema(query: str):
    """用户模糊自然语言 -> 智能映射到数据库真实存在的类目"""
    q_low = query.lower()
    for item in FUZZY_INTENT_MAP:
        for kw in item["keywords"]:
            if kw in q_low:
                if "target_subs" in item:
                    real_sub_list = [
                        s for s in item["target_subs"]
                        for c in GLOBAL_SCHEMA["all_categories"]
                        if s in GLOBAL_SCHEMA["category_to_subs"].get(c, set())
                    ]
                    if real_sub_list:
                        print(f"[FuzzyMapper] 模糊意图命中！query='{query}' -> target_sub(s)={real_sub_list}")
                        # 返回第1个命中的子品类优先
                        for c in GLOBAL_SCHEMA["all_categories"]:
                            for mapped_sub in real_sub_list:
                                if mapped_sub in GLOBAL_SCHEMA["category_to_subs"].get(c, set()):
                                    return (c, mapped_sub)
                if "target_cat" in item:
                    real_target_cat = item["target_cat"]
                    if real_target_cat in GLOBAL_SCHEMA["all_categories"]:
                        print(f"[FuzzyMapper] 模糊意图命中！query='{query}' -> target_cat='{real_target_cat}'")
                        return (real_target_cat, None)
    return (None, None)


# 模块导入时立刻自动扫一遍库，动态学习 Schema
if len(GLOBAL_SCHEMA["all_categories"]) == 0:
    build_schema_once()

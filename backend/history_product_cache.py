"""
历史商品缓存模块 V2：每个session保存完整历史商品列表
当用户说"把第N个加入购物车"、"这几款对比一下"，直接从历史缓存里定位，100%精准匹配
完全跳过向量召回，绝对不会出现返回红牛饮料这种完全无关的结果！
"""
import re
from typing import List, Dict, Any

# 全局缓存: session_id -> { "last_products": List[product_item], "all_history": List[List[product_item]] }
SESSION_PRODUCT_CACHE: Dict[str, Dict[str, Any]] = {}

def save_products_to_cache(session_id: str, products: List[Dict[str, Any]]):
    """每次返回商品卡片给用户之前，保存到历史缓存"""
    if not session_id:
        return
    
    if session_id not in SESSION_PRODUCT_CACHE:
        SESSION_PRODUCT_CACHE[session_id] = {
            "last_products": [],
            "all_history": []
        }
    
    SESSION_PRODUCT_CACHE[session_id]["last_products"] = products
    SESSION_PRODUCT_CACHE[session_id]["all_history"].append(products)
    print(f"[HistoryCache] session={session_id} 保存商品数 = {len(products)}")

def find_target_product_from_history(session_id: str, add_to_cart_keyword: str):
    """
    从该session的历史商品缓存里，通过用户的关键词定位目标商品
    搜索范围：所有历史轮次的所有商品（去重后），保证多轮对话后仍能正确定位

    支持：
    1. "第一个" / "第二个" -> 按最近一轮的索引定位
    2. "macbook pro" -> 标题/品牌模糊匹配（遍历所有历史）
    """
    if session_id not in SESSION_PRODUCT_CACHE:
        print(f"[HistoryCache] 缓存 miss，session={session_id} 没有历史商品")
        return None

    last_products = SESSION_PRODUCT_CACHE[session_id].get("last_products", [])
    all_history_lists = SESSION_PRODUCT_CACHE[session_id].get("all_history", [])

    # 把所有历史商品汇总并去重（按product_id）
    seen_pids = set()
    all_products = []
    for hist_list in all_history_lists:
        for item in hist_list:
            p = item.get('product', {})
            pid = p.get('product_id', '')
            if pid and pid not in seen_pids:
                seen_pids.add(pid)
                all_products.append(item)

    print(f"[HistoryCache] 命中历史缓存，最近一轮 {len(last_products)} 个，跨所有历史 {len(all_products)} 个")

    # 模式A：第N个 -> 在最近一轮里按索引定位
    idx_match = re.search(r'第\s*(\d+)\s*个', add_to_cart_keyword)
    if idx_match:
        target_idx = int(idx_match.group(1)) - 1
        if 0 <= target_idx < len(last_products):
            found = last_products[target_idx]
            print(f"[HistoryCache] 索引匹配成功！取最近一轮第 {target_idx+1} 个商品")
            return found

    # 模式B：关键词在商品标题/品牌里模糊匹配（遍历所有历史）
    kw_low = add_to_cart_keyword.lower()
    # 优先匹配最近一轮
    for item in last_products:
        p = item.get('product', {})
        title = p.get('title', '').lower()
        brand = p.get('brand', '').lower()
        if kw_low and (kw_low in title or kw_low in brand):
            print(f"[HistoryCache] 关键词模糊匹配成功(最近一轮)！{p.get('title')}")
            return item
    # 再在全部历史里兜底查找
    for item in all_products:
        p = item.get('product', {})
        title = p.get('title', '').lower()
        brand = p.get('brand', '').lower()
        if kw_low and (kw_low in title or kw_low in brand):
            print(f"[HistoryCache] 关键词模糊匹配成功(全部历史)！{p.get('title')}")
            return item

    print(f"[HistoryCache] 缓存里没有找到匹配商品，keyword={add_to_cart_keyword}")
    return None

def is_pure_compare_query(query: str) -> bool:
    """判断用户当前query是不是纯对比短句，直接从历史缓存取商品，完全跳过向量召回！"""
    compare_patterns = ['对比一下', '对比', '比较一下', '比一下', '这几款对比']
    q_stripped = query.strip()
    # 长度非常短，同时包含对比关键词
    for pat in compare_patterns:
        if pat in q_stripped and len(q_stripped) <= 15:
            return True
    return False

def get_last_recommended_products_for_compare(session_id: str) -> List[Dict[str, Any]]:
    """纯对比场景直接取session上一轮给用户推荐过的商品，完全不重新召回！
    关键：补全完整结构，确保和普通检索返回的 item 格式 100% 兼容，不影响结构化生成！
    """
    if session_id not in SESSION_PRODUCT_CACHE:
        return []
    
    raw_list = SESSION_PRODUCT_CACHE[session_id].get("last_products", [])
    print(f"[CompareHistory] 从历史缓存取商品做对比，原始数量 {len(raw_list)}")
    
    full_format_result = []
    for item_data in raw_list:
        p = item_data.get('product', {})
        full_format_result.append({
            "product": p,
            "skus": item_data.get('skus', []),
            "fragment": {
                "fragment_id": f"compare_{p.get('product_id', '')}",
                "content": p.get('title', '')
            },
            "score": 1.0
        })
    
    print(f"[CompareHistory] 格式补全完成，返回给结构化生成器的商品数 = {len(full_format_result)}")
    return full_format_result

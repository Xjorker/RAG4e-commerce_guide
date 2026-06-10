"""
基于LLM回复反向校准展示卡片
1. 解析LLM回复，提取里面提到的所有商品标题/品牌
2. 拿这个集合和 retrieved 列表做模糊匹配
3. 返回按LLM回复顺序排列的商品列表
"""
import re


def extract_product_mentions_from_reply(reply_text: str, retrieved_items: list) -> list:
    """
    从LLM回复里识别出实际提到的商品，按回复中出现的顺序返回
    :param reply_text: LLM的完整回复
    :param retrieved_items: 后端候选商品列表，元素结构是 {product: {...}, skus: [...], fragment: {...}}
    :return: 按LLM回复里出现顺序的retrieved_items子集
    """
    if not reply_text or not retrieved_items:
        return []

    # 构建 (品牌/标题片段) -> item 的映射
    keyword_to_item = {}
    for idx, item in enumerate(retrieved_items):
        p = item.get('product', {})
        title = p.get('title', '') or ''
        brand = p.get('brand', '') or ''

        # 收集品牌名作为强匹配信号
        if brand:
            keyword_to_item[brand.strip()] = (idx, item)

        # 收集标题里 4+ 字的连续片段作为弱匹配信号
        cleaned = re.sub(r'[\d\(\)（）。.]', ' ', title)
        for seg in cleaned.split():
            seg = seg.strip()
            if len(seg) >= 3:
                keyword_to_item[seg] = (idx, item)

        # 整标题也作为匹配
        keyword_to_item[title] = (idx, item)

    # 用滑动窗口扫描LLM回复，记录每个商品首次出现位置
    occurrences = {}  # idx -> first_pos
    for kw, (idx, item) in keyword_to_item.items():
        if not kw:
            continue
        pos = reply_text.find(kw)
        if pos >= 0 and idx not in occurrences:
            occurrences[idx] = pos

    # 按出现位置排序，返回对应的item列表
    sorted_indices = sorted(occurrences.keys(), key=lambda i: occurrences[i])
    matched_items = [retrieved_items[i] for i in sorted_indices]

    print(f"[CardAlign] LLM回复里识别到 {len(matched_items)} 个商品")

    return matched_items

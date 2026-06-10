"""快速修复，替换 main.py 中从第 420 行之后的部分，完全修复所有问题"""
    # === 反选与排除识别 ===
    exclude_keywords = []
    pure_exclude_query = False  # 是否是"不要X"这种纯排除型查询（无任何正向内容）
    # 模式1: "不要X的"
    for m in re.finditer(r'不要(.+?)(?:的|，|。|$)', query):
        exclude_keywords.append(m.group(1).strip())
        pure_exclude_query = True
    # 模式2: "除了X"
    for m in re.finditer(r'除[了非](.+?)(?:还有什么|以外|都|，|。|$)', query):
        exclude_keywords.append(m.group(1).strip())
        pure_exclude_query = True
    # 模式3: "X以外"
    for m in re.finditer(r'(.+?)以外(?:的)?', query):
        exclude_keywords.append(m.group(1).strip())
        pure_exclude_query = True

    # 先推断目标 (类目, 子品类)
    # 第1层最高优先级：LLM模糊意图推理，"提神饮品" → 自动推理成库里真实的"咖啡"
    from services.llm_fuzzy_reason import llm_reason_fuzzy_intent
    llm_reasoned_cate, llm_reasoned_sub = llm_reason_fuzzy_intent(query)
    if llm_reasoned_cate and llm_reasoned_sub:
        target_cat, target_sub = llm_reasoned_cate, llm_reasoned_sub
        print(f"[LLMFuzzy] 模糊意图推理成功！query='{query}' 直接命中精确真实子品类 ('{target_cat}'/'{target_sub}')")
    else:
        # 第2层兜底：普通硬关键词匹配
        target_cat, target_sub = detect_target_with_history(query, req.history)

    # 识别是否是"把第 N 个加入购物车"
    import re
    idx_match = re.search(r'第\s*(\d+)\s*个', query)
    retrieved = []
    is_index_cart = False
    if idx_match and add_to_cart_intent:
        is_index_cart = True
        target_idx = int(idx_match.group(1)) - 1
        print(f"[IndexMode] 直接索引模式，取第 {target_idx+1} 个商品")
        # 从 req.history 取最近返回的 products（安卓端会携带）
        if req.history:
            for msg in req.history:
                if msg.get("products"):
                    for prod in msg["products"]:
                        skus_list = prod.get("skus", [])
                        retrieved.append({
                            "product": prod.get("product"),
                            "skus": skus_list,
                            "fragment": {
                                "fragment_id": f"hist_{prod['product'].get('product_id')}",
                                "content": prod['product'].get('title', '')
                            },
                            "score": 1.0
                        })
        # 若历史为空，直接用当前类目全量商品
        if not retrieved:
            for p in sqlite_client.get_all_products():
                match = False
                if target_sub and p.get('sub_category') == target_sub:
                    match = True
                elif target_cat and p.get('category') == target_cat and not target_sub:
                    match = True
                if match:
                    skus_list = sqlite_client.get_skus_by_product_id(p['product_id'])
                    retrieved.append({
                        "product": p,
                        "skus": skus_list,
                        "fragment": {
                            "fragment_id": f"def_{p['product_id']}",
                            "content": p.get('title', '')
                        },
                        "score": 1.0
                    })
        # 截取目标索引之后的全部，保留顺序
        if 0 &lt;= target_idx &lt; len(retrieved):
            retrieved = retrieved[target_idx:target_idx+1]
        print(f"[IndexMode] 最终选中的商品数 = {len(retrieved)}")
    else:
        # 普通查询：走正常逻辑
        # 纯排除型查询（用户只说"不要华为的"）
        if pure_exclude_query and exclude_keywords:
            print(f"[PureExclude] 纯排除模式，类目=({target_cat}/{target_sub})")
            for p in sqlite_client.get_all_products():
                match = False
                if target_sub and p.get('sub_category') == target_sub:
                    match = True
                elif target_cat and p.get('category') == target_cat and not target_sub:
                    match = True
                elif not target_cat and not target_sub:
                    match = True
                if match:
                    skus_list = sqlite_client.get_skus_by_product_id(p['product_id'])
                    frag = sqlite_client.get_fragments_by_product_id(p['product_id'])
                    retrieved.append({
                        "product": p,
                        "skus": skus_list,
                        "fragment": frag if frag else {"fragment_id": f"px_{p['product_id']}", "content": p.get('title', '')},
                        "score": 1.0
                    })
        else:
            # 常规流程
            full_parse_result = parse_and_full_filter_products(query)
            try:
                if full_parse_result:
                    retrieved = full_parse_result
                    print(f"[FullIntent] 全量解析，返回 {len(retrieved)}")
                else:
                    qe = embedding_service.embed_text(query)
                    retrieved = hybrid_retrieval_service.hybrid_search(query, qe, target_category=target_cat, target_sub=target_sub)
            except Exception as e:
                raise HTTPException(status_code=503, detail=str(e))

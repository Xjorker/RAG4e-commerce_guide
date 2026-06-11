import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, UploadFile, File, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uuid
import base64
import random
import json
import asyncio
from typing import List, Dict, Any, Optional
from config import settings
from services import embedding_service, hybrid_retrieval_service, llm_service
from database import sqlite_client
from user_auth import get_auth_manager

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

class ChatRequest(BaseModel):
    session_id: str = ""
    query: str
    history: Optional[List[Dict[str, str]]] = None

class SearchRequest(BaseModel):
    query: str

# 类目关键词表
CATEGORY_KEYWORDS = {
    "美妆护肤": ["精华", "面霜", "眼霜", "面膜", "洁面", "爽肤水", "乳液", "护肤", "口红", "粉底", "眼影", "防晒", "隔离", "香水", "美妆", "雅诗兰黛", "兰蔻", "SK-II", "资生堂", "倩碧", "欧莱雅"],
    "数码电子": ["耳机", "手机", "笔记本", "电脑", "switch", "相机", "键盘", "鼠标", "平板", "音响", "充电宝", "手环", "手表", "耳机", "音箱", "AirPods", "FreeBuds", "华为", "苹果", "iPhone", "Mac", "iPad"],
    "食品饮料": ["饮料", "咖啡", "牛奶", "零食", "方便面", "矿泉水", "薯片", "坚果", "巧克力", "饼干", "奶茶", "可口可乐", "农夫山泉", "康师傅", "三得利", "元气森林"],
    "服饰运动": ["T恤", "衣服", "鞋子", "运动鞋", "运动服", "外套", "牛仔裤", "跑鞋", "篮球鞋", "Nike", "Adidas", "运动", "安踏", "李宁"]
}

def detect_target_category(query: str):
    q_low = query.lower()
    best_cat = None
    max_hits = 0
    for cat, kw_list in CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in kw_list if kw.lower() in q_low)
        if hits > max_hits:
            max_hits = hits
            best_cat = cat
    return best_cat if max_hits > 0 else None

def filter_by_category(rets, target_cat):
    if not target_cat:
        return rets
    filtered = [
        x for x in rets
        if (x['product'].get('category') == target_cat)
    ]
    if len(filtered) < 2:
        return rets[:6]
    return filtered

@app.get("/")
async def root():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.VERSION}

@app.get("/health")
async def health():
    return {"status": "healthy"}

async def stream_chat_response(req: ChatRequest):
    session_id = req.session_id if req.session_id else str(uuid.uuid4())
    query = req.query.strip()

    yield 'data: ' + json.dumps({'type': 'session', 'session_id': session_id}, ensure_ascii=False) + '\n\n'

    if not query:
        yield 'data: ' + json.dumps({'type': 'error', 'message': 'query cannot be empty'}, ensure_ascii=False) + '\n\n'
        return

    # ===== SSE 也完整提取反选关键词，和非流接口 100% 对齐 =====
    import re
    exclude_keywords = []
    for m in re.finditer(r'不要(.+?)(?:的|，|。|$)', query):
        exclude_keywords.append(m.group(1).strip())
    for m in re.finditer(r'除[了非](.+?)(?:还有什么|以外|都|，|。|$)', query):
        exclude_keywords.append(m.group(1).strip())
    for m in re.finditer(r'(.+?)以外(?:的)?', query):
        exclude_keywords.append(m.group(1).strip())

    # SSE 也完全支持纯对比模式，直接从历史缓存取商品，跳过向量召回
    from history_product_cache import is_pure_compare_query, get_last_recommended_products_for_compare
    sse_pure_compare_flag = False
    sse_pure_compare_too_many = False
    retrieved = []
    if is_pure_compare_query(query):
        sse_pure_compare_flag = True
        retrieved = get_last_recommended_products_for_compare(session_id)
        # 即使是历史缓存取商品也必须执行 V2 过滤：反选+价格过滤！
        from filter_engine import smart_filter_products
        retrieved = smart_filter_products(retrieved, query, exclude_keywords, session_id)
        if len(retrieved) > 5:
            sse_pure_compare_too_many = True
            retrieved = retrieved[:5]
        print(f"[SSE-PureCompare] 纯对比模式激活，过滤后剩余 {len(retrieved)} 商品")
    else:
        # 非纯对比词，正常向量召回
        try:
            query_embedding = embedding_service.embed_text(query)
            retrieved = hybrid_retrieval_service.hybrid_search(query, query_embedding)
        except Exception as e:
            yield 'data: ' + json.dumps({'type': 'error', 'message': f'Embedding service unavailable: {str(e)}'}, ensure_ascii=False) + '\n\n'
            return

    seen_pids_sse = set()
    deduped_sse = []
    for item in retrieved:
        pid = item['product'].get('product_id', '')
        if pid and pid not in seen_pids_sse:
            seen_pids_sse.add(pid)
            deduped_sse.append(item)
    retrieved = deduped_sse

    retrieved.sort(key=lambda x: x.get('score', 0.0), reverse=True)
    target_cat = detect_target_category(query)
    print(f'[SSE CategoryDetect] query="{query}" -> target_category="{target_cat}"')
    retrieved = filter_by_category(retrieved, target_cat)
    
    # SSE 完全接入V2过滤引擎：反选关键词 + session历史继承，100%和非流接口对齐！
    from filter_engine import smart_filter_products
    retrieved = smart_filter_products(retrieved, query, exclude_keywords, session_id)

    # 用户没指定数量时，默认返回5个商品
    retrieved = retrieved[:5]

    print(f'[SSE Final] after filter, total {len(retrieved)} products')

    products_data = []
    for item in retrieved:
        products_data.append({
            "product": item['product'],
            "skus": item['skus']
        })

    # SSE接口也保存商品到历史缓存，和非流接口完全对齐
    from history_product_cache import save_products_to_cache
    save_products_to_cache(session_id, products_data)

    # SSE接口也支持加购intent识别
    sse_add_to_cart_intent = None
    import re
    _sse_triggers = ['加购物车', '加入购物车', '加到购物车', '放进购物车', '加购']
    for _t in _sse_triggers:
        _idx = query.find(_t)
        if _idx > 0:
            _kw = query[:_idx]
            _kw = re.sub(r'^(把|将|帮|要|请|麻烦你?|请帮我?)', '', _kw)
            _kw = re.sub(r'(也|就|啊|吧|呀)$', '', _kw)
            _kw = _kw.strip()
            if _kw:
                sse_add_to_cart_intent = _kw
            break

    sse_cart_action = None
    if sse_add_to_cart_intent:
        from history_product_cache import find_target_product_from_history
        from services.sku_selection_parser import parse_user_sku_selection
        target = find_target_product_from_history(session_id, sse_add_to_cart_intent)
        if target:
            product_title = target['product']['title']
            all_skus = target.get('skus', [])
            print(f"[SSE-AddCart] 找到目标商品 {product_title}, SKU总数 = {len(all_skus)}")

            sku_parse_result = parse_user_sku_selection(
                product_title=product_title,
                all_skus=all_skus,
                user_query=query
            )

            if sku_parse_result.status == "exact_one" and sku_parse_result.matched_sku:
                target_sku = sku_parse_result.matched_sku
                sku_reason = 'user_specified'
            elif all_skus:
                target_sku = all_skus[0]
                sku_reason = 'default_first_sku'
            else:
                target_sku = None
                sku_reason = 'no_sku_data'

            try:
                from cart_models import CartItemAdd
                item = CartItemAdd(
                    user_id=session_id,
                    product_id=target['product']['product_id'],
                    sku_id=target_sku['sku_id'] if target_sku else None,
                    title=product_title,
                    brand=target['product'].get('brand'),
                    image_path=target['product'].get('image_path'),
                    unit_price=target_sku['price'] if target_sku else target['product'].get('base_price', 0),
                    quantity=1
                )
                inserted_id = sqlite_client.add_cart_item(item.dict())
                sse_cart_action = {
                    'intent_detected': True,
                    'keyword': sse_add_to_cart_intent,
                    'product_id': target['product']['product_id'],
                    'title': product_title,
                    'added_to_cart': True,
                    'cart_item_id': inserted_id,
                    'sku_selection_reason': sku_reason,
                    'selected_sku': target_sku
                }
                if sku_parse_result.status == "multiple_options":
                    sse_cart_action['need_user_select_sku'] = True
                    sse_cart_action['candidate_skus'] = sku_parse_result.candidates
                    sse_cart_action['ask_user_msg'] = sku_parse_result.ask_user_msg
                    sse_cart_action['note'] = '已自动加入第一个SKU'
                print(f"[SSE-AddCart] 加购成功 cart_item_id={inserted_id}")
            except Exception as e:
                sse_cart_action = {
                    'intent_detected': True,
                    'keyword': sse_add_to_cart_intent,
                    'added_to_cart': False,
                    'error': str(e)
                }
                print(f"[SSE-AddCartError] {e}")
                import traceback
                traceback.print_exc()

    # 如果有加购动作，先推送 cart_action 事件给客户端
    if sse_cart_action:
        yield 'data: ' + json.dumps({'type': 'cart_action', 'cart_action': sse_cart_action}, ensure_ascii=False) + '\n\n'

    yield 'data: ' + json.dumps({'type': 'products', 'products': products_data}, ensure_ascii=False) + '\n\n'

    context_parts = []
    # 关键：把商品标题+品牌+价格+卖点拼成结构化context，确保LLM回答和卡片商品完全一致！
    # 鲁棒：item可能没有fragment字段（来自子品类兜底模式），用prod基本信息兜底
    for idx, item in enumerate(retrieved):
        prod = item.get('product', {})
        frag = item.get('fragment') or {
            'fragment_id': f"f_{prod.get('product_id', '')}",
            'content': f"{prod.get('title', '')} {prod.get('brand', '')} {prod.get('sub_category', '')}"
        }
        title = prod.get('title', '')
        brand = prod.get('brand', '')
        price = prod.get('base_price', '未知')
        sub_cat = prod.get('sub_category', '')
        content = (frag.get('content', '') or '')[:300]
        context_parts.append(
            f'【商品{idx+1}】\n'
            f'  - 标题: {title}\n'
            f'  - 品牌: {brand}\n'
            f'  - 价格: ¥{price}\n'
            f'  - 类别: {sub_cat}\n'
            f'  - 描述: {content}'
        )

    context_str = '\n\n'.join(context_parts)
    history_str = ''
    if req.history:
        for msg in req.history[-6:]:
            role = '用户' if msg.get('role') == 'user' else '助手'
            history_str += f'{role}: {msg.get("content", "")}\n'
    else:
        db_history = sqlite_client.get_chat_history(session_id, limit=6)
        for msg in db_history:
            role = '用户' if msg.get('role') == 'user' else '助手'
            history_str += f'{role}: {msg.get("content", "")}\n'

    sse_extra_hint = ''
    if sse_pure_compare_too_many:
        sse_extra_hint += '\n\n[系统消息] 用户要对比的商品数量超过了5个，请礼貌地建议用户减少商品数量，挑选不超过5款来进行高效清晰的对比.'
    if len(retrieved) == 0:
        sse_extra_hint += '\n\n[系统强制最高优先级提示] 现在检索结果为空列表！你绝对不能编造任何不存在的商品信息、标题、价格，你必须直接礼貌地告诉用户：目前在数据库中没有找到符合您要求的商品，请换个条件再试试。'

    system_prompt = f'''你是一个专业的电商智能导购助手。
请基于以下检索到的商品知识，为用户提供专业、友好的导购建议。
【绝对铁律】如果检索到的商品列表为空，100%禁止编造任何虚拟商品，直接如实告知用户没找到。

检索到的商品知识：
{context_str}

对话历史（用于理解上下文）：
{history_str}
{sse_extra_hint}

用户当前问题：{query}

请根据上述信息，给出自然流畅的导购回复，详细介绍推荐的商品卖点，帮助用户做出购买决策。'''

    full_reply = ''
    # SSE接口也生成结构化对比事件
    from structured_comparison import is_user_asking_for_comparison, generate_structured_comparison
    sse_comparison_table = None
    if is_user_asking_for_comparison(query) and len(retrieved) >= 2:
        sse_comparison_table = generate_structured_comparison(retrieved, query)
        yield 'data: ' + json.dumps({'type': 'comparison_table', 'comparison_table': sse_comparison_table}, ensure_ascii=False) + '\n\n'
    
    full_reply = ''
    try:
        for chunk in llm_service.chat_stream(system_prompt, query):
            full_reply += chunk
            yield 'data: ' + json.dumps({'type': 'content', 'delta': chunk}, ensure_ascii=False) + '\n\n'
            await asyncio.sleep(0.01)
        print(f'[SSE-LLM] 流式回复成功, 长度={len(full_reply)}')
    except Exception as e:
        import traceback
        print(f"[SSE-LLMError] {e}")
        traceback.print_exc()
        # 兜底：用商品信息流式生成回复
        fallback_lines = []
        for idx, item in enumerate(retrieved):
            p = item.get('product', {})
            fallback_lines.append(f'{idx+1}. {p.get("title", "")} - {p.get("brand", "")} - ¥{p.get("base_price", 0)}\n')
        err_msg = '抱歉,AI服务暂时无法使用,但已为您找到以下商品:\n\n'
        for c in err_msg:
            full_reply += c
            yield 'data: ' + json.dumps({'type': 'content', 'delta': c}, ensure_ascii=False) + '\n\n'
            await asyncio.sleep(0.01)
        for line in fallback_lines:
            for c in line:
                full_reply += c
                yield 'data: ' + json.dumps({'type': 'content', 'delta': c}, ensure_ascii=False) + '\n\n'
                await asyncio.sleep(0.01)

    sqlite_client.insert_chat_msg({
        'msg_id': str(uuid.uuid4()),
        'session_id': session_id,
        'role': 'user',
        'content': query
    })

    sqlite_client.insert_chat_msg({
        'msg_id': str(uuid.uuid4()),
        'session_id': session_id,
        'role': 'assistant',
        'content': full_reply
    })

    yield 'data: ' + json.dumps({'type': 'done', 'session_id': session_id}, ensure_ascii=False) + '\n\n'

@app.post('/api/v1/chat/stream')
async def chat_stream(req: ChatRequest):
    return StreamingResponse(
        stream_chat_response(req),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

from cart_models import CartItemAdd, CartItemUpdate
from cart_service import CartService
cart_service = CartService(settings.SQLITE_PATH)
@app.post('/api/v1/chat', response_model=dict)
async def chat(req: ChatRequest):
    # 全局异常兜底：不让任何意外导致500还不返回详情
    try:
        return await _do_chat(req)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        err_detail = f'{type(e).__name__}: {e}'
        print(f'[ChatError] {err_detail}')
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f'chat服务异常: {err_detail}')


async def _do_chat(req: ChatRequest):
    session_id = req.session_id if req.session_id else str(uuid.uuid4())
    query = req.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail='query cannot be empty')

    import re
    add_to_cart_intent = None
    _triggers = ['加购物车', '加入购物车', '加到购物车', '放进购物车', '加购']
    for _t in _triggers:
        _idx = query.find(_t)
        if _idx > 0:
            _kw = query[:_idx]
            _kw = re.sub(r'^(把|将|帮|要|请|麻烦你?|请帮我?)', '', _kw)
            _kw = re.sub(r'(也|就|啊|吧|呀)$', '', _kw)
            _kw = _kw.strip()
            if _kw:
                add_to_cart_intent = _kw
            break

    exclude_keywords = []
    for m in re.finditer(r'不要(.+?)(?:的|，|。|$)', query):
        exclude_keywords.append(m.group(1).strip())
    for m in re.finditer(r'除[了非](.+?)(?:还有什么|以外|都|，|。|$)', query):
        exclude_keywords.append(m.group(1).strip())
    for m in re.finditer(r'(.+?)以外(?:的)?', query):
        exclude_keywords.append(m.group(1).strip())

    # 纯对比词特殊处理：直接从历史缓存取上一轮推荐过的商品，完全跳过向量召回，杜绝无关商品！
    from history_product_cache import is_pure_compare_query, get_last_recommended_products_for_compare
    pure_compare_flag = False
    pure_compare_too_many = False
    retrieved = []
    if is_pure_compare_query(query):
        pure_compare_flag = True
        retrieved = get_last_recommended_products_for_compare(session_id)
        # 即使是从历史缓存取商品，也必须执行完整的 V2 智能过滤：反选 + 价格过滤！
        from filter_engine import smart_filter_products
        retrieved = smart_filter_products(retrieved, query, exclude_keywords, session_id)
        if len(retrieved) > 5:
            pure_compare_too_many = True
            retrieved = retrieved[:5]
        print(f"[PureCompare] 纯对比模式激活，过滤完成后剩余 {len(retrieved)} 个商品")
    else:
        # 非纯对比词，正常向量召回
        try:
            query_embedding = embedding_service.embed_text(query)
            retrieved = hybrid_retrieval_service.hybrid_search(query, query_embedding)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Embedding service不可用: {str(e)}. 请检查火山引擎API Key和端点配置.")

    # 接入全新V2过滤引擎：支持历史上下文继承
    from filter_engine import smart_filter_products
    retrieved = smart_filter_products(retrieved, query, exclude_keywords, session_id)

    seen_pids = set()
    deduped = []
    for item in retrieved:
        pid = item['product'].get('product_id', '')
        if pid and pid not in seen_pids:
            seen_pids.add(pid)
            deduped.append(item)
    retrieved = deduped
    retrieved.sort(key=lambda x: x.get('score', 0.0), reverse=True)

    target_cat = detect_target_category(query)
    print(f'[Chat CategoryDetect] query="{query}" -> target_category="{target_cat}"')
    retrieved = filter_by_category(retrieved, target_cat)
    # 用户没指定数量时，默认返回5个商品
    retrieved = retrieved[:5]
    print(f'[Chat Final] total {len(retrieved)} relevant products (category filtered)')

    cart_action = None
    from history_product_cache import save_products_to_cache, find_target_product_from_history
    from services.sku_selection_parser import parse_user_sku_selection
    # 先把当前这轮要返回给用户的商品保存到历史缓存
    product_list_for_cache = []
    for item in retrieved:
        product_list_for_cache.append({
            "product": item['product'],
            "skus": item.get('skus', [])
        })
    save_products_to_cache(session_id, product_list_for_cache)
    
    if add_to_cart_intent:
        target = find_target_product_from_history(session_id, add_to_cart_intent)
        if target:
            product_title = target['product']['title']
            all_skus = target.get('skus', [])
            print(f"[AddCart] 找到目标商品, SKU总数 = {len(all_skus)}")

            sku_parse_result = parse_user_sku_selection(
                product_title=product_title,
                all_skus=all_skus,
                user_query=query
            )

            cart_action = {
                'intent_detected': True,
                'keyword': add_to_cart_intent,
                'product_id': target['product']['product_id'],
                'title': product_title,
                'added_to_cart': False,
                'sku_parse_status': sku_parse_result.status
            }

            # 决定要加入的SKU：
            # 1. 精确唯一匹配 -> 用户指定的SKU
            # 2. 多SKU但用户没指定 -> 默认取第一个SKU，确保加购流程不会卡住
            # 3. 整个商品没有SKU数据 -> 用商品基础价格作为unit_price，sku_id为None
            if sku_parse_result.status == "exact_one" and sku_parse_result.matched_sku:
                target_sku = sku_parse_result.matched_sku
                cart_action['sku_selection_reason'] = 'user_specified'
            elif all_skus:
                target_sku = all_skus[0]
                cart_action['sku_selection_reason'] = 'default_first_sku'
            else:
                target_sku = None
                cart_action['sku_selection_reason'] = 'no_sku_data_use_base_price'

            # 关键：用全局的 sqlite_client 单例，避免双实例双数据库
            try:
                sqlite_client_for_cart = sqlite_client
                # 用绝对路径import，避开sys.path问题
                import importlib.util
                spec = importlib.util.spec_from_file_location("cart_models", "d:/RAG导购/cart_models.py")
                cart_models_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(cart_models_module)
                CartItemAdd = cart_models_module.CartItemAdd
                item = CartItemAdd(
                    user_id=session_id,
                    product_id=target['product']['product_id'],
                    sku_id=target_sku['sku_id'] if target_sku else None,
                    title=product_title,
                    brand=target['product'].get('brand'),
                    image_path=target['product'].get('image_path'),
                    unit_price=target_sku['price'] if target_sku else target['product'].get('base_price', 0),
                    quantity=1
                )
                inserted_id = sqlite_client_for_cart.add_cart_item(item.dict())
                cart_action['added_to_cart'] = True
                cart_action['cart_item_id'] = inserted_id
                cart_action['selected_sku'] = target_sku
                # 把商品卡片追加到返回结果里展示
                retrieved.append(target)
                print(f"[AddCart] 加购成功！cart_item_id = {inserted_id}, sku = {target_sku.get('sku_id') if target_sku else 'None'}")
            except Exception as e:
                cart_action['error'] = str(e)
                cart_action['added_to_cart'] = False
                print(f"[AddCartError] 加购失败: {e}")
                import traceback
                traceback.print_exc()
            # 如果是多SKU未明确指定，仍然把选项告诉用户，方便他精确指定
            if sku_parse_result.status == "multiple_options":
                cart_action['need_user_select_sku'] = True
                cart_action['candidate_skus'] = sku_parse_result.candidates
                cart_action['ask_user_msg'] = sku_parse_result.ask_user_msg
                cart_action['note'] = '已自动加入第一个SKU，您可以从下列规格中修改为其他款式'

    context_parts = []
    # 关键：把商品标题+品牌+价格+卖点拼成结构化context，确保LLM回答和卡片商品完全一致！
    # 鲁棒：item可能没有fragment字段（来自子品类兜底模式），用prod基本信息兜底
    for idx, item in enumerate(retrieved):
        prod = item.get('product', {})
        frag = item.get('fragment') or {
            'fragment_id': f"f_{prod.get('product_id', '')}",
            'content': f"{prod.get('title', '')} {prod.get('brand', '')} {prod.get('sub_category', '')}"
        }
        title = prod.get('title', '')
        brand = prod.get('brand', '')
        price = prod.get('base_price', '未知')
        sub_cat = prod.get('sub_category', '')
        content = (frag.get('content', '') or '')[:300]
        context_parts.append(
            f'【商品{idx+1}】\n'
            f'  - 标题: {title}\n'
            f'  - 品牌: {brand}\n'
            f'  - 价格: ¥{price}\n'
            f'  - 类别: {sub_cat}\n'
            f'  - 描述: {content}'
        )

    context_str = '\n\n'.join(context_parts)
    history_str = ''
    if req.history:
        for msg in req.history[-6:]:
            role = '用户' if msg.get('role') == 'user' else '助手'
            history_str += f'{role}: {msg.get("content", "")}\n'
    else:
        db_history = sqlite_client.get_chat_history(session_id, limit=6)
        for msg in db_history:
            role = '用户' if msg.get('role') == 'user' else '助手'
            history_str += f'{role}: {msg.get("content", "")}\n'

    extra_hint = ''
    if cart_action and cart_action.get('added_to_cart'):
        extra_hint += f'\n\n[系统消息] 用户刚说"{query}"，你已经把"{cart_action["title"]}"加入了用户的购物车，请在回复中确认此操作.'
    if exclude_keywords:
        extra_hint += f'\n\n[系统消息] 用户明确排除了这些特征/品牌/类型: {exclude_keywords}. 请确保推荐的商品不包含这些特征.'
    if pure_compare_too_many:
        extra_hint += '\n\n[系统消息] 用户要对比的商品数量超过了5个，请礼貌地建议用户减少商品数量，挑选不超过5款来进行高效清晰的对比.'

    system_prompt = f'''你是一个专业的电商智能导购助手。
请基于下列候选商品库为用户导购。
回答要自然、专业、简洁。

【候选商品库】（共 {len(retrieved)} 件）：
{context_str}

【对话历史】（用于理解上下文）：
{history_str}
{extra_hint}

【用户当前问题】：{query}

请根据上述信息，给出自然流畅的导购回复，详细介绍推荐的商品卖点，帮助用户做出购买决策.'''

    # LLM调用 - 完整异常保护，绝不让401错误让进程退出
    ai_reply = ''
    try:
        ai_reply = llm_service.chat(system_prompt, query)
        print(f'[LLM] 回复成功, 长度={len(ai_reply)}')
    except Exception as e:
        import traceback
        print(f"[LLMError] LLM调用失败: {e}")
        traceback.print_exc()
        # 兜底：用商品信息生成回复
        fallback_lines = []
        for idx, item in enumerate(retrieved):
            p = item.get('product', {})
            fallback_lines.append(f'{idx+1}. {p.get("title", "")} - {p.get("brand", "")} - ¥{p.get("base_price", 0)}')
        ai_reply = '抱歉,AI服务暂时无法使用,但我已为您找到以下符合条件的商品:\n\n' + '\n'.join(fallback_lines)

    sqlite_client.insert_chat_msg({
        'msg_id': str(uuid.uuid4()),
        'session_id': session_id,
        'role': 'user',
        'content': query
    })

    sqlite_client.insert_chat_msg({
        'msg_id': str(uuid.uuid4()),
        'session_id': session_id,
        'role': 'assistant',
        'content': ai_reply
    })

    product_list = []
    for item in retrieved:
        product_list.append({
            'product': item['product'],
            'skus': item['skus']
        })

    # 检测用户是否要对比商品，如果是，生成结构化对比数据返回
    structured_comparison = None
    from structured_comparison import is_user_asking_for_comparison, generate_structured_comparison
    if is_user_asking_for_comparison(query) and len(retrieved) >= 2:
        structured_comparison = generate_structured_comparison(retrieved, query)
    
    current_history = sqlite_client.get_chat_history(session_id, limit=10)
    current_history_formatted = [{'role': msg['role'], 'content': msg['content']} for msg in current_history]

    return {
        'ai_reply': ai_reply,
        'products': product_list,
        'session_id': session_id,
        'history': current_history_formatted,
        'cart_action': cart_action,
        'exclude_keywords': exclude_keywords,
        'structured_comparison': structured_comparison
    }

@app.post('/api/v1/search')
async def search(req: SearchRequest):
    query = req.query.strip()
    try:
        query_embedding = embedding_service.embed_text(query)
        retrieved = hybrid_retrieval_service.hybrid_search(query, query_embedding)
        seen = set()
        out = []
        for x in retrieved:
            pid = x['product'].get('product_id', '')
            if pid and pid not in seen:
                seen.add(pid)
                out.append(x)
        out.sort(key=lambda x: x.get('score', 0.0), reverse=True)
        target_cat = detect_target_category(query)
        out = filter_by_category(out, target_cat)
        out = out[:6]
        return {'results': out}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Embedding服务不可用: {str(e)}. 请检查火山引擎API Key和端点配置.")

@app.get('/api/v1/product/{product_id}')
async def get_product(product_id: str):
    prod = sqlite_client.get_product_by_id(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail='product not found')
    skus = sqlite_client.get_skus_by_product_id(product_id)
    return {'product': prod, 'skus': skus}

@app.post('/api/v1/search/image')
async def search_by_image(
    image: UploadFile = File(...),
    query = None
):
    try:
        filename = image.filename or 'test.jpg'
        filename_lower = filename.lower()
        all_products = sqlite_client.get_all_products()
        target_category = '美妆护肤'
        if any(key in filename_lower for key in ['digital', 'switch', 'phone', 'laptop', '数码', '电子']):
            target_category = '数码电子'
        elif any(key in filename_lower for key in ['clothes', 'sport', 'tshirt', '运动', '服饰']):
            target_category = '服饰运动'
        elif any(key in filename_lower for key in ['food', 'coffee', 'milk', '咖啡', '牛奶', '零食', '食品', '饮料']):
            target_category = '食品饮料'
        category_products = [p for p in all_products if p.get('category') == target_category]
        random.shuffle(category_products)
        results = []
        for idx in range(min(6, len(category_products))):
            prod = category_products[idx]
            product_id = prod['product_id']
            skus = sqlite_client.get_skus_by_product_id(product_id)
            results.append({
                'fragment_id': f'{product_id}_image_001',
                'score': 1.0 - (idx * 0.05),
                'product': prod,
                'skus': skus
            })
        return {'results': results, 'image_filename': filename, 'query_text': query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Image search failed: {str(e)}')

# ==================== 登录注册 ====================

class LoginRegisterRequest(BaseModel):
    username: str
    password: str
    nickname: Optional[str] = None


def get_current_user_id(authorization: Optional[str] = Header(None, alias="Authorization")) -> str:
    """从Authorization: Bearer <token> 头中解析user_id，未登录返回401"""
    if not authorization:
        raise HTTPException(status_code=401, detail='未登录：请先调用 /api/v1/auth/login')
    token = authorization.replace("Bearer ", "").strip()
    auth = get_auth_manager()
    info = auth.verify_token(token)
    if not info:
        raise HTTPException(status_code=401, detail='Token无效或已过期')
    return str(info["user_id"])


@app.post('/api/v1/auth/register')
async def auth_register(req: LoginRegisterRequest):
    """注册新用户，注册成功自动登录返回token"""
    auth = get_auth_manager()
    result = auth.register(req.username, req.password, req.nickname)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "注册失败"))
    return result


@app.post('/api/v1/auth/login')
async def auth_login(req: LoginRegisterRequest):
    """登录获取token"""
    auth = get_auth_manager()
    result = auth.login(req.username, req.password)
    if not result.get("ok"):
        raise HTTPException(status_code=401, detail=result.get("error", "登录失败"))
    return result


@app.post('/api/v1/auth/logout')
async def auth_logout(authorization: Optional[str] = Header(None, alias="Authorization")):
    """登出"""
    if not authorization:
        return {"ok": True}
    token = authorization.replace("Bearer ", "").strip()
    get_auth_manager().logout(token)
    return {"ok": True}


@app.get('/api/v1/auth/me')
async def auth_me(authorization: Optional[str] = Header(None, alias="Authorization")):
    """查询当前登录用户信息"""
    user_id = get_current_user_id(authorization)
    return {"user_id": user_id, "ok": True}


# ==================== 购物车（必须登录） ====================

@app.post('/api/v1/cart')
async def add_to_cart(item: CartItemAdd, authorization: Optional[str] = Header(None, alias="Authorization")):
    # 鉴权：从Authorization Bearer Token中获取user_id
    current_user = get_current_user_id(authorization)
    # 强制以token解析出的user_id为准，防止请求体伪造
    item.user_id = current_user
    try:
        inserted_id = sqlite_client.add_cart_item(item.dict())
        return {'success': True, 'cart_item_id': inserted_id, 'user_id': current_user}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'加购失败: {str(e)}')

# 注册一个绝对路径的兜底导入
import importlib.util
_cart_models_spec = importlib.util.spec_from_file_location("cart_models", "d:/RAG导购/cart_models.py")
_cart_models_module = importlib.util.module_from_spec(_cart_models_spec)
_cart_models_spec.loader.exec_module(_cart_models_module)
CartItemAdd = _cart_models_module.CartItemAdd
CartItemUpdate = _cart_models_module.CartItemUpdate

@app.get('/api/v1/cart')
async def get_cart(authorization: Optional[str] = Header(None, alias="Authorization")):
    # 鉴权：只允许从token解析user_id，禁止query参数越权
    current_user = get_current_user_id(authorization)
    try:
        items = sqlite_client.get_cart_items(current_user)
        total_count = sum(i.get('quantity', 0) for i in items)
        total_amount = round(sum(i.get('subtotal', 0) for i in items), 2)
        return {
            'user_id': current_user,
            'items': items,
            'total_count': total_count,
            'total_amount': total_amount
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'查询购物车失败: {str(e)}')

@app.put('/api/v1/cart/{item_id}')
async def update_cart_item(item_id: int, update: CartItemUpdate, authorization: Optional[str] = Header(None, alias="Authorization")):
    # 鉴权：必须登录
    current_user = get_current_user_id(authorization)
    try:
        # 关键：先校验这个item_id是否属于当前用户
        cart_items = sqlite_client.get_cart_items(current_user)
        target = next((it for it in cart_items if it.get('id') == item_id), None)
        if not target:
            raise HTTPException(status_code=403, detail='无权限：此购物车项不属于您')
        ok = sqlite_client.update_cart_quantity(item_id, update.quantity)
        if not ok:
            raise HTTPException(status_code=404, detail='item not found or invalid quantity')
        return {'success': True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'修改失败: {str(e)}')

@app.delete('/api/v1/cart/{item_id}')
async def remove_cart_item(item_id: int, authorization: Optional[str] = Header(None, alias="Authorization")):
    current_user = get_current_user_id(authorization)
    try:
        # 权限校验
        cart_items = sqlite_client.get_cart_items(current_user)
        target = next((it for it in cart_items if it.get('id') == item_id), None)
        if not target:
            raise HTTPException(status_code=403, detail='无权限：此购物车项不属于您')
        ok = sqlite_client.remove_cart_item(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail='item not found')
        return {'success': True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'删除失败: {str(e)}')

@app.delete('/api/v1/cart')
async def clear_cart(authorization: Optional[str] = Header(None, alias="Authorization")):
    # 鉴权：只清空当前登录用户的购物车
    current_user = get_current_user_id(authorization)
    try:
        cleared = sqlite_client.clear_cart(current_user)
        return {'success': True, 'cleared': cleared, 'user_id': current_user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'清空失败: {str(e)}')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)

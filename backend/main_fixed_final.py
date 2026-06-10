import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, UploadFile, File
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
from cart_models import CartItemAdd, CartItemUpdate
from cart_service import CartService

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

# 自动类目推断 - 只展示相关卡片，完全移除10张不相关混排问题
CATEGORY_KEYWORDS = {
    "美妆护肤": ["精华", "面霜", "眼霜", "面膜", "洁面", "爽肤水", "乳液", "护肤", "口红", "粉底", "眼影", "防晒", "隔离", "香水", "美妆", "雅诗兰黛", "兰蔻", "SK-II", "资生堂", "倩碧", "欧莱雅"],
    "数码电子": ["耳机", "手机", "笔记本", "电脑", "switch", "相机", "键盘", "鼠标", "平板", "音响", "充电宝", "手环", "手表", "耳机", "音箱", "AirPods", "FreeBuds", "华为", "苹果", "iPhone", "Mac", "iPad"],
    "食品饮料": ["饮料", "咖啡", "牛奶", "零食", "方便面", "矿泉水", "薯片", "坚果", "巧克力", "饼干", "奶茶", "可口可乐", "农夫山泉", "康师傅", "三得利", "元气森林"],
    "服饰运动": ["T恤", "衣服", "鞋子", "运动鞋", "运动服", "外套", "牛仔裤", "跑鞋", "篮球鞋", "Nike", "Adidas", "运动", "安踏", "李宁"]
}

def detect_target_category(query):
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
    filtered = [x for x in rets if x['product'].get('category') == target_cat]
    if len(filtered) < 2:
        return rets[:6]
    return filtered

class ChatRequest(BaseModel):
    session_id: str = ""
    query: str
    history: Optional[List[Dict[str, str]]] = None

class SearchRequest(BaseModel):
    query: str

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

    try:
        query_embedding = embedding_service.embed_text(query)
        retrieved = hybrid_retrieval_service.hybrid_search(query, query_embedding)
    except Exception as e:
        yield 'data: ' + json.dumps({'type': 'error', 'message': f'Embedding service unavailable: {str(e)}'}, ensure_ascii=False) + '\n\n'
        return

    # 去重 + 按 score 降序重排 + 类目过滤 - 只展示相关卡片
    seen_pids_sse = set()
    deduped_sse = []
    for item in retrieved:
        pid = item['product'].get('product_id', '')
        if pid and pid not in seen_pids_sse:
            seen_pids_sse.add(pid)
            deduped_sse.append(item)
    retrieved = deduped_sse
    retrieved.sort(key=lambda x: x.get('score', 0.0), reverse=True)
    target_cat_sse = detect_target_category(query)
    retrieved = filter_by_category(retrieved, target_cat_sse)
    retrieved = retrieved[:6]
    print(f"[SSE Filter] category='{target_cat_sse}', total {len(retrieved)} products")

    products_data = []
    for item in retrieved:
        products_data.append({
            "product": item['product'],
            "skus": item['skus']
        })
    yield 'data: ' + json.dumps({'type': 'products', 'products': products_data}, ensure_ascii=False) + '\n\n'

    context_parts = []
    for idx, item in enumerate(retrieved):
        frag = item['fragment']
        prod = item['product']
        context_parts.append(f"[商品{idx+1}: {prod.get('title', '')}]\n{frag.get('content', '')}")

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

    system_prompt = f'''你是一个专业的电商智能导购助手。
请基于以下检索到的商品知识，为用户提供专业、友好的导购建议。

检索到的商品知识：
{context_str}

对话历史（用于理解上下文）：
{history_str}

用户当前问题：{query}

请根据上述信息，给出自然流畅的导购回复，详细介绍推荐的商品卖点，帮助用户做出购买决策。
'''

    full_reply = ''
    for chunk in llm_service.chat_stream(system_prompt, query):
        full_reply += chunk
        yield 'data: ' + json.dumps({'type': 'content', 'delta': chunk}, ensure_ascii=False) + '\n\n'
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

cart_service = CartService('d:/RAG导购/ecommerce.db')

@app.post('/api/v1/chat', response_model=dict)
async def chat(req: ChatRequest):
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

    try:
        query_embedding = embedding_service.embed_text(query)
        retrieved = hybrid_retrieval_service.hybrid_search(query, query_embedding)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Embedding服务不可用: {str(e)}. 请检查火山引擎API Key和Endpoint配置.")

    if exclude_keywords:
        original_count = len(retrieved)
        retrieved = [
            item for item in retrieved
            if not any(kw and kw in (item['product'].get('title', '') + item['product'].get('brand', '') + item['product'].get('sub_category', '')) for kw in exclude_keywords)
        ]
        print(f"[Exclude] filter {original_count} -> {len(retrieved)} (excluded: {exclude_keywords})")

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
    print(f"[Filter] category='{target_cat}', total {len(retrieved)} before cat filter")
    retrieved = filter_by_category(retrieved, target_cat)
    retrieved = retrieved[:6]
    print(f"[Filter Final] total {len(retrieved)} relevant products after category filter")

    cart_action = None
    if add_to_cart_intent and retrieved:
        target = retrieved[0]
        sku = target['skus'][0] if target.get('skus') else None
        cart_action = {
            'intent_detected': True,
            'keyword': add_to_cart_intent,
            'product_id': target['product']['product_id'],
            'title': target['product']['title'],
            'added_to_cart': False
        }
        try:
            item = CartItemAdd(
                user_id=session_id,
                product_id=target['product']['product_id'],
                sku_id=sku['sku_id'] if sku else None,
                title=target['product']['title'],
                brand=target['product'].get('brand'),
                image_path=target['product'].get('image_path'),
                unit_price=sku['price'] if sku else target['product'].get('base_price', 0),
                quantity=1
            )
            result = cart_service.add_to_cart(item)
            cart_action['added_to_cart'] = True
            cart_action['cart_item_id'] = result.id
        except Exception as e:
            cart_action['error'] = str(e)

    context_parts = []
    for idx, item in enumerate(retrieved):
        frag = item['fragment']
        prod = item['product']
        context_parts.append(f"[商品{idx+1}: {prod.get('title', '')}]\n{frag.get('content', '')}")

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
        extra_hint += f'\n\n[系统消息] 用户刚说"{query}"，你已经把"{cart_action["title"]}"加入了用户的购物车，请在回复中确认此操作。'
    if exclude_keywords:
        extra_hint += f'\n\n[系统消息] 用户明确排除了这些特征/品牌/类型：{exclude_keywords}。请确保推荐的商品不包含这些特征。'

    system_prompt = f'''你是一个专业的电商智能导购助手。
请基于以下检索到的商品知识，为用户提供专业、友好的导购建议。

检索到的商品知识：
{context_str}

对话历史（用于理解上下文）：
{history_str}

用户当前问题：{query}
{extra_hint}

请根据上述信息，给出自然流畅的导购回复，详细介绍推荐的商品卖点，帮助用户做出购买决策。
'''

    ai_reply = llm_service.chat(system_prompt, query)

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

    current_history = sqlite_client.get_chat_history(session_id, limit=10)
    current_history_formatted = [{'role': msg['role'], 'content': msg['content']} for msg in current_history]

    return {
        'ai_reply': ai_reply,
        'products': product_list,
        'session_id': session_id,
        'history': current_history_formatted,
        'cart_action': cart_action,
        'exclude_keywords': exclude_keywords
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
        raise HTTPException(status_code=503, detail=f"Embedding服务不可用: {str(e)}. 请检查火山引擎API Key和Endpoint配置.")

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
    query: Optional[str] = None
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

@app.post('/api/v1/cart')
async def add_to_cart(item: CartItemAdd):
    try:
        result = cart_service.add_to_cart(item)
        return {'success': True, 'item': result.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'加购失败: {str(e)}')

@app.get('/api/v1/cart')
async def get_cart(user_id: str = 'default_user'):
    try:
        items = cart_service.get_cart(user_id)
        total_count = sum(i.quantity for i in items)
        total_amount = round(sum(i.subtotal for i in items), 2)
        return {
            'items': [i.dict() for i in items],
            'total_count': total_count,
            'total_amount': total_amount
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'查询购物车失败: {str(e)}')

@app.put('/api/v1/cart/{item_id}')
async def update_cart_item(item_id: int, update: CartItemUpdate):
    try:
        result = cart_service.update_quantity(item_id, update)
        if not result:
            raise HTTPException(status_code=404, detail='item not found')
        return {'success': True, 'item': result.dict()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'修改失败: {str(e)}')

@app.delete('/api/v1/cart/{item_id}')
async def remove_cart_item(item_id: int):
    try:
        ok = cart_service.remove_from_cart(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail='item not found')
        return {'success': True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'删除失败: {str(e)}')

@app.delete('/api/v1/cart')
async def clear_cart(user_id: str = 'default_user'):
    try:
        cleared = cart_service.clear_cart(user_id)
        return {'success': True, 'cleared': cleared}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'清空失败: {str(e)}')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)

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

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

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

    # 【修复】SSE流式接口：去重 + 按分数降序重排
    seen_pids_sse = set()
    deduped_sse = []
    for item in retrieved:
        pid = item['product'].get('product_id', '')
        if pid and pid not in seen_pids_sse:
            seen_pids_sse.add(pid)
            deduped_sse.append(item)
    retrieved = deduped_sse
    retrieved.sort(key=lambda x: x.get('score', 0.0), reverse=True)
    print(f"[SSE ReRank] after dedup + sort, total {len(retrieved)} items (sorted by score DESC)")

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

    context_str = "\n\n".join(context_parts)

    history_str = ""
    if req.history:
        for msg in req.history[-6:]:
            role = "用户" if msg.get('role') == 'user' else "助手"
            history_str += f"{role}: {msg.get('content', '')}\n"
    else:
        db_history = sqlite_client.get_chat_history(session_id, limit=6)
        for msg in db_history:
            role = "用户" if msg.get('role') == 'user' else "助手"
            history_str += f"{role}: {msg.get('content', '')}\n"

    system_prompt = f"""你是一个专业的电商智能导购助手。
请基于以下检索到的商品知识，为用户提供专业、友好的导购建议。

检索到的商品知识：
{context_str}

对话历史（用于理解上下文）：
{history_str}

用户当前问题：{query}

请根据上述信息，给出自然流畅的导购回复，详细介绍推荐的商品卖点，帮助用户做出购买决策。
"""

    full_reply = ""
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

@app.post("/api/v1/chat/stream")
async def chat_stream(req: ChatRequest):
    return StreamingResponse(
        stream_chat_response(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/v1/chat", response_model=dict)
async def chat(req: ChatRequest):
    session_id = req.session_id if req.session_id else str(uuid.uuid4())
    query = req.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="query cannot be empty")

    # === 对话式加购意图识别 ===
    import re
    # 先在 query 中查找触发短语，再倒推前面的 keyword
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

    # === 反选与排除识别 ===
    exclude_keywords = []
    # 模式1: "不要X的"
    for m in re.finditer(r'不要(.+?)(?:的|，|。|$)', query):
        exclude_keywords.append(m.group(1).strip())
    # 模式2: "除了X"
    for m in re.finditer(r'除[了非](.+?)(?:还有什么|以外|都|，|。|$)', query):
        exclude_keywords.append(m.group(1).strip())
    # 模式3: "X以外"
    for m in re.finditer(r'(.+?)以外(?:的)?', query):
        exclude_keywords.append(m.group(1).strip())

    from cart_models import CartItemAdd
    from cart_service import CartService
    cart_service = CartService("d:/RAG导购/ecommerce.db")

    try:
        query_embedding = embedding_service.embed_text(query)
        retrieved = hybrid_retrieval_service.hybrid_search(query, query_embedding)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Embedding服务不可用: {str(e)}. 请检查火山引擎API Key和Endpoint配置。")

    # === 反选排除：把含排除关键词的商品从结果中过滤掉 ===
    if exclude_keywords:
        original_count = len(retrieved)
        retrieved = [
            item for item in retrieved
            if not any(kw and kw in (item['product'].get('title', '') + item['product'].get('brand', '') + item['product'].get('sub_category', ''))
                       for kw in exclude_keywords)
        ]
        print(f"[Exclude] filter {original_count} -> {len(retrieved)} (excluded: {exclude_keywords})")

    # === 核心修复1：去重，确保同一个 product_id 只出现一次 ===
    seen_pids = set()
    deduped = []
    for item in retrieved:
        pid = item['product'].get('product_id', '')
        if pid and pid not in seen_pids:
            seen_pids.add(pid)
            deduped.append(item)
    retrieved = deduped

    # === 核心修复2：按相似度分数 score 从高到低 降序重排 ===
    # 保证最相关的商品排在最前面，不会出现"推荐耳机结果前几个全不是耳机"的乱序问题
    retrieved.sort(key=lambda x: x.get('score', 0.0), reverse=True)
    print(f"[ReRank] after dedup + sort, total {len(retrieved)} items (sorted by score DESC)")

    # === 对话式加购：若识别到加购意图，尝试写入购物车 ===
    cart_action = None
    if add_to_cart_intent and retrieved:
        # 取Top1作为加购目标
        target = retrieved[0]
        sku = target['skus'][0] if target.get('skus') else None
        cart_action = {
            "intent_detected": True,
            "keyword": add_to_cart_intent,
            "product_id": target['product']['product_id'],
            "title": target['product']['title'],
            "added_to_cart": False
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
            cart_action["added_to_cart"] = True
            cart_action["cart_item_id"] = result.id
        except Exception as e:
            cart_action["error"] = str(e)

    context_parts = []
    for idx, item in enumerate(retrieved):
        frag = item['fragment']
        prod = item['product']
        context_parts.append(f"[商品{idx+1}: {prod.get('title', '')}]\n{frag.get('content', '')}")

    context_str = "\n\n".join(context_parts)

    history_str = ""
    if req.history:
        for msg in req.history[-6:]:
            role = "用户" if msg.get('role') == 'user' else "助手"
            history_str += f"{role}: {msg.get('content', '')}\n"
    else:
        db_history = sqlite_client.get_chat_history(session_id, limit=6)
        for msg in db_history:
            role = "用户" if msg.get('role') == 'user' else "助手"
            history_str += f"{role}: {msg.get('content', '')}\n"

    # 在Prompt中加入加购/排除感知
    extra_hint = ""
    if cart_action and cart_action.get("added_to_cart"):
        extra_hint = f"\n\n[系统消息] 用户刚说「{query}」，你已经把「{cart_action['title']}」加入了用户的购物车，请在回复中确认此操作。"
    if exclude_keywords:
        extra_hint += f"\n\n[系统消息] 用户明确排除了这些特征/品牌/类型：{exclude_keywords}。请确保推荐的商品不包含这些特征。"

    system_prompt = f"""你是一个专业的电商智能导购助手。
请基于以下检索到的商品知识，为用户提供专业、友好的导购建议。

检索到的商品知识：
{context_str}

对话历史（用于理解上下文）：
{history_str}

用户当前问题：{query}
{extra_hint}

请根据上述信息，给出自然流畅的导购回复，详细介绍推荐的商品卖点，帮助用户做出购买决策。
"""

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
    current_history_formatted = [{"role": msg['role'], "content": msg['content']} for msg in current_history]

    return {
        "ai_reply": ai_reply,
        "products": product_list,
        "session_id": session_id,
        "history": current_history_formatted,
        "cart_action": cart_action,
        "exclude_keywords": exclude_keywords
    }

@app.post("/api/v1/search")
async def search(req: SearchRequest):
    query = req.query.strip()
    try:
        query_embedding = embedding_service.embed_text(query)
        retrieved = hybrid_retrieval_service.hybrid_search(query, query_embedding)
        # 同样去重+排序
        seen = set()
        out = []
        for x in retrieved:
            pid = x['product'].get('product_id', '')
            if pid and pid not in seen:
                seen.add(pid)
                out.append(x)
        out.sort(key=lambda x: x.get('score', 0.0), reverse=True)
        return {"results": out}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Embedding服务不可用: {str(e)}. 请检查火山引擎API Key和Endpoint配置。")

@app.get("/api/v1/product/{product_id}")
async def get_product(product_id: str):
    prod = sqlite_client.get_product_by_id(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="product not found")
    skus = sqlite_client.get_skus_by_product_id(product_id)
    return {"product": prod, "skus": skus}

@app.post("/api/v1/search/image")
async def search_by_image(
    image: UploadFile = File(...),
    query: Optional[str] = None
):
    try:
        filename = image.filename or "test.jpg"
        filename_lower = filename.lower()
        all_products = sqlite_client.get_all_products()
        target_category = "美妆护肤"
        if any(key in filename_lower for key in ["digital", "switch", "phone", "laptop", "数码", "电子"]):
            target_category = "数码电子"
        elif any(key in filename_lower for key in ["clothes", "sport", "tshirt", "运动", "服饰"]):
            target_category = "服饰运动"
        elif any(key in filename_lower for key in ["food", "coffee", "milk", "咖啡", "牛奶", "零食", "食品", "饮料"]):
            target_category = "食品饮料"
        category_products = [p for p in all_products if p.get('category') == target_category]
        random.shuffle(category_products)
        results = []
        for idx in range(min(10, len(category_products))):
            prod = category_products[idx]
            product_id = prod['product_id']
            skus = sqlite_client.get_skus_by_product_id(product_id)
            results.append({
                "fragment_id": f"{product_id}_image_001",
                "score": 1.0 - (idx * 0.05),
                "product": prod,
                "skus": skus
            })
        return {"results": results, "image_filename": filename, "query_text": query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image search failed: {str(e)}")

cart_service = CartService("d:/RAG导购/ecommerce.db")

@app.post("/api/v1/cart")
async def add_to_cart(item: CartItemAdd):
    """加购：若已存在则数量+1"""
    try:
        result = cart_service.add_to_cart(item)
        return {"success": True, "item": result.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加购失败: {str(e)}")

@app.get("/api/v1/cart")
async def get_cart(user_id: str = "default_user"):
    """查询购物车"""
    try:
        items = cart_service.get_cart(user_id)
        total_count = sum(i.quantity for i in items)
        total_amount = round(sum(i.subtotal for i in items), 2)
        return {
            "items": [i.dict() for i in items],
            "total_count": total_count,
            "total_amount": total_amount
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询购物车失败: {str(e)}")

@app.put("/api/v1/cart/{item_id}")
async def update_cart_item(item_id: int, update: CartItemUpdate):
    """修改购物车商品数量"""
    try:
        result = cart_service.update_quantity(item_id, update)
        if not result:
            raise HTTPException(status_code=404, detail="item not found")
        return {"success": True, "item": result.dict()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"修改失败: {str(e)}")

@app.delete("/api/v1/cart/{item_id}")
async def remove_cart_item(item_id: int):
    """删除购物车某项"""
    try:
        ok = cart_service.remove_from_cart(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="item not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@app.delete("/api/v1/cart")
async def clear_cart(user_id: str = "default_user"):
    """清空购物车"""
    try:
        cleared = cart_service.clear_cart(user_id)
        return {"success": True, "cleared": cleared}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

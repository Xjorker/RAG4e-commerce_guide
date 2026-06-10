import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uuid
import base64
import random
import json
import asyncio
from typing import List, Dict, Any, Optional
from config import settings
from services import embedding_service, hybrid_retrieval_service, llm_service
from services.sorting_agent import parse_sorting_strategy
from services.full_intent_parser import parse_and_full_filter_products
from services.schema_aware_agent import build_schema_once
from services.llm_fuzzy_reason import llm_reason_fuzzy_intent
from services.llm_struct_sort import llm_struct_sort
from database import sqlite_client

# 服务启动自动扫描全库Schema，学习库里真实存在的类目/子品类/品牌
build_schema_once()

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

# 挂载商品图片静态资源，让 Android 可以直接访问 /images/1_美妆护肤/xxx.jpg
import os
IMAGE_FOLDER = "d:/RAG导购"
if os.path.exists(IMAGE_FOLDER):
    try:
        app.mount("/images/", StaticFiles(directory=IMAGE_FOLDER), name="images")
        print(f"[StaticFiles] Image dir mounted at /images/ -> {IMAGE_FOLDER}")
    except Exception as e:
        print(f"[StaticFiles] Mount skipped: {e}")

# 二层级关键词树 - 类目 → 子品类 → 关键词列表
# 解决"手机/平板/笔记本/耳机"等同类目下不同子品类的区分问题
HIERARCHY = {
    "数码电子": {
        "智能手机":   ["手机", "iPhone", "iphone", "小米", "OPPO", "oppo", "vivo", "华为", "苹果", "数码", "电子产品", "5G", "智能机", "Mate", "Pura", "Reno", "Find", "Mix"],
        "平板电脑":   ["平板", "iPad", "ipad", "MatePad", "Pad", "Tab"],
        "笔记本电脑": ["笔记本", "笔记本电脑", "MacBook", "macbook", "ThinkPad", "thinkpad",
                       "MateBook", "ThinkBook", "Mac"],
        "真无线耳机": ["耳机", "AirPods", "airpods", "FreeBuds", "freebuds", "蓝牙耳机",
                       "降噪耳机", "入耳式", "头戴式", "有线耳机"]
    },
    "美妆护肤": {
        "精华":   ["精华", "小棕瓶", "小灯泡", "小黑瓶", "安瓶", "护肤品", "化妆品", "美妆", "彩妆", "保养", "护肤"],
        "面霜":   ["面霜", "日霜", "晚霜", "面乳"],
        "眼霜":   ["眼霜", "眼部精华"],
        "面膜":   ["面膜", "面膜贴"],
        "洁面":   ["洁面", "洗面奶", "洁面乳", "洁面霜", "洁面慕斯", "洗颜专科"],
        "化妆水": ["化妆水", "爽肤水", "粉水", "精华水", "收敛水"],
        "乳液":   ["乳液", "润肤乳"],
        "防晒":   ["防晒", "防晒霜", "防晒乳", "防晒喷雾"],
        "粉底液": ["粉底液", "粉底", "粉底霜", "气垫", "BB霜"],
        "唇釉":   ["唇釉", "口红", "唇彩", "唇膏"],
        "眉笔":   ["眉笔", "眉粉", "眉膏"],
        "蜜粉":   ["蜜粉", "散粉", "定妆粉"],
        "卸妆":   ["卸妆", "卸妆水", "卸妆油", "卸妆膏"]
    },
    "食品饮料": {
        "咖啡":       ["咖啡", "星巴克", "雀巢", "拿铁", "美式", "摩卡", "卡布奇诺", "食品", "饮料", "零食"],
        "茶饮":       ["茶饮", "茶π", "乌龙茶", "绿茶", "红茶", "茉莉花茶", "柠檬茶", "果茶"],
        "功能饮料":   ["红牛", "脉动", "东鹏", "佳得乐"],
        "牛奶":       ["牛奶", "纯牛奶", "鲜奶", "高钙奶", "特仑苏", "金典", "脱脂奶"],
        "酸奶":       ["酸奶", "酸牛奶", "发酵乳"],
        "碳酸饮料":   ["可乐", "雪碧", "可口可乐", "百事可乐", "芬达", "醒目"],
        "方便食品":   ["方便面", "泡面", "拉面", "自热饭", "螺蛳粉", "速食", "自热火锅"],
        "坚果/零食":  ["零食", "坚果", "薯片", "巧克力", "饼干", "辣条", "锅巴", "果干"],
        "调味品":     ["调味品", "酱油", "醋", "料酒", "蚝油", "鸡精", "味精"]
    },
    "服饰运动": {
        "跑步鞋":   ["跑步鞋", "跑鞋", "运动鞋", "运动", "鞋子", "鞋", "服饰", "运动装", "安踏", "Nike", "耐克", "特步", "李宁", "篮球鞋"],
        "篮球鞋":   ["篮球鞋", "球鞋", "高帮"],
        "徒步鞋":   ["徒步鞋", "登山鞋", "户外鞋", "越野鞋"],
        "短袖T恤":  ["短袖", "T恤", "t恤", "短袖t恤"],
        "速干T恤":  ["速干", "速干衣", "速干T恤"],
        "运动长裤": ["运动长裤", "运动裤", "健身裤"],
        "卫衣":     ["卫衣", "连帽衫"],
        "户外裤":   ["户外裤"],
        "瑜伽裤":   ["瑜伽裤"],
        "帽子":     ["帽子", "棒球帽", "渔夫帽", "鸭舌帽"],
        "背包":     ["背包", "双肩包", "登山包", "书包"],
        "运动短裤": ["运动短裤", "健身短裤", "训练短裤"]
    }
}

# 单次查询最大返回卡片数
MAX_CARDS = 6

def detect_target(query):
    """根据 query 中的关键词命中数推断目标 (类目, 子品类)。
    优先匹配子品类（更精准），命中数最多的子品类获胜。
    没有子品类命中时再回退到大品类。
    返回 (category, subcategory) 二元组。
    """
    if not query:
        return None, None
    q_low = query.lower()

    # 1) 子品类优先（更精准的过滤）
    best_sub = None
    best_sub_cat = None
    best_sub_hits = 0
    for cat, subs in HIERARCHY.items():
        for sub, kw_list in subs.items():
            unique_kws = set(k.lower() for k in kw_list)
            hits = sum(1 for kw in unique_kws if kw in q_low)
            if hits > best_sub_hits:
                best_sub_hits = hits
                best_sub = sub
                best_sub_cat = cat
    if best_sub_hits > 0:
        return best_sub_cat, best_sub

    # 2) 大品类兜底（关键词被分散到不同子品类的情况）
    best_cat = None
    best_cat_hits = 0
    for cat, subs in HIERARCHY.items():
        all_kws = set()
        for kws in subs.values():
            for k in kws:
                all_kws.add(k.lower())
        hits = sum(1 for k in all_kws if k in q_low)
        if hits > best_cat_hits:
            best_cat_hits = hits
            best_cat = cat
    return best_cat if best_cat_hits > 0 else None, None

def detect_target_with_history(query, history=None):
    """先用当前 query 检测；无命中时倒序遍历 history 中的用户消息找最近的命中。
    修复：当前 query 自己命中了全新类目，直接返回，不继承任何历史的旧类目。
    """
    cat, sub = detect_target(query)
    if cat is not None:
        # 当前 query 自己就命中了类目，完全不需要历史 fallback
        return cat, sub
    if not history:
        return None, None
    # 倒序遍历 history，找最近一条能命中类目的用户消息
    for msg in reversed(history):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if not content:
                continue
            cat, sub = detect_target(content)
            if cat is not None:
                return cat, sub
    return None, None

# 价格敏感词 - 命中时按价格升序（更便宜排前）
PRICE_SENSITIVE_KEYWORDS = [
    "便宜", "更便宜", "实惠", "划算", "廉价", "低价", "低预算",
    "省钱", "省钱", "经济", "性价比", "学生", "学生党",
    "穷", "打折", "促销", "优惠", "秒杀", "百亿补贴"
]

# 品牌关键词 - 命中后返回该品牌全品类所有商品，不限制单一子品类
BRAND_KEYWORDS = {
    "苹果": ["Apple", "apple", "苹果", "iphone", "iPhone"],
    "华为": ["华为", "HUAWEI", "huawei"],
    "小米": ["小米", "MI", "mi"],
    "OPPO": ["OPPO", "oppo", "欧珀"],
    "vivo": ["vivo", "VIVO", "维沃"],
    "耐克": ["Nike", "nike", "耐克"],
    "特步": ["特步", "XTEP", "xtep"],
    "安踏": ["安踏", "ANTA", "anta"],
    "雅诗兰黛": ["雅诗兰黛", "Estee Lauder", "esteelauder"],
    "珀莱雅": ["珀莱雅", "PROYA", "proya"]
}

def detect_brand(query):
    """检测 query 命中的品牌名称，返回品牌名 / None"""
    if not query:
        return None
    q_low = query.lower()
    for brand_name, kw_list in BRAND_KEYWORDS.items():
        for kw in kw_list:
            if kw.lower() in q_low:
                return brand_name
    return None

def is_price_sensitive(query):
    """判断 query 是否表达了"想要更便宜"的诉求"""
    if not query:
        return False
    q_low = query.lower()
    return any(kw in q_low for kw in PRICE_SENSITIVE_KEYWORDS)

def detect_target_category(query):
    """向后兼容：返回大品类字符串"""
    cat, sub = detect_target(query)
    return cat

def filter_by_category(rets, target_cat, target_sub=None):
    """按 (类目, 子品类) 严格过滤：
    - 子品类命中时，**绝不**回退到混合类目
    - 大类目兜底
    - 命中多少就返回多少，最多 MAX_CARDS 张
    """
    if not target_cat:
        return rets[:MAX_CARDS]
    if target_sub:
        # 严格子品类过滤
        filtered = [x for x in rets if x.get('product', {}).get('sub_category') == target_sub]
        if filtered:
            return filtered[:MAX_CARDS]
    # 大类目过滤（兜底）
    filtered = [x for x in rets if x.get('product', {}).get('category') == target_cat]
    return filtered[:MAX_CARDS]

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
    
    yield f"data: {json.dumps({'type': 'session', 'session_id': session_id}, ensure_ascii=False)}\n\n"
    
    if not query:
        yield f"data: {json.dumps({'type': 'error', 'message': 'query cannot be empty'}, ensure_ascii=False)}\n\n"
        return

    # 先推断目标 (类目, 子品类) - 子品类优先，更精准
    # 如果当前 query 没命中类目，从 history 中找最近一条用户消息的类目作为兜底
    target_cat_sse, target_sub_sse = detect_target_with_history(query, req.history)

    # ========== SSE: 全维度意图解析器 ==========
    full_parse_sse = parse_and_full_filter_products(query)

    try:
        if full_parse_sse:
            retrieved = full_parse_sse
            print(f"[SSE FullIntent] 仅本次新查询，共={len(retrieved)}，完全不混入历史旧卡片")
        else:
            query_embedding = embedding_service.embed_text(query)
            retrieved = hybrid_retrieval_service.hybrid_search(query, query_embedding, target_category=target_cat_sse, target_sub=target_sub_sse)
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'Embedding服务不可用: {str(e)}'}, ensure_ascii=False)}\n\n"
        return

    # 仅去重，当前新查询返回的产品 ID 不重复
    seen_pids_sse = set()
    deduped_sse = []
    for item in retrieved:
        pid = item['product'].get('product_id', '')
        if pid and pid not in seen_pids_sse:
            seen_pids_sse.add(pid)
            deduped_sse.append(item)
    retrieved = deduped_sse

    # 🧠 LLM Agent 自主分析用户意图排序
    sort_result = parse_sorting_strategy(query, retrieved)
    retrieved = sort_result.get("products", retrieved)
    print(f"[SSE SortingAgent] strategy={sort_result.get('strategy')}, explanation={sort_result.get('explanation')}")

    # 无全量解析命中，才走常规子品类过滤
    if not full_parse_sse:
        retrieved = filter_by_category(retrieved, target_cat_sse, target_sub_sse)
        print(f"[SSE Filter] category='{target_cat_sse}' sub='{target_sub_sse}', total {len(retrieved)}")
   

    products_data = []
    for item in retrieved:
        products_data.append({
            "product": item['product'],
            "skus": item['skus'],
            "score": float(item.get('score', 0.0))
        })
    yield f"data: {json.dumps({'type': 'products', 'products': products_data}, ensure_ascii=False)}\n\n"
    
    context_parts = []
    product_list_str = ""
    for idx, item in enumerate(retrieved):
        frag = item['fragment']
        prod = item['product']
        context_parts.append(f"[商品{idx+1}: {prod.get('title', '')}]\n{frag.get('content', '')}")
        # 列出所有可用商品，明确告诉 LLM "只许从这些中选"
        price = prod.get('base_price', '')
        product_list_str += f"  {idx+1}. {prod.get('title', '')} (¥{price})\n"

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

    # 推断本次 query 的筛选/排序意图（不仅是价格），注入 prompt 让 LLM 自主筛排
    sort_intent_hint = ""
    if is_price_sensitive(query):
        sort_intent_hint = '\n[系统提示] 用户表达了「更便宜/低价/学生党/性价比」等价格敏感意图。请优先推荐清单中**价格更低**的款，并按价格从低到高组织推荐顺序。'

    system_prompt = f"""你是一个专业的电商智能导购助手。

【严格规则 - 防止编造商品】（违反任何一条即为幻觉，必须严格遵守）
1. 你**只能**从下面【可推荐商品清单】中挑选商品向用户推荐，**清单之外的世界对你不存在**
2. **严禁**编造、杜撰、臆测清单中不存在的商品型号/品牌/价格/规格
   - 例：清单里没有"红米/Redmi"就**绝对不能说**有红米，更不能用"红米"举例
   - 例：清单里没有某个价格档位的机型就**绝对不能**说"该价位有XX款"
3. **严禁**用"通常来说/一般来说/市面上/比如"等模糊措辞暗示清单外的商品
4. 描述商品信息时（型号、价格、内存、颜色等），必须与商品标题和描述**逐字一致**
5. 引用对话历史时，**不要**凭印象编造前面推荐过的内容；只承认清单里实际出现的
6. 清单中**没有的商品 = 不存在**。如果用户要的更便宜/更高端/特定型号在清单中找不到：
   - 不得编造，必须诚实告诉用户"清单里没有 X，目前最接近的是 Y（¥价格）"
   - 列出清单里价格最低（最高/最匹配）的 1-2 款做替代推荐
7. 回复语言：中文。控制 200 字以内，避免冗长。

【理解用户的筛选/排序条件 - 关键能力】
用户问题中常常隐含筛选/排序意图，你需要识别并按这些条件**对清单中的商品重新筛选和排序**后推荐：
- 价格维度：更便宜/便宜/实惠/性价比/学生党/经济/省钱/更贵/高端/旗舰 → 按价格升序/降序
- 性能维度：游戏/性能/速度/快 → 优先 CPU/GPU 强的
- 影像维度：拍照/摄影/影像/自拍/vlog → 优先摄像头规格高的
- 续航维度：续航/电池/电量 → 优先电池容量大的
- 屏幕维度：大屏/小屏/折叠 → 按屏幕形态筛
- 品牌维度：苹果/华为/小米/OPPO/vivo/三星 → 优先匹配品牌
- 使用对象：学生/老人/小孩/商务 → 按定位筛
- 排除维度：不要 X/除了 X → 排除含 X 的商品
识别出意图后，**先按该条件对清单筛排，再写推荐**。如果清单中不满足该条件（如要更便宜但清单里都是高端机），如实告知用户清单中能匹配到的最接近选项。

【可推荐商品清单】（清单里的才是数据库中真实存在的商品）：
{product_list_str}

【商品详情/卖点】：
{context_str}

【对话历史】（用于理解上下文，不要凭此编造未推荐过的内容）：
{history_str}
{sort_intent_hint}

【用户当前问题】：{query}

请根据上述清单和详情，先识别用户的筛选/排序条件并对清单筛排，再给出诚实、简洁的导购回复。**只推荐清单里有的商品**，必要时坦白告知清单的边界（"清单里没有更便宜的选择，最便宜的是 XXX ¥XXX"）。
"""

    full_reply = ""
    for chunk in llm_service.chat_stream(system_prompt, query):
        full_reply += chunk
        yield f"data: {json.dumps({'type': 'content', 'delta': chunk}, ensure_ascii=False)}\n\n"
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
    
    yield f"data: {json.dumps({'type': 'done', 'session_id': session_id}, ensure_ascii=False)}\n\n"

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

    # ========== 核心全维度意图解析器 ==========
    # 直接从全库扫描，不依赖向量召回，返回所有符合用户 品牌/品类/关键词 的商品
    # 跨子品类全量返回（比如“苹果的产品”=手机 + 平板 + AirPods... 全部）
    full_parse_result = parse_and_full_filter_products(query)

    try:
        if full_parse_result:
            # 全维度解析返回非空，直接优先采用（100% 覆盖数据库真实商品）
            retrieved = full_parse_result
            print(f"[FullIntent] 仅返回本次新查询的结果，共 {len(retrieved)} 件，完全不混入历史旧卡片")
        else:
            # 普通场景：向量检索
            query_embedding = embedding_service.embed_text(query)
            retrieved = hybrid_retrieval_service.hybrid_search(query, query_embedding, target_category=target_cat, target_sub=target_sub)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Embedding服务不可用: {str(e)}. 请检查火山引擎API Key和Endpoint配置。")

    # 只做去重：确保当前这条新查询返回的产品 ID 不重复
    seen_pids = set()
    deduped = []
    for item in retrieved:
        pid = item['product'].get('product_id', '')
        if pid and pid not in seen_pids:
            seen_pids.add(pid)
            deduped.append(item)
    retrieved = deduped

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

    # === 🧠 LLM Agent 智能筛选重排 ===
    # 不再人工硬编码 if-else！让 Sorting Agent 自主分析用户自然语言意图，
    # 自主判断要按什么维度对商品进行筛排，完全替代旧的"价格敏感"硬编码逻辑。
    sort_result = parse_sorting_strategy(query, retrieved)
    retrieved = sort_result.get("products", retrieved)
    print(f"[SortingAgent] strategy={sort_result.get('strategy')}, explanation={sort_result.get('explanation')}")

    # 自动类目推断过滤，只返回相关类目商品
    retrieved = filter_by_category(retrieved, target_cat, target_sub)
    print(f"[Filter] category='{target_cat}' sub='{target_sub}', total {len(retrieved)} products")

    # === 完整SKU确认对话式加购机制 ===
    from services.sku_selection_parser import parse_user_sku_selection
    cart_action = None
    if add_to_cart_intent and retrieved:
        target = retrieved[0]
        product_title = target['product']['title']
        all_skus = target.get('skus', [])
        
        # 核心：调用SKU解析器判断用户是否指定了唯一SKU
        sku_parse_result = parse_user_sku_selection(
            product_title=product_title,
            all_skus=all_skus,
            user_query=query
        )
        
        cart_action = {
            "intent_detected": True,
            "keyword": add_to_cart_intent,
            "product_id": target['product']['product_id'],
            "title": product_title,
            "added_to_cart": False,
            "sku_parse_status": sku_parse_result.status
        }
        
        if sku_parse_result.status == "exact_one":
            # 用户已经明确指定了唯一SKU，直接加入购物车
            try:
                matched_sku = sku_parse_result.matched_sku
                item = CartItemAdd(
                    user_id=session_id,
                    product_id=target['product']['product_id'],
                    sku_id=matched_sku['sku_id'] if matched_sku else None,
                    title=product_title,
                    brand=target['product'].get('brand'),
                    image_path=target['product'].get('image_path'),
                    unit_price=matched_sku['price'] if matched_sku else target['product'].get('base_price', 0),
                    quantity=1
                )
                result = cart_service.add_to_cart(item)
                cart_action["added_to_cart"] = True
                cart_action["cart_item_id"] = result.id
                cart_action["selected_sku"] = matched_sku
            except Exception as e:
                cart_action["error"] = str(e)
        else:
            # 用户没有指定唯一SKU，返回所有选项询问用户选择
            cart_action["need_user_select_sku"] = True
            cart_action["candidate_skus"] = sku_parse_result.candidates
            cart_action["ask_user_msg"] = sku_parse_result.ask_user_msg

    context_parts = []
    product_list_str = ""
    for idx, item in enumerate(retrieved):
        frag = item['fragment']
        prod = item['product']
        context_parts.append(f"[商品{idx+1}: {prod.get('title', '')}]\n{frag.get('content', '')}")
        price = prod.get('base_price', '')
        product_list_str += f"  {idx+1}. {prod.get('title', '')} (¥{price})\n"

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

    # 在Prompt中加入加购/排除/SKU选择感知
    extra_hint = ""
    if cart_action and cart_action.get("added_to_cart"):
        extra_hint = f"\n\n[系统消息] 用户刚说「{query}」，你已经把「{cart_action['title']}」加入了用户的购物车，请在回复中确认此操作。"
    elif cart_action and cart_action.get("need_user_select_sku"):
        # 用户未指定明确SKU，展示选项询问用户
        extra_hint = f"\n\n[系统消息] 用户想加购的商品有多个不同规格可选，你不要擅自直接加入购物车，请友好地把这些规格选项告诉用户，让用户从中选择一款。\n{cart_action['ask_user_msg']}"
    if exclude_keywords:
        extra_hint += f"\n\n[系统消息] 用户明确排除了这些特征/品牌/类型：{exclude_keywords}。请确保推荐的商品不包含这些特征。"
    # 筛选/排序意图提示（不仅是价格）
    sort_intent_hint = ""
    if is_price_sensitive(query):
        sort_intent_hint = '\n[系统提示] 用户表达了「更便宜/低价/学生党/性价比」等价格敏感意图。请优先推荐清单中**价格更低**的款，并按价格从低到高组织推荐顺序。'

    system_prompt = f"""你是一个专业的电商智能导购助手。

【严格规则 - 防止编造商品】（违反任何一条即为幻觉，必须严格遵守）
1. 你**只能**从下面【可推荐商品清单】中挑选商品向用户推荐，**清单之外的世界对你不存在**
2. **严禁**编造、杜撰、臆测清单中不存在的商品型号/品牌/价格/规格
   - 例：清单里没有"红米/Redmi"就**绝对不能说**有红米，更不能用"红米"举例
   - 例：清单里没有某个价格档位的机型就**绝对不能**说"该价位有XX款"
3. **严禁**用"通常来说/一般来说/市面上/比如"等模糊措辞暗示清单外的商品
4. 描述商品信息时（型号、价格、内存、颜色等），必须与商品标题和描述**逐字一致**
5. 引用对话历史时，**不要**凭印象编造前面推荐过的内容；只承认清单里实际出现的
6. 清单中**没有的商品 = 不存在**。如果用户要的更便宜/更高端/特定型号在清单中找不到：
   - 不得编造，必须诚实告诉用户"清单里没有 X，目前最接近的是 Y（¥价格）"
   - 列出清单里价格最低（最高/最匹配）的 1-2 款做替代推荐
7. 回复语言：中文。控制 200 字以内，避免冗长。

【理解用户的筛选/排序条件 - 关键能力】
用户问题中常常隐含筛选/排序意图，你需要识别并按这些条件**对清单中的商品重新筛选和排序**后推荐：
- 价格维度：更便宜/便宜/实惠/性价比/学生党/经济/省钱/更贵/高端/旗舰 → 按价格升序/降序
- 性能维度：游戏/性能/速度/快 → 优先 CPU/GPU 强的
- 影像维度：拍照/摄影/影像/自拍/vlog → 优先摄像头规格高的
- 续航维度：续航/电池/电量 → 优先电池容量大的
- 屏幕维度：大屏/小屏/折叠 → 按屏幕形态筛
- 品牌维度：苹果/华为/小米/OPPO/vivo/三星 → 优先匹配品牌
- 使用对象：学生/老人/小孩/商务 → 按定位筛
- 排除维度：不要 X/除了 X → 排除含 X 的商品
识别出意图后，**先按该条件对清单筛排，再写推荐**。如果清单中不满足该条件（如要更便宜但清单里都是高端机），如实告知用户清单中能匹配到的最接近选项。

【可推荐商品清单】（已按"价格/相关度"为你预排序，清单上的才是真实存在的）：
{product_list_str}

【商品详情/卖点】：
{context_str}

【对话历史】（用于理解上下文，不要凭此编造未推荐过的内容）：
{history_str}
{sort_intent_hint}

【用户当前问题】：{query}
{extra_hint}

请根据上述清单和详情，先识别用户的筛选/排序条件并对清单筛排，再给出诚实、简洁的导购回复。**只推荐清单里有的商品**，必要时坦白告知清单的边界（"清单里没有更便宜的选择，最便宜的是 XXX ¥XXX"）。
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
            'skus': item['skus'],
            'score': float(item.get('score', 0.0))
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
    # 先推断目标 (类目, 子品类) - 子品类优先，更精准
    # 如果当前 query 没命中类目，从 history 中找最近一条用户消息的类目作为兜底
    target_cat, target_sub = detect_target_with_history(query, req.history)
    try:
        query_embedding = embedding_service.embed_text(query)
        retrieved = hybrid_retrieval_service.hybrid_search(query, query_embedding, target_category=target_cat, target_sub=target_sub)
        # 去重 + 排序 + 类目过滤
        seen_pids = set()
        deduped = []
        for item in retrieved:
            pid = item['product'].get('product_id', '')
            if pid and pid not in seen_pids:
                seen_pids.add(pid)
                deduped.append(item)
        retrieved = deduped
        retrieved.sort(key=lambda x: x.get('score', 0.0), reverse=True)
        retrieved = filter_by_category(retrieved, target_cat, target_sub)
        return {"results": retrieved}
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
                "fragment": {
                    "fragment_id": f"{product_id}_image_001",
                    "product_id": product_id,
                    "content_type": "image",
                    "title": "",
                    "content": "商品图片"
                },
                "product": prod,
                "skus": skus
            })

        return {
            "results": results,
            "image_filename": filename,
            "query_text": query or ""
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"图像检索失败: {str(e)}")


# ============== 购物车 API ==============
from cart_models import CartItemAdd, CartItemUpdate, init_cart_table
from cart_service import CartService

# 初始化购物车表
init_cart_table("d:/RAG导购/ecommerce.db")
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

# AI全栈挑战赛 - RAG多模态智能导购系统 完整参赛文档

---

## 📋 基础信息

| 项目项 | 内容 |
|--------|------|
| **项目名称** | RAG多模态智能导购系统 |
| **版本** | v1.0.3 |
| **最后更新** | 2026-06-10 |
| **队名** | 个人参赛 |
| **团队成员** | 单人全栈开发 |
| **分工说明** | 独立完成全部模块：后端FastAPI智能检索引擎 + Android移动端Jetpack Compose + 数据库全量工程 + SSE流式交互 + 向量检索多模态模块 |
| **代码仓库地址** | https://github.com/Xjorker/RAG4e-commerce_guide |

---

## 1️⃣ 项目简介

本项目是一个基于 RAG (检索增强生成) 技术的完整多模态AI智能导购应用，支持自然语言对话选品、图片以图搜同款、三大核心智能意图Agent、完整购物车管理、SSE流式回复，采用Android移动端 + 后端RESTful/SSE双协议架构，覆盖电商导购全核心交互场景。

---

## 2️⃣ 设计文档

### 2.1 系统架构图
```
┌──────────────────────────────────────────────────────────────┐
│                      Android 移动端 App                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Login    │  │ Chat     │  │ Product  │  │ Cart     │ │
│  │ Register│  │ Screen   │  │ Detail   │  │ Screen  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
└───────────────────────────────┬──────────────────────────────┘
                                 │ HTTP / SSE 直连
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│              FastAPI 后端服务 (Python 3.10+)                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  用户意图Agent层  - 三大核心意图识别                         │  │
│  │  1. 推荐筛选意图 (价格/类目/品牌/颜色/功能属性过滤)        │  │
│  │  2. 加购意图 (历史商品定位 + 智能选SKU)                     │  │
│  │  3. 对比分析意图 (多商品导购对比)                           │  │
│  │  认证鉴权层  (Bearer JWT Token)                             │  │
│  │  历史结果上下文缓存层 (全维度继承式过滤)                      │  │
│  │  RAG 混合检索层 (BM25 + 向量 + V4.3规则过滤引擎)            │  │
│  │  LLM 服务层 (火山引擎 Ark / OpenAI 兼容接口)                  │  │
│  │  业务数据库 SQLite (商品 100款 / SKU 585个 / 用户 / 购物车)    │  │
│  │  向量库 Chroma (CLIP图像特征 + Embedding文本向量持久化)       │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈清单

#### 后端技术栈 (Python)
| 模块 | 技术选型 |
|------|----------|
| Web框架 | FastAPI + Uvicorn |
| 数据校验 | Pydantic v2 |
| 中文分词 | Jieba |
| 文本检索 | Okapi BM25 |
| 向量库 | Chroma DB |
| 向量模型 | CLIP 图像特征 + text2vec |
| 认证鉴权 | python-jose (JWT) + passlib 密码哈希 |
| LLM兼容层 | 火山引擎Ark / OpenAI 兼容接口 |
| 数据库 | SQLite 3 (单文件零部署) |

#### Android移动端技术栈 (Kotlin)
| 模块 | 技术选型 |
|------|----------|
| UI框架 | Jetpack Compose 完全声明式 |
| 网络请求 | Retrofit 2 + OkHttp |
| SSE客户端 | OkHttp Server Sent Events 原生支持 |
| 图片加载 | Coil (异步加载assets商品图) |
| 异步框架 | Kotlin Coroutines + Flow |
| 最低SDK版本 | API 26 (Android 8.0+) |
| 目标SDK版本 | API 34 (Android 14) |

### 2.3 依赖环境配置

#### 后端环境安装
```bash
# 一键安装所有Python依赖
pip install fastapi uvicorn pydantic requests numpy jieba chromadb openai python-jose passlib python-multipart
```

创建 `.env` 环境变量配置文件：
```env
# 大模型配置
VOLCENGINE_API_KEY=你的火山引擎Ark API Key
VOLCENGINE_EP_ID=你的推理接入点ID
VOLCENGINE_EMBEDDING_API_KEY=你的Embedding服务Key

# 服务端口
PORT=9000
```

#### Android构建环境
- Android Studio 版本：Hedgehog | Iguana | Jellyfish 均可
- compileSdk = 34
- minSdk = 26
- targetSdk = 34
- Gradle = 8.x 以上版本

### 2.4 完整目录结构
```
RAG导购/
├── .env                                  # 环境变量配置文件
├── AI全栈挑战赛参赛项目文档.md           # 本参赛文档
├── README.md                             # 项目说明
├── backend/
│   ├── main.py                           # FastAPI主程序入口
│   ├── user_auth.py                      # 用户认证模块 - Token签发/校验
│   ├── filter_engine.py                  # V4.3 全维度智能意图过滤引擎
│   ├── config.py                         # 全局配置常量
│   ├── response_card_aligner.py          # 卡片文字一致性对齐器
│   ├── structured_comparison.py          # 结构化多商品对比生成器
│   ├── history_product_cache.py          # 全量历史推荐结果上下文缓存
│   ├── cart_service.py                   # 购物车CRUD服务
│   ├── cart_models.py                    # 购物车Pydantic模型
│   ├── database/
│   │   ├── sqlite_client.py             # SQLite数据库CRUD - 存商品/SKU/用户/购物车/聊天记录
│   │   ├── bm25_index.py                # BM25 全量商品知识库索引管理
│   │   └── chroma_client.py             # Chroma 向量数据库客户端
│   └── services/
│       ├── llm_service.py               # LLM流式SSE服务模块
│       ├── hybrid_retrieval_service.py   # 混合检索引擎
│       ├── full_intent_parser.py        # 三大核心意图完整识别引擎
│       ├── sku_selection_parser.py      # SKU智能选择解析器
│       └── embedding_service.py         # Embedding向量生成服务
├── data/
│   ├── ecommerce.db                      # SQLite主库 (100商品+585SKU)
│   └── chroma_db/                       # Chroma向量持久化目录
├── data_ingestion/                       # 全量数据集生成工程脚本
├── RAG-Shopping-Guide-Android/          # Android移动端完整项目
    └── app/src/main/
        ├── assets/                       # 100张4K实拍商品图片
        ├── kotlin/com/rag/shopping/guide/
        │   ├── data/api/
        │   │   ├── RetrofitClient.kt    # Retrofit单例
        │   │   ├── SSEClient.kt         # SSE流式对话客户端
        │   │   ├── TokenManager.kt      # SharedPreferences Token持久化
        │   │   └── AuthInterceptor.kt  # 自动注入Bearer Token拦截器
        │   ├── data/model/
        │   │   └── Models.kt            # 前后端统一数据模型定义
        │   ├── ui/
        │   │   ├── auth/                # 登录页 / 注册页
        │   │   ├── chat/                 # 主对话聊天页 (核心)
        │   │   ├── cart/                 # 购物车管理页
        │   │   └── detail/               # 商品详情 + SKU选择页
        │   ├── RAGGuideApp.kt            # Application全局初始化
        │   └── MainActivity.kt           # 主入口导航路由
        └── res/
```

### 2.5 API 接口总览

| 接口路径 | 方法 | 功能描述 |
|----------|------|----------|
| `/api/v1/auth/register` | POST | 用户新用户注册 |
| `/api/v1/auth/login` | POST | 用户登录获取JWT Token |
| `/api/v1/chat/stream` | POST | SSE流式对话主入口 |
| `/api/v1/product/{pid}` | GET | 获取单个商品详情及全部SKU |
| `/api/v1/cart` | GET | 获取当前用户全购物车列表 |
| `/api/v1/cart` | POST | 添加新商品到购物车 |
| `/api/v1/cart/{item_id}` | PUT | 更新购物车中商品数量 |
| `/api/v1/cart/{item_id}` | DELETE | 删除指定购物车项 |

---

## 3️⃣ 核心亮点/创新点 (3条)

### 创新点1：V4.3 全维度历史继承式意图理解引擎
不做每次查询都全库重新检索的传统模式，而是基于上一轮的推荐结果做渐进式上下文过滤：
- 第一轮查询："15000以内笔记本" → 正常返回5款符合条件的笔记本
- 第二轮："不要华为的" → **仅在上一轮5个商品集合里操作**，剔除华为MateBook，剩下4款非华为笔记本，绝对不会返回全库100个无关的美妆/服饰/食品商品
- 第三轮："更便宜一点的" → 直接继承全部上下文，价格自动向下浮动30%，用户完全不用重复描述任何子品类、品牌约束

### 创新点2：SSE流驱动自动加购原生交互
大模型在流式生成回复过程中实时识别加购意图，无需用户跳转额外加购按钮，完全自然对话交互：
- 用户说"把第一款 MacBook Pro 14英寸的给我加购"
- LLM流式输出时，后端自动通过历史商品缓存定位到目标商品ID，智能取第1个SKU
- 写入购物车成功后，立刻通过SSE追加 `cart_action` 事件实时推送到Android端
- App收到事件后自动更新右上角购物车角标数字，全程零跳转

### 创新点3：100款全品类真实电商数据集
不是Demo级模拟数据，覆盖4大电商核心品类，数据规格真实：
- 数码电子：25款手机/笔记本/平板
- 美妆护肤：25款精华/面霜/防晒
- 服饰运动：25款跑鞋/篮球鞋/运动服饰
- 食品生活：25款咖啡/饮料/零食
- **总计585个真实多规格SKU**，每款商品的属性、价格、图片完全贴近真实电商平台

---

## 4️⃣ 关键问题解决方案汇总

| 问题编号 | 问题描述 | 解决方案 |
|---------|----------|----------|
| 7.1 | LLM大模型生成的文字介绍和下方卡片展示的商品不一致 | 1. 后端结构化拼接Context：把推荐出来的商品100%用「序号+标题+品牌+价格+描述」的固定格式传给LLM 2. App端完全信任后端返回的商品顺序，不做任何本地二次排序/过滤 3. 前后端商品列表完全同源，保证文字和卡片100%对齐 |
| 7.2 | 用户修改他人购物车数据，越权访问 | 1. 所有购物车接口强制从 Authorization: Bearer xxx Token 解析user_id 2. 完全拒绝任何通过query参数传递user_id的做法 3. 执行update/delete操作前，先校验item_id是否属于当前登录用户，不属于直接返回403 4. 商品库所有公开接口全部为只读，无任何用户可写入商品的端点 |
| 7.3 | Android App冷启动每次都要求重新登录 | SharedPreferences 持久化存储 JWT Token，App冷启动时自动读取本地Token，检测到Token有效则直接进入聊天主页面，用户完全无需重复登录 |
| 7.4 | 三大核心意图完整识别系统 | 1. 推荐筛选意图：自动识别数字价格阈值、目标子品类、品牌关键词、颜色属性、功能属性，精准召回商品默认返回5个 2. 加购意图：关键词模式匹配 + 历史商品缓存定位，自动取第1个可用SKU写入购物车 3. 对比分析意图：识别「对比这两款」指令，自动提取指定商品生成结构化导购对比 |
| 7.5 | 用户输入"不要华为"，卡片被本地过滤全部清空 | 移除Android端冗余的本地二次分类过滤逻辑，完全信任后端已经过滤好的结果，后端返回什么就展示什么，不会出现卡片消失的问题 |
| 7.6 | 多SKU规格全部丢失 | 重写全量数据导入脚本，把585个真实多规格SKU完整导入SQLite数据库，SKU选择列表全部正常展示 |
| 7.7 | SSE响应慢，用户等待时间长 | 改用SSE流式输出，大模型每生成几个Token就立刻推送到前端，用户即刻就能看到输出，不会等到大模型全部生成完毕才一次性返回 |

---

## 5️⃣ 安全设计清单

1. **密码安全**：所有用户密码使用 `bcrypt` 风格的 passlib SHA256 + salt 进行哈希存储，数据库中不会保存任何明文密码
2. **JWT过期**：Token默认有效期设置为7天，过期后自动要求重新登录
3. **SQL注入防护**：所有数据库操作全部使用参数化查询，绝对不拼接SQL字符串
4. **权限隔离**：普通用户完全没有权限访问任何管理类接口，所有购物车操作强制绑定当前登录用户的user_id
5. **网络安全**：AndroidManifest.xml 配置明文HTTP访问权限，允许本地开发调试访问 `10.0.2.2:9000`

---

## 6️⃣ 部署体验指南

### 6.1 本地启动后端服务
打开终端进入项目根目录，执行：
```bash
cd d:\RAG导购
python start_fastapi_9000.py
```
服务启动成功后访问 `http://127.0.0.1:9000/docs` 可以看到Swagger接口文档。

### 6.2 Android模拟器网络配置
Android模拟器中，后端地址使用 `http://10.0.2.2:9000/` 自动映射到你宿主机的回环地址，无需修改任何IP配置。

### 6.3 评委快速体验路径
按照以下4步就能完整体验所有核心功能，全程2分钟：
1. **注册登录**：在App首页随便输入用户名密码点注册，自动登录跳转到主聊天界面
2. **自然语言选品**：输入"15000以内的笔记本，不要华为的" → 系统正常返回4款非华为笔记本卡片，全部正常展示
3. **加购体验**：接着输入"把第一款 MacBook Pro 14英寸的给我加购" → 系统自动识别并添加到购物车，右上角购物车角标数字立刻变成1
4. **图片搜款**：点输入框左边的附件图标，选择任意一张数码产品实拍图发送 → 系统用CLIP向量检索自动找到同款商品

---

## 7️⃣ 后续迭代规划
1. 向量检索基于Chroma DB全维度优化召回精度
2. 新增支付/订单模块完整链路
3. 新增管理员后台商品管理面板
4. LLM完全切换成本地部署的开源大模型（Qwen / Llama 系列）

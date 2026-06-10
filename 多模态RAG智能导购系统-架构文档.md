# 多模态RAG智能导购系统 - 完整架构文档

---

## 一、系统概述

本课题是一个面向电商领域的**多模态检索增强生成（RAG）智能导购系统**，融合图文多模态向量混合检索、大语言模型生成能力，为用户提供自然流畅的智能商品咨询、推荐和导购服务。

系统核心特色：
- 支持文本、图像跨模态统一检索
- 融合向量相似度检索 + BM25关键词检索的**混合检索策略**，召回更精准
- 整合商品详情、营销话术、官方FAQ、真实用户评价多维度知识
- 基于火山引擎多模态Embedding实现图文共享向量空间
- 全栈采用轻量级本地数据库（SQLite+ChromaDB），零额外依赖部署
- 提供Android移动端友好交互入口

---

## 二、核心技术栈选型

| 模块 | 技术选型 | 说明 |
|------|---------|------|
| 多模态Embedding模型 | 火山引擎 doubao-embedding-vision-251215 | 已测试通过，支持文本+图片统一1024维向量输出 |
| 大语言模型 | 火山引擎/OpenAI兼容接口 | 负责对话生成、导购推理 |
| 向量数据库 | ChromaDB（或Infinity） | 轻量级本地部署，用于存储多模态向量 |
| 业务数据库 | SQLite | 零依赖文件型数据库，存储商品元数据、SKU、对话历史 |
| 全文检索 | BM25（使用rank_bm25库） | 纯关键词倒排索引，与向量检索做混合召回 |
| 后端框架 | Python FastAPI | 提供RESTful API服务 |
| 移动端 | 原生Android（基于现有chatgpt-android-main项目） | 用户交互入口 |
| RAG底座 | 基于ragflow-main优化 | 提供文档解析、分块、检索流水线能力 |

---

## 三、数据层设计

### 3.1 SQLite业务库表结构设计

#### 表1：products（商品主表）
| 字段名 | 类型 | 说明 |
|-------|------|------|
| product_id | TEXT PRIMARY KEY | 商品唯一标识 |
| title | TEXT NOT NULL | 商品标题 |
| brand | TEXT | 品牌 |
| category | TEXT | 一级分类 |
| sub_category | TEXT | 二级子分类 |
| base_price | REAL | 基础价格 |
| image_path | TEXT | 商品图片相对路径 |
| created_at | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | 创建时间 |

#### 表2：skus（商品SKU表）
| 字段名 | 类型 | 说明 |
|-------|------|------|
| sku_id | TEXT PRIMARY KEY | SKU唯一标识 |
| product_id | TEXT NOT NULL | 关联商品ID（外键） |
| properties | TEXT | JSON格式规格属性（容量/口味等） |
| price | REAL | 该SKU售价 |

#### 表3：rag_fragments（RAG知识片段表，同时用于BM25索引）
| 字段名 | 类型 | 说明 |
|-------|------|------|
| fragment_id | TEXT PRIMARY KEY | 片段唯一ID |
| product_id | TEXT NOT NULL | 关联商品ID |
| content_type | TEXT | 片段类型：marketing/faq/review |
| title | TEXT | 片段标题（可选） |
| content | TEXT NOT NULL | 片段完整文本内容（用于BM25检索） |
| metadata_json | TEXT | 附加元数据JSON |
| created_at | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | 创建时间 |

#### 表4：chat_history（对话历史表）
| 字段名 | 类型 | 说明 |
|-------|------|------|
| msg_id | TEXT PRIMARY KEY | 消息唯一ID |
| session_id | TEXT NOT NULL | 会话ID |
| role | TEXT NOT NULL | user/assistant |
| content | TEXT NOT NULL | 消息内容 |
| created_at | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | 消息时间 |

---

### 3.2 多模态向量库存储设计

- **文本向量**：商品标题、营销描述、FAQ问答、评价文本 → 生成1024维向量
- **图像向量**：商品主图 → 生成1024维向量
- **统一空间**：图文共享同一向量空间，支持跨模态检索（图搜文、文搜图）

向量库每条记录结构：
```
{
  id: "p_beauty_001_text_001",
  embedding: [float, ...], // 1024维
  metadata: {
    product_id: "p_beauty_001",
    fragment_id: "frag_001",
    type: "text",
    content_type: "marketing", // marketing/faq/review/image
  },
  document: "文本内容快照"
}
```

---

### 3.3 BM25全文检索索引

使用`rank_bm25`轻量级库构建倒排索引，针对`rag_fragments`表中所有知识片段的content字段建立索引，实现关键词级别的精准召回。

---

## 四、系统分层架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     端侧交互层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Android APP │  │ Web管理后台  │  │ 小程序端     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              ↕ HTTP/REST
┌─────────────────────────────────────────────────────────────┐
│                    API服务层 (FastAPI)                      │
│  /chat, /search, /recommend, /product/manage...            │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                  业务逻辑与RAG引擎层                          │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ 意图理解模块     │  │ 对话记忆管理     │                │
│  └──────────────────┘  └──────────────────┘                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              多模态混合检索流水线                        │  │
│  │                                                      │  │
│  │  ┌─────────────┐          ┌─────────────┐           │  │
│  │  │ 向量检索     │ ────┐   │ BM25关键词   │           │  │
│  │  │ (Top-50)    │      ├──→ │ 融合排序     │ → 最终Top-10│  │
│  │  └─────────────┘      │   └─────────────┘           │  │
│  │  ┌─────────────┐      │                              │  │
│  │  │ 火山引擎    │ ─────┘   (权重可调alpha: 0.7向量+0.3BM25)│  │
│  │  │ Embedding   │                                  │  │
│  │  └─────────────┘                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ LLM生成导购回复  │  │ 商品推荐策略     │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                    数据存储层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  ChromaDB   │  │   SQLite     │  │ BM25索引     │     │
│  │  (多模态向量)│  │  (商品元数据) │  │  (关键词倒排) │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                      ↓ 文件存储 ↓                          │
│                  ┌──────────────┐                           │
│                  │ 商品图片文件 │                           │
│                  └──────────────┘                           │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                 外部模型服务层（火山引擎）                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  doubao-embedding-vision-251215 (已测试成功)         │  │
│  │  多模态图文Embedding接口                                │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Doubao LLM 对话生成服务                               │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 五、核心业务流程

### 5.1 多模态混合检索导购对话主流程

1. **用户输入阶段**：用户发送自然文本消息，或上传商品图片进行以图搜物
2. **向量化阶段**：调用火山引擎多模态Embedding API，将用户输入（文本/图片）转为1024维查询向量
3. **双路召回阶段**：
   - 路径A（向量检索）：在ChromaDB中执行相似度检索，召回Top-50向量相关片段
   - 路径B（BM25关键词检索）：对用户Query分词，在BM25倒排索引中执行关键词检索，召回Top-50命中片段
4. **分数融合阶段**：两路召回结果归一化，按权重融合（α=0.7向量分 + β=0.3 BM25分），去重合并后重排序，选出最终Top-10知识片段
5. **元数据关联阶段**：通过product_id/SQLite关联完整商品元数据，补充SKU、价格等结构化信息
6. **Prompt组装阶段**：将召回的Top-10商品知识片段、对话历史上下文组装成结构化增强Prompt
7. **LLM生成阶段**：调用Doubao大模型，基于增强Prompt生成自然流畅的导购回复
8. **结果返回阶段**：返回AI回复文本 + 关联推荐商品卡片列表给前端展示
9. **记忆持久化**：将本轮对话存入SQLite的chat_history表，保持多轮上下文连续性

### 5.2 商品知识库构建（离线）流程

1. 批量读取ecommerce_agent_dataset中的商品JSON数据
2. 先将完整商品元数据、SKU信息批量写入SQLite建立索引
3. 对每个商品的不同知识片段（标题、营销描述、每条FAQ、每条评价）单独拆分，存入rag_fragments表
4. 基于rag_fragments表的所有content字段，构建rank_bm25倒排索引文件
5. 分别调用火山引擎多模态Embedding API生成对应文本向量
6. 对商品主图进行处理后调用接口生成图像向量
7. 将所有向量 + 元数据批量写入ChromaDB向量库
8. 完成全量知识库初始化，等待上线运行

---

## 六、火山引擎API调用规范

### 6.1 多模态Embedding接口（已测试通过）

**请求地址**：
```
POST https://ark.cn-beijing.volces.com/api/v3/embeddings/multimodal
```

**请求头**：
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer d930929b-e2e2-404c-83f7-2b7b673780fe"
}
```

**请求体示例**：
```json
{
  "model": "doubao-embedding-vision-251215",
  "input": [
    {
      "type": "text",
      "text": "天很蓝，海很深"
    },
    {
      "type": "image_url",
      "image_url": {
        "url": "https://ark-project.tos-cn-beijing.volces.com/images/view.jpeg"
      }
    }
  ]
}
```

**响应示例**：
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "embedding": [0.123, -0.456, ...],  // 1024维浮点数数组
      "index": 0
    }
  ],
  "model": "doubao-embedding-vision-251215",
  "usage": {
    "prompt_tokens": 524,
    "prompt_tokens_details": {
      "image_tokens": 497,
      "text_tokens": 27
    },
    "total_tokens": 524
  }
}
```

**API测试状态**：✅ 已验证调用成功，返回正常

---

## 七、项目目录结构规划

```
d:\RAG导购\
├── 多模态RAG智能导购系统-架构文档.md    # 本文档
├── test_multimodal_embedding.py          # API测试脚本
├── ecommerce_agent_dataset\               # 电商原始商品数据集
│   ├── 1_美妆护肤\
│   ├── 4_食品生活\
│   └── ...
├── backend\                               # 新增：FastAPI后端代码
│   ├── main.py                            # API入口
│   ├── config.py                          # 配置文件
│   ├── services\
│   │   ├── embedding_service.py           # 火山引擎Embedding服务
│   │   ├── hybrid_retrieval_service.py   # 混合检索核心服务（向量+BM25融合）
│   │   └── llm_service.py                 # LLM对话生成服务
│   ├── models\
│   │   ├── product.py                     # 商品数据模型
│   │   └── chat.py                        # 对话数据模型
│   └── database\
│       ├── chroma_client.py                # ChromaDB向量库客户端
│       ├── sqlite_client.py                # SQLite业务库客户端
│       └── bm25_index.py                  # BM25全文检索索引管理
├── data_ingestion\                         # 新增：知识库构建脚本
│   └── build_knowledge_base.py            # 批量向量化入库 + 构建BM25索引
├── data\                                   # 数据库文件目录
│   ├── ecommerce.db                        # SQLite业务数据库
│   └── bm25_index.pkl                      # BM25倒排索引序列化文件
├── ragflow-main\                           # 开源RAGFlow底座（参考）
├── chatgpt-android-main\                   # Android移动端源码
└── RAG-Anything-main\                      # 参考演示项目
```

---

## 八、API接口设计

| 接口路径 | 方法 | 功能说明 |
|---------|------|---------|
| `/api/v1/chat` | POST | 发送导购对话消息，获取AI回复+推荐商品 |
| `/api/v1/search` | POST | 多模态混合检索商品（文本/图片查询） |
| `/api/v1/product/{id}` | GET | 获取单个商品详情 |
| `/api/v1/recommend` | GET | 获取个性化推荐商品列表 |
| `/api/v1/admin/ingest` | POST | 触发生成全量知识库向量化、BM25索引构建入库 |

---

## 九、项目已有的基础资产盘点

| 资源 | 路径 | 状态 |
|------|------|------|
| 火山引擎多模态Embedding API | 已测试验证 | ✅ 可直接使用 |
| 电商商品数据集（美妆/食品等） | `ecommerce_agent_dataset/` | 2个类目50+商品样例 |
| RAGFlow完整开源RAG底座 | `ragflow-main/` | 完整RAG流水线代码 |
| Android端聊天界面基础框架 | `chatgpt-android-main/` | 移动端交互基础 |
| RAG-Anything快速演示参考 | `RAG-Anything-main/` | 快速验证参考 |

---

## 十、后续开发路线图

1. **第一阶段**：搭建FastAPI基础工程，封装火山引擎Embedding服务，完成SQLite表结构初始化
2. **第二阶段**：集成ChromaDB，实现BM25倒排索引构建，开发知识库批量向量化入库脚本
3. **第三阶段**：实现双路召回混合检索流水线（向量+BM25分数融合），组装RAG增强Prompt对接LLM
4. **第四阶段**：适配Android移动端，完成端到端完整链路调通
5. **第五阶段**：优化权重调参、个性化推荐逻辑，进行导购效果评估

---

*文档生成日期：2026-05-21（修订版）*

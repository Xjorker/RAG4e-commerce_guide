# RAG 智能导购系统

> 基于多模态检索的AI智能电商导购App，支持文字、图片混合搜索，大语言模型Agent自动推荐商品并加入购物车，完整的移动端Android体验。

## ✨ 核心功能

### 🤖 AI智能导购
- **多模态RAG混合检索**：BM25关键词 + 向量召回，精准匹配用户需求
- **SSE流式输出**：实时展示大模型生成内容，体验丝滑流畅
- **Agent自动加购**：识别用户"加购物车"意图，无需手动操作自动完成商品添加
- **智能过滤引擎**：支持价格区间筛选、关键词排除、按分类过滤
- **结构化商品对比**：自动生成多商品对比表格，帮用户快速决策

### 👤 用户系统
- 完整的用户名密码注册登录
- JWT Token 无感认证，7天有效期
- 权限隔离：每个用户只能操作自己的购物车

### 🛒 购物车完整功能
- 添加商品到购物车
- 查看购物车商品列表
- 修改商品数量
- 删除指定商品
- 一键清空购物车

### 📷 图片搜索
- 支持从相册选择商品图片上传检索
- 结合CLIP多模态向量，精准识别图片中的商品品类
- 图片 + 文字描述组合搜索，效果更精准

### 📱 Android App 原生体验
- Jetpack Compose 全现代化UI
- Material Design 3 设计规范
- 商品卡片瀑布流展示
- 商品详情页完整展示
- 图片异步加载优化（Coil）

## 🏗️ 技术架构

### 后端技术栈
| 组件 | 技术选型 |
|------|----------|
| Web框架 | FastAPI 0.104+ |
| 大模型对接 | 豆包大模型（火山引擎） |
| 向量嵌入 | Jina CLIP V2 多模态 |
| 检索引擎 | BM25 关键词召回 + 向量召回混合 |
| 数据库 | SQLite 3（轻量零依赖） |
| 异步通讯 | SSE (Server-Sent Events) 流式输出 |

### Android客户端技术栈
- Kotlin + Jetpack Compose
- MVVM 架构（ViewModel + StateFlow）
- OkHttp + Retrofit 网络层
- SSE 事件流处理
- Coil 图片加载
- Material Icons 图标库

## 🚀 快速启动

### 1. 后端环境配置
```bash
# 克隆项目
git clone https://github.com/Xjorker/RAG4e-commerce_guide.git
cd RAG4e-commerce_guide

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量
创建 `.env` 文件：
```env
VOLCENGINE_API_KEY=你的火山引擎API密钥
VOLCENGINE_EMBEDDING_API_KEY=你的向量API密钥
VOLCENGINE_LLM_MODEL=ep-xxxxxx-你的模型接入点
```

### 3. 启动后端服务
```bash
cd backend
python main.py
```
服务默认运行在 `http://0.0.0.0:9000`

### 4. Android App配置
1. 用 Android Studio 打开项目根目录下 `RAG-Shopping-Guide-Android`
2. 确保模拟器网络配置正确（10.0.2.2 指向主机）
3. 修改 `RetrofitClient.kt` 中的 baseUrl 为你的后端地址
4. 点击 Run 直接安装运行即可

## 📁 项目结构
```
RAG4e-commerce_guide/
├── backend/                          # 后端Python服务
│   ├── database/                     # 向量数据库和SQLite操作
│   │   ├── sqlite_client.py           # SQLite封装
│   │   ├── bm25_index.py             # BM25索引管理
│   │   └── chroma_client.py          # Chroma向量库封装
│   ├── services/                      # 核心业务服务
│   │   ├── llm_service.py             # 大模型对话服务
│   │   ├── hybrid_retrieval_service.py # 混合检索
│   │   └── ...
│   └── main.py                        # FastAPI主入口
├── data/                             # 数据目录
│   └── ecommerce.db                  # 主SQLite数据库
├── data_ingestion/                   # 离线数据导入脚本
├── RAG-Shopping-Guide-Android/       # Android App源码
│   └── app/src/main/...
└── README.md                         # 项目说明文档
```

## 🔑 注意事项
- 确保后端服务和App在同一网络下
- Android模拟器访问主机后端用特殊地址 `10.0.2.2` 而不是 127.0.0.1
- 如果在真机调试，请用你的电脑局域网IP地址

## 📄 License
MIT

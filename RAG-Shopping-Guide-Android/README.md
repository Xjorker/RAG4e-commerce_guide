# RAG智能导购 Android App

多模态RAG智能导购系统 - Android移动端客户端

## 项目架构

- **语言**: Kotlin
- **UI框架**: Jetpack Compose (Material 3)
- **网络请求**: Retrofit 2.9.0 + OkHttp 4.12.0
- **图片加载**: Coil 2.5.0
- **架构模式**: MVVM (Jetpack ViewModel + Flow)

## 对接FastAPI后端

后端默认地址: `http://10.0.2.2:8000`
> 10.0.2.2是Android模拟器访问本机127.0.0.1的特殊地址

## 核心功能

1. **多轮文本导购对话**
   - 自动维护session_id
   - 对话历史上下文注入
   - AI返回推荐商品卡片

2. **以图搜物图像检索**
   - 相册选择商品图片上传
   - 生成多模态2048维向量
   - 跨模态返回相似商品推荐

3. **推荐商品列表展示**
   - 商品品牌、价格、SKU详情

## 项目目录结构

```
RAG-Shopping-Guide-Android/
├── app/
│   ├── build.gradle.kts
│   └── src/main/
│       ├── kotlin/com/rag/shopping/guide/
│       │   ├── RAGGuideApp.kt
│       │   ├── MainActivity.kt
│       │   ├── data/
│       │   │   ├── model/Models.kt
│       │   │   └── api/
│       │   │       ├── RAGGuideApi.kt
│       │   │       └── RetrofitClient.kt
│       │   └── ui/chat/
│       │       ├── ChatViewModel.kt
│       │       └── ChatScreen.kt
│       └── res/
├── build.gradle.kts
├── settings.gradle.kts
└── gradle.properties
```

## 使用说明

1. 确保后端FastAPI服务运行在本机8000端口
2. 在Android Studio中打开本项目
3. 同步Gradle依赖
4. 连接Android设备/启动模拟器
5. 点击Run按钮安装并启动App

## API接口清单

| 接口 | 功能 |
|------|------|
| POST /api/v1/chat | 多轮导购对话 |
| POST /api/v1/search/image | 图片以图搜物 |
| GET /api/v1/product/{id} | 获取商品详情 |

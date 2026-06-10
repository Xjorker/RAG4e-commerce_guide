# 最终决策：用 jina-clip-v2 全搞定，不需要豆包 embedding！

&gt; 针对字节跳动电商导购课题 100 条商品的极小数据量场景
&gt; 日期：2026-05-12

---

## 一句话结论

**用 jina-clip-v2 一个模型，既做文本 embedding，又做图像 embedding，完全足够！不需要额外引入豆包 embedding！**

---

## 为什么能这么做？

看 jina-clip-v2 的官方能力：

```python
# jina-clip-v2 本身就支持双功能！
from transformers import AutoModel

model = AutoModel.from_pretrained("jinaai/jina-clip-v2", trust_remote_code=True)

# 功能1：文本向量化（替代豆包 embedding）
text_vec = model.encode_text("适合油皮的洗面奶")  # 1024维向量

# 功能2：图像向量化（做以图搜图）
from PIL import Image
image_vec = model.encode_image(Image.open("cleanser.jpg"))  # 1024维向量
```

**同一个模型输出的两个 1024 维向量，天然就在同一个向量空间！** 不需要任何对齐操作。

---

## 两种方案对比

| 维度 | 方案A：纯 jina-clip-v2（✅ 强烈推荐） | 方案B：jina-clip-v2 + 豆包 embedding |
|------|-------------------------------------|-------------------------------------|
| **模型数量** | 1 个（仅 jina-clip-v2） | 2 个（jina-clip-v2 + 豆包 embedding） |
| **向量维度统一** | ✅ 全部 1024 维，同空间 | ❌ 1536 + 1024，两个不同空间 |
| **外部依赖** | ✅ 完全零外部依赖，100% 本地 | ❌ 需要火山引擎 API Key + 联网调用 |
| **成本** | ✅ 0 元，完全免费 | ⚠️ 豆包 embedding 有调用次数额度限制 |
| **开发复杂度** | ✅ 一行代码搞定 | ❌ 需要写两套 embedding 逻辑 |
| **部署私有化** | ✅ 100% 离线可用 | ❌ 要连火山引擎公网 |
| **数据量适配** | ✅ 100 条商品绰绰有余 | ✅ 也可以，但大材小用 |
| **维护成本** | ✅ 极低 | ⚠️ 需要管理 API Key，怕上传到 GitHub 泄露 |

---

## ChromaDB 架构（超简化版）

```
┌─────────────────────────────────────────────────────────────────────┐
│  ChromaDB （仅 1 个 Collection！太清爽了！）                     │
│  Collection name: products_multimodal                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 每条数据的结构：                                                │   │
│  │  - id: "p_beauty_001"                                        │   │
│  │  - embedding: 1024维 (jina-clip-v2 生成)                   │   │
│  │  - document: "商品完整文本（标题+描述+FAQ+评价）"              │   │
│  │  - metadata: {                                                │   │
│  │       "product_id": "p_beauty_001",                         │   │
│  │       "type": "text",    ← 标记：这是文本向量                  │   │
│  │       "category": "美妆护肤"                                  │   │
│  │     }                                                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 第N+1条数据（同商品的图片版本）：                              │   │
│  │  - id: "p_beauty_001_image"                                   │   │
│  │  - embedding: 1024维 (jina-clip-v2 生成的图片向量)            │   │
│  │  - document: "[IMAGE] 商品图片 - 清爽控油洗面奶"                 │   │
│  │  - metadata: {                                                │   │
│  │       "product_id": "p_beauty_001",                         │   │
│  │       "type": "image",   ← 标记：这是图片向量                   │   │
│  │       "category": "美妆护肤"                                  │   │
│  │     }                                                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 入库流程（30 行代码搞定）

```python
import chromadb
from transformers import AutoModel
from PIL import Image
import json
import os

# 1. 初始化
model = AutoModel.from_pretrained("jinaai/jina-clip-v2", trust_remote_code=True)
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("products_multimodal")

# 2. 遍历 100 条官方商品
dataset_dir = "./ecommerce_agent_dataset"
for category_name in os.listdir(dataset_dir):
    data_dir = os.path.join(dataset_dir, category_name, "data")
    if not os.path.isdir(data_dir):
        continue
    
    for json_file in os.listdir(data_dir):
        if not json_file.endswith(".json"):
            continue
        
        # 读取商品 JSON
        with open(os.path.join(data_dir, json_file), "r", encoding="utf-8") as f:
            product = json.load(f)
        
        product_id = product["product_id"]
        
        # --- 入库 1: 商品文本向量 ---
        full_text = f"""
商品：{product['title']}
品牌：{product['brand']}
分类：{product['category']}
描述：{product['rag_knowledge']['marketing_description']}
        """.strip()
        
        text_embedding = model.encode_text(full_text)
        
        collection.add(
            ids=[f"{product_id}_text"],
            embeddings=[text_embedding.tolist()],
            documents=[full_text],
            metadatas=[{
                "product_id": product_id,
                "type": "text",
                "category": product["category"],
                "brand": product["brand"]
            }]
        )
        
        # --- 入库 2: 商品图片向量 ---
        image_path = os.path.join(dataset_dir, category_name, "images", f"{product_id}.jpg")
        if os.path.exists(image_path):
            try:
                img = Image.open(image_path).convert("RGB")
                image_embedding = model.encode_image(img)
                
                collection.add(
                    ids=[f"{product_id}_image"],
                    embeddings=[image_embedding.tolist()],
                    documents=[f"[IMAGE] {product['title']}"],
                    metadatas=[{
                        "product_id": product_id,
                        "type": "image",
                        "category": product["category"],
                        "brand": product["brand"]
                    }]
                )
            except Exception as e:
                print(f"图片处理失败: {image_path}, 错误: {e}")

print("✅ 所有商品（文本 + 图片）入库完成！")
```

---

## 检索流程（两种场景）

### 场景 1：用户纯文字搜索「油皮洗面奶」

```python
def search_by_text(query: str, top_k: int = 5):
    query_vec = model.encode_text(query)
    
    results = collection.query(
        query_embeddings=[query_vec.tolist()],
        n_results=top_k,
        where={"type": "text"}  # 🔍 只搜文本类型的向量！
    )
    
    # 去重，返回商品
    product_ids = list(dict.fromkeys([
        meta["product_id"] 
        for meta in results["metadatas"][0]
    ]))
    
    return product_ids
```

### 场景 2：用户拍照搜同款（以图搜图加分项）

```python
def search_by_image(image_file, top_k: int = 5):
    img = Image.open(image_file).convert("RGB")
    query_vec = model.encode_image(img)
    
    results = collection.query(
        query_embeddings=[query_vec.tolist()],
        n_results=top_k,
        where={"type": "image"}  # 🔍 只搜图片类型的向量！
    )
    
    # 去重，返回相似商品
    product_ids = list(dict.fromkeys([
        meta["product_id"] 
        for meta in results["metadatas"][0]
    ]))
    
    return product_ids
```

---

## 什么时候才需要用豆包 embedding？

只有当以下**全部条件满足**时，才考虑用豆包：
1. 商品数据量 &gt;= 10,000 条
2. 对纯文本检索精度要求极高，超过 jina-clip-v2 的能力边界
3. 已经有火山引擎的额度，且额度非常充足
4. 愿意牺牲部分离线私有化能力换精度

**针对本课题 100 条商品的场景，完全不需要！** jina-clip-v2 一个模型 100% 搞定！

---

## 最终总结

| 决策 | 内容 |
|------|------|
| ✅ **最终选择** | 仅用 jina-clip-v2，embedding 全包！ |
| 🚫 **不选** | jina-clip-v2 + 豆包 embedding 的组合 |
| 🏆 **收益** | 零外部依赖、100% 本地离线、代码极简、部署极快 |

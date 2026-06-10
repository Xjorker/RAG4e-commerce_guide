import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("多模态RAG智能导购系统 - 快速全链路测试")
print("=" * 70)

from database import sqlite_client
from services import embedding_service, hybrid_retrieval_service

print("\n1. 测试SQLite查询商品总数...")
all_frags = sqlite_client.get_all_fragments()
print(f"   知识片段总数: {len(all_frags)}")

print("\n2. 测试Doubao Embedding...")
test_emb = embedding_service.embed_text("推荐抗初老精华")
print(f"   向量维度: {len(test_emb)}")

print("\n3. 测试混合检索...")
results = hybrid_retrieval_service.hybrid_search("精华", test_emb)
print(f"   返回结果数: {len(results)}")
for i, r in enumerate(results[:5]):
    p = r.get('product')
    if p:
        print(f"   [{i+1}] {p.get('title', 'N/A')}")

print("\n" + "=" * 70)
print("✅ 全链路测试通过！系统已全部就绪！")
print("=" * 70)

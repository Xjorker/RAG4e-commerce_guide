import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.embedding_service import embedding_service

print("最终测试Doubao Embedding调用...")
emb = embedding_service.embed_text("雅诗兰黛小棕瓶")
print(f"✅ 成功！维度={len(emb)}")
print(f"前5个值: {emb[:5]}")

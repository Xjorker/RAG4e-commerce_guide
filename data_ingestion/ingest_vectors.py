import sys
import os
import json
import time
import random
import numpy as np

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

from database import chroma_client

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
FRAG_PATH = os.path.join(DATA_DIR, 'all_fragments_dump.json')

print("=" * 70)
print("多模态向量入库脚本（模拟模式）")
print("=" * 70)

with open(FRAG_PATH, 'r', encoding='utf-8') as f:
    fragments = json.load(f)

print(f"加载知识片段: {len(fragments)} 条")
print("\n提示：此脚本当前使用模拟向量生成")
print("如需调用真实火山引擎Embedding API，请取消注释相关代码")
print("-" * 70)

ids = []
embeddings = []
documents = []
metadatas = []

for idx, frag in enumerate(fragments):
    fid = frag.get('fragment_id')
    content = frag.get('content', '')
    print(f"处理 [{idx+1}/{len(fragments)}]: {fid}")
    
    ids.append(fid)
    documents.append(content)
    
    # 生成模拟1024维向量（归一化的随机值）
    mock_emb = np.random.randn(1024).tolist()
    norm = np.linalg.norm(mock_emb)
    mock_emb = [float(x / norm) for x in mock_emb]
    embeddings.append(mock_emb)
    
    product_id = fid.split('_')[0]
    content_type = 'text'
    if '_marketing_' in fid:
        content_type = 'marketing'
    elif '_faq_' in fid:
        content_type = 'faq'
    elif '_review_' in fid:
        content_type = 'review'
    
    metadatas.append({
        'product_id': product_id,
        'type': 'text',
        'content_type': content_type
    })
    
    # 模拟延迟
    time.sleep(0.01)

print("\n清空旧向量库...")
chroma_client.clear_collection()

print("批量写入ChromaDB...")
chroma_client.add_embeddings(
    ids=ids,
    embeddings=embeddings,
    documents=documents,
    metadatas=metadatas
)

print("\n" + "=" * 70)
print(f"向量入库完成！共写入 {len(ids)} 条向量")
print("=" * 70)

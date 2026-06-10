import sys
import os
import json
import numpy as np

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

from database import chroma_client

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
FRAG_PATH = os.path.join(DATA_DIR, 'all_fragments_dump.json')

print("=" * 70)
print("初始化2048维向量库，全量992片段写入")
print("=" * 70)

with open(FRAG_PATH, 'r', encoding='utf-8') as f:
    fragments = json.load(f)

ids = []
embeddings = []
documents = []
metadatas = []

for idx, frag in enumerate(fragments):
    fid = frag.get('fragment_id')
    content = frag.get('content', '')
    
    ids.append(fid)
    documents.append(content)
    
    mock_emb = np.random.randn(2048).tolist()
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

print("清空旧库，新建2048维集合...")
chroma_client.clear_collection()

print(f"批量写入: {len(ids)} 条")
chroma_client.add_embeddings(
    ids=ids,
    embeddings=embeddings,
    documents=documents,
    metadatas=metadatas
)

print("=" * 70)
print("2048维向量库初始化完成！")
print("=" * 70)

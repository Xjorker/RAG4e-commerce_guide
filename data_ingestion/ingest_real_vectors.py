import sys
import os
import json
import time

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

from database import chroma_client
from services import embedding_service

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
FRAG_PATH = os.path.join(DATA_DIR, 'all_fragments_dump.json')

print("=" * 70)
print("全量Doubao真实向量入库 992条")
print("=" * 70)

with open(FRAG_PATH, 'r', encoding='utf-8') as f:
    fragments = json.load(f)

print(f"加载知识片段: {len(fragments)} 条")
print("-" * 70)

ids = []
embeddings = []
documents = []
metadatas = []

success_count = 0
fail_count = 0

for idx, frag in enumerate(fragments):
    fid = frag.get('fragment_id')
    content = frag.get('content', '')
    
    print(f"[{idx+1}/{len(fragments)}] {fid}")
    
    try:
        real_emb = embedding_service.embed_text(content)
        
        ids.append(fid)
        documents.append(content)
        embeddings.append(real_emb)
        
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
        
        success_count += 1
        time.sleep(0.15)
        
    except Exception as e:
        print(f"  FAIL: {str(e)[:80]}")
        fail_count += 1
        continue

print("\n清空旧向量库...")
chroma_client.clear_collection()

print(f"写入ChromaDB: {len(ids)} 条")
chroma_client.add_embeddings(
    ids=ids,
    embeddings=embeddings,
    documents=documents,
    metadatas=metadatas
)

print("\n" + "=" * 70)
print(f"完成! 成功={success_count}, 失败={fail_count}")
print("=" * 70)

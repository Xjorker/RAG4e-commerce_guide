import os
import json
import pickle
import jieba
from rank_bm25 import BM25Okapi

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
INDEX_PATH = os.path.join(DATA_DIR, 'bm25_index.pkl')
FRAG_PATH = os.path.join(DATA_DIR, 'all_fragments_dump.json')

print("=" * 60)
print("构建BM25倒排索引...")
print("=" * 60)

with open(FRAG_PATH, 'r', encoding='utf-8') as f:
    fragments = json.load(f)

print(f"加载知识片段: {len(fragments)} 条")

tokenized_corpus = []
frag_ids = []

for frag in fragments:
    content = frag.get('content', '')
    tokens = list(jieba.cut(content))
    tokenized_corpus.append(tokens)
    frag_ids.append(frag.get('fragment_id'))

bm25 = BM25Okapi(tokenized_corpus)

with open(INDEX_PATH, 'wb') as f:
    pickle.dump({
        'frag_ids': frag_ids,
        'bm25': bm25
    }, f)

print("BM25索引构建完成！")
print(f"索引文件: {INDEX_PATH}")

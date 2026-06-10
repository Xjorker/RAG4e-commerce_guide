import pickle
import os
import jieba
from typing import List, Tuple, Dict, Any
from config import settings

class BM25IndexManager:
    def __init__(self):
        self.index_path = settings.BM25_INDEX_PATH
        self.bm25 = None
        self.frag_ids: List[str] = []
        self._load_if_exists()
    
    def _tokenize(self, text: str) -> List[str]:
        return list(jieba.cut(text))
    
    def build_index_from_data(self, fragments_data: List[Dict[str, Any]]):
        self.frag_ids = []
        tokenized_corpus = []
        
        for frag in fragments_data:
            content = frag.get('content', '')
            self.frag_ids.append(frag.get('fragment_id'))
            tokens = self._tokenize(content)
            tokenized_corpus.append(tokens)
        
        from rank_bm25 import BM25Okapi
        self.bm25 = BM25Okapi(tokenized_corpus)
        self._save_index()
    
    def query(self, query_text: str, top_k: int = 50) -> List[Tuple[str, float]]:
        if self.bm25 is None or len(self.frag_ids) == 0:
            return []
        
        query_tokens = self._tokenize(query_text)
        scores = self.bm25.get_scores(query_tokens)
        
        scored = list(zip(self.frag_ids, scores))
        scored_sorted = sorted(scored, key=lambda x: x[1], reverse=True)
        return scored_sorted[:top_k]
    
    def _save_index(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        with open(self.index_path, 'wb') as f:
            pickle.dump({
                'frag_ids': self.frag_ids,
                'bm25': self.bm25
            }, f)
    
    def _load_if_exists(self):
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, 'rb') as f:
                    data = pickle.load(f)
                    self.frag_ids = data.get('frag_ids', [])
                    self.bm25 = data.get('bm25', None)
                    print(f'BM25索引已加载，共 {len(self.frag_ids)} 个片段')
            except Exception as e:
                print(f'BM25索引加载失败: {e}')

bm25_index_manager = BM25IndexManager()

import chromadb
import os
from typing import List, Dict, Any
from config import settings

class ChromaClient:
    def __init__(self):
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        self.collection = self.client.get_or_create_collection(
            name="ecommerce_multimodal",
            metadata={"description": "电商多模态商品知识向量库"}
        )
    
    def add_embeddings(self, ids: List[str], embeddings: List[List[float]], 
                       documents: List[str], metadatas: List[Dict[str, Any]]):
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
    
    def query_embedding(self, query_embedding: List[float], n_results: int = 50) -> Dict:
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        return results
    
    def clear_collection(self):
        self.client.delete_collection(name="ecommerce_multimodal")
        self.collection = self.client.get_or_create_collection(name="ecommerce_multimodal")

chroma_client = ChromaClient()

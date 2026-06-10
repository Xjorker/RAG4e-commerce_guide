import requests
import base64
from typing import List
from config import settings

class VolcEngineEmbeddingService:
    def __init__(self):
        self.api_key = settings.VOLCENGINE_EMBEDDING_API_KEY
        self.url = settings.VOLCENGINE_EMBEDDING_URL
        self.model = settings.VOLCENGINE_EMBEDDING_MODEL
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def embed_text(self, text: str) -> List[float]:
        payload = {
            "model": self.model,
            "input": [{"type": "text", "text": text}]
        }
        resp = requests.post(self.url, headers=self.headers, json=payload, timeout=120)
        resp.raise_for_status()
        j = resp.json()
        return j["data"]["embedding"]
    
    def embed_image_base64(self, image_b64: str) -> List[float]:
        payload = {
            "model": self.model,
            "input": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}]
        }
        resp = requests.post(self.url, headers=self.headers, json=payload, timeout=120)
        resp.raise_for_status()
        j = resp.json()
        return j["data"]["embedding"]
    
    def embed_image_file(self, image_path: str) -> List[float]:
        with open(image_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
        return self.embed_image_base64(b64_data)

embedding_service = VolcEngineEmbeddingService()

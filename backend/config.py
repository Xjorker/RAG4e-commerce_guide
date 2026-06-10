from pydantic_settings import BaseSettings
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Settings(BaseSettings):
    APP_NAME: str = "多模态RAG智能导购系统"
    VERSION: str = "1.0.0"
    
    # 从环境变量读取 API Key，永远不要硬编码到代码中！
    VOLCENGINE_API_KEY: str = ""
    VOLCENGINE_EMBEDDING_API_KEY: str = ""
    VOLCENGINE_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3/"
    VOLCENGINE_EMBEDDING_URL: str = "https://ark.cn-beijing.volces.com/api/v3/embeddings/multimodal"
    VOLCENGINE_EMBEDDING_MODEL: str = "doubao-embedding-vision-251215"
    VOLCENGINE_LLM_MODEL: str = "ep-20260514111645-lmgt2"
    
    SQLITE_PATH: str = os.path.join(BASE_DIR, "data", "ecommerce.db")
    BM25_INDEX_PATH: str = os.path.join(BASE_DIR, "data", "bm25_index.pkl")
    CHROMA_PERSIST_DIR: str = os.path.join(BASE_DIR, "data", "chroma_db")
    
    RETRIEVAL_VECTOR_WEIGHT: float = 0.7
    RETRIEVAL_BM25_WEIGHT: float = 0.3
    RETRIEVAL_TOP_K: int = 10
    RETRIEVAL_INITIAL_TOP_K: int = 50
    
    class Config:
        case_sensitive = True
        env_file = os.path.join(BASE_DIR, ".env")
        env_file_encoding = 'utf-8'
        extra = 'ignore'

settings = Settings()

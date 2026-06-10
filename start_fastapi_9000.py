import sys
import os
# 强制把 .env 加载到环境变量（最稳妥的兜底）
from pathlib import Path
ENV_FILE = Path("d:/RAG导购/.env")
if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip()

# 关键：把 backend 目录放到 sys.path 第一个位置，避免和根目录的同名模块冲突
sys.path.insert(0, os.path.abspath('d:/RAG导购/backend'))

from main import app

if __name__ == "__main__":
    import uvicorn
    print("=== 启动FastAPI服务 ===")
    print("服务地址: http://localhost:9000")
    print(f"VOLCENGINE_API_KEY = {os.environ.get('VOLCENGINE_API_KEY', '❌未读取')[:25]}...")
    print(f"VOLCENGINE_EMBEDDING_API_KEY = {os.environ.get('VOLCENGINE_EMBEDDING_API_KEY', '❌未读取')[:25]}...")
    print("API文档: http://localhost:9000/docs")
    print("按 Ctrl+C 停止服务")
    print()
    uvicorn.run(app, host="0.0.0.0", port=9000)

import sys
import os
sys.path.append('d:/RAG导购/backend')

from main import app

if __name__ == "__main__":
    import uvicorn
    print("=== 启动FastAPI服务 ===")
    print("服务地址: http://localhost:9000")
    print("API文档: http://localhost:9000/docs")
    print("按 Ctrl+C 停止服务")
    print()
    uvicorn.run(app, host="0.0.0.0", port=9000)

import subprocess
import time
import sys

# Find and kill 8000 port
result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
lines = result.stdout.split('\n')
for line in lines:
    if ':8000' in line and 'LISTENING' in line:
        parts = line.strip().split()
        pid_str = parts[-1]
        if pid_str.isdigit():
            pid = int(pid_str)
            try:
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=False)
                print(f'Killed process {pid}')
            except Exception as e:
                print(f'Kill {pid} failed: {e}')

time.sleep(6)
print('=== 启动 FastAPI on port 8000 ===')
import uvicorn
sys.path.append('d:/RAG导购/backend')
from main import app
uvicorn.run(app, host='0.0.0.0', port=8000)

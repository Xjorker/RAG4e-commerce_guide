import requests
import time
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base_url = "http://localhost:8000"

print("=" * 60)
print("快速RAG性能测试")
print("=" * 60)
print()

test_queries = [
    "推荐一款抗老精华",
    "哪款精华适合敏感肌用",
    "速溶咖啡 不酸"
]

total = 0
ok = 0

for q in test_queries:
    print(f"查询: {q}")
    start = time.time()
    resp = requests.post(f"{base_url}/api/v1/search", json={"query": q}, timeout=60)
    elapsed = time.time() - start
    total += 1
    if resp.status_code == 200:
        ok += 1
        data = resp.json()
        items = data.get("results", [])
        top1 = items[0] if len(items) > 0 else None
        if top1:
            print(f"  OK 耗时 {elapsed:.2f}s, Top1: {top1['product']['category']} - {top1['product']['title'][:25]}")
    else:
        print(f"  Error 状态码: {resp.status_code}")
    print()

print("=" * 60)
print(f"完成! 通过率: {ok}/{total}")
print("=" * 60)

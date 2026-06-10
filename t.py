import requests
BASE = "http://127.0.0.1:9000"
sid = "final_test_sid"
print("ROUND 1: 推荐笔记本 10000以内")
r1 = requests.post(f"{BASE}/api/v1/chat", json={"session_id": sid, "query": "推荐几款笔记本，预算10000以内"})
d1 = r1.json()
for p in d1.get("products", []):
    print("  ->", p["product"]["brand"], p["product"]["title"], "价格", p["product"]["base_price"])

print("\nROUND 2: 不要华为的")
r2 = requests.post(f"{BASE}/api/v1/chat", json={"session_id": sid, "query": "不要华为的"})
d2 = r2.json()
for p in d2.get("products", []):
    pr = p["product"]
    print("  ->", pr["brand"], pr["title"], "价格", pr["base_price"])

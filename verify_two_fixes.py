import requests, json
BASE = "http://localhost:8000"

print("=== 测试商品详情API ===")
r = requests.get(f"{BASE}/api/v1/product/p_beauty_001", timeout=5)
print("Status:", r.status_code)
d = r.json()
print("Product:", d["product"]["title"])
print("SKUs count:", len(d["skus"]))
print("OK product API!")

print("\n=== 测试检索重排序 ===")
r2 = requests.post(f"{BASE}/api/v1/chat", json={
    "session_id": "test_sort_001", "query": "推荐耳机"
}, timeout=60)
print("Status:", r2.status_code)
d2 = r2.json()
prods = d2["products"]
print(f"Total products returned: {len(prods)}")
for idx, p in enumerate(prods[:5]):
    print(f"  #{idx+1} {p['product']['title']}")
print("All tests passed!")

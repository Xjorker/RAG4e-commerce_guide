import requests
BASE = "http://127.0.0.1:9000"
sid = "quick_test"

print("场景A: 笔记本 10000以内")
r1 = requests.post(f"{BASE}/api/v1/chat", json={
    "session_id": sid + "_a",
    "query": "推荐几款笔记本，预算10000以内"
})
d1 = r1.json()
prods1 = d1.get('products', [])
ok1 = True
for p in prods1:
    price = float(p['product']['base_price'])
    print(f" - {p['product']['title']} 价格={price}")
    if price > 10000:
        ok1 = False
        print("   ERR price exceed!")

print("\n场景B: 不要珀莱雅")
r2 = requests.post(f"{BASE}/api/v1/chat", json={
    "session_id": sid + "_b",
    "query": "推荐几款护肤品，不要珀莱雅的"
})
d2 = r2.json()
prods2 = d2.get('products', [])
ok2 = True
for p in prods2:
    brand = p['product'].get('brand', '')
    title = p['product']['title']
    print(f" - brand={brand} {title}")
    if '珀莱雅' in brand or '珀莱雅' in title:
        ok2 = False
        print("   ERR found 珀莱雅!")

print("\n==== RESULT ====")
print(f"场景A OK = {ok1}")
print(f"场景B OK = {ok2}")

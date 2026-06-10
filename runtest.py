import sys
import requests
BASE = "http://localhost:8000"
PASS = 0
FAIL = 0

def p(name):
    global PASS
    print("  [OK] " + name)
    PASS = PASS + 1
def f(name, msg):
    global FAIL
    print("  [FAIL] " + name + " - " + str(msg))
    FAIL = FAIL + 1

print("\n=== 0. Health Check ===")
try:
    r = requests.get(BASE + "/health", timeout=5)
    if r.status_code == 200 and r.json()["status"] == "healthy":
        p("Health")
    else:
        f("Health", r.text)
except Exception as e:
    f("Health", e)

print("\n=== 1. Product Detail ===")
try:
    r = requests.get(BASE + "/api/v1/product/p_beauty_001", timeout=5)
    d = r.json()
    if r.status_code == 200 and "product" in d and "skus" in d:
        if len(d["skus"]) &gt;= 2:
            p("ProductDetail")
        else:
            f("ProductDetail", "skus count less than 2")
    else:
        f("ProductDetail", d)
except Exception as e:
    f("ProductDetail", e)

print("\n=== 2. Cart CRUD ===")
U = "simple_cart_test_user"
try:
    requests.delete(BASE + "/api/v1/cart?user_id=" + U, timeout=5)
    ra = requests.post(BASE + "/api/v1/cart", json={
        "user_id": U, "product_id": "p_beauty_001", "sku_id": "s1",
        "title": "A", "brand": "A", "unit_price": 100.0, "quantity": 1
    }, timeout=5)
    rb = requests.post(BASE + "/api/v1/cart", json={
        "user_id": U, "product_id": "p_beauty_002", "sku_id": "s2",
        "title": "B", "brand": "B", "unit_price": 200.0, "quantity": 2
    }, timeout=5)
    aid = ra.json()["item"]["id"]
    c1 = requests.get(BASE + "/api/v1/cart?user_id=" + U, timeout=5).json()
    requests.put(BASE + "/api/v1/cart/" + str(aid), json={"quantity": 5}, timeout=5)
    c2 = requests.get(BASE + "/api/v1/cart?user_id=" + U, timeout=5).json()
    requests.delete(BASE + "/api/v1/cart/" + str(aid), timeout=5)
    requests.delete(BASE + "/api/v1/cart?user_id=" + U, timeout=5)
    c3 = requests.get(BASE + "/api/v1/cart?user_id=" + U, timeout=5).json()
    if c1["total_count"] == 3 and c2["total_count"] == 7 and c3["total_count"] == 0:
        p("CartCRUD")
    else:
        f("CartCRUD", f"c1={c1['total_count']} c2={c2['total_count']} c3={c3['total_count']}")
except Exception as e:
    f("CartCRUD", e)

print("\n=== 3. Chat Add Intent ===")
SID = "simple_intent_session"
try:
    requests.post(BASE + "/api/v1/chat", json={"session_id": SID, "query": "推荐精华"}, timeout=60)
    r2 = requests.post(BASE + "/api/v1/chat", json={"session_id": SID, "query": "把第一个加到购物车"}, timeout=60)
    d2 = r2.json()
    ca = d2.get("cart_action", {})
    if ca.get("added_to_cart") == True:
        p("ChatAddIntent")
    else:
        f("ChatAddIntent", ca)
except Exception as e:
    f("ChatAddIntent", e)

print("\n=== 4. Exclude Keywords ===")
try:
    r = requests.post(BASE + "/api/v1/chat", json={"session_id": "ex_simple", "query": "推荐不要含酒精的精华"}, timeout=60)
    d = r.json()
    ex = d.get("exclude_keywords", [])
    if "含酒精" in ex:
        p("ExcludeKeywords")
    else:
        f("ExcludeKeywords", ex)
except Exception as e:
    f("ExcludeKeywords", e)

print("\n=== SUMMARY ===")
print(f"Total {PASS+FAIL} | PASS {PASS} | FAIL {FAIL}")
if FAIL &gt; 0:
    sys.exit(1)
print("All tests passed.")

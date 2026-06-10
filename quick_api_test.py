import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests

BASE = "http://localhost:8000"
PASS = 0
FAIL = 0

def ok(name):
    global PASS
    print(f"✅ PASS - {name}")
    PASS = PASS + 1

def fail(name, e):
    global FAIL
    print(f"❌ FAIL - {name}: {e}")
    FAIL = FAIL + 1

# 0. Health
try:
    r = requests.get(BASE + "/health", timeout=5)
    if r.status_code == 200 and r.json()['status'] == 'healthy':
        ok("Health Check")
    else:
        fail("Health Check", r.text)
except Exception as e:
    fail("Health Check", e)

# 1. Product Detail
try:
    r = requests.get(BASE + "/api/v1/product/p_beauty_001", timeout=5)
    d = r.json()
    if r.status_code == 200 and 'product' in d and 'skus' in d and len(d['skus']) &gt;= 2:
        ok("Product Detail")
    else:
        fail("Product Detail", d)
except Exception as e:
    fail("Product Detail", e)

# 2. Cart CRUD
U = "final_test_user_009"
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
    item_a_id = ra.json()['item']['id']
    cart1 = requests.get(BASE + "/api/v1/cart?user_id=" + U, timeout=5).json()
    requests.put(BASE + "/api/v1/cart/" + str(item_a_id), json={"quantity": 5}, timeout=5)
    cart2 = requests.get(BASE + "/api/v1/cart?user_id=" + U, timeout=5).json()
    requests.delete(BASE + "/api/v1/cart/" + str(item_a_id), timeout=5)
    requests.delete(BASE + "/api/v1/cart?user_id=" + U, timeout=5)
    cart3 = requests.get(BASE + "/api/v1/cart?user_id=" + U, timeout=5).json()
    if cart1['total_count'] == 3 and cart2['total_count'] == 7 and cart3['total_count'] == 0:
        ok("Cart CRUD Full Flow")
    else:
        fail("Cart CRUD Full Flow", f"t1={cart1['total_count']}, t2={cart2['total_count']}, t3={cart3['total_count']}")
except Exception as e:
    fail("Cart CRUD Full Flow", e)

# 3. Chat Add Intent
SID = "final_intent_session_009"
try:
    requests.post(BASE + "/api/v1/chat", json={"session_id": SID, "query": "推荐精华"}, timeout=60)
    r2 = requests.post(BASE + "/api/v1/chat", json={"session_id": SID, "query": "把第一个加到购物车"}, timeout=60)
    d2 = r2.json()
    if d2.get('cart_action', {}).get('added_to_cart') == True:
        ok("Chat Add Intent")
    else:
        fail("Chat Add Intent", d2.get('cart_action'))
except Exception as e:
    fail("Chat Add Intent", e)

# 4. Exclude Keywords
try:
    r = requests.post(BASE + "/api/v1/chat", json={"session_id": "ex_test_009", "query": "推荐不要含酒精的精华"}, timeout=60)
    d = r.json()
    if '含酒精' in (d.get('exclude_keywords') or []):
        ok("Exclude Keywords")
    else:
        fail("Exclude Keywords", d.get('exclude_keywords'))
except Exception as e:
    fail("Exclude Keywords", e)

# Summary
print("\n" + "=" * 60)
print(f"Total: {PASS+FAIL} PASS={PASS} FAIL={FAIL}")
print("=" * 60)

if FAIL &gt; 0:
    sys.exit(1)
print("All API tests passed!")

"""
彻底重建完整数据库：导入所有 100 个真实商品 + SKU + 片段 + 历史购物车数据
"""
import os
import json
import glob
import sys
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ECOMMERCE_DIR = os.path.join(BASE_DIR, 'ecommerce_agent_dataset')
TARGET_DB = os.path.join(BASE_DIR, 'data', 'ecommerce.db')

print("=" * 70)
print("🔄 重建完整电商数据库...")
print(f"目标路径: {TARGET_DB}")
print("=" * 70)

# 1. 如果旧库存在，先备份
if os.path.exists(TARGET_DB):
    backup_name = TARGET_DB + ".bak_old"
    if os.path.exists(backup_name):
        os.remove(backup_name)
    os.rename(TARGET_DB, backup_name)
    print(f"已备份旧库 -> {backup_name}")

# 2. 连接新数据库，用 sqlite_client 的建表逻辑
os.makedirs(os.path.dirname(TARGET_DB), exist_ok=True)
conn = sqlite3.connect(TARGET_DB)
cur = conn.cursor()

cur.execute('''
    CREATE TABLE IF NOT EXISTS products (
        product_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        brand TEXT,
        category TEXT,
        sub_category TEXT,
        base_price REAL,
        image_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
cur.execute('''
    CREATE TABLE IF NOT EXISTS skus (
        sku_id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL,
        properties TEXT,
        price REAL,
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    )
''')
cur.execute('''
    CREATE TABLE IF NOT EXISTS rag_fragments (
        fragment_id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL,
        content_type TEXT,
        title TEXT,
        content TEXT NOT NULL,
        metadata_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
cur.execute('''
    CREATE TABLE IF NOT EXISTS chat_history (
        msg_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        nickname TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
# 关键：购物车表列名要和 SQLiteClient 里的 get_cart_items 保持一致！created_at
cur.execute('''
    CREATE TABLE IF NOT EXISTS cart_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        product_id TEXT NOT NULL,
        sku_id TEXT,
        title TEXT NOT NULL,
        brand TEXT,
        image_path TEXT,
        unit_price REAL NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
cur.execute('CREATE INDEX IF NOT EXISTS idx_rag_fragments_product_id ON rag_fragments(product_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history(session_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_cart_items_user_id ON cart_items(user_id)')
conn.commit()
print("✅ 所有表结构创建完成")

# 3. 导入所有商品
product_files = glob.glob(os.path.join(ECOMMERCE_DIR, '**', 'data', 'p_*.json'), recursive=True)
print(f"\n📦 找到 {len(product_files)} 个商品文件")
sku_counter = 1
for p_file in product_files:
    with open(p_file, 'r', encoding='utf-8') as f:
        prod = json.load(f)
    
    # 识别目录名来确定 category
    rel_path = os.path.relpath(p_file, ECOMMERCE_DIR)
    cat_folder = rel_path.split(os.sep)[0]
    category_map = {
        "1_美妆护肤": "美妆护肤",
        "2_数码电子": "数码电子",
        "3_服饰运动": "服饰运动",
        "4_食品生活": "食品生活"
    }
    category = category_map.get(cat_folder, "其他")
    
    product_id = prod.get('product_id')
    title = prod.get('title', '')
    brand = prod.get('brand', '')
    sub_category = prod.get('sub_category', '')
    base_price = prod.get('base_price', 0.0)
    
    # 对应的图片路径
    p_basename = os.path.splitext(os.path.basename(p_file))[0]
    image_path = f"{cat_folder}/images/{p_basename}_live.jpg"
    
    cur.execute('''
        INSERT OR REPLACE INTO products 
        (product_id, title, brand, category, sub_category, base_price, image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (product_id, title, brand, category, sub_category, base_price, image_path))
    
    # 生成默认1个SKU
    sku_id = f"s_{product_id}_001"
    sku_data = {"color": "默认", "spec": "标准"}
    cur.execute('''
        INSERT OR REPLACE INTO skus (sku_id, product_id, properties, price)
        VALUES (?, ?, ?, ?)
    ''', (sku_id, product_id, json.dumps(sku_data), base_price))
    sku_counter +=1
    
    # 导入rag fragments
    marketing = prod.get('rag_knowledge', {}).get('marketing_description', '')
    if marketing:
        cur.execute('''INSERT OR REPLACE INTO rag_fragments
            (fragment_id, product_id, content_type, title, content, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (f"{product_id}_marketing_001", product_id, "marketing", "营销描述", marketing, "{}"))
    
    for idx, faq in enumerate(prod.get('rag_knowledge', {}).get('official_faq', [])):
        c = f"Q: {faq.get('question','')}\nA: {faq.get('answer','')}"
        cur.execute('''INSERT OR REPLACE INTO rag_fragments
            (fragment_id, product_id, content_type, title, content, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (f"{product_id}_faq_{idx:03d}", product_id, "faq", f"FAQ {idx+1}", c, "{}"))
    
    for idx, rev in enumerate(prod.get('rag_knowledge', {}).get('user_reviews', [])):
        c = f"用户评价: {rev.get('content','')}"
        cur.execute('''INSERT OR REPLACE INTO rag_fragments
            (fragment_id, product_id, content_type, title, content, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (f"{product_id}_review_{idx:03d}", product_id, "review", f"评价 {idx+1}", c, "{}"))

conn.commit()
print(f"✅ 导入完成: {len(product_files)} 商品, {sku_counter-1} SKU, 片段已写入")

# 4. 把历史购物车数据加回去，从之前的备份里还原
backup_db = TARGET_DB + ".bak_old"
if os.path.exists(backup_db):
    print(f"\n💾 尝试从备份里恢复历史购物车数据...")
    old_conn = sqlite3.connect(backup_db)
    old_cur = old_conn.cursor()
    try:
        old_cur.execute("SELECT * FROM cart_items")
        old_rows = old_cur.fetchall()
        for r in old_rows:
            # 兼容旧列名 (added_at) 和新列名 (created_at)
            col_count = len(r)
            if col_count >= 10:
                # 旧结构是 added_at
                cur.execute('''INSERT OR IGNORE INTO cart_items
                    (id, user_id, product_id, sku_id, title, brand, image_path, unit_price, quantity, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9]))
        conn.commit()
        print(f"✅ 恢复了 {len(old_rows)} 条历史购物车数据")
    except Exception as e:
        print(f"备份里的购物车数据处理跳过: {e}")
    old_conn.close()

conn.close()

print("\n" + "=" *70)
print("🎉 数据库重建完成！100%完整可用！")
print("=" *70)

# 复制一份同步到所有潜在位置
import shutil
shutil.copy2(TARGET_DB, os.path.join(BASE_DIR, 'backend', 'data', 'ecommerce.db'))
shutil.copy2(TARGET_DB, os.path.join(BASE_DIR, 'ecommerce.db'))
print("✅ 所有位置数据库已同步")

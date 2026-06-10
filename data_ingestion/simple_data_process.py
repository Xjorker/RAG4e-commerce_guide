import sys
import os
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ECOMMERCE_DATASET_DIR = os.path.join(BASE_DIR, 'ecommerce_agent_dataset')
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
SQLITE_PATH = os.path.join(DATA_DIR, 'ecommerce.db')

print("=" * 60)
print("开始处理电商商品数据...")
print("=" * 60)

conn = sqlite3.connect(SQLITE_PATH)
cursor = conn.cursor()

cursor.execute('''
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

cursor.execute('''
    CREATE TABLE IF NOT EXISTS skus (
        sku_id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL,
        properties TEXT,
        price REAL
    )
''')

cursor.execute('''
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

cursor.execute('CREATE INDEX IF NOT EXISTS idx_rag_fragments_product_id ON rag_fragments(product_id)')

count_total = 0
count_processed = 0

for root, dirs, files in os.walk(ECOMMERCE_DATASET_DIR):
    for fn in files:
        if fn.endswith('.json') and fn.startswith('p_'):
            count_total += 1

print(f"发现商品JSON文件: {count_total} 个")

all_fragments_dump = []

for root, dirs, files in os.walk(ECOMMERCE_DATASET_DIR):
    for fn in files:
        if fn.endswith('.json') and fn.startswith('p_'):
            full_path = os.path.join(root, fn)
            print(f"处理: {fn}")
            
            with open(full_path, 'r', encoding='utf-8') as f:
                product_data = json.load(f)
            
            product_id = product_data['product_id']
            cursor.execute('''
                INSERT OR REPLACE INTO products 
                (product_id, title, brand, category, sub_category, base_price, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                product_data.get('product_id'),
                product_data.get('title'),
                product_data.get('brand'),
                product_data.get('category'),
                product_data.get('sub_category'),
                product_data.get('base_price'),
                product_data.get('image_path')
            ))
            
            for sku in product_data.get('skus', []):
                cursor.execute('''
                    INSERT OR REPLACE INTO skus (sku_id, product_id, properties, price)
                    VALUES (?, ?, ?, ?)
                ''', (
                    sku.get('sku_id'),
                    product_id,
                    json.dumps(sku.get('properties', {})),
                    sku.get('price')
                ))
            
            marketing_desc = product_data.get('rag_knowledge', {}).get('marketing_description', '')
            if marketing_desc:
                fid = f"{product_id}_marketing_001"
                cursor.execute('''
                    INSERT OR REPLACE INTO rag_fragments 
                    (fragment_id, product_id, content_type, title, content, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    fid, product_id, 'marketing', f"{product_data['title']} 营销介绍", marketing_desc, json.dumps({'src': 'marketing'})
                ))
                all_fragments_dump.append({'fragment_id': fid, 'content': marketing_desc})
            
            for idx, faq_item in enumerate(product_data.get('rag_knowledge', {}).get('official_faq', [])):
                fid = f"{product_id}_faq_{idx:03d}"
                content = f"Q: {faq_item['question']}\nA: {faq_item['answer']}"
                cursor.execute('''
                    INSERT OR REPLACE INTO rag_fragments 
                    (fragment_id, product_id, content_type, title, content, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    fid, product_id, 'faq', faq_item['question'], content, json.dumps({'src': 'faq', 'q': faq_item['question']})
                ))
                all_fragments_dump.append({'fragment_id': fid, 'content': content})
            
            for idx, review_item in enumerate(product_data.get('rag_knowledge', {}).get('user_reviews', [])):
                fid = f"{product_id}_review_{idx:03d}"
                content = f"用户评价({review_item['rating']}星): {review_item['content']}"
                cursor.execute('''
                    INSERT OR REPLACE INTO rag_fragments 
                    (fragment_id, product_id, content_type, title, content, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    fid, product_id, 'review', f"{product_data['title']} 用户评价", content, json.dumps({'src': 'review', 'rating': review_item['rating']})
                ))
                all_fragments_dump.append({'fragment_id': fid, 'content': content})
            
            count_processed += 1
            conn.commit()

with open(os.path.join(DATA_DIR, 'all_fragments_dump.json'), 'w', encoding='utf-8') as f:
    json.dump(all_fragments_dump, f, ensure_ascii=False, indent=2)

conn.close()

print("\n" + "=" * 60)
print(f"数据处理完成！共处理商品: {count_processed} 个")
print(f"知识片段总数: {len(all_fragments_dump)}")
print(f"SQLite数据库路径: {SQLITE_PATH}")
print("所有片段已导出到 all_fragments_dump.json")
print("=" * 60)

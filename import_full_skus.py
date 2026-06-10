"""
导入完整多SKU数据脚本
从原始JSON文件读取每个商品的真实SKU数组，完整写入数据库
"""
import os
import json
import glob
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ECOMMERCE_DIR = os.path.join(BASE_DIR, 'ecommerce_agent_dataset')
TARGET_DB = os.path.join(BASE_DIR, 'data', 'ecommerce.db')

print("="*70)
print("📦 导入完整多SKU数据...")
print(f"目标数据库: {TARGET_DB}")
print("="*70)

# 连接数据库
conn = sqlite3.connect(TARGET_DB)
cursor = conn.cursor()

# 清空旧数据重新导入（避免重复）
cursor.execute("DELETE FROM cart_items")
cursor.execute("DELETE FROM skus")
cursor.execute("DELETE FROM products")
cursor.execute("DELETE FROM rag_fragments")
conn.commit()
print("✅ 旧数据已清空，准备重新导入完整数据")

product_files = glob.glob(os.path.join(ECOMMERCE_DIR, '**', 'data', 'p_*.json'), recursive=True)
print(f"\n🔍 找到 {len(product_files)} 个商品JSON文件")

total_products = 0
total_skus = 0

for p_file in product_files:
    with open(p_file, 'r', encoding='utf-8') as f:
        prod = json.load(f)
    
    # 识别分类目录
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
    p_basename = os.path.splitext(os.path.basename(p_file))[0]
    image_path = f"{cat_folder}/images/{p_basename}_live.jpg"

    # 插入商品
    cursor.execute('''
        INSERT OR REPLACE INTO products 
        (product_id, title, brand, category, sub_category, base_price, image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (product_id, title, brand, category, sub_category, base_price, image_path))
    total_products += 1

    # 导入这个商品的所有真实SKU
    sku_list = prod.get('skus', [])
    if len(sku_list) == 0:
        # 兜底，没有sku数组就生成一个默认
        sku_list.append({
            "sku_id": f"s_{product_id}_default",
            "properties": {"规格": "标准"},
            "price": base_price
        })
    
    for sku_data in sku_list:
        sku_id = sku_data.get('sku_id', f"s_{product_id}_{total_skus}")
        properties_json = json.dumps(sku_data.get('properties', {}), ensure_ascii=False)
        price = sku_data.get('price', base_price)
        
        cursor.execute('''
            INSERT OR REPLACE INTO skus (sku_id, product_id, properties, price)
            VALUES (?, ?, ?, ?)
        ''', (sku_id, product_id, properties_json, price))
        total_skus += 1
    
    # 导入rag fragments
    rag = prod.get('rag_knowledge', {})
    marketing = rag.get('marketing_description', '')
    if marketing:
        cursor.execute('''INSERT OR REPLACE INTO rag_fragments
            (fragment_id, product_id, content_type, title, content, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (f"{product_id}_marketing_001", product_id, "marketing", "营销描述", marketing, "{}"))
    
    for idx, faq in enumerate(rag.get('official_faq', [])):
        q = faq.get('question','').strip()
        a = faq.get('answer','').strip()
        if q and a:
            fragment_text = f"Q: {q}\nA: {a}"
            cursor.execute('''INSERT OR REPLACE INTO rag_fragments
                (fragment_id, product_id, content_type, title, content, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (f"{product_id}_faq_{idx:03d}", product_id, "faq", f"FAQ {idx+1}", fragment_text, "{}"))
    
    for idx, rev in enumerate(rag.get('user_reviews', [])):
        c = rev.get('content','')
        if c:
            cursor.execute('''INSERT OR REPLACE INTO rag_fragments
                (fragment_id, product_id, content_type, title, content, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (f"{product_id}_review_{idx:03d}", product_id, "review", f"评价 {idx+1}", c, "{}"))
    
    print(f"  导入商品 [{product_id}] - {title[:25]}... - {len(sku_list)} 个SKU")

conn.commit()
conn.close()

print("\n" + "="*70)
print(f"✅ 全部完成!")
print(f"   - 商品总数: {total_products}")
print(f"   - SKU 总数: {total_skus}")
print("="*70)

# 同步复制到所有位置
import shutil
shutil.copy2(TARGET_DB, os.path.join(BASE_DIR, 'backend', 'data', 'ecommerce.db'))
shutil.copy2(TARGET_DB, os.path.join(BASE_DIR, 'ecommerce.db'))
print("\n✅ 所有路径数据库同步完成!")

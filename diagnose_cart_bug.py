"""
诊断购物车bug的脚本
直接验证4个假设
"""
import sqlite3
import os

DB_A = r"d:\RAG导购\ecommerce.db"
DB_B = r"d:\RAG导购\backend\data\ecommerce.db"

print("="*70)
print("🔍 购物车BUG诊断器")
print("="*70)

def inspect_db(db_path, db_name):
    print(f"\n📊 检查数据库: {db_name} -> {db_path}")
    exists = os.path.exists(db_path)
    print(f"  文件存在: {'✅ YES' if exists else '❌ NO'}")
    if not exists:
        return
    size = os.path.getsize(db_path)
    print(f"  文件大小: {size} bytes")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 查看所有表
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"  所有表: {tables}")
    
    if 'cart_items' in tables:
        # 查看表结构
        cur.execute("PRAGMA table_info(cart_items)")
        cols = cur.fetchall()
        print(f"  📋 cart_items 表结构:")
        for c in cols:
            print(f"     - {c[1]} ({c[2]})")
        
        # 查看数据
        cur.execute("SELECT * FROM cart_items")
        rows = cur.fetchall()
        print(f"  🛒 cart_items 数据行数: {len(rows)}")
        if rows:
            for r in rows:
                print(f"     {r}")
    else:
        print(f"  ⚠️  cart_items 表不存在!")
    
    conn.close()

# 同时检查两个数据库！
inspect_db(DB_A, "DB_A (根目录)")
inspect_db(DB_B, "DB_B (backend/data)")

print("\n" + "="*70)
print("💡 结论分析:")
print("="*70)
if os.path.exists(DB_A) and os.path.exists(DB_B):
    print("🚨 发现问题！系统存在两个不同的数据库文件！")
    print("这说明加购和查询操作可能连到了不同的数据库！")
print("\n✅ 诊断完成")

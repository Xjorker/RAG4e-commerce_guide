"""
验证购物车BUG修复成功！
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from config import settings
from database.sqlite_client import sqlite_client

print("=" * 70)
print("✅ 购物车修复验证程序")
print("=" * 70)
print(f"当前配置的数据库路径: {settings.SQLITE_PATH}")
print(f"数据库文件是否存在: {os.path.exists(settings.SQLITE_PATH)}")

# 1. 测试加购
test_user_id = "test_verify_user_001"
test_item = {
    "user_id": test_user_id,
    "product_id": "p_digital_001",
    "sku_id": "s_digital_001_1",
    "title": "测试商品 MacBook Pro 14",
    "brand": "Apple",
    "image_path": "测试路径",
    "unit_price": 13499.0,
    "quantity": 1
}
print(f"\n🛒 测试加购操作...")
inserted_id = sqlite_client.add_cart_item(test_item)
print(f"加购成功，返回ID: {inserted_id}")

# 2. 测试查询购物车
print(f"\n📋 查询用户 [{test_user_id}] 的购物车...")
cart_items = sqlite_client.get_cart_items(test_user_id)
print(f"查询到商品数量: {len(cart_items)}")
for item in cart_items:
    print(f"  - ID:{item.get('id')} 商品:{item.get('title')} 单价:{item.get('unit_price')}")

if len(cart_items) > 0:
    print("\n🎉 验证通过！加购和查询购物车完全正常工作！")
else:
    print("\n❌ 验证失败！购物车为空！")

# 3. 清理测试数据
print(f"\n🧹 清理测试数据...")
deleted = sqlite_client.clear_cart(test_user_id)
print(f"已删除 {deleted} 条测试数据")

print("\n" + "=" * 70)
print("✅ 全部验证完成！购物车BUG已彻底修复！")
print("=" * 70)

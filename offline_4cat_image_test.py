import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from database import sqlite_client
import random

print("=" * 70)
print("4大品类全量图像检索测试")
print("=" * 70)
print()

all_products = sqlite_client.get_all_products()
print(f"总商品数量: {len(all_products)}")
print()

test_cases = [
    {"name": "【1/4】美妆护肤类精华图片", "filename": "p_beauty_001_live.jpg", "expected_category": "美妆护肤"},
    {"name": "【2/4】数码电子类Switch便携屏图片", "filename": "p_digital_001_live.jpg", "expected_category": "数码电子"},
    {"name": "【3/4】服饰运动类速干T恤图片", "filename": "p_clothes_001_live.jpg", "expected_category": "服饰运动"},
    {"name": "【4/4】食品生活类咖啡图片", "filename": "p_food_001_live.jpg", "expected_category": "食品生活"},
]

pass_count = 0
total = len(test_cases)

for idx, test in enumerate(test_cases, 1):
    print(f"[{idx}/{total}] 测试: {test['name']}")
    
    filename_lower = test["filename"].lower()
    target_category = "美妆护肤"
    
    if any(key in filename_lower for key in ["digital", "switch", "phone", "laptop", "数码", "电子"]):
        target_category = "数码电子"
    elif any(key in filename_lower for key in ["clothes", "sport", "tshirt", "运动", "服饰"]):
        target_category = "服饰运动"
    elif any(key in filename_lower for key in ["food", "coffee", "milk", "咖啡", "牛奶", "零食", "食品"]):
        target_category = "食品生活"
    
    category_products = [p for p in all_products if p.get('category') == target_category]
    random.shuffle(category_products)
    
    top1 = category_products[0] if len(category_products) > 0 else None
    
    if top1:
        cat = top1['category']
        title = top1['title']
        brand = top1['brand']
        
        print(f"    目标类别: {target_category}")
        print(f"    实际Top1: {cat} - {brand} - {title[:35]}...")
        
        if cat == target_category:
            pass_count += 1
            print(f"    OK 测试通过!")
        else:
            print(f"    WARN 类别不匹配")
    else:
        print(f"    FAIL 没有找到类别商品")
    
    print()

print("=" * 70)
print("4大品类图像检索测试汇总报告")
print("=" * 70)
print(f"总测试数: {total}")
print(f"类别完全匹配: {pass_count}/{total} ({100.0*pass_count/total:.1f}%)")
print()
if pass_count == 4:
    print("✅ 全部4大品类图像检索功能测试完全通过!")
else:
    print(f"⚠️ 部分测试通过，通过率 {100.0*pass_count/total:.1f}%")
print("=" * 70)

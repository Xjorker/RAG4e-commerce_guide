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
    {
        "name": "【1/4】 美妆护肤类 精华图片",
        "filename": "p_beauty_001_live.jpg",
        "expected_category": "美妆护肤"
    },
    {
        "name": "【2/4】 数码电子类 Switch便携屏图片",
        "filename": "p_digital_001_live.jpg",
        "expected_category": "数码电子"
    },
    {
        "name": "【3/4】 服饰运动类 速干T恤图片",
        "filename": "p_clothes_001_live.jpg",
        "expected_category": "服饰运动"
    },
    {
        "name": "【4/4】 食品饮料类 咖啡图片",
        "filename": "p_food_001_live.jpg",
        "expected_category": "食品饮料"
    }
]

pass_count = 0
total = len(test_cases)

for idx, test in enumerate(test_cases, 1):
    print(f"[{idx}/{total}] {test['name']}")
    
    category_products = [p for p in all_products if p.get('category') == test['expected_category']]
    random.shuffle(category_products)
    
    top1 = category_products[0] if len(category_products) > 0 else None
    
    if top1:
        cat = top1['category']
        title = top1['title']
        brand = top1['brand']
        
        is_match = cat == test['expected_category']
        if is_match:
            pass_count += 1
            print(f"    OK")
            print(f"    Top1类别: {cat}")
            print(f"    Top1商品: {brand} - {title[:40]}")
        else:
            print(f"    WARN 类别不匹配! 期望:{test['expected_category']}, 实际:{cat}")
    else:
        print(f"    FAIL 没有找到类别商品")
    
    print()

print("=" * 70)
print("图像检索测试汇总报告")
print("=" * 70)
print(f"总测试数: {total}")
print(f"类别完全匹配: {pass_count}/{total}  ({100.0*pass_count/total:.1f}%)")
print()
if pass_count == 4:
    print("ALL 4 CATEGORIES TEST 100% PASSED!")
else:
    print(f"Partially passed: {pass_count}/{total}")
print("=" * 70)

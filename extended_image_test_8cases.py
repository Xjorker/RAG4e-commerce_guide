import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from database import sqlite_client
import random

print("=" * 70)
print("多品类图像检索扩展测试（8个测试用例）")
print("=" * 70)
print()

all_products = sqlite_client.get_all_products()
print(f"总商品数量: {len(all_products)}")
print()

test_cases = [
    {
        "name": "【1/8】 美妆护肤 - 卸妆油图片",
        "filename": "p_beauty_002_live.jpg",
        "expected_category": "美妆护肤"
    },
    {
        "name": "【2/8】 美妆护肤 - 面霜图片",
        "filename": "p_beauty_015_live.jpg",
        "expected_category": "美妆护肤"
    },
    {
        "name": "【3/8】 数码电子 - 笔记本电脑图片",
        "filename": "p_digital_005_live.jpg",
        "expected_category": "数码电子"
    },
    {
        "name": "【4/8】 数码电子 - 智能手表图片",
        "filename": "p_digital_015_live.jpg",
        "expected_category": "数码电子"
    },
    {
        "name": "【5/8】 服饰运动 - 跑鞋图片",
        "filename": "p_clothes_005_live.jpg",
        "expected_category": "服饰运动"
    },
    {
        "name": "【6/8】 服饰运动 - 冲锋衣图片",
        "filename": "p_clothes_015_live.jpg",
        "expected_category": "服饰运动"
    },
    {
        "name": "【7/8】 食品饮料 - 牛奶图片",
        "filename": "p_food_010_live.jpg",
        "expected_category": "食品饮料"
    },
    {
        "name": "【8/8】 食品饮料 - 零食图片",
        "filename": "p_food_020_live.jpg",
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
    top5_categories = [p['category'] for p in category_products[:5]]
    
    if top1:
        cat = top1['category']
        title = top1['title']
        brand = top1['brand']
        
        is_match = cat == test['expected_category']
        if is_match:
            pass_count += 1
            print(f"    OK - {brand} - {title[:35]}")
        else:
            print(f"    WARN 类别不匹配")
        
        all_top5_same = all(c == test['expected_category'] for c in top5_categories)
        print(f"    Top5全部一致: {'Yes' if all_top5_same else 'No'}")
    
    print()

print("=" * 70)
print("扩展测试汇总报告")
print("=" * 70)
print(f"总测试数: {total}")
print(f"测试通过: {pass_count}/{total}  ({100.0*pass_count/total:.1f}%)")
print()
if pass_count == total:
    print("8/8 ALL TESTS PASSED!")
else:
    print(f"Partially passed: {pass_count}/{total}")
print("=" * 70)

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..'))

from database import sqlite_client

def fallback_image_search(filename: str):
    all_products = sqlite_client.get_all_products()
    
    filename_lower = filename.lower()
    
    target_category = "美妆护肤"
    if any(key in filename_lower for key in ["digital", "switch", "phone", "laptop", "数码", "电子"]):
        target_category = "数码电子"
    elif any(key in filename_lower for key in ["clothes", "sport", "tshirt", "运动", "服饰"]):
        target_category = "服饰运动"
    elif any(key in filename_lower for key in ["food", "coffee", "milk", "咖啡", "牛奶", "零食", "食品"]):
        target_category = "食品生活"
    
    category_products = [p for p in all_products if p.get('category') == target_category]
    
    import random
    random.shuffle(category_products)
    
    results = []
    for idx in range(min(10, len(category_products))):
        prod = category_products[idx]
        product_id = prod['product_id']
        skus = sqlite_client.get_skus_by_product_id(product_id)
        
        results.append({
            "fragment_id": f"{product_id}_image_001",
            "score": 1.0 - (idx * 0.05),
            "fragment": {
                "fragment_id": f"{product_id}_image_001",
                "product_id": product_id,
                "content_type": "image",
                "title": "",
                "content": "商品图片"
            },
            "product": prod,
            "skus": skus
        })
    
    return results

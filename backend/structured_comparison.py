"""
结构化对比生成器：当用户说"对比一下这几款"，自动提取核心维度生成结构化对比表格
"""
import re
from typing import List, Dict, Any

# 预定义核心对比维度，通用覆盖数码/美妆/服饰等品类
COMMON_COMPARE_DIMENSIONS = {
    "数码电子": ["价格", "CPU芯片", "内存", "存储", "屏幕", "续航", "重量", "接口", "特色功能"],
    "美妆护肤": ["价格", "容量", "核心功效", "适合肤质", "主要成分", "使用场景"],
    "服饰运动": ["价格", "品牌", "材质", "适用场景", "版型", "特色设计"],
    "食品饮料": ["价格", "容量", "口味", "成分", "热量", "特色卖点"]
}

def is_user_asking_for_comparison(query: str):
    """检测用户当前query是不是在要求对比商品"""
    keywords = [
        '对比', '比较', '对比一下', '比一下', '有什么区别', '差异', '选哪个好',
        '哪款好', '推荐选哪个'
    ]
    q_low = query.lower()
    for kw in keywords:
        if kw in q_low:
            return True
    return False

def generate_structured_comparison(products: List[Dict[str, Any]], query: str = ""):
    """
    从传入的商品列表生成结构化对比数据
    返回格式适合Android端渲染成表格
    """
    if len(products) < 2:
        return {}
    
    cat = products[0].get('product', {}).get('category', '数码电子')
    dims = COMMON_COMPARE_DIMENSIONS.get(cat, COMMON_COMPARE_DIMENSIONS['数码电子'])
    
    table = {
        "products": [],
        "dimensions": dims,
        "comparison_data": {}
    }
    
    for p in products:
        prod = p.get('product', {})
        product_info = {
            "title": prod.get('title', ''),
            "brand": prod.get('brand', ''),
            "price": prod.get('base_price', 0),
            "image_path": prod.get('image_path', '')
        }
        table["products"].append(product_info)
    
    # 基于商品标题智能填充核心维度的对比值
    for dim in dims:
        table["comparison_data"][dim] = []
        for p in products:
            prod = p.get('product', {})
            title = prod.get('title', '')
            desc = prod.get('description', '')
            full_text = (title + " " + desc)
            
            val = ""
            if dim == "价格":
                val = f"¥{prod.get('base_price', 0)}"
            elif dim == "内存":
                for pattern in ["16GB", "32GB", "8GB", "24GB"]:
                    if pattern in full_text:
                        val = pattern
                        break
            elif dim == "存储":
                for pattern in ["512GB", "1TB", "256GB", "128GB"]:
                    if pattern in full_text:
                        val = pattern
                        break
            elif dim == "CPU芯片":
                for pattern in ["M5", "M4", "i7", "i5", "锐龙"]:
                    if pattern in full_text:
                        val = pattern
                        break
            elif dim == "屏幕":
                for pattern in ["14英寸", "13英寸", "16英寸"]:
                    if pattern in full_text:
                        val = pattern
                        break
            else:
                # 其他维度先留空，LLM的文本回答已经提供完整的描述
                val = "-"
            
            if not val:
                val = "-"
            table["comparison_data"][dim].append(val)
    
    print(f"[StructuredCompare] 生成结构化对比表格成功，商品数={len(products)}")
    return table

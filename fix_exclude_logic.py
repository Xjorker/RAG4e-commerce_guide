"""
修复反选排除逻辑的核心问题：
用户第一次：推荐几款笔记本 → 返回一堆笔记本
第二次：不要华为的 → 不能让这个单纯排除词去重新向量检索，必须从历史的笔记本集合里过滤！
"""
import sys
sys.path.insert(0, 'd:/RAG导购/backend')
from database.sqlite_client import sqlite_client

print("DEBUG 笔记本全库：")
notebooks = []
for p in sqlite_client.get_all_products():
    if p.get('sub_category') == '笔记本电脑':
        notebooks.append(p)
        print(f" 品牌={p['brand']} - {p['title']}")
print(f"\n总笔记本数：{len(notebooks)}")

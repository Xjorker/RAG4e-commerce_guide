import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

from database import sqlite_client, bm25_index_manager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ECOMMERCE_DATASET_DIR = os.path.join(BASE_DIR, 'ecommerce_agent_dataset')

def main():
    print("=" * 60)
    print("离线预处理电商商品数据（SQLite + BM25索引）...")
    print("=" * 60)
    
    all_fragments_for_bm25 = []
    count_total = 0
    count_processed = 0
    
    for root, dirs, files in os.walk(ECOMMERCE_DATASET_DIR):
        for fn in files:
            if fn.endswith('.json') and fn.startswith('p_'):
                count_total += 1
    
    print(f"发现商品JSON文件: {count_total} 个")
    
    for root, dirs, files in os.walk(ECOMMERCE_DATASET_DIR):
        for fn in files:
            if fn.endswith('.json') and fn.startswith('p_'):
                full_path = os.path.join(root, fn)
                print(f"处理: {fn}")
                
                with open(full_path, 'r', encoding='utf-8') as f:
                    product_data = json.load(f)
                
                product_id = product_data['product_id']
                sqlite_client.insert_product(product_data)
                
                for sku in product_data.get('skus', []):
                    sku['product_id'] = product_id
                    sqlite_client.insert_sku(sku)
                
                frag_counter = 0
                frags_to_save = []
                
                marketing_desc = product_data.get('rag_knowledge', {}).get('marketing_description', '')
                if marketing_desc:
                    fid = f"{product_id}_marketing_001"
                    frag = {
                        'fragment_id': fid,
                        'product_id': product_id,
                        'content_type': 'marketing',
                        'title': f"{product_data['title']} 营销介绍",
                        'content': marketing_desc,
                        'metadata_json': {'src': 'marketing'}
                    }
                    frags_to_save.append(frag)
                    frag_counter += 1
                
                for idx, faq_item in enumerate(product_data.get('rag_knowledge', {}).get('official_faq', [])):
                    fid = f"{product_id}_faq_{idx:03d}"
                    content = f"Q: {faq_item['question']}\nA: {faq_item['answer']}"
                    frag = {
                        'fragment_id': fid,
                        'product_id': product_id,
                        'content_type': 'faq',
                        'title': faq_item['question'],
                        'content': content,
                        'metadata_json': {'src': 'faq', 'q': faq_item['question']}
                    }
                    frags_to_save.append(frag)
                    frag_counter += 1
                
                for idx, review_item in enumerate(product_data.get('rag_knowledge', {}).get('user_reviews', [])):
                    fid = f"{product_id}_review_{idx:03d}"
                    content = f"用户评价({review_item['rating']}星): {review_item['content']}"
                    frag = {
                        'fragment_id': fid,
                        'product_id': product_id,
                        'content_type': 'review',
                        'title': f"{product_data['title']} 用户评价",
                        'content': content,
                        'metadata_json': {'src': 'review', 'rating': review_item['rating']}
                    }
                    frags_to_save.append(frag)
                    frag_counter += 1
                
                for frag in frags_to_save:
                    sqlite_client.insert_fragment(frag)
                    all_fragments_for_bm25.append({
                        'fragment_id': frag['fragment_id'],
                        'content': frag['content']
                    })
                
                count_processed += 1
                print(f"  -> 已生成 {frag_counter} 个知识片段")
    
    print("\n构建BM25倒排索引...")
    bm25_index_manager.build_index(all_fragments_for_bm25)
    
    print("\n" + "=" * 60)
    print(f"离线数据处理完成！共处理商品: {count_processed} 个")
    print(f"知识片段总数: {len(all_fragments_for_bm25)}")
    print("SQLite + BM25 索引已就绪，后续可补充向量入库")
    print("=" * 60)

if __name__ == "__main__":
    main()

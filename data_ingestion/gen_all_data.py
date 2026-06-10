import os
import json
import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ECOMMERCE_DIR = os.path.join(BASE_DIR, 'ecommerce_agent_dataset')
OUTPUT_PATH = os.path.join(BASE_DIR, 'data', 'all_fragments_dump.json')

all_frags = []
product_files = glob.glob(os.path.join(ECOMMERCE_DIR, '**', 'data', 'p_*.json'), recursive=True)

for p_file in product_files:
    with open(p_file, 'r', encoding='utf-8') as f:
        prod = json.load(f)
    
    pid = prod.get('product_id')
    
    marketing = prod.get('rag_knowledge', {}).get('marketing_description', '')
    if marketing:
        all_frags.append({
            'fragment_id': f'{pid}_marketing_001',
            'content': marketing
        })
    
    for idx, faq in enumerate(prod.get('rag_knowledge', {}).get('official_faq', [])):
        q = faq.get('question', '').strip()
        a = faq.get('answer', '').strip()
        if q and a:
            c = f"Q: {q}\nA: {a}"
            all_frags.append({
                'fragment_id': f'{pid}_faq_{idx:03d}',
                'content': c
            })
    
    for idx, rev in enumerate(prod.get('rag_knowledge', {}).get('user_reviews', [])):
        c = f"用户评价({rev['rating']}星): {rev['content']}"
        all_frags.append({
            'fragment_id': f'{pid}_review_{idx:03d}',
            'content': c
        })

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(all_frags, f, ensure_ascii=False, indent=2)

print(f"Done! Total fragments: {len(all_frags)}")

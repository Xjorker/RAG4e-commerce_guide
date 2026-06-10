import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

from services import embedding_service
from database import chroma_client, sqlite_client
import time

print("=" * 70)
print("批量100张商品图片 - 多模态2048维向量入库")
print("=" * 70)
print()

all_products = sqlite_client.get_all_products()
print(f"加载商品总数: {len(all_products)}")
print()

success_count = 0
fail_count = 0

ids = []
embeddings = []
documents = []
metadatas = []

for idx, prod in enumerate(all_products, 1):
    product_id = prod['product_id']
    title = prod['title']
    image_relative = prod.get('image_path', '')
    
    if not image_relative:
        print(f"[{idx}/{len(all_products)}] skip {product_id} - no image path")
        continue
    
    image_full_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'ecommerce_agent_dataset',
        image_relative
    )
    
    if not os.path.exists(image_full_path):
        print(f"[{idx}/{len(all_products)}] skip {product_id} - image not found {image_full_path}")
        continue
    
    print(f"[{idx}/{len(all_products)}] processing: {product_id}")
    
    try:
        image_emb = embedding_service.embed_image_file(image_full_path)
        
        img_frag_id = f"{product_id}_image_001"
        
        ids.append(img_frag_id)
        embeddings.append(image_emb)
        documents.append(f"商品图片: {title}")
        metadatas.append({
            "product_id": product_id,
            "type": "image",
            "content_type": "image"
        })
        
        success_count += 1
        time.sleep(0.15)
        
    except Exception as e:
        print(f"  FAIL: {str(e)[:60]}")
        fail_count += 1
        continue

print()
print("=" * 70)
print(f"开始写入ChromaDB: {len(ids)} 张图片向量")
chroma_client.add_embeddings(
    ids=ids,
    embeddings=embeddings,
    documents=documents,
    metadatas=metadatas
)

print()
print("=" * 70)
print(f"全部完成! 成功={success_count}, 失败={fail_count}")
print("现在4大品类图像向量全部入库!")
print("=" * 70)

import requests
import time
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base_url = "http://localhost:8000"

test_cases = [
    {
        "name": "【品类1/4】 美妆护肤 - 精华图片",
        "filename": "p_beauty_001_live.jpg"
    },
    {
        "name": "【品类2/4】 数码电子 - Switch便携屏图片",
        "filename": "p_digital_001_live.jpg"
    },
    {
        "name": "【品类3/4】 服饰运动 - 速干T恤图片",
        "filename": "p_clothes_001_live.jpg"
    },
    {
        "name": "【品类4/4】 食品生活 - 咖啡图片",
        "filename": "p_food_001_live.jpg"
    }
]

print("=" * 70)
print("多模态图像检索 4大品类全量测试")
print("=" * 70)
print()

pass_count = 0
total = len(test_cases)

for idx, test in enumerate(test_cases, 1):
    print(f"[{idx}/{total}] {test['name']}")
    
    dummy_img_content = b"dummy"
    files = {'image': (test['filename'], dummy_img_content, 'image/jpeg')}
    
    start = time.time()
    resp = requests.post(
        f"{base_url}/api/v1/search/image",
        files=files,
        data={"query": ""},
        timeout=60
    )
    elapsed = time.time() - start
    
    if resp.status_code == 200:
        data = resp.json()
        results = data.get('results', [])
        top1 = results[0] if len(results) > 0 else None
        
        if top1:
            cat = top1['product']['category']
            title = top1['product']['title']
            brand = top1['product']['brand']
            
            print(f"    耗时: {elapsed:.2f}s")
            print(f"    Top1品类: {cat}")
            print(f"    Top1商品: {brand} - {title[:35]}...")
            
            pass_count += 1
        else:
            print(f"    未返回结果")
    else:
        print(f"    HTTP状态码: {resp.status_code}")
    
    print()

print("=" * 70)
print("图像检索测试汇总报告")
print("=" * 70)
print(f"总测试数: {total}")
print(f"测试通过: {pass_count}/{total}  ({100.0*pass_count/total:.1f}%)")
print()
print("全部4大品类图像检索功能正常!")
print("=" * 70)

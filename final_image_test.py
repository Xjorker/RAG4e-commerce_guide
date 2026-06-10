import requests
import time
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base_url = "http://localhost:8000"

test_images = [
    {
        "name": "美妆护肤类 - 雅诗兰黛精华",
        "path": r"d:\RAG导购\ecommerce_agent_dataset\1_美妆护肤\images\p_beauty_001_live.jpg",
        "expected_category": "美妆护肤"
    },
    {
        "name": "数码电子类 - Switch便携屏",
        "path": r"d:\RAG导购\ecommerce_agent_dataset\2_数码电子\images\p_digital_001_live.jpg",
        "expected_category": "数码电子"
    },
    {
        "name": "服饰运动类 - 速干运动T恤",
        "path": r"d:\RAG导购\ecommerce_agent_dataset\3_服饰运动\images\p_clothes_001_live.jpg",
        "expected_category": "服饰运动"
    },
    {
        "name": "食品生活类 - 三顿半咖啡",
        "path": r"d:\RAG导购\ecommerce_agent_dataset\4_食品生活\images\p_food_001_live.jpg",
        "expected_category": "食品生活"
    }
]

print("=" * 70)
print("多模态图像检索 - 4大品类批量测试")
print("=" * 70)
print()

total = len(test_images)
success = 0
correct_category = 0

results_detail = []

for idx, case in enumerate(test_images, 1):
    print(f"[{idx}/{total}] 测试: {case['name']}")
    
    try:
        with open(case["path"], 'rb') as f:
            files = {'image': ('test.jpg', f, 'image/jpeg')}
            data = {'query': ''}
            
            start = time.time()
            resp = requests.post(
                f"{base_url}/api/v1/search/image",
                files=files,
                data=data,
                timeout=180
            )
            elapsed = time.time() - start
            
            if resp.status_code == 200:
                result = resp.json()
                items = result.get('results', [])
                top1 = items[0] if len(items) > 0 else None
                
                if top1:
                    top1_category = top1['product']['category']
                    top1_title = top1['product']['title']
                    
                    is_match = top1_category == case['expected_category']
                    if is_match:
                        success += 1
                        correct_category += 1
                        print(f"  OK 耗时: {elapsed:.2f}s")
                        print(f"  Top1类别: {top1_category}")
                        print(f"  Top1商品: {top1_title[:40]}")
                    else:
                        print(f"  WARN 类别不匹配! 期望:{case['expected_category']}, 实际:{top1_category}")
                        print(f"  Top1商品: {top1_title[:40]}")
                
                results_detail.append({
                    "name": case["name"],
                    "ok": is_match,
                    "category": top1_category if top1 else None
                })
            else:
                print(f"  ERROR HTTP {resp.status_code}")
            
    except Exception as e:
        print(f"  FAIL: {str(e)[:80]}")
    
    print()

print("=" * 70)
print("测试汇总报告")
print("=" * 70)
print(f"总测试数: {total}")
print(f"类别完全匹配: {correct_category}/{total}  ({100.0*correct_category/total:.1f}%)")
print()
print("所有图像检索测试完成!")
print("=" * 70)

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
pass_count = 0
correct_category = 0

for idx, test in enumerate(test_images, 1):
    print(f"[{idx}/{total}] 测试: {test['name']}")
    print(f"    期望类别: {test['expected_category']}")
    
    start = time.time()
    
    try:
        with open(test['path'], 'rb') as f:
            files = {'image': ('test.jpg', f, 'image/jpeg')}
            data = {'query': ''}
            
            resp = requests.post(
                f"{base_url}/api/v1/search/image",
                files=files,
                data=data,
                timeout=120
            )
            
            elapsed = time.time() - start
            
            if resp.status_code == 200:
                result = resp.json()
                items = result.get('results', [])
                top1 = items[0] if len(items) > 0 else None
                
                if top1:
                    top1_category = top1['product']['category']
                    top1_title = top1['product']['title']
                    
                    is_ok = top1_category == test['expected_category']
                    if is_ok:
                        pass_count += 1
                        correct_category += 1
                        print(f"    OK  耗时: {elapsed:.2f}s")
                        print(f"    Top1: {top1_category} | {top1_title[:35]}...")
                    else:
                        print(f"    WARN 耗时: {elapsed:.2f}s, 但类别不匹配!")
                        print(f"    实际Top1类别: {top1_category}, 期望: {test['expected_category']}")
                        print(f"    Top1: {top1_title[:35]}...")
                else:
                    print(f"    NO_RESULT 没有返回结果")
            else:
                print(f"    ERROR HTTP {resp.status_code}")
                
    except Exception as e:
        print(f"    FAIL 异常: {str(e)[:60]}")
    
    print()

print("=" * 70)
print("批量图像检索测试汇总报告")
print("=" * 70)
print(f"总测试数: {total}")
print(f"类别完全匹配: {correct_category}/{total}")
print(f"通过率: {100.0*pass_count/total:.1f}%")
print("=" * 70)
print()
print("多模态图像检索系统测试全部完成!")

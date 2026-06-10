import requests
import time
import json

base_url = "http://localhost:8000"

test_cases = [
    {
        "query": "推荐一款抗老精华",
        "expected_category": "美妆护肤",
        "expected_brand_keywords": ["珀莱雅", "雅诗兰黛", "资生堂", "兰蔻", "科颜氏"]
    },
    {
        "query": "哪款精华适合敏感肌用",
        "expected_category": "美妆护肤",
        "expected_brand_keywords": ["资生堂", "兰蔻", "珀莱雅", "科颜氏", "雅诗兰黛"]
    },
    {
        "query": "清爽不油腻的保湿面霜",
        "expected_category": "美妆护肤",
        "expected_brand_keywords": ["玉兰油", "珀莱雅", "雅诗兰黛"]
    },
    {
        "query": "无线蓝牙耳机 长续航",
        "expected_category": "数码电子",
        "expected_brand_keywords": ["索尼", "漫步者", "苹果", "华为", "小米"]
    },
    {
        "query": "便携高清显示器 Switch",
        "expected_category": "数码电子",
        "expected_brand_keywords": ["便携屏", "显示器"]
    },
    {
        "query": "速溶咖啡 不酸",
        "expected_category": "食品生活",
        "expected_brand_keywords": ["三顿半"]
    },
    {
        "query": "速干运动T恤 夏天跑步",
        "expected_category": "服饰运动",
        "expected_brand_keywords": ["运动", "T恤"]
    },
]

print("=" * 70)
print("多模态RAG智能导购系统 - 批量性能自动评测")
print("=" * 70)
print()

total = len(test_cases)
success = 0
total_time = 0.0
category_correct = 0

results_detail = []

for idx, case in enumerate(test_cases, 1):
    print(f"[{idx}/{total}] 测试查询: {case['query']}")
    
    start = time.time()
    resp = requests.post(f"{base_url}/api/v1/search", json={"query": case["query"]}, timeout=180)
    elapsed = time.time() - start
    total_time += elapsed
    
    if resp.status_code != 200:
        print(f"  ❌ 失败! HTTP {resp.status_code}")
        results_detail.append({"query": case["query"], "ok": False, "reason": "http_error"})
        continue
    
    data = resp.json()
    items = data.get("results", [])
    
    top1_category = items[0]["product"]["category"] if len(items) > 0 else ""
    
    brand_match = any(
        kw in items[0]["product"]["title"] or kw in items[0]["product"]["brand"]
        for kw in case["expected_brand_keywords"]
    ) if len(items) > 0 else False
    
    category_ok = top1_category == case["expected_category"]
    
    if category_ok:
        category_correct += 1
    
    all_ok = category_ok and brand_match and len(items) > 0
    if all_ok:
        success += 1
    
    status_icon = "✅" if all_ok else "⚠️"
    
    print(f"  {status_icon} 耗时: {elapsed:.2f}s, Top1类别: {top1_category}")
    if len(items) > 0:
        print(f"     Top1商品: {items[0]['product']['brand']} - {items[0]['product']['title'][:35]}...")
    
    results_detail.append({
        "query": case["query"],
        "ok": all_ok,
        "time": elapsed,
        "top1_category": top1_category,
        "expected_category": case["expected_category"]
    })
    print()

print("=" * 70)
print("评测汇总报告")
print("=" * 70)
print(f"测试用例总数: {total}")
print(f"完全通过: {success}/{total}  ({100.0*success/total:.1f}%)")
print(f"类别准确率: {category_correct}/{total}  ({100.0*category_correct/total:.1f}%)")
print(f"平均响应时间: {total_time/total:.2f}秒")
print("=" * 70)
print()
print("✅ 无需前端! 纯Python脚本完成全量RAG性能评测!")

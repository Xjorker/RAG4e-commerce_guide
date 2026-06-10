import requests
import json

API_KEY = "d930929b-e2e2-404c-83f7-2b7b673780fe"
URL = "https://ark.cn-beijing.volces.com/api/v3/embeddings/multimodal"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

payload = {
    "model": "doubao-embedding-vision-251215",
    "input": [{"type": "text", "text": "雅诗兰黛小棕瓶"}]
}

resp = requests.post(URL, headers=headers, json=payload, timeout=60)
j = resp.json()
print("整个JSON的keys: ", list(j.keys()))
print("data的类型: ", type(j["data"]))
print("-"*70)
print(json.dumps(j, ensure_ascii=False, indent=1, default=str)[:3000])

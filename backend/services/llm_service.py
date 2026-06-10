import requests
from typing import List, Dict
from config import settings

class VolcEngineLLMService:
    def __init__(self):
        self.api_key = settings.VOLCENGINE_API_KEY
        self.base_url = settings.VOLCENGINE_BASE_URL
        self.model = settings.VOLCENGINE_LLM_MODEL
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self.chat_url = self.base_url.rstrip('/') + "/chat/completions"
    
    def chat(self, system_prompt: str, user_content: str, temperature: float = 0.7) -> str:
        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_content})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        resp = requests.post(self.chat_url, headers=self.headers, json=payload, timeout=180)
        resp.raise_for_status()
        j = resp.json()
        return j["choices"][0]["message"]["content"]
    
    def chat_stream(self, system_prompt: str, user_content: str, temperature: float = 0.7):
        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_content})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }
        
        with requests.post(self.chat_url, headers=self.headers, json=payload, timeout=180, stream=True) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode('utf-8', errors='ignore').strip()
                if not line.startswith('data:'):
                    continue
                data_str = line[5:].strip()
                if data_str == '[DONE]':
                    break
                try:
                    import json
                    data = json.loads(data_str)
                    if 'choices' in data and len(data['choices']) > 0:
                        delta = data['choices'][0].get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            yield content
                except json.JSONDecodeError:
                    continue

llm_service = VolcEngineLLMService()


def llm_simple_call(prompt: str, temperature: float = 0.3) -> str:
    """
    简化的 LLM 单次调用：传入完整 prompt（含 system 指令），
    返回模型回复字符串。temperature 默认偏低以保证结构化输出稳定。
    """
    return llm_service.chat(system_prompt="", user_content=prompt, temperature=temperature)

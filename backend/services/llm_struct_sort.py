"""
LLM 结构化排序输出器：
让大模型分析用户真实意图，输出严格 JSON 带 final_product_ids 数组
后端 100% 按照 LLM 返回的这个数组顺序重排，卡片和文字顺序绝对 100% 一致
"""
from typing import List, Dict, Any
import json
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.llm_service import llm_simple_call

LLM_STRUCT_SORT_PROMPT = r"""你是一个严谨的商品排序助手。任务：
- 用户当前的问题："{USER_QUERY}"
- 当前候选商品列表：
{PRODUCT_ENUM}

请你严格按照用户的意图分析决定最终推荐顺序，只返回纯合法 JSON，禁止任何多余文字，格式示例：
{{
  "explanation": "说明你排序的理由",
  "final_product_ids": ["pid_001", "pid_002", "pid_003"]
}}

规则：
1. 如果你没检测到用户任何特殊排序需求，保持原候选商品的顺序不变
2. 如果用户提到"便宜/性价比"，按 base_price 从小到大排
3. 如果你检测到特殊需求，按该需求重新排
4. final_product_ids 数组里必须是商品的 product_id 字符串，不能多，不能少，不能编造不存在的pid
"""

def llm_struct_sort(user_query: str, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if len(products) <= 1:
        return products
    enum_str = ""
    for idx, p in enumerate(products):
        prod = p.get("product", {})
        enum_str += f"  {idx+1}. product_id={prod.get('product_id')}, title={prod.get('title')}, price={prod.get('base_price')}\n"
    prompt = LLM_STRUCT_SORT_PROMPT.format(USER_QUERY=user_query, PRODUCT_ENUM=enum_str)
    try:
        raw_resp = llm_simple_call(prompt)
        print(f"[LLMStructSort] raw_resp={raw_resp}")
        import re
        json_match = re.search(r'\{[\s\S]*\}', raw_resp, re.DOTALL)
        if not json_match:
            return products
        obj = json.loads(json_match.group())
        final_pid_list = obj.get("final_product_ids", [])
        if not final_pid_list or len(final_pid_list) != len(products):
            return products
        pid_to_item = {
            item["product"]["product_id"]: item for item in products
        }
        result = []
        for pid in final_pid_list:
            if pid in pid_to_item:
                result.append(pid_to_item[pid])
        if len(result) == len(products):
            print(f"[LLMStructSort] 排序完成！最终顺序完全对齐产品数={len(result)}")
            return result
        else:
            return products
    except Exception as e:
        print(f"[LLMStructSort] 出错了，fallback: {e}")
        return products

"""
模糊意图 LLM 推理器：
输入：用户模糊自然语言
输出：从本项目数据库真实 Schema 里推理出 精确的子品类/关键词
完全不允许返回库里没有的虚构品类，返回结果直接指导检索
"""
import sys, os, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.schema_aware_agent import GLOBAL_SCHEMA
from services.llm_service import llm_simple_call

LLM_FUZZY_REASON_PROMPT = r"""你是一个"精确的导购意图分析器"。你手头现在有如下真实数据库 Schema：
=== 数据库真实存在的类目 ===
{CATE_LIST}

=== 每个类目下面真实存在的子品类 ===
{SUB_MAP}

用户输入的查询："{USER_QUERY}"

任务：你必须严格从上面 Schema 列表中挑选，分析用户模糊描述背后最真实匹配的1-2个子品类，输出纯 JSON，不要任何别的文字。
返回格式示例：
{{"matched_sub": ["咖啡", "功能饮料"], "matched_category": "食品饮料"}}

规则：
1. 如果你觉得用户模糊描述完全不匹配库里任何Schema，matched_sub返回空数组
2. 绝对不能编造库里不存在的子品类名字
3. 优先选用户描述最相关的1-2个
"""

def llm_reason_fuzzy_intent(user_query: str):
    """
    让大模型从库真实Schema里推理用户模糊意图对应的精确子品类
    不是硬编码字典，是智能语义映射
    """
    if not user_query or len(user_query) < 2:
        return None, None

    cate_list_str = str(sorted(list(GLOBAL_SCHEMA["all_categories"])))
    sub_map_str = ""
    for c, sub_set in GLOBAL_SCHEMA["category_to_subs"].items():
        sub_map_str += f"  '{c}' -> {sorted(list(sub_set))}\n"

    final_prompt = LLM_FUZZY_REASON_PROMPT.format(
        CATE_LIST = cate_list_str,
        SUB_MAP = sub_map_str,
        USER_QUERY = user_query
    )

    try:
        raw_resp = llm_simple_call(final_prompt)
        print(f"[LLMReason] 用户输入='{user_query}' 大模型返回: {raw_resp}")
        import re
        json_match = re.search(r'\{.*\}', raw_resp, re.DOTALL)
        if not json_match:
            return None, None
        obj = json.loads(json_match.group())
        matched_sub_list = obj.get("matched_sub", [])
        matched_cate = obj.get("matched_category")
        if matched_sub_list and len(matched_sub_list) > 0:
            # 取第一个最相关的子品类
            final_sub = matched_sub_list[0]
            # 验证子品类是否真的在库Schema里，防止幻觉
            valid = False
            for c in GLOBAL_SCHEMA["all_categories"]:
                if final_sub in GLOBAL_SCHEMA["category_to_subs"].get(c, set()):
                    valid = True
                    matched_cate = c
                    break
            if valid:
                print(f"[LLMReason Success] 最终结果 -> category='{matched_cate}' sub='{final_sub}'")
                return matched_cate, final_sub
    except Exception as e:
        print(f"[LLMReason 出错了回退] {e}")
        return None, None
    return None, None

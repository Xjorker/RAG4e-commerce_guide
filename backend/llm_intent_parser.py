"""
完全由大模型驱动的结构化意图识别器
=================================
不写任何硬编码规则，全靠LLM理解自然语言，返回JSON格式结果
输出格式：
{
    "sub_category": "字符串 / null，目标子品类名称",
    "target_brand": "字符串 / null，指定要的品牌",
    "exclude_brands": ["华为", ...] 要排除的品牌列表
    "max_price": 数字 / null，价格上限
    "color": "字符串 / null，目标颜色",
    "intent_type": "new_query / pure_inherit",
    "note": "大模型自己的解析说明"
}
"""
import json
from llm_service import chat_simple

SYSTEM_PROMPT = '''你是专业的电商导购意图解析专家，请完全理解用户的自然语言，输出严格合法JSON，不能输出任何JSON以外的内容。

输出字段说明：
1. sub_category: 精准提取用户要的商品子品类，可选值只能从下面列表选：
   "笔记本电脑", "智能手机", "平板电脑", "精华", "跑步鞋", "篮球鞋", "登山鞋", "T恤", "卫衣", "运动长裤", "帽子", "速干衣", "咖啡", "饮料", "牛奶酸奶", "零食糕点", "方便面"，如果用户没提品类就返回null
2. target_brand: 用户明确指定"要XX品牌"，提取品牌名，否则返回null
3. exclude_brands: 数组，用户说"不要/别/除了XX品牌"，把提取到的品牌名放数组，空的话返回[]
4. max_price: 用户明确说价格不超过多少，提取数字，例如"15000以内"就是15000，没提返回null
5. color: 用户提了商品颜色，例如"黑色的"，返回"黑"，"红色"返回"红"，没提返回null
6. intent_type: 判断用户这轮是不是完全没有任何新的筛选条件，只是基于上轮结果继续说的，返回"pure_inherit"，否则"new_query"
7. note: 简单写一句你的解析说明

现有品牌参考库，方便你准确提取：
"Apple", "华为", "苹果", "小米", "联想", "OPPO", "vivo", "戴尔", "华硕", "惠普", "微软", "雅诗兰黛", "兰蔻", "SK-II", "资生堂", "科颜氏", "巴黎欧莱雅", "薇诺娜", "玉兰油", "珀莱雅", "安热沙", "Nike", "Adidas", "李宁", "HOKA", "特步", "安踏", "The North Face", "萨洛蒙", "优衣库", "lululemon", "始祖鸟", "三顿半", "雀巢", "农夫山泉", "元气森林", "东鹏特饮", "红牛", "伊利", "蒙牛", "三只松鼠", "良品铺子", "康师傅", "统一"
'''

def parse_user_intent(query: str):
    user_prompt = f"用户输入：{query}\n请输出严格合法JSON"
    try:
        raw = chat_simple(SYSTEM_PROMPT, user_prompt, temperature=0.0)
        raw_clean = raw.strip()
        if raw_clean.startswith('```json'): raw_clean = raw_clean[7:]
        if raw_clean.startswith('```'): raw_clean = raw_clean[3:]
        if raw_clean.endswith('```'): raw_clean = raw_clean[:-3]
        raw_clean = raw_clean.strip()
        obj = json.loads(raw_clean)
        print(f"[LLM意图识别] 查询={query} 解析结果={obj}")
        return obj
    except Exception as e:
        print(f"[LLM意图识别] 异常={e}，返回空默认值")
        return {
            "sub_category": None,
            "target_brand": None,
            "exclude_brands": [],
            "max_price": None,
            "color": None,
            "intent_type": "new_query",
            "note": "解析出错"
        }

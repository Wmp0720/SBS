
import datetime
import logging
import textwrap

import yaml
import uuid
import time
import json
from typing import List, Dict, Any, Tuple, Set

from mpmath import re

from utils.vivo_model import vivo_GPT

# ========= 规则加载 =========
def load_rules(yaml_path="config/scoring_rules4.yaml"):
    """
    加载评分规则 YAML 文件
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        rules = yaml.safe_load(f)
        return rules

# ======== 新增：离线学习Prompts ========

def create_loss_analysis_prompt(loss_samples_str: str) -> str:
    """为败因分析（RCA）生成Prompt"""
    prompt = f"""
你是一位逻辑严谨的根本原因分析（RCA）专家。你的任务是分析以下自研模型明确失败的案例，找出导致其失败的核心、可复现的模式。请将这些模式总结为一系列机器可读的JSON对象数组。

【任务背景】
失败案例指的是"自研模型"的表现显著劣于"竞品模型"。你需要从这些案例中，提炼出可以作为"红线"或"警报"的通用性失败原因。

【失败案例集（Markdown格式）】
{loss_samples_str}

【任务要求】
1. 归纳出通用的"失败触发器"（trigger_name），例如"事实性错误"、"核心指令遗忘"、"不合理拒答"等。
2. 为每个触发器提供：
   - `description`: 一句简洁的描述。
   - `keywords`: 一组相关的关键词，用于未来可能的文本匹配。
   - `severity`: 该错误的严重性评级，只能从 ["弱智", "不合格"] 中选择。
3. 你的输出必须是、且仅是一个严格的JSON格式的列表（List of Objects），不要包含任何额外的介绍、总结或Markdown标记。

【输出格式】
[
  {{
    "trigger_name": "事实性错误",
    "description": "回答中包含与公认事实相悖的、可被验证的错误信息。",
    "keywords": ["错误", "不正确", "与事实不符", "过时信息", "伪造信息"],
    "severity": "不合格"
  }},
  {{
    "trigger_name": "核心指令遗忘",
    "description": "未能遵循用户在Prompt中明确提出的格式、长度、角色或内容等核心约束。",
    "keywords": ["未遵循", "未执行", "遗忘", "忽略", "未按"],
    "severity": "不合格"
  }}
]

请开始分析。
"""
    return prompt


def create_win_analysis_prompt(win_samples_str: str) -> str:
    """为胜因分析生成Prompt"""
    prompt = f"""
你是一位经验丰富的产品分析专家。你的任务是分析以下自研模型明确获胜的案例，提炼出决定性的优势模式。请将这些模式总结为一系列机器可读的JSON对象数组。

【任务背景】
获胜案例指的是"自研模型"的表现显著优于"竞品模型"。你需要从这些案例中，提炼出可以作为"亮点"或"标杆"的通用性优势原因。

【获胜案例集（Markdown格式）】
{win_samples_str}

【任务要求】
1. 归纳出通用的"胜利模式"（pattern_name），例如"结构化呈现"、"提供增量价值"、"创造性解决方案"等。
2. 为每个模式提供：
   - `description`: 一句简洁的描述。
   - `keywords`: 一组相关的关键词，用于未来可能的文本匹配。
   - `impact`: 该优势的影响力评级，只能从 ["高", "中", "低"] 中选择。
3. 你的输出必须是、且仅是一个严格的JSON格式的列表（List of Objects），不要包含任何额外的介绍、总结或Markdown标记。

【输出格式】
[
  {{
    "pattern_name": "结构化呈现",
    "description": "采用清晰的层级结构、列表或表格来组织信息，便于用户快速获取关键内容。",
    "keywords": ["结构化", "层次", "列表", "表格", "清晰", "重点突出"],
    "impact": "高"
  }},
  {{
    "pattern_name": "提供增量价值",
    "description": "在回答基础问题之外，提供了额外的、有价值的信息或见解。",
    "keywords": ["额外", "深入", "扩展", "补充", "增值", "深入分析"],
    "impact": "中"
  }}
]

请开始分析。
"""
    return prompt


def create_reflection_prompt(golden_samples_str: str, rules: dict):
    """
    构建一个让LLM学习和反思精标样本的Prompt。
    目标是让LLM理解人类标注员和先前LLM标注结果的差异，并提炼出其中的评判逻辑。
    """
    prompt = f"""
你是一名顶级的评测元分析师，你的任务是深入学习一套高质量的"精标数据集"，并从中提炼出人类专家的核心标注逻辑，特别是要理解他们的评判尺度和宽松倾向。

【任务背景】
我们有一个自动化评测系统，系统中的LLM标注员有时会因为过于"专业"和"严格"而与人类专家的判断不一致。人类专家在长时间标注后，会更关注那些真正影响用户体验的明显错误，对于一些细枝末节的问题则倾向于宽容。
你的任务就是学习并模仿这种合理"宽容的专业主义"和人类的判断思维模式。

【你的核心任务】
1.  对比分析：仔细对比每一条样本中"标注员_"系列字段和"LLMs_"系列字段的异同。
2.  逻辑提炼与尺度校准:
    *   重点关注人类标注为"13无问题"的案例：当人类标注"13无问题"，而LLM却找出了问题时，要深刻反思：人类为什么会认为这些问题不重要？是不是这些问题在真实用户场景下影响不大？
    *   识别"关键阈值": 分析人类在什么情况下才会判定一个问题是"不合格"或"弱智"。提炼出触发人类给出负面评价的"最低容忍底线"。
3.  归纳总结：将你从所有样本中学习到的评测逻辑、判断尺度，总结成一套新的评测指南。

【精标数据集样本】
下面就是你需要学习的精标数据，以Markdown表格形式呈现：

{golden_samples_str}

【你的输出】
请不要逐条分析样本。请你站在一个经验丰富、看过成千上万条数据、有点"疲劳感"的互联网标注员的视角，将你提炼出的【宽容性评测指南】以要点的形式总结出来。但是必须要确保答案的真实性、符合常理、提供用户实际想要的信息和现实的实际情况为原则性底线，

请按以下格式输出你的总结：

"我是一名经验丰富的互联网标注员，在快速评估大量数据时，我会遵循以下务实、高效的评判原则：
1.  [你提炼出的第一条宽容原则]: (例如：优先关注核心任务完成度。只要模型的主要回答内容正确且切题，对于一些轻微的表述瑕疵或格式不完美，我倾向于忽略，给予'13无问题'。)
2.  [你提炼出的第二条宽容原则]: (例如：关于"冗长"和"简略"，我的判断阈值会放宽。除非内容重复得令人烦躁，或者信息缺失到无法使用的地步、并未提供用户实际想要信息，或者自研和竞品的回复上存在明显的内容差距，否则我不会轻易标注这两类问题。)
3.  [你提炼出的第三条宽容原则]: (例如：只有当出现肉眼可见的、无需深入思考就能发现的事实性错误（如"地球是方的"）、严重逻辑矛盾（前后矛盾）或完全不遵从指令时，我才会给出'不合格'或更低的评价。)
4.  [你提炼出的第四条宽容原则]: (例如：在Side-by-Side对比中，如果两个模型的回答"大差不差"，在几秒钟内看不出显著优劣，我会直接判定为'平'，以保证标注效率。)
5.  ..."
"""
    return prompt
# ========= Prompt 构造（单模打标）=========
def create_single_model_prompt(run_time, history_text, resp_text, dimension, rules):
    """
    针对一个模型的多轮问答对，标注主要问题。
    仅产出：主要问题（来自"单个大模型主要问题"集合，鼓励多选、逗号分隔）；
    若属于 12弱智/14优质，还需在"优质弱智主要问题"中给出具体原因（来自维度优质标签或弱智标签）。
    """
    dim_rule = rules.get("dimension_definitions", {}).get(dimension, {})
    description = dim_rule.get("description", "")
    notes = dim_rule.get("注意事项", [])
    hq_labels = dim_rule.get("优质标签", []) or []
    question_show = rules.get("单个大模型标注示例", [])
    
    single_labels_spec = rules.get("单个大模型主要问题", {})
    # dumb_labels = rules.get("弱智标签", []) or rules.get("满意度", {}).get("弱智标签", [])

    # 从rules中获取学习到的指南
    learned_guidelines = rules.get('learned_guidelines', '无')

    # 从rules中加载失败触发器知识库
    loss_triggers_str = yaml.dump(rules.get('loss_triggers', []), allow_unicode=True, sort_keys=False)

    prompt = f"""
    【你的角色和心态】
你是一名经验丰富、看过成千上万条数据的互联网标注员。你的评判核心是效率和用户体感。你需要快速判断，抓大放小，不要在细枝末节上过度"钻牛角尖"。

【你的核心评判依据】
在进行本次评测时，你必须严格遵循你之前从精标数据中学习并总结出的以下【宽容性评测指南】：

{learned_guidelines}


【任务指令】
现在是 {run_time}（2025年9月1日），案例的对话都是在目前时间之前发生的，请运用上述角色心态和评判依据以及下面的规则，目标是从真实用户体验的角度，对以下对话进行评测，其中的问题都是用户真实问出。请记住，只有在遇到真正影响理解和使用的明显错误时，才给出负面评价。如果双方表现"大差不差"，或问题不影响核心任务，就大胆地给出"13无问题"或"平"。


请仅基于"该模型"的多轮对话，对最后一轮对话中大模型的回答的多轮记忆、回答内容、格式以及其他等多方面问题表现标注存在的【主要问题】：
- 关于【主要问题】的标注：你可以选择1-3个最相关的问题标签。如果只有一个问题，就只给一个；如果有多个，请都列出，但总数不要超过3个。
- 若为"12弱智"，请在"优质弱智主要问题"中给出来自"弱智标签"的具体原因（可多选）。
- 若为"14优质"，请在"优质弱智主要问题"中给出本维度的"优质标签"（可多选）。
- 否则，请从"单个大模型主要问题"中多选，逗号分隔。
- 对于案例中引用的"摘要"和"参考文献"等予以信任，并且对于提及的时间，与2025年相差不多即可。
- 禁止输出不在清单内的标签。

【评判参考】
为了让你更好地评判失败，如下提供了由实际案例判断得出地"失败触发器清单"，可以作为你判断时的参考：
- 第一步：对照"失败触发器清单"进行检查。请仔细阅读下面的清单，判断模型的回答是否明确命中了其中任何一条。这是最重要的步骤，用于识别严重错误。
- 第二步：标注"主要问题"。结合第一步的检查结果和你的综合判断，从"单个大模型主要问题标签全集"中选择1-3个最核心的问题标签。
    - 如果第一步命中了失败触发器，那么"主要问题"必须包含能反映该触发器类型的问题标签（例如，命中"事实性错误"触发器，则主要问题应包含"2内容质量差_1.内容错误"）。
    - 如果没有命中任何触发器，再根据用户体验、信息量等因素，从标签全集中选择最合适的问题。
    - 如果没有任何问题，请标注 "13无问题"。

【失败触发器清单】
{loss_triggers_str}

---

【当前维度】{dimension}
- 维度说明：{description}
- 注意事项：{notes}
- 该维度可用优质标签（仅当主要问题=14优质时使用，可多选）：{hq_labels}

【单个大模型主要问题标签全集】（只能从中选择，多选用中文逗号分隔）：
{single_labels_spec}

【对话上下文（不含最后一轮）】：
{history_text}

【本轮用户-模型问答对】：
{resp_text}

【主要问题标注示例】：
{question_show}

---

请输出严格 JSON：
{{
  "主要问题": "多个标签用中文逗号分隔",
  "优质弱智主要问题": "若包含12弱智或14优质请在此写具体原因；否则留空",
  "标注理由": "一句话解释你做出以上判断的理由（简洁）"
}}"""
    return prompt


# ========= Prompt 构造（胜平负裁判，只有程序无法判定时才会用到）=========
def create_winloss_tiebreak_prompt(dimension,  v_history, c_history, v_resp, c_resp, a_main_issues, b_main_issues,rules):

    sbs_labels = rules.get("SBS主要问题", [])
    question_show = rules.get("SBS标注示例", [])
    dim_rule = rules.get("dimension_definitions", {}).get(dimension, {})
    description = dim_rule.get("description", "")
    notes = dim_rule.get("注意事项", [])

    # 加载结构化知识库
    loss_triggers_str = yaml.dump(rules.get('loss_triggers', []), allow_unicode=True, sort_keys=False)
    win_patterns_str = yaml.dump(rules.get('win_patterns', []), allow_unicode=True, sort_keys=False)

    # 从rules中获取学习到的指南
    learned_guidelines = rules.get('learned_guidelines', '无')

    prompt = f"""
你是一个经过"精标数据"深度训练的、顶级的用户视角评审员。目标是从真实用户体验的角度，对"用户-大模型"对话进行打标，其中的问题都是用户真实问出。
在进行本次评测时，除了通用的评测规则外，你必须严格遵循你之前从精标数据中学习并总结出的以下【核心评判逻辑和原则】：

{learned_guidelines}

关于【大模型A/B_SBS主要问题】的标注：你可以为每个模型选择1-3个最相关的SBS问题标签。如果模型没有明显问题，则标注 "13无问题"。如下也是根据实际判断案例得出的判断规则，可作为你标注的参考：

1.  第一步：检查失败触发器
    对照下面的【失败触发器清单】，检查模型A和模型B的回答是否明确命中了其中任何一条？
    【失败触发器清单】
    {loss_triggers_str}

2.  第二步：评估胜利模式
    对照下面的【胜利模式清单】，评估模型A和模型B各自符合哪些胜利模式？
    【胜利模式清单】
    {win_patterns_str}

3.  第三步：综合决策
    基于以上分析以及双方的"初步诊断问题"，做出最终的'胜/平/负'判断。决策逻辑如下：
    - 致命错误优先: 任何一方命中`失败触发器`，直接判负。若双方都命中，则问题更严重（按严重性评级）或数量更多的一方判负。
    - 优势决定胜负: 若双方均未命中`失败触发器`，则符合`胜利模式`更多或更具决定性优势的一方判胜。
    - 问题多者劣: 若双方优劣势不明显，则"初步诊断问题"更多或更严重的一方判负。
    - 无法区分则平: 若以上都无法区分，则判为"平"。

4.  第四步：生成分析报告
    将你的决策过程和关键发现，填充到下面的JSON模板中。`裁判分析报告`需要简洁地概括你的决策理由。

【输出格式】
请严格按照以下JSON格式输出，不要包含任何额外说明：
{{
  "大模型A_命中的失败触发器": ["如果命中，在此列出触发器名称，可多选"],
  "大模型B_命中的失败触发器": ["如果命中，在此列出触发器名称，可多选"],
  "大模型A_符合的胜利模式": ["如果符合，在此列出模式名称，可多选"],
  "大模型B_符合的胜利模式": ["如果符合，在此列出模式名称，可多选"],
  "裁判分析报告": "总结你的核心决策依据，例如：模型A命中了"事实性错误"触发器，直接判负。模型B虽无亮点，但没有严重错误。"
}}

---

现在你获得了两个模型在同一任务下的多轮对话表现。

请仅基于"该模型"的多轮对话，对最后一轮对话（本轮）中大模型的回答的多轮记忆、回答内容、格式以及其他等多方面问题表现进行对比，
然后对存在问题的一方标注主要问题，问题标签需要从下面的选择中进行选择：
【SBS标签集合】（只能从中选择，逗号分隔）：
{sbs_labels}
【SBS标注示例】：
{question_show}

【大模型A：上下文】
{v_history}

【大模型A：本轮】
{v_resp}

【大模型B：上下文】
{c_history}

【大模型B：本轮】
{c_resp}

上述对话属于【维度】【{dimension}】，该维度下的说明如下：{description}；有注意事项如下：{notes}

请严格遵循以下要求：
1. 对比打标时，只能使用提供的 SBS标签集合，不得引入集合外标签。
2. 标注时，必须为大模型A 和大模型B 各自输出一个主要问题：
   - 如果模型确实存在问题，选择一个或多个最符合的标签；
   - 如果模型没有明显问题，则强制标注【13无问题】。
3. 判定胜负时，必须结合：
   - 大模型A 与大模型B 各自的主要问题（已给出）
   - 以及本次对比过程中发现的主要问题
   来综合判定。

【胜平负判定规则】
参考上面选取的"主要问题标签"和"标签严重程度"进行 胜平负 判定，具体如下:
1. 标签严重程度参考如下（从严重到轻微）：
   12弱智 > 1未提供需要信息 > 2内容质量差_1.内容错误 > 2内容质量差 = 3多轮效果不佳 > 4冗长 = 5简略 = 6语言表达不佳 > 7格式及呈现不佳 = 8内容要素不佳 > 13无问题 > 14优质
2. 判定顺序：
   - 首先根据"标签严重程度"的来判定，严重者为负，另一方为胜；
   - 如果双方最严重的标签等级一致，则进入下一步。
3. 在最严重的等级中，根据该等级下的标签个数判定，多者判负；
4. 如果在最严重的等级中标签一致，但一方还有其他问题标签，则该方为负（因为问题更多）；
5. 如果双方的问题标签完全一致，或者等级完全一致且无法区分，则将大模型A和大模型B的对话整体表现再交由大模型自由判断胜/平/负。


大模型A存在的主要问题：{a_main_issues},
大模型B存在的主要问题：{b_main_issues}
【示例】：
- 若模型A存在的问题标签：12弱智_……，模型B存在的问题标签：1未提供需要信息_1.回答不相关，大模型A_SBS主要问题：4冗长_1. 篇幅过长；大模型A_SBS主要问题：5简略_2. 拓展过少。 则最终结果A负，B胜，裁判说明：因为严重程度：大模型A【12弱智】 > 大模型B【1未提供需要信息】。
- 若模型A存在的问题标签：1未提供需要信息_1.回答不相关，模型B存在的问题标签：2内容质量差_1.内容错误，大模型A_SBS主要问题：2内容质量差_4.实用性不佳；大模型A_SBS主要问题：8内容要素不佳_3.无用资源过多。则最终结果A负，B胜,裁判说明：因为严重程度：大模型A【1未提供需要信息】 >大模型B【2内容质量差_1.内容错误】。
- 若模型A存在的问题标签：1未提供需要信息_1.回答不相关，模型B存在的问题标签：1未提供需要信息_1.回答不相关, 6语言表达不佳_1.AI感强，大模型A_SBS主要问题：2内容质量差_4.实用性不佳；大模型A_SBS主要问题：8内容要素不佳_3.无用资源过多。则最终结果A胜，B负,裁判说明：因为最严重的标签等级大模型A=大模型B，但是B额外有主要问题。
- 若模型A存在的问题标签：13无问题，模型B存在的问题标签：13无问题，大模型A_SBS主要问题：2内容质量差_4.实用性不佳；大模型A_SBS主要问题：8内容要素不佳_3.无用资源过多。则最终结果A负，B胜,裁判说明：因为严重程度：大模型A【2内容质量差】 >大模型B【8内容要素不佳】。
-若模型A和模型B的问题标签完全一样，或等级一致无法区分，则结果为"平"。

最终输出格式要求：
- 只输出严格 JSON，不要多余叙述。
- JSON 字段如下：
{{
  "大模型A_SBS主要问题": "从集合中选择或13无问题，若有多个用中文逗号隔开",
  "大模型B_SBS主要问题": "从集合中选择或13无问题，若有多个用中文逗号隔开",
  "大模型A竞品对比": "胜/平/负",
  "裁判说明": "一句话简洁解释理由"
}}
"""
    return prompt


# ================= 第一步 - 对比分析 Prompt =================
def create_sbs_analysis_prompt(dimension, v_history, c_history, v_resp, c_resp, rules):
    """
    CoT 第一步：进行事实收集和对比分析，不进行最终裁决。
    增加了更详细的指引和角色设定。
    """
    sbs_labels = rules.get("SBS主要问题", [])
    sbs_examples = rules.get("SBS标注示例", [])
    dim_rule = rules.get("dimension_definitions", {}).get(dimension, {})
    description = dim_rule.get("description", "")
    notes_list = dim_rule.get("注意事项", [])
    notes = "\n- ".join(notes_list) if isinstance(notes_list, list) else notes_list

    # 加载知识库
    loss_triggers_str = yaml.dump(rules.get('loss_triggers', []), allow_unicode=True, sort_keys=False)
    win_patterns_str = yaml.dump(rules.get('win_patterns', []), allow_unicode=True, sort_keys=False)

    learned_guidelines = rules.get('learned_guidelines', '无')

    prompt = f"""
【你的角色】
你是一位客观、细致、只相信证据的评测分析员。你的任务是像法庭的"证据书记员"一样，完整地记录双方的表现，但绝对不要做出任何"胜/平/负"的结论性判断。你的输出将作为后续"法官"裁决的唯一依据。

【核心任务指令】
请仔细阅读并对比"大模型A"和"大模型B"的对话表现，然后完成以下三项事实分析任务：

1.  对比问题标注 (Side-by-Side Issues):
    *   目标: 从对比的视角，找出每个模型相对另一方的具体问题。
    *   操作: 从【SBS标签集合】中，为两个模型分别选择2-4个最能体现其相对优劣的问题标签，可以多选同一个一级标签主要问题下的分问题，更建议选不同一级标签下的主要问题，这样可以更好提高命中率。
    *   注意: 如果某个模型在对比中没有明显问题，请为其标注为 "13无问题"。

2.  失败触发器检查 (Loss Trigger Check):
    *   目标: 识别出那些不可容忍的、会导致直接判负的严重错误。
    *   操作: 对照【失败触发器清单】，检查两个模型的回答是否明确命中了其中任何一条。

3.  胜利模式评估 (Win Pattern Evaluation):
    *   目标: 识别出那些能体现显著优势的、决定性的亮点表现。
    *   操作: 对照【胜利模式清单】，评估两个模型各自符合哪些胜利模式。
    
在进行本次评测时，除了通用的评测规则外，你必须严格遵循你之前从精标数据中学习并总结出的以下【核心评判逻辑和原则】：

{learned_guidelines}

【输出格式】
你的输出必须且只能是一个严格的JSON对象，不要包含任何额外说明或裁决性语言。请将你的分析结果填入以下模板：
{{
  "大模型A_SBS主要问题": "从SBS标签集合中选择，可多选，用中文逗号分隔",
  "大模型B_SBS主要问题": "从SBS标签集合中选择，可多选，用中文逗号分隔",
  "大模型A_命中的失败触发器": ["如果命中，在此列出触发器名称，可多选"],
  "大模型B_命中的失败触发器": ["如果命中，在此列出触发器名称，可多选"],
  "大模型A_符合的胜利模式": ["如果符合，在此列出模式名称，可多选"],
  "大模型B_符合的胜利模式": ["如果符合，在此列出模式名称，可多选"]
}}

---
【评测上下文信息】
*   评测维度: {dimension} - {description}
*   维度注意事项: 
    - {notes}
*   SBS标签集合 (只能从中选择): 
{sbs_labels}
*   失败触发器清单 (用于检查):
{loss_triggers_str}
*   胜利模式清单 (用于评估):
{win_patterns_str}

---
【待分析的对话材料】

【大模型A：上下文】
{v_history}
【大模型A：本轮】
{v_resp}

---
【大模型B：上下文】
{c_history}
【大模型B：本轮】
{c_resp}

---
【参考：SBS标注示例】
{sbs_examples}
"""
    return prompt


# ================= 第二步 - 最终裁决 Prompt =================
def create_final_judgment_prompt(analysis_json_str: str, a_single_main_issues: str, b_single_main_issues: str,
                                 rules: dict):
    """
    CoT 第二步：基于已有的、结构化的分析档案，做出最终的胜负裁决。
    增加了更丰富的规则、逻辑和示例，使其裁决能力更强。
    """
    learned_guidelines = rules.get('learned_guidelines', '无')

    prompt = f"""
【你的角色】
你是一位经验丰富、逻辑严谨、遵循判例的高级评测法官。你不需要关心原始对话的细枝末节，你的唯一任务是基于下属"分析员"提交的、结构化的【案件档案】，做出最终的"胜/平/负"裁决，并给出清晰、简洁的裁决理由。

【你的核心判决依据】
1.  首要原则: 你必须严格遵循你从大量精标数据中学习并总结出的以下【核心评判逻辑和原则】。
    {learned_guidelines}
2.  判例法: 你必须严格参考下面详细说明的【胜平负判定规则】。

---
【案件档案（由分析员提交的全部证据）】
{analysis_json_str}

提醒：以上档案中已包含了对双方的对比问题(SBS)、失败触发器和胜利模式的全面分析。

---
【胜平负判定规则】
请严格按照以下顺序和逻辑进行决策：

1.  第一优先级：致命错误裁定 (Fatal Error Ruling)
    *   检查【案件档案】中的`失败触发器`字段。
    *   规则: 任何一方命中`失败触发器`，直接判负。若双方都命中，则问题更严重（按知识库中的严重性评级）或数量更多的一方判负。此规则拥有最高否决权。

2.  第二优先级：显著优势裁定 (Clear Advantage Ruling)
    *   若双方均无致命错误，则检查`胜利模式`字段。
    *   规则: 符合`胜利模式`更多或优势更具决定性的一方判胜。

3.  第三优先级：问题严重性与数量对比 (Issue Severity & Count Comparison)
    *   若优劣势不明显，则综合对比双方的全部问题（包括你收到的"单模主要问题"和【案件档案】中的"SBS主要问题"）。
    *   标签严重性排序 (从重到轻): 
        `12弱智 > 1未提供需要信息 > 2内容质量差_1.内容错误 > 2内容质量差 = 3多轮效果不佳 > 4冗长 = 5简略 = 6语言表达不佳 > 7格式及呈现不佳 = 8内容要素不佳 > 13无问题 > 14优质`
    *   判定顺序:
        a. 比等级: 找出双方最严重的问题标签，按上述排序比较，问题更严重者判负。
        b. 比数量: 若最严重等级相同，则比较在该等级下的问题标签数量，多者判负。
        c. 比总数: 若还无法区分，则比较问题总数，多者判负。

4.  最终裁定：平局 (Tie Ruling)
    *   若以上所有规则都无法明确区分优劣（例如，双方问题标签完全一致），则判为"平"。
    

---
【辅助信息：单模初步诊断问题（仅供参考）】
*   大模型A的初步诊断问题: {a_single_main_issues}
*   大模型B的初步诊断问题: {b_single_main_issues}

---
【裁决示例】
- 示例1: 档案显示A命中了"事实性错误"触发器，B没有。裁决: A负B胜。理由: 模型A存在致命错误，直接判负。
- 示例2: 档案显示A、B均无触发器。但A符合"结构化呈现"和"提供增量价值"两个胜利模式，B只有一个。裁决: A胜B负。理由: 模型A的亮点优势更显著。
- 示例3: 档案无触发器和胜利模式。A的单模问题是"4冗长"，B的单模问题是"2内容质量差"。根据严重性排序，"2内容质量差" > "4冗长"。裁决: B负A胜。理由: B的问题严重等级高于A。
- 示例4: 双方最严重的问题都是"4冗长"，但A有两个冗长类问题，B只有一个。裁决: A负B胜。理由: 同级问题下，A的数量更多。

---
【你的输出】
请将你的最终裁决结果严格按照以下JSON格式输出，不要包含任何额外说明：
{{
  "大模型A竞品对比": "胜/平/负",
  "裁判说明": "（必填）用一句话简洁概括你的核心决策依据。例如：模型A因命中"事实性错误"触发器而被判负。"
}}
"""
    return prompt



# ========= 模型调用 =========
def test(prompt, model="o3", verbose=False, show_prompts=False):
    """
    调用 vivo_GPT 模型，支持超时重试机制
    """
    result = vivo_GPT(prompt, model=model, sessionId=str(uuid.uuid4()), verbose=verbose, show_prompts=show_prompts)
    count = 0
    while isinstance(result, str) and "timeout" in result and count < 3:
        time.sleep(1)
        count += 1
        result = vivo_GPT(prompt, model=model, sessionId=str(uuid.uuid4()), verbose=verbose, show_prompts=show_prompts)
    return result


# ========= 知识问答维度特殊处理 =========
def evaluate_knowledge_qa_with_source_check(question: str, v_answer: str, c_answer: str,
                                          v_history: str = "", c_history: str = "",
                                          rules: dict = None, show_prompts: bool = False) -> Dict[str, Any]:
    """
    知识问答维度的特殊评估，包含信息源事实性检测

    Args:
        question: 用户问题
        v_answer: 自研模型回答
        c_answer: 竞品模型回答
        v_history: 自研模型对话历史
        c_history: 竞品模型对话历史
        rules: 评分规则配置
        show_prompts: 是否显示完整的prompt内容

    Returns:
        知识问答维度评估结果
    """
    if rules is None:
        rules = load_rules()

    try:
        # 导入知识问答裁判
        from utils.knowledge_qa_judge import KnowledgeQAJudge

        # 初始化裁判
        judge = KnowledgeQAJudge(rules, show_prompts=show_prompts)

        # 执行知识问答SBS评估
        result = judge.evaluate_knowledge_qa(
            question, v_answer, c_answer, v_history, c_history
        )

        return result

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"知识问答维度评估失败: {e}")

        # 降级到普通评估
        return _fallback_evaluation(question, v_answer, c_answer, v_history, c_history, rules)


def _fallback_evaluation(question: str, v_answer: str, c_answer: str,
                        v_history: str = "", c_history: str = "",
                        rules: dict = None) -> Dict[str, Any]:
    """
    降级评估函数，当知识问答特殊评估失败时使用

    Args:
        question: 用户问题
        v_answer: 自研模型回答
        c_answer: 竞品模型回答
        v_history: 自研模型对话历史
        c_history: 竞品模型对话历史
        rules: 评分规则配置

    Returns:
        降级评估结果
    """
    if rules is None:
        rules = load_rules()

    # 使用普通的SBS评估
    sbs_prompt = create_sbs_analysis_prompt(
        "知识问答", v_history, c_history, v_answer, c_answer, rules
    )

    analysis_result = test(sbs_prompt, model="o3", show_prompts=show_prompts)

    # 解析分析结果
    try:
        analysis_json = json.loads(analysis_result)
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', analysis_result, re.DOTALL)
        if json_match:
            analysis_json = json.loads(json_match.group())
        else:
            analysis_json = {
                "大模型A_SBS主要问题": "13无问题",
                "大模型B_SBS主要问题": "13无问题",
                "大模型A_命中的失败触发器": [],
                "大模型B_命中的失败触发器": [],
                "大模型A_符合的胜利模式": [],
                "大模型B_符合的胜利模式": []
            }

    # 生成最终裁决提示
    final_prompt = create_final_judgment_prompt(
        json.dumps(analysis_json, ensure_ascii=False),
        analysis_json.get("大模型A_SBS主要问题", "13无问题"),
        analysis_json.get("大模型B_SBS主要问题", "13无问题"),
        rules
    )

    # 获取最终裁决
    final_result = test(final_prompt, model="o3", show_prompts=show_prompts)

    # 解析最终结果
    try:
        final_json = json.loads(final_result)
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', final_result, re.DOTALL)
        if json_match:
            final_json = json.loads(json_match.group())
        else:
            final_json = {
                "大模型A竞品对比": "平",
                "裁判说明": "评估结果解析失败，默认平局"
            }

    # 构建最终结果
    fallback_result = {
        "维度": "知识问答",
        "问题": question,
        "自研模型回答": v_answer,
        "竞品模型回答": c_answer,
        "评估方式": "降级评估",
        "大模型A竞品对比": final_json.get("大模型A竞品对比", "平"),
        "LLMs_标注理由": final_json.get("裁判说明", "降级评估结果"),
        "评估时间": datetime.now().isoformat(),
        "异常信息": "知识问答特殊评估失败，使用降级评估"
    }

    return fallback_result


def is_knowledge_qa_dimension(dimension: str, rules: dict = None) -> bool:
    """
    判断是否为知识问答维度

    Args:
        dimension: 维度名称
        rules: 评分规则配置

    Returns:
        是否为知识问答维度
    """
    if rules is None:
        rules = load_rules()

    dimension_definitions = rules.get("dimension_definitions", {})
    return dimension == "知识问答" or dimension in dimension_definitions


def create_knowledge_qa_prompt_with_source_check(question: str, v_history: str, c_history: str,
                                              v_resp: str, c_resp: str, rules: dict) -> str:
    """
    创建包含信息源检测的知识问答评估提示

    Args:
        question: 用户问题
        v_history: 自研模型对话历史
        c_history: 竞品模型对话历史
        v_resp: 自研模型回答
        c_resp: 竞品模型回答
        rules: 评分规则配置

    Returns:
        评估提示
    """
    # 检查是否启用信息源检测
    source_check_enabled = rules.get("source_check_whitelist", [])

    if "知识问答" in source_check_enabled:
        # 使用信息源检测的特殊评估
        return create_knowledge_qa_sbs_prompt_with_source_check(
            question, v_history, c_history, v_resp, c_resp, rules
        )
    else:
        # 使用普通评估
        return create_sbs_analysis_prompt("知识问答", v_history, c_history, v_resp, c_resp, rules)
    
def create_knowledge_qa_sbs_prompt_with_source_check(question: str, v_history: str, c_history: str,
                                                   v_resp: str, c_resp: str, rules: dict, show_prompts: bool = False) -> str:
    """
        创建包含信息源检测的知识问答SBS评估提示

        Args:
            question: 用户问题
            v_history: 自研模型对话历史
            c_history: 竞品模型对话历史
            v_resp: 自研模型回答
            c_resp: 竞品模型回答
            rules: 评分规则配置
            show_prompts: 是否显示完整的prompt内容

        Returns:
            评估提示
    """
    try:
        # 导入信息源检测器
        from utils.source_checker import SourceChecker

        # 初始化信息源检测器
        source_checker = SourceChecker(rules, show_prompts=show_prompts)

        # 执行信息源检测
        v_source_check = source_checker.comprehensive_source_check(question, v_resp)
        c_source_check = source_checker.comprehensive_source_check(question, c_resp)

        # 构建信息源对比文本
        v_sources_text = ""
        if v_source_check.get("补充信息源"):
            v_sources_text = "【自研模型补充信息源】\n" + "\n".join([
                f"- {s['title']}: {s['summary']}" for s in v_source_check["补充信息源"]
            ])

        c_sources_text = ""
        if c_source_check.get("补充信息源"):
            c_sources_text = "【竞品模型补充信息源】\n" + "\n".join([
                f"- {s['title']}: {s['summary']}" for s in c_source_check["补充信息源"]
            ])

        # 获取知识问答评分标准
        qa_criteria = rules.get("dimension_definitions", {}).get("知识问答", {}).get("score_criteria", {})

        prompt = f"""
你是一位专业的知识问答评测专家，请从事实准确性、信息源可靠性、专业深度等角度，对比评估以下两个模型的回答质量。

【评测维度】知识问答
{rules.get("dimension_definitions", {}).get("知识问答", {}).get("description", "")}

【评分标准】
准确性 (满分2分): {qa_criteria.get("准确性", {}).get("rules", {})}
专业性 (满分2分): {qa_criteria.get("专业性", {}).get("rules", {})}
时效性 (满分2分): {qa_criteria.get("时效性", {}).get("rules", {})}
格式 (满分2分): {qa_criteria.get("格式", {}).get("rules", {})}
详略得当 (满分2分): {qa_criteria.get("详略得当", {}).get("rules", {})}
逻辑 (满分2分): {qa_criteria.get("逻辑", {}).get("rules", {})}
回复风格 (满分2分): {qa_criteria.get("回复风格", {}).get("rules", {})}

【用户问题】
{question}

【自研模型回答】
{v_resp}
{v_sources_text}

【竞品模型回答】
{c_resp}
{c_sources_text}

【信息源检测结果对比】
自研模型综合评分: {v_source_check.get('综合评分', '未知')} ({v_source_check.get('评分等级', '未知')})
竞品模型综合评分: {c_source_check.get('综合评分', '未知')} ({c_source_check.get('评分等级', '未知')})

【评测任务】
请严格按照以下步骤进行评测：

1. 事实准确性对比:
   - 检查两个回答中是否存在事实性错误
   - 对比回答的准确性和完整性
   - 评估答案与问题的相关性

2. 信息源质量对比:
   - 对比两个回答中引用的信息源权威性
   - 评估补充信息源的相关性和可靠性
   - 检查信息源的时效性

3. 专业深度对比:
   - 对比回答的专业性和深度
   - 评估知识拓展的合理性
   - 检查逻辑结构的清晰度

4. 用户体验对比:
   - 对比回答的格式和呈现方式
   - 评估信息量的合理性
   - 检查回复风格的自然度

【输出要求】
请严格按照以下JSON格式输出评测结果：
{{
  "大模型A二级满意度": "弱智/不合格/合格/优质",
  "大模型B二级满意度": "弱智/不合格/合格/优质", 
  "大模型A优质弱智主要问题": "",
  "大模型B优质弱智主要问题": "",
  "大模型A竞品对比": "胜/平/负",
  "大模型A主要问题": "主类_子类（可多个，用英文逗号分隔）",
  "大模型B主要问题": "主类_子类（可多个，用英文逗号分隔）",
  "LLMs_标注理由": "基于信息源检测和事实性对比的详细评测理由"
}}

【特别说明】
- 知识问答维度重点关注事实准确性和信息源可靠性
- 对于涉及医疗、法律、金融等敏感内容，必须检查是否有免责声明
- 优先选择信息源更权威、事实准确性更高的回答
- 如果双方表现相当，请给出"平"的评判
"""

        return prompt

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"创建知识问答SBS提示失败: {e}")

        # 降级到普通提示
        return create_sbs_analysis_prompt("知识问答", v_history, c_history, v_resp, c_resp, rules)


if __name__ == "__main__":
    # 测试代码
    test_rules = load_rules()

    # 测试知识问答评估
    test_question = "什么是人工智能？"
    v_answer = "人工智能（AI）是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统。"
    c_answer = "人工智能是指由人类制造出来的机器所表现出来的智能。"

    result = evaluate_knowledge_qa_with_source_check(
        test_question, v_answer, c_answer, rules=test_rules
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
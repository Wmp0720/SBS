
"""
auto_rules.py —— 模糊标签匹配版
核心：
  • keyword2bucket：对“不完整标签/自然语关键词”进行模糊归一
  • main_issues ➜ satisfaction  ：弱智/不合格/合格/优质/未选中
  • decide_winloss_by_rules    ：A vs B 胜/负/平
"""

import re
from typing import Dict, List, Tuple

# 维度优质标签前缀
DIM_QUALITY_PREFIX = ("技能_", "生文_", "问答_", "闲聊_")

# -------- 1. 关键词到桶名映射（可按需扩充） -----------------
KEYWORD2BUCKET = {
    # ======= “弱智”明显错误 =======
    "弱智": "12弱智",
    # ======= 1 未提供需要信息 ======
    "未提供需要信息": "1未提供需要信息",
    "答非所问": "1未提供需要信息",
    "不跟随指令": "1未提供需要信息",
    "不合理拒答": "1未提供需要信息",
    # ======= 2 内容质量差 ==========
    "内容错误": "2内容质量差_1.内容错误",
    "实体错误": "2内容质量差_1.内容错误",
    "信息过时": "2内容质量差_2.内容过时",
    "内容过时": "2内容质量差_2.内容过时",
    "内容质量差":"2内容质量差",
    "要点不全面": "2内容质量差",
    "实用性不佳": "2内容质量差",
    "逻辑不清":   "2内容质量差",
    "执行深度不足": "2内容质量差",
    # ======= 3 多轮效果不佳 ========
    "多轮效果不佳": "3多轮效果不佳",
    "多轮记忆错误": "3多轮效果不佳",
    "多轮逻辑错误": "3多轮效果不佳",
    "任务不持续": "3多轮效果不佳",
    # ======= 4 冗长 =================
    "冗长": "4冗长",
    "拓展过多": "4冗长",
    "篇幅过长": "4冗长",
    "内容重复": "4冗长",
    "无关内容过多": "4冗长",
    # ======= 5 简略 =================
    "简略": "5简略",
    "篇幅过短": "5简略",
    "拓展过少": "5简略",
    "表达过于精简": "5简略",
    # ======= 6 语言表达不佳 =========
    "语言表达不佳": "6语言表达不佳",
    "AI感强": "6语言表达不佳",
    "风格不一致": "6语言表达不佳",
    "无免责声明": "6语言表达不佳",
    "有攻击性":   "6语言表达不佳_4.有攻击性",
    # ======= 7 格式 =================
    "格式": "7格式及呈现不佳",
    "格式及呈现不佳": "7格式及呈现不佳",
    "界面呈现不佳": "7格式及呈现不佳",
    "文字格式不佳": "7格式及呈现不佳",
    # ======= 8 内容要素不佳 =========
    "富媒体": "8内容要素不佳",
    "无用资源": "8内容要素不佳",
    "内容要素不佳": "8内容要素不佳",
    "组织内容形式少": "8内容要素不佳",
    # ======= 优质 ===================
    "有趣好聊": "14优质",
    "专业有深度": "14优质",
    "观点独到": "14优质"
}

# -------------------------------------------------
def _split_labels(labels: str) -> List[str]:
    if not labels:
        return []
    return [p.strip() for p in re.split(r"[，,\n]+", labels.strip()) if p.strip()]

# -------------------------------------------------
def bucket_of(label: str) -> str:
    """
    把任意原始标签/短语转成 severity_order 中能识别的“桶名”
    优先级：维度优质 > 直写弱智/优质 > keyword2bucket > 模糊contains > fallback
    """
    # 维度优质
    if label.startswith(DIM_QUALITY_PREFIX):
        return "14优质"

    # 显式弱智 / 优质
    if label.startswith("12弱智"):
        return "12弱智"
    if label.startswith("14优质"):
        return "14优质"
    if label.startswith("13无问题"):
        return "13无问题"

    # 关键词映射（全局表）
    for kw, bucket in KEYWORD2BUCKET.items():
        if kw in label:
            return bucket

    # 模糊 contains（保留原来的 contains 逻辑）
    if "内容质量差_1.内容错误" in label or "内容错误" in label:
        return "2内容质量差_1.内容错误"
    if "内容质量差" in label:
        return "2内容质量差"
    if "未提供需要信息" in label:
        return "1未提供需要信息"
    if "多轮效果不佳" in label:
        return "3多轮效果不佳"
    if "冗长" in label:
        return "4冗长"
    if "简略" in label:
        return "5简略"
    if "语言表达不佳" in label:
        return "6语言表达不佳"
    if "格式及呈现不佳" in label or "格式" in label:
        return "7格式及呈现不佳"
    if "内容要素不佳" in label or "富媒体" in label:
        return "8内容要素不佳"

    # 兜底：截 '_' 前缀
    return label.split("_")[0]


# -------------------------------------------------
def map_main_issues_to_satisfaction(
        main_issues: str,
        rules: Dict
) -> Tuple[str, str]:
    issues = _split_labels(main_issues)
    if not issues:
        return "未选中", "未标注任何主要问题"

    # 0) 维度优质
    if any(lbl.startswith(DIM_QUALITY_PREFIX) for lbl in issues):
        return "优质", "命中维度优质标签"

    # 1) 弱智 / 14优质直接判
    if any(lbl.startswith("12弱智") or "弱智" in lbl for lbl in issues):
        return "弱智", "命中弱智关键词"
    if any(lbl.startswith("14优质") for lbl in issues):
        return "优质", "命中14优质标签"

    # 2) 按 bucket + satisfaction_map
    #    先把每个 label -> bucket
    buckets = {bucket_of(lbl) for lbl in issues}

    smap = rules.get("satisfaction_map", {})
    for lv in ["弱智", "不合格", "合格", "优质"]:
        for ptn in smap.get(lv, []):
            # ① 原始标签 startswith
            cond1 = any(lbl.startswith(ptn) or ptn in lbl for lbl in issues)
            # ② bucket 等价或前缀
            cond2 = any(bkt == ptn or bkt.startswith(ptn) for bkt in buckets)
            if cond1 or cond2:
                return lv, f"命中【{lv}】档模式: {ptn}"

    # 3) 没命中
    return "未选中", "未在 satisfaction_map 中命中"


# -------------------------------------------------
def _top_severity_bucket(labels: str, rules: Dict):
    issues = _split_labels(labels)
    sev_order = rules.get("severity_order", [])
    bucket_count = {b: 0 for b in sev_order}

    for lbl in issues:
        bkt = bucket_of(lbl)
        if bkt in bucket_count:
            bucket_count[bkt] += 1

    for b in sev_order:
        if bucket_count.get(b, 0):
            return b, bucket_count[b], bucket_count
    return "13无问题", 0, bucket_count


# -------------------------------------------------
def decide_winloss_by_rules(
        a_main_issues: str,
        b_main_issues: str,
        rules: Dict
) -> Tuple[str, bool, str]:
    sev_order = rules.get("severity_order", [])

    a_bkt, a_cnt, a_map = _top_severity_bucket(a_main_issues, rules)
    b_bkt, b_cnt, b_map = _top_severity_bucket(b_main_issues, rules)

    rank = lambda x: sev_order.index(x) if x in sev_order else len(sev_order)
    a_r, b_r = rank(a_bkt), rank(b_bkt)

    if a_r < b_r:
        return "负", False, f"A最严重的主要问题【{a_bkt}】比B【{b_bkt}】更严重"
    if a_r > b_r:
        return "胜", False, f"B最严重的主要问题【{b_bkt}】比A【{a_bkt}】更严重"

    if a_cnt > b_cnt:
        return "负", False, f"同级主要问题【{a_bkt}】，A问题数({a_cnt})>B({b_cnt})"
    if a_cnt < b_cnt:
        return "胜", False, f"同级主要问题【{a_bkt}】，B问题数({b_cnt})>A({a_cnt})"

    a_total, b_total = sum(a_map.values()), sum(b_map.values())
    if a_total > b_total:
        return "负", False, f"问题总数 A({a_total})>B({b_total})"
    if a_total < b_total:
        return "胜", False, f"问题总数 B({b_total})>A({a_total})"

    return "", True, "自动规则无法区分，需要裁判模型"

# ------------------ DEMO -------------------
if __name__ == "__main__":
    rules = {
        "satisfaction_map": {
            "弱智":  ["12弱智"],
            "不合格": ["1未提供需要信息",
                     "2内容质量差_1.内容错误",
                     "2内容质量差_2.内容过时","3多轮效果不佳"],
            "合格":  ["2内容质量差", "4冗长", "5简略", "6语言表达不佳"],
            "优质":  []  # 维度优质或14优质直接触发
        },
        "severity_order": [
            "12弱智",
            "1未提供需要信息",
            "2内容质量差_1.内容错误",
            "2内容质量差",
            "3多轮效果不佳",
            "4冗长",
            "5简略",
            "6语言表达不佳",
            "7格式及呈现不佳",
            "8内容要素不佳",
            "13无问题",
            "14优质"
        ]
    }

    examples = [
        ("内容错误，且冗长", "有趣好聊"),
        ("答非所问", "专业有深度"),
        ("多轮记忆错误", "拓展过少"),
        ("AI感强", "内容过时"),
        ("弱智", "内容重复")
    ]

    for a, b in examples:
        sa, ra = map_main_issues_to_satisfaction(a, rules)
        sb, rb = map_main_issues_to_satisfaction(b, rules)
        res, tie, why = decide_winloss_by_rules(a, b, rules)
        print(f"\nA标签: {a}  |  B标签: {b}")
        print("  A满意度:", sa, ra)
        print("  B满意度:", sb, rb)
        print("  胜负平:", res, "need_tiebreak:", tie, "原因:", why)


import os
import sys
import json
import pandas as pd

from evaluation import (
    load_rules,
    create_single_model_prompt,
    # create_sbs_prompt,
    # create_winloss_tiebreak_prompt,
    create_sbs_analysis_prompt,
    create_final_judgment_prompt,
    test,
)
from output_writer import initialize_output, write_output_row, mark_row_as_dropped
from utils.tee import Tee
from result_parser import parse_result_json

from auto_rules import (
    map_main_issues_to_satisfaction,        # 主要问题 -> 二级满意度
    decide_winloss_by_rules                 # 程序自动：胜平负
)

"""
负责逐行读取 Excel 表格，解析历史内容，调用 prompt 构建与模型评估逻辑，写入结果，保存中间进度。
四步链式流程：
1) A、B单模打标（主要问题、多选）
2) 程序自动映射“二级满意度”；（若12/14则主要问题中必须包含，且优质/弱智具体原因来自 YAML）
3) SBS对比打标（裁判模型）
4) 程序自动胜平负；若无法判定，再调裁判模型做最后判定
"""


def _format_histories(small_v_history, competitor_history):
    """
    将历史对话格式化为 prompt 需要的文本：
    - history（不含最后一轮）
    - resp（最后一轮问答）
    """
    last_small_v = small_v_history[-1]
    last_competitor = competitor_history[-1]

    v_history = "\n".join([
        f"问题：{x['human']}\n大模型A的回答内容：{x['AI']}"
        for x in small_v_history[:-1]
    ])
    c_history = "\n".join([
        f"问题：{x['human']}\n大模型B的回答内容：{x['AI']}"
        for x in competitor_history[:-1]
    ])
    v_resp = f"问题：{last_small_v.get('human', '')}\n大模型A的回答内容：{last_small_v.get('AI', '')}"
    c_resp = f"问题：{last_competitor.get('human', '')}\n大模型B的回答内容：{last_competitor.get('AI', '')}"

    return v_history, c_history, v_resp, c_resp


# 
def _call_and_parse(prompt, model_name, retry=3):
    """
    统一的：模型调用+JSON解析重试
    """
    for attempt in range(retry):
        raw = test(prompt, model=model_name)
        try:
            return parse_result_json(raw)
        except Exception:
            if attempt == retry - 1:
                raise
    # 理论不会到达这里
    return {}

def process_data(file_path, output_dir, model_name, rules):
    """
    【完整版】逐行处理数据的主函数，已集成新的两步式CoT评测流程。
    """
    df = pd.read_excel(file_path)

    # 初始化输出环境
    out_df, output_file_path, log_file_path, terminal_file_path, last_id_path = initialize_output(
        file_path, output_dir, model_name, df
    )

    # 重定向输出
    terminal_fp = open(terminal_file_path, "a", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, terminal_fp)

    # 断点续传
    start_id = 0
    if os.path.exists(last_id_path):
        with open(last_id_path, "r") as f:
            try:
                start_id = int(f.read().strip())
            except:
                start_id = 0

    # 主循环
    for idx, row in df.iterrows():
        id_val = row["id"]
        if id_val < start_id:
            continue

        try:
            # =======================================================
            # 1. 数据解析与预处理
            # =======================================================
            dimension = row.get("度量一级分类", "其他").strip()
            run_time_val = row.get("prompt_time")
            run_time = run_time_val.strip() if run_time_val else ""

            try:
                small_v_history = json.loads(row["小Vcompletions_content"])
                competitor_history = json.loads(row["竞品completions_content"])
            except Exception as e:
                mark_row_as_dropped(out_df, idx, f"JSON解析失败: {e}")
                continue  # 跳到下一行

            if not small_v_history or not competitor_history:
                mark_row_as_dropped(out_df, idx, "对话历史为空")
                continue

            v_history, c_history, v_resp, c_resp = _format_histories(small_v_history, competitor_history)

            # =======================================================
            # 2. 第一阶段：单模型独立打标
            # =======================================================
            prompt_a = create_single_model_prompt(run_time, v_history, v_resp, dimension, rules)
            single_a = _call_and_parse(prompt_a, model_name)

            prompt_b = create_single_model_prompt(run_time, c_history, c_resp, dimension, rules)
            single_b = _call_and_parse(prompt_b, model_name)

            a_single_main_issues = (single_a.get("主要问题") or "").strip()
            b_single_main_issues = (single_b.get("主要问题") or "").strip()
            a_qzrz = (single_a.get("优质弱智主要问题") or "").strip()
            b_qzrz = (single_b.get("优质弱智主要问题") or "").strip()

            # =======================================================
            # 3. 第二阶段：程序化满意度映射
            # =======================================================
            a_satisfaction, _ = map_main_issues_to_satisfaction(a_single_main_issues, rules)
            b_satisfaction, _ = map_main_issues_to_satisfaction(b_single_main_issues, rules)

            # =======================================================
            # 4. 第三阶段：两步式CoT对比与裁决
            # =======================================================

            # --- CoT Step 1: 对比分析 ---
            analysis_prompt = create_sbs_analysis_prompt(dimension, v_history, c_history, v_resp, c_resp, rules)
            try:
                analysis_res = _call_and_parse(analysis_prompt, model_name)
            except Exception as e:
                analysis_res = {}
                with open(log_file_path, "a", encoding="utf-8") as f:
                    f.write(f"Error at row {id_val}: SBS分析步骤(CoT-Step1)失败: {e}\n")

            a_sbs_issues = (analysis_res.get("大模型A_SBS主要问题") or "").strip()
            b_sbs_issues = (analysis_res.get("大模型B_SBS主要问题") or "").strip()

            # --- CoT Step 2: 最终裁决 ---
            analysis_json_str = json.dumps(analysis_res, ensure_ascii=False, indent=2)
            judgment_prompt = create_final_judgment_prompt(analysis_json_str, a_single_main_issues,
                                                           b_single_main_issues, rules)
            try:
                judgment_res = _call_and_parse(judgment_prompt, model_name)
            except Exception as e:
                judgment_res = {}
                with open(log_file_path, "a", encoding="utf-8") as f:
                    f.write(f"Error at row {id_val}: 最终裁决步骤(CoT-Step2)失败: {e}\n")

            sv_compare = (judgment_res.get("大模型A竞品对比") or "").strip()
            tiebreak_reason = (judgment_res.get("裁判说明") or "").strip()

            # =======================================================
            # 5. 第四阶段：结果汇总与写入
            # =======================================================
            def con_issues(single_issues, sbs_issues):
                sbs_issues_set = set(s.strip() for s in (sbs_issues or "").split('，') if s.strip())
                single_issues_set = set(s.strip() for s in (single_issues or "").split('，') if s.strip())
                all_issues = single_issues_set.union(sbs_issues_set)
                if "13无问题" in all_issues and len(all_issues) > 1:
                    all_issues.remove("13无问题")
                if not all_issues:
                    return "13无问题"
                return "，".join(sorted(list(all_issues)))

            a_main_issues = con_issues(a_single_main_issues, a_sbs_issues)
            b_main_issues = con_issues(b_single_main_issues, b_sbs_issues)

            reason_parts = [
                f"大模型A主要问题选择理由：{single_a.get('标注理由', '')}",
                f"大模型B主要问题选择理由：{single_b.get('标注理由', '')}",
                f"裁判说明：{tiebreak_reason}",
            ]
            reason_str = " | ".join([p for p in reason_parts if p and not p.endswith('：')])

            result_json = {
                "大模型A二级满意度": a_satisfaction, "大模型A优质弱智主要问题": a_qzrz,
                "大模型B二级满意度": b_satisfaction, "大模型B优质弱智主要问题": b_qzrz,
                "大模型A竞品对比": sv_compare, "大模型A主要问题": a_main_issues,
                "大模型B主要问题": b_main_issues, "LLMs_标注理由": reason_str,
                "LLMs_自研本身主要问题": a_single_main_issues, "LLMs_竞品本身主要问题": b_single_main_issues,
                "LLMs_自研SBS主要问题": a_sbs_issues, "LLMs_竞品SBS主要问题": b_sbs_issues,
                "LLMs_A_失败触发器": str(analysis_res.get("大模型A_命中的失败触发器", [])),
                "LLMs_B_失败触发器": str(analysis_res.get("大模型B_命中的失败触发器", [])),
                "LLMs_A_胜利模式": str(analysis_res.get("大模型A_符合的胜利模式", [])),
                "LLMs_B_胜利模式": str(analysis_res.get("大模型B_符合的胜利模式", [])),
                "LLMs_裁判分析报告": tiebreak_reason
            }

            write_output_row(out_df, idx, result_json)

        except Exception as e:
            # 主循环的兜底异常处理
            mark_row_as_dropped(out_df, idx, f"未知严重错误: {e}")
            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write(f"CRITICAL Error at row {id_val}: {e}\n")
        finally:
            # 无论成功或失败，都保存当前进度
            out_df.to_excel(output_file_path, index=False)
            with open(last_id_path, "w") as f:
                f.write(str(id_val))
            print("*" * 30, f"Row {id_val} 执行完成", "*" * 30, "\n")

    print(f"所有行处理完毕！已保存至：{output_file_path}")
    sys.stdout = sys.__stdout__
    terminal_fp.close()
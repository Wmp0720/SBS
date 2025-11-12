import os
import sys
import json
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import threading
from tqdm import tqdm

from evaluation import (
    load_rules,
    create_single_model_prompt,
    # create_winloss_tiebreak_prompt,
    create_sbs_analysis_prompt,
    create_final_judgment_prompt,
    test,
)
from output_writer import initialize_output, write_output_row, mark_row_as_dropped
from utils.tee import Tee
from result_parser import parse_result_json
from auto_rules import map_main_issues_to_satisfaction

lock = threading.Lock()

def _format_histories(small_v_history, competitor_history):
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

def _call_and_parse(prompt, model_name, retry=3, verbose=False, show_prompts=False):
    for attempt in range(retry):
        # [修改] 将 verbose 和 show_prompts 参数传递给 test 函数
        raw = test(prompt, model=model_name, verbose=verbose, show_prompts=show_prompts)
        try:
            return parse_result_json(raw)
        except Exception:
            if attempt == retry - 1:
                raise
    return {}

def process_single_row(row, idx, out_df, output_file_path, last_id_path, log_file_path, model_name, rules, pbar,
                       verbose=False, show_prompts=False):
    """
    【完整版】处理单行数据的核心函数，已集成新的两步式CoT评测流程。
    """
    id_val = row.get("id", idx)
    try:
        # =======================================================
        # 1. 数据解析与预处理 (保持不变)
        # =======================================================
        dimension = row.get("度量一级分类", "其他").strip()
        run_time_val = row.get("prompt_time")
        run_time = run_time_val.strip() if run_time_val else ""

        # 解析历史记录，并处理各种异常情况
        try:
            small_v_history = json.loads(row["小Vcompletions_content"])
        except Exception as e:
            with lock:
                mark_row_as_dropped(out_df, idx, "自研内容解析失败")
            return
        try:
            competitor_history = json.loads(row["竞品completions_content"])
        except Exception as e:
            with lock:
                mark_row_as_dropped(out_df, idx, "竞品内容解析失败")
            return

        # 空内容检查
        if not small_v_history or row['小Vcompletions_content'] == "[]":
            with lock:
                mark_row_as_dropped(out_df, idx, "自研内容为空")
            return
        if not competitor_history or row['竞品completions_content'] == "[]":
            with lock:
                mark_row_as_dropped(out_df, idx, "竞品内容为空")
            return

        # 格式化历史
        v_history, c_history, v_resp, c_resp = _format_histories(small_v_history, competitor_history)

        # =======================================================
        # 2. 第一阶段：单模型独立打标 (保持不变)
        # =======================================================
        prompt_a = create_single_model_prompt(run_time, v_history, v_resp, dimension, rules)
        single_a = _call_and_parse(prompt_a, model_name, verbose=verbose, show_prompts=show_prompts)

        prompt_b = create_single_model_prompt(run_time, c_history, c_resp, dimension, rules)
        single_b = _call_and_parse(prompt_b, model_name, verbose=verbose, show_prompts=show_prompts)

        a_single_main_issues = (single_a.get("主要问题") or "").strip()
        b_single_main_issues = (single_b.get("主要问题") or "").strip()
        a_qzrz = (single_a.get("优质弱智主要问题") or "").strip()
        b_qzrz = (single_b.get("优质弱智主要问题") or "").strip()

        # =======================================================
        # 3. 第二阶段：程序化满意度映射 (保持不变)
        # =======================================================
        a_satisfaction, reason_a = map_main_issues_to_satisfaction(a_single_main_issues, rules)
        b_satisfaction, reason_b = map_main_issues_to_satisfaction(b_single_main_issues, rules)

        # =======================================================
        # 4. 第三阶段：【核心改造】两步式CoT对比与裁决
        # =======================================================

        # --- CoT Step 1: 对比分析 (事实收集) ---
        analysis_prompt = create_sbs_analysis_prompt(dimension, v_history, c_history, v_resp, c_resp, rules)
        try:
            analysis_res = _call_and_parse(analysis_prompt, model_name, verbose=verbose, show_prompts=show_prompts)
        except Exception as e:
            analysis_res = {}  # 即使此步失败，也用空字典继续，保证流程不中断
            with lock:
                with open(log_file_path, "a", encoding="utf-8") as f:
                    f.write(f"Error at row {id_val}: SBS分析步骤(CoT-Step1)失败: {e}\n")

        # 从分析结果中提取信息
        a_sbs_issues = (analysis_res.get("大模型A_SBS主要问题") or "").strip()
        b_sbs_issues = (analysis_res.get("大模型B_SBS主要问题") or "").strip()

        # --- CoT Step 2: 最终裁决 (基于事实判断) ---
        analysis_json_str = json.dumps(analysis_res, ensure_ascii=False, indent=2)
        judgment_prompt = create_final_judgment_prompt(analysis_json_str, a_single_main_issues, b_single_main_issues,
                                                       rules)
        try:
            judgment_res = _call_and_parse(judgment_prompt, model_name, verbose=verbose, show_prompts=show_prompts)
        except Exception as e:
            judgment_res = {}  # 裁决失败也用空字典继续
            with lock:
                with open(log_file_path, "a", encoding="utf-8") as f:
                    f.write(f"Error at row {id_val}: 最终裁决步骤(CoT-Step2)失败: {e}\n")

        # 从裁决结果中提取最终判断
        sv_compare = (judgment_res.get("大模型A竞品对比") or "").strip()
        tiebreak_reason = (judgment_res.get("裁判说明") or "").strip()

        # =======================================================
        # 5. 第四阶段：结果汇总与写入 (保持不变)
        # =======================================================

        # 合并所有问题标签
        def con_issues(single_issues, sbs_issues):
            sbs_issues_set = set(s.strip() for s in (sbs_issues or "").split('，') if s.strip())
            single_issues_set = set(s.strip() for s in (single_issues or "").split('，') if s.strip())
            all_issues = single_issues_set.union(sbs_issues_set)
            if "13无问题" in all_issues and len(all_issues) > 1:
                all_issues.remove("13无问题")  # 如果有其他问题，就移除“无问题”标签
            if not all_issues:
                return "13无问题"
            return "，".join(sorted(list(all_issues)))

        a_main_issues = con_issues(a_single_main_issues, a_sbs_issues)
        b_main_issues = con_issues(b_single_main_issues, b_sbs_issues)

        # 汇总所有标注理由
        reason_parts = [
            f"大模型A主要问题选择理由：{single_a.get('标注理由', '')}",
            f"大模型B主要问题选择理由：{single_b.get('标注理由', '')}",
            f"裁判说明：{tiebreak_reason}",
        ]
        reason_str = " | ".join([p for p in reason_parts if p and not p.endswith('：')])

        # 构建最终要写入的JSON对象
        result_json = {
            "大模型A二级满意度": a_satisfaction,
            "大模型A优质弱智主要问题": a_qzrz,
            "大模型B二级满意度": b_satisfaction,
            "大模型B优质弱智主要问题": b_qzrz,
            "大模型A竞品对比": sv_compare,
            "大模型A主要问题": a_main_issues,
            "大模型B主要问题": b_main_issues,
            "LLMs_标注理由": reason_str,
            # --- 新增的详细分析字段 ---
            "LLMs_自研本身主要问题": a_single_main_issues,
            "LLMs_竞品本身主要问题": b_single_main_issues,
            "LLMs_自研SBS主要问题": a_sbs_issues,
            "LLMs_竞品SBS主要问题": b_sbs_issues,
            "LLMs_A_失败触发器": str(analysis_res.get("大模型A_命中的失败触发器", [])),
            "LLMs_B_失败触发器": str(analysis_res.get("大模型B_命中的失败触发器", [])),
            "LLMs_A_胜利模式": str(analysis_res.get("大模型A_符合的胜利模式", [])),
            "LLMs_B_胜利模式": str(analysis_res.get("大模型B_符合的胜利模式", [])),
            "LLMs_裁判分析报告": tiebreak_reason  # 复用裁判说明
        }
    # 线程安全地写入结果
        with lock:
            write_output_row(out_df, idx, result_json)
            out_df.to_excel(output_file_path, index=False)
            with open(last_id_path, "w", encoding="utf-8") as f:
                f.write(str(id_val))

    except Exception as e:
        # 主循环的兜底异常处理
        with lock:
            # 标记为剔除，以防万一
            mark_row_as_dropped(out_df, idx, f"未知严重错误: {e}")
            out_df.to_excel(output_file_path, index=False)
            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write(f"CRITICAL Error at row {id_val}: {e}\n")
    finally:
        # 确保进度条总是更新
        pbar.update(1)

def process_data_multithread(file_path, output_dir, model_name, rules, thread_num=2, verbose=False, show_prompts=False):
    df = pd.read_excel(file_path)
    df_split = [df_part for df_part in np.array_split(df, thread_num)]
    os.makedirs(output_dir, exist_ok=True)

    # 在启动线程池前初始化tqdm进度条
    total_rows = len(df)
    pbar = tqdm(total=total_rows, desc="评测进度", unit="条")

    # run_thread 函数签名增加 pbar 参数
    def run_thread(thread_id, sub_df, pbar, verbose, show_prompts):
        thread_model_name = f"{model_name}_part_{thread_id}"
        out_df, output_file_path, log_file_path, terminal_file_path, last_id_path = initialize_output(
            file_path, output_dir, thread_model_name, sub_df
        )
        # 注意：此处为简化，不再为每个线程重定向stdout，进度条将统一在主控制台显示
        # terminal_fp = open(terminal_file_path, "a", encoding="utf-8")
        # sys.stdout = Tee(sys.__stdout__, terminal_fp)

        # [修改] 在循环中传递pbar
        for idx, row in sub_df.iterrows():
            process_single_row(row, idx, out_df, output_file_path, last_id_path, log_file_path, model_name, rules, pbar, verbose=verbose, show_prompts=show_prompts)

        # sys.stdout = sys.__stdout__
        # terminal_fp.close()

    with ThreadPoolExecutor(max_workers=thread_num) as executor:
        # [修改] 提交任务时传递pbar
        for i, sub_df in enumerate(df_split):
            executor.submit(run_thread, i, sub_df, pbar, verbose, show_prompts)

    # 任务完成后关闭进度条
    pbar.close()
    print("所有线程任务已完成！")
import os
import pandas as pd
import json
import yaml

from evaluation import create_loss_analysis_prompt, create_win_factor_prompt, test


def format_df_to_markdown(df: pd.DataFrame) -> str:
    """辅助函数：将DataFrame格式化为Markdown表格字符串"""
    # 选择性地只展示核心列，防止prompt过长
    key_columns = [
        "prompt_content", "小Vcompletions_content", "竞品completions_content",
        "小v主要问题", "竞品主要问题", "小v竞品对比",
        "标注备注","小v优质弱智","竞品优质弱智"
    ]
    # 过滤掉数据集中不存在的列
    existing_cols = [col for col in key_columns if col in df.columns]
    return df[existing_cols].to_markdown(index=False)


def clean_and_parse_json_list(raw_str: str) -> list:
    """清理并解析LLM返回的可能是JSON列表的字符串"""
    # 移除Markdown包裹
    cleaned_str = raw_str.strip().strip('`').strip('json').strip()
    try:
        # 解析为Python列表
        parsed_list = json.loads(cleaned_str)
        if isinstance(parsed_list, list):
            return parsed_list
        else:
            print(f"[警告] 解析结果不是一个列表，而是 {type(parsed_list)} 类型。")
            return []
    except json.JSONDecodeError as e:
        print(f"[错误] JSON解析失败: {e}")
        print(f"原始字符串: {raw_str}")
        return []


if __name__ == "__main__":
    # --- 配置区 ---
    MODEL_NAME = "o3"  # 使用你最强大的模型来执行学习任务
    WIN_SET_PATH = "config/Win-Set.xlsx"
    LOSS_SET_PATH = "config/Loss-Set.xlsx"
    OUTPUT_DIR = "config/learned_rules"
    # ---

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # === 1. 学习败因分析 (Loss Analysis) ===
    print("--- 阶段A：正在从失败案例中学习“失败触发器”... ---")
    try:
        loss_df = pd.read_excel(LOSS_SET_PATH)
        loss_samples_str = format_df_to_markdown(loss_df)
        loss_prompt = create_loss_analysis_prompt(loss_samples_str)

        print("正在请求LLM进行败因分析...")
        raw_loss_triggers = test(loss_prompt, model=MODEL_NAME, verbose=True)

        learned_loss_triggers = clean_and_parse_json_list(raw_loss_triggers)

        if learned_loss_triggers:
            output_path = os.path.join(OUTPUT_DIR, "learned_loss_triggers.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(learned_loss_triggers, f, ensure_ascii=False, indent=2)
            print(f"✅ 失败触发器学习成功！结果已保存至: {output_path}")
            print("学到的规则内容：")
            print(json.dumps(learned_loss_triggers, ensure_ascii=False, indent=2))
        else:
            print("❌ 败因分析未能生成有效的规则列表。")

    except FileNotFoundError:
        print(f"[错误] 未找到失败案例集: {LOSS_SET_PATH}")
    except Exception as e:
        print(f"[严重错误] 败因分析阶段失败: {e}")

    print("\n" + "=" * 50 + "\n")

    # === 2. 学习胜决因素分析 (Win-Factor Analysis) ===
    print("--- 阶段B：正在从成功案例中学习“胜利模式”... ---")
    try:
        win_df = pd.read_excel(WIN_SET_PATH)
        win_samples_str = format_df_to_markdown(win_df)
        win_prompt = create_win_factor_prompt(win_samples_str)

        print("正在请求LLM进行胜决因素分析...")
        raw_win_patterns = test(win_prompt, model=MODEL_NAME, verbose=True)

        learned_win_patterns = clean_and_parse_json_list(raw_win_patterns)

        if learned_win_patterns:
            output_path = os.path.join(OUTPUT_DIR, "learned_win_patterns.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(learned_win_patterns, f, ensure_ascii=False, indent=2)
            print(f"✅ 胜利模式学习成功！结果已保存至: {output_path}")
            print("学到的规则内容：")
            print(json.dumps(learned_win_patterns, ensure_ascii=False, indent=2))
        else:
            print("❌ 胜决因素分析未能生成有效的规则列表。")

    except FileNotFoundError:
        print(f"[错误] 未找到成功案例集: {WIN_SET_PATH}")
    except Exception as e:
        print(f"[严重错误] 胜决因素分析阶段失败: {e}")
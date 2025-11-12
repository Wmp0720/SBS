
import os
import sys
import argparse
from evaluation import load_rules, create_reflection_prompt, test
from processor_threaded import process_data_multithread
# from processor import process_data
from check_consistency import compute_consistency, add_consistency_flag_columns
from utils.tee import Tee
from merge_outputs import merge_thread_outputs
import pandas as pd
from check_consistency import compute_consistency, add_consistency_flag_columns, _normalize_columns


def format_df_to_markdown(df: pd.DataFrame) -> str:
    """辅助函数：将DataFrame格式化为Markdown表格字符串"""
    return df.to_markdown(index=False)


if __name__ == "__main__":
    # ===============================
    # 命令行参数解析
    parser = argparse.ArgumentParser(description="自动化评测系统")
    parser.add_argument("--model", default="o3",
                       help="使用的模型名称")
    parser.add_argument("--dataset", default="test4.xlsx",
                       help="数据集文件名")
    parser.add_argument("--golden", default="config/golden_dataset.xlsx",
                       help="精标数据集路径")
    parser.add_argument("--threads", type=int, default=5,
                       help="并发线程数")
    parser.add_argument("--version", default="test4",
                       help="结果目录版本标记")
    parser.add_argument("--verbose", action="store_true",
                       help="启用详细日志输出")
    parser.add_argument("--show-prompts", action="store_true",
                       help="显示完整的prompt内容")
    args = parser.parse_args()

    # ===============================
    # 总开关，控制是否打印详细日志
    VERBOSE_MODE = args.verbose  # 设置为 False 来关闭详细Prompt打印，需要调试时改为 True
    SHOW_PROMPTS = args.show_prompts  # 控制是否显示完整的prompt内容
    # ===============================
    model_name = args.model  # 可选：gpt_4o/deepseek-r1/豆包1.5_pro/o3/gemini-2.5-pro/Doubao-1.6-agent-pro等
    dataset = args.dataset  # 数据集文件名
    golden_dataset_path = args.golden
    thread_num = args.threads  # 并发线程数
    version = args.version  # 结果目录版本标记
    # ==============================

    # 输出文件的路径规划
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "Datesets", dataset)
    output_dir = os.path.join(current_dir, "Results", version,
                              os.path.basename(file_path).replace(".xlsx", f"_{model_name}"))
    output_dir_mutithread = os.path.join(output_dir, "multithread")
    final_output_file = os.path.join(output_dir,
                                     f"{os.path.basename(file_path).replace('.xlsx', '')}_{model_name}Eval.xlsx")

    # 【说明】确保我们导入了正确的函数
    # from check_consistency import compute_consistency, add_consistency_flag_columns

    rules = load_rules()

    # =================== 反思学习阶段 ===================
    print("--- 阶段零：LLM反思学习阶段 ---")
    try:
        golden_df = pd.read_excel(os.path.join(current_dir, golden_dataset_path))
        key_columns = [
            "prompt_content", "小Vcompletions_content", "竞品completions_content",
            "标注员_小v主要问题", "标注员_竞品主要问题", "标注员_小v竞品对比",
            "LLMs_自研主要问题", "LLMs_竞品主要问题", "LLMs_自研竞品对比"
        ]
        key_columns_exist = [col for col in key_columns if col in golden_df.columns]
        golden_samples_df = golden_df[key_columns_exist].head(9)
        golden_samples_str = format_df_to_markdown(golden_samples_df)
        reflection_prompt = create_reflection_prompt(golden_samples_str, rules)

        print("正在请求LLM学习精标数据并生成评测指南...")
        learned_guidelines = test(reflection_prompt, model=model_name, verbose=VERBOSE_MODE, show_prompts=SHOW_PROMPTS)
        print("LLM学习完成，生成的评测指南如下：\n", learned_guidelines)

        rules['learned_guidelines'] = learned_guidelines
    except FileNotFoundError:
        print(f"[警告] 未找到精标数据集: {golden_dataset_path}。将跳过学习阶段。")
        rules['learned_guidelines'] = "无"
    except Exception as e:
        print(f"[错误] LLM学习阶段失败: {e}。将跳过学习阶段。")
        rules['learned_guidelines'] = "无"
    print("------------------------------------\n")

    # =================== 评测执行与合并 ===================
    print(f"--- 阶段一：开始对 {dataset} 进行多线程评测 ---")
    process_data_multithread(
        file_path,
        output_dir_mutithread,
        model_name=model_name,
        rules=rules,
        thread_num=thread_num,
        verbose=VERBOSE_MODE,
        show_prompts=SHOW_PROMPTS
    )
    print("\n--- 阶段二：合并多线程结果文件 ---")
    merge_thread_outputs(output_dir_mutithread, model_name, final_output_file)
    print(f"✅ 多线程结果已合并至: {final_output_file}")

    # =================== 后处理：添加标记列 ===================
    print("\n--- 阶段三：为最终结果文件添加'人机一致'标记列 ---")
    try:
        print(f"正在读取合并后的文件: {final_output_file}")
        final_df = pd.read_excel(final_output_file)
        print(f"读取成功，原始列数: {len(final_df.columns)}")

        final_df = _normalize_columns(final_df)
        print(f"归一化后列: {final_df.columns.to_list()}")

        # 调用函数添加标记列
        final_df_with_flags = add_consistency_flag_columns(final_df)
        print(f"标记列添加完成，当前列数: {len(final_df_with_flags.columns)}")

        # 将带有新列的DataFrame写回，覆盖原文件
        print(f"正在将更新后的数据写回文件，这会覆盖原有内容...")
        final_df_with_flags.to_excel(final_output_file, index=False)
        print(f"✅ 三列标记列已成功添加并保存回: {final_output_file}")
    except FileNotFoundError:
        print(f"[错误] 未找到最终结果文件: {final_output_file}，跳过添加标记列。")
    except Exception as e:
        print(f"[严重错误] 添加标记列时发生失败: {e}")
        # 在这里可以加入更详细的错误追溯
        import traceback

        traceback.print_exc()

    # =================== 最终分析 ===================
    print("\n--- 阶段四：在已包含标记列的文件上执行一致性统计 ---")
    # 【说明】compute_consistency 函数设计为在现有文件上追加或替换sheet，
    # 它不会修改文件中的第一个sheet（即我们刚刚写入的主数据）。
    try:
        compute_consistency(file_path=final_output_file, model_name=model_name)
        print(f"\n🎉🎉🎉 所有流程执行完毕！最终的完整报告已生成在: {final_output_file}")
    except Exception as e:
        print(f"[严重错误] 执行最终一致性分析时失败: {e}")
        import traceback

        traceback.print_exc()
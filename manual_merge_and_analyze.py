
# manual_merge_and_analyze.py
# -----------------------------------------------------------------------------
# 功能：一个独立的手动合并与分析脚本。
#       第1步: 将多线程产生的部分结果文件（_part_N.xlsx）合并成一个完整的Excel文件。
#       第2步: 在合并好的文件上，运行人机一致性检查，并追加统计报告Sheet。
#
# 使用方法：
#   1. 将此文件放置在项目根目录下。
#   2. 修改下面的【配置区】变量。
#   3. 在终端运行 `python manual_merge_and_analyze.py`。
# -----------------------------------------------------------------------------

import os
import sys

# --- 导入项目中的核心逻辑 ---
try:
    # 导入合并函数
    from merge_outputs import merge_thread_outputs
    # 导入一致性分析函数
    from check_consistency import compute_consistency
except ImportError as e:
    print(f"[错误] 无法导入项目模块: {e}")
    print("请确保此脚本与 merge_outputs.py, check_consistency.py 等文件在同一个项目的根目录下。")
    sys.exit(1)

if __name__ == "__main__":

    # ============================ 【配置区】 ============================
    # 请根据你想要合并与分析的评测任务，修改以下三个变量

    # 结果目录的版本标记，对应于 Results/ 目录下的子文件夹名
    VERSION = "test2-1-拓展"
    # test2-1-拓展

    # 评测时使用的模型名称，这会影响查找哪些部分文件
    MODEL_NAME = "o3"

    # 原始数据集的文件名（包含扩展名 .xlsx）
    DATASET_BASENAME = "test2.xlsx"

    # =================================================================

    print("--- 启动手动合并与分析脚本 ---")

    # --- 1. 根据配置构建路径 ---
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # 构建存储部分结果的目录路径
        base_output_dir = os.path.join(current_dir, "Results", VERSION,
                                       os.path.splitext(DATASET_BASENAME)[0] + f"_{MODEL_NAME}")
        parts_input_dir = os.path.join(base_output_dir, "multithread")

        # 构建最终合并后文件的完整路径
        final_output_file = os.path.join(base_output_dir,
                                         os.path.splitext(DATASET_BASENAME)[0] + f"_{MODEL_NAME}Eval.xlsx")

        print(f"[*] 待合并文件目录: {parts_input_dir}")
        print(f"[*] 最终输出文件路径: {final_output_file}")

        if not os.path.isdir(parts_input_dir):
            print(f"\n[错误] 找不到待合并文件的目录！请检查配置和路径是否正确。")
            print(f"预期路径: {parts_input_dir}")
            sys.exit(1)

    except Exception as e:
        print(f"\n[严重错误] 构建路径时失败: {e}")
        sys.exit(1)

    # --- 2. 调用核心合并逻辑 ---
    print("\n--- 阶段1：开始执行合并操作 ---")
    try:
        merge_thread_outputs(
            output_dir=parts_input_dir,
            model_name=MODEL_NAME,
            final_output_file=final_output_file
        )
        print("--- ✅ 合并完成！---")

    except Exception as e:
        print(f"\n[严重错误] 合并过程中发生意外: {e}")
        print("请检查配置是否正确，以及部分结果文件是否存在且格式无误。")
        sys.exit(1)

    # --- 3. 调用人机一致性分析逻辑 ---
    print("\n--- 阶段2：开始执行人机一致性分析 ---")
    try:
        if not os.path.exists(final_output_file):
            print(f"\n[错误] 合并后的文件未找到，无法进行一致性分析。")
            print(f"预期文件路径: {final_output_file}")
            sys.exit(1)

        # 在合并好的文件上直接运行一致性计算
        compute_consistency(file_path=final_output_file, model_name=MODEL_NAME)

        print(f"\n--- ✅ 统计报告已生成并追加到结果文件中！ ---")
        print(f"\n🎉🎉🎉 合并与分析全部完成！最终报告已生成在: {final_output_file}")

    except Exception as e:
        print(f"\n[严重错误] 人机一致性分析过程中发生意外: {e}")
        print("请检查合并后的Excel文件内容是否完整，以及 'check_consistency.py' 脚本是否能正常处理该文件。")

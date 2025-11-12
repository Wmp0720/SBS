
import os
import pandas as pd

def merge_thread_outputs(output_dir, model_name, final_output_file):
    part_files = [
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.endswith(".xlsx") and f"{model_name}_part" in f
    ]
    part_files.sort()  # 确保顺序一致

    dfs = []
    for file in part_files:
        try:
            df = pd.read_excel(file)
            dfs.append(df)
        except Exception as e:
            print(f"读取文件出错：{file}，错误：{e}")

    if dfs:
        final_df = pd.concat(dfs, ignore_index=True)
        final_df.to_excel(final_output_file, index=False)
        print(f"已合并 {len(part_files)} 个子结果文件，输出至：{final_output_file}")
    else:
        print("未找到可合并的线程结果文件。")
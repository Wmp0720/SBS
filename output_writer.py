import os
import pandas as pd
"""
    输出写入逻辑（Excel / 中间文件）
"""

def initialize_output(file_path, output_dir, model_name, df):
    """
    初始化输出 DataFrame 和相关路径

    Args:
     file_path (str): 输入文件的路径
     output_dir (str): 输出目录的路径
     model_name (str): 模型的名称
     df (pandas.DataFrame): 输入的 DataFrame

    Returns:
     tuple: 包含初始化后的 DataFrame, 输出文件路径, 日志文件路径, 终端打印文件路径, 最后成功 ID 文件路径
    """
    """
    初始化输出 DataFrame 和 路径
    """
    if "id" not in df.columns:
        df.insert(0, "id", range(len(df)))

    output_file_path = os.path.join(output_dir, os.path.basename(file_path).replace(".xlsx", f"_{model_name}Eval.xlsx"))
    log_file_path = os.path.join(output_dir, os.path.basename(file_path).replace(".xlsx", "_Errorlog.txt"))
    terminal_file_path = os.path.join(output_dir, os.path.basename(file_path).replace(".xlsx", "_Terminal_Print.txt"))
    last_id_path = os.path.join(output_dir, "last_success_id.txt")

    os.makedirs(output_dir, exist_ok=True)

    if os.path.exists(output_file_path):
        out_df = pd.read_excel(output_file_path)
    else:
        out_df = df.copy()
        for col in [
            "LLMs_自研满意度",
            "LLMs_自研优质弱智",
            "LLMs_自研优质弱智主要问题",
            "LLMs_竞品满意度",
            "LLMs_竞品优质弱智",
            "LLMs_竞品优质弱智主要问题",
            "LLMs_自研竞品对比",
            "LLMs_自研主要问题",
            "LLMs_竞品竞品对比",
            "LLMs_竞品主要问题",
            "LLMs_标注理由",
            # ====== 新增四列（便于单步质检）======
            "LLMs_自研本身主要问题",
            "LLMs_竞品本身主要问题",
            "LLMs_自研SBS主要问题",
            "LLMs_竞品SBS主要问题",
            "LLMs_A_失败触发器",
            "LLMs_B_失败触发器",
            "LLMs_A_胜利模式",
            "LLMs_B_胜利模式",
            "LLMs_裁判分析报告"
        ]:
            if col not in out_df.columns:
                out_df[col] = ""

    return out_df, output_file_path, log_file_path, terminal_file_path, last_id_path


def write_output_row(out_df, idx, result_json):
    """
    将模型输出写入指定行
    """
    sv_score = result_json.get("大模型A二级满意度", "").strip()
    cp_score = result_json.get("大模型B二级满意度", "").strip()
    sv_compare = result_json.get("大模型A竞品对比", "").strip()

    # 满意度
    out_df.at[idx, "LLMs_自研优质弱智"] = sv_score
    out_df.at[idx, "LLMs_竞品优质弱智"] = cp_score
    out_df.at[idx, "LLMs_自研满意度"] = "剔除" if sv_score == "剔除" else "1" if sv_score in ["合格", "优质"] else "0"
    out_df.at[idx, "LLMs_竞品满意度"] = "剔除" if cp_score == "剔除" else "1" if cp_score in ["合格", "优质"] else "0"

    # 优质/弱智主要问题
    if sv_score in ["弱智", "优质"]:
        out_df.at[idx, "LLMs_自研优质弱智主要问题"] = result_json.get("大模型A优质弱智主要问题", "").strip()
    if cp_score in ["弱智", "优质"]:
        out_df.at[idx, "LLMs_竞品优质弱智主要问题"] = result_json.get("大模型B优质弱智主要问题", "").strip()

    # 对比胜负
    out_df.at[idx, "LLMs_自研竞品对比"] = sv_compare
    out_df.at[idx, "LLMs_竞品竞品对比"] = {"胜": "负", "平": "平", "负": "胜"}.get(sv_compare, "")

    # 对比失败方主要问题
    # if sv_compare == "负":
    #     out_df.at[idx, "LLMs_自研主要问题"] = result_json.get("大模型A主要问题", "").strip()
    # if sv_compare == "胜":
    #     out_df.at[idx, "LLMs_竞品主要问题"] = result_json.get("大模型B主要问题", "").strip()
    
    # 修改逻辑为全部输出主要问题
    out_df.at[idx, "LLMs_自研主要问题"] = result_json.get("大模型A主要问题", "").strip()
    out_df.at[idx, "LLMs_竞品主要问题"] = result_json.get("大模型B主要问题", "").strip()


    # ====== 新增四列写出（来自链式四步）======
    out_df.at[idx, "LLMs_自研本身主要问题"] = result_json.get("大模型A本身主要问题", "").strip()
    out_df.at[idx, "LLMs_竞品本身主要问题"] = result_json.get("大模型B本身主要问题", "").strip()
    out_df.at[idx, "LLMs_自研SBS主要问题"] = result_json.get("大模型A_SBS主要问题", "").strip()
    out_df.at[idx, "LLMs_竞品SBS主要问题"] = result_json.get("大模型B_SBS主要问题", "").strip()

    # result_json现在应该包含来自新版tiebreak_prompt的丰富输出
    out_df.at[idx, "LLMs_A_失败触发器"] = str(result_json.get("大模型A_命中的失败触发器", ""))
    out_df.at[idx, "LLMs_B_失败触发器"] = str(result_json.get("大模型B_命中的失败触发器", ""))
    out_df.at[idx, "LLMs_A_胜利模式"] = str(result_json.get("大模型A_符合的胜利模式", ""))
    out_df.at[idx, "LLMs_B_胜利模式"] = str(result_json.get("大模型B_符合的胜利模式", ""))
    out_df.at[idx, "LLMs_裁判分析报告"] = result_json.get("裁判分析报告", "").strip()

    # 理由补充
    out_df.at[idx, "LLMs_标注理由"] = result_json.get("LLMs_标注理由", "").strip()


def mark_row_as_dropped(out_df, idx, reason):
    """
    标记一行数据为“剔除”，并说明理由
    """
    for col in out_df.columns:
        if col.startswith("LLMs_"):
            out_df.at[idx, col] = "剔除"
    out_df.at[idx, "LLMs_标注理由"] = reason
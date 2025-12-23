
**## 项目简介**

**SBS（Side-by-Side Evaluation **System）是一个面向大语言模型（LLM）的自动化对比评测系统，用于在真实用户对话数据上，对**自研模型**与**竞品模型**进行多维度、可解释的 **Side-by-Side 评估。**

**系统的核心特点：**

**- **四步链路评测流程**：单模标注 → 满意度映射 → CoT 对比分析 → 最终裁决**

**- **模糊标签 + 规则推理引擎**：支持噪声标签与自然语言描述，自动推理满意度与胜负**

**- **SBS 对比裁判**：通过 CoT 两步式（事实归档 + 法官裁决）提升评测稳定性与可解释性**

**- **知识问答专用事实性检测**：融合信息源检索与事实核查**

**- **多线程流水线 + 断点续跑**：支持大规模数据高效评测**

**- **人机一致性分析**：自动生成多维度一致率报表**

**---**

**## 功能概览**

**- **数据驱动评测****

**  - 从 Excel 数据集（含用户问题、自研/竞品对话历史）读取样本**

**  - 支持按维度（技能、文本生成、知识问答、聊天等）打标**

**- **四步链路 SBS 评测流程****

**  1. 单模型主要问题标注（自研/竞品各一次）**

**  2. 主要问题标签 → 二级满意度（弱智/不合格/合格/优质）**

**  3. SBS 对比分析（CoT Step1：只收集问题标签、失败触发器、胜利模式）**

**  4. 最终裁决（CoT Step2：基于“案件档案”输出胜/平/负 + 裁判说明）**

**- **规则引擎与标签系统****

**  - 基于 `config/scoring_rules4.yaml` 定义维度、标签、规则**

**  - `auto_rules.py` 提供标签桶映射、满意度推理、胜负规则判定**

**- **知识问答增强评测****

**  - `utils/source_checker.py`：信息源检索 + 事实性验证 + 综合评分**

**  - `utils/knowledge_qa_judge.py`：线性打分 + 满意度 + SBS **裁判一体化

**- **工程化支撑****

**  - `processor_threaded.py`：多线程评测 + 进度条**

**  - `output_writer.py`：结果写回、日志、中间文件、断点续跑**

**  - `merge_outputs.py` / **`manual_merge_and_analyze.py`：结果合并与分析

**  - `check_consistency.py`：人机一致率报表（总览 + 分维度 + 分竞品）**

**---**

**## 目录结构说明**

**见项目根目录大致结构：**

**- `main.py`：推荐入口脚本，串起**反思学习 → 多线程评测 → 合并 → **一致性分析**全流程。

**- `processor_threaded.py`：多线程评测核心逻辑（建议主流程使用）。**

**- `processor.py`：单线程/调试版本，便于阅读与验证。**

**- `evaluation.py`：所有 Prompt 构造与统一的模型调用封装（包括 **CoT、SBS、反思学习等）。

**- `auto_rules.py`：模糊标签桶、满意度映射与胜负规则推理逻辑。**

**- `check_consistency.py`：对最终结果进行人机一致性分析，输出统计 **Sheet。

**- `learn_from_golden.py`：从 Win/Loss **精标集学习“失败触发器”和“胜利模式”。

**- `utils/`：模型调用、日志、知识问答裁判、信息源检测等基础组件。**

**- `config/`：评分规则与模型配置。**

**---**

**## 环境依赖**

**### 基础环境**

**- Python 3.8+**

**- 推荐使用虚拟环境（`venv` / `conda`）**

**### 主要第三方库（示例）**

**pip install pandas numpy openpyxl pyyaml tqdm **requests如果项目中已有 `requirements.txt`，建议直接：

**pip install -r requirements.txt---**

**## 快速开始**

**### 1. 准备数据与配置**

**1. 将评测数据集（Excel）放入项目指定目录（例如 `Datasets/`），格式需包含：**

**   - 用户问题列（如 `prompt_content`）**

**   - 自研模型对话内容列（如 `小Vcompletions_content`，JSON 字符串）**

**   - 竞品模型对话内容列（如 `竞品completions_content`，JSON 字符串）**

**   - 评测维度列（如 `度量一级分类`）**

**2. 配置评分规则：**

**   - 编辑 **`config/scoring_rules4.yaml`，按需要调整维度、标签与规则。

**3. 配置模型调用：**

**   - 在 `config/config.py` 指向的 `model.yaml` **中，填好各模型的 `appid`、`appkey`、`uri`、`domain` 等信息。

**---**

**### 2. 运行主流程（推荐）**

**python main.py \**

**  --model o3 \**

**  --dataset test4.xlsx \**

**  --golden config/golden_dataset.xlsx \**

**  --threads 5 \**

**  --version test4 \**

**  --verbose \**

**  --show-prompts- `--model`：评测使用的模型名称（须在 **`config/model.yaml` 中配置）

**- `--dataset`：待评测数据集文件名（位于 `Datasets/` 下）**

**- `--golden`：精标数据集路径，用于“反思学习”（可选）**

**- `--threads`：并发线程数**

**- `--version`：结果输出目录版本号**

**- `--verbose`：打印更详细的调试信息**

**- `--show-prompts`：是否打印完整 Prompt**

****输出路径示例：****

**- **中间结果：`Results/{version}/{dataset_basename}_{model}/multithread/`

**- **合并结果：`Results/{version}/{dataset_basename}_{model}/{dataset_basename}_{model}Eval.xlsx`

**- 人机一致性报表：写入到上述 Excel 的新 Sheet 中（由 **`check_consistency.py` 追加）

**---**

**### 3. 手动合并与分析（可选）**

**如需单独执行合并与一致性分析，可使用：**

**python manual_merge_and_analyze.py在脚本顶部配置：**

**- `VERSION`**

**- `MODEL_NAME`**

**- `DATASET_BASENAME`**

**脚本将：**

**1. 合并 **`Results/{VERSION}/{DATASET_BASENAME}_{MODEL_NAME}/multithread/` **下的多线程结果；**

**2. 在合并后的 Excel 上执行人机一致性分析。**

**---**

**## 开发者说明**

**- 推荐从 `processor.py` 理解核心“四步链路”逻辑，再看 **`processor_threaded.py` 的多线程实现。

**- 所有与 LLM 调用相关的逻辑集中在：**

**  - `evaluation.py`（高层接口）**

**  - `utils/vivo_model.py`（底层 HTTP 调用封装）**

**- 如需扩展新维度或新标签：**

**  - 修改 `config/scoring_rules4.yaml`**

**  - 必要时同步更新 Prompt **构造逻辑（`evaluation.py`）与规则引擎（`auto_rules.py`）。

**---**

**## 许可证与版权**

**- 本项目用于内部评测与研究用途。**

**- 如需对外开源或商用发布，请根据公司政策与法务要求增补版权与许可证说明。**

bash

pip install pandas numpy openpyxl pyyaml tqdm requests

**如果项目中已有 `requirements.txt`，建议直接：**

**pip install -r requirements.txt**

---

## 快速开始

### 1. 准备数据与配置

1. 将评测数据集（Excel）放入项目指定目录（例如 Datasets/），格式需包含：

* 用户问题列（如 prompt_content）
* 自研模型对话内容列（如 小Vcompletions_content，JSON 字符串）
* 竞品模型对话内容列（如 竞品completions_content，JSON 字符串）
* 评测维度列（如 度量一级分类）

1. 配置评分规则：

* 编辑 config/scoring_rules4.yaml，按需要调整维度、标签与规则。

1. 配置模型调用：

* 在 config/config.py 指向的 model.yaml 中，填好各模型的 appid、appkey、uri、domain 等信息。

---

### 2. 运行主流程（推荐）

**python** **main.py** **\**

**  **--model** **o3** **\

**  **--dataset** **test4.xlsx** **\

**  **--golden** **config/golden_dataset.xlsx** **\

**  **--threads** **5** **\

**  **--version** **test4** **\

**  **--verbose** **\

**  **--show-prompts

* --model：评测使用的模型名称（须在 config/model.yaml 中配置）
* --dataset：待评测数据集文件名（位于 Datasets/ 下）
* --golden：精标数据集路径，用于“反思学习”（可选）
* --threads：并发线程数
* --version：结果输出目录版本号
* --verbose：打印更详细的调试信息
* --show-prompts：是否打印完整 Prompt

输出路径示例：

* 中间结果：Results/{version}/{dataset_basename}_{model}/multithread/
* 合并结果：Results/{version}/{dataset_basename}_{model}/{dataset_basename}_{model}Eval.xlsx
* 人机一致性报表：写入到上述 Excel 的新 Sheet 中（由 check_consistency.py 追加）

---

### 3. 手动合并与分析（可选）

如需单独执行合并与一致性分析，可使用：

**python** **manual_merge_and_analyze.py**

在脚本顶部配置：

* VERSION
* MODEL_NAME
* DATASET_BASENAME

脚本将：

1. 合并 Results/{VERSION}/{DATASET_BASENAME}_{MODEL_NAME}/multithread/ 下的多线程结果；
2. 在合并后的 Excel 上执行人机一致性分析。

---

## 开发者说明

* 推荐从 processor.py 理解核心“四步链路”逻辑，再看 processor_threaded.py 的多线程实现。
* 所有与 LLM 调用相关的逻辑集中在：
* evaluation.py（高层接口）
* utils/vivo_model.py（底层 HTTP 调用封装）
* 如需扩展新维度或新标签：
* 修改 config/scoring_rules4.yaml
* 必要时同步更新 Prompt 构造逻辑（evaluation.py）与规则引擎（auto_rules.py）。

---

## 许可证与版权

* 本项目用于内部评测与研究用途。
* 如需对外开源或商用发布，请根据公司政策与法务要求增补版权与许可证说明。

```

```

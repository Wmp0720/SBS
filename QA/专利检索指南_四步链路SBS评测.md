# 专利检索指南：四步链路SBS评测相关专利

## 一、专利检索平台推荐

### 1. 中国专利检索平台
- **中国国家知识产权局专利检索系统**：http://pss-system.cnipa.gov.cn/
- **SooPat专利检索**：http://www.soopat.com/
- **智慧芽专利检索**：https://www.zhihuiya.com/
- **Incopat专利检索**：https://www.incopat.com/

### 2. 国际专利检索平台
- **USPTO（美国专利商标局）**：https://www.uspto.gov/patents/search
- **EPO（欧洲专利局）**：https://worldwide.espacenet.com/
- **WIPO（世界知识产权组织）**：https://patentscope.wipo.int/

## 二、核心关键词组合策略

### 2.1 中文关键词组合

#### 组合1：核心概念
```
("大语言模型" OR "LLM" OR "大型语言模型") 
AND 
("评测" OR "评估" OR "评价" OR "测试")
```

#### 组合2：多步/链式概念
```
("多步推理" OR "链式思维" OR "思维链" OR "CoT" OR "Chain of Thought")
AND
("评测" OR "评估" OR "评价")
```

#### 组合3：对比评测概念
```
("对比评测" OR "Side-by-Side" OR "SBS" OR "并排对比" OR "模型对比")
AND
("大语言模型" OR "LLM")
```

#### 组合4：自动化评测概念
```
("自动化评测" OR "自动评估" OR "自动化评估")
AND
("对话系统" OR "对话模型" OR "聊天机器人")
```

#### 组合5：裁判/判断概念
```
("LLM裁判" OR "模型裁判" OR "自动裁判" OR "AI裁判" OR "LLM-as-a-Judge")
AND
("评测" OR "评估")
```

### 2.2 英文关键词组合

#### 组合1：Core Concepts
```
("Large Language Model" OR "LLM" OR "GPT" OR "ChatGPT")
AND
("Evaluation" OR "Assessment" OR "Testing" OR "Benchmarking")
```

#### 组合2：Multi-step/CoT Concepts
```
("Multi-step reasoning" OR "Chain of Thought" OR "CoT" OR "Stepwise reasoning")
AND
("Evaluation" OR "Assessment")
```

#### 组合3：Comparative Evaluation
```
("Side-by-Side" OR "Comparative evaluation" OR "Pairwise comparison")
AND
("Large Language Model" OR "LLM")
```

#### 组合4：Automated Evaluation
```
("Automated evaluation" OR "Automatic assessment")
AND
("Dialogue system" OR "Conversational AI" OR "Chatbot")
```

#### 组合5：LLM-as-a-Judge
```
("LLM-as-a-Judge" OR "LLM judge" OR "Model judge" OR "AI judge")
AND
("Evaluation" OR "Assessment")
```

## 三、IPC分类号检索

### 3.1 相关IPC分类号

- **G06F 17/00**：特别适用于特定功能的数字计算设备或数据处理设备或数据处理方法
- **G06F 17/27**：自动分析，例如语法分析、校正；语言识别
- **G06F 17/28**：自然语言处理
- **G06N 3/00**：基于生物学模型的计算机系统
- **G06N 3/08**：学习算法
- **G06N 5/00**：基于知识推理的计算机系统
- **G06N 20/00**：机器学习

### 3.2 组合检索示例
```
IPC分类号: G06F 17/28 OR G06N 3/08
AND
关键词: ("大语言模型" AND "评测")
```

## 四、检索策略与技巧

### 4.1 检索层次

#### 第一层：宽泛检索
- 目标：找到所有可能相关的专利
- 策略：使用核心关键词，不限制时间
- 示例：`("大语言模型" AND "评测")`

#### 第二层：精确检索
- 目标：找到与你的技术方案最接近的专利
- 策略：组合多个关键词，限制时间范围（近3-5年）
- 示例：`("大语言模型" AND "多步推理" AND "对比评测")`

#### 第三层：深度检索
- 目标：找到可能构成现有技术的专利
- 策略：阅读第一层和第二层检索结果的引用专利
- 方法：查看"引用的专利"和"被引用的专利"

### 4.2 时间范围建议

- **重点关注**：2020年至今（LLM快速发展期）
- **次要关注**：2015-2020年（深度学习评测方法）
- **参考范围**：2010-2015年（传统NLP评测方法）

### 4.3 检索字段选择

- **标题/摘要**：快速筛选相关专利
- **权利要求**：判断技术方案是否重叠
- **说明书**：了解技术细节和实现方式
- **全文检索**：确保不遗漏相关专利

## 五、重点关注的技术点

### 5.1 需要重点检索的技术特征

1. **多步评测流程**
   - 关键词：多步、分步、阶段、步骤、流程
   - 关注点：是否有固定的多步评测流程

2. **事实收集与裁决分离**
   - 关键词：事实收集、证据收集、分析、裁决、判断
   - 关注点：是否有将"分析"和"裁决"分离的设计

3. **CoT（Chain of Thought）在评测中的应用**
   - 关键词：CoT、链式思维、思维链、推理链
   - 关注点：是否将CoT用于评测而非生成

4. **Side-by-Side对比评测**
   - 关键词：Side-by-Side、SBS、对比、并排、成对
   - 关注点：是否有专门的SBS评测框架

5. **标签映射与规则推理**
   - 关键词：标签映射、规则推理、自动推理、标签归一化
   - 关注点：是否有类似的标签处理机制

### 5.2 可能相关的专利类型

1. **评测方法类专利**
   - 关注：评测流程、评测步骤、评测指标

2. **系统架构类专利**
   - 关注：模块划分、数据流转、接口设计

3. **算法类专利**
   - 关注：标签映射算法、规则推理算法

## 六、检索结果分析要点

### 6.1 判断专利相关性的标准

#### 高度相关（需要重点关注）
- 包含"多步评测流程"或"分步评测"
- 包含"事实收集"+"裁决"分离的设计
- 包含"Side-by-Side"或"对比评测"框架
- 包含"CoT"在评测中的应用

#### 中度相关（需要了解）
- 包含"LLM评测"或"自动化评测"
- 包含"多步推理"但不明确用于评测
- 包含"对比评测"但方法不同

#### 低度相关（参考即可）
- 仅涉及"LLM"或"评测"的单一概念
- 评测方法完全不同（如单模型评测）

### 6.2 需要重点阅读的专利部分

1. **权利要求书**
   - 判断技术方案是否与你的方案重叠
   - 关注独立权利要求的技术特征

2. **技术方案部分**
   - 了解具体实现方式
   - 对比与你的方案的差异

3. **实施例**
   - 了解具体应用场景
   - 判断是否与你的应用场景相同

## 七、具体检索示例

### 7.1 中国专利检索示例

在**中国国家知识产权局专利检索系统**中：

```
检索式1（宽泛）：
(大语言模型 OR LLM OR 大型语言模型) AND (评测 OR 评估 OR 评价)

检索式2（精确）：
(大语言模型 OR LLM) AND (多步推理 OR 链式思维 OR CoT) AND (评测 OR 评估)

检索式3（SBS相关）：
(大语言模型 OR LLM) AND (对比评测 OR Side-by-Side OR SBS OR 并排对比)

检索式4（裁判相关）：
(LLM裁判 OR 模型裁判 OR LLM-as-a-Judge) AND (评测 OR 评估)
```

### 7.2 美国专利检索示例

在**USPTO Patent Search**中：

```
检索式1：
TTL/(("Large Language Model" OR LLM) AND (Evaluation OR Assessment))

检索式2：
TTL/(("Chain of Thought" OR CoT OR "Multi-step reasoning") AND Evaluation)

检索式3：
TTL/(("Side-by-Side" OR "Comparative evaluation") AND ("Large Language Model" OR LLM))

检索式4：
TTL/("LLM-as-a-Judge" OR "LLM judge") AND Evaluation
```

### 7.3 欧洲专利检索示例

在**Espacenet**中：

```
检索式1：
("Large Language Model" OR LLM) AND (Evaluation OR Assessment)

检索式2：
("Chain of Thought" OR CoT) AND ("Model evaluation" OR "Automated assessment")

检索式3：
("Side-by-Side" OR "Pairwise comparison") AND ("Language Model" OR LLM)
```

## 八、检索后的工作

### 8.1 建立专利对比表

对检索到的相关专利，建议建立对比表：

| 专利号 | 专利名称 | 技术方案 | 与本发明差异 | 相关性评级 |
|--------|---------|---------|------------|-----------|
| CN... | ... | ... | ... | 高/中/低 |

### 8.2 撰写现有技术分析

- 总结现有技术的共同特点
- 指出现有技术的不足
- 突出本发明的创新点

### 8.3 调整专利申请策略

根据检索结果：
- 如果发现高度相关的专利：需要调整技术方案，突出差异化
- 如果未发现相关专利：可以更自信地申请，但仍需谨慎撰写

## 九、可能相关的学术论文（作为参考）

虽然论文不是专利，但可以帮助了解技术趋势：

1. **LLM-as-a-Judge相关**
   - "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena"
   - "Crowd Comparative Reasoning: Unlocking Comprehensive Evaluations for LLM-as-a-Judge"

2. **CoT评测相关**
   - "TRACT: Regression-Aware Fine-tuning Meets Chain-of-Thought Reasoning for LLM-as-a-Judge"
   - "Self-Consistency Improves Chain of Thought Reasoning in Language Models"

3. **多步推理相关**
   - "PCRLLM: Proof-Carrying Reasoning with Large Language Models under Stepwise Logical Constraints"
   - "DetermLR: Augmenting LLM-based Logical Reasoning from Indeterminacy to Determinacy"

## 十、建议的检索顺序

1. **第一步**：在中国专利数据库进行宽泛检索
   - 使用组合1和组合2的关键词
   - 时间范围：2020年至今
   - 目标：找到10-20篇可能相关的专利

2. **第二步**：阅读检索结果的标题和摘要
   - 筛选出5-10篇高度相关的专利
   - 记录专利号和基本信息

3. **第三步**：深度阅读高度相关的专利
   - 重点阅读权利要求书和技术方案
   - 建立专利对比表

4. **第四步**：在国际专利数据库检索
   - 使用英文关键词组合
   - 重点关注USPTO和EPO的专利

5. **第五步**：查看引用关系
   - 阅读相关专利的"被引用专利"
   - 可能发现更多相关专利

6. **第六步**：综合分析
   - 总结现有技术状况
   - 确定本发明的创新点
   - 调整专利申请策略

## 十一、注意事项

1. **专利检索是一个迭代过程**
   - 不要期望一次检索就能找到所有相关专利
   - 需要多次调整关键词组合

2. **关注专利的法律状态**
   - 已授权专利：需要重点关注，可能构成现有技术
   - 申请中专利：了解技术趋势，但不会影响你的申请
   - 已失效专利：参考价值较低

3. **注意专利的地域性**
   - 中国专利：主要影响在中国申请
   - 国际专利：可能影响PCT申请

4. **建议委托专业机构**
   - 如果条件允许，建议委托专利代理机构进行专业检索
   - 专业检索更全面、更准确

## 十二、快速检索清单

### 必检关键词组合（按优先级）

1. ⭐⭐⭐ 最高优先级
   - `("大语言模型" OR "LLM") AND ("多步推理" OR "CoT" OR "链式思维") AND "评测"`
   - `("Large Language Model" OR LLM) AND ("Chain of Thought" OR CoT) AND Evaluation`

2. ⭐⭐ 高优先级
   - `("大语言模型" OR "LLM") AND ("对比评测" OR "Side-by-Side" OR "SBS")`
   - `("LLM裁判" OR "LLM-as-a-Judge") AND "评测"`

3. ⭐ 中优先级
   - `("大语言模型" OR "LLM") AND ("自动化评测" OR "自动评估")`
   - `("对话系统" OR "对话模型") AND ("评测" OR "评估")`

### 必检专利数据库

1. 中国国家知识产权局专利检索系统
2. USPTO Patent Search
3. Espacenet（欧洲专利局）

### 必检时间范围

- 主要：2020年至今
- 次要：2015-2020年

---

**建议**：完成检索后，将结果整理成表格，并与专利代理人讨论，以确定最佳的专利申请策略。



#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信息源事实性检测模块
专门用于知识问答维度的信息源验证和事实核查
"""

import json
import re
import yaml
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

# 导入vivo_GPT模型调用
from utils.vivo_model import vivo_GPT

logger = logging.getLogger(__name__)


class SourceChecker:
    """信息源检测器"""

    def __init__(self, rules: dict, verbose: bool = False, show_prompts: bool = False):
        """
        初始化信息源检测器

        Args:
            rules: 评分规则配置
            verbose: 详细输出模式
            show_prompts: 是否显示完整的prompt内容
        """
        self.rules = rules
        self.src_cfg = rules.get("source_reliability", {})
        self.reliable_keywords = self.src_cfg.get("reliable_keywords", [])
        self.suspicious_keywords = self.src_cfg.get("suspicious_keywords", [])
        self.output_schema = self.src_cfg.get("output_schema", "")
        self.verbose = verbose
        self.show_prompts = show_prompts

        # 可用的联网API模型
        self.available_models = {
            "Doubao-1.6-agent-pro": "Doubao-1.6-agent-pro",
            "Doubao-1.5-thinking-pro": "Doubao-1.5-thinking-pro",
            "Doubao-1.6-agent-lite": "Doubao-1.6-agent-lite",
            "Doubao-1.6-agent-pro-thinking": "Doubao-1.6-agent-pro-thinking"
        }

        logger.info("信息源检测器初始化完成")

    def extract_question_topic(self, question: str) -> str:
        """
        从问题中提取核心主题关键词

        Args:
            question: 用户问题

        Returns:
            核心主题关键词
        """
        # 移除常见疑问词和停用词
        stop_words = {'什么', '如何', '怎么', '为什么', '哪里', '什么时候', '哪些', '吗', '呢', '？', '。', '，', '的', '了', '是', '在', '有', '和', '与', '或', '但', '如果', '请问', '麻烦', '请'}

        # 简单分词和关键词提取
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', question)
        keywords = [word for word in words if len(word) > 1 and word not in stop_words]

        # 取前3个最重要的关键词
        return " ".join(keywords[:3])

    def check_source_reliability(self, answer: str) -> Dict[str, Any]:
        """
        检查回答中已有引用的可靠性

        Args:
            answer: 大模型回答

        Returns:
            信源检测结果
        """
        # 检查是否包含外部引用
        source_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+|《[^》]+》|《[^>]+》|《[^>]+》|《[^>]+》'
        sources = re.findall(source_pattern, answer)

        if not sources:
            return {
                "信源判定": "无外部引用",
                "判定理由": "回答中未发现外部引用",
                "补充情报": []
            }

        # 分析引用类型
        reliable_count = 0
        suspicious_count = 0
        source_details = []

        for source in sources:
            is_reliable = False
            is_suspicious = False

            # 检查可靠关键词
            for keyword in self.reliable_keywords:
                if keyword in source:
                    is_reliable = True
                    break

            # 检查可疑关键词
            if not is_reliable:
                for keyword in self.suspicious_keywords:
                    if keyword in source:
                        is_suspicious = True
                        break

            source_details.append({
                "source": source,
                "is_reliable": is_reliable,
                "is_suspicious": is_suspicious
            })

            if is_reliable:
                reliable_count += 1
            elif is_suspicious:
                suspicious_count += 1

        # 判断整体信源可靠性
        if reliable_count > 0 and suspicious_count == 0:
            judgment = "可靠"
            reason = f"发现{reliable_count}个可靠信源，无可疑信源"
        elif suspicious_count > 0:
            judgment = "可疑"
            reason = f"发现{suspicious_count}个可疑信源"
        else:
            judgment = "一般"
            reason = "信源类型不明确"

        return {
            "信源判定": judgment,
            "判定理由": reason,
            "补充情报": []
        }

    def search_online_sources(self, question: str, model: str = "Doubao-1.6-agent-lite") -> List[Dict[str, str]]:
        """
        使用联网API搜索相关信息源

        Args:
            question: 用户问题
            model: 使用的联网API模型

        Returns:
            补充信息源列表
        """
        try:
            # 提取问题主题
            topic = self.extract_question_topic(question)

            # 构建搜索提示
            search_prompt = f"""
请作为专业信息检索助手，针对用户问题"{question}"（核心主题：{topic}），搜索并提供3-5条权威、可靠的信息源。

要求：
1. 优先选择政府官网、学术期刊、权威媒体、国际组织等可靠来源
2. 每条信息源应包含标题、URL和30字以内的中文摘要
3. 确保信息源与问题主题高度相关
4. 不要返回注册受限或付费墙内容

请以JSON格式返回，格式如下：
{{
    "信息源": [
        {{
            "title": "信息源标题",
            "url": "完整URL链接",
            "summary": "30字以内的中文摘要"
        }}
    ]
}}

请确保返回有效的JSON格式。
"""

            # 调用联网API
            result = vivo_GPT(
                search_prompt,
                model=model,
                sessionId=str(uuid.uuid4()),
                show_prompts=self.show_prompts
            )

            # 解析JSON结果
            try:
                # 尝试直接解析
                search_result = json.loads(result)
            except json.JSONDecodeError:
                # 尝试提取JSON部分
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    search_result = json.loads(json_match.group())
                else:
                    logger.warning("无法解析搜索结果JSON")
                    return []

            # 提取信息源
            sources = search_result.get("信息源", [])

            # 验证和清理数据
            valid_sources = []
            for source in sources:
                if (source.get("title") and source.get("url") and source.get("summary") and
                    len(source.get("summary", "")) <= 30):
                    valid_sources.append({
                        "title": source["title"].strip(),
                        "url": source["url"].strip(),
                        "summary": source["summary"].strip()
                    })

            logger.info(f"成功搜索到{len(valid_sources)}条信息源")
            return valid_sources

        except Exception as e:
            logger.error(f"信息源搜索失败: {e}")
            return []
    
    def verify_answer_facts(self, answer: str, sources: List[Dict[str, str]],
                          model: str = "Doubao-1.5-thinking-pro") -> Dict[str, Any]:
        """
        验证回答中的事实性

        Args:
            answer: 大模型回答
            sources: 补充信息源
            model: 使用的验证模型

        Returns:
            事实性验证结果
        """
        try:
            # 构建验证提示
            sources_text = "\n".join([f"- {s['title']}: {s['summary']} ({s['url']})" for s in sources])

            verification_prompt = f"""
作为事实核查专家，请对以下大模型回答进行事实性验证：

【大模型回答】
{answer}

【补充信息源】
{sources_text}

请完成以下任务：
1. 检查回答中是否存在明显的事实性错误
2. 对比回答与信息源的一致性
3. 评估回答的准确性和可靠性

请以JSON格式返回验证结果：
{{
    "事实性评分": 0-100的整数,
    "错误描述": "发现的事实性错误描述，若无错误则为空",
    "一致性评分": 0-100的整数,
    "可靠性评估": "高/中/低",
    "改进建议": "针对回答的改进建议"
}}
"""

            # 调用验证API
            result = vivo_GPT(
                verification_prompt,
                model=model,
                sessionId=str(uuid.uuid4()),
                show_prompts=self.show_prompts
            )

            # 解析验证结果
            try:
                verification_result = json.loads(result)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    verification_result = json.loads(json_match.group())
                else:
                    # 返回默认结果
                    return {
                        "事实性评分": 50,
                        "错误描述": "验证结果解析失败",
                        "一致性评分": 50,
                        "可靠性评估": "中",
                        "改进建议": "需要人工验证"
                    }

            # 确保评分在合理范围内
            verification_result["事实性评分"] = max(0, min(100, int(verification_result.get("事实性评分", 50))))
            verification_result["一致性评分"] = max(0, min(100, int(verification_result.get("一致性评分", 50))))

            return verification_result

        except Exception as e:
            logger.error(f"事实性验证失败: {e}")
            return {
                "事实性评分": 50,
                "错误描述": "验证过程出错",
                "一致性评分": 50,
                "可靠性评估": "中",
                "改进建议": "需要人工验证"
            }

    def comprehensive_source_check(self, question: str, answer: str,
                                 search_model: str = "Doubao-1.6-agent-lite",
                                 verify_model: str = "Doubao-1.5-thinking-pro") -> Dict[str, Any]:
        """
        综合信息源检测

        Args:
            question: 用户问题
            answer: 大模型回答
            search_model: 搜索模型
            verify_model: 验证模型

        Returns:
            综合检测结果
        """
        logger.info(f"开始综合信息源检测: {question[:50]}...")

        # 1. 检查已有信源可靠性
        source_reliability = self.check_source_reliability(answer)

        # 2. 搜索补充信息源
        additional_sources = self.search_online_sources(question, search_model)

        # 3. 验证回答事实性
        verification_result = self.verify_answer_facts(answer, additional_sources, verify_model)

        # 4. 计算综合评分
        fact_score = verification_result.get("事实性评分", 50)
        consistency_score = verification_result.get("一致性评分", 50)
        reliability_score = 80 if source_reliability["信源判定"] == "可靠" else 60 if source_reliability["信源判定"] == "一般" else 40

        # 线性加权计算综合评分
        comprehensive_score = int(fact_score * 0.4 + consistency_score * 0.3 + reliability_score * 0.3)

        # 构建最终结果
        result = {
            "检测时间": datetime.now().isoformat(),
            "问题": question,
            "回答": answer,
            "信源可靠性": source_reliability,
            "补充信息源": additional_sources,
            "事实性验证": verification_result,
            "综合评分": comprehensive_score,
            "评分等级": self._get_score_level(comprehensive_score),
            "检测建议": self._generate_detection_suggestions(source_reliability, verification_result, additional_sources)
        }

        logger.info(f"信息源检测完成，综合评分: {comprehensive_score}")
        return result

    def _get_score_level(self, score: int) -> str:
        """根据评分获取等级"""
        if score >= 80:
            return "优秀"
        elif score >= 60:
            return "良好"
        elif score >= 40:
            return "一般"
        else:
            return "需改进"

    def _generate_detection_suggestions(self, source_reliability: Dict,
                                      verification_result: Dict,
                                      additional_sources: List) -> str:
        """生成检测建议"""
        suggestions = []

        # 信源建议
        if source_reliability["信源判定"] == "可疑":
            suggestions.append("建议引用更权威的信息源")
        elif source_reliability["信源判定"] == "无外部引用":
            suggestions.append("建议增加权威信息源引用")

        # 事实性建议
        if verification_result.get("错误描述"):
            suggestions.append("存在事实性错误，需要修正")

        # 信息源数量建议
        if len(additional_sources) < 3:
            suggestions.append("建议增加更多补充信息源")

        # 一致性建议
        if verification_result.get("一致性评分", 50) < 60:
            suggestions.append("回答与信息源一致性较低，需要调整")

        return "；".join(suggestions) if suggestions else "回答质量良好，建议保持"
    def create_knowledge_qa_sbs_prompt(question: str, v_answer: str, c_answer: str,
                                 source_check_v: Dict, source_check_c: Dict,
                                 rules: dict) -> str:
        """
            创建知识问答维度的SBS裁判提示

            Args:
                question: 用户问题
                v_answer: 自研模型回答
                c_answer: 竞品模型回答
                source_check_v: 自研模型信息源检测结果
                source_check_c: 竞品模型信息源检测结果
                rules: 评分规则

            Returns:
                SBS裁判提示
        """
        # 获取知识问答维度的评分标准
        qa_criteria = rules.get("dimension_definitions", {}).get("知识问答", {}).get("score_criteria", {})

        # 构建信息源对比文本
        v_sources_text = ""
        if source_check_v.get("补充信息源"):
            v_sources_text = "【自研模型补充信息源】\n" + "\n".join([
                f"- {s['title']}: {s['summary']}" for s in source_check_v["补充信息源"]
            ])

        c_sources_text = ""
        if source_check_c.get("补充信息源"):
            c_sources_text = "【竞品模型补充信息源】\n" + "\n".join([
                f"- {s['title']}: {s['summary']}" for s in source_check_c["补充信息源"]
            ])

        prompt = f"""
        你是一位专业的知识问答评测专家，请从事实准确性、信息源可靠性、专业深度等角度，对比评估以下两个模型的回答质量。

        【评测维度】知识问答
        {rules.get("dimension_definitions", {}).get("知识问答", {}).get("description", "")}

        【评分标准】
        准确性 (满分2分): {qa_criteria.get("准确性", {}).get("rules", {})}
        专业性 (满分2分): {qa_criteria.get("专业性", {}).get("rules", {})}
        时效性 (满分2分): {qa_criteria.get("时效性", {}).get("rules", {})}
        格式 (满分2分): {qa_criteria.get("格式", {}).get("rules", {})}
        详略得当 (满分2分): {qa_criteria.get("详略得当", {}).get("rules", {})}
        逻辑 (满分2分): {qa_criteria.get("逻辑", {}).get("rules", {})}
        回复风格 (满分2分): {qa_criteria.get("回复风格", {}).get("rules", {})}

        【用户问题】
        {question}

        【自研模型回答】
        {v_answer}
        {v_sources_text}

        【竞品模型回答】
        {c_answer}
        {c_sources_text}

        【信息源检测结果对比】
        自研模型综合评分: {source_check_v.get('综合评分', '未知')} ({source_check_v.get('评分等级', '未知')})
        竞品模型综合评分: {source_check_c.get('综合评分', '未知')} ({source_check_c.get('评分等级', '未知')})

        【评测任务】
        请严格按照以下步骤进行评测：

        1. 事实准确性对比:
        - 检查两个回答中是否存在事实性错误
        - 对比回答的准确性和完整性
        - 评估答案与问题的相关性

        2. 信息源质量对比:
        - 对比两个回答中引用的信息源权威性
        - 评估补充信息源的相关性和可靠性
        - 检查信息源的时效性

        3. 专业深度对比:
        - 对比回答的专业性和深度
        - 评估知识拓展的合理性
        - 检查逻辑结构的清晰度

        4. 用户体验对比:
        - 对比回答的格式和呈现方式
        - 评估信息量的合理性
        - 检查回复风格的自然度

        【输出要求】
        请严格按照以下JSON格式输出评测结果：
        {{
        "大模型A二级满意度": "弱智/不合格/合格/优质",
        "大模型B二级满意度": "弱智/不合格/合格/优质", 
        "大模型A优质弱智主要问题": "",
        "大模型B优质弱智主要问题": "",
        "大模型A竞品对比": "胜/平/负",
        "大模型A主要问题": "主类_子类（可多个，用英文逗号分隔）",
        "大模型B主要问题": "主类_子类（可多个，用英文逗号分隔）",
        "LLMs_标注理由": "基于信息源检测和事实性对比的详细评测理由"
        }}

        【特别说明】
        - 知识问答维度重点关注事实准确性和信息源可靠性
        - 对于涉及医疗、法律、金融等敏感内容，必须检查是否有免责声明
        - 优先选择信息源更权威、事实准确性更高的回答
        - 如果双方表现相当，请给出"平"的评判
        """

        return prompt


if __name__ == "__main__":
    # 测试代码
    test_rules = {
        "source_reliability": {
            "reliable_keywords": ["Nature", "Science", "新华社", "中华医学会", "世卫组织", "政府官网"],
            "suspicious_keywords": ["知乎", "贴吧", "豆瓣小组", "某宝", "微博热搜"],
            "output_schema": "{}"
        },
        "dimension_definitions": {
            "知识问答": {
                "description": "知识问答主要是指与各行业知识相关的问答",
                "score_criteria": {
                    "准确性": {"rules": {"2": "答案和问题的相关性高，并且准确无误"}},
                    "专业性": {"rules": {"2": "答案专业性高，角度全面"}},
                    "时效性": {"rules": {"2": "答案时效性高，结合了最新信息"}},
                    "格式": {"rules": {"2": "答案有markdown层级，对关键答案信息进行了前置加粗"}},
                    "详略得当": {"rules": {"2": "答案中没有冗余，也不啰嗦"}},
                    "逻辑": {"rules": {"2": "答案逻辑顺畅，清晰易懂"}},
                    "回复风格": {"rules": {"2": "答案回复风格较好，没有很强的AI感"}}
                }
            }
        }
    }

    checker = SourceChecker(test_rules)

    # 测试用例
    test_question = "什么是人工智能？"
    test_answer = "人工智能（AI）是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统。"

    result = checker.comprehensive_source_check(test_question, test_answer)
    print(json.dumps(result, ensure_ascii=False, indent=2))
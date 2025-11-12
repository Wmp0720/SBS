#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识问答维度SBS裁判模型集成
专门处理知识问答维度的特殊评估逻辑，包括信息源检测和事实性验证
"""

import json
import re
import yaml
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

# 导入现有模块
from utils.vivo_model import vivo_GPT
from utils.source_checker import SourceChecker, create_knowledge_qa_sbs_prompt

logger = logging.getLogger(__name__)


class KnowledgeQAJudge:
    """知识问答维度SBS裁判"""

    def __init__(self, rules: dict, verbose: bool = False, show_prompts: bool = False):
        """
        初始化知识问答裁判

        Args:
            rules: 评分规则配置
            verbose: 详细输出模式
            show_prompts: 是否显示完整的prompt内容
        """
        self.rules = rules
        self.source_checker = SourceChecker(rules, verbose=verbose, show_prompts=show_prompts)

        # 知识问答裁判模型
        self.judge_model = "Doubao-1.6-agent-pro-thinking"

        # 线性打分权重配置
        self.scoring_weights = {
            "准确性": 0.25,      # 25%
            "专业性": 0.20,      # 20%
            "时效性": 0.15,      # 15%
            "格式": 0.10,        # 10%
            "详略得当": 0.15,    # 15%
            "逻辑": 0.10,        # 10%
            "回复风格": 0.05     # 5%
        }

    def calculate_linear_score(self, scores: Dict[str, int]) -> float:
        """
        计算线性加权总分

        Args:
            scores: 各维度评分

        Returns:
            加权总分
        """
        total_score = 0.0
        for dimension, weight in self.scoring_weights.items():
            dimension_score = scores.get(dimension, 0)
            total_score += dimension_score * weight
        return round(total_score, 2)

    def score_to_satisfaction(self, total_score: float, source_check_result: Dict, answer: str) -> Tuple[str, str]:
        """
        将总分转换为满意度等级

        Args:
            total_score: 总分
            source_check_result: 信息源检测结果
            answer: 模型回答

        Returns:
            满意度等级和主要问题
        """
        # 检查是否需要特殊处理（事实性错误等）
        if self._should_special_handling(source_check_result, answer):
            return "弱智", "2内容质量差_1.内容错误"

        # 根据总分确定满意度
        if total_score >= 85:
            return "优质", ""
        elif total_score >= 60:
            return "合格", ""
        else:
            return "弱智", self._get_main_issues(total_score, source_check_result)

    def _should_special_handling(self, source_check_result: Dict, answer: str) -> bool:
        """判断是否需要特殊处理"""
        # 检查事实性评分
        fact_score = source_check_result.get("事实性验证", {}).get("事实性评分", 100)
        if fact_score < 30:
            return True

        # 检查是否有明显错误
        error_desc = source_check_result.get("事实性验证", {}).get("错误描述", "")
        if "错误" in error_desc and "严重" in error_desc:
            return True

        # 检查是否完全拒答
        if "无法回答" in answer or "不知道" in answer:
            return True

        return False

    def _get_main_issues(self, total_score: float, source_check_result: Dict) -> str:
        """获取主要问题标签"""
        issues = []

        # 根据评分确定问题类型
        if total_score < 40:
            issues.append("2内容质量差_1.内容错误")
        elif total_score < 60:
            issues.append("2内容质量差_3.要点不全面")

        # 检查信息源问题
        source_reliability = source_check_result.get("信源可靠性", {})
        if source_reliability.get("信源判定") == "可疑":
            issues.append("2内容质量差_4.实用性不佳")

        # 检查格式问题
        format_score = source_check_result.get("事实性验证", {}).get("一致性评分", 100)
        if format_score < 60:
            issues.append("7格式及呈现不佳_1.界面呈现不佳")

        return ",".join(issues) if issues else "13无问题"

    def evaluate_knowledge_qa(self, question: str, v_answer: str, c_answer: str,
                             v_history: str = "", c_history: str = "") -> Dict[str, Any]:
        """
        评估知识问答维度的SBS对比

        Args:
            question: 用户问题
            v_answer: 自研模型回答
            c_answer: 竞品模型回答
            v_history: 自研模型对话历史
            c_history: 竞品模型对话历史

        Returns:
            SBS评估结果
        """
        logger.info(f"开始知识问答SBS评估: {question[:50]}...")

        # 1. 信息源检测
        logger.info("执行自研模型信息源检测...")
        v_source_check = self.source_checker.comprehensive_source_check(
            question, v_answer
        )

        logger.info("执行竞品模型信息源检测...")
        c_source_check = self.source_checker.comprehensive_source_check(
            question, c_answer
        )

        # 2. 计算各维度评分
        logger.info("计算自研模型维度评分...")
        v_scores = self._calculate_dimension_scores(v_answer, v_source_check)
        v_total_score = self.calculate_linear_score(v_scores)

        logger.info("计算竞品模型维度评分...")
        c_scores = self._calculate_dimension_scores(c_answer, c_source_check)
        c_total_score = self.calculate_linear_score(c_scores)

        # 3. 转换为满意度等级
        v_satisfaction, v_main_issues = self.score_to_satisfaction(
            v_total_score, v_source_check, v_answer
        )
        c_satisfaction, c_main_issues = self.score_to_satisfaction(
            c_total_score, c_source_check, c_answer
        )

        # 4. 生成优质弱智主要问题
        v_qzrz = self._get_hq_dumb_issues(v_satisfaction, v_scores)
        c_qzrz = self._get_hq_dumb_issues(c_satisfaction, c_scores)

        # 5. 生成SBS裁判提示
        sbs_prompt = create_knowledge_qa_sbs_prompt(
            question, v_answer, c_answer, v_source_check, c_source_check, self.rules
        )

        # 6. 调用SBS裁判模型
        logger.info("调用SBS裁判模型...")
        sbs_result = self._call_judge_model(sbs_prompt)

        # 7. 解析和整合结果 - 确保格式与其他维度一致
        final_result = self._integrate_results_consistent(
            question, v_answer, c_answer,
            v_scores, c_scores, v_total_score, c_total_score,
            v_satisfaction, c_satisfaction, v_main_issues, c_main_issues,
            v_qzrz, c_qzrz,
            v_source_check, c_source_check, sbs_result
        )

        logger.info(f"知识问答SBS评估完成，自研: {v_total_score}, 竞品: {c_total_score}")
        return final_result
    def _get_default_judge_result(self) -> Dict[str, Any]:
        """获取默认裁判结果"""
        return {
            "大模型A二级满意度": "合格",
            "大模型B二级满意度": "合格",
            "大模型A优质弱智主要问题": "",
            "大模型B优质弱智主要问题": "",
            "大模型A竞品对比": "平",
            "大模型A主要问题": "13无问题",
            "大模型B主要问题": "13无问题",
            "LLMs_标注理由": "默认评判结果，建议人工复核"
        }

    def _integrate_results_consistent(self, question: str, v_answer: str, c_answer: str,
                                     v_scores: Dict, c_scores: Dict, v_total_score: float, c_total_score: float,
                                     v_satisfaction: str, c_satisfaction: str, v_main_issues: str, c_main_issues: str,
                                     v_qzrz: str, c_qzrz: str,
                                     v_source_check: Dict, c_source_check: Dict, sbs_result: Dict) -> Dict[str, Any]:
        """
        整合所有评估结果 - 确保格式与其他维度一致

        Args:
            各种评估数据和结果

        Returns:
            最终整合的评估结果
        """
        # 确定竞品对比结果
        if sbs_result.get("大模型A竞品对比"):
            comparison = sbs_result["大模型A竞品对比"]
        else:
            # 根据评分自动判断
            if v_total_score > c_total_score + 10:
                comparison = "胜"
            elif c_total_score > v_total_score + 10:
                comparison = "负"
            else:
                comparison = "平"

        # 构建最终结果 - 确保格式与processor.py中的标准输出一致
        final_result = {
            "大模型A二级满意度": v_satisfaction,
            "大模型A优质弱智主要问题": v_qzrz,
            "大模型B二级满意度": c_satisfaction,
            "大模型B优质弱智主要问题": c_qzrz,
            "大模型A竞品对比": comparison,
            "大模型A主要问题": v_main_issues,
            "大模型B主要问题": c_main_issues,
            "LLMs_标注理由": sbs_result.get("LLMs_标注理由", f"基于线性评分：自研{v_total_score} vs 竞品{c_total_score}"),
            # 保留知识问答特有的信息（可选）
            "维度": "知识问答",
            "问题": question,
            "自研模型回答": v_answer,
            "竞品模型回答": c_answer,
            "自研模型评分": {
                "总分": v_total_score,
                "各维度评分": v_scores,
                "满意度": v_satisfaction,
                "主要问题": v_main_issues,
                "优质弱智主要问题": v_qzrz,
                "信息源检测结果": v_source_check
            },
            "竞品模型评分": {
                "总分": c_total_score,
                "各维度评分": c_scores,
                "满意度": c_satisfaction,
                "主要问题": c_main_issues,
                "优质弱智主要问题": c_qzrz,
                "信息源检测结果": c_source_check
            },
            "评估时间": datetime.now().isoformat()
        }

        return final_result

    def _get_hq_dumb_issues(self, satisfaction: str, scores: Dict) -> str:
        """获取优质或弱智主要问题"""
        if satisfaction == "优质":
            # 根据评分最高的维度选择优质标签
            max_score_dim = max(scores.items(), key=lambda x: x[1])[0]
            quality_tag_mapping = {
                "准确性": "问答_1. 专业有深度",
                "专业性": "问答_2. 实用价值高",
                "时效性": "问答_3. 创新观点",
                "逻辑": "问答_4. 逻辑层次佳"
            }
            return quality_tag_mapping.get(max_score_dim, "问答_1. 专业有深度")
        else:  # 弱智
            return "12弱智_2内容质量差_1.常识缺乏"


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

    judge = KnowledgeQAJudge(test_rules)

    # 测试用例
    test_question = "什么是人工智能？"
    v_answer = "人工智能（AI）是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统。它包括机器学习、深度学习、自然语言处理等技术。"
    c_answer = "人工智能是指由人类制造出来的机器所表现出来的智能。通常人工智能是指通过普通计算机程序来呈现人类智能的技术。"

    result = judge.evaluate_knowledge_qa(test_question, v_answer, c_answer)
    print(json.dumps(result, ensure_ascii=False, indent=2))
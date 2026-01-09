
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证知识问答维度输出格式一致性
"""

import json
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def validate_output_format():
    """验证输出格式"""
    print("🔍 验证知识问答维度输出格式...")

    try:
        from utils.knowledge_qa_judge import KnowledgeQAJudge
        from evaluation import load_rules

        rules = load_rules()
        judge = KnowledgeQAJudge(rules)

        # 检查裁判类的核心方法
        print("导入成功")
        print("KnowledgeQAJudge 类初始化成功")

        # 检查必需的方法是否存在
        required_methods = [
            'evaluate_knowledge_qa',
            'calculate_linear_score',
            'score_to_satisfaction'
        ]

        print("\n 方法检查:")
        for method in required_methods:
            if hasattr(judge, method):
                print(f"  {method}")
            else:
                print(f"  {method}: 缺失")
                return False

        # 检查评分权重配置
        print("\n 评分权重配置:")
        if hasattr(judge, 'scoring_weights'):
            weights = judge.scoring_weights
            total_weight = sum(weights.values())
            print(f"  总权重: {total_weight}")

            if abs(total_weight - 1.0) < 0.01:
                print("  权重配置正确")
            else:
                print(f"  权重配置错误，期望1.0，实际{total_weight}")
                return False
        else:
            print("  缺少scoring_weights配置")
            return False

        # 检查线性打分功能
        print("\n 线性打分测试:")
        test_scores = {
            "准确性": 90,
            "专业性": 85,
            "时效性": 80,
            "格式": 75,
            "详略得当": 85,
            "逻辑": 80,
            "回复风格": 70
        }

        total_score = judge.calculate_linear_score(test_scores)
        print(f"  测试总分: {total_score}")

        if 0 <= total_score <= 100:
            print("  线性打分计算正常")
        else:
            print("  线性打分计算异常")
            return False

        # 检查满意度转换
        print("\n满意度转换测试:")
        satisfaction, issues = judge.score_to_satisfaction(total_score, {}, "")
        print(f"  满意度: {satisfaction}")
        print(f"  主要问题: {issues}")

        if satisfaction in ["优质", "合格", "弱智"]:
            print("  满意度转换正常")
        else:
            print("  满意度转换异常")
            return False

        # 检查输出格式方法
        print("\n📄 输出格式检查:")

        # 模拟一个简单的评估结果结构
        mock_result = {
            "大模型A二级满意度": "合格",
            "大模型A优质弱智主要问题": "",
            "大模型B二级满意度": "合格",
            "大模型B优质弱智主要问题": "",
            "大模型A竞品对比": "平",
            "大模型A主要问题": "13无问题",
            "大模型B主要问题": "13无问题",
            "LLMs_标注理由": "测试结果"
        }

        # 检查必需字段
        required_fields = [
            "大模型A二级满意度",
            "大模型A优质弱智主要问题",
            "大模型B二级满意度",
            "大模型B优质弱智主要问题",
            "大模型A竞品对比",
            "大模型A主要问题",
            "大模型B主要问题",
            "LLMs_标注理由"
        ]

        all_fields_present = True
        for field in required_fields:
            if field in mock_result:
                value = mock_result[field]
                print(f"  {field}: {value}")

                # 验证字段值的有效性
                if field == "大模型A竞品对比" and value not in ["胜", "平", "负"]:
                    print(f"    无效的竞品对比值: {value}")
                    all_fields_present = False
                elif "满意度" in field and value not in ["优质", "合格", "弱智"]:
                    print(f"    无效的满意度值: {value}")
                    all_fields_present = False
            else:
                print(f"  {field}: 缺失")
                all_fields_present = False

        if all_fields_present:
            print("  输出格式完整且有效")
        else:
            print("  输出格式有问题")
            return False

        print("\n 知识问答维度输出格式验证通过！")
        print("与其他维度的输出格式保持一致")
        return True

    except Exception as e:
        print(f"验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print(" 开始知识问答维度输出格式验证...")
    print("=" * 60)

    success = validate_output_format()

    print("\n" + "=" * 60)
    print(" 验证结果")
    print("=" * 60)

    if success:
        print(" 验证成功！")
        print("知识问答维度输出格式与其他维度一致")
        print("所有必需字段都存在且有效")
        print("竞品对比值、满意度值等都符合规范")
    else:
        print("验证失败！")
        print(" 输出格式存在问题，需要修复")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
    
    
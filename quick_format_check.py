#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速输出格式检查
"""

import json
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    print("🔍 快速检查知识问答维度输出格式...")

    try:
        from utils.knowledge_qa_judge import KnowledgeQAJudge
        from evaluation import load_rules

        rules = load_rules()
        judge = KnowledgeQAJudge(rules)

        # 简单测试
        question = "什么是AI？"
        v_answer = "人工智能是计算机科学的一个分支。"
        c_answer = "AI是人工智能的缩写。"

        print("执行评估...")
        result = judge.evaluate_knowledge_qa(question, v_answer, c_answer)

        # 检查核心字段
        core_fields = [
            "大模型A二级满意度",
            "大模型A优质弱智主要问题",
            "大模型B二级满意度",
            "大模型B优质弱智主要问题",
            "大模型A竞品对比",
            "大模型A主要问题",
            "大模型B主要问题",
            "LLMs_标注理由"
        ]

        print("\n📋 核心字段检查:")
        all_present = True
        for field in core_fields:
            if field in result:
                value = result[field]
                print(f"  ✅ {field}: {value}")

                # 验证字段值
                if field == "大模型A竞品对比" and value not in ["胜", "平", "负"]:
                    print(f"    ❌ 无效值: {value}")
                    all_present = False
                elif "满意度" in field and value not in ["优质", "合格", "弱智"]:
                    print(f"    ❌ 无效值: {value}")
                    all_present = False
            else:
                print(f"  ❌ {field}: 缺失")
                all_present = False

        print(f"\n📊 格式一致性: {'✅ 通过' if all_present else '❌ 失败'}")

        if all_present:
            print("\n🎉 知识问答维度输出格式正确！")
            print("✅ 与其他维度的输出格式保持一致")
        else:
            print("\n⚠️ 输出格式存在问题")

        return all_present

    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    print(f"\n最终结果: {'✅ 成功' if success else '❌ 失败'}")
    sys.exit(0 if success else 1)
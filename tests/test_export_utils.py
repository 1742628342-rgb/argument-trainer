import unittest

from modules.export_utils import analysis_to_markdown, export_training_to_markdown


class ExportUtilsTests(unittest.TestCase):
    def setUp(self):
        self.session = {
            "id": 12,
            "original_claim": "所有成功都由努力决定。",
            "opponent_strength": "正常",
            "created_at": "2026-06-14 12:00:00",
        }
        self.analysis = {
            "supporting_reasons": ["努力通常会增加练习量。"],
            "opposing_reasons": ["机会和资源也可能影响结果。"],
            "conditions": ["目标可由个人行动影响。"],
            "concept_shift_risks": ["可能把相关关系偷换成因果关系。"],
            "rigorous_expression": "努力可能提高部分情境下的成功概率。",
            "detected_features": {},
        }

    def test_formats_initial_analysis_as_markdown(self):
        text = analysis_to_markdown(
            self.session["original_claim"],
            self.session["opponent_strength"],
            self.analysis,
        )

        self.assertIn("# 观点反驳训练结果", text)
        self.assertIn("- 努力通常会增加练习量。", text)
        self.assertIn("努力可能提高部分情境下的成功概率。", text)

    def test_exports_complete_training_record(self):
        turns = [
            {
                "turn_number": number,
                "question_type": f"类型 {number}",
                "opponent_question": f"问题 {number}",
                "why_ask": f"原因 {number}",
                "user_answer": f"回答 {number}",
            }
            for number in range(1, 6)
        ]
        score = {
            "scores": {
                "concept_clarity": 6,
                "argument_completeness": 7,
                "counterexample_awareness": 8,
                "boundary_awareness": 7,
                "causal_rigor": 8,
                "expression_maturity": 7,
            },
            "total_score": 43,
            "main_problem": "概念仍需进一步限定。",
            "strongest_part": "能够识别相关与因果的区别。",
            "next_training_advice": "下次补充更具体的定义。",
            "final_rewrite": "在资源和机会相近时，努力可能提高成功概率。",
        }

        text = export_training_to_markdown(
            self.session,
            self.analysis,
            turns,
            score,
        )

        required_sections = (
            "# 观点反驳训练记录",
            "## 原观点",
            "## 初始分析",
            "### 支持这个观点的理由",
            "### 反对这个观点的理由",
            "### 观点成立的条件",
            "### 容易偷换概念的地方",
            "### 更严谨的表达方式",
            "## 5 轮反方追问",
            "## 最终逻辑评分",
            "## 最大问题",
            "## 最值得保留的优点",
            "## 下一次训练建议",
            "## 最终严谨表达",
        )
        for section in required_sections:
            self.assertIn(section, text)

        self.assertIn("### 第 5 轮", text)
        self.assertIn("**问题类型：** 类型 5", text)
        self.assertIn("**我的回答：** 回答 5", text)
        self.assertIn("- 概念清晰度：6/10", text)
        self.assertIn("- 总分：43/60", text)
        self.assertIn("在资源和机会相近时", text)
        text.encode("utf-8")

    def test_exports_without_turns_or_score(self):
        text = export_training_to_markdown(
            self.session,
            self.analysis,
            [],
            None,
        )

        self.assertIn("## 5 轮反方追问\n\n暂无追问记录。", text)
        self.assertIn("## 最终逻辑评分\n\n暂无评分。", text)
        self.assertIn("## 最大问题\n\n暂无。", text)
        self.assertIn(
            "## 最终严谨表达\n\n努力可能提高部分情境下的成功概率。",
            text,
        )

    def test_exports_structured_llm_analysis_with_field_labels(self):
        analysis = {
            **self.analysis,
            "supporting_reasons": [
                {
                    "reason": "努力增加练习量。",
                    "condition": "目标受练习影响。",
                    "example": "持续训练提高熟练度。",
                }
            ],
            "opposing_reasons": [
                {
                    "reason": "资源也会影响结果。",
                    "weakness": "忽略外部条件。",
                    "example": "机会不同会产生不同结果。",
                }
            ],
            "concept_shift_risks": [
                {
                    "risk": "把相关当因果。",
                    "why": "尚未排除其他变量。",
                    "better_boundary": "改为可能提高概率。",
                }
            ],
        }

        text = export_training_to_markdown(self.session, analysis, [], None)

        self.assertIn("理由：努力增加练习量。", text)
        self.assertIn("适用前提：目标受练习影响。", text)
        self.assertIn("可能漏洞：忽略外部条件。", text)
        self.assertIn("更好的边界：改为可能提高概率。", text)


if __name__ == "__main__":
    unittest.main()

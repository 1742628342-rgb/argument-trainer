import unittest

from modules.prompt_templates import (
    build_analysis_prompts,
    build_debate_prompts,
    build_scoring_prompts,
    merge_analysis_with_rule_fallback,
    merge_question_with_rule_fallback,
    merge_score_with_rule_fallback,
)


class PromptTemplateTests(unittest.TestCase):
    def test_prompts_request_required_json_contracts(self):
        _, analysis_prompt = build_analysis_prompts("观点", "正常")
        _, debate_prompt = build_debate_prompts("观点", [], 1, "正常")
        _, scoring_prompt = build_scoring_prompts("观点", {}, [])

        self.assertIn('"supporting_reasons"', analysis_prompt)
        self.assertIn('"question_type"', debate_prompt)
        self.assertIn('"concept_clarity"', scoring_prompt)

    def test_partial_analysis_uses_rule_fallback_for_missing_fields(self):
        rule = {
            "supporting_reasons": ["规则支持"],
            "opposing_reasons": ["规则反对"],
            "conditions": ["规则条件"],
            "concept_shift_risks": ["规则风险"],
            "rigorous_expression": "规则改写",
            "detected_features": {"absolute_terms": []},
        }
        merged = merge_analysis_with_rule_fallback(
            {"rigorous_rewrite": "模型改写"},
            rule,
        )

        self.assertEqual(merged["supporting_reasons"], ["规则支持"])
        self.assertEqual(merged["rigorous_expression"], "模型改写")
        self.assertEqual(merged["detected_features"], rule["detected_features"])

    def test_analysis_merge_rejects_wrong_field_types(self):
        rule = {
            "supporting_reasons": ["规则支持"],
            "opposing_reasons": ["规则反对"],
            "conditions": ["规则条件"],
            "concept_shift_risks": ["规则风险"],
            "rigorous_expression": "规则改写",
            "detected_features": {},
        }

        merged = merge_analysis_with_rule_fallback(
            {
                "supporting_reasons": "不是列表",
                "opposing_reasons": {"reason": "不是列表"},
                "valid_conditions": [""],
                "concept_switch_risks": 42,
                "rigorous_rewrite": ["不是文本"],
            },
            rule,
        )

        self.assertEqual(merged["supporting_reasons"], ["规则支持"])
        self.assertEqual(merged["opposing_reasons"], ["规则反对"])
        self.assertEqual(merged["conditions"], ["规则条件"])
        self.assertEqual(merged["concept_shift_risks"], ["规则风险"])
        self.assertEqual(merged["rigorous_expression"], "规则改写")

    def test_partial_question_and_score_use_rule_fallback(self):
        question = merge_question_with_rule_fallback(
            {"question": "模型问题？"},
            {
                "question": "规则问题？",
                "question_type": "定义追问",
                "why_ask": "规则原因",
            },
        )
        self.assertEqual(question["question"], "模型问题？")
        self.assertEqual(question["question_type"], "定义追问")

        score = merge_score_with_rule_fallback(
            {"scores": {"concept_clarity": 8}},
            {
                "scores": {
                    "concept_clarity": 5,
                    "argument_completeness": 5,
                    "counterexample_awareness": 5,
                    "boundary_awareness": 5,
                    "causal_rigor": 5,
                    "expression_maturity": 5,
                },
                "total_score": 30,
                "main_problem": "规则问题",
                "strongest_part": "规则优点",
                "next_training_advice": "规则建议",
                "final_rewrite": "规则改写",
            },
        )
        self.assertEqual(score["scores"]["concept_clarity"], 8)
        self.assertEqual(score["scores"]["causal_rigor"], 5)
        self.assertEqual(score["total_score"], sum(score["scores"].values()))
        self.assertEqual(score["final_rewrite"], "规则改写")


if __name__ == "__main__":
    unittest.main()

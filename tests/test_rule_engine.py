import unittest

from modules.rule_engine import (
    analyze_claim_rule_based,
    generate_opponent_question_rule_based,
)


class RuleEngineTests(unittest.TestCase):
    def test_returns_all_analysis_sections(self):
        result = analyze_claim_rule_based(
            "只要情绪独立，就一定不需要别人。",
            "正常",
        )

        self.assertEqual(
            set(result),
            {
                "supporting_reasons",
                "opposing_reasons",
                "conditions",
                "concept_shift_risks",
                "rigorous_expression",
                "detected_features",
            },
        )
        for key in (
            "supporting_reasons",
            "opposing_reasons",
            "conditions",
            "concept_shift_risks",
        ):
            self.assertTrue(result[key])

        self.assertIn("一定", result["detected_features"]["absolute_terms"])
        self.assertIn("只要", result["detected_features"]["causal_terms"])
        self.assertTrue(
            any("情绪独立" in item for item in result["concept_shift_risks"])
        )
        self.assertIn("需要进一步限定", result["rigorous_expression"])

    def test_strength_changes_opposing_tone_without_personal_attack(self):
        mild = analyze_claim_rule_based("所有成功都由努力决定。", "温和")
        sharp = analyze_claim_rule_based("所有成功都由努力决定。", "尖锐但不攻击")

        self.assertNotEqual(mild["opposing_reasons"], sharp["opposing_reasons"])
        self.assertTrue(any("直接反问" in item for item in sharp["opposing_reasons"]))
        self.assertFalse(any("你" in item for item in sharp["opposing_reasons"]))

    def test_rejects_blank_claim_and_invalid_strength(self):
        with self.assertRaises(ValueError):
            analyze_claim_rule_based("   ", "正常")

        with self.assertRaises(ValueError):
            analyze_claim_rule_based("努力可能提高成功概率。", "激烈")

    def test_generates_the_five_required_question_types(self):
        expected_types = ("定义追问", "边界追问", "反例追问", "因果追问", "实践副作用追问")

        for turn_number, expected_type in enumerate(expected_types, start=1):
            result = generate_opponent_question_rule_based(
                "所有成功都由努力决定。",
                [],
                turn_number,
                "正常",
            )

            self.assertEqual(result["question_type"], expected_type)
            self.assertIn("所有成功都由努力决定", result["question"])
            self.assertEqual(result["question"].count("？"), 1)
            self.assertTrue(result["why_ask"])

    def test_follow_up_uses_previous_answer_without_attacking_user(self):
        result = generate_opponent_question_rule_based(
            "所有成功都由努力决定。",
            [{"turn_number": 1, "user_answer": "成功是达到自己设定的目标。"}],
            2,
            "尖锐但不攻击",
        )

        self.assertIn("达到自己设定的目标", result["question"])
        self.assertIn("直接", result["question"])
        self.assertNotIn("愚蠢", result["question"])

    def test_rejects_invalid_debate_question_inputs(self):
        with self.assertRaises(ValueError):
            generate_opponent_question_rule_based("", [], 1, "正常")

        with self.assertRaises(ValueError):
            generate_opponent_question_rule_based("观点", [], 6, "正常")


if __name__ == "__main__":
    unittest.main()

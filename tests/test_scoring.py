import unittest

from modules.scoring import score_answers_rule_based


def make_turns(answers):
    return [
        {
            "turn_number": index,
            "question_type": f"第{index}轮",
            "user_answer": answer,
        }
        for index, answer in enumerate(answers, start=1)
    ]


class ScoringTests(unittest.TestCase):
    def test_scores_all_dimensions_without_giving_automatic_full_marks(self):
        turns = make_turns(
            [
                "我说的是：成功具体指达到自己设定并可验证的目标。",
                "但是在资源不足或健康受限的情况下不一定成立，范围取决于条件。",
                "例如同样努力的人，也可能因为机会不同而有不同结果，这是一个反例。",
                "努力和成功可能相关，但不能说明存在单一因果关系。",
                "更准确地说，这个观点需要限定，否则可能导致过度自责。",
            ]
        )

        result = score_answers_rule_based(
            "所有成功都由努力决定。",
            {"rigorous_expression": "努力可能提高部分情境下的成功概率。"},
            turns,
        )

        self.assertEqual(
            set(result["scores"]),
            {
                "concept_clarity",
                "argument_completeness",
                "counterexample_awareness",
                "boundary_awareness",
                "causal_rigor",
                "expression_maturity",
            },
        )
        self.assertEqual(result["total_score"], sum(result["scores"].values()))
        self.assertTrue(all(0 <= score <= 10 for score in result["scores"].values()))
        self.assertTrue(any(score < 10 for score in result["scores"].values()))
        self.assertGreater(len(set(result["scores"].values())), 1)
        self.assertTrue(result["main_problem"])
        self.assertTrue(result["strongest_part"])
        self.assertNotEqual(result["main_problem"], result["strongest_part"])
        self.assertTrue(result["next_training_advice"])
        self.assertIn("部分情境", result["final_rewrite"])

    def test_short_repetitive_absolute_answers_score_lower(self):
        strong = score_answers_rule_based(
            "所有成功都由努力决定。",
            {},
            make_turns(
                [
                    "定义为达到目标。",
                    "但是在资源不足的情况下不一定成立。",
                    "例如有人努力却失败，这是反例。",
                    "只是相关，不能说明因果。",
                    "可能有副作用，需要限定。",
                ]
            ),
        )
        weak = score_answers_rule_based(
            "所有成功都由努力决定。",
            {},
            make_turns(["所有成功都由努力决定。"] * 5),
        )

        self.assertLess(weak["total_score"], strong["total_score"])

    def test_requires_five_completed_turns(self):
        with self.assertRaises(ValueError):
            score_answers_rule_based("观点", {}, make_turns(["回答"] * 4))


if __name__ == "__main__":
    unittest.main()

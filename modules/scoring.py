from __future__ import annotations

from collections import Counter
from typing import Any


SCORE_RULES = {
    "concept_clarity": ("意思是", "定义为", "我说的是", "具体指"),
    "argument_completeness": ("例如", "比如", "因为", "所以", "理由是"),
    "counterexample_awareness": ("但是", "也可能", "不一定", "反例", "例外"),
    "boundary_awareness": ("前提", "条件", "范围", "情况下", "取决于", "除非"),
    "causal_rigor": ("相关", "因果", "导致", "不能说明", "只是同时出现"),
    "expression_maturity": ("可能", "更准确地说", "不能绝对", "需要限定"),
}

SCORE_LABELS = {
    "concept_clarity": "概念清晰度",
    "argument_completeness": "论证完整度",
    "counterexample_awareness": "反例意识",
    "boundary_awareness": "边界感",
    "causal_rigor": "因果严谨度",
    "expression_maturity": "表达成熟度",
}

ABSOLUTE_TERMS = ("必须", "永远", "所有", "一定", "完全", "绝对")


def _answer_texts(debate_turns: list[dict[str, Any]]) -> list[str]:
    return [str(turn.get("user_answer", "")).strip() for turn in debate_turns]


def _score_dimension(
    evaluation_text: str,
    keywords: tuple[str, ...],
    repeated_claim_count: int,
    extra_information_bonus: int = 0,
) -> int:
    matched = sum(1 for keyword in keywords if keyword in evaluation_text)
    absolute_count = sum(evaluation_text.count(term) for term in ABSOLUTE_TERMS)

    score = 3
    score += min(matched, 4)
    score += 1 if len(evaluation_text) >= 18 else 0
    score += extra_information_bonus
    score -= 2 if len(evaluation_text) < 8 else 0
    score -= min(absolute_count, 2)
    score -= min(repeated_claim_count * 2, 4)
    return max(0, min(score, 9))


def _final_rewrite(claim: str, analysis: dict, answers: list[str]) -> str:
    existing = str(analysis.get("rigorous_expression", "")).strip()
    if existing:
        return existing

    boundary_answer = answers[1] if len(answers) > 1 else ""
    causal_answer = answers[3] if len(answers) > 3 else ""
    boundary = boundary_answer[:70] if boundary_answer else "适用对象和条件明确"
    causal = causal_answer[:70] if causal_answer else "有足够证据支持"
    return (
        f"更准确地说，在“{boundary}”所限定的部分情境下，"
        f"并且“{causal}”时，观点“{claim}”可能成立，"
        "但不能绝对化，也需要保留反例和实践副作用的空间。"
    )


def score_answers_rule_based(
    claim: str,
    analysis: dict,
    debate_turns: list,
) -> dict:
    """Score five completed debate answers using transparent text rules."""
    normalized_claim = claim.strip()
    answers = _answer_texts(debate_turns)
    if not normalized_claim:
        raise ValueError("观点不能为空。")
    if len(answers) != 5 or any(not answer for answer in answers):
        raise ValueError("必须完成 5 轮有效回答后才能生成评分。")

    all_text = "\n".join(answers)
    normalized_claim_text = normalized_claim.rstrip("。！？!? ")
    repeated_claim_count = sum(
        1
        for answer in answers
        if answer.rstrip("。！？!? ") == normalized_claim_text
    )

    evaluation_texts = {
        "concept_clarity": answers[0],
        "argument_completeness": all_text,
        "counterexample_awareness": f"{answers[1]}\n{answers[2]}",
        "boundary_awareness": answers[1],
        "causal_rigor": answers[3],
        "expression_maturity": answers[4],
    }
    scores = {
        dimension: _score_dimension(
            evaluation_texts[dimension],
            keywords,
            repeated_claim_count,
            extra_information_bonus=(
                1
                if dimension == "argument_completeness"
                and sum(len(answer) >= 18 for answer in answers) >= 3
                else 0
            ),
        )
        for dimension, keywords in SCORE_RULES.items()
    }
    weakest = min(scores, key=scores.get)
    strongest = max(reversed(scores), key=scores.get)

    advice = {
        "concept_clarity": "下次先用一句可检验的话定义核心词，再开始论证。",
        "argument_completeness": "下次至少补充一个理由和一个具体例子，避免只给结论。",
        "counterexample_awareness": "下次主动提出一个最强反例，并说明观点如何收窄。",
        "boundary_awareness": "下次明确写出适用对象、条件和不成立的情境。",
        "causal_rigor": "下次区分相关与因果，并说明可能的机制和其他影响因素。",
        "expression_maturity": "下次减少绝对化词语，多使用“可能”“在特定条件下”等限定。",
    }

    return {
        "scores": scores,
        "total_score": sum(scores.values()),
        "main_problem": (
            f"当前最需要改进的是{SCORE_LABELS[weakest]}。"
            f"这一项得到 {scores[weakest]}/10，说明相关回答还缺少明确证据或限定。"
        ),
        "strongest_part": (
            f"最值得保留的是{SCORE_LABELS[strongest]}。"
            f"这一项得到 {scores[strongest]}/10，相关表达已经提供了较好的论证基础。"
        ),
        "next_training_advice": advice[weakest],
        "final_rewrite": _final_rewrite(normalized_claim, analysis, answers),
    }

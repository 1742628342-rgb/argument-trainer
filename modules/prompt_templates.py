from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = (
    "你是理性、直接、克制的中文逻辑训练助手。"
    "不鸡汤，不攻击用户，不羞辱，只输出请求的 JSON。"
)

SCORE_KEYS = (
    "concept_clarity",
    "argument_completeness",
    "counterexample_awareness",
    "boundary_awareness",
    "causal_rigor",
    "expression_maturity",
)


def build_analysis_prompts(claim: str, strength: str) -> tuple[str, str]:
    user_prompt = f"""
分析以下观点，反方强度为“{strength}”：
{claim}

返回 JSON：
{{
  "supporting_reasons": [
    {{"reason": "...", "condition": "...", "example": "..."}}
  ],
  "opposing_reasons": [
    {{"reason": "...", "weakness": "...", "example": "..."}}
  ],
  "valid_conditions": ["..."],
  "concept_switch_risks": [
    {{"risk": "...", "why": "...", "better_boundary": "..."}}
  ],
  "rigorous_rewrite": "..."
}}
只分析这个观点，结论保守，明确条件和边界。
""".strip()
    return SYSTEM_PROMPT, user_prompt


def build_debate_prompts(
    claim: str,
    previous_turns: list,
    turn_number: int,
    strength: str,
) -> tuple[str, str]:
    user_prompt = f"""
围绕原观点生成第 {turn_number} 轮反方追问。
原观点：{claim}
反方强度：{strength}
此前问答：{json.dumps(previous_turns, ensure_ascii=False)}

返回 JSON：
{{
  "question": "...",
  "question_type": "...",
  "why_ask": "..."
}}
每轮只问一个问题。结合上一轮回答，不攻击用户。
""".strip()
    return SYSTEM_PROMPT, user_prompt


def build_scoring_prompts(
    claim: str,
    analysis: dict,
    debate_turns: list,
) -> tuple[str, str]:
    user_prompt = f"""
根据原观点、初始分析和 5 轮回答进行逻辑评分。
原观点：{claim}
初始分析：{json.dumps(analysis, ensure_ascii=False)}
五轮问答：{json.dumps(debate_turns, ensure_ascii=False)}

每项 0-10 分，不要轻易满分。返回 JSON：
{{
  "scores": {{
    "concept_clarity": 0,
    "argument_completeness": 0,
    "counterexample_awareness": 0,
    "boundary_awareness": 0,
    "causal_rigor": 0,
    "expression_maturity": 0
  }},
  "total_score": 0,
  "main_problem": "...",
  "strongest_part": "...",
  "next_training_advice": "...",
  "final_rewrite": "..."
}}
""".strip()
    return SYSTEM_PROMPT, user_prompt


def _text_or_fallback(value: Any, fallback: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def _list_or_fallback(value: Any, fallback: list) -> list:
    if not isinstance(value, list):
        return fallback
    cleaned = [
        item
        for item in value
        if (isinstance(item, str) and item.strip())
        or (isinstance(item, dict) and item)
    ]
    return cleaned or fallback


def merge_analysis_with_rule_fallback(
    llm_result: dict | None,
    rule_result: dict,
) -> dict:
    llm_result = llm_result or {}
    return {
        "supporting_reasons": _list_or_fallback(
            llm_result.get("supporting_reasons"),
            rule_result["supporting_reasons"],
        ),
        "opposing_reasons": _list_or_fallback(
            llm_result.get("opposing_reasons"),
            rule_result["opposing_reasons"],
        ),
        "conditions": _list_or_fallback(
            llm_result.get("valid_conditions"),
            rule_result["conditions"],
        ),
        "concept_shift_risks": _list_or_fallback(
            llm_result.get("concept_switch_risks"),
            rule_result["concept_shift_risks"],
        ),
        "rigorous_expression": _text_or_fallback(
            llm_result.get("rigorous_rewrite"),
            rule_result["rigorous_expression"],
        ),
        "detected_features": rule_result.get("detected_features", {}),
    }


def merge_question_with_rule_fallback(
    llm_result: dict | None,
    rule_result: dict,
) -> dict:
    llm_result = llm_result or {}
    return {
        key: _text_or_fallback(llm_result.get(key), rule_result[key])
        for key in ("question", "question_type", "why_ask")
    }


def merge_score_with_rule_fallback(
    llm_result: dict | None,
    rule_result: dict,
) -> dict:
    llm_result = llm_result or {}
    llm_scores = llm_result.get("scores")
    if not isinstance(llm_scores, dict):
        llm_scores = {}

    scores = {}
    for key in SCORE_KEYS:
        value = llm_scores.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            scores[key] = max(0, min(10, int(round(value))))
        else:
            scores[key] = rule_result["scores"][key]

    return {
        "scores": scores,
        "total_score": sum(scores.values()),
        "main_problem": _text_or_fallback(
            llm_result.get("main_problem"),
            rule_result["main_problem"],
        ),
        "strongest_part": _text_or_fallback(
            llm_result.get("strongest_part"),
            rule_result["strongest_part"],
        ),
        "next_training_advice": _text_or_fallback(
            llm_result.get("next_training_advice"),
            rule_result["next_training_advice"],
        ),
        "final_rewrite": _text_or_fallback(
            llm_result.get("final_rewrite"),
            rule_result["final_rewrite"],
        ),
    }

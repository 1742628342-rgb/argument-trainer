from __future__ import annotations

from collections.abc import Iterable


ABSOLUTE_TERMS = ("必须", "只能", "一定", "永远", "从来", "完全", "所有", "没有任何")
VAGUE_TERMS = ("独立", "成熟", "优秀", "可靠", "强大", "稳定", "有价值", "好", "差", "成功", "失败")
CAUSAL_TERMS = ("因为", "所以", "导致", "决定", "只要", "就会")
VALUE_TERMS = ("应该", "不应该", "正常", "失败", "没用", "低级", "高级")
VALID_STRENGTHS = ("温和", "正常", "尖锐但不攻击")

DEBATE_QUESTION_TYPES = {
    1: "定义追问",
    2: "边界追问",
    3: "反例追问",
    4: "因果追问",
    5: "实践副作用追问",
}

CONCEPT_SHIFT_PATTERNS = (
    (("情绪独立", "不需要别人"), "把“情绪独立”偷换成“不需要别人”"),
    (("多元来源", "真正强大"), "把“多元来源”偷换成“真正强大”"),
    (("短期舒服", "长期正确"), "把“短期舒服”偷换成“长期正确”"),
    (("个人选择", "普遍规律"), "把“个人选择”偷换成“普遍规律”"),
)


def _find_terms(claim: str, terms: Iterable[str]) -> list[str]:
    return [term for term in terms if term in claim]


def _supporting_reasons(claim: str, vague_terms: list[str]) -> list[str]:
    reasons = [
        "这个观点可能抓住了某些常见经验，作为提醒或行动原则有一定价值。",
        "如果相关概念有明确标准，并且适用对象相近，这个判断可能具有解释力。",
    ]
    if vague_terms:
        reasons.append(
            f"其中“{'、'.join(vague_terms)}”可能对应真实需求，但需要先说明具体含义。"
        )
    else:
        reasons.append("若有可核验的案例或数据支持，这个判断会更有说服力。")
    return reasons


def _opposing_reasons(
    absolute_terms: list[str],
    causal_terms: list[str],
    strength: str,
) -> list[str]:
    tone_openers = {
        "温和": "也可以温和地补充：",
        "正常": "需要指出的是：",
        "尖锐但不攻击": "可以直接反问这个判断：",
    }
    reasons = [
        f"{tone_openers[strength]}不同个体、情境和时间尺度可能产生不同结果。",
        "这个判断还缺少反例检验，单个经验更像是线索，而不是普遍结论。",
    ]
    if absolute_terms:
        reasons.append(
            f"“{'、'.join(absolute_terms)}”把结论说得过满；只要存在合理反例，原表述就需要收窄。"
        )
    if causal_terms:
        reasons.append(
            f"“{'、'.join(causal_terms)}”暗示了因果链条，但目前还没有排除其他影响因素。"
        )
    if not absolute_terms and not causal_terms:
        reasons.append("还需要说明比较对象、判断标准和证据范围，否则结论可能无法检验。")
    return reasons


def _conditions(
    absolute_terms: list[str],
    vague_terms: list[str],
    causal_terms: list[str],
) -> list[str]:
    conditions = [
        "适用对象、场景和时间范围需要进一步限定。",
        "关键概念应采用同一套可观察或可讨论的标准。",
        "结论需要有足够且具有代表性的事实、案例或数据支持。",
    ]
    if absolute_terms:
        conditions.append("需要说明是否允许例外，以及例外出现时结论如何调整。")
    if vague_terms:
        conditions.append(f"需要先界定“{'、'.join(vague_terms)}”分别指什么。")
    if causal_terms:
        conditions.append("需要排除共同原因、反向因果和偶然相关等可能性。")
    return conditions


def _concept_shift_risks(claim: str, vague_terms: list[str], causal_terms: list[str]) -> list[str]:
    risks = [
        description
        for required_terms, description in CONCEPT_SHIFT_PATTERNS
        if all(term in claim for term in required_terms)
    ]
    if ("相关" in claim and any(term in claim for term in ("导致", "决定", "所以"))) or (
        causal_terms and "数据" in claim
    ):
        risks.append("可能把“相关关系”偷换成“因果关系”")
    if any(term in claim for term in ("我", "个人", "身边")) and any(
        term in claim for term in ("所有", "都", "普遍", "大家")
    ):
        risks.append("可能把“个人选择”或个体经验扩大成“普遍规律”")
    if vague_terms:
        risks.append(
            f"“{'、'.join(vague_terms)}”可能在论证前后使用了不同标准，需要进一步限定。"
        )
    if not risks:
        risks.append("暂未发现明显的固定偷换模式，但仍需检查关键词在前后文中的含义是否一致。")
    return list(dict.fromkeys(risks))


def _rigorous_expression(
    claim: str,
    absolute_terms: list[str],
    vague_terms: list[str],
    causal_terms: list[str],
) -> str:
    limitations = ["在明确适用对象、场景和时间范围后"]
    if vague_terms:
        limitations.append(f"并具体界定“{'、'.join(vague_terms)}”")
    if causal_terms:
        limitations.append("且有证据支持相关机制")
    if absolute_terms:
        limitations.append("同时允许合理例外")

    return (
        f"{'，'.join(limitations)}，可以更谨慎地表达为："
        f"“{claim}”可能在部分情境下成立，但这个判断还缺少条件，"
        "需要进一步限定，不能直接推广为普遍规律。"
    )


def analyze_claim_rule_based(claim: str, strength: str) -> dict:
    """Analyze a claim using transparent keyword and template rules."""
    normalized_claim = claim.strip()
    if not normalized_claim:
        raise ValueError("观点不能为空。")
    if strength not in VALID_STRENGTHS:
        raise ValueError(f"反方强度必须是：{'、'.join(VALID_STRENGTHS)}。")

    absolute_terms = _find_terms(normalized_claim, ABSOLUTE_TERMS)
    vague_terms = _find_terms(normalized_claim, VAGUE_TERMS)
    causal_terms = _find_terms(normalized_claim, CAUSAL_TERMS)
    value_terms = _find_terms(normalized_claim, VALUE_TERMS)

    return {
        "supporting_reasons": _supporting_reasons(normalized_claim, vague_terms),
        "opposing_reasons": _opposing_reasons(absolute_terms, causal_terms, strength),
        "conditions": _conditions(absolute_terms, vague_terms, causal_terms),
        "concept_shift_risks": _concept_shift_risks(
            normalized_claim,
            vague_terms,
            causal_terms,
        ),
        "rigorous_expression": _rigorous_expression(
            normalized_claim,
            absolute_terms,
            vague_terms,
            causal_terms,
        ),
        "detected_features": {
            "absolute_terms": absolute_terms,
            "vague_terms": vague_terms,
            "causal_terms": causal_terms,
            "value_terms": value_terms,
        },
    }


def _previous_answer_context(previous_turns: list) -> str:
    if not previous_turns:
        return ""
    answer = str(previous_turns[-1].get("user_answer", "")).strip()
    answer = " ".join(answer.split()).replace("？", "").replace("?", "")
    if not answer:
        return ""
    return answer[:60]


def _core_term_for_question(claim: str) -> str:
    detected = _find_terms(claim, VAGUE_TERMS)
    if detected:
        return detected[0]
    return "核心判断"


def generate_opponent_question_rule_based(
    claim: str,
    previous_turns: list,
    turn_number: int,
    strength: str,
) -> dict:
    """Generate one of five deterministic, non-attacking follow-up questions."""
    normalized_claim = claim.strip()
    if not normalized_claim:
        raise ValueError("观点不能为空。")
    if strength not in VALID_STRENGTHS:
        raise ValueError(f"反方强度必须是：{'、'.join(VALID_STRENGTHS)}。")
    if turn_number not in DEBATE_QUESTION_TYPES:
        raise ValueError("追问轮次必须在 1 到 5 之间。")

    tone = {
        "温和": "请进一步说明",
        "正常": "请明确回答",
        "尖锐但不攻击": "请直接回答",
    }[strength]
    previous_answer = _previous_answer_context(previous_turns)
    continuation = (
        f"你上一轮提到“{previous_answer}”。" if previous_answer else ""
    )
    claim_reference = f"观点“{normalized_claim}”"

    question_details = {
        1: (
            f"{tone}：对于{claim_reference}，你所说的"
            f"“{_core_term_for_question(normalized_claim)}”到底是什么意思？",
            "先统一核心词的含义，避免双方使用不同定义讨论同一个观点。",
        ),
        2: (
            f"{continuation}{tone}：{claim_reference}在什么情况下不成立？",
            "明确观点的适用边界，能避免把局部经验扩大成普遍规律。",
        ),
        3: (
            f"{continuation}{tone}：有没有一个具体反例能够削弱{claim_reference}？",
            "主动寻找反例，可以检验观点是否说得过满。",
        ),
        4: (
            f"{continuation}{tone}：{claim_reference}说的是因果关系，还是只是相关关系？",
            "区分因果与相关，能检查论证中是否缺少关键机制或证据。",
        ),
        5: (
            f"{continuation}{tone}：如果按{claim_reference}行动，可能会带来什么副作用？",
            "检验观点落地后的代价，避免只看到预期收益而忽略实践风险。",
        ),
    }
    question, why_ask = question_details[turn_number]

    return {
        "question": question,
        "question_type": DEBATE_QUESTION_TYPES[turn_number],
        "why_ask": why_ask,
    }

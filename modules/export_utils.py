from __future__ import annotations

from typing import Any


SCORE_LABELS = {
    "concept_clarity": "概念清晰度",
    "argument_completeness": "论证完整度",
    "counterexample_awareness": "反例意识",
    "boundary_awareness": "边界感",
    "causal_rigor": "因果严谨度",
    "expression_maturity": "表达成熟度",
}

ANALYSIS_FIELD_LABELS = {
    "reason": "理由",
    "condition": "适用前提",
    "example": "例子",
    "weakness": "可能漏洞",
    "risk": "风险",
    "why": "为什么",
    "better_boundary": "更好的边界",
}


def _bullet_list(items: list[Any] | None) -> str:
    if not items:
        return "- 暂无。"

    lines = []
    for item in items:
        if isinstance(item, dict):
            values = [
                f"{ANALYSIS_FIELD_LABELS.get(key, key)}：{str(value).strip()}"
                for key, value in item.items()
                if str(value).strip()
            ]
            lines.append(f"- {'；'.join(values)}" if values else "- 暂无。")
        else:
            lines.append(f"- {item}")
    return "\n".join(lines)


def analysis_to_markdown(
    claim: str,
    strength: str,
    analysis: dict[str, Any],
) -> str:
    """Format only the initial analysis for the new-training page."""
    return "\n\n".join(
        (
            "# 观点反驳训练结果",
            f"**原始观点：** {claim}",
            f"**反方强度：** {strength}",
            f"## 支持理由\n{_bullet_list(analysis.get('supporting_reasons'))}",
            f"## 反对理由\n{_bullet_list(analysis.get('opposing_reasons'))}",
            f"## 成立条件\n{_bullet_list(analysis.get('conditions'))}",
            f"## 偷换概念风险\n{_bullet_list(analysis.get('concept_shift_risks'))}",
            f"## 更严谨表达\n{analysis.get('rigorous_expression', '暂无。')}",
        )
    )


def _turns_markdown(debate_turns: list[dict[str, Any]] | None) -> str:
    if not debate_turns:
        return "暂无追问记录。"

    sections = []
    for turn in debate_turns:
        turn_number = turn.get("turn_number", "未知")
        sections.append(
            "\n\n".join(
                (
                    f"### 第 {turn_number} 轮",
                    f"**问题类型：** {turn.get('question_type') or '暂无'}",
                    f"**反方问题：** {turn.get('opponent_question') or '暂无'}",
                    f"**为什么问这个：** {turn.get('why_ask') or '暂无'}",
                    f"**我的回答：** {turn.get('user_answer') or '暂无'}",
                )
            )
        )
    return "\n\n".join(sections)


def _score_markdown(score: dict[str, Any] | None) -> str:
    if not score:
        return "暂无评分。"

    scores = score.get("scores", {})
    lines = [
        f"- {label}：{scores.get(key, '暂无')}/10"
        for key, label in SCORE_LABELS.items()
    ]
    lines.append(f"- 总分：{score.get('total_score', '暂无')}/60")
    return "\n".join(lines)


def export_training_to_markdown(
    session: dict,
    analysis: dict,
    debate_turns: list,
    score: dict | None,
) -> str:
    """Export a full training record as UTF-8-compatible Markdown text."""
    session = session or {}
    analysis = analysis or {}
    debate_turns = debate_turns or []
    score = score or {}

    initial_rewrite = analysis.get("rigorous_expression") or "暂无。"
    final_rewrite = (
        score.get("final_rewrite")
        or session.get("final_rewrite")
        or initial_rewrite
    )

    return "\n\n".join(
        (
            "# 观点反驳训练记录",
            f"## 原观点\n\n{session.get('original_claim') or '暂无。'}",
            "## 初始分析",
            (
                "### 支持这个观点的理由\n\n"
                f"{_bullet_list(analysis.get('supporting_reasons'))}"
            ),
            (
                "### 反对这个观点的理由\n\n"
                f"{_bullet_list(analysis.get('opposing_reasons'))}"
            ),
            (
                "### 观点成立的条件\n\n"
                f"{_bullet_list(analysis.get('conditions'))}"
            ),
            (
                "### 容易偷换概念的地方\n\n"
                f"{_bullet_list(analysis.get('concept_shift_risks'))}"
            ),
            f"### 更严谨的表达方式\n\n{initial_rewrite}",
            f"## 5 轮反方追问\n\n{_turns_markdown(debate_turns)}",
            f"## 最终逻辑评分\n\n{_score_markdown(score or None)}",
            f"## 最大问题\n\n{score.get('main_problem') or '暂无。'}",
            (
                "## 最值得保留的优点\n\n"
                f"{score.get('strongest_part') or '暂无。'}"
            ),
            (
                "## 下一次训练建议\n\n"
                f"{score.get('next_training_advice') or '暂无。'}"
            ),
            f"## 最终严谨表达\n\n{final_rewrite}",
        )
    )

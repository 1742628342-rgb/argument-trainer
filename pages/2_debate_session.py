import sqlite3

import streamlit as st

from modules.database import (
    create_debate_turn,
    get_debate_turns,
    init_database,
    list_training_sessions,
    save_training_score,
)
from modules.llm_client import LLMUnavailableError, call_llm, parse_json_response
from modules.prompt_templates import (
    build_debate_prompts,
    build_scoring_prompts,
    merge_question_with_rule_fallback,
    merge_score_with_rule_fallback,
)
from modules.rule_engine import generate_opponent_question_rule_based
from modules.scoring import score_answers_rule_based


st.set_page_config(page_title="反方追问", page_icon="💬", layout="centered")
init_database()

SCORE_LABELS = {
    "concept_clarity": "概念清晰度",
    "argument_completeness": "论证完整度",
    "counterexample_awareness": "反例意识",
    "boundary_awareness": "边界感",
    "causal_rigor": "因果严谨度",
    "expression_maturity": "表达成熟度",
}
MODE_LABELS = {
    "rule": "规则分析",
    "gemini": "Gemini API",
    "openrouter": "OpenRouter API",
    "groq": "Groq API",
    "auto": "自动模式",
}


def render_item(item) -> None:
    if isinstance(item, dict):
        st.markdown(f"- {'；'.join(str(value) for value in item.values() if value)}")
    else:
        st.markdown(f"- {item}")


def render_analysis(analysis: dict) -> None:
    sections = (
        ("支持理由", "supporting_reasons"),
        ("反对理由", "opposing_reasons"),
        ("成立条件", "conditions"),
        ("偷换概念风险", "concept_shift_risks"),
    )
    for title, key in sections:
        st.markdown(f"**{title}**")
        for item in analysis.get(key, []):
            render_item(item)
    st.markdown("**更严谨表达**")
    st.write(analysis.get("rigorous_expression", "暂无"))


def render_score(score_result: dict) -> None:
    st.subheader("逻辑评分")
    score_items = list(score_result["scores"].items())
    for start in range(0, len(score_items), 3):
        columns = st.columns(3)
        for column, (key, value) in zip(columns, score_items[start : start + 3]):
            column.metric(SCORE_LABELS[key], f"{value}/10")
    st.metric("总分", f"{score_result['total_score']}/60")
    st.markdown("**最大问题**")
    st.write(score_result["main_problem"])
    st.markdown("**最值得保留的优点**")
    st.write(score_result["strongest_part"])
    st.markdown("**下一次训练建议**")
    st.write(score_result["next_training_advice"])
    st.markdown("**最终严谨表达**")
    st.success(score_result["final_rewrite"])


def generate_question(session: dict, turns: list, turn_number: int) -> tuple[dict, bool]:
    rule_question = generate_opponent_question_rule_based(
        session["original_claim"],
        turns,
        turn_number,
        session["opponent_strength"],
    )
    if session["analysis_mode"] == "rule":
        return rule_question, False

    try:
        system_prompt, user_prompt = build_debate_prompts(
            session["original_claim"],
            turns,
            turn_number,
            session["opponent_strength"],
        )
        raw_response = call_llm(
            session["analysis_mode"],
            system_prompt,
            user_prompt,
        )
        parsed = parse_json_response(raw_response)
        if parsed is None:
            parsed = {"question": raw_response.strip()}
        return merge_question_with_rule_fallback(parsed, rule_question), False
    except LLMUnavailableError:
        return rule_question, True


st.title("连续反方追问")
st.caption("API 不可用时会自动回退规则问题，并继续保存训练进度。")

sessions = list_training_sessions()
if not sessions:
    st.info("还没有训练记录。请先到“新训练”页面完成一次分析。")
    st.stop()

session_by_id = {session["id"]: session for session in sessions}
session_ids = list(session_by_id)
query_session_id = st.query_params.get("session_id")
try:
    query_session_id = int(query_session_id) if query_session_id else None
except ValueError:
    query_session_id = None

preferred_id = st.session_state.get("selected_debate_session_id", query_session_id)
if preferred_id not in session_by_id:
    preferred_id = session_ids[0]

selected_id = st.selectbox(
    "选择训练记录",
    session_ids,
    index=session_ids.index(preferred_id),
    format_func=lambda session_id: (
        f"#{session_id} · {session_by_id[session_id]['original_claim'][:42]}"
    ),
)
st.session_state["selected_debate_session_id"] = selected_id
st.query_params["session_id"] = str(selected_id)

session = session_by_id[selected_id]
st.subheader("原观点")
st.write(session["original_claim"])
st.caption(
    f"反方强度：{session['opponent_strength']} · "
    f"模式：{MODE_LABELS.get(session['analysis_mode'], session['analysis_mode'])}"
)

with st.expander("查看初始分析"):
    render_analysis(session["initial_analysis"])

turns = get_debate_turns(selected_id)
st.progress(len(turns) / 5, text=f"已完成 {len(turns)} / 5 轮")

if turns:
    with st.expander("查看已完成的追问"):
        for turn in turns:
            st.markdown(f"**第 {turn['turn_number']} 轮 · {turn['question_type']}**")
            st.write(turn["opponent_question"])
            st.caption(f"追问目的：{turn['why_ask']}")
            st.write(f"你的回答：{turn['user_answer']}")
            st.divider()

if len(turns) >= 5:
    st.success("已完成 5 轮反方追问，可以进入评分阶段。")
    if session["final_score"]:
        render_score(session["final_score"])
    elif st.button("生成逻辑评分", type="primary", use_container_width=True):
        rule_score = score_answers_rule_based(
            session["original_claim"],
            session["initial_analysis"],
            turns,
        )
        score_result = rule_score
        fallback_used = False
        if session["analysis_mode"] != "rule":
            try:
                system_prompt, user_prompt = build_scoring_prompts(
                    session["original_claim"],
                    session["initial_analysis"],
                    turns,
                )
                raw_response = call_llm(
                    session["analysis_mode"],
                    system_prompt,
                    user_prompt,
                )
                parsed = parse_json_response(raw_response)
                if parsed is None:
                    parsed = {"main_problem": raw_response.strip()}
                score_result = merge_score_with_rule_fallback(parsed, rule_score)
            except LLMUnavailableError:
                fallback_used = True
        save_training_score(selected_id, score_result)
        st.session_state[f"score_fallback_{selected_id}"] = fallback_used
        st.rerun()
    if st.session_state.get(f"score_fallback_{selected_id}"):
        st.warning("API 不可用，已回退到规则分析。")
    st.stop()

turn_number = len(turns) + 1
question_cache_key = f"question_{selected_id}_{turn_number}"
if question_cache_key not in st.session_state:
    question, fallback_used = generate_question(session, turns, turn_number)
    st.session_state[question_cache_key] = question
    st.session_state[f"{question_cache_key}_fallback"] = fallback_used
question = st.session_state[question_cache_key]

if st.session_state.get(f"{question_cache_key}_fallback"):
    st.warning("API 不可用，已回退到规则分析。")

st.subheader(f"第 {turn_number} 轮 · {question['question_type']}")
st.write(question["question"])
st.caption(f"为什么问：{question['why_ask']}")

with st.form(f"debate-turn-{selected_id}-{turn_number}", clear_on_submit=True):
    answer = st.text_area(
        "你的回答",
        height=130,
        placeholder="请尽量给出明确的定义、边界、例子或依据。",
    )
    button_label = "完成第 5 轮" if turn_number == 5 else "下一轮"
    submitted = st.form_submit_button(
        button_label,
        type="primary",
        use_container_width=True,
    )

if submitted:
    if not answer.strip():
        st.warning("请先输入回答。")
    else:
        try:
            create_debate_turn(
                session_id=selected_id,
                turn_number=turn_number,
                opponent_question=question["question"],
                question_type=question["question_type"],
                why_ask=question["why_ask"],
                user_answer=answer,
            )
            del st.session_state[question_cache_key]
            st.session_state.pop(f"{question_cache_key}_fallback", None)
            st.rerun()
        except (ValueError, sqlite3.IntegrityError) as exc:
            st.error(f"保存失败：{exc}")

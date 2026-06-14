import streamlit as st

from modules.database import (
    delete_training_session,
    get_debate_turns,
    init_database,
    list_training_sessions,
)
from modules.export_utils import export_training_to_markdown


st.set_page_config(page_title="历史记录", page_icon="🗂️", layout="centered")
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


FIELD_LABELS = {
    "reason": "理由",
    "condition": "适用前提",
    "example": "例子",
    "weakness": "可能漏洞",
    "risk": "风险",
    "why": "为什么",
    "better_boundary": "更好的边界",
}


def render_list(title: str, items: list) -> None:
    st.markdown(f"**{title}**")
    for item in items:
        if isinstance(item, dict):
            text = "；".join(
                f"{FIELD_LABELS.get(key, key)}：{value}"
                for key, value in item.items()
                if value
            )
            st.markdown(f"- {text or '暂无'}")
        else:
            st.markdown(f"- {item}")


def render_score(score_result: dict) -> None:
    st.markdown("### 逻辑评分")
    for key, value in score_result["scores"].items():
        st.write(f"**{SCORE_LABELS[key]}：** {value}/10")
    st.write(f"**总分：** {score_result['total_score']}/60")
    st.write(f"**最大问题：** {score_result['main_problem']}")
    st.write(f"**最值得保留的优点：** {score_result['strongest_part']}")
    st.write(f"**下一次训练建议：** {score_result['next_training_advice']}")
    st.markdown("**最终严谨表达**")
    st.success(score_result["final_rewrite"])


st.title("历史记录")
st.caption("查看完整训练、逻辑评分，并导出 UTF-8 Markdown 记录。")
sessions = list_training_sessions()

if not sessions:
    st.info("还没有训练记录。请先到“新训练”页面完成一次分析。")

for session in sessions:
    turns = get_debate_turns(session["id"])
    completion = "已评分" if session["is_completed"] else "未评分"
    label = (
        f"#{session['id']} · {session['original_claim'][:36]} · "
        f"追问 {len(turns)}/5 轮 · {completion} · {session['created_at']}"
    )
    with st.expander(label):
        st.write(f"**原始观点：** {session['original_claim']}")
        st.write(f"**反方强度：** {session['opponent_strength']}")
        st.write(
            f"**分析模式：** "
            f"{MODE_LABELS.get(session['analysis_mode'], session['analysis_mode'])}"
        )
        analysis = session["initial_analysis"]
        render_list("支持理由", analysis["supporting_reasons"])
        render_list("反对理由", analysis["opposing_reasons"])
        render_list("成立条件", analysis["conditions"])
        render_list("偷换概念风险", analysis["concept_shift_risks"])
        st.markdown("**初始严谨表达**")
        st.write(analysis["rigorous_expression"])

        st.markdown("### 反方追问记录")
        if not turns:
            st.caption("尚未开始反方追问。")
        for turn in turns:
            st.markdown(f"**第 {turn['turn_number']} 轮 · {turn['question_type']}**")
            st.write(f"问题：{turn['opponent_question']}")
            st.caption(f"追问目的：{turn['why_ask']}")
            st.write(f"回答：{turn['user_answer']}")

        if session["final_score"]:
            render_score(session["final_score"])
        elif len(turns) == 5:
            st.info("五轮追问已完成，尚未生成逻辑评分。")

        left, right = st.columns(2)
        with left:
            markdown = export_training_to_markdown(
                session,
                analysis,
                turns,
                session["final_score"],
            )
            created_date = str(session["created_at"])[:10]
            st.download_button(
                "导出 Markdown",
                markdown,
                file_name=(
                    f"argument_training_{created_date}_{session['id']}.md"
                ),
                mime="text/markdown; charset=utf-8",
                key=f"download-{session['id']}",
                use_container_width=True,
            )
        with right:
            if st.button(
                "删除记录",
                key=f"delete-{session['id']}",
                use_container_width=True,
            ):
                delete_training_session(session["id"])
                st.rerun()

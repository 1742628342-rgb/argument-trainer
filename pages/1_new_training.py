import streamlit as st

from modules.database import create_training_session, init_database
from modules.export_utils import analysis_to_markdown
from modules.llm_client import (
    LLMUnavailableError,
    call_llm,
    get_default_provider,
    parse_json_response,
)
from modules.prompt_templates import (
    build_analysis_prompts,
    merge_analysis_with_rule_fallback,
)
from modules.rule_engine import analyze_claim_rule_based


st.set_page_config(page_title="新训练", page_icon="🧠", layout="centered")
init_database()

MODE_OPTIONS = {
    "规则分析": "rule",
    "Gemini API": "gemini",
    "OpenRouter API": "openrouter",
    "Groq API": "groq",
    "自动模式": "auto",
}
PROVIDER_TO_LABEL = {value: key for key, value in MODE_OPTIONS.items()}


def render_item(item) -> None:
    if not isinstance(item, dict):
        st.markdown(f"- {item}")
        return
    values = [str(value) for value in item.values() if value]
    st.markdown(f"- {'；'.join(values)}")


def render_list(title: str, items: list) -> None:
    st.subheader(title)
    for item in items:
        render_item(item)


st.title("新训练")
st.caption("API 是可选增强；未配置或调用失败时会自动使用规则分析。")

claim = st.text_area(
    "观点",
    height=140,
    placeholder="例如：只要情绪独立，就一定不需要别人。",
)
strength = st.radio(
    "反方强度",
    ("温和", "正常", "尖锐但不攻击"),
    index=1,
    horizontal=True,
)
default_mode = get_default_provider()
default_label = PROVIDER_TO_LABEL.get(default_mode, "自动模式")
mode_labels = list(MODE_OPTIONS)
mode_label = st.selectbox(
    "分析模式",
    mode_labels,
    index=mode_labels.index(default_label),
)
analysis_mode = MODE_OPTIONS[mode_label]

if st.button("开始分析", type="primary", use_container_width=True):
    if not claim.strip():
        st.warning("请先输入一个观点。")
    else:
        try:
            rule_analysis = analyze_claim_rule_based(claim, strength)
            analysis = rule_analysis
            fallback_used = False
            if analysis_mode != "rule":
                try:
                    system_prompt, user_prompt = build_analysis_prompts(
                        claim,
                        strength,
                    )
                    raw_response = call_llm(
                        analysis_mode,
                        system_prompt,
                        user_prompt,
                    )
                    parsed = parse_json_response(raw_response)
                    if parsed is None:
                        parsed = {"rigorous_rewrite": raw_response.strip()}
                    analysis = merge_analysis_with_rule_fallback(
                        parsed,
                        rule_analysis,
                    )
                except LLMUnavailableError:
                    fallback_used = True

            session_id = create_training_session(
                claim,
                strength,
                analysis,
                analysis_mode=analysis_mode,
            )
            st.session_state["latest_analysis"] = analysis
            st.session_state["latest_claim"] = claim.strip()
            st.session_state["latest_strength"] = strength
            st.session_state["latest_session_id"] = session_id
            st.session_state["selected_debate_session_id"] = session_id
            st.session_state["latest_analysis_mode"] = analysis_mode
            st.session_state["latest_api_fallback"] = fallback_used
        except (ValueError, OSError) as exc:
            st.error(f"分析失败：{exc}")

analysis = st.session_state.get("latest_analysis")
if analysis:
    if st.session_state.get("latest_api_fallback"):
        st.warning("API 不可用，已回退到规则分析。")
    st.success(
        f"分析已完成并保存，记录编号："
        f"{st.session_state['latest_session_id']}"
    )
    st.divider()
    render_list("支持这个观点的理由", analysis["supporting_reasons"])
    render_list("反对这个观点的理由", analysis["opposing_reasons"])
    render_list("这个观点成立的条件", analysis["conditions"])
    render_list("容易偷换概念的地方", analysis["concept_shift_risks"])
    st.subheader("更严谨的表达方式")
    st.write(analysis["rigorous_expression"])

    detected = analysis["detected_features"]
    with st.expander("查看规则命中情况"):
        labels = {
            "absolute_terms": "绝对化词语",
            "vague_terms": "模糊概念",
            "causal_terms": "因果词",
            "value_terms": "价值判断词",
        }
        for key, label in labels.items():
            values = detected.get(key, [])
            st.write(f"**{label}：** {'、'.join(values) if values else '未命中'}")

    left, right = st.columns(2)
    with left:
        markdown = analysis_to_markdown(
            st.session_state["latest_claim"],
            st.session_state["latest_strength"],
            analysis,
        )
        st.download_button(
            "下载分析结果",
            markdown,
            file_name=f"argument-training-{st.session_state['latest_session_id']}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with right:
        if st.button("进入 5 轮反方追问", type="primary", use_container_width=True):
            st.switch_page("pages/2_debate_session.py")

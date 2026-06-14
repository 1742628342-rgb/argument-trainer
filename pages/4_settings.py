import streamlit as st

from modules.llm_client import (
    LLMUnavailableError,
    call_llm,
    get_default_provider,
    get_model_for_provider,
    get_provider_status,
)


st.set_page_config(page_title="API 设置", page_icon="⚙️", layout="centered")

PROVIDER_LABELS = {
    "gemini": "Gemini",
    "openrouter": "OpenRouter",
    "groq": "Groq",
}

st.title("API 设置")
st.caption(
    "密钥从本地 .env 或 Streamlit Secrets 读取，"
    "本页面不会显示完整 API Key。"
)
st.info("API 完全可选。未配置、额度不足或调用失败时，训练会继续使用规则模式。")

status = get_provider_status()
for provider, label in PROVIDER_LABELS.items():
    configured = "已配置" if status[provider] else "未配置"
    st.write(f"**{label} API Key：** {configured}")

default_provider = get_default_provider()
st.write(f"**当前默认 provider：** {default_provider}")

if default_provider == "auto":
    configured_order = [
        provider
        for provider in ("gemini", "openrouter", "groq")
        if status[provider]
    ]
    if configured_order:
        first_provider = configured_order[0]
        st.write(
            f"**当前默认模型：** "
            f"{get_model_for_provider(first_provider)}"
        )
    else:
        st.write("**当前默认模型：** 无（将使用规则模式）")
else:
    st.write(
        f"**当前默认模型：** {get_model_for_provider(default_provider)}"
    )

if st.button("测试 API 可用性", type="primary", use_container_width=True):
    configured_providers = [
        provider for provider, configured in status.items() if configured
    ]
    if not configured_providers:
        st.warning("未检测到 API Key，规则模式仍可正常使用。")
    for provider in configured_providers:
        try:
            response = call_llm(
                provider,
                "只做连通性测试。",
                "请只回复 OK。",
            )
            if response.strip():
                st.success(f"{PROVIDER_LABELS[provider]}：可用")
        except LLMUnavailableError:
            st.error(f"{PROVIDER_LABELS[provider]}：不可用")

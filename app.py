import streamlit as st

from modules.database import init_database


st.set_page_config(
    page_title="观点反驳训练器",
    page_icon="⚖️",
    layout="centered",
)
init_database()

st.title("观点反驳训练器")
st.caption("规则模式可直接使用 · API 为可选增强")

st.markdown(
    """
这个工具帮助你从支持、反对、成立条件、概念风险和严谨表达五个角度审视观点，
并通过连续 5 轮反方追问训练论证能力。

请从左侧页面导航进入：

- **新训练**：输入观点，选择规则模式或可选 API 模式
- **反方追问**：选择训练记录并完成 5 轮追问
- **历史记录**：查看、导出或删除完整训练记录
- **设置**：检查可选 API 配置并测试 provider
"""
)

st.info("不配置任何 API Key 也能完整训练；API 不可用时会自动回退规则模式。")

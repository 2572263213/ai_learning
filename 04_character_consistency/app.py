import streamlit as st
from check_ooc import build_character_db, check_ooc, generate_revised_text

st.set_page_config(page_title="同人文角色一致性检测", page_icon="📝")
st.title("📝 同人文角色一致性检测")


@st.cache_resource
def load_stores():
    return build_character_db()


stores = load_stores()

char_map = {
    "夜神月": "yagami_light",
    "陈俊南": "chen_junnan",
    "乔家劲": "qiao_jiajin"
}
selected_name = st.selectbox("选择角色", list(char_map.keys()))
character_id = char_map[selected_name]

user_text = st.text_area("粘贴你的同人文片段", height=200)

# ===== 检测按钮 =====
if st.button("🔍 检测OOC", type="primary"):
    if not user_text.strip():
        st.warning("请先粘贴文本")
    else:
        with st.spinner("正在检测..."):
            report = check_ooc(character_id, user_text, stores)
        # 把结果存进 session_state
        st.session_state["last_report"] = report
        st.session_state["last_text"] = user_text
        st.session_state["last_character_id"] = character_id
        # 清掉上一次的改写结果，避免混淆
        if "revised_text" in st.session_state:
            del st.session_state["revised_text"]

# ===== 显示检测结果（从 session_state 读取，与按钮点击无关）=====
if "last_report" in st.session_state:
    report = st.session_state["last_report"]

    # 评分
    score = report.consistency_score
    if score >= 80:
        st.success(f"一致性评分：{score}/100 ✅")
    elif score >= 50:
        st.warning(f"一致性评分：{score}/100 ⚠️")
    else:
        st.error(f"一致性评分：{score}/100 ❌")

    # 风险点
    if report.ooc_risks:
        st.subheader("OOC风险点")
        for risk in report.ooc_risks:
            st.warning(risk)

    # 修改建议（固定高度+滚动条）
    st.subheader("修改建议")
    st.text_area("修改建议", report.suggestion, height=120, label_visibility="collapsed")

    # ===== 生成修改文本按钮（独立于检测按钮）=====
    if st.button("✨ 生成修改后的文本"):
        with st.spinner("正在改写..."):
            revised = generate_revised_text(
                st.session_state["last_character_id"],
                st.session_state["last_text"],
                report,
                stores
            )
        st.session_state["revised_text"] = revised

# ===== 显示修改前后对比 =====
if "revised_text" in st.session_state:
    st.subheader("修改前后对比")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**原文**")
        st.text_area("原文", st.session_state["last_text"], height=200, label_visibility="collapsed")
        st.metric("原评分", f"{st.session_state['last_report'].consistency_score}/100")
    with col2:
        st.markdown("**修改后**")
        st.text_area("修改后", st.session_state["revised_text"], height=200, label_visibility="collapsed")
        new_report = check_ooc(
            st.session_state["last_character_id"],
            st.session_state["revised_text"],
            stores
        )
        st.metric(
            "新评分",
            f"{new_report.consistency_score}/100",
            delta=new_report.consistency_score - st.session_state["last_report"].consistency_score
        )

    # 一键复制修改后的文本
    st.subheader("一键复制")
    st.text_area("一键复制", st.session_state["revised_text"], height=120, label_visibility="collapsed")
import json
import streamlit as st
from check_ooc import build_character_db, check_ooc, generate_revised_text, parse_custom_character

st.set_page_config(page_title="同人文角色一致性检测", page_icon="📝")
st.title("📝 同人文角色一致性检测")

if "add_success" in st.session_state:
    st.success(st.session_state["add_success"])
    del st.session_state["add_success"]


@st.cache_resource
def load_stores():
    return build_character_db()


stores = load_stores()

with open("characters.json", "r", encoding="utf-8") as f:
    char_data = json.load(f)
char_map = {char["name"]: char["character_id"] for char in char_data["characters"]}
selected_name = st.selectbox("选择角色", list(char_map.keys()))
character_id = char_map[selected_name]

user_text = st.text_area("粘贴你的同人文片段", height=200, key="main_text_area")

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
    st.subheader("问题诊断与修改方向")
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
    st.subheader("参考改写版本与对比")
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

with st.expander("➕ 添加自定义角色"):
    new_char_text = st.text_area("粘贴角色描述", height=150, key="new_char_input")
    if st.button("解析角色"):
        if not new_char_text.strip():
            st.warning("请先粘贴角色描述")
        else:
            with st.spinner("正在解析..."):
                result = parse_custom_character(new_char_text)
            st.session_state["parsed_result"] = result

    # 只有解析过之后，才展示结果和确认按钮
    if "parsed_result" in st.session_state:
        result = st.session_state["parsed_result"]

        # 展示已提取字段（人类可读）
        st.subheader("已提取字段")
        parsed = result["parsed"]
        field_names = {
            "name": "角色名",
            "core_beliefs": "核心信念",
            "tone": "说话风格",
            "catchphrases": "口头禅"
        }
        for key, label in field_names.items():
            value = parsed.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                st.markdown(f"**{label}**：{'；'.join(value)}")
            else:
                st.markdown(f"**{label}**：{value}")

        # 收集缺失字段的用户选择
        user_choices = {}
        if result["missing_fields"]:
            st.subheader("需要补充的字段")
            for field in result["missing_fields"]:
                options = result["options"].get(field, [])
                choice = st.radio(f"请选择【{field}】：", options, key=f"missing_{field}")
                user_choices[field] = choice

        # 确认添加按钮
        if st.button("✅ 确认添加角色"):
            parsed["unbreakable"] = user_choices.get("绝对底线", "")
            parsed["flexible"] = user_choices.get("灵活空间", "")
            forbidden_value = user_choices.get("禁止表达", "")

            new_char = {
                "character_id": parsed["name"].lower().replace(" ", "_"),
                "name": parsed["name"],
                "core_beliefs": parsed["core_beliefs"],
                "user_defined_traits": {
                    "unbreakable": parsed["unbreakable"],
                    "flexible": parsed["flexible"]
                },
                "speech_style": {
                    "tone": parsed["tone"],
                    "catchphrases": parsed["catchphrases"],
                    "forbidden": [forbidden_value] if forbidden_value else []
                }
            }

            with open("characters.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                            # 检查是否已存在同名角色
            existing_names = [c["name"] for c in data["characters"]]
            if parsed["name"] in existing_names:
                st.warning(f"角色【{parsed['name']}】已存在，请勿重复添加。")
                st.stop()
            data["characters"].append(new_char)
            with open("characters.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            st.session_state["add_success"] = f"角色【{parsed['name']}】已添加！下拉菜单中已可选。"
            st.cache_resource.clear()
            st.rerun()
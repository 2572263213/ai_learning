# 学习日志：第三天（2026-10-10）

## 完成事项
- [x] 剧情上下文检测：四层判断（合规/剧情驱动/角色复杂性/真OOC）
- [x] 改写逻辑感知剧情上下文，保留偏离核心、只调整表达方式
- [x] 角色切换时清空主文本框、剧情上下文、旧检测报告
- [x] 自定义角色区内容保留（仅折叠）
- [x] 补全 requirements.txt（补上 rank-bm25）
- [x] 写项目 README

## 关键理解
- 同一段文本，加剧情后从"真OOC"变成"剧情驱动偏离"
- 四层判断的核心是区分"行为异常"和"内心崩坏"
- on_change 删 session_state 会失效，改用 input_version 动态 key 解决

## 踩的坑
- Streamlit 缓存旧模块，改完 check_ooc.py 必须重启
- on_change 回调删 key 后，Streamlit 会恢复旧值
- st.expander 重跑时默认折叠，是正常行为
- requirements.txt 缺了 rank-bm25，会导致线上部署失败

## 下一步
- 魔搭部署新版本
- 在 README 补上在线演示链接

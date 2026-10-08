# 学习日志：第1-2天

## 日期
2026-10-08 ~ 2026-10-09

## 完成事项
- [x] 安装 Python 3.11.9、VS Code、Git，配置开发环境
- [x] 跑通第一个 DeepSeek API 调用脚本
- [x] 学会用 .env + .gitignore 隔离敏感密钥
- [x] 理解并跑通 Pydantic 数据校验
- [x] 搭建第一个 RAG 应用（政策文档问答）
- [x] 完成同人文角色一致性检测核心逻辑
- [x] 为夜神月、陈俊南、乔家劲建立角色向量库
- [x] 完成 Streamlit 交互界面：检测OOC + 生成改写文本
- [x] 用 Git 推送到 GitHub

## 遇到的坑与解决
- 下载了 .tar.xz 而不是 .exe → 去官网重新下载 Windows installer
- langChain_community 大写 C → Python 严格区分大小写，改为全小写
- c10.dll 报错 → 安装 VC++ Redistributable 运行库
- git add . 少了空格 → 命令与参数之间必须空格
- Streamlit 按钮无反应 → 把按钮移出 if 块，用 session_state 保存状态

## 心得
- 报错不是失败，是学习最快的时候
- AI 是打字员，我才是架构师
- 先跑通再优化，不追求完美
- 从“用AI工具”到“造AI应用”的跨越开始了

## 下一步
- 部署 Streamlit 应用到 Streamlit Cloud
- 给同人文检测工具加历史记录和对比评分
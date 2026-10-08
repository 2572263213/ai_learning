import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from openai import OpenAI

load_dotenv()
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 初始化大模型客户端
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)
def build_character_db():
    """读取 characters.json，为每个角色建立独立的向量库"""
    with open("characters.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")

    # 为每个角色单独建一个向量库（实现"私人设定隔离"）
    character_stores = {}
    for char in data["characters"]:
        # 把角色的所有设定拼成一段文本
        char_text = f"""
        角色名：{char['name']}
        核心信念：{'；'.join(char['core_beliefs'])}
        绝对底线：{char['user_defined_traits']['unbreakable']}
        灵活空间：{char['user_defined_traits']['flexible']}
        说话风格：{char['speech_style']['tone']}
        口头禅：{'、'.join(char['speech_style']['catchphrases'])}
        禁止出现的表达：{'、'.join(char['speech_style']['forbidden'])}
        """
        store = Chroma.from_texts(
            texts=[char_text],
            embedding=embeddings,
            persist_directory=f"./character_db/{char['character_id']}"
        )
        character_stores[char['character_id']] = store
        print(f"已为 {char['name']} 建立专属向量库")

    return character_stores
class OOCReport(BaseModel):
    consistency_score: int = Field(description="角色一致性评分，0-100分", ge=0, le=100)
    ooc_risks: List[str] = Field(description="具体的OOC风险点列表，没有则返回空列表")
    suggestion: str = Field(description="修改建议")


def check_ooc(character_id: str, user_text: str, stores: dict) -> OOCReport:
    """检测一段文本中，指定角色是否OOC"""
    if character_id not in stores:
        raise ValueError(f"未找到角色：{character_id}")

    # 从该角色的专属向量库中检索设定
    retriever = stores[character_id].as_retriever(search_kwargs={"k": 1})
    docs = retriever.invoke(user_text)
    context = "\n\n".join([doc.page_content for doc in docs])

    prompt = f"""你是一个同人文角色一致性审查员。请严格根据以下角色设定，判断用户文本中角色的言行是否符合设定。

角色设定：
{context}

用户文本：
{user_text}

请以JSON格式输出，包含以下字段：
- consistency_score: 0-100的整数，表示角色一致性
- ooc_risks: 字符串列表，列出具体的OOC风险点，没有则空列表
- suggestion: 修改建议
只输出JSON，不要任何解释。"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    raw = response.choices[0].message.content.strip()

    # 清理可能出现的 markdown 代码块标记
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    data = json.loads(raw)
    return OOCReport(**data)  # Pydantic校验
if __name__ == "__main__":
    print("正在构建角色向量库...")
    stores = build_character_db()

    # 测试用例：故意写一段OOC的文本
    test_text = "夜神月看着镜子里的自己，突然流下眼泪，说：'也许我真的错了，我不该用死亡笔记。'"

    print("\n正在检测OOC...")
    report = check_ooc("yagami_light", test_text, stores)

    print("\n=== OOC检测报告 ===")
    print(f"一致性评分：{report.consistency_score}/100")
    print(f"风险点：")
    for risk in report.ooc_risks:
        print(f"  - {risk}")
    print(f"修改建议：{report.suggestion}")
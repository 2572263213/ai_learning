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

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


def build_character_db():
    """读取 characters.json，为每个角色建立独立的向量库和BM25索引"""
    from rank_bm25 import BM25Okapi

    with open("characters.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")

    character_stores = {}
    for char in data["characters"]:
        db_path = f"./character_db/{char['character_id']}"

        # 安全处理所有可能为 None 的字段
        core_beliefs = char.get('core_beliefs') or []
        if not isinstance(core_beliefs, list):
            core_beliefs = [core_beliefs]

        traits = char.get('user_defined_traits', {}) or {}
        speech = char.get('speech_style', {}) or {}

        unbreakable = traits.get('unbreakable') or "（未定义）"
        flexible = traits.get('flexible') or "（未定义）"
        tone = speech.get('tone') or "（未定义）"

        catchphrases = speech.get('catchphrases') or []
        if not isinstance(catchphrases, list):
            catchphrases = [catchphrases]

        forbidden = speech.get('forbidden') or []
        if not isinstance(forbidden, list):
            forbidden = [forbidden]

        segments = [
            {"text": f"核心信念：{'；'.join(core_beliefs)}", "source": "核心信念"},
            {"text": f"绝对底线：{unbreakable}", "source": "绝对底线"},
            {"text": f"灵活空间：{flexible}", "source": "灵活空间"},
            {"text": f"说话风格：{tone}", "source": "说话风格"},
            {"text": f"口头禅：{'、'.join(catchphrases)}", "source": "口头禅"},
            {"text": f"禁止表达：{'、'.join(forbidden)}", "source": "禁止表达"},
        ]

        # 建向量库
        text_list = [seg["text"] for seg in segments]
        if os.path.exists(db_path):
            store = Chroma(persist_directory=db_path, embedding_function=embeddings)
        else:
            store = Chroma.from_texts(texts=text_list, embedding=embeddings, persist_directory=db_path)

        # 建BM25索引
        tokenized = [list(seg["text"]) for seg in segments]
        bm25 = BM25Okapi(tokenized)

        character_stores[char['character_id']] = {
            "vectorstore": store,
            "bm25": bm25,
            "segments": segments
        }
        print(f"已加载 {char['name']} 的向量库和BM25索引")

    return character_stores


class OOCReport(BaseModel):
    consistency_score: int = Field(description="角色一致性评分，0-100分", ge=0, le=100)
    judgment_type: str = Field(description="判断类型：合规 / 剧情驱动 / 角色复杂性 / 真OOC")
    ooc_risks: List[str] = Field(description="具体的风险点列表，没有则空列表")
    suggestion: str = Field(description="修改方向建议")


def hybrid_retrieve(character_id: str, query: str, stores: dict, k: int = 3):
    
    """混合检索：向量 + BM25 + RRF融合"""
    store_dict = stores[character_id]
    vectorstore = store_dict["vectorstore"]
    bm25 = store_dict["bm25"]
    segments = store_dict["segments"]
    source_map = {seg["text"]: seg["source"] for seg in segments}
    # 1. 向量检索
    vector_results = vectorstore.similarity_search(query, k=k)
    vector_texts = [doc.page_content for doc in vector_results]

    # 2. BM25检索
    tokenized_query = list(query)
    bm25_scores = bm25.get_scores(tokenized_query)
    # 按分数从高到低排序，取前k个的索引
    bm25_top_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:k]
    bm25_texts = [segments[i]["text"] for i in bm25_top_indices]

    # 3. RRF融合
    rrf_scores = {}
    for rank, text in enumerate(vector_texts):
        rrf_scores[text] = rrf_scores.get(text, 0) + 1 / (60 + rank + 1)
    for rank, text in enumerate(bm25_texts):
        rrf_scores[text] = rrf_scores.get(text, 0) + 1 / (60 + rank + 1)

    # 按RRF得分排序，返回前k个
    sorted_texts = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:k]
    return [{"text": text, "source": source_map[text]} for text, score in sorted_texts]

def check_ooc(character_id: str, user_text: str, stores: dict, plot_context: str = "") -> OOCReport:
    """检测一段文本中，指定角色是否OOC"""
    if character_id not in stores:
        raise ValueError(f"未找到角色：{character_id}")

    contexts = hybrid_retrieve(character_id, user_text, stores, k=3)
    context = "\n\n".join([f"[{c['source']}] {c['text']}" for c in contexts])

    prompt = f"""你是一个同人文角色一致性审查员。请严格根据以下角色设定，判断用户文本中角色的言行是否符合设定。

角色设定：
{context}

用户文本：
{user_text}

剧情上下文：
{plot_context if plot_context else "（用户未提供剧情上下文）"}

请按以下顺序判断：
1. 角色言行是否符合设定？如果是，judgment_type 填「合规」。
2. 如果不符合，是否可以用剧情上下文解释？能解释则填「剧情驱动」。
3. 如果不符合且无法用剧情解释，是否属于表面/内里的差异（如策略性伪装、内心戏）？是则填「角色复杂性」。
4. 以上都不符合，则填「真OOC」，并指出违反了哪条底线。

如果用户没有提供剧情上下文，跳过第2步。

请以JSON格式输出，包含以下字段：
- consistency_score: 0-100的整数，表示角色一致性
- judgment_type: 字符串，只能是「合规」「剧情驱动」「角色复杂性」「真OOC」之一
- ooc_risks: 字符串列表，列出具体的OOC风险点，没有则空列表
- suggestion: 修改方向建议，用1-2句话说明应该往哪个方向改，不要给出完整的改写文本
只输出JSON，不要任何解释。"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=500
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    data = json.loads(raw)
    return OOCReport(**data)


def generate_revised_text(character_id: str, original_text: str, report: OOCReport, stores: dict, plot_context: str = "") -> str:
    """基于OOC报告，生成修改后的文本"""
    if character_id not in stores:
        raise ValueError(f"未找到角色：{character_id}")

    contexts = hybrid_retrieve(character_id, original_text, stores, k=3)
    context = "\n\n".join([f"[{c['source']}] {c['text']}" for c in contexts])

    prompt = f"""你是一个同人文写作助手。请根据以下角色设定和修改方向，改写用户的原文，使其符合角色设定，同时保留作者原有的创作意图。

角色设定：
{context}

原文：
{original_text}

OOC风险点：
{chr(10).join(report.ooc_risks)}

修改方向：
{report.suggestion}

剧情上下文：
{plot_context if plot_context else "（用户未提供剧情上下文）"}

要求：
- 保留作者原有的场景和叙事意图
- 按照修改方向调整角色的言行
- 直接给出改写后的完整文本，不要任何解释。"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=800
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    print("正在构建角色向量库...")
    stores = build_character_db()

    test_text = "夜神月看着镜子里的自己，突然流下眼泪，说：'也许我真的错了，我不该用死亡笔记。'"
    report = check_ooc("yagami_light", test_text, stores)
    print("原评分:", report.consistency_score)
    print("风险点:", report.ooc_risks)
    print("修改方向:", report.suggestion)

    revised = generate_revised_text("yagami_light", test_text, report, stores)
    print("修改后:", revised)

def parse_custom_character(user_text: str) -> dict:
        """解析用户输入的自由文本，输出结构化角色档案 + 缺失字段候选选项"""

        prompt = f"""你是一个角色档案解析器。用户会给你一段关于某个角色的自由描述。请你完成两件事：

    1. 从描述中提取以下字段（能提取的填上，提取不到的填 null）：
    - name: 角色名
    - core_beliefs: 核心信念，字符串列表
    - unbreakable: 绝对底线，字符串
    - flexible: 灵活空间，字符串
    - tone: 说话风格，字符串
    - catchphrases: 口头禅，字符串列表
    - forbidden: 禁止表达，字符串

    2. 对于提取不到的字段，根据已有信息，生成3-4个候选选项供用户选择。

    请以JSON格式输出，结构如下：
    {{
    "parsed": {{ ...已提取的字段... }},
    "missing_fields": ["绝对底线", "灵活空间"],
    "options": {{
        "绝对底线": ["选项1", "选项2", "选项3"],
        "灵活空间": ["选项1", "选项2", "选项3"]
    }}
    }}

    用户输入：
    {user_text}

    只输出JSON，不要任何解释。"""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=800
        )

        raw = response.choices[0].message.content.strip()

        # 去掉可能的 markdown 代码块标记
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        data = json.loads(raw)

        return data
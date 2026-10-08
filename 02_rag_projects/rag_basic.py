import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from openai import OpenAI

# 加载 .env 中的密钥
load_dotenv()
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com" 

# 1. 纯 Python 原生读取文件（彻底告别 TextLoader 报错）
print("正在读取文档...")
with open("policy.txt", "r", encoding="utf-8") as f:
    raw_text = f.read()

# 2. 文本切块
text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
chunks = text_splitter.split_text(raw_text)
print(f"成功把文档切成了 {len(chunks)} 块")

# 3. 向量化并存入 Chroma
print("正在加载向量模型（第一次运行需下载约100MB模型，请耐心等待）...")
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")
vectorstore = Chroma.from_texts(texts=chunks, embedding=embeddings, persist_directory="./chroma_db")
print("向量数据库构建完成！")

# 4. 检索 + 调用大模型
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
query = "深圳二手房契税怎么算？"
matched_docs = retriever.invoke(query)
context_text = "\n\n".join([doc.page_content for doc in matched_docs])

client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
prompt = f"请严格根据以下参考资料回答问题，不要自己编造。\n\n参考资料：\n{context_text}\n\n问题：{query}"

print("\n正在呼叫 DeepSeek 生成回答...")
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": prompt}]
)

print("\n=== AI 回答 ===")
print(response.choices[0].message.content)
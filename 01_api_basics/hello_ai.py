import os
from dotenv import load_dotenv
from openai import OpenAI

# 1. 自动加载 .env 文件里的密钥
load_dotenv() 

# 2. 从环境变量里读取 API Key，不再硬编码
api_key = os.getenv("DEEPSEEK_API_KEY")

# 3. 增加一个检查，如果没读到密钥，直接报错提醒
if not api_key:
    raise ValueError("没有找到 API Key，请检查 .env 文件是否配置正确！")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一个资深的房产中介。"},
        {"role": "user", "content": "请写一套二手房的房源朋友圈文案，要求突出：近地铁、精装修、满五唯一。"},
    ],
    stream=False
)

print("AI的回复：")
print(response.choices[0].message.content)
from pydantic import BaseModel, Field

# 1. 定义我们的数据结构（房源模型）
class HouseProperty(BaseModel):
    title: str = Field(description="房源标题")
    price: int = Field(description="总价（万元）")
    is_near_subway: bool = Field(description="是否近地铁")
    tags: list[str] = Field(description="房源标签，比如精装修、满五唯一")

# 2. 模拟一段大模型返回的错误数据（故意把 price 写成了文字，tags 写成了字符串）
fake_ai_data = {
    "title": "南山中心区两房",
    "price": "很便宜",  # 错误：这里应该是数字
    "is_near_subway": True,
    "tags": "精装修、满五唯一" # 错误：这里应该是列表
}

# 3. 尝试用 Pydantic 解析这段数据
try:
    house = HouseProperty(**fake_ai_data)
    print("解析成功！", house)
except Exception as e:
    print("=== 拦截到错误数据！===")
    print("报错原因：")
    print(e)
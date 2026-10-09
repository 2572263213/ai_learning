import json
from check_ooc import build_character_db, check_ooc

# 1. 加载测试集
with open("eval_set.json", "r", encoding="utf-8") as f:
    test_cases = json.load(f)

# 2. 加载角色向量库
print("正在加载角色向量库...")
stores = build_character_db()

# 3. 遍历测试
correct = 0
total = len(test_cases)
results = []

for case in test_cases:
    character_id = case["character_id"]
    text = case["text"]
    expected = case["expected"]  # "high" 或 "low"

    report = check_ooc(character_id, text, stores)
    score = report.consistency_score

    # TODO 1: 判断实际结果是否符合预期
    # 如果 expected == "high"，那么实际分数 >= 80 才算对
    # 如果 expected == "low"，那么实际分数 <= 50 才算对
    # 写一个 if/else，设一个变量 is_correct = True 或 False
    if expected == "high":
        is_correct = score >= 80
    else:
        is_correct = score <= 50

    if is_correct:
        correct += 1

    results.append({
        "character": character_id,
        "expected": expected,
        "actual_score": score,
        "correct": is_correct
    })

# 4. 打印结果
print("\n=== 评估结果 ===")
for r in results:
    mark = "✅" if r["correct"] else "❌"
    print(f"{mark} {r['character']} | 预期：{r['expected']} | 实际得分：{r['actual_score']}")

accuracy = correct / total * 100
print(f"\n准确率：{correct}/{total} = {accuracy:.1f}%")
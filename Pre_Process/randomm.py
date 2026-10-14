# Time：2026/10/12 17:30
import random
random.seed(2026)

# 读取本地 categories.txt
with open("../categories.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

# 清理空行、前后空格
all_categories = [line.strip() for line in lines if line.strip()]

# 无重复随机取100条
selected_categories = random.sample(all_categories, 100)

# 写入新txt文件
with open("../random_100_categories.txt", "w", encoding="utf-8") as out_f:
    for item in selected_categories:
        out_f.write(item + "\n")

print(f"原始总条目：{len(all_categories)}")
print("已随机抽取100个类别，保存到 random_100_categories.txt")

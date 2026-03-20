import json
import csv

# 读取修复后的数据
with open('fixed_new_cases.json', 'r', encoding='utf-8') as f:
    new_cases = json.load(f)

# 追加到现有CSV文件
with open('myproject/data/fraud_cases.csv', 'a', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    for case in new_cases:
        row = [
            case['案例标题'],
            case['诈骗类型'],
            case['详细描述'],
            case['涉案金额'],
            case['受害者特征'],
            case['关键词'],
            case['来源']
        ]
        writer.writerow(row)

print(f"已成功添加 {len(new_cases)} 个新案例到 fraud_cases.csv")

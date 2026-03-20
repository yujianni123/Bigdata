import csv

# 读取CSV文件
with open('myproject/data/fraud_cases.csv', 'r', encoding='utf-8') as f:
    lines = list(csv.reader(f))

print(f'总行数: {len(lines)}')
print('\n最后10行:')
for line in lines[-10:]:
    print(','.join(line))

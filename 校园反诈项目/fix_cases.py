import json
import csv

# 读取临时文件
with open('temp_new_cases.json', 'r', encoding='utf-8') as f:
    cases = json.load(f)

# 修复数据
fixed_cases = []
for case in cases:
    # 关键词和来源字段需要重新处理
    # 原始数据中，关键词是多个逗号分隔的词，最后一个是来源
    all_keywords = case['关键词'] + ',' + case['来源']
    keyword_list = [k.strip() for k in all_keywords.split(',')]
    
    # 最后一个是来源，前面的都是关键词
    if len(keyword_list) > 1:
        source = keyword_list[-1]
        keywords = ','.join(keyword_list[:-1])
    else:
        source = case['来源']
        keywords = case['关键词']
    
    fixed_case = {
        '案例标题': case['案例标题'],
        '诈骗类型': case['诈骗类型'],
        '详细描述': case['详细描述'],
        '涉案金额': case['涉案金额'],
        '受害者特征': case['受害者特征'],
        '关键词': keywords,
        '来源': source
    }
    fixed_cases.append(fixed_case)

# 保存修复后的数据
with open('fixed_new_cases.json', 'w', encoding='utf-8') as f:
    json.dump(fixed_cases, f, ensure_ascii=False, indent=2)

print(f"修复了 {len(fixed_cases)} 个案例的数据")
print("修复后的数据已保存到 fixed_new_cases.json")

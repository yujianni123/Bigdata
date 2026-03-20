#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博数据转换脚本
功能：将微博数据转换为fraud_cases.csv格式
"""

import csv
import re
import os

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
WEIBO_FILE = os.path.join(DATA_DIR, 'weibo_cases.csv')
FRAUD_CASES_FILE = os.path.join(DATA_DIR, 'fraud_cases.csv')

# 诈骗类型映射
FRAUD_TYPE_MAPPING = {
    '刷单': '刷单返利诈骗',
    '冒充熟人': '冒充熟人诈骗',
    '网贷': '虚假贷款诈骗',
    '虚假投资': '虚假投资诈骗',
    '冒充客服': '冒充客服诈骗',
    '网络兼职': '网络兼职诈骗',
    '游戏诈骗': '网络游戏产品虚假交易',
    '校园贷': '校园贷诈骗',
    '电信诈骗': '电信网络诈骗',
    '网络诈骗': '网络诈骗',
    '短信诈骗': '短信诈骗',
    '钓鱼网站': '钓鱼网站/钓鱼诈骗'
}

# 受害者特征映射
VICTIM_MAPPING = {
    '大学生': '高校学生',
    '学生': '高校学生',
    '高校': '高校学生',
    '大学': '高校学生',
    '新生': '高校新生',
    '毕业生': '高校毕业生'
}

def extract_fraud_type(content):
    """从内容中提取诈骗类型"""
    # 优先匹配完整的诈骗类型
    for keyword, fraud_type in FRAUD_TYPE_MAPPING.items():
        if keyword in content:
            return fraud_type
    return '其他诈骗'

def extract_amount(content):
    """从内容中提取涉案金额"""
    # 匹配多种金额格式
    patterns = [
        r'被骗[取]?([\d,]+)元',
        r'损失([\d,]+)元',
        r'被骗[取]?([\d,]+)余元',
        r'损失([\d,]+)余元',
        r'骗走([\d,]+)元',
        r'骗取([\d,]+)元'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1) + '元'
    
    return '未公布'

def extract_victim(content):
    """从内容中提取受害者特征"""
    for keyword, victim in VICTIM_MAPPING.items():
        if keyword in content:
            return victim
    return '不特定'

def extract_keywords(content, fraud_type):
    """从内容中提取关键词"""
    keywords = []
    
    # 添加诈骗类型作为关键词
    keywords.append(fraud_type.split('诈骗')[0])
    
    # 提取其他关键词
    keyword_patterns = [
        '刷单', '兼职', '返利', '客服', '贷款', '投资', '熟人', '校园',
        '游戏', '充值', '转账', '验证码', '链接', '佣金', '利息',
        '钓鱼', '虚假', '冒充', '电信', '网络', '短信', '银行卡',
        '密码', '账号', '安全', '防范', '提醒'
    ]
    
    for pattern in keyword_patterns:
        if pattern in content and pattern not in keywords:
            keywords.append(pattern)
    
    # 限制关键词数量
    return keywords[:4]

def generate_title(content, fraud_type):
    """生成案例标题"""
    # 提取内容中的关键信息作为标题
    # 优先提取【】中的内容
    match = re.search(r'【([^】]+)】', content)
    if match:
        title = match.group(1)
    else:
        # 否则提取前20个字符
        title = content[:20]
        if len(title) < len(content):
            title += '...'
    return f"{title}"

def convert_weibo_to_fraud_cases():
    """将微博数据转换为fraud_cases.csv格式"""
    try:
        # 读取微博数据
        weibo_cases = []
        with open(WEIBO_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                weibo_cases.append(row)
        
        if not weibo_cases:
            print("没有微博数据可转换")
            return
        
        # 转换数据
        fraud_cases = []
        for i, case in enumerate(weibo_cases, 1):
            content = case['content']
            
            # 提取信息
            fraud_type = extract_fraud_type(content)
            amount = extract_amount(content)
            victim = extract_victim(content)
            keywords = extract_keywords(content, fraud_type)
            title = generate_title(content, fraud_type)
            source = f"微博@{case['nickname']}"
            
            # 构建案例
            fraud_case = {
                '案例标题': title,
                '诈骗类型': fraud_type,
                '详细描述': content,
                '涉案金额': amount,
                '受害者特征': victim,
                '关键词': ','.join(keywords),
                '来源': source
            }
            fraud_cases.append(fraud_case)
        
        # 保存数据
        with open(FRAUD_CASES_FILE, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['案例标题', '诈骗类型', '详细描述', '涉案金额', '受害者特征', '关键词', '来源']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(fraud_cases)
        
        print(f"成功转换 {len(fraud_cases)} 条微博数据到 {FRAUD_CASES_FILE}")
        
    except Exception as e:
        print(f"转换失败: {str(e)}")

def main():
    """主函数"""
    print("开始转换微博数据到fraud_cases.csv格式...")
    convert_weibo_to_fraud_cases()
    print("转换完成！")

if __name__ == '__main__':
    main()

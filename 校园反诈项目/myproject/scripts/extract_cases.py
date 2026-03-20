#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博案例提取脚本
功能：从抓取的微博数据中清洗和提取反诈案例
"""

import csv
import re
import logging
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extract_cases.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CaseExtractor:
    def __init__(self):
        # 诈骗类型关键词
        self.fraud_types = {
            '刷单诈骗': ['刷单', '刷信誉', '刷评价', '兼职刷单'],
            '冒充熟人': ['冒充', '熟人', '朋友', '同学', '亲戚'],
            '网贷诈骗': ['贷款', '校园贷', '网贷', '小额贷'],
            '冒充公检法': ['公检法', '警察', '法院', '检察院'],
            '电信诈骗': ['电信', '电话', '短信', '诈骗'],
            '网络诈骗': ['网络', '网上', '线上', '互联网'],
            '投资诈骗': ['投资', '理财', '股票', '基金'],
            '游戏诈骗': ['游戏', '账号', '装备', '皮肤'],
            '虚假招聘': ['招聘', '兼职', '工作', '求职'],
            '其他诈骗': []
        }
        
        # 金额关键词
        self.amount_pattern = re.compile(r'\d+\.?\d*\s*(元|万|千|百|块|人民币)')
        
        # 受害者特征关键词
        self.victim_patterns = {
            '学生': ['学生', '大学生', '高校', '校园'],
            '年轻人': ['年轻人', '年轻人', '20岁', '30岁'],
            '老年人': ['老人', '老年人', '退休', ' elderly'],
            '职场人士': ['上班族', '职场', '白领', '员工']
        }
    
    def extract_cases(self, input_file, output_file):
        """从微博数据中提取案例"""
        try:
            cases = []
            
            # 读取微博数据
            with open(input_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 过滤掉无关内容
                    if not self._is_relevant_content(row['content']):
                        continue
                    
                    # 提取案例信息
                    case = self._extract_case_info(row)
                    if case:
                        cases.append(case)
            
            # 保存提取的案例
            self._save_cases(cases, output_file)
            
            logger.info(f'提取成功，共{len(cases)}个案例')
            return cases
        except Exception as e:
            logger.error(f'提取案例失败: {str(e)}')
            return []
    
    def _is_relevant_content(self, content):
        """判断内容是否相关"""
        # 过滤掉太短的内容
        if len(content) < 50:
            return False
        
        # 过滤掉广告和推广
        ad_keywords = ['推广', '广告', '营销', '赞助', '合作']
        for keyword in ad_keywords:
            if keyword in content:
                return False
        
        # 必须包含诈骗相关关键词
        fraud_keywords = ['诈骗', '受骗', '上当', '被骗', '欺诈']
        for keyword in fraud_keywords:
            if keyword in content:
                return True
        
        return False
    
    def _extract_case_info(self, row):
        """提取案例信息"""
        try:
            content = row['content']
            
            # 提取诈骗类型
            fraud_type = self._extract_fraud_type(content)
            
            # 提取金额
            amount = self._extract_amount(content)
            
            # 提取受害者特征
            victim特征 = self._extract_victim特征(content)
            
            # 提取关键词
            keywords = self._extract_keywords(content, fraud_type)
            
            # 构建案例
            case = {
                '案例标题': self._generate_title(content, fraud_type),
                '诈骗类型': fraud_type,
                '详细描述': content,
                '涉案金额': amount,
                '受害者特征': victim特征,
                '关键词': ','.join(keywords),
                '来源': f'微博@{row["nickname"]}',
                '发布时间': row['post_time'],
                '微博链接': row['link']
            }
            
            return case
        except Exception as e:
            logger.warning(f'提取案例信息失败: {str(e)}')
            return None
    
    def _extract_fraud_type(self, content):
        """提取诈骗类型"""
        for fraud_type, keywords in self.fraud_types.items():
            for keyword in keywords:
                if keyword in content:
                    return fraud_type
        return '其他诈骗'
    
    def _extract_amount(self, content):
        """提取涉案金额"""
        match = self.amount_pattern.search(content)
        if match:
            return match.group(0)
        return '未提及'
    
    def _extract_victim特征(self, content):
        """提取受害者特征"""
        for feature, keywords in self.victim_patterns.items():
            for keyword in keywords:
                if keyword in content:
                    return feature
        return '未提及'
    
    def _extract_keywords(self, content, fraud_type):
        """提取关键词"""
        keywords = []
        
        # 添加诈骗类型作为关键词
        keywords.append(fraud_type)
        
        # 从内容中提取关键词
        # 这里可以根据需要添加更多关键词提取逻辑
        
        # 限制关键词数量
        return keywords[:5]
    
    def _generate_title(self, content, fraud_type):
        """生成案例标题"""
        # 从内容中提取前30个字符作为标题
        title = content[:30]
        if len(title) < len(content):
            title += '...'
        return f'{fraud_type}: {title}'
    
    def _save_cases(self, cases, output_file):
        """保存提取的案例"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
            
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['案例标题', '诈骗类型', '详细描述', '涉案金额', '受害者特征', '关键词', '来源', '发布时间', '微博链接']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(cases)
            
            logger.info(f'保存成功，共{len(cases)}个案例')
        except Exception as e:
            logger.error(f'保存案例失败: {str(e)}')

def main():
    """主函数"""
    extractor = CaseExtractor()
    
    # 从微博数据中提取案例
    input_file = 'data/weibo_cases.csv'
    output_file = 'data/extracted_cases.csv'
    
    if not os.path.exists(input_file):
        logger.error(f'输入文件不存在: {input_file}')
        return
    
    extractor.extract_cases(input_file, output_file)

if __name__ == '__main__':
    main()

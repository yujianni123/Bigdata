import json
import csv
import os
import re
from datetime import datetime, timedelta

# 缓存存储
cache = {}

# 缓存装饰器
def cached(timeout=3600):
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            
            # 检查缓存
            if cache_key in cache:
                cached_data, timestamp = cache[cache_key]
                # 检查缓存是否过期
                if (datetime.now().timestamp() - timestamp) < timeout:
                    return cached_data
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            cache[cache_key] = (result, datetime.now().timestamp())
            return result
        return wrapper
    return decorator

# 数据文件夹路径
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# 诈骗案例数据文件
FRAUD_CASES_FILE = os.path.join(DATA_DIR, 'fraud_cases.csv')

# 风险规则文件
RISK_RULES_FILE = os.path.join(DATA_DIR, 'risk_rules.json')

# 风险词库文件
RISK_WORDS_FILE = os.path.join(DATA_DIR, 'risk_words.json')

# 高风险号段文件
HIGH_RISK_PHONENUMBERS_FILE = os.path.join(DATA_DIR, 'high_risk_phonenumbers.csv')

# URL规则文件
URL_RULES_FILE = os.path.join(DATA_DIR, 'url_rules.json')

@cached(timeout=3600)
def load_fraud_cases():
    """加载诈骗案例数据"""
    try:
        cases = []
        with open(FRAUD_CASES_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                # 映射新的CSV格式到API期望的字段结构
                case = {
                    'case_id': f'FC{i:03d}',  # 生成案例ID
                    'case_type': row.get('诈骗类型', '其他诈骗'),
                    'description': row.get('详细描述', ''),
                    'loss_amount': 0.0,  # 默认金额
                    'occurred_at': datetime.now()  # 使用当前时间作为默认值
                }
                
                # 处理涉案金额
                amount_str = row.get('涉案金额', '').strip()
                if amount_str and amount_str not in ['未公布', '未明确', '未遂']:
                    # 提取数字部分
                    amount_match = re.search(r'\d+(\.\d+)?', amount_str)
                    if amount_match:
                        try:
                            case['loss_amount'] = float(amount_match.group(0))
                        except:
                            pass
                
                cases.append(case)
        return cases
    except Exception as e:
        print(f"Error loading fraud cases: {e}")
        return []

@cached(timeout=7200)
def load_risk_rules():
    """加载风险规则"""
    try:
        with open(RISK_RULES_FILE, 'r', encoding='utf-8') as f:
            rules = json.load(f)
        return rules
    except Exception as e:
        print(f"Error loading risk rules: {e}")
        return {}

@cached(timeout=7200)
def load_risk_words():
    """加载风险词库"""
    try:
        with open(RISK_WORDS_FILE, 'r', encoding='utf-8') as f:
            words = json.load(f)
        return words
    except Exception as e:
        print(f"Error loading risk words: {e}")
        return {
            "high_risk_words": [],
            "medium_risk_words": [],
            "suspicious_phrases": []
        }

@cached(timeout=7200)
def load_high_risk_phonenumbers():
    """加载高风险号段"""
    try:
        numbers = []
        with open(HIGH_RISK_PHONENUMBERS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                numbers.append(row)
        return numbers
    except Exception as e:
        print(f"Error loading high risk phone numbers: {e}")
        return []

@cached(timeout=7200)
def load_url_rules():
    """加载URL规则"""
    try:
        with open(URL_RULES_FILE, 'r', encoding='utf-8') as f:
            rules = json.load(f)
        return rules
    except Exception as e:
        print(f"Error loading URL rules: {e}")
        return {
            "short_url_domains": [],
            "fake_domain_patterns": []
        }

def calculate_risk_score(transaction_data, rules=None):
    """计算风险评分"""
    if rules is None:
        rules = load_risk_rules()
    
    risk_score = 0.0
    matched_rules = []
    
    # 检查交易金额
    amount = transaction_data.get('amount', 0)
    if amount > rules.get('max_safe_amount', 5000):
        risk_score += rules.get('amount_weight', 0.3)
        matched_rules.append('金额超过安全阈值')
    
    # 检查交易时间
    hour = datetime.now().hour
    if hour < rules.get('safe_hour_start', 6) or hour > rules.get('safe_hour_end', 22):
        risk_score += rules.get('time_weight', 0.2)
        matched_rules.append('交易时间异常')
    
    # 检查交易对象
    recipient = transaction_data.get('recipient', '')
    if recipient in rules.get('suspicious_recipients', []):
        risk_score += rules.get('recipient_weight', 0.4)
        matched_rules.append('交易对象可疑')
    
    # 检查交易频率
    if transaction_data.get('frequency', 0) > rules.get('max_frequency', 5):
        risk_score += rules.get('frequency_weight', 0.1)
        matched_rules.append('交易频率异常')
    
    # 确保风险评分在0-1之间
    risk_score = min(max(risk_score, 0), 1)
    
    return {
        'risk_score': risk_score,
        'matched_rules': matched_rules,
        'risk_level': 'high' if risk_score > 0.7 else 'medium' if risk_score > 0.3 else 'low'
    }

def calculate_fraud_risk_score(content, phone_number=None, url=None):
    """计算诈骗风险评分"""
    risk_score = 0
    matched_items = []
    
    # 加载风险词库
    risk_words = load_risk_words()
    
    # 检查高危词
    for word in risk_words.get('high_risk_words', []):
        if word in content:
            risk_score += 20
            matched_items.append(f'包含高危词: {word}')
    
    # 检查中危词
    for word in risk_words.get('medium_risk_words', []):
        if word in content:
            risk_score += 10
            matched_items.append(f'包含中危词: {word}')
    
    # 检查可疑短语
    for phrase in risk_words.get('suspicious_phrases', []):
        if phrase in content:
            risk_score += 15
            matched_items.append(f'包含可疑短语: {phrase}')
    
    # 检查高风险号码
    if phone_number:
        high_risk_numbers = load_high_risk_phonenumbers()
        for item in high_risk_numbers:
            if item['number'] == phone_number:
                risk_score += 30
                matched_items.append(f'使用高风险号码: {phone_number}')
                break
    
    # 检查URL
    if url:
        url_rules = load_url_rules()
        # 检查短链接
        for domain in url_rules.get('short_url_domains', []):
            if domain in url:
                risk_score += 15
                matched_items.append(f'使用短链接: {url}')
                break
        # 检查仿冒域名
        for pattern in url_rules.get('fake_domain_patterns', []):
            # 简单的模式匹配
            if '*' in pattern:
                pattern = pattern.replace('*', '.*')
                if re.match(pattern, url):
                    risk_score += 25
                    matched_items.append(f'使用仿冒域名: {url}')
                    break
            else:
                if pattern in url:
                    risk_score += 25
                    matched_items.append(f'使用仿冒域名: {url}')
                    break
    
    # 确定风险等级
    if risk_score > 60:
        risk_level = '高风险'
    elif risk_score > 30:
        risk_level = '中风险'
    else:
        risk_level = '低风险'
    
    return {
        'risk_score': risk_score,
        'matched_items': matched_items,
        'risk_level': risk_level
    }

def format_response(success, message, data=None, error=None):
    """格式化API响应"""
    response = {
        'success': success,
        'message': message
    }
    if data is not None:
        response['data'] = data
    if error is not None:
        response['error'] = error
    return response

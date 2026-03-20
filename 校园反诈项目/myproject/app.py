from flask import Flask, request, jsonify, send_from_directory
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
from auth import auth_bp
from utils import load_fraud_cases, calculate_risk_score, calculate_fraud_risk_score, format_response, load_risk_words, load_url_rules
from models import init_db, add_warning, get_user_warnings, get_class_warnings, handle_warning, get_user_by_username, get_user_query_count, get_db
import os
import re
import sqlite3
import logging
from datetime import datetime
from dotenv import load_dotenv

# 内存队列模拟推送
notification_queue = []

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

# 加载环境变量
load_dotenv()

# 创建Flask应用
app = Flask(__name__)

# 配置静态文件目录
app.static_folder = 'static'

# 配置JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')

# 配置CSRF（API服务不需要CSRF保护）
app.config['WTF_CSRF_ENABLED'] = False
app.config['WTF_CSRF_SECRET_KEY'] = os.getenv('CSRF_SECRET_KEY', 'your-csrf-secret-key')

# 初始化JWT
jwt = JWTManager(app)

# 初始化CORS
CORS(app, origins=['*'], supports_credentials=True)

# 初始化限流
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=['200 per day', '50 per hour']
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 初始化数据库
init_db()

# 注册蓝图
app.register_blueprint(auth_bp, url_prefix='')

# 初始化CSRF保护（在注册蓝图后）
csrf = CSRFProtect(app)

# 为API路由禁用CSRF保护的装饰器
def csrf_exempt_api(f):
    return csrf.exempt(f)

# 为所有API路由添加CSRF豁免
for rule in app.url_map.iter_rules():
    if rule.rule.startswith('/api/'):
        endpoint = app.view_functions.get(rule.endpoint)
        if endpoint:
            app.view_functions[rule.endpoint] = csrf.exempt(endpoint)

# 为登录和注册接口添加CSRF豁免
login_endpoint = app.view_functions.get('auth.login')
if login_endpoint:
    app.view_functions['auth.login'] = csrf.exempt(login_endpoint)

register_endpoint = app.view_functions.get('auth.register')
if register_endpoint:
    app.view_functions['auth.register'] = csrf.exempt(register_endpoint)

@app.route('/')
def index():
    """首页"""
    return send_from_directory('static', 'index.html')

@app.route('/api')
def api_index():
    """API首页"""
    return jsonify(format_response(True, 'Welcome to Fraud Detection API'))

@app.route('/fraud-cases', methods=['GET'])
def get_fraud_cases():
    """获取诈骗案例"""
    try:
        cases = load_fraud_cases()
        # 转换日期格式
        for case in cases:
            if isinstance(case['occurred_at'], str):
                # 如果是字符串，尝试转换为datetime对象
                try:
                    case['occurred_at'] = datetime.strptime(case['occurred_at'], '%Y-%m-%d %H:%M:%S')
                except:
                    case['occurred_at'] = datetime.now()
            case['occurred_at'] = case['occurred_at'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify(format_response(True, 'Fraud cases retrieved successfully', data=cases))
    except Exception as e:
        logger.error(f"Error in get_fraud_cases: {str(e)}")
        return jsonify(format_response(False, 'Failed to retrieve fraud cases', error=str(e)))

@app.route('/api/cases', methods=['GET'])
def get_cases():
    """案例列表（分页）"""
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        
        # 加载案例数据
        cases = load_fraud_cases()
        
        # 计算分页
        total = len(cases)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_cases = cases[start:end]
        
        # 转换日期格式
        for case in paginated_cases:
            if isinstance(case['occurred_at'], str):
                # 如果是字符串，尝试转换为datetime对象
                try:
                    case['occurred_at'] = datetime.strptime(case['occurred_at'], '%Y-%m-%d %H:%M:%S')
                except:
                    case['occurred_at'] = datetime.now()
            case['occurred_at'] = case['occurred_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'success': True,
            'cases': paginated_cases,
            'total': total,
            'page': page,
            'page_size': page_size
        })
    except Exception as e:
        logger.error(f"Error in get_cases: {str(e)}")
        return jsonify(format_response(False, 'Failed to get cases', error=str(e)))

@app.route('/api/cases/<string:case_id>', methods=['GET'])
def get_case_detail(case_id):
    """案例详情"""
    try:
        cases = load_fraud_cases()
        case = next((c for c in cases if c['case_id'] == case_id), None)
        
        if not case:
            return jsonify(format_response(False, 'Case not found')), 404
        
        # 转换日期格式
        if isinstance(case['occurred_at'], str):
            # 如果是字符串，尝试转换为datetime对象
            try:
                case['occurred_at'] = datetime.strptime(case['occurred_at'], '%Y-%m-%d %H:%M:%S')
            except:
                case['occurred_at'] = datetime.now()
        case['occurred_at'] = case['occurred_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'success': True,
            'case': case
        })
    except Exception as e:
        logger.error(f"Error in get_case_detail: {str(e)}")
        return jsonify(format_response(False, 'Failed to get case detail', error=str(e)))

@app.route('/api/cases/random', methods=['GET'])
def get_random_case():
    """每日一案例"""
    try:
        import random
        cases = load_fraud_cases()
        
        if not cases:
            return jsonify(format_response(False, 'No cases found')), 404
        
        # 随机选择一个案例
        random_case = random.choice(cases)
        
        # 转换日期格式
        if isinstance(random_case['occurred_at'], str):
            # 如果是字符串，尝试转换为datetime对象
            try:
                random_case['occurred_at'] = datetime.strptime(random_case['occurred_at'], '%Y-%m-%d %H:%M:%S')
            except:
                random_case['occurred_at'] = datetime.now()
        random_case['occurred_at'] = random_case['occurred_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'success': True,
            'case': random_case
        })
    except Exception as e:
        logger.error(f"Error in get_random_case: {str(e)}")
        return jsonify(format_response(False, 'Failed to get random case', error=str(e)))

@app.route('/risk-assessment', methods=['POST'])
def risk_assessment():
    """风险评估"""
    try:
        data = request.get_json()
        if not data:
            return jsonify(format_response(False, 'No input data provided')), 400
        
        risk_result = calculate_risk_score(data)
        return jsonify(format_response(True, 'Risk assessment completed', data=risk_result))
    except Exception as e:
        return jsonify(format_response(False, 'Failed to assess risk', error=str(e)))

@app.route('/fraud-risk-assessment', methods=['POST'])
def fraud_risk_assessment():
    """诈骗风险评估"""
    try:
        data = request.get_json()
        if not data:
            return jsonify(format_response(False, 'No input data provided')), 400
        
        content = data.get('content', '')
        phone_number = data.get('phone_number')
        url = data.get('url')
        
        if not content:
            return jsonify(format_response(False, 'Content is required')), 400
        
        risk_result = calculate_fraud_risk_score(content, phone_number, url)
        return jsonify(format_response(True, 'Fraud risk assessment completed', data=risk_result))
    except Exception as e:
        return jsonify(format_response(False, 'Failed to assess fraud risk', error=str(e)))

def check_warning_conditions(user_id, risk_score, content):
    """检查是否需要生成预警"""
    # 检查单次检测风险>80
    if risk_score > 80:
        return True, f'单次检测风险分数过高: {risk_score}'
    
    # 检查24小时内3次中风险
    query_count = get_user_query_count(user_id, 24)
    if query_count >= 3:
        return True, '24小时内查询次数过多'
    
    # 检查敏感词
    sensitive_words = ['裸聊', '网贷', '赌博', '色情', '毒品']
    for word in sensitive_words:
        if word in content:
            return True, f'包含敏感词: {word}'
    
    return False, ''

def send_notification(user_id, message, notification_type):
    """模拟发送通知"""
    notification = {
        'user_id': user_id,
        'message': message,
        'type': notification_type,
        'timestamp': datetime.now().isoformat()
    }
    notification_queue.append(notification)
    print(f"通知已添加到队列: {message}")

@app.route('/api/check/text', methods=['POST'])
@jwt_required()
@limiter.limit('10 per minute')
def check_text():
    """文本检测API"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            logger.warning(f"User not found: {current_user}")
            return jsonify(format_response(False, 'User not found')), 404
        
        data = request.get_json()
        if not data or 'text' not in data:
            logger.warning(f"Missing text parameter for user: {current_user}")
            return jsonify(format_response(False, 'Text is required')), 400
        
        text = data['text']
        logger.info(f"Text check request from user: {current_user}, text length: {len(text)}")
        
        # 加载风险词库
        risk_words = load_risk_words()
        
        # 分词并匹配风险词
        matched_keywords = []
        risk_score = 0
        
        # 检查高危词
        for word in risk_words.get('high_risk_words', []):
            if word in text:
                matched_keywords.append(word)
                risk_score += 20
        
        # 检查中危词
        for word in risk_words.get('medium_risk_words', []):
            if word in text:
                matched_keywords.append(word)
                risk_score += 10
        
        # 检查可疑短语
        for phrase in risk_words.get('suspicious_phrases', []):
            if phrase in text:
                matched_keywords.append(phrase)
                risk_score += 15
        
        # 识别诈骗类型
        fraud_type = '未知类型'
        if '安全账户' in text or '涉嫌洗钱' in text:
            fraud_type = '冒充公检法'
        elif '刷单' in text or '返利' in text:
            fraud_type = '刷单返利'
        elif '客服' in text and '退款' in text:
            fraud_type = '冒充客服'
        elif '贷款' in text or '保证金' in text:
            fraud_type = '虚假贷款'
        elif '投资' in text or '高收益' in text:
            fraud_type = '网络投资'
        
        # 确定风险等级
        if risk_score > 60:
            risk_level = 'high'
        elif risk_score > 30:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        # 生成建议
        suggestion = '请提高警惕，注意防范诈骗！'
        if fraud_type == '冒充公检法':
            suggestion = '这是典型的冒充公检法诈骗，请立即挂断电话！'
        elif fraud_type == '刷单返利':
            suggestion = '刷单是违法行为，切勿参与！'
        elif fraud_type == '冒充客服':
            suggestion = '请通过官方渠道联系客服，不要轻信陌生电话！'
        elif fraud_type == '虚假贷款':
            suggestion = '正规贷款不会收取前期费用，请勿转账！'
        elif fraud_type == '网络投资':
            suggestion = '高收益往往伴随高风险，投资需谨慎！'
        
        # 检索相似案例
        cases = load_fraud_cases()
        similar_cases = []
        
        for case in cases:
            if fraud_type in case['case_type']:
                similar_cases.append({
                    'type': case['case_type'],
                    'description': case['description'],
                    'amount': case['loss_amount']
                })
            if len(similar_cases) >= 3:
                break
        
        # 检查是否需要生成预警
        should_warn, warning_reason = check_warning_conditions(user['id'], risk_score, text)
        if should_warn:
            # 添加预警记录
            add_warning(user['id'], warning_reason, risk_score)
            # 发送通知
            send_notification(user['id'], f'您有一条新的预警: {warning_reason}', 'warning')
            logger.info(f"Warning generated for user {current_user}: {warning_reason}")
        
        # 记录查询日志
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
        INSERT INTO query_log (user_id, content, result, risk_score)
        VALUES (?, ?, ?, ?)
        ''', (user['id'], text, fraud_type, risk_score))
        db.commit()
        db.close()
        
        logger.info(f"Text check completed for user {current_user}, risk score: {risk_score}, fraud type: {fraud_type}")
        
        return jsonify({
            'success': True,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'fraud_type': fraud_type,
            'matched_keywords': matched_keywords,
            'suggestion': suggestion,
            'similar_cases': similar_cases,
            'warning_generated': should_warn
        })
    except Exception as e:
        logger.error(f"Error in check_text: {str(e)}")
        return jsonify(format_response(False, 'Failed to check text', error=str(e)))

@app.route('/api/check/url', methods=['POST'])
@jwt_required()
@limiter.limit('10 per minute')
def check_url():
    """URL检测API"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            logger.warning(f"User not found: {current_user}")
            return jsonify(format_response(False, 'User not found')), 404
        
        data = request.get_json()
        if not data or 'url' not in data:
            logger.warning(f"Missing URL parameter for user: {current_user}")
            return jsonify(format_response(False, 'URL is required')), 400
        
        url = data['url']
        logger.info(f"URL check request from user: {current_user}, URL: {url}")
        
        # 加载URL规则
        url_rules = load_url_rules()
        
        # 检查是否在黑名单域名中
        risk_score = 0
        reasons = []
        domain = url.split('//')[-1].split('/')[0]
        
        # 检查短链接
        for short_domain in url_rules.get('short_url_domains', []):
            if short_domain in url:
                risk_score += 15
                reasons.append('使用短链接')
                break
        
        # 检查仿冒域名
        fake_domains = {
            'ta0ba0.com': '疑似仿冒淘宝',
            '1688.com': '疑似仿冒阿里巴巴',
            'weixin.com': '疑似仿冒微信',
            'qq.com': '疑似仿冒腾讯',
            'baidu.com': '疑似仿冒百度'
        }
        
        for fake_domain, reason in fake_domains.items():
            if fake_domain in url:
                risk_score += 30
                reasons.append(reason)
                break
        
        # 检查URL特征
        if re.search(r'[0-9]{10,}', url):
            risk_score += 10
            reasons.append('URL包含大量数字')
        
        if re.search(r'[!@#$%^&*()_+{}|:"<>?]', url):
            risk_score += 10
            reasons.append('URL包含特殊字符')
        
        # 模拟Whois信息
        creation_date = '2024-01-01'  # 模拟数据
        
        # 确定风险等级
        if risk_score > 60:
            risk_level = 'high'
        elif risk_score > 30:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        # 检查是否需要生成预警
        should_warn, warning_reason = check_warning_conditions(user['id'], risk_score, url)
        if should_warn:
            # 添加预警记录
            add_warning(user['id'], warning_reason, risk_score)
            # 发送通知
            send_notification(user['id'], f'您有一条新的预警: {warning_reason}', 'warning')
            logger.info(f"Warning generated for user {current_user}: {warning_reason}")
        
        # 记录查询日志
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
        INSERT INTO query_log (user_id, content, result, risk_score)
        VALUES (?, ?, ?, ?)
        ''', (user['id'], url, 'URL检测', risk_score))
        db.commit()
        db.close()
        
        logger.info(f"URL check completed for user {current_user}, risk score: {risk_score}, domain: {domain}")
        
        return jsonify({
            'success': True,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'reasons': reasons,
            'domain': domain,
            'creation_date': creation_date,
            'warning_generated': should_warn
        })
    except Exception as e:
        logger.error(f"Error in check_url: {str(e)}")
        return jsonify(format_response(False, 'Failed to check URL', error=str(e)))

@app.route('/api/check/history', methods=['GET'])
@jwt_required()
def get_check_history():
    """查询历史检测记录"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 获取历史记录
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
        SELECT * FROM query_log WHERE user_id = ? ORDER BY created_at DESC
        ''', (user['id'],))
        history = cursor.fetchall()
        db.close()
        
        history_list = []
        for record in history:
            history_list.append({
                'id': record['id'],
                'content': record['content'],
                'result': record['result'],
                'risk_score': record['risk_score'],
                'created_at': record['created_at']
            })
        
        return jsonify({
            'success': True,
            'history': history_list
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get history', error=str(e)))

@app.route('/api/warnings/my', methods=['GET'])
@jwt_required()
def get_my_warnings():
    """学生查看自己的预警"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        warnings = get_user_warnings(user['id'])
        warnings_list = []
        for warning in warnings:
            warnings_list.append({
                'id': warning['id'],
                'reason': warning['reason'],
                'risk_score': warning['risk_score'],
                'status': warning['status'],
                'created_at': warning['created_at']
            })
        
        return jsonify({
            'success': True,
            'warnings': warnings_list
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get warnings', error=str(e)))

@app.route('/api/teacher/warnings/all', methods=['GET'])
@jwt_required()
def get_teacher_all_warnings():
    """辅导员查看班级所有预警"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为辅导员
        if user['role'] != 'teacher':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 假设辅导员负责的班级
        class_name = user['class_name'] or '计算机科学与技术1班'
        warnings = get_class_warnings(class_name)
        
        warnings_list = []
        for warning in warnings:
            warnings_list.append({
                'id': warning['id'],
                'user_id': warning['user_id'],
                'username': warning['username'],
                'class_name': warning['class_name'],
                'reason': warning['reason'],
                'risk_score': warning['risk_score'],
                'status': warning['status'],
                'created_at': warning['created_at']
            })
        
        return jsonify({
            'success': True,
            'warnings': warnings_list
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get warnings', error=str(e)))

@app.route('/api/warnings/<int:warning_id>/handle', methods=['POST'])
@jwt_required()
def handle_warning_endpoint(warning_id):
    """处理预警"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 处理预警
        handle_warning(warning_id, user['id'])
        
        return jsonify({
            'success': True,
            'message': '预警处理成功'
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to handle warning', error=str(e)))

@app.route('/api/user/profile', methods=['GET'])
@jwt_required()
def get_user_profile():
    """个人信息"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'name': user['name'],
                'role': user['role'],
                'class_name': user['class_name'],
                'created_at': user['created_at']
            }
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get user profile', error=str(e)))

@app.route('/api/user/risk-score', methods=['GET'])
@jwt_required()
def get_user_risk_score():
    """我的风险分"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 计算用户风险分
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
        SELECT AVG(risk_score) as avg_risk_score, MAX(risk_score) as max_risk_score, COUNT(*) as total_queries
        FROM query_log WHERE user_id = ?
        ''', (user['id'],))
        result = cursor.fetchone()
        db.close()
        
        avg_risk_score = result['avg_risk_score'] or 0
        max_risk_score = result['max_risk_score'] or 0
        total_queries = result['total_queries'] or 0
        
        # 计算综合风险分
        risk_score = int(avg_risk_score * 0.7 + max_risk_score * 0.3)
        
        # 确定风险等级
        if risk_score > 60:
            risk_level = 'high'
        elif risk_score > 30:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return jsonify({
            'success': True,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'avg_risk_score': round(avg_risk_score, 2),
            'max_risk_score': max_risk_score,
            'total_queries': total_queries
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get risk score', error=str(e)))

@app.route('/api/user/warnings', methods=['GET'])
@jwt_required()
def get_user_warnings_api():
    """我的预警"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        warnings = get_user_warnings(user['id'])
        warnings_list = []
        for warning in warnings:
            warnings_list.append({
                'id': warning['id'],
                'reason': warning['reason'],
                'risk_score': warning['risk_score'],
                'status': warning['status'],
                'created_at': warning['created_at']
            })
        
        return jsonify({
            'success': True,
            'warnings': warnings_list
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get warnings', error=str(e)))

@app.route('/api/feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    """提交线索"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        data = request.get_json()
        if not data:
            return jsonify(format_response(False, 'No input data provided')), 400
        
        # 检查必要字段
        if 'content' not in data or 'type' not in data:
            return jsonify(format_response(False, 'Missing required fields')), 400
        
        content = data['content']
        feedback_type = data['type']
        
        # 提交反馈
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
        INSERT INTO feedback (user_id, content, type, status)
        VALUES (?, ?, ?, ?)
        ''', (user['id'], content, feedback_type, 'pending'))
        db.commit()
        db.close()
        
        return jsonify({
            'success': True,
            'message': '反馈提交成功'
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to submit feedback', error=str(e)))

@app.route('/api/feedback/my', methods=['GET'])
@jwt_required()
def get_my_feedback():
    """我的反馈"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 获取用户的反馈
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
        SELECT * FROM feedback WHERE user_id = ? ORDER BY created_at DESC
        ''', (user['id'],))
        feedbacks = cursor.fetchall()
        db.close()
        
        feedback_list = []
        for feedback in feedbacks:
            feedback_list.append({
                'id': feedback['id'],
                'content': feedback['content'],
                'type': feedback['type'],
                'status': feedback['status'],
                'created_at': feedback['created_at']
            })
        
        return jsonify({
            'success': True,
            'feedbacks': feedback_list
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get feedback', error=str(e)))

# 辅导员端API
@app.route('/api/teacher/dashboard', methods=['GET'])
@jwt_required()
def get_teacher_dashboard():
    """班级概览"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为辅导员
        if user['role'] != 'teacher':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 辅导员负责的班级
        class_name = user['class_name']
        
        # 获取班级数据
        db = get_db()
        cursor = db.cursor()
        
        # 1. 总人数
        cursor.execute('''
        SELECT COUNT(*) as total_students FROM user WHERE class_name = ? AND role = 'student'
        ''', (class_name,))
        total_students = cursor.fetchone()['total_students']
        
        # 2. 高风险人数（风险分>60）
        cursor.execute('''
        SELECT COUNT(DISTINCT q.user_id) as high_risk_students
        FROM query_log q
        JOIN user u ON q.user_id = u.id
        WHERE u.class_name = ? AND u.role = 'student' AND q.risk_score > 60
        ''', (class_name,))
        high_risk_students = cursor.fetchone()['high_risk_students']
        
        # 3. 今日预警
        cursor.execute('''
        SELECT COUNT(*) as today_warnings
        FROM warning w
        JOIN user u ON w.user_id = u.id
        WHERE u.class_name = ? AND w.created_at >= date('now')
        ''', (class_name,))
        today_warnings = cursor.fetchone()['today_warnings']
        
        db.close()
        
        return jsonify({
            'success': True,
            'dashboard': {
                'total_students': total_students,
                'high_risk_students': high_risk_students,
                'today_warnings': today_warnings,
                'class_name': class_name
            }
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get dashboard data', error=str(e)))

@app.route('/api/teacher/students', methods=['GET'])
@jwt_required()
def get_teacher_students():
    """学生列表（含风险等级）"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为辅导员
        if user['role'] != 'teacher':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 辅导员负责的班级
        class_name = user['class_name']
        
        # 获取学生列表
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
        SELECT u.id, u.username, u.name, u.email
        FROM user u
        WHERE u.class_name = ? AND u.role = 'student'
        ORDER BY u.username
        ''', (class_name,))
        students = cursor.fetchall()
        
        student_list = []
        for student in students:
            # 计算学生的风险等级
            cursor.execute('''
            SELECT AVG(risk_score) as avg_risk_score
            FROM query_log
            WHERE user_id = ?
            ''', (student['id'],))
            avg_risk = cursor.fetchone()['avg_risk_score'] or 0
            
            # 确定风险等级
            if avg_risk > 60:
                risk_level = 'high'
            elif avg_risk > 30:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            student_list.append({
                'id': student['id'],
                'username': student['username'],
                'name': student['name'],
                'email': student['email'],
                'risk_level': risk_level,
                'risk_score': round(avg_risk, 2)
            })
        
        db.close()
        
        return jsonify({
            'success': True,
            'students': student_list,
            'class_name': class_name
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get students', error=str(e)))

@app.route('/api/teacher/warnings', methods=['GET'])
@jwt_required()
def get_teacher_pending_warnings():
    """待处理预警"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为辅导员
        if user['role'] != 'teacher':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 辅导员负责的班级
        class_name = user['class_name']
        
        # 获取待处理预警
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
        SELECT w.id, w.user_id, u.username, u.name, w.reason, w.risk_score, w.status, w.created_at
        FROM warning w
        JOIN user u ON w.user_id = u.id
        WHERE u.class_name = ? AND w.status = 'pending'
        ORDER BY w.created_at DESC
        ''', (class_name,))
        warnings = cursor.fetchall()
        
        warning_list = []
        for warning in warnings:
            warning_list.append({
                'id': warning['id'],
                'user_id': warning['user_id'],
                'username': warning['username'],
                'name': warning['name'],
                'reason': warning['reason'],
                'risk_score': warning['risk_score'],
                'status': warning['status'],
                'created_at': warning['created_at']
            })
        
        db.close()
        
        return jsonify({
            'success': True,
            'warnings': warning_list,
            'class_name': class_name
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get warnings', error=str(e)))

@app.route('/api/teacher/warnings/<int:warning_id>', methods=['PUT'])
@jwt_required()
def update_teacher_warning(warning_id):
    """标记已处理（填写处理记录）"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为辅导员
        if user['role'] != 'teacher':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify(format_response(False, 'No input data provided')), 400
        
        # 检查预警是否存在且属于该辅导员的班级
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
        SELECT w.id, u.class_name
        FROM warning w
        JOIN user u ON w.user_id = u.id
        WHERE w.id = ? AND u.class_name = ?
        ''', (warning_id, user['class_name']))
        warning = cursor.fetchone()
        
        if not warning:
            db.close()
            return jsonify(format_response(False, 'Warning not found or not in your class')), 404
        
        # 更新预警状态
        cursor.execute('''
        UPDATE warning SET status = 'handled', handler_id = ?
        WHERE id = ?
        ''', (user['id'], warning_id))
        
        db.commit()
        db.close()
        
        return jsonify({
            'success': True,
            'message': '预警处理成功'
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to update warning', error=str(e)))

@app.route('/api/teacher/focus', methods=['GET'])
@jwt_required()
def get_teacher_focus():
    """重点关注列表"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为辅导员
        if user['role'] != 'teacher':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 获取重点关注列表
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
        SELECT f.id, s.id as student_id, s.username, s.name, s.email, f.reason, f.created_at
        FROM focus f
        JOIN user s ON f.student_id = s.id
        WHERE f.teacher_id = ?
        ORDER BY f.created_at DESC
        ''', (user['id'],))
        focus_list = cursor.fetchall()
        
        focus_items = []
        for item in focus_list:
            # 计算学生的风险等级
            cursor.execute('''
            SELECT AVG(risk_score) as avg_risk_score
            FROM query_log
            WHERE user_id = ?
            ''', (item['student_id'],))
            avg_risk = cursor.fetchone()['avg_risk_score'] or 0
            
            # 确定风险等级
            if avg_risk > 60:
                risk_level = 'high'
            elif avg_risk > 30:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            focus_items.append({
                'id': item['id'],
                'student_id': item['student_id'],
                'username': item['username'],
                'name': item['name'],
                'email': item['email'],
                'reason': item['reason'],
                'risk_level': risk_level,
                'risk_score': round(avg_risk, 2),
                'created_at': item['created_at']
            })
        
        db.close()
        
        return jsonify({
            'success': True,
            'focus_list': focus_items
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get focus list', error=str(e)))

@app.route('/api/teacher/focus', methods=['POST'])
@jwt_required()
def add_teacher_focus():
    """添加重点关注"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为辅导员
        if user['role'] != 'teacher':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 获取请求数据
        data = request.get_json()
        if not data or 'student_id' not in data or 'reason' not in data:
            return jsonify(format_response(False, 'Missing required fields')), 400
        
        student_id = data['student_id']
        reason = data['reason']
        
        # 检查学生是否存在且属于该辅导员的班级
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
        SELECT id, class_name FROM user
        WHERE id = ? AND class_name = ? AND role = 'student'
        ''', (student_id, user['class_name']))
        student = cursor.fetchone()
        
        if not student:
            db.close()
            return jsonify(format_response(False, 'Student not found or not in your class')), 404
        
        # 添加重点关注
        try:
            cursor.execute('''
            INSERT INTO focus (teacher_id, student_id, reason)
            VALUES (?, ?, ?)
            ''', (user['id'], student_id, reason))
            db.commit()
        except sqlite3.IntegrityError:
            db.close()
            return jsonify(format_response(False, 'Student already in focus list')), 400
        
        db.close()
        
        return jsonify({
            'success': True,
            'message': '添加重点关注成功'
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to add focus', error=str(e)))

@app.route('/api/teacher/focus/<int:focus_id>', methods=['DELETE'])
@jwt_required()
def remove_teacher_focus(focus_id):
    """移除重点关注"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为辅导员
        if user['role'] != 'teacher':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 检查重点关注是否存在且属于该辅导员
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
        SELECT id FROM focus
        WHERE id = ? AND teacher_id = ?
        ''', (focus_id, user['id']))
        focus = cursor.fetchone()
        
        if not focus:
            db.close()
            return jsonify(format_response(False, 'Focus not found')), 404
        
        # 移除重点关注
        cursor.execute('''
        DELETE FROM focus
        WHERE id = ?
        ''', (focus_id,))
        db.commit()
        db.close()
        
        return jsonify({
            'success': True,
            'message': '移除重点关注成功'
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to remove focus', error=str(e)))

@app.route('/api/teacher/stats/weekly', methods=['GET'])
@jwt_required()
def get_teacher_weekly_stats():
    """本周趋势"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为辅导员
        if user['role'] != 'teacher':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 辅导员负责的班级
        class_name = user['class_name']
        
        # 获取本周趋势数据
        db = get_db()
        cursor = db.cursor()
        
        # 生成最近7天的日期
        import datetime
        today = datetime.date.today()
        dates = [(today - datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
        
        # 获取每天的预警数量
        daily_warnings = []
        for date in dates:
            cursor.execute('''
            SELECT COUNT(*) as count
            FROM warning w
            JOIN user u ON w.user_id = u.id
            WHERE u.class_name = ? AND date(w.created_at) = ?
            ''', (class_name, date))
            count = cursor.fetchone()['count']
            daily_warnings.append(count)
        
        # 获取每天的查询数量
        daily_queries = []
        for date in dates:
            cursor.execute('''
            SELECT COUNT(*) as count
            FROM query_log q
            JOIN user u ON q.user_id = u.id
            WHERE u.class_name = ? AND date(q.created_at) = ?
            ''', (class_name, date))
            count = cursor.fetchone()['count']
            daily_queries.append(count)
        
        db.close()
        
        return jsonify({
            'success': True,
            'weekly_stats': {
                'dates': dates,
                'warnings': daily_warnings,
                'queries': daily_queries
            },
            'class_name': class_name
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get weekly stats', error=str(e)))

@app.route('/api/teacher/stats/types', methods=['GET'])
@jwt_required()
def get_teacher_type_stats():
    """诈骗类型分布"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为辅导员
        if user['role'] != 'teacher':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 辅导员负责的班级
        class_name = user['class_name']
        
        # 获取诈骗类型分布数据
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
        SELECT q.result as fraud_type, COUNT(*) as count
        FROM query_log q
        JOIN user u ON q.user_id = u.id
        WHERE u.class_name = ? AND q.result != 'URL检测'
        GROUP BY q.result
        ORDER BY count DESC
        ''', (class_name,))
        type_stats = cursor.fetchall()
        
        categories = []
        series = []
        for item in type_stats:
            categories.append(item['fraud_type'])
            series.append(item['count'])
        
        db.close()
        
        return jsonify({
            'success': True,
            'type_stats': {
                'categories': categories,
                'series': series
            },
            'class_name': class_name
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get type stats', error=str(e)))

# 大屏端API（管理员权限）
@app.route('/api/admin/overview', methods=['GET'])
@jwt_required()
def get_admin_overview():
    """总览卡片"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为管理员
        if user['role'] != 'admin':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 获取总览数据
        db = get_db()
        cursor = db.cursor()
        
        # 1. 总用户数
        cursor.execute('SELECT COUNT(*) as total_users FROM user WHERE role = "student"')
        total_users = cursor.fetchone()['total_users']
        
        # 2. 今日预警数
        cursor.execute('SELECT COUNT(*) as today_warnings FROM warning WHERE created_at >= date("now")')
        today_warnings = cursor.fetchone()['today_warnings']
        
        # 3. 本周预警数
        cursor.execute('SELECT COUNT(*) as weekly_warnings FROM warning WHERE created_at >= date("now", "-7 days")')
        weekly_warnings = cursor.fetchone()['weekly_warnings']
        
        # 4. 高风险用户数
        cursor.execute('''
        SELECT COUNT(DISTINCT q.user_id) as high_risk_users
        FROM query_log q
        JOIN user u ON q.user_id = u.id
        WHERE u.role = "student" AND q.risk_score > 60
        ''')
        high_risk_users = cursor.fetchone()['high_risk_users']
        
        # 5. 今日查询数
        cursor.execute('SELECT COUNT(*) as today_queries FROM query_log WHERE created_at >= date("now")')
        today_queries = cursor.fetchone()['today_queries']
        
        db.close()
        
        return jsonify({
            'success': True,
            'overview': {
                'total_users': total_users,
                'today_warnings': today_warnings,
                'weekly_warnings': weekly_warnings,
                'high_risk_users': high_risk_users,
                'today_queries': today_queries
            }
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get overview data', error=str(e)))

@app.route('/api/admin/recent-warnings', methods=['GET'])
@jwt_required()
def get_admin_recent_warnings():
    """最新10条预警"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为管理员
        if user['role'] != 'admin':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 获取最新10条预警
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
        SELECT w.id, w.user_id, u.username, u.name, u.class_name, w.reason, w.risk_score, w.status, w.created_at
        FROM warning w
        JOIN user u ON w.user_id = u.id
        ORDER BY w.created_at DESC
        LIMIT 10
        ''')
        warnings = cursor.fetchall()
        
        warning_list = []
        for warning in warnings:
            warning_list.append({
                'id': warning['id'],
                'user_id': warning['user_id'],
                'username': warning['username'],
                'name': warning['name'],
                'class_name': warning['class_name'],
                'reason': warning['reason'],
                'risk_score': warning['risk_score'],
                'status': warning['status'],
                'created_at': warning['created_at']
            })
        
        db.close()
        
        return jsonify({
            'success': True,
            'warnings': warning_list
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get recent warnings', error=str(e)))

@app.route('/api/admin/trends/daily', methods=['GET'])
@jwt_required()
def get_admin_daily_trends():
    """近7天趋势"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为管理员
        if user['role'] != 'admin':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 获取近7天趋势数据
        db = get_db()
        cursor = db.cursor()
        
        # 生成最近7天的日期
        import datetime
        today = datetime.date.today()
        dates = [(today - datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
        
        # 获取每天的预警数量
        daily_warnings = []
        for date in dates:
            cursor.execute('''
            SELECT COUNT(*) as count
            FROM warning
            WHERE date(created_at) = ?
            ''', (date,))
            count = cursor.fetchone()['count']
            daily_warnings.append(count)
        
        # 获取每天的查询数量
        daily_queries = []
        for date in dates:
            cursor.execute('''
            SELECT COUNT(*) as count
            FROM query_log
            WHERE date(created_at) = ?
            ''', (date,))
            count = cursor.fetchone()['count']
            daily_queries.append(count)
        
        db.close()
        
        return jsonify({
            'success': True,
            'trends': {
                'categories': dates,
                'series': [
                    {'name': '预警数', 'data': daily_warnings},
                    {'name': '查询数', 'data': daily_queries}
                ]
            }
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get daily trends', error=str(e)))

@app.route('/api/admin/trends/types', methods=['GET'])
@jwt_required()
def get_admin_type_trends():
    """诈骗类型TOP5"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为管理员
        if user['role'] != 'admin':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 获取诈骗类型TOP5
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
        SELECT result as fraud_type, COUNT(*) as count
        FROM query_log
        WHERE result != 'URL检测'
        GROUP BY result
        ORDER BY count DESC
        LIMIT 5
        ''')
        type_stats = cursor.fetchall()
        
        categories = []
        series = []
        for item in type_stats:
            categories.append(item['fraud_type'])
            series.append(item['count'])
        
        db.close()
        
        return jsonify({
            'success': True,
            'trends': {
                'categories': categories,
                'series': [
                    {'name': '诈骗类型', 'data': series}
                ]
            }
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get type trends', error=str(e)))

@app.route('/api/admin/trends/colleges', methods=['GET'])
@jwt_required()
def get_admin_college_trends():
    """学院排行"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为管理员
        if user['role'] != 'admin':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 获取学院排行
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
        SELECT u.class_name as college, COUNT(*) as warning_count
        FROM warning w
        JOIN user u ON w.user_id = u.id
        GROUP BY u.class_name
        ORDER BY warning_count DESC
        ''')
        college_stats = cursor.fetchall()
        
        categories = []
        series = []
        for item in college_stats:
            categories.append(item['college'])
            series.append(item['warning_count'])
        
        db.close()
        
        return jsonify({
            'success': True,
            'trends': {
                'categories': categories,
                'series': [
                    {'name': '预警数', 'data': series}
                ]
            }
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get college trends', error=str(e)))

@app.route('/api/admin/heatmap', methods=['GET'])
@jwt_required()
def get_admin_heatmap():
    """各区域案发数量（宿舍楼/教学楼）"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为管理员
        if user['role'] != 'admin':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 模拟热力图数据
        # 这里使用模拟数据，因为数据库中没有存储区域信息
        heatmap_data = [
            # 宿舍楼
            {"name": "1号楼", "value": 12, "type": "宿舍楼"},
            {"name": "2号楼", "value": 8, "type": "宿舍楼"},
            {"name": "3号楼", "value": 15, "type": "宿舍楼"},
            {"name": "4号楼", "value": 5, "type": "宿舍楼"},
            {"name": "5号楼", "value": 10, "type": "宿舍楼"},
            {"name": "6号楼", "value": 7, "type": "宿舍楼"},
            {"name": "7号楼", "value": 13, "type": "宿舍楼"},
            {"name": "8号楼", "value": 6, "type": "宿舍楼"},
            
            # 教学楼
            {"name": "A楼", "value": 9, "type": "教学楼"},
            {"name": "B楼", "value": 11, "type": "教学楼"},
            {"name": "C楼", "value": 14, "type": "教学楼"},
            {"name": "D楼", "value": 4, "type": "教学楼"},
            {"name": "E楼", "value": 8, "type": "教学楼"}
        ]
        
        return jsonify({
            'success': True,
            'heatmap': heatmap_data
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get heatmap data', error=str(e)))

@app.route('/api/admin/portrait', methods=['GET'])
@jwt_required()
def get_admin_portrait():
    """高危人群特征"""
    try:
        current_user = get_jwt_identity()
        user = get_user_by_username(current_user)
        if not user:
            return jsonify(format_response(False, 'User not found')), 404
        
        # 检查用户是否为管理员
        if user['role'] != 'admin':
            return jsonify(format_response(False, 'Permission denied')), 403
        
        # 获取高危人群特征数据
        db = get_db()
        cursor = db.cursor()
        
        # 1. 按班级统计高风险用户
        cursor.execute('''
        SELECT u.class_name, COUNT(DISTINCT q.user_id) as high_risk_count
        FROM query_log q
        JOIN user u ON q.user_id = u.id
        WHERE u.role = "student" AND q.risk_score > 60
        GROUP BY u.class_name
        ORDER BY high_risk_count DESC
        ''')
        class_stats = cursor.fetchall()
        
        # 2. 按诈骗类型统计
        cursor.execute('''
        SELECT result as fraud_type, COUNT(*) as count
        FROM query_log
        WHERE risk_score > 60
        GROUP BY result
        ORDER BY count DESC
        ''')
        fraud_type_stats = cursor.fetchall()
        
        # 3. 高风险用户预警次数统计
        cursor.execute('''
        SELECT w.user_id, u.username, u.name, u.class_name, COUNT(*) as warning_count
        FROM warning w
        JOIN user u ON w.user_id = u.id
        WHERE u.role = "student"
        GROUP BY w.user_id
        ORDER BY warning_count DESC
        LIMIT 10
        ''')
        user_warning_stats = cursor.fetchall()
        
        db.close()
        
        # 整理数据
        class_data = []
        for item in class_stats:
            class_data.append({"class_name": item['class_name'], "count": item['high_risk_count']})
        
        fraud_type_data = []
        for item in fraud_type_stats:
            fraud_type_data.append({"type": item['fraud_type'], "count": item['count']})
        
        user_warning_data = []
        for item in user_warning_stats:
            user_warning_data.append({
                "username": item['username'],
                "name": item['name'],
                "class_name": item['class_name'],
                "warning_count": item['warning_count']
            })
        
        return jsonify({
            'success': True,
            'portrait': {
                'class_distribution': class_data,
                'fraud_type_distribution': fraud_type_data,
                'high_risk_users': user_warning_data
            }
        })
    except Exception as e:
        return jsonify(format_response(False, 'Failed to get portrait data', error=str(e)))

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify(format_response(False, 'Resource not found')), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return jsonify(format_response(False, 'Internal server error')), 500

if __name__ == '__main__':
    # 运行应用
    app.run(debug=True)
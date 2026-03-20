from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import get_db
from werkzeug.security import generate_password_hash, check_password_hash

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No input data provided'}), 400
        
        # 检查必要字段
        required_fields = ['username', 'email', 'password', 'name']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # 检查用户名是否已存在
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM user WHERE username = ?', (data['username'],))
        if cursor.fetchone():
            db.close()
            return jsonify({'error': 'Username already exists'}), 400
        
        # 检查邮箱是否已存在
        cursor.execute('SELECT * FROM user WHERE email = ?', (data['email'],))
        if cursor.fetchone():
            db.close()
            return jsonify({'error': 'Email already exists'}), 400
        
        # 创建新用户
        hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
        cursor.execute('''
        INSERT INTO user (username, email, password, name, role, class_name)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['username'], data['email'], hashed_password, data['name'], 'student', '计算机科学与技术1班'))
        
        db.commit()
        db.close()
        
        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No input data provided'}), 400
        
        # 检查必要字段
        if 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Missing username or password'}), 400
        
        # 查找用户
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM user WHERE username = ?', (data['username'],))
        user = cursor.fetchone()
        db.close()
        
        if not user:
            return jsonify({'error': 'Invalid username or password'}), 401
        
        # 验证密码
        if not check_password_hash(user['password'], data['password']):
            return jsonify({'error': 'Invalid username or password'}), 401
        
        # 创建访问令牌
        access_token = create_access_token(identity=user['username'])
        
        return jsonify({
            'access_token': access_token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'name': user['name'],
                'role': user['role'],
                'class_name': user['class_name']
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    """受保护的路由"""
    try:
        current_user = get_jwt_identity()
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM user WHERE username = ?', (current_user,))
        user = cursor.fetchone()
        db.close()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'message': 'Protected route accessed',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email']
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

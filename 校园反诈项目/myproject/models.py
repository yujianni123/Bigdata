import sqlite3
import os
from datetime import datetime

# 数据库文件路径
DB_FILE = os.path.join(os.path.dirname(__file__), 'app.db')

def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        role TEXT DEFAULT 'student',
        class_name TEXT DEFAULT '计算机科学与技术1班',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 为用户表添加索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_username ON user(username)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_role ON user(role)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_class_name ON user(class_name)')
    
    # 创建诈骗案例表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fraud_case (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id TEXT UNIQUE NOT NULL,
        case_type TEXT NOT NULL,
        description TEXT NOT NULL,
        loss_amount REAL NOT NULL,
        occurred_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 为诈骗案例表添加索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fraud_case_case_id ON fraud_case(case_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fraud_case_case_type ON fraud_case(case_type)')
    
    # 创建查询日志表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS query_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        result TEXT NOT NULL,
        risk_score INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user (id)
    )
    ''')
    
    # 为查询日志表添加索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_query_log_user_id ON query_log(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_query_log_created_at ON query_log(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_query_log_risk_score ON query_log(risk_score)')
    
    # 创建预警表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS warning (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        risk_score INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        handler_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user (id),
        FOREIGN KEY (handler_id) REFERENCES user (id)
    )
    ''')
    
    # 为预警表添加索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_warning_user_id ON warning(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_warning_status ON warning(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_warning_created_at ON warning(created_at)')
    
    # 创建反馈表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        type TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user (id)
    )
    ''')
    
    # 为反馈表添加索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback(status)')
    
    # 创建重点关注表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS focus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES user (id),
        FOREIGN KEY (student_id) REFERENCES user (id),
        UNIQUE (teacher_id, student_id)
    )
    ''')
    
    # 为重点关注表添加索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_focus_teacher_id ON focus(teacher_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_focus_student_id ON focus(student_id)')
    
    # 插入示例用户
    try:
        # 导入密码哈希函数
        from werkzeug.security import generate_password_hash
        
        # 生成密码哈希
        admin_hash = generate_password_hash('admin123', method='pbkdf2:sha256')
        test_hash = generate_password_hash('test123', method='pbkdf2:sha256')
        teacher_hash = generate_password_hash('teacher123', method='pbkdf2:sha256')
        
        cursor.execute('''
        INSERT INTO user (username, email, password, name, role, class_name) VALUES
        ('admin', 'admin@example.com', ?, '管理员', 'admin', '计算机科学与技术1班'),
        ('test', 'test@example.com', ?, '测试用户', 'student', '计算机科学与技术1班'),
        ('teacher', 'teacher@example.com', ?, '教师', 'teacher', '计算机科学与技术1班')
        ''', (admin_hash, test_hash, teacher_hash))
    except sqlite3.IntegrityError:
        # 用户已存在，跳过
        pass
    
    # 插入示例诈骗案例
    try:
        cursor.execute('''
        INSERT INTO fraud_case (case_id, case_type, description, loss_amount, occurred_at) VALUES
        ('FC001', '刷单返利', '受害人在网上看到刷单兼职广告，按照要求完成刷单任务后，对方以系统故障为由拒绝返款。', 5000.0, '2024-01-15 14:30:00'),
        ('FC002', '冒充客服', '受害人接到冒充淘宝客服的电话，称其购买的商品存在质量问题，需要退款，诱导受害人提供银行卡信息。', 12000.0, '2024-01-20 10:15:00'),
        ('FC003', '虚假贷款', '受害人在网上申请贷款，对方以需要缴纳保证金为由，骗取受害人转账。', 8000.0, '2024-01-25 16:45:00'),
        ('FC004', '网络投资', '受害人在社交媒体上看到高收益投资广告，点击链接后被诱导投资虚拟货币，最终血本无归。', 20000.0, '2024-02-01 09:30:00'),
        ('FC005', '冒充熟人', '受害人收到冒充朋友的微信消息，称急需用钱，受害人转账后发现被骗。', 3000.0, '2024-02-05 18:20:00')
        ''')
    except sqlite3.IntegrityError:
        # 案例已存在，跳过
        pass
    
    conn.commit()
    conn.close()

def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def add_warning(user_id, reason, risk_score, handler_id=None):
    """添加预警记录"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO warning (user_id, reason, risk_score, status, handler_id)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, reason, risk_score, 'pending', handler_id))
    conn.commit()
    conn.close()

def get_user_warnings(user_id):
    """获取用户的预警记录"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM warning WHERE user_id = ? ORDER BY created_at DESC
    ''', (user_id,))
    warnings = cursor.fetchall()
    conn.close()
    return warnings

def get_class_warnings(class_name):
    """获取班级的预警记录"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT w.*, u.username, u.class_name 
    FROM warning w 
    JOIN user u ON w.user_id = u.id 
    WHERE u.class_name = ? 
    ORDER BY w.created_at DESC
    ''', (class_name,))
    warnings = cursor.fetchall()
    conn.close()
    return warnings

def handle_warning(warning_id, handler_id, status='handled'):
    """处理预警"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE warning SET status = ?, handler_id = ? WHERE id = ?
    ''', (status, handler_id, warning_id))
    conn.commit()
    conn.close()

def get_user_by_username(username):
    """根据用户名获取用户信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_query_count(user_id, hours=24):
    """获取用户在指定时间内的查询次数"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT COUNT(*) FROM query_log 
    WHERE user_id = ? AND created_at >= datetime('now', '-' || ? || ' hours')
    ''', (user_id, hours))
    count = cursor.fetchone()[0]
    conn.close()
    return count

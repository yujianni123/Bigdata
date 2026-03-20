import sys
import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

# 数据库文件路径
DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.db')

def init_db():
    """初始化数据库表结构"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        class_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建案例表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        keywords TEXT,
        date TIMESTAMP NOT NULL
    )
    ''')
    
    # 创建查询记录表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS query_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        result TEXT,
        risk_score REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user (id)
    )
    ''')
    
    # 创建预警表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS warning (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        risk_score REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        handler_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user (id),
        FOREIGN KEY (handler_id) REFERENCES user (id)
    )
    ''')
    
    # 创建反馈表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print('数据库表结构创建完成')

def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_sample_data():
    """初始化示例数据"""
    db = get_db()
    cursor = db.cursor()
    
    # 检查是否已有用户
    cursor.execute('SELECT COUNT(*) FROM user')
    if cursor.fetchone()[0] == 0:
        # 添加默认用户
        admin_user = (
            'admin',
            generate_password_hash('admin123', method='pbkdf2:sha256'),
            'admin',
            '管理员'
        )
        cursor.execute('''
        INSERT INTO user (username, password_hash, role, class_name)
        VALUES (?, ?, ?, ?)
        ''', admin_user)
        
        # 添加普通用户
        test_user = (
            'test',
            generate_password_hash('test123', method='pbkdf2:sha256'),
            'user',
            '计算机科学与技术1班'
        )
        cursor.execute('''
        INSERT INTO user (username, password_hash, role, class_name)
        VALUES (?, ?, ?, ?)
        ''', test_user)
        print('示例用户添加完成')
    
    # 检查是否已有案例
    cursor.execute('SELECT COUNT(*) FROM cases')
    if cursor.fetchone()[0] == 0:
        # 添加示例案例
        sample_cases = [
            (
                '刷单返利',
                '受害人在网上看到刷单兼职广告，按照要求完成刷单任务后，对方以系统故障为由拒绝返款。',
                5000.0,
                '刷单,返利,兼职',
                '2024-01-15 14:30:00'
            ),
            (
                '冒充客服',
                '受害人接到冒充淘宝客服的电话，称其购买的商品存在质量问题，需要退款，诱导受害人提供银行卡信息。',
                12000.0,
                '客服,退款,银行卡',
                '2024-01-20 10:15:00'
            ),
            (
                '虚假贷款',
                '受害人在网上申请贷款，对方以需要缴纳保证金为由，骗取受害人转账。',
                8000.0,
                '贷款,保证金,转账',
                '2024-01-25 16:45:00'
            )
        ]
        
        for case_data in sample_cases:
            cursor.execute('''
            INSERT INTO cases (type, description, amount, keywords, date)
            VALUES (?, ?, ?, ?, ?)
            ''', case_data)
        print('示例案例添加完成')
    
    db.commit()
    db.close()
    print('数据库初始化完成')

if __name__ == '__main__':
    init_db()
    init_sample_data()

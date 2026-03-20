import sys
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from models_sqlalchemy import Base, User, Case, QueryLog, Warning, Feedback
from sqlalchemy.orm import sessionmaker

def init_sqlalchemy_db():
    """初始化SQLAlchemy数据库"""
    # 创建数据库引擎
    engine = create_engine('sqlite:///app_sqlalchemy.db')
    
    # 创建所有表
    Base.metadata.create_all(engine)
    print('数据库表创建完成')
    
    # 创建会话
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 检查是否已有用户
        if not session.query(User).first():
            # 添加默认用户
            admin_user = User(
                username='admin',
                password_hash=generate_password_hash('admin123', method='pbkdf2:sha256'),
                role='admin',
                class_name='管理员'
            )
            session.add(admin_user)
            
            # 添加普通用户
            test_user = User(
                username='test',
                password_hash=generate_password_hash('test123', method='pbkdf2:sha256'),
                role='user',
                class_name='计算机科学与技术1班'
            )
            session.add(test_user)
            print('示例用户添加完成')
        
        # 检查是否已有案例
        if not session.query(Case).first():
            # 添加示例案例
            sample_cases = [
                {
                    'type': '刷单返利',
                    'description': '受害人在网上看到刷单兼职广告，按照要求完成刷单任务后，对方以系统故障为由拒绝返款。',
                    'amount': 5000.0,
                    'keywords': '刷单,返利,兼职',
                    'date': datetime(2024, 1, 15, 14, 30, 0)
                },
                {
                    'type': '冒充客服',
                    'description': '受害人接到冒充淘宝客服的电话，称其购买的商品存在质量问题，需要退款，诱导受害人提供银行卡信息。',
                    'amount': 12000.0,
                    'keywords': '客服,退款,银行卡',
                    'date': datetime(2024, 1, 20, 10, 15, 0)
                },
                {
                    'type': '虚假贷款',
                    'description': '受害人在网上申请贷款，对方以需要缴纳保证金为由，骗取受害人转账。',
                    'amount': 8000.0,
                    'keywords': '贷款,保证金,转账',
                    'date': datetime(2024, 1, 25, 16, 45, 0)
                }
            ]
            
            for case_data in sample_cases:
                case = Case(**case_data)
                session.add(case)
            print('示例案例添加完成')
        
        # 提交事务
        session.commit()
        print('数据库初始化完成')
    except Exception as e:
        print(f'初始化数据库时出错: {e}')
        session.rollback()
    finally:
        session.close()

if __name__ == '__main__':
    init_sqlalchemy_db()

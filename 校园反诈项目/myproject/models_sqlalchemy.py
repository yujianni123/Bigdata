from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    """用户表"""
    __tablename__ = 'user'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default='user')
    class_name = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    query_logs = relationship('QueryLog', back_populates='user')
    warnings = relationship('Warning', back_populates='user')
    feedbacks = relationship('Feedback', back_populates='user')
    handled_warnings = relationship('Warning', back_populates='handler', foreign_keys='Warning.handler_id')

class Case(Base):
    """案例表"""
    __tablename__ = 'case'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    keywords = Column(Text, nullable=True)
    date = Column(DateTime, nullable=False)

class QueryLog(Base):
    """查询记录表"""
    __tablename__ = 'query_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    content = Column(Text, nullable=False)
    result = Column(Text, nullable=True)
    risk_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    user = relationship('User', back_populates='query_logs')

class Warning(Base):
    """预警表"""
    __tablename__ = 'warning'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    reason = Column(Text, nullable=False)
    risk_score = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default='pending')
    handler_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    user = relationship('User', back_populates='warnings', foreign_keys=[user_id])
    handler = relationship('User', back_populates='handled_warnings', foreign_keys=[handler_id])

class Feedback(Base):
    """反馈表"""
    __tablename__ = 'feedback'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    content = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default='pending')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    user = relationship('User', back_populates='feedbacks')

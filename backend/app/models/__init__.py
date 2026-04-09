"""数据库模型"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    phone = Column(String, unique=True, index=True)
    name = Column(String)
    role = Column(String)  # student, parent
    grade = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DailyCheckin(Base):
    """每日打卡模型"""
    __tablename__ = "daily_checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    checkin_date = Column(DateTime, default=datetime.now)
    emotion_score = Column(Integer)  # 1-5
    sleep_hours = Column(Float)
    study_hours = Column(Float)
    social_score = Column(Integer)  # 1-5
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class PsychAssessment(Base):
    """心理测评模型"""
    __tablename__ = "psych_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    assessment_type = Column(String)
    answers = Column(Text)  # JSON
    total_score = Column(Integer)
    risk_level = Column(String)  # low, medium, high
    result = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class ChatMessage(Base):
    """聊天记录模型"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    role = Column(String)  # student, parent
    session_id = Column(String, nullable=True)
    content = Column(Text)
    is_ai = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)


class CrisisAlert(Base):
    """危机预警模型"""
    __tablename__ = "crisis_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    alert_type = Column(String)  # crisis, emotion, behavior
    content = Column(Text)
    is_read = Column(Boolean, default=False)
    is_handled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)


class KnowledgeDocument(Base):
    """知识库文档模型"""
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String)
    content = Column(Text)
    category = Column(String, index=True)
    tags = Column(String, nullable=True)  # JSON array
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
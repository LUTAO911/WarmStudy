"""同步数据库连接（用于工具函数）"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import get_settings
from app.models import Base
import os

settings = get_settings()

_sync_engine = None
_sync_session = None


def get_sync_engine():
    """获取同步数据库引擎"""
    global _sync_engine
    if _sync_engine is None:
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        database_url = settings.DATABASE_URL.replace("+aiosqlite", "")
        _sync_engine = create_engine(
            database_url,
            echo=settings.DEBUG,
            future=True,
        )
    return _sync_engine


def get_sync_session():
    """获取同步会话"""
    global _sync_session
    if _sync_session is None:
        engine = get_sync_engine()
        _sync_session = sessionmaker(bind=engine, expire_on_commit=False)
    return _sync_session


def get_db():
    """获取数据库会话（同步版本）"""
    session = get_sync_session()
    return session()


def init_sync_db():
    """初始化数据库（同步版本）"""
    engine = get_sync_engine()
    Base.metadata.create_all(engine)

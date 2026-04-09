"""数据库连接管理"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import get_settings
from app.models import Base
import os

settings = get_settings()


def get_database_url() -> str:
    """获取数据库URL"""
    return settings.DATABASE_URL


def ensure_data_dir():
    """确保数据目录存在"""
    os.makedirs(settings.DATA_DIR, exist_ok=True)


_engine = None
_async_session = None


def get_engine():
    """获取数据库引擎"""
    global _engine
    if _engine is None:
        ensure_data_dir()
        _engine = create_async_engine(
            get_database_url(),
            echo=settings.DEBUG,
            future=True,
        )
    return _engine


def get_session_factory():
    """获取会话工厂"""
    global _async_session
    if _async_session is None:
        engine = get_engine()
        _async_session = sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        return session


async def init_db():
    """初始化数据库"""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """关闭数据库连接"""
    global _engine, _async_session
    if _engine:
        await _engine.dispose()
        _engine = None
        _async_session = None
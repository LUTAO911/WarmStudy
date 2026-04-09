"""DB模块"""
from app.db.base import get_db, init_db, close_db
from app.db.sync import get_db as get_sync_db, init_sync_db

__all__ = [
    "get_db",
    "init_db",
    "close_db",
    "get_sync_db",
    "init_sync_db",
]
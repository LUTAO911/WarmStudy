"""应用配置"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """应用配置"""

    APP_NAME: str = "WarmStudy AI"
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/warmchat.db"
    DATA_DIR: str = "./data"

    MINIMAX_API_KEY: str = ""
    MINIMAX_BASE_URL: str = "https://api.minimaxi.com/anthropic/v1/messages"
    MINIMAX_MODEL: str = "MiniMax-M2.7"

    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-turbo"
    QWEN_EMBEDDING_MODEL: str = "text-embedding-v3"

    KNOWLEDGE_BASE_PATH: str = "./knowledge"
    VECTOR_DB_PATH: str = "./data/vector_db"

    SECRET_KEY: str = "nuanxuebang-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    CORS_ORIGINS: list = [
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "https://servicewechat.com",
        "https://miniprogram://",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def get_settings() -> Settings:
    return settings
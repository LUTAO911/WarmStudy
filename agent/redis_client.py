# -*- coding: utf-8 -*-
"""
redis_client.py - Redis 连接池 + 缓存抽象层
支持：答案缓存、会话存储、LLM 响应缓存
"""
import os
import json
import time
import hashlib
from typing import Optional, Any, Dict
try:
    import redis
except ImportError:
    redis = None


class RedisClient:
    _instance: Optional["RedisClient"] = None
    _lock_instance = None

    def __new__(cls) -> "RedisClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self._pool: Optional[redis.ConnectionPool] = None
        self._client = None
        self._connected = False
        self._connect()

    def _connect(self) -> None:
        try:
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))
            db = int(os.getenv("REDIS_DB", "0"))
            password = os.getenv("REDIS_PASSWORD") or None

            self._pool = redis.ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                max_connections=50,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )
            self._client = redis.Redis(connection_pool=self._pool)
            self._client.ping()
            self._connected = True
            print(f"[Redis] Connected to {host}:{port}")
        except Exception as e:
            print(f"[Redis] Connection failed: {e}, running without Redis")
            self._connected = False

    @property
    def client(self) -> object:
        return self._client

    @property
    def is_connected(self) -> bool:
        if not self._connected:
            return False
        try:
            if self._client:
                self._client.ping()
                return True
        except Exception:
            self._connected = False
        return False

    # ── 答案缓存（LRU TTL）───────────────────────────────────
    def get_cached_answer(self, query: str, session_id: str) -> Optional[str]:
        """答案缓存查询，TTL 内返回缓存内容"""
        if not self.is_connected:
            return None
        try:
            key = self._make_key("answer", query, session_id)
            val = self._client.get(key)
            return val
        except Exception:
            return None

    def set_cached_answer(self, query: str, session_id: str, answer: str,
                          ttl: Optional[int] = None) -> bool:
        """写入答案缓存"""
        if not self.is_connected:
            return False
        try:
            key = self._make_key("answer", query, session_id)
            ttl = ttl or int(os.getenv("REDIS_CACHE_TTL", "300"))
            self._client.setex(key, ttl, answer)
            return True
        except Exception:
            return False

    # ── LLM 响应缓存（防重复调用）─────────────────────────────
    def get_llm_cache(self, prompt_hash: str) -> Optional[Dict]:
        """LLM 响应缓存，同 prompt_hash 在 TTL 内返回"""
        if not self.is_connected:
            return None
        try:
            key = f"llm_cache:{prompt_hash}"
            val = self._client.get(key)
            return json.loads(val) if val else None
        except Exception:
            return None

    def set_llm_cache(self, prompt_hash: str, response: Dict,
                       ttl: int = 600) -> bool:
        """LLM 响应缓存"""
        if not self.is_connected:
            return False
        try:
            key = f"llm_cache:{prompt_hash}"
            self._client.setex(key, ttl, json.dumps(response))
            return True
        except Exception:
            return False

    # ── 会话存储 ────────────────────────────────────────────
    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话数据"""
        if not self.is_connected:
            return None
        try:
            key = f"session:{session_id}"
            val = self._client.get(key)
            return json.loads(val) if val else None
        except Exception:
            return None

    def set_session(self, session_id: str, data: Dict, ttl: int = 3600) -> bool:
        """存储会话数据"""
        if not self.is_connected:
            return False
        try:
            key = f"session:{session_id}"
            self._client.setex(key, ttl, json.dumps(data))
            return True
        except Exception:
            return False

    # ── 缓存统计 ────────────────────────────────────────────
    def get_cache_stats(self) -> Dict[str, Any]:
        """缓存命中率统计"""
        if not self.is_connected:
            return {"connected": False}
        try:
            info = self._client.info("stats")
            return {
                "connected": True,
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "total_commands": info.get("total_commands_processed", 0),
            }
        except Exception:
            return {"connected": False}

    def _make_key(self, prefix: str, query: str, session_id: str) -> str:
        h = hashlib.sha256(f"{session_id}:{query}".encode()).hexdigest()[:32]
        return f"cache:{prefix}:{h}"


def get_redis() -> RedisClient:
    return RedisClient()

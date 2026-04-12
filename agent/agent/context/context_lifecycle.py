"""
Context Lifecycle - 上下文生命周期管理
定义上下文数据的创建、使用、过期、销毁流程
"""
import time
import threading
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum

class ContextScope(Enum):
    """上下文作用域"""
    MESSAGE = "message"
    SESSION = "session"
    USER = "user"
    GLOBAL = "global"

class ContextTTL(Enum):
    """上下文存活时间"""
    EPHEMERAL = 60
    SHORT = 300
    MEDIUM = 1800
    LONG = 3600
    PERSISTENT = 86400

@dataclass
class ContextEntry:
    """上下文条目"""
    id: str
    key: str
    value: Any
    scope: ContextScope
    ttl: ContextTTL
    created_at: float
    last_accessed: float
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """检查是否过期"""
        age = time.time() - self.created_at
        ttl_seconds = {
            ContextTTL.EPHEMERAL: 60,
            ContextTTL.SHORT: 300,
            ContextTTL.MEDIUM: 1800,
            ContextTTL.LONG: 3600,
            ContextTTL.PERSISTENT: 86400,
        }.get(self.ttl, 300)
        return age > ttl_seconds

class ContextLifecycle:
    """
    上下文生命周期管理器
    
    职责：
    1. 管理不同作用域的上下文
    2. 自动过期清理
    3. 访问追踪
    """

    def __init__(self, cleanup_interval: int = 60):
        self._contexts: Dict[ContextScope, Dict[str, ContextEntry]] = {
            scope: {} for scope in ContextScope
        }
        self._lock = threading.RLock()
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
        self._cleanup_callbacks: List[Callable] = []
        self._thread_local = threading.local()

    def set(
        self,
        key: str,
        value: Any,
        scope: ContextScope,
        ttl: ContextTTL = ContextTTL.SHORT,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> ContextEntry:
        """
        设置上下文
        """
        scope_key = self._get_scope_key(scope, session_id, user_id)
        entry_id = f"{scope_key}:{key}"

        entry = ContextEntry(
            id=entry_id,
            key=key,
            value=value,
            scope=scope,
            ttl=ttl,
            created_at=time.time(),
            last_accessed=time.time()
        )

        with self._lock:
            self._contexts[scope][entry_id] = entry

        return entry

    def get(
        self,
        key: str,
        scope: ContextScope,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[Any]:
        """
        获取上下文
        """
        scope_key = self._get_scope_key(scope, session_id, user_id)
        entry_id = f"{scope_key}:{key}"

        with self._lock:
            entry = self._contexts[scope].get(entry_id)

            if entry is None:
                return None

            if entry.is_expired():
                del self._contexts[scope][entry_id]
                return None

            entry.last_accessed = time.time()
            entry.access_count += 1

            return entry.value

    def delete(
        self,
        key: str,
        scope: ContextScope,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """删除上下文"""
        scope_key = self._get_scope_key(scope, session_id, user_id)
        entry_id = f"{scope_key}:{key}"

        with self._lock:
            if entry_id in self._contexts[scope]:
                del self._contexts[scope][entry_id]
                return True
        return False

    def clear_scope(
        self,
        scope: ContextScope,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> int:
        """清除某个作用域的所有上下文"""
        with self._lock:
            if scope == ContextScope.SESSION and session_id:
                scope_key = f"session:{session_id}"
                keys_to_delete = [
                    k for k in self._contexts[scope].keys()
                    if k.startswith(scope_key)
                ]
                for k in keys_to_delete:
                    del self._contexts[scope][k]
                return len(keys_to_delete)
            elif scope == ContextScope.USER and user_id:
                scope_key = f"user:{user_id}"
                keys_to_delete = [
                    k for k in self._contexts[scope].keys()
                    if k.startswith(scope_key)
                ]
                for k in keys_to_delete:
                    del self._contexts[scope][k]
                return len(keys_to_delete)
            else:
                count = len(self._contexts[scope])
                self._contexts[scope].clear()
                return count

    def cleanup_expired(self) -> int:
        """清理所有过期的上下文"""
        current_time = time.time()

        if current_time - self._last_cleanup < self._cleanup_interval:
            return 0

        with self._lock:
            total_cleaned = 0

            for scope, entries in self._contexts.items():
                expired_keys = [
                    k for k, entry in entries.items()
                    if entry.is_expired()
                ]

                for k in expired_keys:
                    self._trigger_cleanup_callbacks(entries[k])
                    del entries[k]
                    total_cleaned += 1

            self._last_cleanup = current_time

            return total_cleaned

    def register_cleanup_callback(self, callback: Callable) -> None:
        """注册清理回调"""
        self._cleanup_callbacks.append(callback)

    def _get_scope_key(
        self,
        scope: ContextScope,
        session_id: Optional[str],
        user_id: Optional[str]
    ) -> str:
        """生成作用域键"""
        if scope == ContextScope.MESSAGE:
            thread_id = id(self._thread_local)
            return f"msg:{thread_id}"
        elif scope == ContextScope.SESSION:
            return f"session:{session_id or 'default'}"
        elif scope == ContextScope.USER:
            return f"user:{user_id or 'anonymous'}"
        else:
            return "global"

    def _trigger_cleanup_callbacks(self, entry: ContextEntry) -> None:
        """触发清理回调"""
        for callback in self._cleanup_callbacks:
            try:
                callback(entry)
            except Exception:
                pass

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = sum(len(entries) for entries in self._contexts.values())
            return {
                "total_entries": total,
                "by_scope": {
                    scope.value: len(entries)
                    for scope, entries in self._contexts.items()
                }
            }

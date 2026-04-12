"""
Cache Manager - 多级缓存管理器
L1: 内存LRU / L2: Redis / L3: 持久化
版本: v5.0
"""
import time
import json
import hashlib
import threading
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List, Callable
from pathlib import Path
from collections import OrderedDict
from enum import Enum

# ========== 缓存层级 ==========

class CacheLevel(Enum):
    """缓存层级"""
    L1_MEMORY = "l1_memory"     # 进程内存LRU
    L2_REDIS = "l2_redis"       # Redis分布式缓存
    L3_PERSISTENT = "l3_persistent"  # 持久化存储

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    level: CacheLevel
    created_at: float = field(default_factory=time.time)
    access_count: int = 1
    last_accessed: float = field(default_factory=time.time)
    ttl: Optional[float] = None  # 生存时间（秒）
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def touch(self) -> None:
        """更新访问时间"""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    l1_hits: int = 0
    l2_hits: int = 0
    l3_hits: int = 0
    evictions: int = 0
    total_size_bytes: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{self.hit_rate * 100:.1f}%",
            "l1_hits": self.l1_hits,
            "l2_hits": self.l2_hits,
            "l3_hits": self.l3_hits,
            "evictions": self.evictions,
            "total_size_mb": self.total_size_bytes / (1024 * 1024),
        }


# ========== L1 内存缓存 ==========

class L1MemoryCache:
    """
    L1缓存 - 进程内存LRU

    特点：
    - 最快（纳秒级）
    - 单进程共享
    - 有限容量
    - 无持久化
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[float] = 3600
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._size_bytes = 0

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # 检查过期
            if entry.is_expired():
                del self._cache[key]
                self._size_bytes -= entry.size_bytes
                return None

            # 移到末尾（最近使用）
            self._cache.move_to_end(key)
            entry.touch()

            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        size_hint: int = 0
    ) -> None:
        """设置缓存"""
        with self._lock:
            # 计算大小
            value_str = str(value)
            size = size_hint or len(value_str.encode())

            # 如果已存在，减去旧大小
            if key in self._cache:
                old_entry = self._cache[key]
                self._size_bytes -= old_entry.size_bytes

            # LRU淘汰
            while len(self._cache) >= self.max_size:
                oldest_key, oldest_entry = self._cache.popitem(last=False)
                self._size_bytes -= oldest_entry.size_bytes
                break  # 只淘汰一个

            # 添加新条目
            entry = CacheEntry(
                key=key,
                value=value,
                level=CacheLevel.L1_MEMORY,
                ttl=ttl or self.default_ttl,
                size_bytes=size
            )

            self._cache[key] = entry
            self._size_bytes += size

    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._size_bytes -= entry.size_bytes
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._size_bytes = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "level": CacheLevel.L1_MEMORY.value,
                "entries": len(self._cache),
                "max_size": self.max_size,
                "size_bytes": self._size_bytes,
                "size_mb": self._size_bytes / (1024 * 1024),
            }


# ========== L3 持久化缓存 ==========

class L3PersistentCache:
    """
    L3缓存 - 持久化存储

    特点：
    - 慢（毫秒级）
    - 跨进程共享
    - 大容量
    - 持久化到磁盘
    """

    def __init__(
        self,
        persist_dir: str = "data/cache",
        default_ttl: Optional[float] = 86400 * 7  # 7天
    ):
        self.persist_dir = Path(persist_dir)
        self.default_ttl = default_ttl
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # 内存索引
        self._index: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

        # 加载已有缓存
        self._load_index()

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.persist_dir / f"{key_hash}.json"

    def _load_index(self) -> None:
        """加载索引"""
        try:
            for cache_file in self.persist_dir.glob("*.json"):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        entry = CacheEntry(
                            key=data["key"],
                            value=data["value"],
                            level=CacheLevel.L3_PERSISTENT,
                            created_at=data.get("created_at", time.time()),
                            ttl=data.get("ttl", self.default_ttl),
                            size_bytes=data.get("size_bytes", 0)
                        )
                        # 检查是否过期
                        if not entry.is_expired():
                            self._index[entry.key] = entry
                except Exception:
                    # 删除损坏的缓存文件
                    cache_file.unlink(missing_ok=True)
        except Exception:
            pass

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key not in self._index:
                return None

            entry = self._index[key]

            # 检查过期
            if entry.is_expired():
                self._delete_file(key)
                del self._index[key]
                return None

            # 更新访问时间
            entry.touch()
            self._save_entry(entry)

            return entry.value

    def _save_entry(self, entry: CacheEntry) -> None:
        """保存缓存条目"""
        try:
            cache_path = self._get_cache_path(entry.key)
            data = {
                "key": entry.key,
                "value": entry.value,
                "created_at": entry.created_at,
                "last_accessed": entry.last_accessed,
                "access_count": entry.access_count,
                "ttl": entry.ttl,
                "size_bytes": entry.size_bytes
            }
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass

    def _delete_file(self, key: str) -> None:
        """删除缓存文件"""
        try:
            cache_path = self._get_cache_path(key)
            cache_path.unlink(missing_ok=True)
        except Exception:
            pass

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        size_hint: int = 0
    ) -> None:
        """设置缓存"""
        with self._lock:
            # 计算大小
            value_str = str(value)
            size = size_hint or len(value_str.encode())

            entry = CacheEntry(
                key=key,
                value=value,
                level=CacheLevel.L3_PERSISTENT,
                ttl=ttl or self.default_ttl,
                size_bytes=size
            )

            self._index[key] = entry
            self._save_entry(entry)

    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self._index:
                self._delete_file(key)
                del self._index[key]
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            for key in list(self._index.keys()):
                self._delete_file(key)
            self._index.clear()

    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._index.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                self._delete_file(key)
                del self._index[key]
            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total_size = sum(e.size_bytes for e in self._index.values())
            return {
                "level": CacheLevel.L3_PERSISTENT.value,
                "entries": len(self._index),
                "size_bytes": total_size,
                "size_mb": total_size / (1024 * 1024),
                "persist_dir": str(self.persist_dir),
            }


# ========== 多级缓存管理器 ==========

class MultiLevelCache:
    """
    多级缓存管理器

    访问顺序：L1 → L2 → L3
    设置顺序：L1 → L2 → L3

    特点：
    - L1 最快，容量最小
    - L2 (Redis) 可选，需要Redis服务
    - L3 最慢，容量最大
    - 自动逐级回源
    - 统计各层命中率
    """

    def __init__(
        self,
        l1_size: int = 1000,
        l2_enabled: bool = False,  # Redis暂不启用
        l3_enabled: bool = True,
        persist_dir: str = "data/cache",
        default_ttl: float = 3600
    ):
        # L1内存缓存
        self.l1 = L1MemoryCache(max_size=l1_size, default_ttl=default_ttl)

        # L2 Redis（暂不支持）
        self.l2_enabled = l2_enabled
        self.l2 = None

        # L3持久化缓存
        self.l3_enabled = l3_enabled
        self.l3 = L3PersistentCache(
            persist_dir=persist_dir,
            default_ttl=default_ttl * 24
        ) if l3_enabled else None

        # 统计
        self._stats = CacheStats()
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存（自动逐级回源）

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在返回None
        """
        # L1
        value = self.l1.get(key)
        if value is not None:
            with self._lock:
                self._stats.l1_hits += 1
                self._stats.hits += 1
            return value

        # L2 (暂不支持)
        if self.l2_enabled and self.l2:
            value = self._get_l2(key)
            if value is not None:
                with self._lock:
                    self._stats.l2_hits += 1
                    self._stats.hits += 1
                # 回填L1
                self.l1.set(key, value)
                return value

        # L3
        if self.l3_enabled and self.l3:
            value = self.l3.get(key)
            if value is not None:
                with self._lock:
                    self._stats.l3_hits += 1
                    self._stats.hits += 1
                # 回填L1
                self.l1.set(key, value)
                return value

        # 未命中
        with self._lock:
            self._stats.misses += 1
        return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        levels: Optional[List[CacheLevel]] = None
    ) -> None:
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间
            levels: 指定写入的层级，默认全部
        """
        if levels is None:
            levels = [CacheLevel.L1_MEMORY]

            if self.l2_enabled:
                levels.append(CacheLevel.L2_REDIS)

            if self.l3_enabled:
                levels.append(CacheLevel.L3_PERSISTENT)

        for level in levels:
            try:
                if level == CacheLevel.L1_MEMORY:
                    self.l1.set(key, value, ttl)
                elif level == CacheLevel.L2_REDIS and self.l2:
                    self._set_l2(key, value, ttl)
                elif level == CacheLevel.L3_PERSISTENT and self.l3:
                    self.l3.set(key, value, ttl)
            except Exception:
                pass

    def delete(self, key: str) -> bool:
        """删除缓存（所有层级）"""
        deleted = False

        if self.l1.delete(key):
            deleted = True

        if self.l2_enabled and self.l2:
            if self._delete_l2(key):
                deleted = True

        if self.l3_enabled and self.l3:
            if self.l3.delete(key):
                deleted = True

        return deleted

    def clear(self, level: Optional[CacheLevel] = None) -> None:
        """
        清空缓存

        Args:
            level: 指定层级，默认全部
        """
        if level is None or level == CacheLevel.L1_MEMORY:
            self.l1.clear()

        if level is None or level == CacheLevel.L2_REDIS:
            if self.l2_enabled and self.l2:
                self._clear_l2()

        if level is None or level == CacheLevel.L3_PERSISTENT:
            if self.l3_enabled and self.l3:
                self.l3.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            stats = self._stats.to_dict()
            stats["l1"] = self.l1.get_stats()
            if self.l2_enabled and self.l2:
                stats["l2"] = self._get_l2_stats()
            if self.l3_enabled and self.l3:
                stats["l3"] = self.l3.get_stats()
            return stats

    def record_eviction(self) -> None:
        """记录淘汰"""
        with self._lock:
            self._stats.evictions += 1

    # ========== Redis操作（预留接口）==========

    def _get_l2(self, key: str) -> Optional[Any]:
        """从L2获取"""
        # TODO: 实现Redis
        return None

    def _set_l2(self, key: str, value: Any, ttl: Optional[float]) -> None:
        """写入L2"""
        # TODO: 实现Redis
        pass

    def _delete_l2(self, key: str) -> bool:
        """从L2删除"""
        # TODO: 实现Redis
        return False

    def _clear_l2(self) -> None:
        """清空L2"""
        # TODO: 实现Redis
        pass

    def _get_l2_stats(self) -> Dict[str, Any]:
        """获取L2统计"""
        return {"level": "l2_redis", "status": "disabled"}


# ========== 便捷函数 ==========

# 全局缓存实例
_global_cache: Optional[MultiLevelCache] = None


def get_global_cache() -> MultiLevelCache:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = MultiLevelCache(
            l1_size=1000,
            l3_enabled=True,
            persist_dir="data/cache"
        )
    return _global_cache


def cache_get(key: str) -> Optional[Any]:
    """全局缓存获取"""
    return get_global_cache().get(key)


def cache_set(key: str, value: Any, ttl: Optional[float] = None) -> None:
    """全局缓存设置"""
    get_global_cache().set(key, value, ttl)


def cache_delete(key: str) -> bool:
    """全局缓存删除"""
    return get_global_cache().delete(key)


def cache_clear() -> None:
    """全局缓存清空"""
    get_global_cache().clear()

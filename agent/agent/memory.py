"""
Memory 记忆管理系统 - 支持短期记忆和长期记忆
线程安全版本，完整类型提示
"""
import json
import time
import uuid
import threading
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Iterator, TypeVar, Generic
from datetime import datetime
from pathlib import Path


T = TypeVar('T')


@dataclass(frozen=True)
class MemoryEntry:
    id: str
    role: str
    content: str
    timestamp: float
    metadata: tuple = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if isinstance(self.metadata, dict):
            object.__setattr__(self, 'metadata', tuple(self.metadata.items()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        return cls(
            id=data["id"],
            role=data["role"],
            content=data["content"],
            timestamp=data["timestamp"],
            metadata=tuple(data.get("metadata", {}).items())
        )

    @property
    def metadata_dict(self) -> Dict[str, Any]:
        return dict(self.metadata)


class ThreadSafeList:
    def __init__(self, initial: List[Any] = None) -> None:
        self._lock = threading.Lock()
        self._data: List[Any] = initial or []

    def append(self, item: Any) -> None:
        with self._lock:
            self._data.append(item)

    def extend(self, items: List[Any]) -> None:
        with self._lock:
            self._data.extend(items)

    def pop(self, index: int = -1) -> Any:
        with self._lock:
            return self._data.pop(index)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def copy(self) -> List[Any]:
        with self._lock:
            return self._data.copy()

    def __iter__(self) -> Iterator[Any]:
        with self._lock:
            return iter(self._data.copy())

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def __getitem__(self, index: int) -> Any:
        with self._lock:
            return self._data[index]

    def __setitem__(self, index: int, value: Any) -> None:
        with self._lock:
            self._data[index] = value

    def filter(self, predicate) -> List[Any]:
        with self._lock:
            return [x for x in self._data if predicate(x)]

    def slice(self, start: int, end: int) -> List[Any]:
        with self._lock:
            return self._data[start:end]


class ThreadSafeDict:
    def __init__(self, initial: Dict[str, Any] = None) -> None:
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = initial or {}

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def setdefault(self, key: str, default: Any = None) -> Any:
        with self._lock:
            if key not in self._data:
                self._data[key] = default
            return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def __getitem__(self, key: str) -> Any:
        with self._lock:
            return self._data[key]

    def __delitem__(self, key: str) -> None:
        with self._lock:
            del self._data[key]

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._data

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def __iter__(self) -> Iterator[str]:
        with self._lock:
            return iter(list(self._data.keys()))

    def values(self) -> List[Any]:
        with self._lock:
            return list(self._data.values())

    def keys(self) -> List[str]:
        with self._lock:
            return list(self._data.keys())

    def items(self) -> List[tuple]:
        with self._lock:
            return list(self._data.items())

    def copy(self) -> Dict[str, Any]:
        with self._lock:
            return self._data.copy()

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class BaseMemory(ABC):
    @abstractmethod
    def add(self, role: str, content: str, metadata: Dict[str, Any] = None) -> str:
        pass

    @abstractmethod
    def get_recent(self, limit: int = 10) -> List[MemoryEntry]:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        pass


class ShortTermMemory(BaseMemory):
    def __init__(self, max_entries: int = 50, ttl_seconds: int = 3600) -> None:
        self.max_entries: int = max_entries
        self.ttl_seconds: float = float(ttl_seconds)
        self._memory: ThreadSafeList = ThreadSafeList()
        self._lock: threading.RLock = threading.RLock()

    def add(self, role: str, content: str, metadata: Dict[str, Any] = None) -> str:
        entry_id: str = uuid.uuid4().hex[:12]
        entry: MemoryEntry = MemoryEntry(
            id=entry_id,
            role=role,
            content=content,
            timestamp=time.time(),
            metadata=tuple(metadata.items()) if metadata else ()
        )

        with self._lock:
            self._memory.append(entry)

            if len(self._memory) > self.max_entries:
                self._memory.pop(0)

            self._cleanup_expired_locked()

        return entry_id

    def get_recent(self, limit: int = 10) -> List[MemoryEntry]:
        with self._lock:
            self._cleanup_expired_locked()
            return self._memory.slice(-limit, len(self._memory))

    def clear(self) -> None:
        with self._lock:
            self._memory.clear()

    def search(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        with self._lock:
            self._cleanup_expired_locked()
            query_lower: str = query.lower()
            results: List[MemoryEntry] = [
                entry for entry in self._memory
                if query_lower in entry.content.lower()
            ]
            return results[:limit]

    def _cleanup_expired_locked(self) -> None:
        cutoff: float = time.time() - self.ttl_seconds
        original_len: int = len(self._memory)
        self._memory._data = [e for e in self._memory._data if e.timestamp > cutoff]
        new_len: int = len(self._memory)

    def get_all(self) -> List[MemoryEntry]:
        with self._lock:
            self._cleanup_expired_locked()
            return self._memory.copy()

    def __len__(self) -> int:
        with self._lock:
            self._cleanup_expired_locked()
            return len(self._memory)

    def get_context_string(self, limit: int = 10) -> str:
        recent: List[MemoryEntry] = self.get_recent(limit)
        if not recent:
            return ""
        return "\n".join(f"{e.role}: {e.content}" for e in recent)


class LongTermMemory(BaseMemory):
    def __init__(self, persist_dir: str = "data/agent/memory") -> None:
        self.persist_dir: Path = Path(persist_dir)
        self._memory_index: ThreadSafeDict = ThreadSafeDict()
        self._lock: threading.RLock = threading.RLock()
        self._ensure_persist_dir()
        self._load_index()

    def _ensure_persist_dir(self) -> None:
        self.persist_dir.mkdir(parents=True, exist_ok=True)

    def _get_index_path(self) -> Path:
        return self.persist_dir / "memory_index.json"

    def _get_entry_path(self, entry_id: str) -> Path:
        return self.persist_dir / f"{entry_id}.json"

    def _load_index(self) -> None:
        index_path: Path = self._get_index_path()
        if not index_path.exists():
            return

        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index_data: List[Dict[str, Any]] = json.load(f)
                for entry_data in index_data:
                    entry: MemoryEntry = MemoryEntry.from_dict(entry_data)
                    self._memory_index[entry.id] = entry
        except (json.JSONDecodeError, KeyError, OSError):
            pass

    def _save_index(self) -> None:
        with self._lock:
            index_data: List[Dict[str, Any]] = [
                entry.to_dict() for entry in self._memory_index.values()
            ]
            temp_path: Path = self._get_index_path().with_suffix('.tmp')
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            temp_path.replace(self._get_index_path())

    def add(self, role: str, content: str, metadata: Dict[str, Any] = None) -> str:
        entry_id: str = uuid.uuid4().hex[:12]
        entry: MemoryEntry = MemoryEntry(
            id=entry_id,
            role=role,
            content=content,
            timestamp=time.time(),
            metadata=tuple(metadata.items()) if metadata else ()
        )

        entry_path: Path = self._get_entry_path(entry_id)
        temp_path: Path = entry_path.with_suffix('.tmp')

        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, ensure_ascii=False, indent=2)
            temp_path.replace(entry_path)

            with self._lock:
                self._memory_index[entry_id] = entry
                self._save_index()

            return entry_id
        except OSError:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def get_recent(self, limit: int = 10) -> List[MemoryEntry]:
        with self._lock:
            sorted_entries: List[MemoryEntry] = sorted(
                self._memory_index.values(),
                key=lambda e: e.timestamp,
                reverse=True
            )
            return sorted_entries[:limit]

    def clear(self) -> None:
        with self._lock:
            for entry_id in list(self._memory_index.keys()):
                entry_path: Path = self._get_entry_path(entry_id)
                if entry_path.exists():
                    entry_path.unlink()
            self._memory_index.clear()
            self._save_index()

    def search(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        with self._lock:
            query_lower: str = query.lower()
            scored: List[tuple] = [
                (entry.content.lower().count(query_lower), entry)
                for entry in self._memory_index.values()
                if query_lower in entry.content.lower()
            ]
            scored.sort(key=lambda x: x[0], reverse=True)
            return [entry for _, entry in scored[:limit]]

    def get_all(self) -> List[MemoryEntry]:
        with self._lock:
            return list(self._memory_index.values())

    def get_context_string(self, limit: int = 10) -> str:
        recent: List[MemoryEntry] = self.get_recent(limit)
        if not recent:
            return ""
        return "\n".join(f"{e.role}: {e.content}" for e in recent)


class MemoryManager:
    def __init__(
        self,
        short_term_ttl: int = 3600,
        short_term_max: int = 50,
        long_term_persist_dir: str = "data/agent/memory"
    ) -> None:
        self.short_term: ShortTermMemory = ShortTermMemory(
            max_entries=short_term_max,
            ttl_seconds=short_term_ttl
        )
        self.long_term: LongTermMemory = LongTermMemory(persist_dir=long_term_persist_dir)
        self._manager_lock: threading.RLock = threading.RLock()

    def add_user_message(self, content: str, metadata: Dict[str, Any] = None) -> str:
        with self._manager_lock:
            return self.short_term.add("user", content, metadata)

    def add_assistant_message(self, content: str, metadata: Dict[str, Any] = None) -> str:
        with self._manager_lock:
            entry_id: str = self.short_term.add("assistant", content, metadata)
            self.long_term.add("assistant", content, metadata)
            return entry_id

    def add_system_message(self, content: str, metadata: Dict[str, Any] = None) -> str:
        with self._manager_lock:
            return self.short_term.add("system", content, metadata)

    def get_conversation_history(self, limit: int = 20) -> str:
        with self._manager_lock:
            return self.short_term.get_context_string(limit)

    def search_memories(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        with self._manager_lock:
            short_results: List[MemoryEntry] = self.short_term.search(query, limit)
            long_results: List[MemoryEntry] = self.long_term.search(query, limit)

            seen: set = set()
            unique: List[MemoryEntry] = []
            for entry in short_results + long_results:
                if entry.id not in seen:
                    seen.add(entry.id)
                    unique.append(entry)
            return unique[:limit]

    def get_relevant_context(self, query: str, limit: int = 10) -> str:
        memories: List[MemoryEntry] = self.search_memories(query, limit)
        if not memories:
            return ""
        return "\n".join(
            f"[{m.role}]({datetime.fromtimestamp(m.timestamp).strftime('%Y-%m-%d %H:%M')}): {m.content}"
            for m in memories
        )

    def clear_short_term(self) -> None:
        with self._manager_lock:
            self.short_term.clear()

    def clear_all(self) -> None:
        with self._manager_lock:
            self.short_term.clear()
            self.long_term.clear()

    def get_session_summary(self) -> Dict[str, Any]:
        with self._manager_lock:
            short_entries: List[MemoryEntry] = self.short_term.get_all()
            long_entries: List[MemoryEntry] = self.long_term.get_all()
            return {
                "short_term_count": len(short_entries),
                "long_term_count": len(long_entries),
                "short_term_recent": [e.content[:100] for e in short_entries[-3:]],
                "long_term_recent": [e.content[:100] for e in long_entries[-3:]]
            }
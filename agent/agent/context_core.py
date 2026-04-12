"""
Context 上下文处理机制 - 高效的上下文提取、整合与动态更新
线程安全版本，完整类型提示
"""
import time
import uuid
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime


@dataclass(frozen=True)
class ContextEntry:
    id: str
    type: str
    content: str
    relevance_score: float
    timestamp: float
    source: str
    metadata: tuple

    def __post_init__(self) -> None:
        if isinstance(self.metadata, dict):
            object.__setattr__(self, 'metadata', tuple(self.metadata.items()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "relevance_score": self.relevance_score,
            "timestamp": self.timestamp,
            "source": self.source,
            "metadata": dict(self.metadata)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextEntry":
        return cls(
            id=data["id"],
            type=data["type"],
            content=data["content"],
            relevance_score=data["relevance_score"],
            timestamp=data["timestamp"],
            source=data.get("source", ""),
            metadata=tuple(data.get("metadata", {}).items())
        )

    @property
    def metadata_dict(self) -> Dict[str, Any]:
        return dict(self.metadata)


class Context:
    def __init__(self, session_id: Optional[str] = None) -> None:
        self._entries: List[ContextEntry] = []
        self._lock: threading.RLock = threading.RLock()
        self.max_entries: int = 20
        self.session_id: str = session_id or uuid.uuid4().hex[:12]
        self.created_at: float = time.time()
        self.last_updated: float = time.time()

    def add(self, entry: ContextEntry) -> None:
        with self._lock:
            self._entries.append(entry)
            self.last_updated = time.time()
            self._trim_locked()

    def add_entry(
        self,
        content_type: str,
        content: str,
        relevance_score: float = 1.0,
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContextEntry:
        entry: ContextEntry = ContextEntry(
            id=uuid.uuid4().hex[:12],
            type=content_type,
            content=content,
            relevance_score=relevance_score,
            timestamp=time.time(),
            source=source,
            metadata=tuple(metadata.items()) if metadata else ()
        )
        self.add(entry)
        return entry

    def _trim_locked(self) -> None:
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries:]

    def get_recent(self, limit: int = 10) -> List[ContextEntry]:
        with self._lock:
            return self._entries[-limit:] if limit > 0 else self._entries.copy()

    def get_by_type(self, entry_type: str) -> List[ContextEntry]:
        with self._lock:
            return [e for e in self._entries if e.type == entry_type]

    def get_relevant(self, min_score: float = 0.5) -> List[ContextEntry]:
        with self._lock:
            return [e for e in self._entries if e.relevance_score >= min_score]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self.last_updated = time.time()

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "session_id": self.session_id,
                "created_at": self.created_at,
                "last_updated": self.last_updated,
                "entries": [e.to_dict() for e in self._entries],
                "count": len(self._entries)
            }

    def get_context_summary(self) -> str:
        with self._lock:
            if not self._entries:
                return ""
            parts: List[str] = []
            for entry in self._entries[-10:]:
                parts.append(f"[{entry.type}] {entry.content[:200]}")
            return "\n".join(parts)

    def merge(self, other: "Context") -> None:
        with self._lock:
            seen_ids: set = {e.id for e in self._entries}
            for entry in other._entries:
                if entry.id not in seen_ids:
                    self._entries.append(entry)
            self._entries.sort(key=lambda e: e.timestamp, reverse=True)
            self._trim_locked()
            self.last_updated = time.time()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def __iter__(self) -> Iterator[ContextEntry]:
        with self._lock:
            return iter(self._entries.copy())


class ContextManager:
    def __init__(self) -> None:
        self._contexts: Dict[str, Context] = {}
        self._lock: threading.RLock = threading.RLock()
        self._default_session: str = "default"

    def get_context(self, session_id: Optional[str] = None) -> Context:
        sid: str = session_id or self._default_session
        with self._lock:
            if sid not in self._contexts:
                self._contexts[sid] = Context(session_id=sid)
            return self._contexts[sid]

    def create_context(self, session_id: Optional[str] = None) -> Context:
        sid: str = session_id or uuid.uuid4().hex[:12]
        with self._lock:
            context: Context = Context(session_id=sid)
            self._contexts[sid] = context
            return context

    def delete_context(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._contexts:
                del self._contexts[session_id]
                return True
            return False

    def update_context(
        self,
        session_id: str,
        content_type: str,
        content: str,
        relevance_score: float = 1.0,
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContextEntry:
        context: Context = self.get_context(session_id)
        return context.add_entry(content_type, content, relevance_score, source, metadata)

    def add_knowledge_context(
        self,
        session_id: str,
        documents: List[Dict[str, Any]],
        query: str = ""
    ) -> None:
        context: Context = self.get_context(session_id)
        with context._lock:
            for i, doc in enumerate(documents):
                context._entries.append(ContextEntry(
                    id=uuid.uuid4().hex[:12],
                    type="knowledge",
                    content=doc.get("content", ""),
                    relevance_score=doc.get("similarity", 1.0 - (i * 0.1)),
                    timestamp=time.time(),
                    source=doc.get("source", ""),
                    metadata=tuple({"query": query, "rank": i}.items())
                ))
            context._trim_locked()
            context.last_updated = time.time()

    def add_memory_context(
        self,
        session_id: str,
        memories: List[str]
    ) -> None:
        context: Context = self.get_context(session_id)
        with context._lock:
            for mem in memories:
                context._entries.append(ContextEntry(
                    id=uuid.uuid4().hex[:12],
                    type="memory",
                    content=mem,
                    relevance_score=0.8,
                    timestamp=time.time(),
                    source="",
                    metadata=()
                ))
            context._trim_locked()
            context.last_updated = time.time()

    def add_skill_context(
        self,
        session_id: str,
        skill_name: str,
        skill_result: str
    ) -> None:
        context: Context = self.get_context(session_id)
        context.add_entry(
            content_type="skill",
            content=f"Executed {skill_name}: {skill_result}",
            relevance_score=0.9,
            source=skill_name
        )

    def build_context_prompt(
        self,
        session_id: str,
        include_types: Optional[List[str]] = None,
        max_entries: int = 10
    ) -> str:
        context: Context = self.get_context(session_id)
        with context._lock:
            if include_types:
                filtered: List[ContextEntry] = [
                    e for e in context._entries if e.type in include_types
                ]
            else:
                filtered = context._entries

            filtered = filtered[-max_entries:]

            if not filtered:
                return ""

            parts: List[str] = []
            for entry in filtered:
                time_str: str = datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S")
                parts.append(
                    f"[{entry.type.upper()}][{time_str}][{entry.source}] {entry.content}"
                )

            return "\n".join(parts)

    def get_context_stats(self, session_id: str) -> Dict[str, Any]:
        context: Context = self.get_context(session_id)
        with context._lock:
            type_counts: Dict[str, int] = {}
            for entry in context._entries:
                type_counts[entry.type] = type_counts.get(entry.type, 0) + 1

            return {
                "session_id": session_id,
                "total_entries": len(context._entries),
                "type_counts": type_counts,
                "created_at": context.created_at,
                "last_updated": context.last_updated
            }

    def list_sessions(self) -> List[str]:
        with self._lock:
            return list(self._contexts.keys())

    def clear_session(self, session_id: str) -> bool:
        context: Context = self.get_context(session_id)
        context.clear()
        return True

    def get_all_contexts(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {sid: ctx.to_dict() for sid, ctx in self._contexts.items()}

    def cleanup_inactive_sessions(self, max_age_seconds: float = 3600) -> int:
        current_time: float = time.time()
        with self._lock:
            to_delete: List[str] = [
                sid for sid, ctx in self._contexts.items()
                if current_time - ctx.last_updated > max_age_seconds
            ]
            for sid in to_delete:
                del self._contexts[sid]
            return len(to_delete)
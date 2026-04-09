"""Agent记忆管理模块 - 支持持久化存储"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import json
import os
import threading


@dataclass
class MemoryEntry:
    """记忆条目"""
    role: str
    content: str
    timestamp: str
    intent: Optional[str] = None
    state: Optional[str] = None


class AgentMemory:
    """Agent记忆管理器 - 支持持久化"""

    def __init__(self, user_id: str, role: str = "student"):
        self.user_id = user_id
        self.role = role
        self.memory_dir = "./data/memory"
        self.max_entries = 50
        self.lock = threading.Lock()

        os.makedirs(self.memory_dir, exist_ok=True)
        self.memory_file = os.path.join(
            self.memory_dir,
            f"{user_id}_{role}_memory.json"
        )

        self.short_term: List[MemoryEntry] = []
        self.long_term_summary: Optional[str] = None
        self._load_memory()

    def _load_memory(self):
        """从磁盘加载记忆"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.short_term = [
                        MemoryEntry(**entry) for entry in data.get("short_term", [])
                    ]
                    self.long_term_summary = data.get("long_term_summary")
            except Exception:
                self.short_term = []
                self.long_term_summary = None

    def _save_memory(self):
        """持久化保存记忆到磁盘"""
        with self.lock:
            data = {
                "user_id": self.user_id,
                "role": self.role,
                "short_term": [asdict(entry) for entry in self.short_term],
                "long_term_summary": self.long_term_summary,
                "updated_at": datetime.now().isoformat()
            }
            try:
                with open(self.memory_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    def add(self, role: str, content: str, intent: str = None, state: str = None):
        """添加记忆"""
        entry = MemoryEntry(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            intent=intent,
            state=state
        )

        self.short_term.append(entry)

        if len(self.short_term) > self.max_entries:
            self._summarize_and_compress()

        self._save_memory()

    def _summarize_and_compress(self):
        """压缩记忆：当短时记忆超过上限时，生成摘要"""
        if len(self.short_term) < 10:
            return

        recent_entries = self.short_term[-20:]

        summary_parts = []
        for entry in recent_entries:
            role_label = "用户" if entry.role == "user" else "暖暖"
            summary_parts.append(f"{role_label}：{entry.content[:50]}...")

        self.long_term_summary = f"【早期对话摘要】({'、'.join(summary_parts[:5])})"

        self.short_term = self.short_term[-10:]

    def get_context(self, max_turns: int = 10) -> List[Dict[str, str]]:
        """获取对话上下文（最近N轮）"""
        context = []

        if self.long_term_summary:
            context.append({
                "role": "system",
                "content": self.long_term_summary
            })

        recent = self.short_term[-max_turns:] if self.short_term else []

        for entry in recent:
            context.append({
                "role": entry.role,
                "content": entry.content
            })

        return context

    def get_full_history(self) -> List[MemoryEntry]:
        """获取完整记忆"""
        return self.short_term.copy()

    def clear(self):
        """清空记忆"""
        self.short_term = []
        self.long_term_summary = None
        self._save_memory()

        if os.path.exists(self.memory_file):
            try:
                os.remove(self.memory_file)
            except Exception:
                pass

    def search_memory(self, keyword: str) -> List[MemoryEntry]:
        """搜索记忆中的关键词"""
        results = []
        for entry in self.short_term:
            if keyword in entry.content:
                results.append(entry)
        return results

    def get_user_profile(self) -> Dict[str, Any]:
        """从记忆中提取用户画像"""
        emotions = []
        topics = []
        concerns = []

        for entry in self.short_term:
            if entry.intent == "emotion_support":
                emotions.append(entry.content[:100])
            elif entry.intent == "knowledge_query":
                topics.append(entry.content[:100])

        return {
            "user_id": self.user_id,
            "role": self.role,
            "total_conversations": len(self.short_term),
            "emotion_mentioned_count": len(emotions),
            "topics_asked": list(set(topics)),
            "last_interaction": self.short_term[-1].timestamp if self.short_term else None,
            "has_crisis_history": any("危机" in e.content or "自" in e.content for e in self.short_term)
        }


class GlobalMemoryStore:
    """全局记忆存储 - 管理所有用户的Agent实例"""

    _instances: Dict[str, AgentMemory] = {}
    _lock = threading.Lock()

    @classmethod
    def get_memory(cls, user_id: str, role: str = "student") -> AgentMemory:
        """获取用户记忆实例"""
        key = f"{user_id}_{role}"
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = AgentMemory(user_id, role)
            return cls._instances[key]

    @classmethod
    def clear_user_memory(cls, user_id: str, role: str = "student"):
        """清除用户记忆"""
        key = f"{user_id}_{role}"
        with cls._lock:
            if key in cls._instances:
                cls._instances[key].clear()
                del cls._instances[key]

    @classmethod
    def list_all_memories(cls) -> List[str]:
        """列出所有有记忆的用户"""
        return list(cls._instances.keys())

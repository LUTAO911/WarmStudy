"""
Unified Memory Manager - 统一分层记忆管理系统
三层记忆架构：对话记忆 + 用户画像 + 情感历史
版本: v5.0
"""
import time
import json
import threading
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from pathlib import Path
from datetime import datetime

if TYPE_CHECKING:
    pass

# ========== 数据模型 ==========

@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    memory_type: str  # dialogue/profile/emotion/knowledge
    timestamp: float
    importance: float = 0.5  # 0-1 重要度
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "timestamp": self.timestamp,
            "importance": self.importance,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        return cls(**data)


@dataclass
class UserProfile:
    """用户画像"""
    user_id: str
    user_type: str = "student"  # student/parent/teacher
    name: Optional[str] = None
    grade: Optional[str] = None

    # 特征标签
    interests: List[str] = field(default_factory=list)
    learning_style: Optional[str] = None
    communication_preference: str = "friendly"  # friendly/formal/casual

    # 心理状态
    typical_emotions: List[str] = field(default_factory=list)
    stress_triggers: List[str] = field(default_factory=list)
    coping_strategies: List[str] = field(default_factory=list)

    # 关系
    family_members: List[Dict[str, str]] = field(default_factory=list)
    friends: List[str] = field(default_factory=list)

    # 元数据
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "user_type": self.user_type,
            "name": self.name,
            "grade": self.grade,
            "interests": self.interests,
            "learning_style": self.learning_style,
            "communication_preference": self.communication_preference,
            "typical_emotions": self.typical_emotions,
            "stress_triggers": self.stress_triggers,
            "coping_strategies": self.coping_strategies,
            "family_members": self.family_members,
            "friends": self.friends,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        return cls(**data)


@dataclass
class EmotionRecord:
    """情感记录"""
    user_id: str
    emotion_type: str
    intensity: float  # 0-1
    trigger: Optional[str] = None
    context: Optional[str] = None
    response_given: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "emotion_type": self.emotion_type,
            "intensity": self.intensity,
            "trigger": self.trigger,
            "context": self.context,
            "response_given": self.response_given,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmotionRecord":
        return cls(**data)


# ========== 统一记忆管理器 ==========

class UnifiedMemoryManager:
    """
    统一记忆管理器

    记忆分层：
    1. 对话记忆（Dialogue Memory）- 短期会话
    2. 用户画像（User Profile）- 长期用户特征
    3. 情感历史（Emotion History）- 情绪变化追踪
    4. 知识记忆（Knowledge Memory）- 事实性知识
    """

    def __init__(
        self,
        persist_dir: str = "data/agent/memory",
        max_dialogue_entries: int = 100,
        max_emotion_history: int = 500,
    ):
        self.persist_dir = Path(persist_dir)
        self.max_dialogue_entries = max_dialogue_entries
        self.max_emotion_history = max_emotion_history

        self._lock = threading.RLock()

        # 各层记忆存储
        self._dialogue_memory: Dict[str, List[MemoryEntry]] = {}  # session_id -> entries
        self._user_profiles: Dict[str, UserProfile] = {}  # user_id -> profile
        self._emotion_history: Dict[str, List[EmotionRecord]] = {}  # user_id -> records
        self._knowledge_memory: List[MemoryEntry] = []

        # 确保目录存在
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # 加载持久化数据
        self._load_persisted_data()

    # ========== 对话记忆 ==========

    def add_dialogue(
        self,
        session_id: str,
        role: str,  # user/assistant/system
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """添加对话记忆"""
        entry = MemoryEntry(
            id=f"dlg_{int(time.time() * 1000)}",
            content=content,
            memory_type="dialogue",
            timestamp=time.time(),
            importance=0.5,
            metadata={
                "role": role,
                "session_id": session_id,
                **(metadata or {})
            }
        )

        with self._lock:
            if session_id not in self._dialogue_memory:
                self._dialogue_memory[session_id] = []

            self._dialogue_memory[session_id].append(entry)

            # 限制数量
            if len(self._dialogue_memory[session_id]) > self.max_dialogue_entries:
                self._dialogue_memory[session_id].pop(0)

        return entry.id

    def get_dialogue_history(
        self,
        session_id: str,
        limit: int = 20,
        role_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取对话历史"""
        with self._lock:
            entries = self._dialogue_memory.get(session_id, [])

        if role_filter:
            entries = [e for e in entries if e.metadata.get("role") == role_filter]

        recent = entries[-limit:] if limit > 0 else entries

        return [
            {
                "role": e.metadata.get("role"),
                "content": e.content,
                "timestamp": e.timestamp,
            }
            for e in reversed(recent)
        ]

    def clear_dialogue(self, session_id: str) -> bool:
        """清除会话对话"""
        with self._lock:
            if session_id in self._dialogue_memory:
                self._dialogue_memory[session_id].clear()
                return True
        return False

    # ========== 用户画像 ==========

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """获取用户画像"""
        with self._lock:
            return self._user_profiles.get(user_id)

    def create_user_profile(self, user_id: str, user_type: str = "student") -> UserProfile:
        """创建用户画像"""
        with self._lock:
            if user_id in self._user_profiles:
                return self._user_profiles[user_id]

            profile = UserProfile(user_id=user_id, user_type=user_type)
            self._user_profiles[user_id] = profile
            return profile

    def update_user_profile(
        self,
        user_id: str,
        profile_data: Dict[str, Any]
    ) -> Optional[UserProfile]:
        """更新用户画像"""
        with self._lock:
            if user_id not in self._user_profiles:
                return None

            profile = self._user_profiles[user_id]

            for key, value in profile_data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)

            profile.updated_at = time.time()
            return profile

    def add_profile_tag(
        self,
        user_id: str,
        tag_type: str,  # interest/stress_trigger/coping_strategy/emotion
        tag_value: str
    ) -> bool:
        """为用户画像添加标签"""
        with self._lock:
            if user_id not in self._user_profiles:
                return False

            profile = self._user_profiles[user_id]

            tag_map = {
                "interest": profile.interests,
                "stress_trigger": profile.stress_triggers,
                "coping_strategy": profile.coping_strategies,
                "emotion": profile.typical_emotions,
            }

            if tag_type in tag_map and tag_value not in tag_map[tag_type]:
                tag_map[tag_type].append(tag_value)
                profile.updated_at = time.time()
                return True

        return False

    # ========== 情感历史 ==========

    def add_emotion_record(
        self,
        user_id: str,
        emotion_type: str,
        intensity: float,
        trigger: Optional[str] = None,
        context: Optional[str] = None,
        response_given: Optional[str] = None
    ) -> str:
        """添加情感记录"""
        record = EmotionRecord(
            user_id=user_id,
            emotion_type=emotion_type,
            intensity=intensity,
            trigger=trigger,
            context=context,
            response_given=response_given,
            timestamp=time.time()
        )

        with self._lock:
            if user_id not in self._emotion_history:
                self._emotion_history[user_id] = []

            self._emotion_history[user_id].append(record)

            # 限制数量
            if len(self._emotion_history[user_id]) > self.max_emotion_history:
                self._emotion_history[user_id].pop(0)

        return f"emo_{int(time.time() * 1000)}"

    def get_emotion_trends(
        self,
        user_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """获取情绪趋势分析"""
        cutoff_time = time.time() - (days * 86400)

        with self._lock:
            records = self._emotion_history.get(user_id, [])

        # 过滤时间范围
        recent = [r for r in records if r.timestamp > cutoff_time]

        if not recent:
            return {
                "total_records": 0,
                "emotion_distribution": {},
                "average_intensity": 0,
                "trend": "stable",
                "dominant_emotion": None,
                "period_days": days,
            }

        # 统计分布
        emotion_counts: Dict[str, int] = {}
        total_intensity = 0.0

        for record in recent:
            emotion_counts[record.emotion_type] = emotion_counts.get(record.emotion_type, 0) + 1
            total_intensity += record.intensity

        # 计算趋势（最近vs早期）
        mid_point = len(recent) // 2
        early_avg = sum(r.intensity for r in recent[:mid_point]) / max(mid_point, 1)
        late_avg = sum(r.intensity for r in recent[mid_point:]) / max(len(recent) - mid_point, 1)

        if late_avg > early_avg * 1.2:
            trend = "increasing"
        elif late_avg < early_avg * 0.8:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "total_records": len(recent),
            "emotion_distribution": emotion_counts,
            "average_intensity": total_intensity / len(recent),
            "trend": trend,
            "dominant_emotion": max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else None,
            "period_days": days,
        }

    def get_recent_emotions(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取最近的情绪记录"""
        with self._lock:
            records = self._emotion_history.get(user_id, [])

        recent = records[-limit:] if limit > 0 else records

        return [
            {
                "emotion_type": r.emotion_type,
                "intensity": r.intensity,
                "trigger": r.trigger,
                "timestamp": r.timestamp,
            }
            for r in reversed(recent)
        ]

    # ========== 知识记忆 ==========

    def add_knowledge(
        self,
        content: str,
        knowledge_type: str,
        source: Optional[str] = None,
        importance: float = 0.5
    ) -> str:
        """添加知识记忆"""
        entry = MemoryEntry(
            id=f"know_{int(time.time() * 1000)}",
            content=content,
            memory_type="knowledge",
            timestamp=time.time(),
            importance=importance,
            metadata={
                "knowledge_type": knowledge_type,
                "source": source,
            }
        )

        with self._lock:
            self._knowledge_memory.append(entry)

        return entry.id

    def search_knowledge(
        self,
        query: str,
        knowledge_type: Optional[str] = None,
        limit: int = 5
    ) -> List[MemoryEntry]:
        """搜索知识记忆"""
        with self._lock:
            results = []

            for entry in self._knowledge_memory:
                if knowledge_type and entry.metadata.get("knowledge_type") != knowledge_type:
                    continue

                # 简单关键词匹配
                if query.lower() in entry.content.lower():
                    results.append(entry)

            # 按重要度排序
            results.sort(key=lambda x: x.importance, reverse=True)

            return results[:limit]

    # ========== 持久化 ==========

    def persist_data(self) -> None:
        """持久化所有数据到磁盘"""
        with self._lock:
            # 保存用户画像
            profile_data = {
                user_id: profile.to_dict()
                for user_id, profile in self._user_profiles.items()
            }

            profile_file = self.persist_dir / "user_profiles.json"
            with open(profile_file, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, ensure_ascii=False, indent=2)

            # 保存情感历史
            emotion_data = {
                user_id: [r.to_dict() for r in records]
                for user_id, records in self._emotion_history.items()
            }

            emotion_file = self.persist_dir / "emotion_history.json"
            with open(emotion_file, "w", encoding="utf-8") as f:
                json.dump(emotion_data, f, ensure_ascii=False, indent=2)

            # 保存对话记忆索引
            dialogue_data = {
                session_id: [e.to_dict() for e in entries]
                for session_id, entries in self._dialogue_memory.items()
            }

            dialogue_file = self.persist_dir / "dialogue_memory.json"
            with open(dialogue_file, "w", encoding="utf-8") as f:
                json.dump(dialogue_data, f, ensure_ascii=False, indent=2)

    def _load_persisted_data(self) -> None:
        """从磁盘加载持久化数据"""
        # 加载用户画像
        profile_file = self.persist_dir / "user_profiles.json"
        if profile_file.exists():
            try:
                with open(profile_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, profile_dict in data.items():
                        self._user_profiles[user_id] = UserProfile.from_dict(profile_dict)
            except (json.JSONDecodeError, KeyError, Exception):
                pass

        # 加载情感历史
        emotion_file = self.persist_dir / "emotion_history.json"
        if emotion_file.exists():
            try:
                with open(emotion_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, records in data.items():
                        self._emotion_history[user_id] = [
                            EmotionRecord.from_dict(r) for r in records
                        ]
            except (json.JSONDecodeError, KeyError, Exception):
                pass

        # 加载对话记忆
        dialogue_file = self.persist_dir / "dialogue_memory.json"
        if dialogue_file.exists():
            try:
                with open(dialogue_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for session_id, entries in data.items():
                        self._dialogue_memory[session_id] = [
                            MemoryEntry.from_dict(e) for e in entries
                        ]
            except (json.JSONDecodeError, KeyError, Exception):
                pass

    # ========== 统计信息 ==========

    def get_stats(self) -> Dict[str, Any]:
        """获取记忆系统统计"""
        with self._lock:
            return {
                "dialogue_sessions": len(self._dialogue_memory),
                "total_dialogue_entries": sum(len(e) for e in self._dialogue_memory.values()),
                "user_profiles": len(self._user_profiles),
                "emotion_records": sum(len(r) for r in self._emotion_history.values()),
                "knowledge_entries": len(self._knowledge_memory),
            }

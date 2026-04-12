"""
Unit tests for the multi-level memory system.

Tests the four memory layers provided by UnifiedMemoryManager:
  1. 对话记忆 (Dialogue Memory)
  2. 用户画像 (User Profile)
  3. 情感历史 (Emotion History)
  4. 知识记忆 (Knowledge Memory)

Also covers data-model serialisation/deserialisation, cross-layer
interactions, persistence of dialogue and emotion data, and basic
thread-safety of the manager.
"""
import tempfile
import shutil
import threading
import time
from pathlib import Path

import pytest

from agent.memory_store.unified_memory import (
    UnifiedMemoryManager,
    MemoryEntry,
    UserProfile,
    EmotionRecord,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp(tmp_path):
    """Provide a fresh temporary directory for each test."""
    return tmp_path


@pytest.fixture
def mem(tmp):
    """Return a fresh UnifiedMemoryManager backed by a temp directory."""
    return UnifiedMemoryManager(
        persist_dir=str(tmp / "memory"),
        max_dialogue_entries=20,
        max_emotion_history=50,
    )


# ===========================================================================
# Data-model tests
# ===========================================================================

class TestMemoryEntryModel:
    """Tests for MemoryEntry serialisation round-trip."""

    def test_to_dict_contains_required_keys(self):
        entry = MemoryEntry(
            id="e1",
            content="hello",
            memory_type="dialogue",
            timestamp=1_700_000_000.0,
            importance=0.7,
            metadata={"role": "user"},
        )
        d = entry.to_dict()
        assert d["id"] == "e1"
        assert d["content"] == "hello"
        assert d["memory_type"] == "dialogue"
        assert d["importance"] == 0.7
        assert d["metadata"]["role"] == "user"

    def test_from_dict_round_trip(self):
        original = MemoryEntry(
            id="e2",
            content="test content",
            memory_type="knowledge",
            timestamp=1_700_000_001.0,
            importance=0.5,
            metadata={"source": "book"},
        )
        restored = MemoryEntry.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.content == original.content
        assert restored.memory_type == original.memory_type
        assert restored.importance == original.importance
        assert restored.metadata == original.metadata


class TestUserProfileModel:
    """Tests for UserProfile serialisation and field defaults."""

    def test_default_fields(self):
        profile = UserProfile(user_id="u1")
        assert profile.user_type == "student"
        assert profile.interests == []
        assert profile.typical_emotions == []

    def test_to_dict_and_from_dict(self):
        profile = UserProfile(
            user_id="u2",
            user_type="teacher",
            name="王老师",
            interests=["数学", "物理"],
        )
        d = profile.to_dict()
        restored = UserProfile.from_dict(d)
        assert restored.user_id == "u2"
        assert restored.user_type == "teacher"
        assert restored.name == "王老师"
        assert "数学" in restored.interests

    def test_timestamps_present(self):
        profile = UserProfile(user_id="u3")
        d = profile.to_dict()
        assert "created_at" in d
        assert "updated_at" in d


class TestEmotionRecordModel:
    """Tests for EmotionRecord serialisation."""

    def test_to_dict_fields(self):
        record = EmotionRecord(
            user_id="u1",
            emotion_type="anxious",
            intensity=0.6,
            trigger="考试",
            context="期末复习阶段",
        )
        d = record.to_dict()
        assert d["user_id"] == "u1"
        assert d["emotion_type"] == "anxious"
        assert d["intensity"] == 0.6
        assert d["trigger"] == "考试"

    def test_from_dict_round_trip(self):
        record = EmotionRecord(
            user_id="u2",
            emotion_type="happy",
            intensity=0.9,
            timestamp=1_700_000_000.0,
        )
        restored = EmotionRecord.from_dict(record.to_dict())
        assert restored.user_id == record.user_id
        assert restored.emotion_type == record.emotion_type
        assert restored.intensity == record.intensity
        assert restored.timestamp == record.timestamp


# ===========================================================================
# Cross-layer interaction tests
# ===========================================================================

class TestCrossLayerInteractions:
    """Verify that operations on one memory layer do not corrupt another."""

    def test_dialogue_and_profile_independent(self, mem):
        """Writing dialogue should not affect user profile state."""
        mem.create_user_profile("u1", "student")
        mem.add_dialogue("sess1", "user", "叫我小明")
        profile = mem.get_user_profile("u1")
        assert profile is not None
        assert profile.user_id == "u1"

    def test_emotion_and_knowledge_independent(self, mem):
        """Adding an emotion record should not affect knowledge entries."""
        mem.add_knowledge("Python是脚本语言", "programming")
        mem.add_emotion_record("u1", "happy", 0.8)
        results = mem.search_knowledge("Python")
        assert len(results) >= 1
        assert results[0].content == "Python是脚本语言"

    def test_multiple_sessions_isolated(self, mem):
        """Dialogue from session A must not appear in session B."""
        mem.add_dialogue("sessA", "user", "session A message")
        mem.add_dialogue("sessB", "user", "session B message")

        history_a = mem.get_dialogue_history("sessA")
        history_b = mem.get_dialogue_history("sessB")

        contents_a = {h["content"] for h in history_a}
        contents_b = {h["content"] for h in history_b}

        assert "session A message" in contents_a
        assert "session A message" not in contents_b
        assert "session B message" in contents_b
        assert "session B message" not in contents_a

    def test_multiple_users_isolated(self, mem):
        """Emotion records for user A must not appear for user B."""
        mem.add_emotion_record("u1", "happy", 0.9)
        mem.add_emotion_record("u2", "sad", 0.4)

        trends_u1 = mem.get_emotion_trends("u1")
        trends_u2 = mem.get_emotion_trends("u2")

        assert trends_u1["dominant_emotion"] == "happy"
        assert trends_u2["dominant_emotion"] == "sad"

    def test_full_workflow(self, mem):
        """Simulate a typical session: profile + dialogue + emotion + knowledge."""
        # 1. Set up user
        mem.create_user_profile("u1", "student")
        mem.add_profile_tag("u1", "interest", "语文")

        # 2. Exchange messages
        mem.add_dialogue("sess1", "user", "我最近很焦虑")
        mem.add_dialogue("sess1", "assistant", "我理解你的感受，能告诉我更多吗？")

        # 3. Record emotion
        mem.add_emotion_record("u1", "anxious", 0.7, trigger="学习压力")

        # 4. Store relevant knowledge
        mem.add_knowledge("焦虑可以通过呼吸练习缓解", "psychology")

        # Verify all layers
        profile = mem.get_user_profile("u1")
        assert "语文" in profile.interests

        history = mem.get_dialogue_history("sess1")
        assert len(history) == 2

        trends = mem.get_emotion_trends("u1")
        assert trends["dominant_emotion"] == "anxious"

        knowledge = mem.search_knowledge("焦虑")
        assert len(knowledge) >= 1

        stats = mem.get_stats()
        assert stats["user_profiles"] >= 1
        assert stats["dialogue_sessions"] >= 1
        assert stats["emotion_records"] >= 1
        assert stats["knowledge_entries"] >= 1


# ===========================================================================
# Persistence tests (emotion history + dialogue memory)
# ===========================================================================

class TestPersistenceAllLayers:
    """Verify that persist_data / reload works for every layer."""

    def test_dialogue_persists_and_reloads(self, tmp):
        persist_path = str(tmp / "mem")
        m1 = UnifiedMemoryManager(persist_dir=persist_path)
        m1.add_dialogue("sess1", "user", "持久化测试消息")
        m1.persist_data()

        m2 = UnifiedMemoryManager(persist_dir=persist_path)
        history = m2.get_dialogue_history("sess1")
        contents = [h["content"] for h in history]
        assert "持久化测试消息" in contents

    def test_emotion_history_persists_and_reloads(self, tmp):
        persist_path = str(tmp / "mem")
        m1 = UnifiedMemoryManager(persist_dir=persist_path)
        m1.add_emotion_record("u1", "calm", 0.3)
        m1.persist_data()

        m2 = UnifiedMemoryManager(persist_dir=persist_path)
        recent = m2.get_recent_emotions("u1", limit=10)
        emotion_types = [r["emotion_type"] for r in recent]
        assert "calm" in emotion_types

    def test_profile_persists_and_reloads(self, tmp):
        persist_path = str(tmp / "mem")
        m1 = UnifiedMemoryManager(persist_dir=persist_path)
        m1.create_user_profile("u1", "parent")
        m1.update_user_profile("u1", {"name": "李妈妈"})
        m1.persist_data()

        m2 = UnifiedMemoryManager(persist_dir=persist_path)
        profile = m2.get_user_profile("u1")
        assert profile is not None
        assert profile.name == "李妈妈"
        assert profile.user_type == "parent"

    def test_reload_from_empty_dir_does_not_raise(self, tmp):
        """Starting fresh with no persisted data should succeed silently."""
        m = UnifiedMemoryManager(persist_dir=str(tmp / "empty"))
        assert m.get_stats()["user_profiles"] == 0


# ===========================================================================
# Thread-safety tests
# ===========================================================================

class TestThreadSafety:
    """Basic concurrent access checks for UnifiedMemoryManager."""

    def test_concurrent_dialogue_writes(self, mem):
        """Multiple threads writing dialogue must not raise or lose data."""
        errors = []

        def writer(thread_id):
            try:
                for i in range(10):
                    mem.add_dialogue(
                        f"sess{thread_id}", "user", f"thread {thread_id} msg {i}"
                    )
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Unexpected errors: {errors}"

    def test_concurrent_emotion_writes(self, mem):
        """Multiple threads writing emotion records must not raise."""
        errors = []

        def recorder(user_id):
            try:
                for _ in range(10):
                    mem.add_emotion_record(user_id, "neutral", 0.5)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=recorder, args=(f"u{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Unexpected errors: {errors}"

    def test_concurrent_profile_creates(self, mem):
        """Creating the same profile from multiple threads must remain idempotent."""
        errors = []

        def creator():
            try:
                mem.create_user_profile("shared_user", "student")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=creator) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        profile = mem.get_user_profile("shared_user")
        assert profile is not None
        assert profile.user_id == "shared_user"
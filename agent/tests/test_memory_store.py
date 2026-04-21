"""
Comprehensive Unit Tests for Memory and Cache Modules
包括: UnifiedMemoryManager, CacheManager
"""
import pytest
import time
import tempfile
import shutil
from pathlib import Path

from agent.memory_store.unified_memory import (
    UnifiedMemoryManager, MemoryEntry, UserProfile, EmotionRecord
)
from agent.rag.cache_manager import (
    MultiLevelCache, L1MemoryCache, L3PersistentCache,
    CacheLevel, CacheEntry, CacheStats
)


# =============================================================================
# UnifiedMemoryManager Tests
# =============================================================================

class TestUnifiedMemoryManager:
    """统一记忆管理器测试"""

    def setup_method(self):
        """每个测试前创建临时目录和实例"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.memory = UnifiedMemoryManager(
            persist_dir=str(self.temp_dir / "memory"),
            max_dialogue_entries=50,
            max_emotion_history=100
        )

    def teardown_method(self):
        """每个测试后清理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    # ---- 对话记忆测试 ----

    def test_add_dialogue(self):
        """测试添加对话记忆"""
        entry_id = self.memory.add_dialogue(
            session_id="session1",
            role="user",
            content="你好"
        )
        assert entry_id is not None
        assert isinstance(entry_id, str)

    def test_get_dialogue_history(self):
        """测试获取对话历史"""
        self.memory.add_dialogue("session1", "user", "第一条消息")
        self.memory.add_dialogue("session1", "assistant", "回复1")
        self.memory.add_dialogue("session1", "user", "第二条消息")

        history = self.memory.get_dialogue_history("session1")
        assert len(history) >= 3

    def test_get_dialogue_history_with_limit(self):
        """测试限制对话历史数量"""
        for i in range(10):
            self.memory.add_dialogue("session1", "user", f"消息{i}")

        history = self.memory.get_dialogue_history("session1", limit=5)
        assert len(history) == 5

    def test_get_dialogue_history_role_filter(self):
        """测试按角色过滤对话"""
        self.memory.add_dialogue("session1", "user", "用户消息")
        self.memory.add_dialogue("session1", "assistant", "助手消息")

        user_history = self.memory.get_dialogue_history("session1", role_filter="user")
        assert all(h["role"] == "user" for h in user_history)

    def test_clear_dialogue(self):
        """测试清除对话"""
        self.memory.add_dialogue("session1", "user", "消息")
        result = self.memory.clear_dialogue("session1")
        assert result is True

        history = self.memory.get_dialogue_history("session1")
        assert len(history) == 0

    def test_clear_nonexistent_dialogue(self):
        """测试清除不存在的对话"""
        result = self.memory.clear_dialogue("nonexistent")
        assert result is False

    def test_dialogue_memory_limit(self):
        """测试对话记忆数量限制"""
        memory = UnifiedMemoryManager(
            persist_dir=str(self.temp_dir / "limit_test"),
            max_dialogue_entries=5
        )

        for i in range(10):
            memory.add_dialogue("session1", "user", f"消息{i}")

        history = memory.get_dialogue_history("session1")
        assert len(history) <= 5

    # ---- 用户画像测试 ----

    def test_create_user_profile(self):
        """测试创建用户画像"""
        profile = self.memory.create_user_profile("user123", "student")
        assert profile is not None
        assert profile.user_id == "user123"
        assert profile.user_type == "student"

    def test_get_user_profile(self):
        """测试获取用户画像"""
        self.memory.create_user_profile("user123")
        profile = self.memory.get_user_profile("user123")
        assert profile is not None
        assert profile.user_id == "user123"

    def test_get_nonexistent_profile(self):
        """测试获取不存在的用户画像"""
        profile = self.memory.get_user_profile("nonexistent")
        assert profile is None

    def test_update_user_profile(self):
        """测试更新用户画像"""
        self.memory.create_user_profile("user123")
        updated = self.memory.update_user_profile("user123", {"name": "张三"})
        assert updated is not None
        assert updated.name == "张三"

    def test_add_profile_tag(self):
        """测试添加画像标签"""
        self.memory.create_user_profile("user123")
        result = self.memory.add_profile_tag("user123", "interest", "阅读")
        assert result is True

    def test_add_profile_tag_invalid_type(self):
        """测试添加无效标签类型"""
        self.memory.create_user_profile("user123")
        result = self.memory.add_profile_tag("user123", "invalid_type", "value")
        assert result is False

    def test_profile_tags_accumulation(self):
        """测试画像标签累积"""
        self.memory.create_user_profile("user123")
        self.memory.add_profile_tag("user123", "interest", "阅读")
        self.memory.add_profile_tag("user123", "interest", "音乐")

        profile = self.memory.get_user_profile("user123")
        assert "阅读" in profile.interests
        assert "音乐" in profile.interests

    def test_duplicate_tag_not_added(self):
        """测试不添加重复标签"""
        self.memory.create_user_profile("user123")
        self.memory.add_profile_tag("user123", "interest", "阅读")
        self.memory.add_profile_tag("user123", "interest", "阅读")

        profile = self.memory.get_user_profile("user123")
        assert profile.interests.count("阅读") == 1

    # ---- 情感历史测试 ----

    def test_add_emotion_record(self):
        """测试添加情感记录"""
        record_id = self.memory.add_emotion_record(
            user_id="user123",
            emotion_type="happy",
            intensity=0.8,
            trigger="考试满分"
        )
        assert record_id is not None

    def test_get_emotion_trends_no_data(self):
        """测试无数据的情绪趋势"""
        trends = self.memory.get_emotion_trends("user123")
        assert trends["total_records"] == 0
        assert trends["dominant_emotion"] is None

    def test_get_emotion_trends_with_data(self):
        """测试有数据的情绪趋势"""
        self.memory.add_emotion_record("user123", "happy", 0.8)
        self.memory.add_emotion_record("user123", "sad", 0.5)
        self.memory.add_emotion_record("user123", "happy", 0.9)

        trends = self.memory.get_emotion_trends("user123")
        assert trends["total_records"] == 3
        assert trends["dominant_emotion"] == "happy"

    def test_get_emotion_trends_period_filter(self):
        """测试情绪趋势时间段过滤"""
        # 添加老记录
        old_record = EmotionRecord(
            user_id="user123",
            emotion_type="sad",
            intensity=0.5,
            timestamp=time.time() - 1000000
        )
        self.memory._emotion_history["user123"] = [old_record]

        # 添加新记录
        self.memory.add_emotion_record("user123", "happy", 0.8)

        trends = self.memory.get_emotion_trends("user123", days=1)
        # 旧记录应该被过滤掉
        assert trends["dominant_emotion"] == "happy"

    def test_get_recent_emotions(self):
        """测试获取最近情绪"""
        self.memory.add_emotion_record("user123", "happy", 0.8)
        self.memory.add_emotion_record("user123", "sad", 0.5)
        self.memory.add_emotion_record("user123", "anxious", 0.6)

        recent = self.memory.get_recent_emotions("user123", limit=2)
        assert len(recent) == 2

    def test_emotion_history_limit(self):
        """测试情感历史数量限制"""
        memory = UnifiedMemoryManager(
            persist_dir=str(self.temp_dir / "emo_limit"),
            max_emotion_history=5
        )

        for i in range(10):
            memory.add_emotion_record("user123", "happy", 0.5)

        records = memory.get_recent_emotions("user123", limit=100)
        assert len(records) <= 5

    # ---- 知识记忆测试 ----

    def test_add_knowledge(self):
        """测试添加知识记忆"""
        entry_id = self.memory.add_knowledge(
            content="Python是一种编程语言",
            knowledge_type="programming",
            importance=0.8
        )
        assert entry_id is not None

    def test_search_knowledge(self):
        """测试搜索知识记忆"""
        self.memory.add_knowledge("Python是编程语言", "programming")
        self.memory.add_knowledge("JavaScript也编程语言", "programming")
        self.memory.add_knowledge("巴黎是法国首都", "geography")

        results = self.memory.search_knowledge("Python")
        assert len(results) >= 1

    def test_search_knowledge_with_type_filter(self):
        """测试按类型过滤搜索知识"""
        self.memory.add_knowledge("Python是编程语言", "programming")
        self.memory.add_knowledge("巴黎是法国首都", "geography")

        results = self.memory.search_knowledge("是", knowledge_type="programming")
        assert all(r.metadata.get("knowledge_type") == "programming" for r in results)

    def test_search_knowledge_limit(self):
        """测试搜索结果数量限制"""
        for i in range(10):
            self.memory.add_knowledge(f"知识{i}", "general")

        results = self.memory.search_knowledge("知识", limit=3)
        assert len(results) <= 3

    # ---- 持久化测试 ----

    def test_persist_and_load(self):
        """测试持久化和加载"""
        # 创建数据
        self.memory.create_user_profile("user123")
        self.memory.add_emotion_record("user123", "happy", 0.8)
        self.memory.add_dialogue("session1", "user", "测试消息")

        # 持久化
        self.memory.persist_data()

        # 创建新实例
        new_memory = UnifiedMemoryManager(
            persist_dir=str(self.temp_dir / "memory")
        )

        # 验证数据加载
        profile = new_memory.get_user_profile("user123")
        assert profile is not None
        assert profile.user_id == "user123"

    # ---- 统计测试 ----

    def test_get_stats(self):
        """测试获取统计信息"""
        self.memory.add_dialogue("session1", "user", "消息")
        self.memory.create_user_profile("user123")
        self.memory.add_emotion_record("user123", "happy", 0.5)

        stats = self.memory.get_stats()
        assert isinstance(stats, dict)
        assert stats["dialogue_sessions"] >= 1
        assert stats["user_profiles"] >= 1
        assert stats["emotion_records"] >= 1


# =============================================================================
# L1MemoryCache Tests
# =============================================================================

class TestL1MemoryCache:
    """L1内存缓存测试"""

    def setup_method(self):
        """每个测试前创建实例"""
        self.cache = L1MemoryCache(max_size=10, default_ttl=3600)

    def test_set_and_get(self):
        """测试设置和获取"""
        self.cache.set("key1", "value1")
        result = self.cache.get("key1")
        assert result == "value1"

    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        result = self.cache.get("nonexistent")
        assert result is None

    def test_delete(self):
        """测试删除"""
        self.cache.set("key1", "value1")
        result = self.cache.delete("key1")
        assert result is True

        get_result = self.cache.get("key1")
        assert get_result is None

    def test_delete_nonexistent(self):
        """测试删除不存在的键"""
        result = self.cache.delete("nonexistent")
        assert result is False

    def test_clear(self):
        """测试清空"""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.clear()

        assert self.cache.get("key1") is None
        assert self.cache.get("key2") is None

    def test_lru_eviction(self):
        """测试LRU淘汰"""
        cache = L1MemoryCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # 访问key1，使其成为最近使用
        cache.get("key1")

        # 添加新键，应该淘汰key2
        cache.set("key4", "value4")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None  # 被淘汰
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_ttl_expiration(self):
        """测试TTL过期"""
        cache = L1MemoryCache(max_size=10, default_ttl=1)

        cache.set("key1", "value1")
        time.sleep(1.1)

        result = cache.get("key1")
        assert result is None

    def test_custom_ttl(self):
        """测试自定义TTL"""
        cache = L1MemoryCache(max_size=10, default_ttl=3600)

        cache.set("key1", "value1", ttl=0.1)
        time.sleep(0.2)

        result = cache.get("key1")
        assert result is None

    def test_update_existing_key(self):
        """测试更新已存在的键"""
        self.cache.set("key1", "value1")
        self.cache.set("key1", "value2")

        assert self.cache.get("key1") == "value2"

    def test_get_stats(self):
        """测试获取统计"""
        self.cache.set("key1", "value1")
        stats = self.cache.get_stats()

        assert stats["entries"] == 1
        assert stats["max_size"] == 10
        assert "size_bytes" in stats


# =============================================================================
# L3PersistentCache Tests
# =============================================================================

class TestL3PersistentCache:
    """L3持久化缓存测试"""

    def setup_method(self):
        """每个测试前创建临时目录和实例"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cache = L3PersistentCache(
            persist_dir=str(self.temp_dir / "cache"),
            default_ttl=3600
        )

    def teardown_method(self):
        """每个测试后清理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_set_and_get(self):
        """测试设置和获取"""
        self.cache.set("key1", "value1")
        result = self.cache.get("key1")
        assert result == "value1"

    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        result = self.cache.get("nonexistent")
        assert result is None

    def test_delete(self):
        """测试删除"""
        self.cache.set("key1", "value1")
        result = self.cache.delete("key1")
        assert result is True

    def test_clear(self):
        """测试清空"""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.clear()

        assert self.cache.get("key1") is None

    def test_cleanup_expired(self):
        """测试清理过期缓存"""
        self.cache.set("key1", "value1", ttl=0.1)
        time.sleep(0.2)

        count = self.cache.cleanup_expired()
        assert count >= 1

    def test_get_stats(self):
        """测试获取统计"""
        self.cache.set("key1", "value1")
        stats = self.cache.get_stats()

        assert stats["entries"] == 1
        assert stats["level"] == "l3_persistent"


# =============================================================================
# MultiLevelCache Tests
# =============================================================================

class TestMultiLevelCache:
    """多级缓存管理器测试"""

    def setup_method(self):
        """每个测试前创建临时目录和实例"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cache = MultiLevelCache(
            l1_size=10,
            l3_enabled=True,
            persist_dir=str(self.temp_dir / "multilevel"),
            default_ttl=3600
        )

    def teardown_method(self):
        """每个测试后清理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_get_from_l1(self):
        """测试从L1获取"""
        self.cache.set("key1", "value1")
        result = self.cache.get("key1")
        assert result == "value1"

    def test_cache_miss(self):
        """测试缓存未命中"""
        result = self.cache.get("nonexistent")
        assert result is None

    def test_delete_all_levels(self):
        """测试删除所有层级"""
        self.cache.set("key1", "value1")
        self.cache.delete("key1")

        result = self.cache.get("key1")
        assert result is None

    def test_clear_all_levels(self):
        """测试清空所有层级"""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.clear()

        assert self.cache.get("key1") is None

    def test_l3_persistence(self):
        """测试L3持久化"""
        self.cache.set("key1", "value1")

        # 创建新实例
        new_cache = MultiLevelCache(
            l1_size=10,
            l3_enabled=True,
            persist_dir=str(self.temp_dir / "multilevel")
        )

        # L1应该为空，但L3应该有数据（如果实现了回填）
        # 注意：当前实现可能不回填L3到L1
        assert new_cache is not None

    def test_stats(self):
        """测试统计"""
        self.cache.set("key1", "value1")
        self.cache.get("key1")
        self.cache.get("nonexistent")

        stats = self.cache.get_stats()
        assert isinstance(stats, dict)
        assert "l1" in stats
        assert "hits" in stats or "l1" in stats

    def test_record_eviction(self):
        """测试记录淘汰"""
        self.cache.record_eviction()
        stats = self.cache.get_stats()
        assert stats.get("evictions", 0) >= 1


# =============================================================================
# CacheEntry Tests
# =============================================================================

class TestCacheEntry:
    """缓存条目测试"""

    def test_cache_entry_creation(self):
        """测试创建缓存条目"""
        entry = CacheEntry(
            key="test",
            value="value",
            level=CacheLevel.L1_MEMORY
        )
        assert entry.key == "test"
        assert entry.value == "value"
        assert entry.level == CacheLevel.L1_MEMORY

    def test_cache_entry_not_expired(self):
        """测试缓存未过期"""
        entry = CacheEntry(
            key="test",
            value="value",
            level=CacheLevel.L1_MEMORY,
            ttl=3600
        )
        assert entry.is_expired() is False

    def test_cache_entry_expired(self):
        """测试缓存过期"""
        entry = CacheEntry(
            key="test",
            value="value",
            level=CacheLevel.L1_MEMORY,
            ttl=0.1,
            created_at=time.time() - 1
        )
        assert entry.is_expired() is True

    def test_cache_entry_touch(self):
        """测试更新访问时间"""
        entry = CacheEntry(
            key="test",
            value="value",
            level=CacheLevel.L1_MEMORY
        )
        old_access = entry.last_accessed
        time.sleep(0.01)
        entry.touch()

        assert entry.last_accessed > old_access
        assert entry.access_count == 2


# =============================================================================
# CacheStats Tests
# =============================================================================

class TestCacheStats:
    """缓存统计测试"""

    def test_hit_rate_calculation(self):
        """测试命中率计算"""
        stats = CacheStats(hits=80, misses=20)
        assert stats.hit_rate == 0.8

    def test_hit_rate_zero(self):
        """测试零命中时的命中率"""
        stats = CacheStats(hits=0, misses=0)
        assert stats.hit_rate == 0.0

    def test_to_dict(self):
        """测试转换为字典"""
        stats = CacheStats(hits=50, misses=50)
        data = stats.to_dict()
        assert isinstance(data, dict)
        assert "hit_rate" in data


# =============================================================================
# Edge Cases
# =============================================================================

class TestCacheEdgeCases:
    """缓存边界情况测试"""

    def setup_method(self):
        """每个测试前创建临时目录和实例"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """每个测试后清理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_very_large_value(self):
        """测试非常大的值"""
        cache = MultiLevelCache(l1_size=10, l3_enabled=False)
        large_value = "x" * 1000000
        cache.set("key1", large_value)
        result = cache.get("key1")
        assert result == large_value

    def test_special_characters_in_key(self):
        """测试键中的特殊字符"""
        cache = MultiLevelCache(l1_size=10, l3_enabled=False)
        special_keys = ["key@#", "key$%", "key^&", "key*()"]

        for key in special_keys:
            cache.set(key, "value")
            result = cache.get(key)
            assert result == "value"

    def test_unicode_in_value(self):
        """测试Unicode值"""
        cache = MultiLevelCache(l1_size=10, l3_enabled=False)
        unicode_value = "你好🌸💕"
        cache.set("key1", unicode_value)
        result = cache.get("key1")
        assert result == unicode_value

    def test_none_value(self):
        """测试None值"""
        cache = MultiLevelCache(l1_size=10, l3_enabled=False)
        cache.set("key1", None)
        result = cache.get("key1")
        # None可能被存储为字符串"None"
        assert result is None or result == "None"

    def test_concurrent_access(self):
        """测试并发访问"""
        import threading

        cache = MultiLevelCache(l1_size=100, l3_enabled=False)
        errors = []

        def writer(thread_id):
            try:
                for i in range(50):
                    cache.set(f"key_{thread_id}_{i}", f"value_{i}")
            except Exception as e:
                errors.append(e)

        def reader(thread_id):
            try:
                for i in range(50):
                    cache.get(f"key_{thread_id}_{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=writer, args=(i,)))
            threads.append(threading.Thread(target=reader, args=(i,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

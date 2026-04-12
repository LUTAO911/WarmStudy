"""
Unit tests for Memory module
"""
import time
import threading
import pytest
from typing import List

from agent.memory import (
    MemoryEntry,
    ShortTermMemory,
    LongTermMemory,
    MemoryManager,
    ThreadSafeList,
    ThreadSafeDict,
)


class TestMemoryEntry:
    """Tests for MemoryEntry dataclass."""

    def test_create_entry_success(self) -> None:
        """Test creating a memory entry with required fields."""
        entry = MemoryEntry(
            id="test123",
            role="user",
            content="Hello world",
            timestamp=time.time(),
        )
        assert entry.id == "test123"
        assert entry.role == "user"
        assert entry.content == "Hello world"
        assert entry.metadata == ()

    def test_create_entry_with_metadata(self) -> None:
        """Test creating a memory entry with metadata."""
        entry = MemoryEntry(
            id="test456",
            role="assistant",
            content="Response message",
            timestamp=time.time(),
            metadata={"session_id": "sess123", "token_count": 42},
        )
        assert entry.metadata_dict == {"session_id": "sess123", "token_count": 42}

    def test_entry_to_dict(self) -> None:
        """Test converting entry to dictionary."""
        entry = MemoryEntry(
            id="test789",
            role="system",
            content="System message",
            timestamp=1700000000.0,
        )
        result = entry.to_dict()
        assert result["id"] == "test789"
        assert result["role"] == "system"
        assert result["content"] == "System message"
        assert result["timestamp"] == 1700000000.0

    def test_entry_from_dict(self) -> None:
        """Test creating entry from dictionary."""
        data = {
            "id": "test000",
            "role": "user",
            "content": "Test content",
            "timestamp": 1700000000.0,
            "metadata": {"key": "value"},
        }
        entry = MemoryEntry.from_dict(data)
        assert entry.id == "test000"
        assert entry.metadata_dict == {"key": "value"}


class TestThreadSafeList:
    """Tests for ThreadSafeList."""

    def test_append_and_length(self) -> None:
        """Test appending items and checking length."""
        ts_list = ThreadSafeList()
        ts_list.append("item1")
        ts_list.append("item2")
        assert len(ts_list) == 2

    def test_get_item(self) -> None:
        """Test getting item by index."""
        ts_list = ThreadSafeList(["a", "b", "c"])
        assert ts_list[0] == "a"
        assert ts_list[1] == "b"

    def test_pop(self) -> None:
        """Test popping items."""
        ts_list = ThreadSafeList([1, 2, 3])
        popped = ts_list.pop()
        assert popped == 3
        assert len(ts_list) == 2

    def test_clear(self) -> None:
        """Test clearing the list."""
        ts_list = ThreadSafeList(["a", "b"])
        ts_list.clear()
        assert len(ts_list) == 0

    def test_filter(self) -> None:
        """Test filtering items."""
        ts_list = ThreadSafeList([1, 2, 3, 4, 5])
        filtered = ts_list.filter(lambda x: x > 2)
        assert filtered == [3, 4, 5]

    def test_concurrent_access(self) -> None:
        """Test concurrent access to the list."""
        ts_list = ThreadSafeList()
        errors: List[Exception] = []

        def writer(thread_id: int) -> None:
            for i in range(100):
                try:
                    ts_list.append(f"t{thread_id}-{i}")
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(ts_list) == 500


class TestThreadSafeDict:
    """Tests for ThreadSafeDict."""

    def test_set_and_get(self) -> None:
        """Test setting and getting values."""
        ts_dict = ThreadSafeDict()
        ts_dict["key1"] = "value1"
        assert ts_dict["key1"] == "value1"

    def test_get_with_default(self) -> None:
        """Test getting with default value."""
        ts_dict = ThreadSafeDict()
        result = ts_dict.get("nonexistent", "default")
        assert result == "default"

    def test_contains(self) -> None:
        """Test containment check."""
        ts_dict = ThreadSafeDict({"key": "value"})
        assert "key" in ts_dict
        assert "other" not in ts_dict

    def test_keys_values_items(self) -> None:
        """Test keys, values, and items methods."""
        ts_dict = ThreadSafeDict({"a": 1, "b": 2})
        assert set(ts_dict.keys()) == {"a", "b"}
        assert set(ts_dict.values()) == {1, 2}
        assert set(ts_dict.items()) == {("a", 1), ("b", 2)}


class TestShortTermMemory:
    """Tests for ShortTermMemory."""

    def test_add_entry(self) -> None:
        """Test adding entries to short term memory."""
        memory = ShortTermMemory(max_entries=50, ttl_seconds=3600)
        entry_id = memory.add("user", "Hello")
        assert entry_id is not None
        assert len(memory) == 1

    def test_get_recent(self) -> None:
        """Test getting recent entries."""
        memory = ShortTermMemory()
        memory.add("user", "First")
        memory.add("user", "Second")
        memory.add("user", "Third")
        recent = memory.get_recent(2)
        assert len(recent) == 2
        assert recent[-1].content == "Third"

    def test_ttl_expiration(self) -> None:
        """Test that TTL expiration works."""
        memory = ShortTermMemory(ttl_seconds=1)
        memory.add("user", "Will expire")
        time.sleep(1.1)
        recent = memory.get_recent()
        assert len(recent) == 0

    def test_max_entries_limit(self) -> None:
        """Test that max entries limit is enforced."""
        memory = ShortTermMemory(max_entries=5)
        for i in range(10):
            memory.add("user", f"Message {i}")
        assert len(memory.get_all()) == 5

    def test_search(self) -> None:
        """Test searching entries."""
        memory = ShortTermMemory()
        memory.add("user", "Hello world")
        memory.add("assistant", "Hi there")
        results = memory.search("hello")
        assert len(results) == 1
        assert "Hello world" in results[0].content


class TestLongTermMemory:
    """Tests for LongTermMemory with temporary directory."""

    def test_add_and_retrieve(self, temp_dir: "Path") -> None:
        """Test adding and retrieving entries."""
        memory = LongTermMemory(persist_dir=str(temp_dir / "ltm"))
        entry_id = memory.add("user", "Long term message")
        assert entry_id is not None

        recent = memory.get_recent()
        assert len(recent) == 1
        assert recent[0].content == "Long term message"

    def test_search(self, temp_dir: "Path") -> None:
        """Test searching in long term memory."""
        memory = LongTermMemory(persist_dir=str(temp_dir / "ltm_search"))
        memory.add("user", "Python is great")
        memory.add("user", "JavaScript is popular")
        memory.add("assistant", "Python has typing")

        results = memory.search("python")
        assert len(results) == 2

    def test_clear(self, temp_dir: "Path") -> None:
        """Test clearing long term memory."""
        memory = LongTermMemory(persist_dir=str(temp_dir / "ltm_clear"))
        memory.add("user", "Message 1")
        memory.add("user", "Message 2")
        assert len(memory.get_all()) == 2

        memory.clear()
        assert len(memory.get_all()) == 0


class TestMemoryManager:
    """Tests for MemoryManager."""

    def test_add_user_message(self) -> None:
        """Test adding user messages."""
        manager = MemoryManager()
        entry_id = manager.add_user_message("Hello")
        assert entry_id is not None

    def test_add_assistant_message_sync(self, temp_dir: "Path") -> None:
        """Test that assistant messages sync to long term."""
        manager = MemoryManager(long_term_persist_dir=str(temp_dir / "manager"))
        manager.add_user_message("Hello")
        entry_id = manager.add_assistant_message("Hi there!")

        assert entry_id is not None
        context = manager.get_relevant_context("Hi")
        assert "Hi there!" in context

    def test_conversation_history(self) -> None:
        """Test getting conversation history."""
        manager = MemoryManager()
        manager.add_user_message("First")
        manager.add_assistant_message("Second")
        manager.add_user_message("Third")

        history = manager.get_conversation_history(limit=10)
        assert "First" in history
        assert "Second" in history
        assert "Third" in history

    def test_clear_short_term(self) -> None:
        """Test clearing short term memory."""
        manager = MemoryManager()
        manager.add_user_message("Temporary")
        manager.clear_short_term()
        history = manager.get_conversation_history()
        assert "Temporary" not in history

    def test_session_summary(self) -> None:
        """Test getting session summary."""
        manager = MemoryManager()
        manager.add_user_message("Message 1")
        manager.add_user_message("Message 2")

        summary = manager.get_session_summary()
        assert summary["short_term_count"] == 2
        assert summary["long_term_count"] == 0
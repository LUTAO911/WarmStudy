"""
Unit tests for Context module
"""
import time
import pytest
from typing import List

from agent.context import (
    ContextEntry,
    Context,
    ContextManager,
)


class TestContextEntry:
    """Tests for ContextEntry dataclass."""

    def test_create_entry(self) -> None:
        """Test creating a context entry."""
        entry = ContextEntry(
            id="entry123",
            type="knowledge",
            content="Important information",
            relevance_score=0.95,
            timestamp=time.time(),
            source="document.pdf",
            metadata=(),
        )
        assert entry.id == "entry123"
        assert entry.type == "knowledge"
        assert entry.relevance_score == 0.95

    def test_entry_to_dict(self) -> None:
        """Test converting entry to dictionary."""
        entry = ContextEntry(
            id="entry456",
            type="memory",
            content="User preference",
            relevance_score=0.85,
            timestamp=1700000000.0,
            source="session",
            metadata=(("key", "value"),),
        )
        data = entry.to_dict()
        assert data["id"] == "entry456"
        assert data["type"] == "memory"
        assert data["metadata"] == {"key": "value"}


class TestContext:
    """Tests for Context class."""

    def test_add_entry(self) -> None:
        """Test adding entries to context."""
        context = Context()
        entry = context.add_entry(
            content_type="knowledge",
            content="Test content",
            relevance_score=0.9,
        )
        assert entry is not None
        assert len(context) == 1

    def test_get_recent(self) -> None:
        """Test getting recent entries."""
        context = Context()
        for i in range(5):
            context.add_entry("message", f"Content {i}")
        recent = context.get_recent(3)
        assert len(recent) == 3

    def test_get_by_type(self) -> None:
        """Test filtering entries by type."""
        context = Context()
        context.add_entry("knowledge", "Fact 1")
        context.add_entry("memory", "Memory 1")
        context.add_entry("knowledge", "Fact 2")

        knowledge_entries = context.get_by_type("knowledge")
        assert len(knowledge_entries) == 2

    def test_get_relevant(self) -> None:
        """Test filtering by relevance score."""
        context = Context()
        context.add_entry("test", "Low relevance", relevance_score=0.3)
        context.add_entry("test", "High relevance", relevance_score=0.9)

        relevant = context.get_relevant(min_score=0.5)
        assert len(relevant) == 1
        assert relevant[0].content == "High relevance"

    def test_max_entries_limit(self) -> None:
        """Test that max entries limit is enforced."""
        context = Context(max_entries=10)
        for i in range(20):
            context.add_entry("test", f"Entry {i}")
        assert len(context) == 10

    def test_clear(self) -> None:
        """Test clearing context."""
        context = Context()
        context.add_entry("test", "Content")
        context.clear()
        assert len(context) == 0

    def test_context_summary(self) -> None:
        """Test getting context summary."""
        context = Context()
        context.add_entry("knowledge", "A" * 300)
        context.add_entry("memory", "Short memory")

        summary = context.get_context_summary()
        assert len(summary) > 0
        assert "knowledge" in summary

    def test_merge(self) -> None:
        """Test merging two contexts."""
        context1 = Context()
        context1.add_entry("type1", "Content 1")

        context2 = Context()
        context2.add_entry("type2", "Content 2")

        context1.merge(context2)
        assert len(context1) == 2


class TestContextManager:
    """Tests for ContextManager."""

    def test_get_default_context(self) -> None:
        """Test getting default context."""
        manager = ContextManager()
        context = manager.get_context()
        assert context is not None
        assert context.session_id == "default"

    def test_create_named_context(self) -> None:
        """Test creating a named context."""
        manager = ContextManager()
        context = manager.create_context("my_session")
        assert context.session_id == "my_session"

    def test_get_existing_context(self) -> None:
        """Test getting an existing context."""
        manager = ContextManager()
        context1 = manager.get_context("session1")
        context1.add_entry("test", "Content")

        context2 = manager.get_context("session1")
        assert len(context2) == 1

    def test_delete_context(self) -> None:
        """Test deleting a context."""
        manager = ContextManager()
        manager.create_context("to_delete")
        assert manager.delete_context("to_delete") is True
        assert manager.delete_context("nonexistent") is False

    def test_add_knowledge_context(self) -> None:
        """Test adding knowledge context."""
        manager = ContextManager()
        docs = [
            {"content": "Document 1", "source": "file1.txt", "similarity": 0.95},
            {"content": "Document 2", "source": "file2.txt", "similarity": 0.85},
        ]
        manager.add_knowledge_context("session1", docs, "query")

        context = manager.get_context("session1")
        entries = context.get_by_type("knowledge")
        assert len(entries) == 2

    def test_build_context_prompt(self) -> None:
        """Test building context prompt."""
        manager = ContextManager()
        manager.update_context("session1", "knowledge", "Paris is in France")
        manager.update_context("session1", "memory", "User likes art")

        prompt = manager.build_context_prompt(
            "session1",
            include_types=["knowledge"],
            max_entries=10
        )
        assert "Paris" in prompt
        assert "art" not in prompt

    def test_context_stats(self) -> None:
        """Test getting context statistics."""
        manager = ContextManager()
        manager.update_context("session1", "knowledge", "Fact 1")
        manager.update_context("session1", "knowledge", "Fact 2")
        manager.update_context("session1", "memory", "Memory")

        stats = manager.get_context_stats("session1")
        assert stats["total_entries"] == 3
        assert stats["type_counts"]["knowledge"] == 2
        assert stats["type_counts"]["memory"] == 1

    def test_list_sessions(self) -> None:
        """Test listing all sessions."""
        manager = ContextManager()
        manager.create_context("session1")
        manager.create_context("session2")

        sessions = manager.list_sessions()
        assert "default" in sessions
        assert "session1" in sessions
        assert "session2" in sessions

    def test_cleanup_inactive_sessions(self) -> None:
        """Test cleaning up inactive sessions."""
        manager = ContextManager()
        manager.create_context("old_session")

        cleaned = manager.cleanup_inactive_sessions(max_age_seconds=0.1)
        time.sleep(0.2)
        cleaned = manager.cleanup_inactive_sessions(max_age_seconds=0.1)
        assert cleaned >= 1

    def test_clear_session(self) -> None:
        """Test clearing a specific session."""
        manager = ContextManager()
        manager.update_context("session1", "test", "Content")
        manager.clear_session("session1")

        stats = manager.get_context_stats("session1")
        assert stats["total_entries"] == 0
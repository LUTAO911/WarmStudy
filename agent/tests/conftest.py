"""
Pytest configuration and fixtures for agent testing
"""
import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("DASHSCOPE_API_KEY", "test_key_for_testing")
os.environ.setdefault("AGENT_API_KEY", "test_api_key_12345")


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing file operations."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def sample_memory_data() -> dict:
    """Sample memory data for testing."""
    return {
        "messages": [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"},
            {"role": "user", "content": "Tell me about the weather."},
        ]
    }


@pytest.fixture
def sample_tool_result() -> dict:
    """Sample tool result for testing."""
    return {
        "tool_name": "test_tool",
        "status": "success",
        "result": {"output": "test result"},
        "execution_time": 0.123
    }


@pytest.fixture
def sample_context_data() -> dict:
    """Sample context data for testing."""
    return {
        "session_id": "test_session_123",
        "entries": [
            {"type": "knowledge", "content": "Paris is the capital of France.", "relevance_score": 0.95},
            {"type": "memory", "content": "User asked about Paris.", "relevance_score": 0.85},
        ]
    }


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all singleton instances before each test."""
    from agent.memory import MemoryManager
    from agent.tools import ToolRegistry
    from agent.skills import SkillRegistry
    from agent.prompts import PromptManager
    from agent.core.agent import AgentManager
    from agent.utils.monitor import PerformanceMonitor
    from agent.utils.logger import AgentLogger
    from agent.api.auth import AuthManager

    MemoryManager.reset_instance() if hasattr(MemoryManager, 'reset_instance') else None
    ToolRegistry.reset_instance() if hasattr(ToolRegistry, 'reset_instance') else None
    SkillRegistry.reset_instance() if hasattr(SkillRegistry, 'reset_instance') else None
    PromptManager.reset_instance() if hasattr(PromptManager, 'reset_instance') else None
    AgentManager.reset_instance() if hasattr(AgentManager, 'reset_instance') else None
    PerformanceMonitor.reset_instance() if hasattr(PerformanceMonitor, 'reset_instance') else None
    AuthManager.reset_instance() if hasattr(AuthManager, 'reset_instance') else None

    yield

    MemoryManager.reset_instance() if hasattr(MemoryManager, 'reset_instance') else None
    ToolRegistry.reset_instance() if hasattr(ToolRegistry, 'reset_instance') else None
    SkillRegistry.reset_instance() if hasattr(SkillRegistry, 'reset_instance') else None
    PromptManager.reset_instance() if hasattr(PromptManager, 'reset_instance') else None
    AgentManager.reset_instance() if hasattr(AgentManager, 'reset_instance') else None
    PerformanceMonitor.reset_instance() if hasattr(PerformanceMonitor, 'reset_instance') else None
    AuthManager.reset_instance() if hasattr(AuthManager, 'reset_instance') else None
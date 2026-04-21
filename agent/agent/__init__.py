"""
Agent Module - 智能体后端服务核心模块
"""
from .memory import MemoryManager, ShortTermMemory, LongTermMemory
from .tool_registry import Tool, ToolRegistry, ToolResult, setup_builtin_tools
from .context import ContextManager, Context
from .skills import Skill, SkillRegistry, SkillResult, setup_builtin_skills
from .prompts import PromptTemplate, PromptManager
from .core import Agent, AgentConfig, AgentResponse, AgentManager, AgentMode

# 新增核心模块
from .core import (
    Orchestrator,
    OrchestratorConfig,
    ConversationMode,
    UserMessage,
    IntentRouter,
    Intent,
    IntentType,
    RouteContext,
    # 工作流引擎
    WorkflowEngine,
    WorkflowPlan,
    WorkflowResult,
    Task,
    TaskType,
    TaskPriority,
    TaskStatus,
)

# 新增工具模块
from .tools import (
    ToolSelector,
    ToolMatch,
    SelectionResult,
)

# 新增上下文生命周期
from .context import (
    ContextLifecycle,
    ContextScope,
    ContextTTL,
    ContextEntry,
    ContextPipeline,
    PipelineStage,
    PipelineResult,
)

# 新增分层记忆系统
from .memory_store import (
    UnifiedMemoryManager,
    MemoryEntry,
    UserProfile,
    EmotionRecord,
)

# 新增心理学模块
from .modules.psychology_module import (
    PsychologyModule,
    EmotionInfo,
    CrisisInfo,
    PersonalityProfile,
    EmotionLevel,
    CrisisLevel,
)

# 新增RAG模块
from .rag import (
    RAGEngine,
    RAGQuery,
    RAGResult,
    RetrievalResult,
    MultiLevelCache,
    CacheLevel,
    CacheStats,
    get_global_cache,
)

__all__ = [
    # 原有模块
    "MemoryManager",
    "ShortTermMemory",
    "LongTermMemory",
    "Tool",
    "ToolRegistry",
    "ToolResult",
    "setup_builtin_tools",
    "ContextManager",
    "Context",
    "Skill",
    "SkillRegistry",
    "SkillResult",
    "setup_builtin_skills",
    "PromptTemplate",
    "PromptManager",
    "Agent",
    "AgentConfig",
    "AgentResponse",
    "AgentManager",
    "AgentMode",
    # 新增核心模块
    "Orchestrator",
    "OrchestratorConfig",
    "ConversationMode",
    "UserMessage",
    "IntentRouter",
    "Intent",
    "IntentType",
    "RouteContext",
    # 工作流引擎
    "WorkflowEngine",
    "WorkflowPlan",
    "WorkflowResult",
    "Task",
    "TaskType",
    "TaskPriority",
    "TaskStatus",
    # 工具选择器
    "ToolSelector",
    "ToolMatch",
    "SelectionResult",
    # 新增上下文模块
    "ContextLifecycle",
    "ContextScope",
    "ContextTTL",
    "ContextEntry",
    "ContextPipeline",
    "PipelineStage",
    "PipelineResult",
    # 新增分层记忆
    "UnifiedMemoryManager",
    "MemoryEntry",
    "UserProfile",
    "EmotionRecord",
    # 新增心理学模块
    "PsychologyModule",
    "EmotionInfo",
    "CrisisInfo",
    "PersonalityProfile",
    "EmotionLevel",
    "CrisisLevel",
    # 新增RAG模块
    "RAGEngine",
    "RAGQuery",
    "RAGResult",
    "RetrievalResult",
    "MultiLevelCache",
    "CacheLevel",
    "CacheStats",
    "get_global_cache",
]

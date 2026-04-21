"""
Core Module - Agent 核心模块

原有模块（保持向后兼容）：
- Agent, AgentConfig, AgentResponse, AgentManager, AgentMode

新增模块（v5架构）：
- Orchestrator: 主编排引擎
- IntentRouter: 意图路由
- WorkflowEngine: 工作流引擎
"""
from .agent import Agent, AgentConfig, AgentResponse, AgentManager, AgentMode
from .orchestrator import Orchestrator, OrchestratorConfig, ConversationMode, UserMessage
from .intent_router import IntentRouter, Intent, IntentType, RouteContext
from .workflow_engine import WorkflowEngine, WorkflowPlan, WorkflowResult, Task, TaskType, TaskPriority, TaskStatus

__all__ = [
    # 原有（向后兼容）
    "Agent",
    "AgentConfig",
    "AgentResponse",
    "AgentManager",
    "AgentMode",
    # 新增
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
]

"""
Tools Module - 工具模块
"""
from .tool_selector import (
    ToolSelector,
    ToolMatch,
    SelectionResult,
    select_tools_for_message,
    MatchConfidence,
)
from agent.tool_registry import (
    ToolResult,
    ToolStatus,
    ToolParameter,
    ToolSchema,
    Tool,
    ToolRegistry,
    BuiltinTools,
    SafeCalculator,
    setup_builtin_tools,
)

# 从 tool_registry 重新导出（测试兼容性）
from ..tool_registry import (
    Tool,
    ToolRegistry,
    ToolResult,
    ToolStatus,
    ToolParameter,
    ToolSchema,
    BuiltinTools,
    SafeCalculator,
    setup_builtin_tools,
)

__all__ = [
    # tool_selector
    "ToolSelector",
    "ToolMatch",
    "SelectionResult",
    "select_tools_for_message",
    "MatchConfidence",
    # tool_registry (re-exports)
    "Tool",
    "ToolRegistry",
    "ToolResult",
    "ToolStatus",
    "ToolParameter",
    "ToolSchema",
    "BuiltinTools",
    "SafeCalculator",
    "setup_builtin_tools",
]

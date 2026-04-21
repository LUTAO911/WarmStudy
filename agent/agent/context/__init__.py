"""
Context Module - 上下文管理模块
"""
# 兼容层：从context_core导入原来的内容
from agent.context_core import ContextManager, Context, ContextEntry

# 新的生命周期管理
from agent.context.context_lifecycle import ContextLifecycle, ContextScope, ContextTTL
from agent.context.context_pipeline import ContextPipeline, PipelineStage, PipelineResult

__all__ = [
    # 原有类（兼容）
    "ContextManager",
    "Context",
    # 新增类
    "ContextLifecycle",
    "ContextScope",
    "ContextTTL",
    "ContextEntry",
    "ContextPipeline",
    "PipelineStage",
    "PipelineResult",
]

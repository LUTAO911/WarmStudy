"""
Agent API Routes v5 - 新架构API路由
基于 Orchestrator 的标准化API端点
"""
import time
import uuid
from typing import Optional, Dict, Any
from flask import Blueprint, request, jsonify
from datetime import datetime

from .auth import require_auth
from .schemas import (
    ChatRequest, ChatResponse,
    EmotionCheckRequest, EmotionResponse,
    CrisisCheckRequest, CrisisResponse,
    PsychologyRequest,
)
from agent.core.orchestrator import Orchestrator, OrchestratorConfig
from agent.core.intent_router import IntentRouter, RouteContext
from agent.memory import MemoryManager
from agent.memory_store import UnifiedMemoryManager
from agent.context import ContextManager
from agent.tool_registry import ToolRegistry, setup_builtin_tools
from agent.modules.psychology_module import PsychologyModule

# 新架构 Blueprint
v5_bp = Blueprint("agent_v5", __name__, url_prefix="/api/v5")

# 全局实例
_orchestrator: Optional[Orchestrator] = None
_intent_router: Optional[IntentRouter] = None
_memory_manager: Optional[MemoryManager] = None
_unified_memory: Optional[UnifiedMemoryManager] = None
_context_manager: Optional[ContextManager] = None
_tool_registry: Optional[ToolRegistry] = None
_psychology_module: Optional[PsychologyModule] = None


def get_orchestrator() -> Orchestrator:
    """获取或创建 Orchestrator 实例"""
    global _orchestrator, _intent_router, _memory_manager, _unified_memory, _context_manager, _tool_registry, _psychology_module

    if _orchestrator is None:
        # 初始化组件
        _memory_manager = MemoryManager()
        _unified_memory = UnifiedMemoryManager()
        _context_manager = ContextManager()
        _tool_registry = ToolRegistry()
        _psychology_module = PsychologyModule()

        if len(_tool_registry.get_all()) == 0:
            setup_builtin_tools()

        # 创建编排器
        config = OrchestratorConfig(
            name="暖学帮-v5",
            enable_rag=True,
            enable_tools=True,
            enable_psychology=True,
            max_workflow_steps=5,
        )
        _orchestrator = Orchestrator(
            config=config,
            memory_manager=_memory_manager,
            unified_memory=_unified_memory,
            psychology_module=_psychology_module,
            context_manager=_context_manager,
            tool_registry=_tool_registry,
        )
        _intent_router = IntentRouter()

    return _orchestrator


# ========== v5 API 端点 ==========

@v5_bp.route("/chat", methods=["POST"])
def chat():
    """
    v5 对话接口 - 使用新的 Orchestrator

    请求体:
    {
        "message": "用户消息",
        "session_id": "可选的会话ID",
        "user_type": "student|parent|teacher",
        "use_rag": true,
        "use_tools": true
    }
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())[:12]

    try:
        data = request.get_json()

        message = data.get("message", "").strip()
        session_id = data.get("session_id", "default")
        user_id = data.get("user_id")
        user_type = data.get("user_type", "student")
        use_rag = data.get("use_rag", True)
        use_tools = data.get("use_tools", True)

        if not message:
            return jsonify({
                "status": "error",
                "error": {"code": "VALIDATION_ERROR", "message": "消息不能为空"},
                "request_id": request_id
            }), 400

        # 使用 Orchestrator 处理（同步调用）
        orchestrator = get_orchestrator()
        response = orchestrator.chat(
            message=message,
            session_id=session_id,
            user_id=user_id,
            user_type=user_type,
        )

        execution_time = time.time() - start_time

        # 构建响应
        resp_data = {
            "status": "success",
            "data": {
                "answer": response.content,
                "mode": response.mode.value,
                "emotion": response.emotion.to_dict() if response.emotion else None,
                "crisis_level": response.crisis_level,
                "sources": response.sources,
                "tool_results": response.tool_results,
                "session_id": session_id,
                "execution_time": round(execution_time, 3),
            },
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        }

        return jsonify(resp_data)

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            },
            "request_id": request_id
        }), 500


@v5_bp.route("/intent/route", methods=["POST"])
def route_intent():
    """
    意图路由接口 - 智能判断用户意图

    请求体:
    {
        "message": "用户消息",
        "session_id": "会话ID",
        "user_type": "student"
    }
    """
    request_id = str(uuid.uuid4())[:12]

    try:
        data = request.get_json()
        message = data.get("message", "").strip()

        if not message:
            return jsonify({
                "status": "error",
                "error": {"code": "VALIDATION_ERROR", "message": "消息不能为空"},
                "request_id": request_id
            }), 400

        session_id = data.get("session_id", "default")
        user_type = data.get("user_type", "student")

        intent_router = IntentRouter()
        context = RouteContext(
            message=message,
            session_id=session_id,
            user_type=user_type
        )
        intent = intent_router.route(message, context)

        return jsonify({
            "status": "success",
            "data": {
                "primary_intent": intent.primary.value,
                "confidence": intent.confidence,
                "mode": intent.mode.value,
                "reasoning": intent.reasoning,
                "metadata": intent.metadata
            },
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            "request_id": request_id
        }), 500


@v5_bp.route("/emotion/detect", methods=["POST"])
def detect_emotion():
    """
    情绪检测接口

    请求体:
    {
        "text": "待检测文本"
    }
    """
    request_id = str(uuid.uuid4())[:12]

    try:
        data = request.get_json()
        text = data.get("text", "").strip()

        if not text:
            return jsonify({
                "status": "error",
                "error": {"code": "VALIDATION_ERROR", "message": "文本不能为空"},
                "request_id": request_id
            }), 400

        from agent.modules.psychology.emotion import EmotionDetector
        detector = EmotionDetector()
        result = detector.detect(text)

        emotion_labels = {
            "happy": {"icon": "😊"},
            "sad": {"icon": "😢"},
            "anxious": {"icon": "😰"},
            "angry": {"icon": "😠"},
            "fearful": {"icon": "😨"},
            "neutral": {"icon": "😌"},
        }
        label = emotion_labels.get(result.emotion.value, {"icon": "😌"})

        return jsonify({
            "status": "success",
            "data": {
                "emotion": result.emotion.value,
                "intensity": result.intensity,
                "icon": label["icon"],
                "keywords": result.keywords,
                "suggestion": result.suggestion
            },
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            "request_id": request_id
        }), 500


@v5_bp.route("/crisis/check", methods=["POST"])
def check_crisis():
    """
    危机检测接口

    请求体:
    {
        "text": "待检测文本"
    }
    """
    request_id = str(uuid.uuid4())[:12]

    try:
        data = request.get_json()
        text = data.get("text", "").strip()

        if not text:
            return jsonify({
                "status": "error",
                "error": {"code": "VALIDATION_ERROR", "message": "文本不能为空"},
                "request_id": request_id
            }), 400

        from agent.modules.psychology.crisis import CrisisDetector
        detector = CrisisDetector()
        result = detector.check(text)

        requires_intervention = result.level.value in ("high", "critical")

        return jsonify({
            "status": "success",
            "data": {
                "level": result.level.value,
                "signals": result.signals,
                "message": result.message,
                "action": result.action,
                "hotlines": result.hotlines,
                "requires_intervention": requires_intervention
            },
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            "request_id": request_id
        }), 500


@v5_bp.route("/context/lifecycle/stats", methods=["GET"])
def context_stats():
    """上下文生命周期统计"""
    request_id = str(uuid.uuid4())[:12]

    try:
        from agent.context.context_lifecycle import ContextLifecycle
        lifecycle = ContextLifecycle()
        stats = lifecycle.get_stats()

        return jsonify({
            "status": "success",
            "data": stats,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            "request_id": request_id
        }), 500


@v5_bp.route("/status", methods=["GET"])
def v5_status():
    """v5 架构状态"""
    request_id = str(uuid.uuid4())[:12]

    try:
        orchestrator = get_orchestrator()

        return jsonify({
            "status": "success",
            "data": {
                "version": "v5.0",
                "orchestrator": "active",
                "memory_manager": "active" if _memory_manager else "inactive",
                "context_manager": "active" if _context_manager else "inactive",
                "tool_registry": f"{len(_tool_registry.get_all())} tools" if _tool_registry else "inactive",
            },
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            "request_id": request_id
        }), 500

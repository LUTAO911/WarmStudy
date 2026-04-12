"""
Agent API Routes - RESTful API路由定义
版本: 2.0
优化: 混合搜索API、流式响应、异步支持、缓存优化
"""
import time
from typing import Optional, Dict, Any
from flask import Blueprint, request, jsonify, Response
from datetime import datetime
import json
import asyncio
from functools import partial

from .auth import require_auth, get_auth_manager
from agent.core.agent import Agent, AgentConfig, AgentManager, AgentMode
from agent.memory import MemoryManager
from agent.tool_registry import ToolRegistry, setup_builtin_tools
from agent.context import ContextManager
from agent.skills import SkillRegistry, setup_builtin_skills
from agent.prompts import PromptManager
from agent.utils.logger import AgentLogger, RequestLogger
from agent.utils.monitor import PerformanceMonitor, HealthChecker


agent_bp = Blueprint("agent", __name__, url_prefix="/api/agent")

_logger = AgentLogger()
_request_logger = RequestLogger()
_monitor = PerformanceMonitor()
_monitor.start_monitoring()

_agent_manager = AgentManager()


def _get_or_create_agent(agent_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> Agent:
    if agent_id and agent_id in _agent_manager.list_agents():
        return _agent_manager.get_agent(agent_id)

    agent_config: Optional[AgentConfig] = None
    if config:
        agent_config = AgentConfig(**config)

    return _agent_manager.create_agent(agent_id=agent_id, config=agent_config)


@agent_bp.route("/status", methods=["GET"])
def get_status() -> Dict[str, Any]:
    health_checker = HealthChecker(_monitor)
    health = health_checker.check_health()
    stats = _monitor.get_stats_summary()

    try:
        from vectorstore import VectorStoreManager, get_index_info
        vs_stats = get_index_info()
    except Exception:
        vs_stats = {"error": "vectorstore unavailable"}

    return jsonify({
        "ok": True,
        "status": "running",
        "health": health,
        "stats": stats,
        "vectorstore": vs_stats,
        "timestamp": datetime.now().isoformat()
    })


@agent_bp.route("/health", methods=["GET"])
def health_check() -> tuple[Dict[str, Any], int]:
    health_checker = HealthChecker(_monitor)
    health = health_checker.check_health()

    status_code = 200 if health["status"] in ("healthy", "degraded") else 503

    return jsonify({
        "ok": True,
        **health
    }), status_code


@agent_bp.route("/chat", methods=["POST"])
@require_auth("chat")
def chat() -> tuple[Dict[str, Any], int]:
    start_time = time.time()

    try:
        data: Dict[str, Any] = request.get_json()

        message: str = data.get("message", "").strip()
        session_id: str = data.get("session_id", "default")
        agent_id: Optional[str] = data.get("agent_id")
        config: Optional[Dict[str, Any]] = data.get("config")

        use_rag: bool = data.get("use_rag", True)
        use_tools: bool = data.get("use_tools", True)
        use_skills: bool = data.get("use_skills", True)

        if not message:
            return jsonify({"ok": False, "error": "Message is required"}), 400

        agent = _get_or_create_agent(agent_id, config)

        response = agent.chat(
            message=message,
            session_id=session_id,
            use_rag=use_rag,
            use_tools=use_tools,
            use_skills=use_skills
        )

        execution_time = time.time() - start_time
        _monitor.record_request(
            session_id=session_id,
            response_time=execution_time,
            has_error=False,
            tools_used=len(response.tool_results),
            skills_used=len(response.skill_results)
        )

        _request_logger.log(
            session_id=session_id,
            user_message=message,
            assistant_response=response.answer,
            execution_time=execution_time,
            tools_used=[tr["tool_name"] for tr in response.tool_results],
            skills_used=[sr["skill_name"] for sr in response.skill_results],
            context_used=response.context_used
        )

        metadata_dict = {
            "session_id": session_id,
            "execution_time": round(execution_time, 3),
            "agent_id": agent_id
        }
        resp = jsonify({
            "ok": True,
            "answer": response.answer,
            "sources": list(response.sources),
            "tool_results": list(response.tool_results),
            "skill_results": list(response.skill_results),
            "context_used": response.context_used,
            "metadata": metadata_dict
        })
        if hasattr(response.metadata, '__iter__'):
            meta_dict = dict(response.metadata)
            if meta_dict.get("cached"):
                resp.headers["X-Cache"] = "HIT"
            else:
                resp.headers["X-Cache"] = "MISS"
        return resp

    except Exception as e:
        execution_time = time.time() - start_time
        _logger.log_error("ChatError", str(e), {"session_id": data.get("session_id", "default")})

        return jsonify({
            "ok": False,
            "error": str(e),
            "execution_time": round(execution_time, 3)
        }), 500


@agent_bp.route("/rag", methods=["POST"])
@require_auth("rag")
def rag_chat() -> tuple[Dict[str, Any], int]:
    start_time = time.time()

    try:
        data: Dict[str, Any] = request.get_json()

        message: str = data.get("message", "").strip()
        session_id: str = data.get("session_id", "default")
        n_results: int = data.get("n_results", 5)
        use_hybrid: bool = data.get("use_hybrid", True)
        use_rerank: bool = data.get("use_rerank", True)

        if not message:
            return jsonify({"ok": False, "error": "Message is required"}), 400

        agent = _get_or_create_agent()

        if use_hybrid:
            context_results = agent._retrieve_context_hybrid(message, n_results, use_rerank)
        else:
            context_results = agent._retrieve_context(message, n_results)

        prompt = agent.prompts.render(
            "rag_prompt",
            context="\n\n".join([f"[{i+1}] {r['content'][:300]}" for i, r in enumerate(context_results)]),
            question=message
        )

        answer = agent._generate_response(prompt)

        execution_time = time.time() - start_time
        _monitor.record_request(session_id, execution_time)

        return jsonify({
            "ok": True,
            "answer": answer,
            "sources": [
                {
                    "content": r["content"][:150] + "...",
                    "source": r["source"],
                    "page": r.get("page", ""),
                    "similarity": r.get("similarity", 0),
                    "combined_score": r.get("combined_score", r.get("similarity", 0))
                }
                for r in context_results[:3]
            ],
            "context_used": len(context_results) > 0,
            "search_mode": "hybrid" if use_hybrid else "vector",
            "execution_time": round(execution_time, 3)
        })

    except Exception as e:
        _logger.log_error("RAGError", str(e))
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/search", methods=["GET"])
@require_auth("chat")
def search_knowledge_base() -> tuple[Dict[str, Any], int]:
    try:
        query: str = request.args.get("q", "").strip()
        n_results: int = request.args.get("n", 5, type=int)
        use_hybrid: bool = request.args.get("hybrid", "true").lower() == "true"
        use_rerank: bool = request.args.get("rerank", "true").lower() == "true"

        if not query:
            return jsonify({"ok": False, "error": "Query is required"}), 400

        if use_hybrid:
            from vectorstore import query_with_hybrid_search
            results = query_with_hybrid_search(
                query_text=query,
                n_results=n_results,
                rerank=use_rerank
            )
        else:
            from vectorstore import query_chroma
            raw_results = query_chroma(
                query_text=query,
                n_results=n_results
            )
            results = [
                {
                    "content": doc,
                    "metadata": meta,
                    "similarity": round(1 - dist, 4)
                }
                for doc, meta, dist in raw_results
            ]

        return jsonify({
            "ok": True,
            "results": results,
            "query": query,
            "count": len(results),
            "search_mode": "hybrid" if use_hybrid else "vector"
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/hybrid-search", methods=["POST"])
@require_auth("rag")
def hybrid_search() -> tuple[Dict[str, Any], int]:
    try:
        data: Dict[str, Any] = request.get_json()

        query: str = data.get("query", "").strip()
        n_results: int = data.get("n_results", 10)
        vector_weight: float = data.get("vector_weight", 0.7)
        bm25_weight: float = data.get("bm25_weight", 0.3)
        rerank: bool = data.get("rerank", True)

        if not query:
            return jsonify({"ok": False, "error": "Query is required"}), 400

        from vectorstore import query_with_hybrid_search
        results = query_with_hybrid_search(
            query_text=query,
            n_results=n_results,
            vector_weight=vector_weight,
            bm25_weight=bm25_weight,
            rerank=rerank
        )

        return jsonify({
            "ok": True,
            "results": results,
            "query": query,
            "count": len(results),
            "weights": {"vector": vector_weight, "bm25": bm25_weight}
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/session/<session_id>/info", methods=["GET"])
@require_auth("chat")
def get_session_info(session_id: str) -> tuple[Dict[str, Any], int]:
    try:
        agent = _get_or_create_agent()
        info = agent.get_session_info(session_id)

        return jsonify({
            "ok": True,
            "session_info": info
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/session/<session_id>/reset", methods=["POST"])
@require_auth("chat")
def reset_session(session_id: str) -> tuple[Dict[str, Any], int]:
    try:
        agent = _get_or_create_agent()
        agent.reset_session(session_id)

        return jsonify({
            "ok": True,
            "message": f"Session {session_id} reset successfully"
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/tools", methods=["GET"])
@require_auth("tools")
def list_tools() -> tuple[Dict[str, Any], int]:
    try:
        registry = ToolRegistry()
        if len(registry.get_all()) == 0:
            setup_builtin_tools()

        tools = registry.get_schemas()

        return jsonify({
            "ok": True,
            "tools": tools,
            "count": len(tools)
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/tools/execute", methods=["POST"])
@require_auth("tools")
def execute_tool() -> tuple[Dict[str, Any], int]:
    try:
        data: Dict[str, Any] = request.get_json()

        tool_name: str = data.get("tool_name", "").strip()
        params: Dict[str, Any] = data.get("parameters", {})

        if not tool_name:
            return jsonify({"ok": False, "error": "Tool name is required"}), 400

        registry = ToolRegistry()
        result = registry.execute(tool_name, **params)

        return jsonify({
            "ok": result.is_success,
            **result.to_dict()
        }), 200 if result.is_success else 400

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/skills", methods=["GET"])
@require_auth("skills")
def list_skills() -> tuple[Dict[str, Any], int]:
    try:
        registry = SkillRegistry()
        if len(registry.get_all()) == 0:
            setup_builtin_skills()

        skills_info = registry.get_all_schemas()

        return jsonify({
            "ok": True,
            **skills_info
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/skills/execute", methods=["POST"])
@require_auth("skills")
def execute_skill() -> tuple[Dict[str, Any], int]:
    try:
        data: Dict[str, Any] = request.get_json()

        skill_name: str = data.get("skill_name", "").strip()
        params: Dict[str, Any] = data.get("parameters", {})

        if not skill_name:
            return jsonify({"ok": False, "error": "Skill name is required"}), 400

        registry = SkillRegistry()
        result = registry.execute(skill_name, params)

        return jsonify({
            "ok": result.is_success,
            **result.to_dict()
        }), 200 if result.is_success else 400

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/prompts", methods=["GET"])
@require_auth("chat")
def list_prompts() -> tuple[Dict[str, Any], int]:
    try:
        prompt_manager = PromptManager()

        return jsonify({
            "ok": True,
            "templates": prompt_manager.get_all_schemas(),
            "count": len(prompt_manager.list_templates())
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/prompts/render", methods=["POST"])
@require_auth("chat")
def render_prompt() -> tuple[Dict[str, Any], int]:
    try:
        data: Dict[str, Any] = request.get_json()

        template_name: str = data.get("template_name", "").strip()
        variables: Dict[str, Any] = data.get("variables", {})

        if not template_name:
            return jsonify({"ok": False, "error": "Template name is required"}), 400

        prompt_manager = PromptManager()
        rendered = prompt_manager.render(template_name, **variables)

        return jsonify({
            "ok": True,
            "rendered": rendered,
            "template_name": template_name
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/agents", methods=["GET"])
@require_auth("admin")
def list_agents() -> tuple[Dict[str, Any], int]:
    try:
        agent_ids = _agent_manager.list_agents()
        configs = _agent_manager.get_all_configs()

        return jsonify({
            "ok": True,
            "agents": agent_ids,
            "configs": configs,
            "count": len(agent_ids)
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/agents", methods=["POST"])
@require_auth("admin")
def create_agent() -> tuple[Dict[str, Any], int]:
    try:
        data: Dict[str, Any] = request.get_json()

        agent_id: Optional[str] = data.get("agent_id")
        config_data: Optional[Dict[str, Any]] = data.get("config")

        config: Optional[AgentConfig] = None
        if config_data:
            config = AgentConfig(**config_data)

        agent = _agent_manager.create_agent(agent_id=agent_id, config=config)

        return jsonify({
            "ok": True,
            "agent_id": agent.config.name if hasattr(agent.config, 'name') else "agent",
            "message": "Agent created successfully"
        }), 201

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/agents/<agent_id>", methods=["DELETE"])
@require_auth("admin")
def delete_agent(agent_id: str) -> tuple[Dict[str, Any], int]:
    try:
        success = _agent_manager.delete_agent(agent_id)

        if success:
            return jsonify({
                "ok": True,
                "message": f"Agent {agent_id} deleted successfully"
            }), 200
        else:
            return jsonify({
                "ok": False,
                "error": f"Agent {agent_id} not found"
            }), 404

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/cache/invalidate", methods=["POST"])
@require_auth("admin")
def invalidate_cache() -> tuple[Dict[str, Any], int]:
    try:
        from vectorstore import VectorStoreManager
        VectorStoreManager().invalidate_cache()

        return jsonify({
            "ok": True,
            "message": "Cache invalidated successfully"
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/metrics", methods=["GET"])
@require_auth("admin")
def get_metrics() -> tuple[Dict[str, Any], int]:
    try:
        current = _monitor.get_current_metrics()
        stats = _monitor.get_stats_summary()

        return jsonify({
            "ok": True,
            "current": current.to_dict(),
            "stats": stats
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/logs", methods=["GET"])
@require_auth("admin")
def get_logs() -> tuple[Dict[str, Any], int]:
    try:
        limit: int = request.args.get("limit", 100, type=int)
        logs = _logger.get_recent_logs(limit=limit)

        return jsonify({
            "ok": True,
            "logs": logs,
            "count": len(logs)
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/logs/errors", methods=["GET"])
@require_auth("admin")
def get_error_logs() -> tuple[Dict[str, Any], int]:
    try:
        limit: int = request.args.get("limit", 50, type=int)
        errors = _logger.get_error_logs(limit=limit)

        return jsonify({
            "ok": True,
            "errors": errors,
            "count": len(errors)
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/memory/search", methods=["GET"])
@require_auth("chat")
def search_memory() -> tuple[Dict[str, Any], int]:
    try:
        query: str = request.args.get("query", "").strip()
        limit: int = request.args.get("limit", 5, type=int)

        if not query:
            return jsonify({"ok": False, "error": "Query is required"}), 400

        agent = _get_or_create_agent()
        results = agent.memory.search_memories(query, limit)

        return jsonify({
            "ok": True,
            "results": [r.to_dict() for r in results],
            "count": len(results)
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/index/stats", methods=["GET"])
@require_auth("admin")
def get_index_stats() -> tuple[Dict[str, Any], int]:
    try:
        from vectorstore import get_index_info, VectorStoreManager
        stats = get_index_info()

        return jsonify({
            "ok": True,
            "stats": stats
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@agent_bp.route("/chat-stream", methods=["POST"])
@require_auth("chat")
def chat_stream():
    """
    流式聊天端点（Server-Sent Events）
    前端用 fetch + ReadableStream 接收，渐进式显示回答
    """
    from flask import Response as FlaskResponse
    import json

    data = request.get_json()
    message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")
    agent_id = data.get("agent_id")

    if not message:
        return jsonify({"ok": False, "error": "Message is required"}), 400

    agent = _get_or_create_agent(agent_id)

    def generate():
        try:
            # Step 0: 检查缓存
            if agent.config.enable_response_cache:
                cached = agent._response_cache.get(message, session_id)
                if cached:
                    yield "data: " + json.dumps({"type": "cached", "answer": cached}) + "\n\n"
                    yield "data: " + json.dumps({"type": "done", "cached": True}) + "\n\n"
                    return

            # Step 1: 判断是否需要 RAG/Tools（用 Qwen-Turbo）
            need_rag = False
            need_tools = False
            try:
                need_rag, need_tools = agent._llm_judge_needs(message, session_id)
            except Exception:
                pass

            # Step 2: 收集上下文
            context_results = []
            if need_rag:
                context_results = agent._retrieve_context(message, session_id, n_results=5)

            # Step 3: 构建 Prompt
            prompt = agent._build_prompt(
                message=message,
                session_id=session_id,
                context_results=context_results,
                tool_results=[],
                skill_results=[],
            )

            # Step 4: 生成回答（非流式，按批次 yield 模拟打字机）
            full_answer = agent._generate_response(prompt)

            # 模拟打字机效果：每25字吐一次，50ms间隔
            chars = list(full_answer)
            for i in range(0, len(chars), 25):
                chunk = "".join(chars[i:i+25])
                yield "data: " + json.dumps({"type": "token", "token": chunk}) + "\n\n"
                time.sleep(0.05)

            # 保存缓存
            if agent.config.enable_response_cache and full_answer and not full_answer.startswith("Error:"):
                agent._response_cache.set(message, session_id, full_answer)

            yield "data: " + json.dumps({"type": "done", "cached": False}) + "\n\n"

        except Exception as e:
            yield "data: " + json.dumps({"type": "error", "error": str(e)}) + "\n\n"

    return FlaskResponse(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )


@agent_bp.route("/cache/stats", methods=["GET"])
@require_auth("admin")
def cache_stats():
    """答案缓存统计"""
    try:
        agent = _get_or_create_agent()
        stats = agent._response_cache.get_stats()
        return jsonify({"ok": True, **stats}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/cache/clear", methods=["POST"])
@require_auth("admin")
def clear_cache():
    """清空答案缓存"""
    try:
        agent = _get_or_create_agent()
        agent._response_cache._cache.clear()
        return jsonify({"ok": True, "message": "Cache cleared"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ========== 心理支持 API ==========


@agent_bp.route("/psychology/emotion", methods=["POST"])
@require_auth("chat")
def detect_emotion() -> tuple[Dict[str, Any], int]:
    """
    情绪识别 API
    输入用户文本，返回情绪类型、强度、关键词和建议
    """
    try:
        data: Dict[str, Any] = request.get_json()
        text: str = data.get("text", "").strip()

        if not text:
            return jsonify({"ok": False, "error": "Text is required"}), 400

        from agent.tools.psychology import get_psychology_tools
        pt = get_psychology_tools()
        result = pt.detect_emotion(text)

        return jsonify({
            "ok": True,
            "emotion": result
        }), 200

    except Exception as e:
        _logger.log_error("EmotionDetectionError", str(e))
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/psychology/crisis", methods=["POST"])
@require_auth("chat")
def check_crisis() -> tuple[Dict[str, Any], int]:
    """
    危机检测 API
    检测自杀倾向、自伤等危机信号
    """
    try:
        data: Dict[str, Any] = request.get_json()
        text: str = data.get("text", "").strip()

        if not text:
            return jsonify({"ok": False, "error": "Text is required"}), 400

        from agent.tools.psychology import get_psychology_tools
        pt = get_psychology_tools()
        result = pt.check_crisis(text)

        return jsonify({
            "ok": True,
            "crisis": result
        }), 200

    except Exception as e:
        _logger.log_error("CrisisDetectionError", str(e))
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/psychology/knowledge", methods=["GET"])
@require_auth("chat")
def search_psychology_knowledge() -> tuple[Dict[str, Any], int]:
    """
    心理知识检索 API
    """
    try:
        query: str = request.args.get("q", "").strip()
        user_type: str = request.args.get("user_type", "student").strip()
        n_results: int = request.args.get("n", 5, type=int)

        if not query:
            return jsonify({"ok": False, "error": "Query is required"}), 400

        from agent.tools.psychology import get_psychology_tools
        pt = get_psychology_tools()
        result = pt.search_psychology_knowledge(
            query=query,
            user_type=user_type,
            n_results=n_results
        )

        return jsonify({
            "ok": True,
            **result
        }), 200

    except Exception as e:
        _logger.log_error("PsychologyKnowledgeError", str(e))
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/psychology/categories", methods=["GET"])
@require_auth("chat")
def get_psychology_categories() -> tuple[Dict[str, Any], int]:
    """
    获取心理知识分类 API
    """
    try:
        user_type: str = request.args.get("user_type", "student").strip()

        from agent.tools.psychology import get_psychology_tools
        pt = get_psychology_tools()
        categories = pt.get_all_categories(user_type=user_type)

        return jsonify({
            "ok": True,
            "categories": categories,
            "user_type": user_type
        }), 200

    except Exception as e:
        _logger.log_error("PsychologyCategoriesError", str(e))
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/psychology/knowledge/category", methods=["GET"])
@require_auth("chat")
def get_psychology_by_category() -> tuple[Dict[str, Any], int]:
    """
    按分类获取心理知识 API
    """
    try:
        category: str = request.args.get("category", "").strip()
        user_type: str = request.args.get("user_type", "student").strip()

        if not category:
            return jsonify({"ok": False, "error": "Category is required"}), 400

        from agent.tools.psychology import get_psychology_tools
        pt = get_psychology_tools()
        result = pt.get_knowledge_by_category(
            category=category,
            user_type=user_type
        )

        return jsonify({
            "ok": True,
            **result
        }), 200

    except Exception as e:
        _logger.log_error("PsychologyCategoryError", str(e))
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/psychology/support", methods=["POST"])
@require_auth("chat")
def psychological_support() -> tuple[Dict[str, Any], int]:
    """
    综合心理支持 API
    整合情绪识别 + 危机检测 + 知识检索 + 共情回复
    """
    try:
        data: Dict[str, Any] = request.get_json()
        user_input: str = data.get("user_input", "").strip()
        user_type: str = data.get("user_type", "student").strip()

        if not user_input:
            return jsonify({"ok": False, "error": "User input is required"}), 400

        from agent.tools.psychology import get_psychology_tools
        pt = get_psychology_tools()
        result = pt.psychological_support(
            user_input=user_input,
            user_type=user_type
        )

        return jsonify({
            "ok": True,
            **result
        }), 200

    except Exception as e:
        _logger.log_error("PsychologicalSupportError", str(e))
        return jsonify({"ok": False, "error": str(e)}), 500


@agent_bp.route("/psychology/chat", methods=["POST"])
@require_auth("chat")
def psychology_chat() -> tuple[Dict[str, Any], int]:
    """
    心理陪伴对话 API
    基于Agent的心理支持对话，优先使用心理工具
    """
    start_time = time.time()

    try:
        data: Dict[str, Any] = request.get_json()

        message: str = data.get("message", "").strip()
        session_id: str = data.get("session_id", "psychology_default")
        user_type: str = data.get("user_type", "student").strip()

        if not message:
            return jsonify({"ok": False, "error": "Message is required"}), 400

        # 使用心理支持工具
        from agent.tools.psychology import get_psychology_tools
        pt = get_psychology_tools()

        # 1. 危机检测（优先）
        crisis_result = pt.check_crisis(message)

        # 2. 情绪识别
        emotion_result = pt.detect_emotion(message)

        # 3. 根据危机等级处理
        crisis_level = crisis_result.get("level", "safe")
        if crisis_level in ("medium", "high", "critical"):
            # 危机情况，返回干预响应
            from agent.modules.psychology.crisis import CrisisResult, CrisisLevel
            crisis_obj = CrisisResult(
                level=CrisisLevel(crisis_level),
                signals=crisis_result.get("signals", []),
                message=crisis_result.get("message", ""),
                action=crisis_result.get("action", ""),
                hotlines=crisis_result.get("hotlines", [])
            )
            intervention = pt._crisis_detector.get_response(crisis_obj)
            execution_time = time.time() - start_time
            return jsonify({
                "ok": True,
                "type": "crisis_intervention",
                "crisis": crisis_result,
                "emotion": emotion_result,
                "response": intervention,
                "execution_time": round(execution_time, 3)
            }), 200

        # 4. 正常心理陪伴对话
        # 获取相关知识
        knowledge_result = pt.search_psychology_knowledge(
            query=message,
            user_type=user_type,
            n_results=3
        )

        # 生成共情回复
        empathic_response = pt.generate_empathic_response(
            user_input=message,
            emotion=emotion_result.get("emotion"),
            context={"knowledge": knowledge_result}
        )

        execution_time = time.time() - start_time

        return jsonify({
            "ok": True,
            "type": "normal_support",
            "emotion": emotion_result,
            "crisis": crisis_result,
            "knowledge": knowledge_result,
            "response": empathic_response,
            "execution_time": round(execution_time, 3)
        }), 200

    except Exception as e:
        execution_time = time.time() - start_time
        _logger.log_error("PsychologyChatError", str(e))
        return jsonify({
            "ok": False,
            "error": str(e),
            "execution_time": round(execution_time, 3)
        }), 500



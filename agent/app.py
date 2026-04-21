"""
RAG Knowledge Base Web Server + Agent Backend
Flask + LangChain + Agent Architecture
版本: 2.0
优化: 混合搜索支持、增量更新、异步处理
"""
import os
import uuid
import time
from pathlib import Path
from threading import Thread

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

import sys
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from loader import load_document, load_folder
from vectorstore import (
    ingest_to_chroma, query_chroma, query_with_hybrid_search,
    get_index_info, delete_by_source, reset_collection, update_document
)

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

app.config["UPLOAD_FOLDER"] = str(Path(__file__).parent / "uploads")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
Path(app.config["UPLOAD_FOLDER"]).mkdir(exist_ok=True)

try:
    from agent.api import agent_bp
    app.register_blueprint(agent_bp)
    AGENT_ENABLED = True
except Exception as e:
    print(f"[Agent] Failed to load agent module: {e}")
    AGENT_ENABLED = False
    agent_bp = None

# 注册 v5 API 蓝图（新架构）
try:
    from agent.api.routes_v5 import v5_bp
    app.register_blueprint(v5_bp)
    print("[Agent] v5 API blueprint registered")
except Exception as e:
    print(f"[Agent] Failed to load v5 routes: {e}")

# 注册错误处理器
try:
    from agent.api.errors import register_error_handlers
    register_error_handlers(app)
    print("[Agent] Error handlers registered")
except Exception as e:
    print(f"[Agent] Failed to register error handlers: {e}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/docs")
def api_docs():
    """OpenAPI 文档端点"""
    try:
        from agent.api.docs import get_openapi_spec
        return jsonify(get_openapi_spec())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/docs/ui")
def api_docs_ui():
    """Swagger UI 入口"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>暖学帮 API 文档</title>
        <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script>
            window.onload = function() {
                SwaggerUIBundle({{
                    url: "/api/docs",
                    dom_id: '#swagger-ui',
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.SwaggerUIStandalonePreset
                    ],
                    layout: "BaseLayout"
                }})
            }
        </script>
    </body>
    </html>
    '''


@app.route("/api/status")
def api_status():
    try:
        info = get_index_info(
            persist_dir="data/chroma",
            collection_name="knowledge_base",
        )
        return jsonify({
            "ok": True,
            "count": info.get("total_chunks", 0),
            "persist_dir": os.path.abspath("data/chroma"),
            "hybrid_search_enabled": info.get("hybrid_search_enabled", False),
            "cache_size": info.get("cache_size", 0),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    if "file" not in request.files and "folder" not in request.files:
        return jsonify({"ok": False, "error": "no file uploaded"}), 400

    files = request.files.getlist("file")
    folder_files = request.files.getlist("folder")
    all_files = files + [f for f in folder_files if f.filename.strip()]

    if not all_files:
        return jsonify({"ok": False, "error": "no file uploaded"}), 400

    saved_paths = []
    for f in all_files:
        if not f.filename:
            continue
        fname = f"{uuid.uuid4().hex[:8]}_{f.filename}"
        fpath = Path(app.config["UPLOAD_FOLDER"]) / fname
        f.save(fpath)
        saved_paths.append(str(fpath))

    def background_ingest(paths):
        for p in paths:
            docs = load_document(p)
            if docs:
                ingest_to_chroma(docs, persist_dir="data/chroma", collection_name="knowledge_base")

    Thread(target=background_ingest, args=(saved_paths,)).start()

    return jsonify({
        "ok": True,
        "message": f"Received {len(saved_paths)} files, indexing in background...",
        "files": [os.path.basename(p) for p in saved_paths],
    })


@app.route("/api/ingest/sync", methods=["POST"])
def api_ingest_sync():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "no file uploaded"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"ok": False, "error": "no file selected"}), 400

    fname = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    fpath = Path(app.config["UPLOAD_FOLDER"]) / fname
    file.save(fpath)

    try:
        docs = load_document(str(fpath))
        if not docs:
            return jsonify({"ok": False, "error": "failed to load document"}), 500

        result = ingest_to_chroma(
            docs,
            persist_dir="data/chroma",
            collection_name="knowledge_base"
        )

        return jsonify({
            "ok": True,
            "result": result,
            "file": file.filename
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/search", methods=["GET"])
def api_search():
    q = request.args.get("q", "").strip()
    n = int(request.args.get("n", 5))
    use_hybrid = request.args.get("hybrid", "true").lower() == "true"
    use_rerank = request.args.get("rerank", "true").lower() == "true"

    if not q:
        return jsonify({"ok": False, "error": "query is empty"}), 400

    if use_hybrid:
        results = query_with_hybrid_search(
            query_text=q,
            n_results=n,
            rerank=use_rerank
        )
        output = []
        for r in results:
            output.append({
                "content": r.get("content", ""),
                "source": r.get("metadata", {}).get("source", ""),
                "page": r.get("metadata", {}).get("page", ""),
                "type": r.get("metadata", {}).get("type", ""),
                "similarity": r.get("similarity", 0),
                "combined_score": r.get("combined_score", r.get("similarity", 0)),
            })
        results = output
    else:
        raw_results = query_chroma(
            query_text=q,
            n_results=n,
            persist_dir="data/chroma",
            collection_name="knowledge_base",
        )
        output = []
        for doc, meta, dist in raw_results:
            output.append({
                "content": doc,
                "source": meta.get("source", ""),
                "page": meta.get("page", ""),
                "type": meta.get("type", ""),
                "similarity": round(1 - dist, 4),
            })
        results = output

    return jsonify({
        "ok": True,
        "results": results,
        "query": q,
        "search_mode": "hybrid" if use_hybrid else "vector"
    })


@app.route("/api/hybrid-search", methods=["POST"])
def api_hybrid_search():
    body = request.get_json()
    q = body.get("query", "").strip()
    n = body.get("n_results", 10)
    vector_weight = body.get("vector_weight", 0.7)
    bm25_weight = body.get("bm25_weight", 0.3)
    rerank = body.get("rerank", True)

    if not q:
        return jsonify({"ok": False, "error": "query is empty"}), 400

    try:
        results = query_with_hybrid_search(
            query_text=q,
            n_results=n,
            vector_weight=vector_weight,
            bm25_weight=bm25_weight,
            rerank=rerank
        )

        return jsonify({
            "ok": True,
            "results": results,
            "query": q,
            "weights": {"vector": vector_weight, "bm25": bm25_weight}
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def api_chat():
    body = request.get_json()
    q = body.get("query", "").strip()
    n = int(body.get("n", 5))
    model = body.get("model", "qwen-max")
    use_hybrid = body.get("use_hybrid", True)
    use_rerank = body.get("use_rerank", True)

    if not q:
        return jsonify({"ok": False, "error": "query is empty"}), 400

    try:
        if use_hybrid:
            results = query_with_hybrid_search(
                query_text=q,
                n_results=n,
                rerank=use_rerank
            )
        else:
            raw_results = query_chroma(
                query_text=q,
                n_results=n,
                persist_dir="data/chroma",
                collection_name="knowledge_base",
            )
            results = [
                {"content": doc, "metadata": meta, "similarity": round(1 - dist, 4)}
                for doc, meta, dist in raw_results
            ]

        if results:
            context_parts = []
            for i, r in enumerate(results):
                content = r.get("content", "")[:400]
                score = r.get("combined_score", r.get("similarity", 0))
                context_parts.append(f"[{i+1}](Score: {score:.2f}) {content}")
            context_text = "\n\n".join(context_parts)
        else:
            context_text = ""

        if context_text:
            prompt = f"""You are a knowledge base assistant. Answer the user's question based on the provided context.
If the context does not contain relevant information, say so honestly - do not make things up.

---
{context_text}
---

Question: {q}

Answer based on the context above:"""
        else:
            prompt = q

        answer = generate_chat_response(prompt, model)

        sources = [
            {
                "content": r.get("content", "")[:150] + "...",
                "source": os.path.basename(r.get("metadata", {}).get("source", "")),
                "page": r.get("metadata", {}).get("page", ""),
                "similarity": r.get("similarity", 0),
                "combined_score": r.get("combined_score", r.get("similarity", 0)),
            }
            for r in results
        ]

        return jsonify({
            "ok": True,
            "answer": answer,
            "sources": sources,
            "has_context": bool(results),
            "search_mode": "hybrid" if use_hybrid else "vector"
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


def generate_chat_response(prompt: str, model: str = None) -> str:
    chat_model = os.getenv("CHAT_MODEL", "minimax")

    if chat_model == "minimax":
        return call_minimax_api(prompt)
    else:
        # DashScope/Qwen 默认使用 qwen-max
        qwen_model = os.getenv("DASHSCOPE_MODEL", "qwen-max")
        return call_dashscope_api(prompt, qwen_model)


def call_minimax_api(prompt: str) -> str:
    try:
        import requests
        api_key = os.getenv("MINIMAX_API_KEY", "")

        if not api_key:
            return "Error: MINIMAX_API_KEY not configured"

        url = "https://api.minimax.chat/v1/text/chatcompletion_pro"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "abab6.5s-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1500
        }

        resp = requests.post(url, headers=headers, json=data, timeout=30)

        if resp.status_code == 200:
            result = resp.json()
            return result.get("choices", [{}])[0].get("messages", [{}])[0].get("content", "No response")
        else:
            return f"Error: MiniMax API returned {resp.status_code}"

    except Exception as e:
        return f"Error calling MiniMax API: {str(e)}"


def call_dashscope_api(prompt: str, model: str) -> str:
    try:
        from dashscope import Generation
        import dashscope
        dashscope.api_key = os.getenv("DASHSCOPE_API_KEY", "")

        resp = Generation.call(
            model=model,
            prompt=prompt,
            temperature=0.3,
            top_p=0.8,
            max_tokens=1500,
            result_format="message",
        )

        if resp.status_code != 200:
            return f"Error: {resp.message}"

        return resp.output["choices"][0]["message"]["content"]

    except Exception as e:
        return f"Error calling DashScope API: {str(e)}"


@app.route("/api/update", methods=["POST"])
def api_update_document():
    body = request.get_json()
    source = body.get("source", "").strip()

    if not source:
        return jsonify({"ok": False, "error": "source is required"}), 400

    if "file" not in request.files:
        return jsonify({"ok": False, "error": "no file uploaded"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"ok": False, "error": "no file selected"}), 400

    fname = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    fpath = Path(app.config["UPLOAD_FOLDER"]) / fname
    file.save(fpath)

    try:
        docs = load_document(str(fpath))
        if not docs:
            return jsonify({"ok": False, "error": "failed to load document"}), 500

        result = update_document(
            source=source,
            docs=docs,
            persist_dir="data/chroma",
            collection_name="knowledge_base"
        )

        return jsonify({
            "ok": True,
            "result": result,
            "updated_source": source
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/delete", methods=["POST"])
def api_delete():
    body = request.get_json()
    source = body.get("source", "").strip()

    if not source:
        return jsonify({"ok": False, "error": "source is required"}), 400

    try:
        deleted_count = delete_by_source(
            source=source,
            persist_dir="data/chroma",
            collection_name="knowledge_base"
        )

        return jsonify({
            "ok": True,
            "deleted": deleted_count,
            "source": source
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def api_reset():
    try:
        success = reset_collection(
            persist_dir="data/chroma",
            collection_name="knowledge_base"
        )

        return jsonify({
            "ok": success,
            "message": "Collection reset successfully" if success else "Failed to reset"
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/index/info", methods=["GET"])
def api_index_info():
    try:
        info = get_index_info(
            persist_dir="data/chroma",
            collection_name="knowledge_base",
        )
        return jsonify({"ok": True, "info": info})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


@app.route("/psychology-test")
def psychology_test():
    """
    心理支持测试页面
    """
    return render_template("psychology_test.html")


# ===== 学生端心理陪伴 API =====


@app.route("/api/student/chat", methods=["POST"])
def api_student_chat():
    """
    学生端心理陪伴对话 - 接入Qwen LLM
    POST /api/student/chat
    """
    try:
        data = request.get_json()
        user_id = data.get("user_id", "")
        message = data.get("message", "").strip()

        if not message:
            return jsonify({"success": False, "error": "Message is required"}), 400

        # 1. 危机检测（规则，快速）
        from agent.tools.psychology import get_psychology_tools
        pt = get_psychology_tools()
        crisis_result = pt.check_crisis(message)
        crisis_level = crisis_result.get("level", "safe")

        # 2. 情绪识别
        emotion_result = pt.detect_emotion(message)
        emotion_label = emotion_result.get("emotion", "neutral")
        emotion_desc = emotion_result.get("description", "")

        # 3. 危机情况：返回干预响应（规则）
        if crisis_level in ("medium", "high", "critical"):
            from agent.modules.psychology.crisis import CrisisResult, CrisisLevel
            crisis_obj = CrisisResult(
                level=CrisisLevel(crisis_level),
                signals=crisis_result.get("signals", []),
                message=crisis_result.get("message", ""),
                action=crisis_result.get("action", ""),
                hotlines=crisis_result.get("hotlines", [])
            )
            intervention = pt._crisis_detector.get_response(crisis_obj)
            return jsonify({
                "success": True,
                "response": intervention,
                "ai_name": "暖暖",
                "emotion": emotion_label,
                "crisis_level": crisis_level,
                "type": "crisis_intervention"
            })

        # 4. 正常心理陪伴：用Qwen LLM生成共情回复
        knowledge_result = pt.search_psychology_knowledge(
            query=message,
            user_type="student",
            n_results=3
        )

        # 构建知识上下文
        knowledge_text = ""
        if knowledge_result and knowledge_result.get("results"):
            for r in knowledge_result["results"]:
                knowledge_text += f"- {r.get('content', '')}\n"

        # 构建LLM提示词
        if knowledge_text:
            llm_prompt = f"""你是一位温暖、专业的青少年心理陪伴助手"暖暖"。请根据以下信息，用温暖共情的语气回复学生。

学生的话：{message}

检测到的情绪：{emotion_label}（{emotion_desc}）

相关心理知识：
{knowledge_text}

请结合心理知识，用温暖、理解的语气回复（100-200字），体现共情和关心。如果适合，给出一些积极的建议。

回复："""
        else:
            llm_prompt = f"""你是一位温暖、专业的青少年心理陪伴助手"暖暖"。请用温暖共情的语气回复学生。

学生的话：{message}

检测到的情绪：{emotion_label}（{emotion_desc}）

请用温暖、理解的语气回复（100-200字），体现共情和关心。如果适合，给出一些积极的建议。

回复："""

        # 调用LLM生成回复（根据CHAT_MODEL自动选择minimax或qwen）
        llm_response = generate_chat_response(llm_prompt)

        return jsonify({
            "success": True,
            "response": llm_response,
            "ai_name": "暖暖",
            "emotion": emotion_label,
            "crisis_level": crisis_level,
            "type": "normal_support"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/student/checkin", methods=["POST"])
def api_student_checkin():
    """
    学生每日打卡
    POST /api/student/checkin
    """
    try:
        data = request.get_json()
        user_id = data.get("user_id", "")
        emotion = data.get("emotion")
        sleep = data.get("sleep")
        study = data.get("study")
        social = data.get("social")
        note = data.get("note", "")

        # 这里可以保存到数据库，现在先返回成功
        return jsonify({
            "success": True,
            "message": "打卡成功"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/student/psych/status/<user_id>", methods=["GET"])
def api_student_psych_status(user_id):
    """
    获取学生心理状态
    GET /api/student/psych/status/{user_id}
    """
    try:
        # 返回默认心理状态
        return jsonify({
            "success": True,
            "status": {
                "emotion": "neutral",
                "emotion_label": "平静",
                "emotion_icon": "😌",
                "weekly_trend": ["neutral", "happy", "neutral", "anxious", "neutral"],
                "risk_level": "low"
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ===== 家长端 API =====


@app.route("/api/parent/chat", methods=["POST"])
def api_parent_chat():
    """
    家长端家庭教育助手对话
    POST /api/parent/chat
    """
    try:
        data = request.get_json()
        user_id = data.get("user_id", "")
        message = data.get("message", "").strip()

        if not message:
            return jsonify({"success": False, "error": "Message is required"}), 400

        # 使用心理学工具处理（家长模式）
        from agent.tools.psychology import get_psychology_tools
        pt = get_psychology_tools()

        # 危机检测
        crisis_result = pt.check_crisis(message)
        crisis_level = crisis_result.get("level", "safe")

        # 情绪识别
        emotion_result = pt.detect_emotion(message)

        # 危机情况
        if crisis_level in ("medium", "high", "critical"):
            from agent.modules.psychology.crisis import CrisisResult, CrisisLevel
            crisis_obj = CrisisResult(
                level=CrisisLevel(crisis_level),
                signals=crisis_result.get("signals", []),
                message=crisis_result.get("message", ""),
                action=crisis_result.get("action", ""),
                hotlines=crisis_result.get("hotlines", [])
            )
            intervention = pt._crisis_detector.get_response(crisis_obj)
            return jsonify({
                "success": True,
                "response": intervention,
                "ai_name": "暖暖",
                "type": "crisis_intervention"
            })

        # 正常对话 - 检索家长相关心理知识
        knowledge_result = pt.search_psychology_knowledge(
            query=message,
            user_type="parent",
            n_results=3
        )

        empathic_response = pt.generate_empathic_response(
            user_input=message,
            emotion=emotion_result.get("emotion"),
            context={"knowledge": knowledge_result}
        )

        return jsonify({
            "success": True,
            "response": empathic_response,
            "ai_name": "暖暖",
            "type": "normal_support"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/parent/child/<child_id>/status", methods=["GET"])
def api_parent_child_status(child_id):
    """
    获取孩子综合状态
    GET /api/parent/child/{child_id}/status
    """
    try:
        return jsonify({
            "success": True,
            "status": {
                "emotion": "neutral",
                "emotion_label": "平静",
                "emotion_icon": "😌",
                "weekly_checkin_count": 5,
                "last_checkin": "2026-04-11",
                "risk_level": "low",
                "trend": "stable"
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/parent/child/<child_id>/checkins", methods=["GET"])
def api_parent_child_checkins(child_id):
    """
    获取孩子打卡记录
    GET /api/parent/child/{child_id}/checkins?days=7
    """
    try:
        days = request.args.get("days", 7, type=int)
        # 返回模拟数据
        return jsonify({
            "success": True,
            "checkins": []
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/parent/alerts", methods=["GET"])
def api_parent_alerts():
    """
    获取预警列表
    GET /api/parent/alerts?parent_id=xxx&limit=20&offset=0
    """
    try:
        return jsonify({
            "success": True,
            "alerts": [],
            "unread_count": 0
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/parent/child/<child_id>/psych/latest", methods=["GET"])
def api_parent_child_psych_latest(child_id):
    """
    获取孩子最新心理状态
    GET /api/parent/child/{child_id}/psych/latest
    """
    try:
        return jsonify({
            "success": True,
            "latest": {
                "emotion": "neutral",
                "emotion_label": "平静",
                "date": "2026-04-11",
                "risk_level": "low"
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    os.chdir(Path(__file__).parent)

    # 启动 API Gateway（端口 8000）
    def run_gateway():
        from api_gateway import app as gateway_app
        print("\n[API Gateway] 暖学帮小程序后端 starting...")
        print(f"   http://localhost:8000")
        print(f"   RAG Agent URL: http://localhost:5177")
        print()
        gateway_app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)

    gateway_thread = Thread(target=run_gateway, daemon=True)
    gateway_thread.start()

    # 启动 RAG 服务（端口 5177）
    print("\n[RAG] Knowledge base web server starting...")
    print(f"   http://localhost:5177")
    print(f"   Agent Backend: {'Enabled' if AGENT_ENABLED else 'Disabled'}")
    print(f"   API Base: http://localhost:5177/api/agent")
    print(f"   Hybrid Search: Enabled")
    print(f"\n[暖学帮] 双服务启动完成！")
    print(f"   RAG Web界面:  http://localhost:5177")
    print(f"   API Gateway:   http://localhost:8000")
    print()
    app.run(host="0.0.0.0", port=5177, debug=False, use_reloader=False)

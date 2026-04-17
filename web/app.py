"""
WarmStudy (暖学帮) Web 前端
Python / Flask — 对应小程序前端的浏览器端实现
"""
import os
import uuid
from functools import wraps

import requests
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, flash,
)
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)
app.secret_key = os.getenv("WEB_SECRET_KEY", "warmstudy-web-secret-2024")

# 后端 Agent API 地址（可通过环境变量配置）
AGENT_API_URL = os.getenv("AGENT_API_URL", "http://localhost:5001")


# ─────────────────────────────────────────
# 认证辅助
# ─────────────────────────────────────────

def login_required(role=None):
    """检查登录状态的装饰器，可选校验角色"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "user" not in session:
                return redirect(url_for("login"))
            if role and session["user"].get("role") != role:
                flash("权限不足，请以正确身份登录", "error")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


# ─────────────────────────────────────────
# 公共路由
# ─────────────────────────────────────────

@app.route("/")
def index():
    if "user" in session:
        role = session["user"].get("role")
        return redirect(url_for("student_chat") if role == "student" else url_for("parent_dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role", "student")
        name = request.form.get("name", "").strip() or ("同学" if role == "student" else "家长")
        phone = request.form.get("phone", "").strip()

        session["user"] = {
            "id": str(uuid.uuid4())[:8],
            "role": role,
            "name": name,
            "phone": phone,
            "session_id": str(uuid.uuid4()),
        }

        if role == "student":
            return redirect(url_for("student_chat"))
        return redirect(url_for("parent_dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ─────────────────────────────────────────
# 学生端路由
# ─────────────────────────────────────────

@app.route("/student")
@login_required(role="student")
def student_index():
    return redirect(url_for("student_chat"))


@app.route("/student/chat")
@login_required(role="student")
def student_chat():
    user = session["user"]
    return render_template("student/chat.html", user=user)


@app.route("/student/assessment")
@login_required(role="student")
def student_assessment():
    user = session["user"]
    return render_template("student/assessment.html", user=user)


@app.route("/student/library")
@login_required(role="student")
def student_library():
    user = session["user"]
    return render_template("student/library.html", user=user)


# ─────────────────────────────────────────
# 家长端路由
# ─────────────────────────────────────────

@app.route("/parent")
@login_required(role="parent")
def parent_dashboard():
    user = session["user"]
    return render_template("parent/index.html", user=user)


@app.route("/parent/chat")
@login_required(role="parent")
def parent_chat():
    user = session["user"]
    return render_template("parent/chat.html", user=user)


# ─────────────────────────────────────────
# API 代理（转发到 Agent 后端）
# ─────────────────────────────────────────

def _proxy_post(path: str, payload: dict):
    """向 Agent 后端发 POST 请求并返回 JSON。"""
    try:
        resp = requests.post(
            f"{AGENT_API_URL}{path}",
            json=payload,
            timeout=30,
        )
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({
            "status": "error",
            "error": {"code": "BACKEND_UNAVAILABLE", "message": "后端服务暂时不可用，请稍后重试"}
        }), 503
    except Exception:
        app.logger.exception("Proxy error for path: %s", path)
        return jsonify({
            "status": "error",
            "error": {"code": "PROXY_ERROR", "message": "请求处理失败，请稍后重试"}
        }), 500


@app.route("/api/chat", methods=["POST"])
@login_required()
def api_chat():
    """代理对话请求到 Agent v5 后端。"""
    user = session["user"]
    body = request.get_json(force=True) or {}
    body.setdefault("session_id", user.get("session_id", "web-default"))
    body.setdefault("user_type", user.get("role", "student"))
    return _proxy_post("/api/v5/chat", body)


@app.route("/api/search", methods=["GET"])
@login_required()
def api_search():
    """代理知识库搜索请求。"""
    q = request.args.get("q", "").strip()
    n = request.args.get("n", 8)
    if not q:
        return jsonify({"ok": False, "error": "查询内容不能为空"}), 400
    try:
        resp = requests.get(
            f"{AGENT_API_URL}/api/search",
            params={"q": q, "n": n, "hybrid": "true"},
            timeout=30,
        )
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"ok": False, "error": "后端服务暂时不可用"}), 503
    except Exception:
        app.logger.exception("Search proxy error for query: %s", q)
        return jsonify({"ok": False, "error": "搜索请求失败，请稍后重试"}), 500


@app.route("/api/status")
def api_status():
    """检查后端状态。"""
    try:
        resp = requests.get(f"{AGENT_API_URL}/api/status", timeout=5)
        return jsonify(resp.json()), resp.status_code
    except Exception:
        return jsonify({"ok": False, "error": "后端不可达"}), 503


# ─────────────────────────────────────────
# 错误页面
# ─────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="页面不存在"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500, message="服务器内部错误"), 500


if __name__ == "__main__":
    port = int(os.getenv("WEB_PORT", 5002))
    debug = os.getenv("WEB_DEBUG", "true").lower() == "true"
    print(f"🌸 WarmStudy Web 前端启动于 http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)

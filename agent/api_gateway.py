"""
暖学帮 API 网关服务
端口: 8000
职责: 统一API入口，路由到各微服务
"""
import os
import time
import json
import random
import requests
from pathlib import Path
from flask import Flask, request, jsonify, render_template, Response
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__, template_folder="templates", static_folder="static")

RAG_AGENT_URL = os.getenv("RAG_AGENT_URL", "http://localhost:5177")

mock_database = {
    "students": {},
    "parents": {},
    "checkins": {},
    "psych_tests": {},
    "psych_status": {}
}

def generate_code():
    return str(random.randint(100000, 999999))

def get_current_user():
    return request.headers.get("X-User-ID", "student_001")

def format_response(data):
    return {"success": True, **data}

def format_error(message, code=400):
    return jsonify({"success": False, "error": message}), code


def _rag_url(path: str) -> str:
    return f"{RAG_AGENT_URL.rstrip('/')}{path}"


def _proxy_to_rag(
    path: str,
    method: str = "GET",
    *,
    timeout: int = 60,
    pass_query: bool = True,
):
    url = _rag_url(path)
    params = request.args.to_dict(flat=True) if pass_query else None
    headers = {"X-Forwarded-By": "warmstudy-api-gateway"}

    try:
        if request.files:
            files = []
            for key in request.files:
                for storage in request.files.getlist(key):
                    files.append(
                        (
                            key,
                            (
                                storage.filename,
                                storage.stream.read(),
                                storage.mimetype or "application/octet-stream",
                            ),
                        )
                    )
            data = request.form.to_dict(flat=True)
            resp = requests.request(
                method=method,
                url=url,
                params=params,
                data=data,
                files=files,
                headers=headers,
                timeout=timeout,
            )
        else:
            json_body = request.get_json(silent=True)
            if json_body is not None and method in {"POST", "PUT", "PATCH", "DELETE"}:
                resp = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_body,
                    headers=headers,
                    timeout=timeout,
                )
            else:
                resp = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    data=request.get_data() if method in {"POST", "PUT", "PATCH"} else None,
                    headers=headers,
                    timeout=timeout,
                )
    except requests.RequestException as exc:
        return jsonify({
            "success": False,
            "error": f"RAG service request failed: {exc}",
            "rag_agent_url": RAG_AGENT_URL,
        }), 502

    content_type = resp.headers.get("Content-Type", "application/json")
    excluded_headers = {"content-encoding", "content-length", "transfer-encoding", "connection"}
    proxy_headers = [
        (name, value) for name, value in resp.headers.items() if name.lower() not in excluded_headers
    ]
    return Response(resp.content, resp.status_code, proxy_headers, content_type=content_type)


def _safe_json_from_rag(path: str, method: str = "GET", **kwargs):
    try:
        resp = requests.request(method=method, url=_rag_url(path), timeout=15, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

@app.route("/api/auth/send-code", methods=["POST"])
def send_code():
    data = request.get_json()
    phone = data.get("phone")
    if not phone:
        return format_error("手机号不能为空")

    code = generate_code()
    print(f"[验证码] {phone}: {code}")

    return jsonify({"success": True, "message": "验证码已发送", "code": code})

@app.route("/api/auth/login/phone", methods=["POST"])
def login_by_phone():
    data = request.get_json()
    phone = data.get("phone")
    code = data.get("code")
    role = data.get("role", "student")

    if not phone or not code:
        return format_error("手机号和验证码必填")

    user_id = f"{role}_{phone[-4:]}"
    name = f"用户{phone[-4:]}"

    mock_database["students"][user_id] = {
        "user_id": user_id,
        "name": name,
        "phone": phone,
        "role": role
    }

    return jsonify({
        "success": True,
        "data": {
            "user_id": user_id,
            "name": name,
            "phone": phone,
            "role": role,
            "token": f"token_{user_id}_{int(time.time())}"
        }
    })

@app.route("/api/student/chat", methods=["POST"])
def student_chat():
    """
    学生心理陪伴对话 - 代理到5177 RAG服务（接入Qwen模型）
    """
    data = request.get_json()
    user_id = data.get("user_id", get_current_user())
    message = data.get("message", "")

    if not message:
        return format_error("消息内容不能为空")

    try:
        import requests
        resp = requests.post(
            f"{RAG_AGENT_URL}/api/student/chat",
            json={"user_id": user_id, "message": message},
            timeout=30
        )
        if resp.status_code == 200:
            result = resp.json()
            return jsonify({
                "success": True,
                "response": result.get("response", result.get("answer", "")),
                "ai_name": "暖暖",
                "emotion": result.get("emotion", "neutral"),
                "crisis_level": result.get("crisis_level", "safe"),
                "type": result.get("type", "normal_support")
            })
    except Exception as e:
        print(f"[学生聊天] 调用RAG服务失败: {e}")

    return jsonify({
        "success": True,
        "response": "抱歉，服务暂时不可用，请稍后再试。",
        "ai_name": "暖暖",
        "type": "fallback"
    })

@app.route("/api/student/checkin", methods=["POST"])
def student_checkin():
    data = request.get_json()
    user_id = data.get("user_id", get_current_user())

    checkin_data = {
        "user_id": user_id,
        "emotion": data.get("emotion", 3),
        "sleep": data.get("sleep", 7),
        "study": data.get("study", 6),
        "social": data.get("social", 5),
        "note": data.get("note", ""),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if user_id not in mock_database["checkins"]:
        mock_database["checkins"][user_id] = []

    mock_database["checkins"][user_id].append(checkin_data)

    return jsonify({
        "success": True,
        "message": "打卡成功",
        "data": checkin_data
    })

@app.route("/api/student/checkin/<user_id>", methods=["GET"])
def get_checkin_history(user_id, days=7):
    days = int(request.args.get("days", 7))

    checkins = mock_database["checkins"].get(user_id, [])
    cutoff = datetime.now() - timedelta(days=days)
    recent = [
        c for c in checkins
        if datetime.strptime(c["date"], "%Y-%m-%d %H:%M:%S") > cutoff
    ]

    return jsonify({
        "success": True,
        "data": recent,
        "count": len(recent)
    })

@app.route("/api/student/psych/test", methods=["POST"])
def submit_psych_test():
    data = request.get_json()
    user_id = data.get("user_id", get_current_user())
    answers = data.get("answers", [])
    test_type = data.get("test_type", "weekly")

    score = sum(answers) if answers else 0
    max_score = len(answers) * 5 if answers else 25

    normalized = (score / max_score * 100) if max_score > 0 else 50

    if normalized >= 80:
        level = "excellent"
        level_label = "优秀"
    elif normalized >= 60:
        level = "good"
        level_label = "良好"
    elif normalized >= 40:
        level = "fair"
        level_label = "一般"
    else:
        level = "concerning"
        level_label = "需关注"

    test_result = {
        "user_id": user_id,
        "test_type": test_type,
        "score": score,
        "max_score": max_score,
        "normalized": round(normalized, 1),
        "level": level,
        "level_label": level_label,
        "summary": f"本次测评得分{normalized:.0f}分，处于{level_label}水平。",
        "advice": "继续保持良好的生活习惯，多与家人朋友交流。",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "answers": answers
    }

    mock_database["psych_tests"][user_id] = test_result
    mock_database["psych_status"][user_id] = {
        "level": level,
        "normalized": normalized,
        "last_test": datetime.now().strftime("%Y-%m-%d")
    }

    return jsonify({
        "success": True,
        "message": "测评提交成功",
        "data": test_result
    })

@app.route("/api/student/psych/status/<user_id>", methods=["GET"])
def get_psych_status(user_id):
    status = mock_database["psych_status"].get(user_id)

    if not status:
        return jsonify({
            "success": True,
            "data": {
                "user_id": user_id,
                "level": "unknown",
                "normalized": 0,
                "last_test": None,
                "message": "暂无测评记录"
            }
        })

    return jsonify({
        "success": True,
        "data": {
            "user_id": user_id,
            **status
        }
    })

@app.route("/api/parent/chat", methods=["POST"])
def parent_chat():
    """
    家长对话 - 代理到5177 RAG服务（接入Qwen模型）
    """
    data = request.get_json()
    user_id = data.get("user_id", get_current_user())
    message = data.get("message", "")

    if not message:
        return format_error("消息内容不能为空")

    try:
        import requests
        resp = requests.post(
            f"{RAG_AGENT_URL}/api/parent/chat",
            json={"user_id": user_id, "message": message},
            timeout=30
        )
        if resp.status_code == 200:
            result = resp.json()
            return jsonify({
                "success": True,
                "response": result.get("response", result.get("answer", "")),
                "ai_name": "暖暖",
                "type": result.get("type", "normal_support")
            })
    except Exception as e:
        print(f"[家长聊天] 调用RAG服务失败: {e}")

    return jsonify({
        "success": True,
        "response": "抱歉，服务暂时不可用，请稍后再试。",
        "ai_name": "暖暖",
        "type": "fallback"
    })

@app.route("/api/parent/child/<child_id>/status", methods=["GET"])
def get_child_status(child_id):
    checkins = mock_database["checkins"].get(child_id, [])
    recent = checkins[-7:] if len(checkins) > 7 else checkins

    avg_emotion = sum(c.get("emotion", 3) for c in recent) / max(len(recent), 1)
    avg_sleep = sum(c.get("sleep", 7) for c in recent) / max(len(recent), 1)
    avg_study = sum(c.get("study", 6) for c in recent) / max(len(recent), 1)

    return jsonify({
        "success": True,
        "data": {
            "child_id": child_id,
            "avg_emotion": round(avg_emotion, 1),
            "avg_sleep": round(avg_sleep, 1),
            "avg_study": round(avg_study, 1),
            "checkin_count": len(checkins),
            "last_checkin": checkins[-1]["date"] if checkins else None
        }
    })

@app.route("/api/parent/child/<child_id>/checkins", methods=["GET"])
def get_child_checkins(child_id):
    days = int(request.args.get("days", 7))
    checkins = mock_database["checkins"].get(child_id, [])

    cutoff = datetime.now() - timedelta(days=days)
    recent = [
        c for c in checkins
        if datetime.strptime(c["date"], "%Y-%m-%d %H:%M:%S") > cutoff
    ]

    return jsonify({
        "success": True,
        "data": recent,
        "count": len(recent)
    })

@app.route("/api/parent/child/<child_id>/ai_advice", methods=["GET"])
def get_daily_advice(child_id):
    advices = [
        {"advice": "今天天气不错，建议带孩子户外活动一下。", "focus": "运动"},
        {"advice": "注意观察孩子的情绪变化，及时沟通。", "focus": "情绪"},
        {"advice": "保持规律的作息对孩子的身心发展很重要。", "focus": "作息"},
        {"advice": "学习之余，也要注意孩子的休息和放松。", "focus": "休息"},
        {"advice": "多给孩子一些正面的鼓励和支持。", "focus": "鼓励"}
    ]

    return jsonify({
        "success": True,
        **random.choice(advices)
    })

@app.route("/api/parent/child/grade", methods=["POST"])
def submit_grade():
    data = request.get_json()
    return jsonify({
        "success": True,
        "message": "成绩录入成功"
    })

@app.route("/api/parent/login", methods=["POST"])
def parent_login():
    data = request.get_json()
    phone = data.get("phone")

    if not phone:
        return format_error("手机号不能为空")

    parent_id = f"parent_{phone[-4:]}"
    return jsonify({
        "success": True,
        "account": {
            "id": int(phone[-4:]),
            "phone": phone,
            "name": f"家长{phone[-4:]}",
            "qr_token": f"qr_{parent_id}"
        },
        "bound_children": ["student_001"]
    })

@app.route("/api/parent/children/profiles", methods=["POST"])
def get_children_profiles():
    data = request.get_json()
    child_ids = data.get("child_ids", "").split(",")

    profiles = [
        {"user_id": cid.strip(), "name": f"学生{cid.strip()[-3:]}", "grade": "初一"}
        for cid in child_ids if cid.strip()
    ]

    return jsonify({
        "success": True,
        "profiles": profiles
    })

@app.route("/api/parent/alerts", methods=["GET"])
def get_parent_alerts():
    parent_id = request.args.get("parent_id", "parent_001")

    alerts = [
        {
            "id": 1,
            "child_id": "student_001",
            "child_name": "小明",
            "alert_type": "emotion_drop",
            "title": "情绪波动提醒",
            "content": "孩子最近情绪波动较大，建议关注。",
            "is_read": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    ]

    return jsonify({
        "success": True,
        "alerts": alerts,
        "unread_count": 1
    })

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "success": True,
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "warmstudy-api-gateway",
        "version": "1.0.0"
    })


@app.route("/api/gateway/status", methods=["GET"])
def gateway_status():
    rag_health = _safe_json_from_rag("/api/health")
    rag_status = _safe_json_from_rag("/api/status")
    rag_index = _safe_json_from_rag("/api/index/info")
    return jsonify({
        "success": True,
        "gateway": {
            "status": "healthy",
            "service": "warmstudy-api-gateway",
            "port": 8000,
            "timestamp": datetime.now().isoformat(),
        },
        "rag": {
            "base_url": RAG_AGENT_URL,
            "health": rag_health,
            "status": rag_status,
            "index": rag_index,
        },
        "links": {
            "console": "/",
            "playground": "/psychology-test",
            "rag_status_proxy": "/api/gateway/rag/status",
            "rag_docs_proxy": "/api/gateway/rag/docs",
        }
    })


@app.route("/api/gateway/rag/status", methods=["GET"])
def proxy_rag_status():
    return _proxy_to_rag("/api/status")


@app.route("/api/gateway/rag/health", methods=["GET"])
def proxy_rag_health():
    return _proxy_to_rag("/api/health")


@app.route("/api/gateway/rag/index/info", methods=["GET"])
def proxy_rag_index_info():
    return _proxy_to_rag("/api/index/info")


@app.route("/api/gateway/rag/docs", methods=["GET"])
def proxy_rag_docs():
    return _proxy_to_rag("/api/docs")


@app.route("/api/gateway/rag/search", methods=["GET"])
def proxy_rag_search():
    return _proxy_to_rag("/api/search")


@app.route("/api/gateway/rag/hybrid-search", methods=["POST"])
def proxy_rag_hybrid_search():
    return _proxy_to_rag("/api/hybrid-search", method="POST", pass_query=False)


@app.route("/api/gateway/rag/chat", methods=["POST"])
def proxy_rag_chat():
    return _proxy_to_rag("/api/chat", method="POST", pass_query=False)


@app.route("/api/gateway/rag/ingest/sync", methods=["POST"])
def proxy_rag_ingest_sync():
    return _proxy_to_rag("/api/ingest/sync", method="POST", pass_query=False)


@app.route("/api/gateway/rag/reset", methods=["POST"])
def proxy_rag_reset():
    return _proxy_to_rag("/api/reset", method="POST", pass_query=False)


@app.route("/api/gateway/rag/delete", methods=["POST"])
def proxy_rag_delete():
    return _proxy_to_rag("/api/delete", method="POST", pass_query=False)


@app.route("/api/gateway/rag/update", methods=["POST"])
def proxy_rag_update():
    return _proxy_to_rag("/api/update", method="POST", pass_query=False)

@app.route("/", methods=["GET"])
def index():
    """
    暖学帮 - 青少年心理陪伴 AI 对话界面
    接入 Qwen/Tongyi 大模型
    """
    return render_template("gateway_dashboard.html", rag_agent_url=RAG_AGENT_URL)


@app.route("/psychology-test", methods=["GET"])
def psychology_test():
    return render_template("psychology_test.html")


if __name__ == "__main__":
    print("\n" + "="*50)
    print("暖学帮 API 网关服务")
    print(f"RAG Agent URL: {RAG_AGENT_URL}")
    print("端口: 8000")
    print("="*50 + "\n")

    app.run(host="0.0.0.0", port=8000, debug=False)

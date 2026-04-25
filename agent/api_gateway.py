"""
WarmStudy API gateway.

Responsibilities:
- provide a stable single entrypoint for the miniapp
- proxy selected RAG/Agent endpoints from the 5177 service
- expose lightweight mock/demo persistence for parent/student flows
"""

from __future__ import annotations

import json
import os
import random
import time
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests
from flask import Flask, Response, g, jsonify, render_template, request
from flask_cors import CORS

from agent.strategy_engine import (
    build_parent_strategy,
    build_student_strategy,
    infer_school_stage,
    normalize_student_profile,
)

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-User-ID",
        "X-Request-ID",
        "X-API-Key",
    ],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)

DEFAULT_DEV_AGENT_KEY = "agent_dev_key_12345"
ENV_FILE = Path(__file__).parent / ".env"
CONFIG_FILE = Path(__file__).parent / "config" / "gateway.json"


DEFAULT_GATEWAY_CONFIG: dict[str, Any] = {
    "server": {
        "host": "0.0.0.0",
        "port": 8000,
    },
    "rag_service": {
        "base_url": os.getenv("RAG_AGENT_URL", "http://localhost:5177"),
        "timeout": 60,
        "health_timeout": 15,
        "retry": 2,
    },
    "routes": {
        "aliases": [
            {"path": "/api/chat", "target": "/api/gateway/rag/chat", "methods": ["POST"], "description": "Legacy RAG chat alias"},
            {"path": "/api/agent/chat", "target": "/api/gateway/rag/chat", "methods": ["POST"], "description": "Agent chat alias"},
            {"path": "/api/student/chat", "target": "/api/student/chat", "methods": ["POST"], "description": "Student companion chat"},
            {"path": "/api/parent/chat", "target": "/api/parent/chat", "methods": ["POST"], "description": "Parent support chat"},
        ]
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_gateway_config() -> dict[str, Any]:
    config = deepcopy(DEFAULT_GATEWAY_CONFIG)
    if CONFIG_FILE.exists():
        try:
            file_config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            config = _deep_merge(config, file_config)
        except Exception:
            pass
    return config


GATEWAY_CONFIG = _load_gateway_config()
RAG_AGENT_URL = str(GATEWAY_CONFIG["rag_service"]["base_url"]).rstrip("/")
RAG_TIMEOUT = int(GATEWAY_CONFIG["rag_service"]["timeout"])
RAG_HEALTH_TIMEOUT = int(GATEWAY_CONFIG["rag_service"]["health_timeout"])


mock_database: dict[str, Any] = {
    "students": {},
    "parents": {},
    "bindings": {"parent_to_children": {}, "child_to_parents": {}},
    "checkins": {},
    "psych_reports": {},
    "psych_status": {},
    "strategy_state": {},
    "alerts": {},
    "grades": {},
    "admin": {
        "login_events": [],
        "activity_events": [],
        "model_usage": {
            "provider": "qwen",
            "model": os.getenv("DASHSCOPE_MODEL", "qwen-plus"),
            "requests": 0,
            "success": 0,
            "failed": 0,
            "prompt_chars": 0,
            "last_used_at": None,
            "scenes": {},
        },
    },
}


def now_ts() -> float:
    return time.time()


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def generate_code() -> str:
    return str(random.randint(100000, 999999))


def get_current_user() -> str:
    return request.headers.get("X-User-ID", "student_001")


def format_error(message: str, code: int = 400):
    return jsonify({"success": False, "error": message}), code


def _trim_events(key: str, limit: int = 200):
    events = mock_database["admin"][key]
    if len(events) > limit:
        del events[:-limit]


def _record_activity(event_type: str, title: str, *, actor: str = "", target: str = "", details: str = "", meta: dict[str, Any] | None = None):
    mock_database["admin"]["activity_events"].append(
        {
            "id": int(now_ts() * 1000) + random.randint(1, 999),
            "event_type": event_type,
            "title": title,
            "actor": actor,
            "target": target,
            "details": details,
            "meta": meta or {},
            "created_at": now_str(),
        }
    )
    _trim_events("activity_events")


def _record_login(user_id: str, role: str, provider: str):
    mock_database["admin"]["login_events"].append(
        {
            "id": int(now_ts() * 1000) + random.randint(1, 999),
            "user_id": user_id,
            "role": role,
            "provider": provider,
            "created_at": now_str(),
        }
    )
    _trim_events("login_events")
    _record_activity("login", "用户登录", actor=user_id, details=f"{role} 通过 {provider} 登录")


def _record_model_usage(scene: str, *, prompt_text: str = "", success: bool = True):
    usage = mock_database["admin"]["model_usage"]
    usage["requests"] += 1
    usage["prompt_chars"] += len(prompt_text or "")
    usage["last_used_at"] = now_str()
    usage["scenes"][scene] = usage["scenes"].get(scene, 0) + 1
    if success:
        usage["success"] += 1
    else:
        usage["failed"] += 1


@app.before_request
def attach_request_context():
    g.request_id = request.headers.get("X-Request-ID") or uuid4().hex[:12]
    g.request_started_at = time.time()


@app.after_request
def append_response_headers(response: Response):
    response.headers["X-Request-ID"] = getattr(g, "request_id", uuid4().hex[:12])
    started_at = getattr(g, "request_started_at", None)
    if started_at is not None:
        duration_ms = round((time.time() - started_at) * 1000, 2)
        response.headers["X-Response-Time-Ms"] = str(duration_ms)
    return response


def _admin_recent_events(key: str, limit: int = 20) -> list[dict[str, Any]]:
    events = deepcopy(mock_database["admin"][key])
    events.sort(key=lambda item: item["created_at"], reverse=True)
    return events[:limit]


def _admin_user_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for student_id, profile in mock_database["students"].items():
        rows.append(
            {
                "user_id": student_id,
                "name": profile.get("name", student_id),
                "role": profile.get("role", "student"),
                "phone": profile.get("phone", ""),
                "grade": profile.get("grade", ""),
                "children_count": 0,
                "checkins": len(mock_database["checkins"].get(student_id, [])),
                "reports": len(mock_database["psych_reports"].get(student_id, [])),
                "alerts": len(mock_database["bindings"]["child_to_parents"].get(student_id, [])),
            }
        )
    for parent_id, profile in mock_database["parents"].items():
        rows.append(
            {
                "user_id": parent_id,
                "name": profile.get("name", parent_id),
                "role": "parent",
                "phone": profile.get("phone", ""),
                "grade": "",
                "children_count": len(profile.get("children", [])),
                "checkins": 0,
                "reports": 0,
                "alerts": len(mock_database["alerts"].get(parent_id, [])),
            }
        )
    rows.sort(key=lambda item: (item["role"], item["user_id"]))
    return rows


def _admin_app_summary() -> dict[str, Any]:
    total_checkins = sum(len(items) for items in mock_database["checkins"].values())
    total_reports = sum(len(items) for items in mock_database["psych_reports"].values())
    total_alerts = sum(len(items) for items in mock_database["alerts"].values())
    unread_alerts = sum(
        1
        for items in mock_database["alerts"].values()
        for alert in items
        if not alert.get("is_read", False)
    )
    return {
        "students": len(mock_database["students"]),
        "parents": len(mock_database["parents"]),
        "bindings": sum(len(items) for items in mock_database["bindings"]["parent_to_children"].values()),
        "checkins": total_checkins,
        "reports": total_reports,
        "alerts": total_alerts,
        "unread_alerts": unread_alerts,
    }


def _admin_rag_summary() -> dict[str, Any]:
    headers = {"X-API-Key": _internal_agent_api_key()}
    return {
        "health": _safe_json_from_rag("/api/health", headers=headers),
        "status": _safe_json_from_rag("/api/status", headers=headers),
        "index": _safe_json_from_rag("/api/index/info", headers=headers),
        "metrics": _safe_json_from_rag("/api/metrics", headers=headers),
        "logs": _safe_json_from_rag("/api/logs?limit=20", headers=headers),
        "errors": _safe_json_from_rag("/api/logs/errors?limit=10", headers=headers),
    }


def _admin_model_config_summary() -> dict[str, Any]:
    try:
        resp = requests.get(_rag_url("/api/admin/model-config"), timeout=15)
        if resp.ok:
            payload = resp.json()
            return payload.get("config", {})
    except Exception:
        pass
    return {
        "provider": "qwen",
        "chat_model": os.getenv("DASHSCOPE_MODEL", "qwen-plus"),
        "rag_model": os.getenv("RAG_DASHSCOPE_MODEL", os.getenv("DASHSCOPE_MODEL", "qwen-plus")),
        "embedding_model": os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v3"),
        "fallback_embedding_model": os.getenv("DASHSCOPE_EMBEDDING_FALLBACK_MODEL", "text-embedding-v2"),
    }


def _rag_url(path: str) -> str:
    return f"{RAG_AGENT_URL.rstrip('/')}{path}"


def _internal_agent_api_key() -> str:
    return os.getenv("AGENT_API_KEY") or DEFAULT_DEV_AGENT_KEY


def _route_registry() -> list[dict[str, Any]]:
    aliases = deepcopy(GATEWAY_CONFIG.get("routes", {}).get("aliases", []))
    aliases.extend(
        [
            {"path": "/api/admin/overview", "target": "gateway:self", "methods": ["GET"], "description": "Admin overview"},
            {"path": "/api/admin/users", "target": "gateway:self", "methods": ["GET"], "description": "Admin users"},
            {"path": "/api/admin/logins", "target": "gateway:self", "methods": ["GET"], "description": "Admin logins"},
            {"path": "/api/admin/activity", "target": "gateway:self", "methods": ["GET"], "description": "Admin activity"},
            {"path": "/api/admin/model-usage", "target": "gateway:self", "methods": ["GET"], "description": "Model usage"},
            {"path": "/api/admin/model-config", "target": f"{RAG_AGENT_URL}/api/admin/model-config", "methods": ["GET", "POST"], "description": "Model config proxy"},
            {"path": "/api/health", "target": "gateway:self", "methods": ["GET"], "description": "Gateway health"},
            {"path": "/api/admin/routes", "target": "gateway:self", "methods": ["GET"], "description": "Gateway route registry"},
        ]
    )
    return aliases


def _proxy_to_rag(
    path: str,
    method: str = "GET",
    *,
    timeout: int = 60,
    pass_query: bool = True,
    include_agent_auth: bool = False,
):
    url = _rag_url(path)
    params = request.args.to_dict(flat=True) if pass_query else None
    headers = {"X-Forwarded-By": "warmstudy-api-gateway"}
    if include_agent_auth:
        headers["X-API-Key"] = _internal_agent_api_key()

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
            raw_body = request.get_data()
            kwargs: dict[str, Any] = {
                "method": method,
                "url": url,
                "params": params,
                "headers": headers,
                "timeout": timeout or RAG_TIMEOUT,
            }
            if json_body is not None and method in {"POST", "PUT", "PATCH", "DELETE"}:
                kwargs["json"] = json_body
            elif raw_body and method in {"POST", "PUT", "PATCH"}:
                kwargs["data"] = raw_body
            resp = requests.request(**kwargs)
    except requests.RequestException as exc:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"RAG service request failed: {exc}",
                    "rag_agent_url": RAG_AGENT_URL,
                }
            ),
            502,
        )

    content_type = resp.headers.get("Content-Type", "application/json")
    excluded_headers = {"content-encoding", "content-length", "transfer-encoding", "connection"}
    proxy_headers = [
        (name, value) for name, value in resp.headers.items() if name.lower() not in excluded_headers
    ]
    return Response(resp.content, resp.status_code, proxy_headers, content_type=content_type)


def _safe_json_from_rag(path: str, method: str = "GET", **kwargs):
    headers = kwargs.pop("headers", {})
    try:
        timeout = kwargs.pop("timeout", RAG_HEALTH_TIMEOUT)
        resp = requests.request(method=method, url=_rag_url(path), timeout=timeout, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:  # pragma: no cover - diagnostic fallback
        return {"ok": False, "error": str(exc)}


def _child_name(child_id: str) -> str:
    return mock_database["students"].get(child_id, {}).get("name", f"学生{child_id[-3:]}")


def _child_grade(child_id: str) -> str:
    return mock_database["students"].get(child_id, {}).get("grade", "初一")


def _ensure_student_profile(user_id: str, *, phone: str | None = None, role: str = "student") -> dict[str, Any]:
    existing = mock_database["students"].get(user_id)
    if existing:
        if phone and not existing.get("phone"):
            existing["phone"] = phone
        existing["school_stage"] = infer_school_stage(existing.get("age"), existing.get("grade"))
        return existing

    profile = {
        "user_id": user_id,
        "name": f"{'学生' if role == 'student' else '用户'}{user_id[-4:]}",
        "phone": phone or "",
        "role": role,
        "gender": "",
        "age": None,
        "grade": "初一",
        "school_stage": "junior",
    }
    mock_database["students"][user_id] = profile
    return profile


def _refresh_student_strategy(user_id: str) -> dict[str, Any]:
    profile = _ensure_student_profile(user_id)
    reports = mock_database["psych_reports"].get(user_id, [])
    latest_report = reports[-1] if reports else None
    recent_checkins = mock_database["checkins"].get(user_id, [])[-7:]
    strategy = build_student_strategy(
        profile,
        recent_checkins=recent_checkins,
        latest_report=latest_report,
    )
    mock_database["strategy_state"][user_id] = strategy
    return strategy


def _upsert_student_profile(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    profile = _ensure_student_profile(user_id)
    for key in ("name", "gender", "grade", "phone"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            profile[key] = value.strip()

    age_value = payload.get("age")
    if age_value not in (None, ""):
        try:
            profile["age"] = int(age_value)
        except (TypeError, ValueError):
            pass

    profile["school_stage"] = infer_school_stage(profile.get("age"), profile.get("grade"))
    mock_database["students"][user_id] = profile
    _refresh_student_strategy(user_id)
    return profile


def _student_status_snapshot(user_id: str) -> dict[str, Any]:
    payload = mock_database["psych_status"].get(user_id) or _build_status_payload(user_id)
    mock_database["psych_status"][user_id] = payload
    return payload


def _parent_chat_context(parent_id: str, child_id: str | None) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None, dict[str, Any]]:
    parent = _ensure_parent(parent_id)
    resolved_child_id = child_id or (parent.get("children") or [None])[0]
    child_profile = _ensure_student_profile(resolved_child_id) if resolved_child_id else None
    child_status = _student_status_snapshot(resolved_child_id) if resolved_child_id else None
    latest_report = (
        mock_database["psych_reports"].get(resolved_child_id, [])[-1]
        if resolved_child_id and mock_database["psych_reports"].get(resolved_child_id)
        else None
    )
    unread_alerts = sum(
        1 for item in mock_database["alerts"].get(parent["parent_id"], []) if not item.get("is_read")
    )
    strategy = build_parent_strategy(
        parent,
        child_profile,
        child_status=child_status,
        latest_report=latest_report,
        unread_alerts=unread_alerts,
    )
    return parent, child_profile, child_status, strategy


def _normalize_parent_id(parent_id: Any) -> str:
    text = str(parent_id or "").strip()
    if not text:
        return "parent_0001"
    if text.startswith("parent_"):
        return text
    if text.isdigit():
        return f"parent_{text.zfill(4)}"
    return f"parent_{text}"


def _ensure_parent(parent_id: str, *, phone: str | None = None) -> dict[str, Any]:
    parent_id = _normalize_parent_id(parent_id)
    existing = mock_database["parents"].get(parent_id)
    if existing:
        return existing

    qr_token = f"qr_{parent_id}"
    profile = {
        "id": int(parent_id.split("_")[-1]) if parent_id.split("_")[-1].isdigit() else random.randint(1000, 9999),
        "parent_id": parent_id,
        "phone": phone or "",
        "name": f"家长{parent_id[-4:]}",
        "qr_token": qr_token,
        "children": ["student_001"],
    }
    mock_database["parents"][parent_id] = profile
    mock_database["bindings"]["parent_to_children"][parent_id] = list(profile["children"])
    for child_id in profile["children"]:
        mock_database["bindings"]["child_to_parents"].setdefault(child_id, [])
        if parent_id not in mock_database["bindings"]["child_to_parents"][child_id]:
            mock_database["bindings"]["child_to_parents"][child_id].append(parent_id)
        _ensure_student_profile(child_id)
    return profile


def _normalize_radar_scores(scores: list[Any] | None) -> list[int]:
    default_scores = [3, 3, 3, 3, 3, 3]
    if not scores:
        return default_scores

    normalized = []
    for index in range(6):
        try:
            value = int(round(float(scores[index])))
        except Exception:
            value = default_scores[index]
        normalized.append(max(1, min(5, value)))
    return normalized


def _risk_level_from_scores(scores: list[int]) -> int:
    return sum(1 for score in scores if score >= 4)


def _risk_label(risk_level: int) -> str:
    if risk_level >= 4:
        return "high"
    if risk_level >= 2:
        return "medium"
    return "low"


def _build_dimensions(scale_id: str, radar_scores: list[int]) -> list[dict[str, Any]]:
    if scale_id == "pressure":
        labels = ["学业压力", "睡眠恢复", "情绪稳定", "专注状态", "社交支持", "放松能力"]
    elif scale_id == "communication":
        labels = ["表达意愿", "被理解感", "交流频率", "冲突处理", "尊重感", "信任感"]
    else:
        labels = ["情绪", "睡眠", "学习", "社交", "压力", "沟通"]

    dimensions = []
    for name, score in zip(labels, radar_scores):
        if score >= 4:
            level = "concerning"
            level_label = "偏高"
        elif score >= 3:
            level = "moderate"
            level_label = "中等"
        elif score >= 2:
            level = "mild"
            level_label = "轻度"
        else:
            level = "normal"
            level_label = "正常"
        dimensions.append(
            {
                "name": name,
                "score": score,
                "max": 5,
                "level": level,
                "level_label": level_label,
                "pct": round(score / 5 * 100, 1),
            }
        )
    return dimensions


def _build_report(user_id: str, scale_id: str, answers: list[int]) -> dict[str, Any]:
    radar_scores = _normalize_radar_scores(answers[:6] if answers else None)
    avg_score = sum(radar_scores) / max(len(radar_scores), 1)
    normalized = round(avg_score / 5 * 100, 1)
    risk_level = _risk_level_from_scores(radar_scores)

    if normalized >= 80:
        level = "severe"
        summary = "多项指标明显偏高，建议尽快安排重点关注与人工干预。"
    elif normalized >= 65:
        level = "concerning"
        summary = "存在较明显的心理波动与压力负担，建议持续跟进。"
    elif normalized >= 45:
        level = "moderate"
        summary = "整体状态中等，建议通过陪伴、作息和情绪支持持续优化。"
    elif normalized >= 30:
        level = "mild"
        summary = "存在轻微波动，当前以日常关注和规律支持为主。"
    else:
        level = "normal"
        summary = "当前状态总体平稳，可继续保持健康作息与沟通。"

    report_id = int(now_ts() * 1000)
    child_name = _child_name(user_id)
    child_grade = _child_grade(user_id)
    dimensions = _build_dimensions(scale_id, radar_scores)

    report = {
        "id": report_id,
        "user_id": user_id,
        "scale_id": scale_id,
        "level": level,
        "normalized": normalized,
        "summary": summary,
        "advice": "建议结合学生近一周打卡、对话与家庭观察结果进行持续跟进。",
        "key_findings": [
            f"六维雷达中有 {risk_level} 项达到重点关注阈值。",
            "建议结合日常打卡、情绪趋势与家校沟通信息综合判断。",
            "本报告适合用作家长侧的阶段性观察依据，不替代专业诊断。",
        ],
        "dimensions": dimensions,
        "parent_advice": "优先关注作息、沟通频率和情绪表达，减少简单施压，增加支持性回应。",
        "date": today_str(),
        "child_name": child_name,
        "child_grade": child_grade,
        "radarScores": radar_scores,
        "riskLevel": risk_level,
        "created_at": now_str(),
    }
    return report


def _build_status_payload(user_id: str) -> dict[str, Any]:
    student = _ensure_student_profile(user_id)
    reports = mock_database["psych_reports"].get(user_id, [])
    latest_report = reports[-1] if reports else None
    latest_checkins = mock_database["checkins"].get(user_id, [])[-7:]
    strategy = _refresh_student_strategy(user_id)

    if latest_checkins:
        metrics = {
            "emotion": round(sum(item.get("emotion", 3) for item in latest_checkins) / len(latest_checkins), 1),
            "sleep": round(sum(item.get("sleep", 3) for item in latest_checkins) / len(latest_checkins), 1),
            "study": round(sum(item.get("study", 3) for item in latest_checkins) / len(latest_checkins), 1),
            "social": round(sum(item.get("social", 3) for item in latest_checkins) / len(latest_checkins), 1),
        }
    else:
        metrics = {"emotion": 3, "sleep": 3, "study": 3, "social": 3}

    radar_scores = latest_report["radarScores"] if latest_report else [3, 3, 3, 3, 3, 3]
    risk_level = latest_report["riskLevel"] if latest_report else 0

    return {
        "success": True,
        "status": "ok",
        "user_id": user_id,
        "psych": {
            "metrics": metrics,
            "latest_report": {
                "level": latest_report["level"] if latest_report else "normal",
                "normalized": latest_report["normalized"] if latest_report else 0,
                "date": latest_report["date"] if latest_report else None,
            },
        },
        "radarScores": radar_scores,
        "riskLevel": risk_level,
        "strategy": strategy,
        "summary": {
            "profile": {
                "user_id": user_id,
                "name": student["name"],
                "gender": student.get("gender", ""),
                "age": student.get("age"),
                "grade": student.get("grade", "初一"),
                "school_stage": student.get("school_stage", infer_school_stage(student.get("age"), student.get("grade"))),
            }
        },
    }


def _ensure_demo_seed() -> None:
    _ensure_student_profile("student_001", phone="13800138000")
    parent = _ensure_parent("parent_0001", phone="13900139000")
    child_id = parent["children"][0]

    if child_id not in mock_database["checkins"]:
        mock_database["checkins"][child_id] = [
            {
                "user_id": child_id,
                "emotion": 4,
                "sleep": 3,
                "study": 3,
                "social": 4,
                "note": "今天状态一般，但愿意表达。",
                "date": (datetime.now() - timedelta(days=offset)).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for offset in range(3, -1, -1)
        ]

    if child_id not in mock_database["psych_reports"]:
        report = _build_report(child_id, "weekly", [4, 3, 3, 4, 2, 3])
        mock_database["psych_reports"][child_id] = [report]
        mock_database["psych_status"][child_id] = _build_status_payload(child_id)

    if parent["parent_id"] not in mock_database["alerts"]:
        mock_database["alerts"][parent["parent_id"]] = [
            {
                "id": 1,
                "child_id": child_id,
                "child_name": _child_name(child_id),
                "alert_type": "emotion_drop",
                "title": "情绪波动提醒",
                "content": "孩子最近存在轻度情绪波动，建议及时陪伴沟通。",
                "is_read": False,
                "created_at": now_str(),
            }
        ]


def _get_parent_children(parent_id: str) -> list[str]:
    parent_id = _normalize_parent_id(parent_id)
    _ensure_parent(parent_id)
    return list(mock_database["bindings"]["parent_to_children"].get(parent_id, []))


def _append_alert(parent_id: str, child_id: str, alert_type: str, title: str, content: str) -> None:
    parent_id = _normalize_parent_id(parent_id)
    alerts = mock_database["alerts"].setdefault(parent_id, [])
    alerts.append(
        {
            "id": int(now_ts() * 1000) + len(alerts),
            "child_id": child_id,
            "child_name": _child_name(child_id),
            "alert_type": alert_type,
            "title": title,
            "content": content,
            "is_read": False,
            "created_at": now_str(),
        }
    )


_ensure_demo_seed()


@app.route("/api/auth/send-code", methods=["POST"])
def send_code():
    data = request.get_json(silent=True) or {}
    phone = (data.get("phone") or "").strip()
    if not phone:
        return format_error("Phone is required")

    code = generate_code()
    print(f"[verify-code] {phone}: {code}")
    return jsonify({"success": True, "message": "Verification code sent", "code": code})


@app.route("/api/auth/login/phone", methods=["POST"])
def login_by_phone():
    data = request.get_json(silent=True) or {}
    phone = (data.get("phone") or "").strip()
    code = (data.get("code") or "").strip()
    role = (data.get("role") or "student").strip() or "student"
    if not phone or not code:
        return format_error("Phone and code are required")

    user_id = f"{role}_{phone[-4:]}"
    if role == "parent":
        parent = _ensure_parent(user_id, phone=phone)
        payload = {
            "user_id": parent["parent_id"],
            "name": parent["name"],
            "phone": phone,
            "role": role,
            "token": f"token_{parent['parent_id']}_{int(now_ts())}",
        }
    else:
        student = _ensure_student_profile(user_id, phone=phone, role=role)
        payload = {
            "user_id": student["user_id"],
            "name": student["name"],
            "phone": phone,
            "role": role,
            "token": f"token_{student['user_id']}_{int(now_ts())}",
        }
    _record_login(payload["user_id"], role, "phone")
    return jsonify({"success": True, "data": payload})


@app.route("/api/auth/login/wechat", methods=["POST"])
def login_by_wechat():
    data = request.get_json(silent=True) or {}
    wx_code = (data.get("wx_code") or "").strip()
    role = (data.get("role") or "student").strip() or "student"
    if not wx_code:
        return format_error("wx_code is required")

    suffix = wx_code[-6:] if len(wx_code) >= 6 else f"{random.randint(100000, 999999)}"
    phone = f"13{suffix[:9].ljust(9, '0')}"[:11]
    proxy_data = {"phone": phone, "code": "wechat", "role": role}
    with app.test_request_context(json=proxy_data):
        return login_by_phone()


def _proxy_chat(path: str, fallback_text: str):
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    user_id = data.get("user_id", get_current_user())
    if not message:
        return format_error("Message is required")

    try:
        resp = requests.post(_rag_url(path), json={"user_id": user_id, "message": message}, timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            _record_model_usage(path, prompt_text=message, success=True)
            _record_activity("chat", "模型对话请求", actor=user_id, target=path, details="via gateway")
            return jsonify(
                {
                    "success": True,
                    "response": result.get("response", result.get("answer", fallback_text)),
                    "ai_name": "暖暖",
                    "emotion": result.get("emotion", "neutral"),
                    "crisis_level": result.get("crisis_level", "safe"),
                    "type": result.get("type", "normal_support"),
                }
            )
    except Exception:
        _record_model_usage(path, prompt_text=message, success=False)

    return jsonify({"success": True, "response": fallback_text, "ai_name": "暖暖", "type": "fallback"})


@app.route("/api/student/profile", methods=["POST"])
def update_student_profile():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", get_current_user())
    profile = _upsert_student_profile(user_id, data)
    payload = _student_status_snapshot(user_id)
    _record_activity(
        "profile",
        "学生资料更新",
        actor=user_id,
        target=user_id,
        details=f"stage={profile.get('school_stage', 'unknown')}",
    )
    return jsonify(
        {
            "success": True,
            "message": "Student profile updated",
            "profile": normalize_student_profile(profile),
            "strategy": deepcopy(mock_database["strategy_state"].get(user_id, {})),
            "status": payload,
        }
    )


def _adapt_gateway_response(
    text: str,
    *,
    role: str,
    strategy: dict[str, Any],
    profile: dict[str, Any] | None = None,
    child_profile: dict[str, Any] | None = None,
) -> str:
    if not text:
        return text

    if role == "student":
        student = normalize_student_profile(profile)
        stage = student.get("school_stage", "unknown")
        adapted = text.replace("您", "你").replace("家长", "家里人")
        if stage == "primary":
            adapted = adapted.replace("建议", "可以试试").replace("尝试", "试试")
            if len(adapted) > 120:
                adapted = adapted[:120].rstrip("，。； ") + "。"
        elif stage == "senior":
            adapted = adapted.replace("你要", "你可以").replace("必须", "尽量")
        name = student.get("name") or ""
        if name and not adapted.startswith(name):
            adapted = f"{name}，{adapted}"
        return adapted

    child = normalize_student_profile(child_profile)
    adapted = text.replace("你", "您")
    if child.get("school_stage") == "primary":
        adapted = adapted.replace("沟通", "和孩子说话")
    if "建议" not in adapted and "可以先" not in adapted:
        adapted = f"可以先这样做：{adapted}"
    return adapted


def _proxy_chat(path: str, fallback_text: str, *, role: str):
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    user_id = data.get("user_id", get_current_user())
    session_id = str(data.get("session_id") or f"{role}_{user_id}")
    if not message:
        return format_error("Message is required")

    outbound: dict[str, Any] = {
        "user_id": user_id,
        "message": message,
        "session_id": session_id,
        "user_type": role,
    }

    if role == "student":
        local_profile = data.get("profile") if isinstance(data.get("profile"), dict) else {}
        profile = _upsert_student_profile(user_id, local_profile)
        psych_status = _student_status_snapshot(user_id)
        outbound.update(
            {
                "profile": normalize_student_profile(profile),
                "psych_status": psych_status,
                "strategy": deepcopy(mock_database["strategy_state"].get(user_id, {})),
            }
        )
    else:
        requested_child_id = (data.get("child_id") or "").strip() or None
        parent, child_profile, child_status, strategy = _parent_chat_context(user_id, requested_child_id)
        outbound.update(
            {
                "profile": deepcopy(parent),
                "child_id": child_profile.get("user_id") if child_profile else None,
                "child_profile": normalize_student_profile(child_profile),
                "child_status": child_status,
                "strategy": strategy,
            }
        )

    try:
        resp = requests.post(_rag_url(path), json=outbound, timeout=30)
        try:
            result = resp.json()
        except ValueError:
            result = {}
        if resp.status_code == 200:
            if result.get("success") is False:
                _record_model_usage(path, prompt_text=message, success=False)
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": result.get("error", "RAG service returned an error"),
                            "response": result.get("response", fallback_text),
                            "ai_name": "暖暖" if role == "student" else "家庭助手",
                            "type": result.get("type", "upstream_error"),
                            "knowledge_count": result.get("knowledge_count"),
                            "knowledge_sources": result.get("knowledge_sources", []),
                            "session_id": session_id,
                            "strategy": outbound.get("strategy", {}),
                        }
                    ),
                    502,
                )
            _record_model_usage(path, prompt_text=message, success=True)
            _record_activity("chat", "模型对话请求", actor=user_id, target=path, details=f"role={role};session={session_id}")
            adapted_response = _adapt_gateway_response(
                result.get("response", result.get("answer", fallback_text)),
                role=role,
                strategy=outbound.get("strategy", {}),
                profile=outbound.get("profile"),
                child_profile=outbound.get("child_profile"),
            )
            return jsonify(
                {
                    "success": True,
                    "response": adapted_response,
                    "ai_name": "暖暖" if role == "student" else "家庭助手",
                    "emotion": result.get("emotion", "neutral"),
                    "crisis_level": result.get("crisis_level", "safe"),
                    "knowledge_count": result.get("knowledge_count"),
                    "knowledge_sources": result.get("knowledge_sources", []),
                    "type": result.get("type", "normal_support"),
                    "strategy": outbound.get("strategy", {}),
                    "session_id": session_id,
                }
            )
        _record_model_usage(path, prompt_text=message, success=False)
        return (
            jsonify(
                {
                    "success": False,
                    "error": result.get("error", f"RAG service returned HTTP {resp.status_code}"),
                    "response": result.get("response"),
                    "ai_name": "暖暖" if role == "student" else "家庭助手",
                    "type": result.get("type", "upstream_error"),
                    "knowledge_count": result.get("knowledge_count"),
                    "knowledge_sources": result.get("knowledge_sources", []),
                    "session_id": session_id,
                    "strategy": outbound.get("strategy", {}),
                }
            ),
            502,
        )
    except Exception as exc:
        _record_model_usage(path, prompt_text=message, success=False)
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"RAG service request failed: {exc}",
                    "response": fallback_text,
                    "ai_name": "暖暖" if role == "student" else "家庭助手",
                    "type": "upstream_error",
                    "session_id": session_id,
                    "strategy": outbound.get("strategy", {}),
                }
            ),
            502,
        )


@app.route("/api/student/chat", methods=["POST"])
def student_chat():
    return _proxy_chat("/api/student/chat", "我在这里，愿意继续听你说。", role="student")


@app.route("/api/parent/chat", methods=["POST"])
def parent_chat():
    return _proxy_chat("/api/parent/chat", "建议先稳定情绪，再从作息、沟通和陪伴三个方面逐步支持孩子。", role="parent")


@app.route("/api/student/checkin", methods=["POST"])
def student_checkin():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", get_current_user())
    _ensure_student_profile(user_id)

    checkin_data = {
        "user_id": user_id,
        "emotion": int(data.get("emotion", 3)),
        "sleep": int(data.get("sleep", 3)),
        "study": int(data.get("study", 3)),
        "social": int(data.get("social", 3)),
        "note": data.get("note", ""),
        "date": now_str(),
    }
    mock_database["checkins"].setdefault(user_id, []).append(checkin_data)
    _record_activity("checkin", "学生打卡", actor=user_id, target=user_id, details=f"emotion={checkin_data['emotion']}")

    if checkin_data["emotion"] <= 2:
        for parent_id in mock_database["bindings"]["child_to_parents"].get(user_id, []):
            _append_alert(
                parent_id,
                user_id,
                "emotion_drop",
                "情绪波动提醒",
                "学生最近一次情绪打卡偏低，建议家长主动关心并保持沟通。",
            )

    mock_database["psych_status"][user_id] = _build_status_payload(user_id)
    _refresh_student_strategy(user_id)
    _record_activity("checkin", "学生打卡已同步策略", actor=user_id, target=user_id)
    return jsonify({"success": True, "message": "Check-in saved", "data": checkin_data})


@app.route("/api/student/checkin/<user_id>", methods=["GET"])
def get_checkin_history(user_id: str):
    days = int(request.args.get("days", 7))
    checkins = mock_database["checkins"].get(user_id, [])
    cutoff = datetime.now() - timedelta(days=days)
    recent = [item for item in checkins if datetime.strptime(item["date"], "%Y-%m-%d %H:%M:%S") > cutoff]
    return jsonify({"success": True, "data": recent, "records": recent, "count": len(recent)})


@app.route("/api/student/psych/test", methods=["POST"])
def submit_psych_test():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", get_current_user())
    answers = data.get("answers", []) or []
    scale_id = data.get("test_type", "weekly")
    _ensure_student_profile(user_id)

    report = _build_report(user_id, scale_id, answers)
    mock_database["psych_reports"].setdefault(user_id, []).append(report)
    mock_database["psych_status"][user_id] = _build_status_payload(user_id)
    _refresh_student_strategy(user_id)

    if report["riskLevel"] >= 3:
        for parent_id in mock_database["bindings"]["child_to_parents"].get(user_id, []):
            _append_alert(
                parent_id,
                user_id,
                "test_concerning",
                "测评结果提醒",
                "学生最新一次心理测评显示存在较高关注项，建议查看详细报告。",
            )

    return jsonify({"success": True, "message": "Assessment submitted", "data": report})


@app.route("/api/student/psych/status/<user_id>", methods=["GET"])
def get_psych_status(user_id: str):
    _ensure_student_profile(user_id)
    payload = mock_database["psych_status"].get(user_id) or _build_status_payload(user_id)
    mock_database["psych_status"][user_id] = payload
    return jsonify(payload)


@app.route("/api/parent/login", methods=["POST"])
def parent_login():
    data = request.get_json(silent=True) or {}
    phone = (data.get("phone") or "").strip()
    if not phone:
        return format_error("Phone is required")
    parent_id = f"parent_{phone[-4:]}"
    parent = _ensure_parent(parent_id, phone=phone)
    _record_login(parent["parent_id"], "parent", "parent_portal")
    return jsonify(
        {
            "success": True,
            "account": {
                "id": parent["id"],
                "phone": parent["phone"],
                "name": parent["name"],
                "qr_token": parent["qr_token"],
            },
            "bound_children": _get_parent_children(parent_id),
        }
    )


@app.route("/api/parent/qr_token", methods=["POST"])
def get_parent_qr_token():
    data = request.get_json(silent=True) or {}
    parent_id = data.get("parent_id")
    if parent_id in (None, ""):
        return format_error("parent_id is required")
    parent_key = _normalize_parent_id(parent_id)
    parent = _ensure_parent(parent_key)
    token = parent["qr_token"]
    qr_url = f"warmstudy://bind-parent?token={token}"
    _record_activity("binding", "生成绑定二维码", actor=parent["parent_id"], target=token)
    return jsonify({"success": True, "token": token, "qr_url": qr_url})


@app.route("/api/parent/child/bind", methods=["POST"])
def bind_child():
    data = request.get_json(silent=True) or {}
    parent_id = _normalize_parent_id(data.get("parent_id"))
    child_id = (data.get("child_id") or "").strip()
    if not parent_id or not child_id:
        return format_error("parent_id and child_id are required")

    _ensure_parent(parent_id)
    _ensure_student_profile(child_id)
    children = mock_database["bindings"]["parent_to_children"].setdefault(parent_id, [])
    if child_id not in children:
        children.append(child_id)
    parents = mock_database["bindings"]["child_to_parents"].setdefault(child_id, [])
    if parent_id not in parents:
        parents.append(parent_id)
    mock_database["parents"][parent_id]["children"] = children
    _record_activity("binding", "家长绑定孩子", actor=parent_id, target=child_id, details="parent initiated")
    return jsonify({"success": True, "message": "Child bound successfully"})


@app.route("/api/child/bind", methods=["POST"])
def bind_parent_by_token():
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    child_id = (data.get("child_id") or "").strip()
    if not token or not child_id:
        return format_error("token and child_id are required")

    matched_parent_id = None
    for parent_id, parent in mock_database["parents"].items():
        if parent["qr_token"] == token:
            matched_parent_id = parent_id
            break
    if not matched_parent_id:
        return format_error("Invalid token", 404)

    _ensure_student_profile(child_id)
    children = mock_database["bindings"]["parent_to_children"].setdefault(matched_parent_id, [])
    if child_id not in children:
        children.append(child_id)
    mock_database["parents"][matched_parent_id]["children"] = children
    mock_database["bindings"]["child_to_parents"].setdefault(child_id, [])
    if matched_parent_id not in mock_database["bindings"]["child_to_parents"][child_id]:
        mock_database["bindings"]["child_to_parents"][child_id].append(matched_parent_id)
    _record_activity("binding", "扫码绑定成功", actor=child_id, target=matched_parent_id, details="child initiated")

    return jsonify(
        {
            "success": True,
            "parent_name": mock_database["parents"][matched_parent_id]["name"],
        }
    )


@app.route("/api/parent/children/profiles", methods=["POST"])
def get_children_profiles():
    data = request.get_json(silent=True) or {}
    child_ids = [item.strip() for item in str(data.get("child_ids", "")).split(",") if item.strip()]
    profiles = []
    for child_id in child_ids:
        student = _ensure_student_profile(child_id)
        profiles.append({"user_id": child_id, "name": student["name"], "grade": student.get("grade", "初一")})
    return jsonify({"success": True, "profiles": profiles})


@app.route("/api/parent/child/<child_id>/status", methods=["GET"])
def get_child_status(child_id: str):
    _ensure_student_profile(child_id)
    payload = mock_database["psych_status"].get(child_id) or _build_status_payload(child_id)
    mock_database["psych_status"][child_id] = payload
    return jsonify(payload)


@app.route("/api/parent/child/<child_id>/checkins", methods=["GET"])
def get_child_checkins(child_id: str):
    days = int(request.args.get("days", 7))
    checkins = mock_database["checkins"].get(child_id, [])
    cutoff = datetime.now() - timedelta(days=days)
    recent = [item for item in checkins if datetime.strptime(item["date"], "%Y-%m-%d %H:%M:%S") > cutoff]
    return jsonify({"success": True, "records": recent, "count": len(recent)})


@app.route("/api/parent/child/<child_id>/ai_advice", methods=["GET"])
def get_daily_advice(child_id: str):
    payload = mock_database["psych_status"].get(child_id) or _build_status_payload(child_id)
    risk_level = payload.get("riskLevel", 0)
    if risk_level >= 3:
        advice = "建议本周优先减少施压，增加陪伴式沟通，并关注孩子作息与睡眠恢复。"
        focus = "情绪支持"
    elif risk_level >= 1:
        advice = "建议通过规律作息、轻度运动和日常倾听帮助孩子稳定状态。"
        focus = "日常陪伴"
    else:
        advice = "整体状态较平稳，建议继续保持正向反馈与固定沟通时间。"
        focus = "保持节奏"
    return jsonify({"success": True, "advice": advice, "focus": focus})


@app.route("/api/parent/child/grade", methods=["POST"])
def submit_grade():
    data = request.get_json(silent=True) or {}
    child_id = data.get("user_id") or "student_001"
    grade_entry = {
        "subject": data.get("subject", ""),
        "score": data.get("score", 0),
        "exam_date": data.get("exam_date", today_str()),
    }
    mock_database["grades"].setdefault(child_id, []).append(grade_entry)
    return jsonify({"success": True, "message": "Grade saved", "data": grade_entry})


@app.route("/api/parent/child/<child_id>/psych_reports", methods=["GET"])
def get_child_psych_reports(child_id: str):
    limit = int(request.args.get("limit", 5))
    reports = deepcopy(mock_database["psych_reports"].get(child_id, []))
    reports.sort(key=lambda item: item["id"], reverse=True)
    slim_reports = [
        {
            "id": report["id"],
            "scale_id": report["scale_id"],
            "level": report["level"],
            "normalized": report["normalized"],
            "summary": report["summary"],
            "advice": report["advice"],
            "date": report["date"],
        }
        for report in reports[:limit]
    ]
    return jsonify({"success": True, "reports": slim_reports})


@app.route("/api/parent/child/<child_id>/psych/latest", methods=["GET"])
def get_child_psych_latest(child_id: str):
    payload = mock_database["psych_status"].get(child_id) or _build_status_payload(child_id)
    latest_report = mock_database["psych_reports"].get(child_id, [])[-1] if mock_database["psych_reports"].get(child_id) else None
    return jsonify(
        {
            "success": True,
            "latest": {
                "emotion": payload["psych"]["metrics"]["emotion"],
                "emotion_label": "平稳" if payload["psych"]["metrics"]["emotion"] >= 3 else "波动",
                "date": latest_report["date"] if latest_report else None,
                "risk_level": _risk_label(payload["riskLevel"]),
            },
        }
    )


@app.route("/api/parent/report/<report_id>", methods=["GET"])
def get_child_report_detail(report_id: str):
    for reports in mock_database["psych_reports"].values():
        for report in reports:
            if str(report["id"]) == str(report_id):
                return jsonify({"success": True, "report": deepcopy(report)})
    return format_error("Report not found", 404)


@app.route("/api/parent/alerts", methods=["GET"])
def get_parent_alerts():
    parent_id = _normalize_parent_id(request.args.get("parent_id", "parent_0001"))
    _ensure_parent(parent_id)
    alerts = deepcopy(mock_database["alerts"].setdefault(parent_id, []))
    alerts.sort(key=lambda item: item["created_at"], reverse=True)
    unread_count = sum(1 for alert in alerts if not alert["is_read"])
    return jsonify({"success": True, "alerts": alerts, "unread_count": unread_count})


@app.route("/api/parent/alerts/<int:alert_id>/read", methods=["POST"])
def mark_alert_read(alert_id: int):
    data = request.get_json(silent=True) or {}
    parent_id = _normalize_parent_id(data.get("parent_id", "parent_0001"))
    alerts = mock_database["alerts"].setdefault(parent_id, [])
    for alert in alerts:
        if alert["id"] == alert_id:
            alert["is_read"] = True
            _record_activity("alert", "预警已读", actor=parent_id, target=str(alert_id))
            return jsonify({"success": True})
    return format_error("Alert not found", 404)


@app.route("/api/parent/alerts/read_all", methods=["POST"])
def mark_all_alerts_read():
    data = request.get_json(silent=True) or {}
    parent_id = _normalize_parent_id(data.get("parent_id", "parent_0001"))
    alerts = mock_database["alerts"].setdefault(parent_id, [])
    marked_count = 0
    for alert in alerts:
        if not alert["is_read"]:
            alert["is_read"] = True
            marked_count += 1
    _record_activity("alert", "全部预警已读", actor=parent_id, details=f"marked={marked_count}")
    return jsonify({"success": True, "marked_count": marked_count})


@app.route("/api/health", methods=["GET"])
def health_check():
    rag_health = _safe_json_from_rag("/api/health")
    gateway_ok = rag_health.get("ok", True) if isinstance(rag_health, dict) else True
    return jsonify(
        {
            "success": True,
            "status": "healthy" if gateway_ok else "degraded",
            "timestamp": datetime.now().isoformat(),
            "service": "warmstudy-api-gateway",
            "version": "2.0.0",
            "request_id": getattr(g, "request_id", ""),
            "config": {
                "port": GATEWAY_CONFIG["server"]["port"],
                "rag_agent_url": RAG_AGENT_URL,
                "rag_timeout": RAG_TIMEOUT,
            },
            "rag": rag_health,
        }
    )


@app.route("/api/gateway/status", methods=["GET"])
def gateway_status():
    rag_health = _safe_json_from_rag("/api/health")
    rag_status = _safe_json_from_rag("/api/status")
    rag_index = _safe_json_from_rag("/api/index/info")
    return jsonify(
        {
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
                "rag_status_proxy": "/api/gateway/rag/status",
                "rag_docs_proxy": "/api/gateway/rag/docs",
            },
        }
    )


@app.route("/api/admin/overview", methods=["GET"])
def admin_overview():
    app_summary = _admin_app_summary()
    rag_summary = _admin_rag_summary()
    return jsonify(
        {
            "success": True,
            "generated_at": now_str(),
            "gateway": {
                "service": "warmstudy-admin-console",
                "status": "healthy",
                "port": 8000,
                "rag_agent_url": RAG_AGENT_URL,
            },
            "app": app_summary,
            "rag": rag_summary,
            "model_config": _admin_model_config_summary(),
            "model_usage": deepcopy(mock_database["admin"]["model_usage"]),
            "recent_logins": _admin_recent_events("login_events", limit=8),
            "recent_activity": _admin_recent_events("activity_events", limit=12),
        }
    )


@app.route("/api/admin/users", methods=["GET"])
def admin_users():
    role = (request.args.get("role") or "").strip()
    rows = _admin_user_rows()
    if role:
        rows = [row for row in rows if row["role"] == role]
    return jsonify({"success": True, "count": len(rows), "users": rows})


@app.route("/api/admin/logins", methods=["GET"])
def admin_logins():
    limit = int(request.args.get("limit", 50))
    return jsonify({"success": True, "count": len(mock_database["admin"]["login_events"]), "events": _admin_recent_events("login_events", limit=limit)})


@app.route("/api/admin/activity", methods=["GET"])
def admin_activity():
    limit = int(request.args.get("limit", 50))
    return jsonify({"success": True, "count": len(mock_database["admin"]["activity_events"]), "events": _admin_recent_events("activity_events", limit=limit)})


@app.route("/api/admin/model-usage", methods=["GET"])
def admin_model_usage():
    return jsonify({"success": True, "usage": deepcopy(mock_database["admin"]["model_usage"])})


@app.route("/api/admin/routes", methods=["GET"])
def admin_routes():
    return jsonify(
        {
            "success": True,
            "count": len(_route_registry()),
            "routes": _route_registry(),
        }
    )


@app.route("/api/admin/model-config", methods=["GET"])
def admin_model_config():
    return jsonify({"success": True, "config": _admin_model_config_summary()})


@app.route("/api/admin/model-config", methods=["POST"])
def admin_update_model_config():
    payload = request.get_json(silent=True) or {}
    try:
        resp = requests.post(_rag_url("/api/admin/model-config"), json=payload, timeout=20)
    except requests.RequestException as exc:
        return jsonify({"success": False, "error": f"Model config update failed: {exc}"}), 502

    if not resp.ok:
        return Response(resp.content, resp.status_code, content_type=resp.headers.get("Content-Type", "application/json"))

    data = resp.json()
    config = data.get("config", {})
    if config.get("chat_model"):
        mock_database["admin"]["model_usage"]["model"] = config["chat_model"]
    _record_activity("model_config", "模型配置更新", details=str(config))
    return jsonify({"success": True, "config": config})


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
    body = request.get_json(silent=True) or {}
    if "query" not in body and "message" in body:
        body = {**body, "query": body["message"]}
    headers = {"X-Forwarded-By": "warmstudy-api-gateway"}
    try:
        resp = requests.post(_rag_url("/api/chat"), json=body, headers=headers, timeout=60)
    except requests.RequestException as exc:
        _record_model_usage("/api/gateway/rag/chat", prompt_text=body.get("query", ""), success=False)
        return jsonify({"success": False, "error": f"RAG service request failed: {exc}"}), 502
    if resp.ok:
        _record_model_usage("/api/gateway/rag/chat", prompt_text=body.get("query", ""), success=True)
        _record_activity("rag_chat", "管理员触发 RAG 对话", target="knowledge_base", details=body.get("query", "")[:120])
    return Response(resp.content, resp.status_code, content_type=resp.headers.get("Content-Type", "application/json"))


@app.route("/api/chat", methods=["POST"])
def proxy_chat_alias():
    """Backward-compatible alias for clients that still call /api/chat."""
    return proxy_rag_chat()


@app.route("/api/agent/chat", methods=["POST"])
def proxy_agent_chat_alias():
    """Route governance alias for older clients that still call /api/agent/chat."""
    return proxy_rag_chat()


@app.route("/api/gateway/rag/ingest/sync", methods=["POST"])
def proxy_rag_ingest_sync():
    _record_activity("rag_ingest", "上传知识文件", target="knowledge_base")
    return _proxy_to_rag("/api/ingest/sync", method="POST", pass_query=False)


@app.route("/api/gateway/rag/reset", methods=["POST"])
def proxy_rag_reset():
    _record_activity("rag_reset", "重置知识库", target="knowledge_base")
    return _proxy_to_rag("/api/reset", method="POST", pass_query=False)


@app.route("/api/gateway/rag/delete", methods=["POST"])
def proxy_rag_delete():
    body = request.get_json(silent=True) or {}
    _record_activity("rag_delete", "删除知识来源", target=body.get("source", ""))
    return _proxy_to_rag("/api/delete", method="POST", pass_query=False)


@app.route("/api/gateway/rag/update", methods=["POST"])
def proxy_rag_update():
    _record_activity("rag_update", "更新知识来源", target=request.form.get("source", ""))
    return _proxy_to_rag("/api/update", method="POST", pass_query=False)


@app.route("/api/agent/psychology/emotion", methods=["POST"])
def proxy_psychology_emotion():
    return _proxy_to_rag("/api/agent/psychology/emotion", method="POST", pass_query=False, include_agent_auth=True)


@app.route("/api/agent/psychology/crisis", methods=["POST"])
def proxy_psychology_crisis():
    return _proxy_to_rag("/api/agent/psychology/crisis", method="POST", pass_query=False, include_agent_auth=True)


@app.route("/api/agent/psychology/knowledge", methods=["GET"])
def proxy_psychology_knowledge():
    return _proxy_to_rag("/api/agent/psychology/knowledge", include_agent_auth=True)


@app.route("/api/agent/psychology/categories", methods=["GET"])
def proxy_psychology_categories():
    return _proxy_to_rag("/api/agent/psychology/categories", include_agent_auth=True)


@app.route("/", methods=["GET"])
def index():
    return render_template("landing.html")


@app.route("/console", methods=["GET"])
def console():
    return render_template("gateway_dashboard.html", rag_agent_url=RAG_AGENT_URL)


@app.route("/psychology-test", methods=["GET"])
def psychology_test():
    return format_error("This standalone page has been removed. Use the admin console at /", 404)


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("WarmStudy API gateway")
    print(f"RAG Agent URL: {RAG_AGENT_URL}")
    print("Port: 8000")
    print("=" * 50 + "\n")
    app.run(host="0.0.0.0", port=8000, debug=False)

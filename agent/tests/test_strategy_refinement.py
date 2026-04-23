import api_gateway

from agent.strategy_engine import (
    build_parent_strategy,
    build_student_strategy,
    infer_school_stage,
    normalize_student_profile,
)


class DummyResponse:
    def __init__(self, payload: dict, ok: bool = True, status_code: int = 200):
        self._payload = payload
        self.ok = ok
        self.status_code = status_code
        self.content = b"{}"
        self.headers = {"Content-Type": "application/json"}

    def json(self) -> dict:
        return self._payload


def test_infer_school_stage_from_age_and_grade() -> None:
    assert infer_school_stage(9, "") == "primary"
    assert infer_school_stage(None, "初二") == "junior"
    assert infer_school_stage(17, "") == "senior"


def test_build_student_strategy_respects_age_and_risk() -> None:
    profile = normalize_student_profile(
        {
            "user_id": "student_1001",
            "name": "小明",
            "age": 10,
            "grade": "小学四年级",
        }
    )
    strategy = build_student_strategy(
        profile,
        recent_checkins=[{"emotion": 2, "sleep": 3, "study": 2, "social": 3}],
        latest_report={"riskLevel": 3},
    )
    assert strategy["role"] == "student"
    assert strategy["tone"] == "gentle_playful"
    assert strategy["focus"] == "empathy_then_small_steps"


def test_build_parent_strategy_uses_child_context() -> None:
    strategy = build_parent_strategy(
        {"name": "家长A"},
        {"name": "小明", "grade": "初一", "age": 13},
        child_status={"psych": {"metrics": {"emotion": 2.2}}},
        latest_report={"riskLevel": 2},
        unread_alerts=1,
    )
    assert strategy["role"] == "parent"
    assert strategy["focus"] == "coach_parent_support"
    assert strategy["child_context"]["grade"] == "初一"


def test_update_student_profile_route_refreshes_strategy() -> None:
    client = api_gateway.app.test_client()
    response = client.post(
        "/api/student/profile",
        json={
            "user_id": "student_7777",
            "name": "测试学生",
            "gender": "男",
            "age": 11,
            "grade": "小学五年级",
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["profile"]["school_stage"] == "primary"
    assert payload["strategy"]["role"] == "student"


def test_student_chat_route_returns_strategy_metadata() -> None:
    client = api_gateway.app.test_client()
    response = client.post(
        "/api/student/chat",
        json={
            "user_id": "student_8888",
            "message": "我最近有点紧张，考试快到了。",
            "session_id": "student_session_demo",
            "profile": {"name": "小华", "age": 14, "grade": "初二"},
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["session_id"] == "student_session_demo"
    assert payload["strategy"]["role"] == "student"


def test_legacy_api_chat_alias_still_works() -> None:
    client = api_gateway.app.test_client()
    response = client.post(
        "/api/chat",
        json={
            "message": "test",
            "query": "test",
            "n": 2,
            "use_hybrid": False,
        },
    )
    assert response.status_code in (200, 502)


def test_agent_chat_alias_still_works() -> None:
    client = api_gateway.app.test_client()
    response = client.post(
        "/api/agent/chat",
        json={
            "message": "test",
            "query": "test",
            "n": 2,
            "use_hybrid": False,
        },
    )
    assert response.status_code in (200, 502)


def test_admin_routes_registry_available() -> None:
    client = api_gateway.app.test_client()
    response = client.get("/api/admin/routes")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["count"] >= 1
    assert any(route["path"] == "/api/chat" for route in payload["routes"])


def test_health_endpoint_includes_request_id() -> None:
    client = api_gateway.app.test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")
    payload = response.get_json()
    assert payload["success"] is True
    assert "config" in payload


def test_admin_model_config_route_reads_and_updates(monkeypatch) -> None:
    monkeypatch.setattr(
        api_gateway.requests,
        "get",
        lambda *args, **kwargs: DummyResponse(
            {
                "ok": True,
                "config": {
                    "provider": "qwen",
                    "chat_model": "qwen-plus",
                    "rag_model": "qwen-max",
                    "embedding_model": "text-embedding-v3",
                    "fallback_embedding_model": "text-embedding-v2",
                },
            }
        ),
    )
    monkeypatch.setattr(
        api_gateway.requests,
        "post",
        lambda *args, **kwargs: DummyResponse(
            {
                "ok": True,
                "config": {
                    "provider": "qwen",
                    "chat_model": "qwen-max",
                    "rag_model": "qwen-max",
                    "embedding_model": "text-embedding-v3",
                    "fallback_embedding_model": "text-embedding-v2",
                },
            }
        ),
    )

    client = api_gateway.app.test_client()
    get_resp = client.get("/api/admin/model-config")
    assert get_resp.status_code == 200
    assert get_resp.get_json()["config"]["chat_model"] == "qwen-plus"

    post_resp = client.post(
        "/api/admin/model-config",
        json={"chat_model": "qwen-max", "rag_model": "qwen-max"},
    )
    assert post_resp.status_code == 200
    assert post_resp.get_json()["config"]["chat_model"] == "qwen-max"

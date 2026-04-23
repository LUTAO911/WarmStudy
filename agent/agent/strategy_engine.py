"""
WarmStudy agent strategy engine.

This module centralizes persona and communication strategy decisions so the
gateway, chat APIs, and future admin analytics can share the same logic.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def infer_school_stage(age: Any = None, grade: str | None = None) -> str:
    grade_text = (grade or "").strip()
    normalized = grade_text.lower()

    if "小学" in grade_text or grade_text.startswith("小"):
        return "primary"
    if "初" in grade_text:
        return "junior"
    if "高" in grade_text:
        return "senior"
    if "大" in grade_text or "college" in normalized or "university" in normalized:
        return "college"

    age_num = _safe_int(age)
    if age_num is None:
        return "unknown"
    if age_num <= 12:
        return "primary"
    if age_num <= 15:
        return "junior"
    if age_num <= 18:
        return "senior"
    return "college"


def normalize_student_profile(profile: dict[str, Any] | None) -> dict[str, Any]:
    source = deepcopy(profile or {})
    age_num = _safe_int(source.get("age"))
    grade = (source.get("grade") or "").strip()
    normalized = {
        "user_id": source.get("user_id", ""),
        "name": source.get("name", ""),
        "gender": source.get("gender", ""),
        "age": age_num,
        "grade": grade,
        "phone": source.get("phone", ""),
        "role": source.get("role", "student"),
        "school_stage": infer_school_stage(age_num, grade),
    }
    return normalized


def build_student_strategy(
    profile: dict[str, Any] | None,
    *,
    recent_checkins: list[dict[str, Any]] | None = None,
    latest_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    student = normalize_student_profile(profile)
    checkins = recent_checkins or []
    metrics = {
        "emotion": 3.0,
        "sleep": 3.0,
        "study": 3.0,
        "social": 3.0,
    }
    if checkins:
        for key in metrics:
            values = [float(item.get(key, 3) or 3) for item in checkins]
            metrics[key] = round(sum(values) / len(values), 1)

    risk_level = int((latest_report or {}).get("riskLevel", 0) or 0)
    stage = student["school_stage"]
    age_num = student["age"]

    if stage == "primary":
        tone = "gentle_playful"
        vocabulary = "simple_concrete"
        sentence_style = "short"
        response_length = "short"
    elif stage == "junior":
        tone = "warm_respectful"
        vocabulary = "plain_supportive"
        sentence_style = "medium"
        response_length = "medium"
    elif stage == "senior":
        tone = "calm_respectful"
        vocabulary = "mature_supportive"
        sentence_style = "medium"
        response_length = "medium"
    else:
        tone = "warm_respectful"
        vocabulary = "plain_supportive"
        sentence_style = "medium"
        response_length = "medium"

    if risk_level >= 4 or metrics["emotion"] <= 1.8:
        focus = "stabilize_emotion_first"
        directness = "very_gentle"
    elif risk_level >= 2 or metrics["emotion"] <= 2.4:
        focus = "empathy_then_small_steps"
        directness = "gentle"
    elif metrics["study"] <= 2.4:
        focus = "reduce_pressure_and_restore_routine"
        directness = "gentle"
    else:
        focus = "daily_support_and_reflection"
        directness = "balanced"

    if age_num is not None and age_num <= 10:
        examples = "life_like_examples"
    elif age_num is not None and age_num >= 16:
        examples = "respect_autonomy"
    else:
        examples = "school_life_examples"

    summary = (
        f"student:{student['school_stage']} age={student['age'] or 'unknown'} "
        f"grade={student['grade'] or 'unknown'} risk={risk_level} "
        f"focus={focus} tone={tone}"
    )

    return {
        "role": "student",
        "tone": tone,
        "vocabulary": vocabulary,
        "sentence_style": sentence_style,
        "response_length": response_length,
        "directness": directness,
        "focus": focus,
        "examples": examples,
        "metrics": metrics,
        "risk_level": risk_level,
        "summary": summary,
        "guardrails": [
            "avoid_preaching",
            "avoid_excessive_pressure",
            "validate_feelings_first",
        ],
    }


def build_parent_strategy(
    parent_profile: dict[str, Any] | None,
    child_profile: dict[str, Any] | None,
    *,
    child_status: dict[str, Any] | None = None,
    latest_report: dict[str, Any] | None = None,
    unread_alerts: int = 0,
) -> dict[str, Any]:
    parent = deepcopy(parent_profile or {})
    child = normalize_student_profile(child_profile or {})
    risk_level = int((latest_report or {}).get("riskLevel", 0) or 0)
    metrics = ((child_status or {}).get("psych") or {}).get("metrics", {})

    if risk_level >= 4 or unread_alerts >= 2:
        focus = "stabilize_family_response"
        directness = "clear_and_structured"
    elif risk_level >= 2 or float(metrics.get("emotion", 3) or 3) <= 2.4:
        focus = "coach_parent_support"
        directness = "structured"
    else:
        focus = "preventive_guidance"
        directness = "balanced"

    summary = (
        f"parent child_stage={child['school_stage']} child_grade={child['grade'] or 'unknown'} "
        f"risk={risk_level} alerts={unread_alerts} focus={focus}"
    )

    return {
        "role": "parent",
        "tone": "professional_supportive",
        "vocabulary": "clear_actionable",
        "sentence_style": "structured",
        "response_length": "medium",
        "directness": directness,
        "focus": focus,
        "summary": summary,
        "guardrails": [
            "avoid_blaming_child",
            "avoid_alarmism",
            "recommend_observation_and_support",
        ],
        "child_context": {
            "name": child.get("name", ""),
            "age": child.get("age"),
            "grade": child.get("grade", ""),
            "school_stage": child.get("school_stage", "unknown"),
        },
        "parent_name": parent.get("name", ""),
    }


def build_student_system_context(profile: dict[str, Any] | None, strategy: dict[str, Any] | None) -> str:
    student = normalize_student_profile(profile)
    plan = deepcopy(strategy or {})
    return (
        "你是 WarmStudy 的学生心理陪伴智能体。"
        "你的任务是先接住情绪，再给出适龄、温和、具体的回应。\n"
        f"学生资料: 姓名={student.get('name') or '未提供'}，年龄={student.get('age') or '未提供'}，"
        f"年级={student.get('grade') or '未提供'}，学段={student.get('school_stage') or 'unknown'}。\n"
        f"沟通策略: tone={plan.get('tone', 'warm_respectful')}，"
        f"vocabulary={plan.get('vocabulary', 'plain_supportive')}，"
        f"sentence_style={plan.get('sentence_style', 'medium')}，"
        f"focus={plan.get('focus', 'daily_support_and_reflection')}。\n"
        "要求:\n"
        "1. 不要说教，不要居高临下。\n"
        "2. 年龄越小，句子越短、越具体、越少抽象词。\n"
        "3. 如果状态偏低，优先安抚和陪伴，再给一步可执行建议。\n"
        "4. 不要把家长视角的建议直接说给学生。"
    )


def build_parent_system_context(
    parent_profile: dict[str, Any] | None,
    child_profile: dict[str, Any] | None,
    strategy: dict[str, Any] | None,
) -> str:
    parent = deepcopy(parent_profile or {})
    child = normalize_student_profile(child_profile or {})
    plan = deepcopy(strategy or {})
    return (
        "你是 WarmStudy 的家长支持智能体。"
        "你的任务是帮助家长理解孩子状态，并给出稳妥、结构化、可执行的沟通建议。\n"
        f"家长资料: 姓名={parent.get('name') or '未提供'}。\n"
        f"孩子资料: 姓名={child.get('name') or '未提供'}，年龄={child.get('age') or '未提供'}，"
        f"年级={child.get('grade') or '未提供'}，学段={child.get('school_stage') or 'unknown'}。\n"
        f"沟通策略: tone={plan.get('tone', 'professional_supportive')}，"
        f"focus={plan.get('focus', 'preventive_guidance')}，"
        f"directness={plan.get('directness', 'balanced')}。\n"
        "要求:\n"
        "1. 不要责备孩子，也不要制造恐慌。\n"
        "2. 多给家长可操作的话术、观察点和下一步动作。\n"
        "3. 区分孩子年龄阶段，建议要符合学段特点。\n"
        "4. 不要把学生身份的陪伴口吻直接用于家长。"
    )

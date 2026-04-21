"""
Intent routing for WarmStudy.

The router classifies incoming messages into a small set of intent types and
chooses a matching conversation mode. The implementation keeps the public API
stable while simplifying the branching logic and reducing repeated string work.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence


class IntentType(Enum):
    """Supported intent categories."""

    GENERAL_CHAT = "general_chat"
    PSYCHOLOGY_SUPPORT = "psychology"
    EDUCATION = "education"
    KNOWLEDGE_QUERY = "knowledge"
    CRISIS_INTERVENTION = "crisis"


class ConversationMode(Enum):
    """Conversation modes selected by the router."""

    CHAT = "chat"
    PSYCHOLOGY = "psychology"
    EDUCATION = "education"
    CRISIS = "crisis"


@dataclass
class Intent:
    """Router result."""

    primary: IntentType
    confidence: float
    secondary: Optional[IntentType] = None
    mode: ConversationMode = ConversationMode.CHAT
    metadata: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


@dataclass
class RouteContext:
    """Optional context used during routing."""

    message: str
    session_id: str
    user_type: str = "student"
    emotion_state: Optional[Dict[str, Any]] = None
    recent_intents: List[Intent] = field(default_factory=list)


class IntentRouter:
    """Rule-based router for chat, psychology, education, knowledge, and crisis."""

    CRISIS_THRESHOLD = 1.0
    PSYCHOLOGY_ROUTE_THRESHOLD = 0.35
    PSYCHOLOGY_DETECT_THRESHOLD = 0.3
    EDUCATION_ROUTE_THRESHOLD = 0.5
    KNOWLEDGE_ROUTE_THRESHOLD = 0.5

    CRISIS_KEYWORDS: Sequence[str] = (
        "想死",
        "不想活",
        "活不下去",
        "死了",
        "轻生",
        "自杀",
        "自残",
        "割腕",
        "伤害自己",
        "上吊",
        "跳楼",
        "喝药",
        "一了百了",
        "结束生命",
        "活够了",
    )
    PSYCHOLOGY_KEYWORDS: Sequence[str] = (
        "情绪",
        "心情",
        "难过",
        "难受",
        "开心",
        "生气",
        "害怕",
        "焦虑",
        "压力",
        "紧张",
        "压抑",
        "沮丧",
        "失落",
        "失眠",
        "心理",
        "心事",
        "内心",
        "人际关系",
        "亲子关系",
        "考试压力",
        "学习压力",
        "被孤立",
        "被欺负",
        "自卑",
        "不自信",
        "绝望",
        "无助",
    )
    EDUCATION_KEYWORDS: Sequence[str] = (
        "作业",
        "考试",
        "学习",
        "题目",
        "讲解",
        "辅导",
        "数学",
        "语文",
        "英语",
        "物理",
        "化学",
        "生物",
        "历史",
        "地理",
        "学习计划",
        "学习方法",
        "成绩",
        "复习",
        "预习",
    )
    CRISIS_NEGATIONS: Sequence[str] = (
        "不想",
        "不会",
        "没有想",
        "不是想",
        "开个玩笑",
        "说着玩",
        "我没",
        "我不是",
    )
    GENERAL_CHAT_PATTERNS: Sequence[str] = (
        "怎么样",
        "怎么了",
        "好不好",
        "行不行",
        "能不能",
        "天气怎么样",
        "今天怎么样",
        "你好吗",
        "怎么样啊",
    )
    STRONG_KNOWLEDGE_PATTERNS: Sequence[str] = (
        "为什么",
        "什么是",
        "如何",
        "怎样",
        "怎么提高",
        "怎么办",
    )
    KNOWLEDGE_PATTERNS: Sequence[tuple[str, float]] = (
        ("什么是", 0.8),
        ("为什么", 0.7),
        ("如何", 0.7),
        ("怎样", 0.6),
        ("怎么办", 0.6),
        ("怎么", 0.5),
        ("解释", 0.6),
        ("原理", 0.6),
    )

    def __init__(
        self,
        llm_provider: Any = None,
        cache_ttl: int = 60,
        cache_max_size: int = 256,
    ) -> None:
        self.llm = llm_provider
        self._cache: Dict[str, Intent] = {}
        self._cache_ttl = cache_ttl
        self._cache_max_size = cache_max_size

    async def route(
        self,
        message: str,
        context: Optional[RouteContext] = None,
    ) -> Intent:
        """Route one message to the most suitable intent."""

        now = time.time()
        normalized_message = self._normalize_message(message)
        cache_key = self._build_cache_key(normalized_message, context)

        cached_intent = self._get_cached_intent(cache_key, now)
        if cached_intent is not None:
            return cached_intent

        crisis_intent = self._check_crisis(normalized_message, now)
        if crisis_intent is not None:
            return self._store_and_return(cache_key, crisis_intent, now)

        if any(pattern in normalized_message for pattern in self.STRONG_KNOWLEDGE_PATTERNS):
            knowledge_intent = self._check_knowledge(normalized_message, now)
            if knowledge_intent.confidence >= self.KNOWLEDGE_ROUTE_THRESHOLD:
                return self._store_and_return(cache_key, knowledge_intent, now)

        psychology_intent = self._check_psychology(normalized_message, context, now)
        if psychology_intent.confidence > self.PSYCHOLOGY_ROUTE_THRESHOLD:
            return self._store_and_return(cache_key, psychology_intent, now)

        education_intent = self._check_education(normalized_message, now)
        if education_intent.confidence >= self.EDUCATION_ROUTE_THRESHOLD:
            return self._store_and_return(cache_key, education_intent, now)

        knowledge_intent = self._check_knowledge(normalized_message, now)
        if knowledge_intent.confidence >= self.KNOWLEDGE_ROUTE_THRESHOLD:
            return self._store_and_return(cache_key, knowledge_intent, now)

        default_intent = Intent(
            primary=IntentType.GENERAL_CHAT,
            confidence=0.5,
            mode=ConversationMode.CHAT,
            reasoning="默认路由",
        )
        return self._store_and_return(cache_key, default_intent, now)

    def _normalize_message(self, message: str) -> str:
        return (message or "").strip().lower()

    def _build_cache_key(
        self,
        normalized_message: str,
        context: Optional[RouteContext],
    ) -> str:
        user_type = context.user_type if context else "student"
        emotion_state = context.emotion_state if context else None
        emotion_intensity = 0.0
        if emotion_state:
            raw_intensity = emotion_state.get("intensity", 0.0)
            try:
                emotion_intensity = float(raw_intensity)
            except (TypeError, ValueError):
                emotion_intensity = 0.0
        emotion_bucket = "high" if emotion_intensity > 0.7 else "normal"
        payload = f"{normalized_message}|{user_type}|{emotion_bucket}"
        return hashlib.md5(payload.encode("utf-8")).hexdigest()[:16]

    def _get_cached_intent(self, cache_key: str, now: float) -> Optional[Intent]:
        cached = self._cache.get(cache_key)
        if cached is None:
            return None

        cached_at = float(cached.metadata.get("cached_at", 0.0))
        if now - cached_at >= self._cache_ttl:
            self._cache.pop(cache_key, None)
            return None

        return cached

    def _store_and_return(self, cache_key: str, intent: Intent, now: float) -> Intent:
        intent.metadata = {**intent.metadata, "cached_at": now}
        if len(self._cache) >= self._cache_max_size and cache_key not in self._cache:
            oldest_key = next(iter(self._cache))
            self._cache.pop(oldest_key, None)
        self._cache[cache_key] = intent
        return intent

    def _check_crisis(self, normalized_message: str, now: float) -> Optional[Intent]:
        for keyword in self.CRISIS_KEYWORDS:
            if keyword not in normalized_message:
                continue

            keyword_index = normalized_message.find(keyword)
            if self._has_crisis_negation(normalized_message, keyword_index):
                continue

            return Intent(
                primary=IntentType.CRISIS_INTERVENTION,
                confidence=self.CRISIS_THRESHOLD,
                mode=ConversationMode.CRISIS,
                metadata={"keyword": keyword, "cached_at": now},
                reasoning=f"危机关键词检测: {keyword}",
            )

        return None

    def _has_crisis_negation(self, normalized_message: str, keyword_index: int) -> bool:
        for negation in self.CRISIS_NEGATIONS:
            check_start = max(0, keyword_index - len(negation))
            check_end = keyword_index + 1
            if negation in normalized_message[check_start:check_end]:
                return True
        return False

    def _check_psychology(
        self,
        normalized_message: str,
        context: Optional[RouteContext],
        now: float,
    ) -> Intent:
        keyword_matches = self._match_keywords(normalized_message, self.PSYCHOLOGY_KEYWORDS)
        keyword_confidence = min(len(keyword_matches) / 1.5, 0.9)
        emotion_boost = self._psychology_emotion_boost(context)
        confidence = min(keyword_confidence + emotion_boost, 1.0)

        if confidence > self.PSYCHOLOGY_DETECT_THRESHOLD:
            return Intent(
                primary=IntentType.PSYCHOLOGY_SUPPORT,
                confidence=confidence,
                secondary=IntentType.GENERAL_CHAT,
                mode=ConversationMode.PSYCHOLOGY,
                metadata={"keywords": keyword_matches, "cached_at": now},
                reasoning=f"心理学关键词匹配: {len(keyword_matches)}个",
            )

        return Intent(
            primary=IntentType.GENERAL_CHAT,
            confidence=0.3,
            reasoning="无强心理学信号",
        )

    def _psychology_emotion_boost(self, context: Optional[RouteContext]) -> float:
        if not context or not context.emotion_state:
            return 0.0

        raw_intensity = context.emotion_state.get("intensity", 0.0)
        try:
            emotion_intensity = float(raw_intensity)
        except (TypeError, ValueError):
            return 0.0

        return 0.15 if emotion_intensity > 0.7 else 0.0

    def _check_education(self, normalized_message: str, now: float) -> Intent:
        keyword_matches = self._match_keywords(normalized_message, self.EDUCATION_KEYWORDS)
        keyword_count = len(keyword_matches)

        if keyword_count >= 1:
            return Intent(
                primary=IntentType.EDUCATION,
                confidence=min(keyword_count / 2, 0.9),
                mode=ConversationMode.EDUCATION,
                metadata={"keywords": keyword_matches, "cached_at": now},
                reasoning=f"教育关键词匹配: {keyword_count}个",
            )

        return Intent(
            primary=IntentType.EDUCATION,
            confidence=0.3,
            mode=ConversationMode.EDUCATION,
            metadata={"cached_at": now},
            reasoning="少量教育关键词",
        )

    def _check_knowledge(self, normalized_message: str, now: float) -> Intent:
        if any(pattern in normalized_message for pattern in self.GENERAL_CHAT_PATTERNS):
            return Intent(
                primary=IntentType.KNOWLEDGE_QUERY,
                confidence=0.2,
                reasoning="通用聊天模式",
            )

        for pattern, confidence in self.KNOWLEDGE_PATTERNS:
            if pattern in normalized_message:
                return Intent(
                    primary=IntentType.KNOWLEDGE_QUERY,
                    confidence=confidence,
                    mode=ConversationMode.CHAT,
                    metadata={"pattern": pattern, "cached_at": now},
                    reasoning=f"知识查询模式: {pattern}",
                )

        return Intent(
            primary=IntentType.KNOWLEDGE_QUERY,
            confidence=0.2,
            reasoning="无明确知识查询信号",
        )

    def _match_keywords(
        self,
        normalized_message: str,
        keywords: Sequence[str],
    ) -> List[str]:
        return [keyword for keyword in keywords if keyword in normalized_message]

    def clear_cache(self) -> None:
        """Clear the in-memory router cache."""

        self._cache.clear()

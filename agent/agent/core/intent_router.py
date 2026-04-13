"""
Intent Router - 意图识别与路由
智能判断用户意图，决定使用什么处理模式
"""
import time
import hashlib
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    pass

class IntentType(Enum):
    """意图类型"""
    GENERAL_CHAT = "general_chat"
    PSYCHOLOGY_SUPPORT = "psychology"
    EDUCATION = "education"
    KNOWLEDGE_QUERY = "knowledge"
    CRISIS_INTERVENTION = "crisis"

class ConversationMode(Enum):
    """对话模式"""
    CHAT = "chat"
    PSYCHOLOGY = "psychology"
    EDUCATION = "education"
    CRISIS = "crisis"

@dataclass
class Intent:
    """意图识别结果"""
    primary: IntentType
    confidence: float
    secondary: Optional[IntentType] = None
    mode: ConversationMode = ConversationMode.CHAT
    metadata: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""

@dataclass
class RouteContext:
    """路由上下文"""
    message: str
    session_id: str
    user_type: str = "student"
    emotion_state: Optional[Dict[str, Any]] = None
    recent_intents: List[Intent] = field(default_factory=list)

class IntentRouter:
    """
    意图路由器
    
    判断逻辑：
    1. 危机关键词检测 → 最高优先级 → CRISIS
    2. 心理学关键词 + 情绪检测 → PSYCHOLOGY
    3. 教育相关关键词 → EDUCATION
    4. 知识查询类 → KNOWLEDGE_QUERY
    5. 其他 → GENERAL_CHAT
    """

    # 危机关键词（最高优先级）
    CRISIS_KEYWORDS = [
        "想死", "不想活", "活不下去", "死了", "輕生", "自殺",
        "自残", "割腕", "伤害自己", "上吊", "跳楼", "喝药",
        "一了百了", "结束生命", "活腻了",
    ]

    # 心理学关键词
    PSYCHOLOGY_KEYWORDS = [
        "情绪", "心情", "难过", "开心", "生气", "害怕", "焦虑",
        "压力", "紧张", "压抑", "沮喪", "失落", "失眠", "难受",
        "心理", "心事", "内心", "人际关系", "亲子关系",
        "考试压力", "学习压力", "被孤立", "被欺负",
        "自卑", "不自信", "绝望", "無助",
    ]

    # 教育关键词
    EDUCATION_KEYWORDS = [
        "作业", "考试", "学习", "题目", "讲解", "辅导",
        "数学", "语文", "英语", "物理", "化学", "生物", "历史", "地理",
        "学习计划", "学习方法", "成绩", "复习", "预习",
        "做作业", "题",
    ]

    # 知识查询关键词
    KNOWLEDGE_KEYWORDS = [
        "什么是", "概念", "定义", "解释", "原理",
        "为什么", "原因", "如何", "怎样", "怎么办",
    ]

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self._cache: Dict[str, Intent] = {}
        self._cache_ttl = 60

    async def route(
        self,
        message: str,
        context: Optional[RouteContext] = None
    ) -> Intent:
        """
        智能路由判断
        
        Args:
            message: 用户消息
            context: 路由上下文（可选）
            
        Returns:
            Intent: 意图识别结果
        """
        # 1. 检查缓存
        cache_key = hashlib.md5(message.encode()).hexdigest()[:16]
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            cached_time = cached.metadata.get("cached_at", 0)
            if time.time() - cached_time < self._cache_ttl:
                return cached

        # 2. 危机检测（最高优先级）
        crisis_intent = self._check_crisis(message)
        if crisis_intent:
            return crisis_intent

        # 3. 心理学检测
        psych_intent = self._check_psychology(message, context)
        if psych_intent.confidence > 0.4:
            self._cache[cache_key] = psych_intent
            return psych_intent

        # 4. 教育检测
        edu_intent = self._check_education(message)
        if edu_intent.confidence > 0.5:
            self._cache[cache_key] = edu_intent
            return edu_intent

        # 5. 知识查询检测
        knowledge_intent = self._check_knowledge(message)
        if knowledge_intent.confidence > 0.5:
            self._cache[cache_key] = knowledge_intent
            return knowledge_intent

        # 6. 默认普通聊天
        default_intent = Intent(
            primary=IntentType.GENERAL_CHAT,
            confidence=0.5,
            mode=ConversationMode.CHAT,
            reasoning="默认路由"
        )
        self._cache[cache_key] = default_intent
        return default_intent

    def _check_crisis(self, message: str) -> Optional[Intent]:
        """危机检测"""
        msg_lower = message.lower()

        # 否定词
        negations = ["不想", "不会", "没有想", "不是想", "开个玩笑", "说着玩"]

        for kw in self.CRISIS_KEYWORDS:
            if kw in msg_lower:
                # 检查是否有否定词
                idx = msg_lower.find(kw)
                prefix = msg_lower[max(0, idx - 20):idx + 1]
                if any(neg in prefix for neg in negations):
                    continue
                return Intent(
                    primary=IntentType.CRISIS_INTERVENTION,
                    confidence=1.0,
                    mode=ConversationMode.CRISIS,
                    metadata={"keyword": kw, "cached_at": time.time()},
                    reasoning=f"危机关键词检测: {kw}"
                )
        return None

    def _check_psychology(
        self,
        message: str,
        context: Optional[RouteContext]
    ) -> Intent:
        """心理学检测"""
        msg_lower = message.lower()

        # 关键词匹配
        keyword_matches = [kw for kw in self.PSYCHOLOGY_KEYWORDS if kw in msg_lower]
        keyword_count = len(keyword_matches)
        keyword_confidence = min(keyword_count / 2, 0.9)

        # 如果消息是知识查询类型（含"如何"/"为什么"/"什么是"），降低心理学置信度
        knowledge_query_patterns = ["如何", "为什么", "什么是"]
        if any(kp in msg_lower for kp in knowledge_query_patterns):
            keyword_confidence *= 0.4

        # 情绪强度检测（如果有context）
        emotion_boost = 0.0
        if context and context.emotion_state:
            emotion_intensity = context.emotion_state.get("intensity", 0)
            if emotion_intensity >= 0.7:
                emotion_boost = 0.15

        confidence = min(keyword_confidence + emotion_boost, 1.0)

        if confidence > 0.4:
            return Intent(
                primary=IntentType.PSYCHOLOGY_SUPPORT,
                confidence=confidence,
                secondary=IntentType.GENERAL_CHAT,
                mode=ConversationMode.PSYCHOLOGY,
                metadata={
                    "keywords": keyword_matches,
                    "cached_at": time.time()
                },
                reasoning=f"心理学关键词匹配: {keyword_count}个"
            )

        return Intent(
            primary=IntentType.GENERAL_CHAT,
            confidence=0.3,
            reasoning="无强心理学信号"
        )

    def _check_education(self, message: str) -> Intent:
        """教育检测"""
        msg_lower = message.lower()

        keyword_matches = [kw for kw in self.EDUCATION_KEYWORDS if kw in msg_lower]
        keyword_count = len(keyword_matches)

        if keyword_count >= 1:
            confidence = min(keyword_count * 0.6, 0.9)

            # 如果消息是知识查询类型（含问题词），降低教育置信度
            knowledge_query_words = ["如何", "为什么", "什么是"]
            has_knowledge_prefix = any(kp in msg_lower for kp in knowledge_query_words)
            # "怎么"作为疑问词也降低教育置信度，但"怎么做"（解题）除外
            if not has_knowledge_prefix and "怎么" in msg_lower and "怎么做" not in msg_lower:
                has_knowledge_prefix = True
            if has_knowledge_prefix:
                confidence *= 0.4

            return Intent(
                primary=IntentType.EDUCATION,
                confidence=confidence,
                mode=ConversationMode.EDUCATION,
                metadata={"keywords": keyword_matches, "cached_at": time.time()},
                reasoning=f"教育关键词匹配: {keyword_count}个"
            )

        return Intent(
            primary=IntentType.EDUCATION,
            confidence=0.3,
            mode=ConversationMode.EDUCATION,
            metadata={"cached_at": time.time()},
            reasoning="少量教育关键词"
        )

    def _check_knowledge(self, message: str) -> Intent:
        """知识查询检测"""
        msg_lower = message.lower()

        # 检查知识查询模式
        knowledge_patterns = [
            ("什么是", 0.8),
            ("为什么", 0.7),
            ("如何", 0.7),
            ("怎么", 0.6),
            ("解释", 0.6),
            ("原理", 0.6),
        ]

        for pattern, base_conf in knowledge_patterns:
            if pattern in msg_lower:
                # 排除"怎么样"这类口语化用法，以及"怎么做"（属于教育解题范畴）
                if pattern == "怎么" and ("怎么样" in msg_lower or "怎么做" in msg_lower):
                    continue
                return Intent(
                    primary=IntentType.KNOWLEDGE_QUERY,
                    confidence=base_conf,
                    mode=ConversationMode.CHAT,
                    metadata={"pattern": pattern, "cached_at": time.time()},
                    reasoning=f"知识查询模式: {pattern}"
                )

        return Intent(
            primary=IntentType.KNOWLEDGE_QUERY,
            confidence=0.2,
            reasoning="无明确知识查询信号"
        )

    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()

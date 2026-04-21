"""
Psychology Module - 统一心理学模块
整合情绪识别、危机检测、共情生成、人格模拟
版本: v5.0
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    pass

# ========== 数据模型 ==========

class EmotionLevel(Enum):
    """情绪等级"""
    NEUTRAL = "neutral"
    MILD = "mild"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class CrisisLevel(Enum):
    """危机等级"""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EmotionInfo:
    """情绪信息"""
    type: str              # happy/sad/anxious/angry/fearful/neutral
    level: EmotionLevel
    intensity: float        # 0-1
    keywords: List[str]     # 触发关键词
    suggestion: str         # 建议的回应方式
    icon: str = ""         # 情绪图标

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "level": self.level.value,
            "intensity": self.intensity,
            "keywords": self.keywords,
            "suggestion": self.suggestion,
            "icon": self.icon,
        }


@dataclass
class CrisisInfo:
    """危机信息"""
    level: CrisisLevel
    signals: List[Dict[str, Any]]
    message: str
    action: str
    hotlines: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "signals": self.signals,
            "message": self.message,
            "action": self.action,
            "hotlines": self.hotlines,
        }


@dataclass
class PersonalityProfile:
    """人格特征配置"""
    warmth: float = 0.8           # 温暖程度 0-1
    empathy: float = 0.9         # 共情能力 0-1
    positivity: float = 0.7       # 积极倾向 0-1
    formality: float = 0.3        # 正式程度 0-1
    verbosity: float = 0.5       # 冗长程度 0-1

    use_emoji: bool = True
    use_informal_speech: bool = True
    max_response_length: int = 200


@dataclass
class PsychologyResult:
    """心理学处理结果"""
    emotion: Optional[EmotionInfo] = None
    crisis: Optional[CrisisInfo] = None
    knowledge: List[Dict[str, Any]] = field(default_factory=list)
    empathic_response: Optional[str] = None
    personality_adjusted: Optional[str] = None
    recommended_action: str = "continue"


# ========== 心理学模块 ==========

class PsychologyModule:
    """
    统一心理学模块

    整合功能：
    1. 情绪识别（EmotionDetector）
    2. 危机检测（CrisisDetector）
    3. 共情生成（EmpathicGenerator）
    4. 人格模拟（基于PersonalityProfile）
    """

    def __init__(self, personality: Optional[PersonalityProfile] = None):
        self._emotion_detector = None
        self._crisis_detector = None
        self._empathic_generator = None

        # 人格配置
        self._personality = personality or PersonalityProfile()

        # 情绪标签映射
        self._emotion_labels = {
            "happy": {"label": "开心", "icon": "😊"},
            "sad": {"label": "难过", "icon": "😢"},
            "anxious": {"label": "焦虑", "icon": "😰"},
            "angry": {"label": "生气", "icon": "😠"},
            "fearful": {"label": "害怕", "icon": "😨"},
            "surprised": {"label": "惊讶", "icon": "😲"},
            "ashamed": {"label": "羞耻", "icon": "😳"},
            "hopeful": {"label": "有希望", "icon": "🌟"},
            "hopeless": {"label": "绝望", "icon": "😔"},
            "neutral": {"label": "平静", "icon": "😌"},
        }

    def _get_emotion_detector(self):
        """懒加载情绪检测器"""
        if self._emotion_detector is None:
            from agent.modules.psychology.emotion import EmotionDetector
            self._emotion_detector = EmotionDetector()
        return self._emotion_detector

    def _get_crisis_detector(self):
        """懒加载危机检测器"""
        if self._crisis_detector is None:
            from agent.modules.psychology.crisis import CrisisDetector
            self._crisis_detector = CrisisDetector()
        return self._crisis_detector

    def _get_empathic_generator(self):
        """懒加载共情生成器"""
        if self._empathic_generator is None:
            from agent.modules.psychology.empathic import EmpathicGenerator
            self._empathic_generator = EmpathicGenerator()
        return self._empathic_generator

    # ========== 情绪识别 ==========

    async def detect_emotion(self, text: str) -> EmotionInfo:
        """
        识别情绪

        Args:
            text: 用户输入

        Returns:
            EmotionInfo: 情绪信息
        """
        detector = self._get_emotion_detector()
        result = detector.detect(text)

        # 转换情绪等级
        intensity = result.intensity
        if intensity <= 0.2:
            level = EmotionLevel.NEUTRAL
        elif intensity <= 0.4:
            level = EmotionLevel.MILD
        elif intensity <= 0.6:
            level = EmotionLevel.MODERATE
        elif intensity <= 0.8:
            level = EmotionLevel.HIGH
        else:
            level = EmotionLevel.EXTREME

        # 获取标签
        label_info = self._emotion_labels.get(
            result.emotion.value,
            self._emotion_labels["neutral"]
        )

        return EmotionInfo(
            type=result.emotion.value,
            level=level,
            intensity=result.intensity,
            keywords=result.keywords,
            suggestion=result.suggestion,
            icon=label_info["icon"]
        )

    # ========== 危机检测 ==========

    async def check_crisis(self, text: str) -> CrisisInfo:
        """
        危机检测

        Args:
            text: 用户输入

        Returns:
            CrisisInfo: 危机信息
        """
        detector = self._get_crisis_detector()
        result = detector.check(text)

        # 转换危机等级
        level_map = {
            "safe": CrisisLevel.SAFE,
            "low": CrisisLevel.LOW,
            "medium": CrisisLevel.MEDIUM,
            "high": CrisisLevel.HIGH,
            "critical": CrisisLevel.CRITICAL,
        }
        level = level_map.get(result.level.value, CrisisLevel.SAFE)

        return CrisisInfo(
            level=level,
            signals=result.signals,
            message=result.message,
            action=result.action,
            hotlines=result.hotlines
        )

    # ========== 共情回复生成 ==========

    async def generate_empathic_response(
        self,
        user_input: str,
        emotion: EmotionInfo,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成共情回复

        Args:
            user_input: 用户输入
            emotion: 情绪信息
            context: 额外上下文

        Returns:
            str: 共情回复
        """
        generator = self._get_empathic_generator()

        try:
            response = generator.generate(
                user_input=user_input,
                emotion_type=emotion.type,
                intensity=emotion.intensity
            )
        except Exception:
            # 兜底回复
            response = self._generate_fallback_response(emotion)

        # 根据人格特征调整
        adjusted = self._personality.adapt_response(response, emotion)

        return adjusted

    def _generate_fallback_response(self, emotion: EmotionInfo) -> str:
        """生成兜底共情回复"""
        emotion_responses = {
            "sad": "我听到你说的话，能感受到你现在很难过...",
            "anxious": "我能理解你现在的焦虑和压力，这种感觉确实不好受...",
            "angry": "听起来你很生气，我理解你的感受...",
            "happy": "真为你高兴！有什么好事发生了吗？",
            "fearful": "我能感觉到你有些害怕，别担心，我在这里...",
            "hopeless": "我知道你现在可能感到很绝望，但请相信一切都会好起来的...",
            "neutral": "嗯，我在认真听你说话...",
        }
        return emotion_responses.get(emotion.type, "我在这里认真倾听你...")

    # ========== 综合处理 ==========

    async def process(
        self,
        user_input: str,
        user_type: str = "student",
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PsychologyResult:
        """
        综合心理处理

        Args:
            user_input: 用户输入
            user_type: 用户类型
            user_id: 用户ID
            context: 额外上下文

        Returns:
            PsychologyResult: 综合处理结果
        """
        result = PsychologyResult()

        # 1. 情绪识别
        result.emotion = await self.detect_emotion(user_input)

        # 2. 危机检测（优先）
        result.crisis = await self.check_crisis(user_input)

        # 如果是危机情况，直接返回危机响应
        if result.crisis.level in (CrisisLevel.HIGH, CrisisLevel.CRITICAL):
            crisis_response = self._get_crisis_response(result.crisis)
            result.empathic_response = crisis_response
            result.personality_adjusted = crisis_response
            result.recommended_action = "crisis_intervention"
            return result

        # 3. 检索相关心理知识（如果有context）
        if context and "rag_results" in context:
            result.knowledge = context["rag_results"]

        # 4. 生成共情回复
        if result.emotion:
            result.empathic_response = await self.generate_empathic_response(
                user_input, result.emotion, context
            )
            result.personality_adjusted = result.empathic_response

        # 5. 确定推荐行动
        result.recommended_action = self._determine_action(result)

        return result

    def _get_crisis_response(self, crisis: CrisisInfo) -> str:
        """获取危机响应"""
        crisis_responses = {
            CrisisLevel.LOW: """谢谢你愿意告诉我这些。我在这里认真倾听你的感受。

如果你想继续说下去，我很愿意听。记住，无论发生什么，你都不是一个人。💙""",

            CrisisLevel.MEDIUM: """听到你说这些，我有些担心你。

你能告诉我更多吗？发生了什么事情让你有这样的感受？
记住，向信任的人寻求帮助是很勇敢的表现。🌸""",

            CrisisLevel.HIGH: """我听到你说的话，让我非常担心。

我想让你知道，无论你现在感到多么绝望，总有人关心你，你并不孤单。
你愿意告诉我更多吗？或者我可以告诉你一些可以寻求帮助的地方吗？💙""",

            CrisisLevel.CRITICAL: """我想认真告诉你：你很重要，你的生命有意义。

我知道你现在可能感到很痛苦，但请相信，总有办法度过难关。
你能不能告诉我你现在在哪里？我们一起想办法。

全国心理援助热线：400-161-9995

你也可以告诉我你所在的地区，我帮你找到更近的帮助资源。💙""",
        }

        return crisis_responses.get(crisis.level, "")

    def _determine_action(self, result: PsychologyResult) -> str:
        """确定推荐行动"""
        if result.crisis and result.crisis.level != CrisisLevel.SAFE:
            return "crisis_intervention"

        if result.emotion:
            intensity = result.emotion.intensity

            if intensity > 0.8:
                return "urgent_support"
            elif intensity > 0.6:
                return "focused_support"
            elif result.emotion.type in ["sad", "hopeless"]:
                return "comfort_and_encourage"
            elif result.emotion.type == "anxious":
                return "calm_and_guide"

        return "continue"


# ========== PersonalityProfile 方法扩展 ==========

def adapt_response(self, base_response: str, emotion: EmotionInfo) -> str:
    """
    根据人格特征调整回复

    Args:
        base_response: 基础回复
        emotion: 当前情绪

    Returns:
        str: 调整后的回复
    """
    response = base_response

    # 根据情绪强度调整长度
    if emotion.intensity > 0.8:
        if len(response) > self.max_response_length:
            response = response[:self.max_response_length] + "..."

    # 根据温暖程度调整语气
    if self.warmth > 0.7:
        if not any(marker in response for marker in ["🌸", "💙", "我", "你"]):
            response = f"我理解你的感受... {response}"

    # 根据积极倾向调整
    if self.positivity > 0.6:
        if emotion.type in ["sad", "anxious", "hopeless"]:
            import random
            positive_additions = ["相信你", "会好起来的", "你很棒"]
            response += f" {random.choice(positive_additions)}"

    # 添加emoji
    if self.use_emoji and emotion.icon and emotion.icon not in response:
        response = f"{emotion.icon} {response}"

    return response


# 绑定方法到类
PersonalityProfile.adapt_response = adapt_response

"""
Emotion Detector - 情绪识别模块
基于词典+规则的青少年情绪识别
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class EmotionType(Enum):
    """情绪类型"""
    HAPPY = "happy"           # 开心
    SAD = "sad"               # 难过
    ANXIOUS = "anxious"       # 焦虑
    ANGRY = "angry"           # 生气
    FEARFUL = "fearful"        # 害怕
    SURPRISED = "surprised"    # 惊讶
    ASHAMED = "ashamed"        # 羞耻
    HOPEFUL = "hopeful"        # 有希望
    HOPELESS = "hopeless"      # 绝望
    NEUTRAL = "neutral"        # 中性


@dataclass
class EmotionResult:
    """情绪识别结果"""
    emotion: EmotionType
    intensity: float  # 0.0 - 1.0
    keywords: List[str]
    suggestion: str  # 建议的回应方式


# 情绪词典
EMOTION_KEYWORDS = {
    EmotionType.HAPPY: [
        "开心", "高兴", "快乐", "愉快", "喜悦", "兴奋", "激动",
        "太棒了", "太好了", "好开心", "真高兴", "快乐", "欢乐",
        "棒", "优秀", "完美", "满分", "成就感"
    ],
    EmotionType.SAD: [
        "难过", "伤心", "痛苦", "沮丧", "失落", "郁闷", "压抑",
        "想哭", "哭了", "眼泪", "悲伤", "绝望", "无助",
        "心碎", "痛苦", "低落的", "消沉的"
    ],
    EmotionType.ANXIOUS: [
        "焦虑", "紧张", "不安", "担心", "害怕", "恐慌",
        "睡不着", "失眠", "心慌", "忐忑", "顾虑",
        "压力", "喘不过气", "压迫感", "恐惧"
    ],
    EmotionType.ANGRY: [
        "生气", "愤怒", "气愤", "恼火", "烦躁", "恼怒",
        "讨厌", "恨", "讨厌", "不爽", "火大",
        "委屈", "不公平", "凭什么"
    ],
    EmotionType.FEARFUL: [
        "害怕", "恐惧", "担心", "顾虑", "不敢",
        "发抖", "颤抖", "惊慌", "惊恐",
        "忧虑", "忐忑不安"
    ],
    EmotionType.SURPRISED: [
        "惊讶", "吃惊", "意外", "震惊", "没想到",
        "居然", "竟然", "吓了一跳"
    ],
    EmotionType.ASHAMED: [
        "丢人", "丢脸", "惭愧", "内疚", "自责",
        "不好意思", "害羞", "脸红", "尴尬"
    ],
    EmotionType.HOPEFUL: [
        "希望", "期待", "憧憬", "有信心", "有希望",
        "加油", "努力", "会好的", "会变好的"
    ],
    EmotionType.HOPELESS: [
        "没希望", "绝望", "放弃", "算了", "无所谓",
        "无所谓了", "没意义", "活着没意思"
    ],
}

# 强度修饰词
INTENSITY_MODIFIERS = {
    "非常": 0.2,
    "特别": 0.2,
    "极其": 0.3,
    "十分": 0.15,
    "太": 0.15,
    "真的好": 0.2,
    "特别": 0.2,
    "有点": -0.1,
    "有些": -0.1,
    "稍微": -0.1,
    "一点": -0.1,
    "有点点": -0.15,
}


class EmotionDetector:
    """情绪识别器"""
    
    def __init__(self):
        self.emotion_keywords = EMOTION_KEYWORDS
        self.intensity_modifiers = INTENSITY_MODIFIERS
        
    def detect(self, text: str) -> EmotionResult:
        """
        识别文本中的情绪
        
        Args:
            text: 用户输入文本
            
        Returns:
            EmotionResult: 情绪识别结果
        """
        text = text.lower()
        
        # 统计各情绪关键词出现次数
        emotion_scores: Dict[EmotionType, float] = {}
        
        for emotion_type, keywords in self.emotion_keywords.items():
            score = 0.0
            found_keywords = []
            
            for keyword in keywords:
                if keyword.lower() in text:
                    score += 1.0
                    found_keywords.append(keyword)
            
            if score > 0:
                # 计算基础强度
                base_intensity = min(score / 3.0, 1.0)
                
                # 应用修饰词调整
                modifier = 0.0
                for modifier_word, adjustment in self.intensity_modifiers.items():
                    if modifier_word in text:
                        modifier += adjustment
                
                final_intensity = max(0.1, min(base_intensity + modifier, 1.0))
                emotion_scores[emotion_type] = final_intensity
        
        if not emotion_scores:
            return EmotionResult(
                emotion=EmotionType.NEUTRAL,
                intensity=0.5,
                keywords=[],
                suggestion="natural"
            )
        
        # 选择得分最高的情绪
        dominant_emotion = max(emotion_scores.items(), key=lambda x: x[1])
        emotion_type, intensity = dominant_emotion
        
        # 获取该情绪的关键词
        found = []
        for keyword in self.emotion_keywords[emotion_type]:
            if keyword.lower() in text.lower():
                found.append(keyword)
        
        return EmotionResult(
            emotion=emotion_type,
            intensity=intensity,
            keywords=found,
            suggestion=self._get_suggestion(emotion_type, intensity)
        )
    
    def _get_suggestion(self, emotion: EmotionType, intensity: float) -> str:
        """根据情绪类型和强度获取建议的回应方式"""
        suggestions = {
            EmotionType.HAPPY: "share_joy",
            EmotionType.SAD: "comfort",
            EmotionType.ANXIOUS: "calm_down",
            EmotionType.ANGRY: "deescalate",
            EmotionType.FEARFUL: "reassure",
            EmotionType.SURPRISED: "acknowledge",
            EmotionType.ASHAMED: "normalize",
            EmotionType.HOPEFUL: "encourage",
            EmotionType.HOPELESS: "intervene",
            EmotionType.NEUTRAL: "natural",
        }
        
        base = suggestions.get(emotion, "natural")
        
        # 高强度调整
        if intensity > 0.7:
            if emotion in [EmotionType.SAD, EmotionType.HOPELESS, EmotionType.ANXIOUS]:
                return "empathetic+"  # 更强烈的共情
            elif emotion == EmotionType.ANGRY:
                return "deescalate+"  # 更强的缓和
                
        return base
    
    def get_emotion_label(self, emotion: EmotionType) -> Dict:
        """获取情绪标签信息"""
        labels = {
            EmotionType.HAPPY: {"label": "开心", "icon": "😊", "color": "#95de64"},
            EmotionType.SAD: {"label": "难过", "icon": "😢", "color": "#597ef7"},
            EmotionType.ANXIOUS: {"label": "焦虑", "icon": "😰", "color": "#ffd666"},
            EmotionType.ANGRY: {"label": "生气", "icon": "😠", "color": "#ff7875"},
            EmotionType.FEARFUL: {"label": "害怕", "icon": "😨", "color": "#b37feb"},
            EmotionType.SURPRISED: {"label": "惊讶", "icon": "😲", "color": "#ffc069"},
            EmotionType.ASHAMED: {"label": "羞耻", "icon": "😳", "color": "#85a9d9"},
            EmotionType.HOPEFUL: {"label": "有希望", "icon": "🌟", "color": "#73d13d"},
            EmotionType.HOPELESS: {"label": "绝望", "icon": "😔", "color": "#97989a"},
            EmotionType.NEUTRAL: {"label": "平静", "icon": "😌", "color": "#bfbfbfs"},
        }
        return labels.get(emotion, labels[EmotionType.NEUTRAL])


# 全局实例
_detector = None

def get_emotion_detector() -> EmotionDetector:
    """获取情绪检测器单例"""
    global _detector
    if _detector is None:
        _detector = EmotionDetector()
    return _detector

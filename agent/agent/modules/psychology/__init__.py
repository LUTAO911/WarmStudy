"""
Psychology Module - 心理支持模块
暖学帮 - 青少年心理关怀AI

核心组件：
- emotion: 情绪识别
- empathic: 共情生成
- crisis: 危机检测
- knowledge: 心理知识库
"""

from .emotion import EmotionDetector
from .empathic import EmpathicGenerator
from .crisis import CrisisDetector
from .knowledge import PsychologyKnowledgeBase

__all__ = [
    "EmotionDetector",
    "EmpathicGenerator",
    "CrisisDetector",
    "PsychologyKnowledgeBase",
]

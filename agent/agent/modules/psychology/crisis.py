"""
Crisis Detector - 危机检测模块
检测自杀倾向、自伤等危机信号
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class CrisisLevel(Enum):
    """危机等级"""
    SAFE = "safe"           # 安全
    LOW = "low"             # 低风险
    MEDIUM = "medium"       # 中风险
    HIGH = "high"           # 高风险
    CRITICAL = "critical"    # 紧急危机


@dataclass
class CrisisResult:
    """危机检测结果"""
    level: CrisisLevel
    signals: List[Dict]
    message: str
    action: str  # 建议的行动
    hotlines: List[str]  # 危机热线


# 危机关键词分类
CRISIS_KEYWORDS = {
    "self_harm": {
        "keywords": [
            "自残", "割腕", "想死", "不想活", "活不下去",
            "死了算了", "死了好", "死了就解脱了",
            "伤害自己", "自己打自己", "撞墙",
            "轻生", "寻死", "活腻了"
        ],
        "severity": "high",
        "category": "自伤倾向"
    },
    "suicide": {
        "keywords": [
            "自杀", "轻生", "跳楼", "上吊", "割腕自杀",
            "喝药", "吃安眠药", "一了百了", "结束生命",
            "不想活了", "活着没意思", "活着太累了",
            "死了一了百了", "死了就轻松了"
        ],
        "severity": "critical",
        "category": "自杀倾向"
    },
    "abuse": {
        "keywords": [
            "被人欺负", "被打了", "被骂", "被侮辱",
            "被嘲笑", "被孤立", "被排挤",
            "校园暴力", "家暴", "虐待"
        ],
        "severity": "medium",
        "category": "遭受伤害"
    },
    "depression": {
        "keywords": [
            "活着没意义", "没意思", "什么都不想做",
            "行尸走肉", "空洞", "麻木",
            "不想见人", "不想说话", "没胃口",
            "失眠", "早醒", "绝望"
        ],
        "severity": "medium",
        "category": "抑郁倾向"
    },
    "bully": {
        "keywords": [
            "被欺负", "被孤立", "被嘲笑", "被排挤",
            "没人喜欢我", "朋友背叛", "被背叛"
        ],
        "severity": "low",
        "category": "人际关系困扰"
    }
}

# 否定词（降低风险）
NEGATION_WORDS = [
    "不想", "不会", "没有想", "不是想",
    "开个玩笑", "说着玩的", "开玩笑",
    "别人", "有人", "如果", "假设"
]

# 危机热线
CRISIS_HOTLINES = [
    "全国心理援助热线：400-161-9995",
    "北京心理危机研究与干预中心：010-82951332",
    "生命热线：400-821-1215",
    "希望24小时热线：400-161-9995",
]


class CrisisDetector:
    """危机检测器"""
    
    def __init__(self):
        self.crisis_keywords = CRISIS_KEYWORDS
        self.negation_words = NEGATION_WORDS
        self.hotlines = CRISIS_HOTLINES
        
    def check(self, text: str) -> CrisisResult:
        """
        检测文本中的危机信号
        
        Args:
            text: 用户输入文本
            
        Returns:
            CrisisResult: 危机检测结果
        """
        text_lower = text.lower()
        detected_signals: List[Dict] = []
        max_severity = "safe"
        
        for category, info in self.crisis_keywords.items():
            for keyword in info["keywords"]:
                if keyword.lower() in text_lower:
                    # 检查是否有否定词
                    is_negated = self._check_negation(text_lower, keyword)
                    
                    if not is_negated:
                        detected_signals.append({
                            "category": category,
                            "keyword": keyword,
                            "severity": info["severity"],
                            "label": info["category"]
                        })
                        
                        # 更新最高风险等级
                        severity_order = ["safe", "low", "medium", "high", "critical"]
                        if severity_order.index(info["severity"]) > severity_order.index(max_severity):
                            max_severity = info["severity"]
        
        # 确定危机等级
        if max_severity == "critical":
            level = CrisisLevel.CRITICAL
            message = "我注意到你提到了结束生命的念头，我想认真告诉你：你很重要，这个世界需要你。"
            action = "immediate_intervention"
        elif max_severity == "high":
            level = CrisisLevel.HIGH
            message = "我听到你说了一些让我担心的话。你愿意多告诉我一些吗？"
            action = "urgent_attention"
        elif max_severity == "medium":
            level = CrisisLevel.MEDIUM
            message = "听起来你现在经历着很困难的事情，我想帮你。"
            action = "increase_concern"
        elif max_severity == "low":
            level = CrisisLevel.LOW
            message = "谢谢你告诉我这些，我在这里支持你。"
            action = "normal_support"
        else:
            level = CrisisLevel.SAFE
            message = ""
            action = "normal_conversation"
        
        return CrisisResult(
            level=level,
            signals=detected_signals,
            message=message,
            action=action,
            hotlines=self.hotlines if level in [CrisisLevel.HIGH, CrisisLevel.CRITICAL] else []
        )
    
    def _check_negation(self, text: str, keyword: str) -> bool:
        """检查关键词是否被否定"""
        # 找到关键词位置
        idx = text.find(keyword.lower())
        if idx == -1:
            return False
        
        # 检查前面50个字符是否有否定词
        start = max(0, idx - 30)
        context = text[start:idx]
        
        for neg_word in self.negation_words:
            if neg_word in context:
                return True
        
        return False
    
    def get_response(self, result: CrisisResult) -> str:
        """根据危机等级生成响应"""
        if result.level == CrisisLevel.SAFE:
            return None  # 不需要特殊处理
        
        responses = {
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
你能不能告诉我你现在在哪里？我们一起想办法。如果你有立即的危险，请拨打120或联系你身边的人。

全国心理援助热线：400-161-9995

你也可以告诉我你所在的地区，我帮你找到更近的帮助资源。💙"""
        }
        
        return responses.get(result.level, "")
    
    def is_crisis_keyword(self, text: str) -> Tuple[bool, Optional[str]]:
        """快速检查是否包含危机关键词"""
        text_lower = text.lower()
        
        for category, info in self.crisis_keywords.items():
            for keyword in info["keywords"]:
                if keyword.lower() in text_lower:
                    if not self._check_negation(text_lower, keyword):
                        return True, info["category"]
        
        return False, None


# 全局实例
_detector = None

def get_crisis_detector() -> CrisisDetector:
    """获取危机检测器单例"""
    global _detector
    if _detector is None:
        _detector = CrisisDetector()
    return _detector

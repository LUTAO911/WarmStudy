"""
Psychology Tools - 心理支持工具集
封装 psychology 模块，供 Agent 工具调用使用
"""

from typing import Dict, List, Any, Optional

from agent.modules.psychology import (
    EmotionDetector,
    EmpathicGenerator,
    CrisisDetector,
    PsychologyKnowledgeBase,
)
from agent.modules.psychology.emotion import EmotionResult, EmotionType
from agent.modules.psychology.crisis import CrisisResult, CrisisLevel


class PsychologyTools:
    """心理支持工具类 - 封装 psychology 模块的核心功能"""

    def __init__(self):
        self._emotion_detector = EmotionDetector()
        self._empathic_generator = EmpathicGenerator()
        self._crisis_detector = CrisisDetector()
        self._knowledge_base = PsychologyKnowledgeBase()

    # ========== 情绪识别 ==========

    def detect_emotion(self, text: str) -> Dict[str, Any]:
        """
        识别用户输入的情绪状态

        Args:
            text: 用户输入文本

        Returns:
            情绪识别结果字典
        """
        result = self._emotion_detector.detect(text)
        return {
            "emotion": result.emotion.value,
            "emotion_label": result.emotion.value if isinstance(result.emotion, EmotionType) else result.emotion,
            "intensity": result.intensity,
            "keywords": result.keywords,
            "suggestion": result.suggestion,
        }

    def detect_emotion_simple(self, text: str) -> str:
        """
        简单情绪识别（仅返回情绪类型）

        Args:
            text: 用户输入文本

        Returns:
            情绪类型字符串
        """
        result = self._emotion_detector.detect(text)
        return result.emotion.value if isinstance(result.emotion, EmotionType) else str(result.emotion)

    # ========== 危机检测 ==========

    def check_crisis(self, text: str) -> Dict[str, Any]:
        """
        检测危机信号（自杀倾向、自伤等）

        Args:
            text: 用户输入文本

        Returns:
            危机检测结果字典
        """
        result = self._crisis_detector.check(text)
        return {
            "level": result.level.value if isinstance(result.level, CrisisLevel) else str(result.level),
            "signals": result.signals,
            "message": result.message,
            "action": result.action,
            "hotlines": result.hotlines,
        }

    def is_crisis(self, text: str) -> bool:
        """
        快速判断是否存在危机信号

        Args:
            text: 用户输入文本

        Returns:
            是否存在危机
        """
        result = self._crisis_detector.check(text)
        level = result.level.value if isinstance(result.level, CrisisLevel) else str(result.level)
        return level in ("medium", "high", "critical")

    # ========== 共情生成 ==========

    def generate_empathic_response(
        self,
        user_input: str,
        emotion: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        生成共情回复

        Args:
            user_input: 用户输入
            emotion: 识别到的情绪类型（可选）
            context: 额外上下文（可选），包含 knowledge 字段

        Returns:
            共情回复文本
        """
        # 如果没有传入情绪，先检测
        if emotion is None:
            emotion_result = self._emotion_detector.detect(user_input)
        else:
            from agent.modules.psychology.emotion import EmotionType
            emotion_result = self._emotion_detector.detect(user_input)
            # 使用传入的情绪类型
            try:
                emotion_result.emotion = EmotionType(emotion)
            except ValueError:
                pass  # 如果无效，保持检测结果

        # 从context中提取knowledge
        knowledge = None
        if context and "knowledge" in context:
            k = context["knowledge"]
            if isinstance(k, dict) and "results" in k:
                knowledge = [r.get("content", "") for r in k["results"]]
            elif isinstance(k, list):
                knowledge = k

        # 调用共情生成器
        empathic_result = self._empathic_generator.generate(
            user_message=user_input,
            emotion_result=emotion_result,
            knowledge=knowledge
        )

        return empathic_result.response

    # ========== 知识库检索 ==========

    def search_psychology_knowledge(
        self,
        query: str,
        user_type: str = "student",
        n_results: int = 5,
    ) -> Dict[str, Any]:
        """
        检索心理知识库

        Args:
            query: 检索查询
            user_type: 用户类型 (student/parent/teacher)
            n_results: 返回结果数量

        Returns:
            检索结果字典
        """
        results = self._knowledge_base.search(
            query=query,
            user_type=user_type,
            top_k=n_results,
        )
        return {
            "query": query,
            "user_type": user_type,
            "count": len(results),
            "results": [r.to_dict() if hasattr(r, "to_dict") else r for r in results],
        }

    def get_knowledge_by_category(
        self,
        category: str,
        user_type: str = "student",
    ) -> Dict[str, Any]:
        """
        按分类获取心理知识

        Args:
            category: 知识分类
            user_type: 用户类型

        Returns:
            该分类下的知识列表
        """
        entries = self._knowledge_base.get_by_category(
            category=category,
            user_type=user_type,
        )
        return {
            "category": category,
            "user_type": user_type,
            "count": len(entries),
            "entries": [e.to_dict() if hasattr(e, "to_dict") else e for e in entries],
        }

    def get_all_categories(self, user_type: str = "student") -> List[str]:
        """
        获取所有知识分类

        Args:
            user_type: 用户类型

        Returns:
            分类列表
        """
        return self._knowledge_base.get_categories(user_type=user_type)

    # ========== 综合心理支持 ==========

    def psychological_support(
        self,
        user_input: str,
        user_type: str = "student",
    ) -> Dict[str, Any]:
        """
        综合心理支持处理：情绪识别 + 危机检测 + 知识检索 + 共情回复

        Args:
            user_input: 用户输入
            user_type: 用户类型

        Returns:
            综合处理结果
        """
        # 1. 危机检测（优先）
        crisis_result = self.check_crisis(user_input)

        # 2. 情绪识别
        emotion_result = self.detect_emotion(user_input)

        # 3. 如果是危机情况，返回危机干预响应
        crisis_level = crisis_result.get("level", "safe")
        if crisis_level in ("medium", "high", "critical"):
            # 将dict转回CrisisResult以获取响应
            from agent.modules.psychology.crisis import CrisisResult, CrisisLevel
            crisis_obj = CrisisResult(
                level=CrisisLevel(crisis_level),
                signals=crisis_result.get("signals", []),
                message=crisis_result.get("message", ""),
                action=crisis_result.get("action", ""),
                hotlines=crisis_result.get("hotlines", [])
            )
            return {
                "type": "crisis_intervention",
                "crisis": crisis_result,
                "emotion": emotion_result,
                "response": self._crisis_detector.get_response(crisis_obj),
            }

        # 4. 正常情况：检索相关知识
        knowledge_result = self.search_psychology_knowledge(
            query=user_input,
            user_type=user_type,
            n_results=3,
        )

        # 5. 生成共情回复
        empathic_response = self.generate_empathic_response(
            user_input=user_input,
            emotion=emotion_result.get("emotion"),
            context={"knowledge": knowledge_result},
        )

        return {
            "type": "normal_support",
            "emotion": emotion_result,
            "crisis": crisis_result,
            "knowledge": knowledge_result,
            "response": empathic_response,
        }


# 全局单例
_psychology_tools: Optional[PsychologyTools] = None


def get_psychology_tools() -> PsychologyTools:
    """获取 PsychologyTools 单例"""
    global _psychology_tools
    if _psychology_tools is None:
        _psychology_tools = PsychologyTools()
    return _psychology_tools

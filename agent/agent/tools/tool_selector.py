"""
Dynamic Tool Selector - 动态工具选择器
基于语义的工具匹配，替代关键词匹配
版本: v5.0
"""
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from agent.tools import ToolRegistry

# ========== 数据模型 ==========

class MatchConfidence(Enum):
    """匹配置信度"""
    HIGH = "high"      # >= 0.8
    MEDIUM = "medium"  # >= 0.5
    LOW = "low"        # >= 0.3
    NONE = "none"      # < 0.3

@dataclass
class ToolMatch:
    """工具匹配结果"""
    tool_name: str
    confidence: float           # 0-1 匹配置信度
    match_level: MatchConfidence
    match_reason: str            # 匹配原因
    suggested_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SelectionResult:
    """选择结果"""
    selected_tools: List[ToolMatch]
    skipped_tools: List[str]     # 跳过的工具名
    reasoning: str

# ========== 关键词匹配规则 ==========

# 每个工具的触发关键词
TOOL_KEYWORDS = {
    "get_current_time": {
        "keywords": ["时间", "现在", "几点", "日期", "今天", "几点钟", "什么时间"],
        "weight": 1.0
    },
    "calculate": {
        "keywords": ["计算", "等于", "+", "-", "*", "/", "加", "减", "乘", "除", "多少"],
        "weight": 1.0
    },
    "search_knowledge_base": {
        "keywords": ["知识", "库", "文档", "资料", "查找", "检索", "什么", "如何", "怎么"],
        "weight": 0.8
    },
    "search_web": {
        "keywords": ["搜索", "网上", "查一下", "找一下", "google", "百度"],
        "weight": 0.9
    },
    "detect_emotion": {
        "keywords": ["情绪", "心情", "感觉", "感受", "怎样", "怎么样"],
        "weight": 1.0
    },
    "check_crisis": {
        "keywords": ["想死", "自杀", "自残", "轻生", "不想活", "活不下去"],
        "weight": 1.0
    },
    "search_psychology_knowledge": {
        "keywords": ["心理", "焦虑", "压力", "抑郁", "人际", "关系", "学习压力"],
        "weight": 1.0
    },
    "generate_empathic_response": {
        "keywords": ["难过", "伤心", "害怕", "焦虑", "生气", "开心", "高兴"],
        "weight": 1.0
    },
    "psychological_support": {
        "keywords": ["心理支持", "倾诉", "聊聊", "说说", "心事"],
        "weight": 1.0
    }
}

# ========== 工具选择器 ==========

class ToolSelector:
    """
    动态工具选择器

    选择策略：
    1. 关键词匹配 - 显式触发词
    2. 语义模式匹配 - 隐式需求推断
    3. 上下文感知 - 考虑对话模式
    4. 置信度阈值 - 低于阈值不选择
    5. 互斥性处理 - 避免重复选择
    """

    def __init__(
        self,
        tool_registry: Optional["ToolRegistry"] = None,
        min_confidence: float = 0.3
    ):
        self.registry = tool_registry
        self.min_confidence = min_confidence

        # 互斥工具组（同一组只选一个）
        self._mutual_exclusion: Dict[str, List[str]] = {
            "emotion_group": ["detect_emotion", "generate_empathic_response", "psychological_support"],
        }

    async def select_tools(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        max_tools: int = 3,
        force_tools: Optional[List[str]] = None
    ) -> SelectionResult:
        """
        选择合适的工具

        Args:
            message: 用户消息
            context: 对话上下文
            max_tools: 最多选择工具数
            force_tools: 强制选择的工具（不管置信度）

        Returns:
            SelectionResult: 选择结果
        """
        ctx = context or {}
        mode = ctx.get("mode", "chat")

        # 1. 获取所有可用工具
        if self.registry:
            available_tools = self.registry.get_all()
            tool_names = [t.name for t in available_tools]
        else:
            tool_names = list(TOOL_KEYWORDS.keys())

        # 2. 计算每个工具的匹配度
        matches: List[ToolMatch] = []

        for tool_name in tool_names:
            if tool_name not in TOOL_KEYWORDS:
                continue

            match = self._calculate_match(tool_name, message, ctx)
            if match and (match.confidence >= self.min_confidence or
                         (force_tools and tool_name in force_tools)):
                matches.append(match)

        # 3. 处理互斥关系
        matches = self._apply_mutual_exclusion(matches)

        # 4. 强制工具添加
        if force_tools:
            for tool_name in force_tools:
                if not any(m.tool_name == tool_name for m in matches):
                    matches.append(ToolMatch(
                        tool_name=tool_name,
                        confidence=1.0,
                        match_level=MatchConfidence.HIGH,
                        match_reason="forced",
                        suggested_params={}
                    ))

        # 5. 按置信度排序并截取
        matches.sort(key=lambda x: x.confidence, reverse=True)
        selected = matches[:max_tools]

        # 6. 构建结果
        selected_names = [m.tool_name for m in selected]
        skipped = [t for t in tool_names if t not in selected_names]

        reasoning = self._build_reasoning(selected, ctx)

        return SelectionResult(
            selected_tools=selected,
            skipped_tools=skipped,
            reasoning=reasoning
        )

    def _calculate_match(
        self,
        tool_name: str,
        message: str,
        context: Dict[str, Any]
    ) -> Optional[ToolMatch]:
        """计算工具与消息的匹配度"""
        config = TOOL_KEYWORDS.get(tool_name)
        if not config:
            return None

        keywords = config.get("keywords", [])
        base_weight = config.get("weight", 0.5)

        msg_lower = message.lower()

        # 1. 关键词匹配
        matched_keywords = [kw for kw in keywords if kw in msg_lower]
        keyword_score = len(matched_keywords) / max(len(keywords), 1)

        if not matched_keywords:
            return None

        # 2. 模式匹配增强
        pattern_boost = self._check_patterns(tool_name, message)

        # 3. 上下文增强
        context_boost = self._get_context_boost(tool_name, context)

        # 综合分数
        confidence = min(keyword_score * base_weight + pattern_boost + context_boost, 1.0)

        # 确定置信度等级
        if confidence >= 0.8:
            level = MatchConfidence.HIGH
        elif confidence >= 0.5:
            level = MatchConfidence.MEDIUM
        elif confidence >= 0.3:
            level = MatchConfidence.LOW
        else:
            level = MatchConfidence.NONE

        return ToolMatch(
            tool_name=tool_name,
            confidence=confidence,
            match_level=level,
            match_reason=f"匹配关键词: {', '.join(matched_keywords)}",
            suggested_params=self._extract_params(tool_name, message)
        )

    def _check_patterns(self, tool_name: str, message: str) -> float:
        """检查语义模式，返回额外加分"""
        boost = 0.0
        msg_lower = message.lower()

        # 计算相关模式
        calc_patterns = ["多少", "等于", "加起来", "加起来"]
        time_patterns = ["现在几点", "什么时间", "今天几号"]

        if tool_name == "calculate":
            if any(p in msg_lower for p in calc_patterns):
                boost += 0.2

        elif tool_name == "get_current_time":
            if any(p in msg_lower for p in time_patterns):
                boost += 0.2

        # 心理学相关工具的模式
        psych_patterns = {
            "detect_emotion": ["我感觉", "心情", "情绪"],
            "check_crisis": ["想死", "自杀", "不想活", "轻生"],
            "search_psychology_knowledge": ["心理知识", "焦虑怎么办", "压力大"],
            "generate_empathic_response": ["难过", "伤心", "害怕"],
            "psychological_support": ["聊聊", "想说说", "倾诉"],
        }

        if tool_name in psych_patterns:
            patterns = psych_patterns[tool_name]
            if any(p in msg_lower for p in patterns):
                boost += 0.2

        return boost

    def _get_context_boost(self, tool_name: str, context: Dict[str, Any]) -> float:
        """根据上下文字典获取额外加分"""
        boost = 0.0
        mode = context.get("mode", "chat")

        # 心理学模式下，心理学工具获得boost
        if mode == "psychology":
            psych_tools = [
                "detect_emotion", "check_crisis",
                "search_psychology_knowledge", "generate_empathic_response",
                "psychological_support"
            ]
            if tool_name in psych_tools:
                boost += 0.3

        # 危机模式下，危机检测获得boost
        if mode == "crisis":
            if tool_name == "check_crisis":
                boost += 0.5

        # 如果已有情绪信息，避免重复检测
        if context.get("emotion_detected"):
            if tool_name in ["detect_emotion", "generate_empathic_response"]:
                boost -= 0.3

        return boost

    def _apply_mutual_exclusion(self, matches: List[ToolMatch]) -> List[ToolMatch]:
        """应用互斥规则"""
        if not matches:
            return matches

        # 按置信度排序
        matches.sort(key=lambda x: x.confidence, reverse=True)

        result: List[ToolMatch] = []
        selected_groups: Dict[str, str] = {}  # group_name -> tool_name

        for match in matches:
            # 检查是否与已选工具互斥
            is_mutual = False
            for group_name, group_tools in self._mutual_exclusion.items():
                if match.tool_name in group_tools:
                    if group_name in selected_groups:
                        # 该组已选工具，跳过
                        is_mutual = True
                        break
                    else:
                        # 标记该组已选
                        selected_groups[group_name] = match.tool_name

            if not is_mutual:
                result.append(match)

        return result

    def _extract_params(self, tool_name: str, message: str) -> Dict[str, Any]:
        """从消息中提取工具参数"""
        params: Dict[str, Any] = {}

        if tool_name == "calculate":
            import re
            # 提取数学表达式
            expr_match = re.search(r'[\d\+\-\*/\(\)\.\s]+', message)
            if expr_match:
                params["expression"] = expr_match.group().strip()

        elif tool_name == "search_knowledge_base":
            params["query"] = message
            params["n_results"] = 5

        elif tool_name == "search_psychology_knowledge":
            params["query"] = message
            params["n_results"] = 3

        elif tool_name in ["detect_emotion", "check_crisis", "generate_empathic_response"]:
            params["text"] = message

        return params

    def _build_reasoning(self, selected: List[ToolMatch], context: Dict[str, Any]) -> str:
        """构建选择理由"""
        if not selected:
            return "无工具匹配"

        tool_names = [m.tool_name for m in selected]
        mode = context.get("mode", "chat")

        reasoning = f"选择工具: {', '.join(tool_names)}"
        if mode != "chat":
            reasoning += f" (模式: {mode})"

        return reasoning


# ========== 便捷函数 ==========

async def select_tools_for_message(
    message: str,
    tool_registry=None,
    context: Optional[Dict[str, Any]] = None,
    max_tools: int = 3
) -> SelectionResult:
    """为消息选择合适工具的便捷函数"""
    selector = ToolSelector(tool_registry=tool_registry)
    return await selector.select_tools(
        message=message,
        context=context,
        max_tools=max_tools
    )

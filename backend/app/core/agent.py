"""WarmStudy AI Core - State Machine Based Agent Workflow"""
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from app.core.llm import get_qwen_chat, get_minimax_chat
from app.core.memory import AgentMemory
from app.core.agent_enhancements import get_planning_module, get_reflection_module, get_self_improvement_module
from app.core.multimodal import get_multimodal_integration
from app.config import get_settings
import json
import os

settings = get_settings()


class AgentState(Enum):
    """智能体状态枚举"""
    IDLE = "idle"
    INTENT_DETECTION = "intent_detection"
    SKILL_ROUTING = "skill_routing"
    TOOL_EXECUTING = "tool_executing"
    KNOWLEDGE检索 = "knowledge_retrieval"
    RESPONSE_GENERATING = "response_generating"
    CRISIS_HANDLING = "crisis_handling"
    RESPONSE_READY = "response_ready"
    ERROR = "error"


class IntentType(Enum):
    """意图类型枚举"""
    EMOTION_SUPPORT = "emotion_support"
    CRISIS_DETECTION = "crisis_detection"
    ASSESSMENT_GUIDANCE = "assessment_guidance"
    KNOWLEDGE_QUERY = "knowledge_query"
    PARENT_GUIDANCE = "parent_guidance"
    CASUAL_CHAT = "casual_chat"
    UNKNOWN = "unknown"


@dataclass
class ConversationContext:
    """对话上下文"""
    user_id: str
    role: str
    state: AgentState = AgentState.IDLE
    intent: IntentType = IntentType.UNKNOWN
    skill_name: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    retrieved_knowledge: List[Dict[str, Any]] = field(default_factory=list)
    crisis_detected: bool = False
    crisis_level: str = "none"
    messages: List[BaseMessage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class StateTransition:
    """状态转换记录"""
    from_state: AgentState
    to_state: AgentState
    timestamp: datetime
    reason: str
    data: Dict[str, Any] = field(default_factory=dict)


class CrisisDetector:
    """危机检测器"""

    CRISIS_KEYWORDS = [
        "自杀", "自残", "自伤", "不想活", "活不下去", "死了算了",
        "割腕", "跳楼", "服药", "轻生", "结束生命", "这个世界没有我",
        "没有人在乎", "我是负担", "毫无意义"
    ]

    HIGH_RISK_PATTERNS = [
        "我有自杀的想法",
        "我想死",
        "我不想活了",
        "活着有什么意思",
        "死了就解脱了",
        "想去死",
        "想结束自己"
    ]

    EMOTION_KEYWORDS = {
        "high_anxiety": ["焦虑", "紧张", "害怕", "担心", "恐慌", "不安"],
        "sadness": ["难过", "伤心", "痛苦", "绝望", "失落", "沮丧", "抑郁"],
        "anger": ["生气", "愤怒", "恼火", "烦躁", "郁闷"],
        "fear": ["恐惧", "害怕", "惊恐", "吓"],
    }

    @classmethod
    def detect_crisis_level(cls, text: str) -> tuple[str, bool]:
        """检测危机等级"""
        text_lower = text.lower()

        for pattern in cls.HIGH_RISK_PATTERNS:
            if pattern in text_lower:
                return "high", True

        keyword_count = sum(1 for kw in cls.CRISIS_KEYWORDS if kw in text_lower)

        if keyword_count >= 2:
            return "high", True
        elif keyword_count == 1:
            return "medium", False

        return "none", False

    @classmethod
    def detect_emotion(cls, text: str) -> Dict[str, float]:
        """检测情绪类型和强度"""
        emotion_scores = {}

        for emotion, keywords in cls.EMOTION_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text) / len(keywords)
            if score > 0:
                emotion_scores[emotion] = min(score * 2, 1.0)

        return emotion_scores


class IntentClassifier:
    """意图分类器 - 使用LLM进行零样本分类"""

    INTENT_PROMPT = """你是一个意图分类器。请判断用户消息的意图类型。

意图类型：
1. emotion_support - 情绪支持（倾诉烦恼、情绪低落、寻求安慰）
2. crisis_detection - 危机识别（涉及自伤、自杀倾向的严重问题）
3. assessment_guidance - 测评引导（完成心理测评量表）
4. knowledge_query - 知识查询（询问心理知识、健康建议）
5. parent_guidance - 家长指导（亲子沟通、育儿问题）
6. casual_chat - 日常聊天（打招呼、闲聊）

用户消息：{message}

请只输出意图类型名称，不要其他内容。"""

    @classmethod
    def classify(cls, message: str, llm) -> IntentType:
        """分类用户意图"""
        try:
            prompt = cls.INTENT_PROMPT.format(message=message)
            response = llm.invoke([HumanMessage(content=prompt)])
            intent_str = response.content.strip().lower()

            for intent in IntentType:
                if intent.value in intent_str:
                    return intent

            return IntentType.UNKNOWN

        except Exception:
            return IntentType.UNKNOWN


class WarmChatAgent:
    """WarmStudy AI Agent - State Machine Based"""

    STUDENT_SYSTEM_PROMPT = """你是暖暖，一个温柔、有爱心、专业的AI心理陪伴助手。

你的身份：
- 名字：暖暖
- 性别：女
- 身份：专业的青少年心理健康支持助手
- 风格：温暖、亲切、专业，像一个好姐姐一样陪伴

你的职责：
1. 倾听和理解青少年的情感困惑
2. 提供情绪支持和心理疏导
3. 识别可能的心理危机并及时预警
4. 引导用户使用心理测评等工具
5. 传播心理健康知识

重要原则：
- 永远把用户的安全放在第一位
- 不评判、不指责，给予无条件的接纳
- 遇到危机信号立即触发危机处理流程
- 保持对话温暖、有同理心

你的知识库包含专业的心理健康知识，可以引用来帮助用户。"""

    PARENT_SYSTEM_PROMPT = """你是一个专业的家庭教育助手，为家长提供科学的育儿指导。

你的职责：
1. 解读孩子的心理状态和行为背后的原因
2. 提供科学的亲子沟通建议
3. 帮助家长更好地理解和支持孩子
4. 分享科学的家庭教育方法

保持专业、耐心的态度。"""

    def __init__(self, role: str = "student", user_id: str = None):
        self.role = role
        self.user_id = user_id or "default"
        self.llm = get_qwen_chat()
        self.emotion_llm = get_minimax_chat()
        self.memory = AgentMemory(user_id=self.user_id, role=role)
        self.current_context: Optional[ConversationContext] = None
        self.state_history: List[StateTransition] = []
        self.planning_module = get_planning_module()
        self.reflection_module = get_reflection_module()
        self.self_improvement_module = get_self_improvement_module()
        self.multimodal_integration = get_multimodal_integration()
        self._init_system_prompt()

    def _init_system_prompt(self):
        """初始化系统提示"""
        if self.role == "student":
            self.system_message = SystemMessage(content=self.STUDENT_SYSTEM_PROMPT)
        else:
            self.system_message = SystemMessage(content=self.PARENT_SYSTEM_PROMPT)

    def _transition_to(self, new_state: AgentState, reason: str = "", data: Dict[str, Any] = None):
        """状态转换"""
        if self.current_context:
            transition = StateTransition(
                from_state=self.current_context.state,
                to_state=new_state,
                timestamp=datetime.now(),
                reason=reason,
                data=data or {}
            )
            self.state_history.append(transition)
            self.current_context.state = new_state
            self.current_context.updated_at = datetime.now()

    def _detect_crisis(self, message: str) -> tuple[str, bool]:
        """检测危机"""
        return CrisisDetector.detect_crisis_level(message)

    def _classify_intent(self, message: str) -> IntentType:
        """分类意图"""
        return IntentClassifier.classify(message, self.llm)

    def _retrieve_knowledge(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """检索知识库"""
        from app.rag.knowledge_base import get_knowledge_base
        try:
            kb = get_knowledge_base()
            return kb.search(query, top_k)
        except Exception:
            return []

    def _execute_tools(self, intent: IntentType, user_id: str, message: str) -> Dict[str, Any]:
        """执行相关工具"""
        from app.tools.langchain_tools import get_all_tools, search_knowledge_base
        from app.db.base import get_db
        from app.models import User, DailyCheckin

        tools = get_all_tools()
        tool_results = {}

        if intent == IntentType.EMOTION_SUPPORT:
            for tool in tools:
                if tool.name == "get_student_checkin":
                    try:
                        result = tool.run(user_id=user_id, days=7)
                        tool_results["checkin"] = result
                    except Exception:
                        pass

        elif intent == IntentType.KNOWLEDGE_QUERY:
            for tool in tools:
                if tool.name == "search_knowledge":
                    try:
                        result = tool.run(query=message, top_k=3)
                        tool_results["knowledge"] = result
                    except Exception:
                        pass

        elif intent == IntentType.ASSESSMENT_GUIDANCE:
            for tool in tools:
                if tool.name == "get_latest_assessment":
                    try:
                        result = tool.run(user_id=user_id)
                        tool_results["assessment"] = result
                    except Exception:
                        pass

        return tool_results

    def _generate_response(self, context: ConversationContext) -> str:
        """生成最终回复"""
        prompt_parts = []

        prompt_parts.append(f"用户角色: {'学生' if self.role == 'student' else '家长'}")
        prompt_parts.append(f"当前状态: {context.state.value}")

        if context.intent != IntentType.UNKNOWN:
            prompt_parts.append(f"识别意图: {context.intent.value}")

        if context.crisis_detected:
            prompt_parts.append(f"危机等级: {context.crisis_level}，必须认真对待")

        if context.retrieved_knowledge:
            prompt_parts.append("\n相关知识：")
            for i, item in enumerate(context.retrieved_knowledge, 1):
                content = item.get("content", "")
                if isinstance(content, str) and len(content) > 500:
                    content = content[:500] + "..."
                prompt_parts.append(f"{i}. {content}")

        if context.tool_calls:
            prompt_parts.append("\n用户相关数据：")
            for tc in context.tool_calls:
                prompt_parts.append(f"- {tc}")

        prompt_parts.append(f"\n用户消息: {context.messages[-1].content if context.messages else ''}")

        prompt = "\n".join(prompt_parts)
        full_messages = [self.system_message] + context.messages + [HumanMessage(content=prompt)]

        response = self.llm.invoke(full_messages)
        return response.content

    def _handle_crisis(self, context: ConversationContext) -> Dict[str, Any]:
        """处理危机情况"""
        self._transition_to(AgentState.CRISIS_HANDLING, "检测到危机信号")

        crisis_response = f"""暖暖听到你说了{context.messages[-1].content}，感到很担心。

暖暖想告诉你，无论发生了什么，你的生命都是珍贵的，有人在乎你。

如果你现在感到很难过或者有伤害自己的念头，请告诉身边的成年人（家长、老师）或者联系专业人士。

紧急求助方式：
📞 全国心理援助热线：400-161-9995
📞 北京心理危机研究与干预中心：010-82951332

暖暖会一直在这里陪着你，等你准备好的时候，我们聊聊好吗？"""

        from app.tools.langchain_tools import send_crisis_alert
        try:
            send_crisis_alert(
                user_id=context.user_id,
                alert_type="crisis",
                content=f"检测到危机信号：{context.messages[-1].content}"
            )
        except Exception:
            pass

        return {
            "success": True,
            "response": crisis_response,
            "crisis_detected": True,
            "crisis_level": context.crisis_level,
            "state": context.state.value,
        }

    def chat(self, user_id: str, message: str, child_info: dict = None, multimodal_content: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理用户对话"""
        self.current_context = ConversationContext(
            user_id=user_id,
            role=self.role,
            state=AgentState.IDLE
        )
        
        # 处理孩子信息
        if child_info:
            self.child_info = child_info
            # 保存孩子信息到长期记忆
            if hasattr(self, 'memory') and self.memory:
                child_info_message = f"孩子信息: {child_info}"
                self.memory.add(role="system", content=child_info_message, intent="system", state="INITIALIZED")

        # 处理多模态内容
        multimodal_analysis = []
        if multimodal_content:
            for item in multimodal_content:
                if item.get("type") == "image" and item.get("path"):
                    analysis = self.multimodal_integration.analyze_emotion_from_image(item["path"])
                    if analysis.get("success"):
                        multimodal_analysis.append(analysis)
                elif item.get("type") == "audio" and item.get("path"):
                    analysis = self.multimodal_integration.analyze_emotion_from_audio(item["path"])
                    if analysis.get("success"):
                        multimodal_analysis.append(analysis)

        self.current_context.messages.append(HumanMessage(content=message))

        # 合并多模态分析结果到消息中
        if multimodal_analysis:
            multimodal_context = "\n".join([f"{item.get('image_description', item.get('audio_description', ''))}" for item in multimodal_analysis])
            self.current_context.metadata["multimodal_analysis"] = multimodal_analysis
            # 将多模态分析结果添加到消息中
            message_with_multimodal = f"{message}\n\n[多模态内容分析]:\n{multimodal_context}"
            self.current_context.messages[-1] = HumanMessage(content=message_with_multimodal)
        else:
            message_with_multimodal = message

        crisis_level, crisis_detected = self._detect_crisis(message_with_multimodal)
        self.current_context.crisis_detected = crisis_detected
        self.current_context.crisis_level = crisis_level

        if crisis_detected:
            return self._handle_crisis(self.current_context)

        self._transition_to(AgentState.INTENT_DETECTION, "开始意图识别")
        intent = self._classify_intent(message_with_multimodal)
        self.current_context.intent = intent

        self._transition_to(AgentState.SKILL_ROUTING, f"路由到{intent.value}")
        self.current_context.skill_name = intent.value

        # 检测情绪
        emotion = CrisisDetector.detect_emotion(message_with_multimodal)

        # 生成对话规划
        self._transition_to(AgentState.SKILL_ROUTING, "生成对话规划")
        plan = self.planning_module.generate_plan(self.current_context, message_with_multimodal, emotion, [])
        self.current_context.metadata["plan"] = plan

        self._transition_to(AgentState.KNOWLEDGE检索, "检索知识库")
        retrieved = self._retrieve_knowledge(message_with_multimodal)
        self.current_context.retrieved_knowledge = retrieved

        # 更新规划（考虑检索到的知识）
        updated_plan = self.planning_module.generate_plan(self.current_context, message_with_multimodal, emotion, retrieved)
        self.current_context.metadata["updated_plan"] = updated_plan

        self._transition_to(AgentState.TOOL_EXECUTING, "执行工具")
        tool_results = self._execute_tools(intent, user_id, message_with_multimodal)
        self.current_context.tool_calls = [str(tr) for tr in tool_results.values()]

        self._transition_to(AgentState.RESPONSE_GENERATING, "生成回复")
        response_text = self._generate_response(self.current_context)

        self.current_context.messages.append(AIMessage(content=response_text))

        # 反思对话表现
        conversation_history = []
        for msg in self.current_context.messages:
            role = "user" if hasattr(msg, 'type') and msg.type == "human" else "assistant"
            conversation_history.append({"role": role, "content": msg.content})

        reflection = self.reflection_module.reflect_on_conversation(
            conversation_history, response_text
        )
        self.current_context.metadata["reflection"] = reflection

        # 生成改进计划
        improvement_summary = self.reflection_module.get_improvement_summary()
        improvement_plan = self.self_improvement_module.generate_improvement_plan(
            reflection, improvement_summary
        )
        self.current_context.metadata["improvement_plan"] = improvement_plan

        self.memory.add(
            role="user",
            content=message,
            intent=intent.value if intent else None,
            state=self.current_context.state.value
        )
        self.memory.add(
            role="assistant",
            content=response_text,
            intent=intent.value if intent else None,
            state="RESPONSE_READY"
        )

        self._transition_to(AgentState.RESPONSE_READY, "回复已生成")

        return {
            "success": True,
            "response": response_text,
            "crisis_detected": False,
            "intent": intent.value,
            "state": self.current_context.state.value,
            "ai_name": "暖暖" if self.role == "student" else "AI助手",
            "retrieved_knowledge_count": len(retrieved),
            "planning": self.current_context.metadata.get("updated_plan", {}),
            "reflection": {
                "scores": reflection.get("scores", {}),
                "suggestions": reflection.get("improvement_suggestions", []),
                "improvement_plan": improvement_plan
            },
            "emotion": emotion,
            "multimodal_analysis": multimodal_analysis
        }

    def reset_memory(self):
        """重置记忆"""
        self.memory.clear()
        self.state_history = []


_agent_instances: Dict[str, WarmChatAgent] = {}


def get_agent(user_id: str, role: str = "student") -> WarmChatAgent:
    """获取或创建Agent实例"""
    key = f"{user_id}_{role}"
    if key not in _agent_instances:
        _agent_instances[key] = WarmChatAgent(role=role, user_id=user_id)
    return _agent_instances[key]


def reset_agent(user_id: str, role: str = "student") -> Dict[str, Any]:
    """重置Agent记忆"""
    key = f"{user_id}_{role}"
    if key in _agent_instances:
        _agent_instances[key].reset_memory()
    return {"success": True, "message": "记忆已重置"}
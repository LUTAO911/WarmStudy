"""
Orchestrator - 主编排引擎
Agent 核心调度器，协调所有子模块处理用户请求
"""
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from agent.memory import MemoryManager
    from agent.context import ContextManager
    from agent.tools import ToolRegistry
    from agent.modules.psychology import PsychologyModule
    from agent.memory_store.unified_memory import UnifiedMemoryManager

class ConversationMode(Enum):
    """对话模式"""
    CHAT = "chat"
    PSYCHOLOGY = "psychology"
    EDUCATION = "education"
    CRISIS = "crisis"

@dataclass
class OrchestratorConfig:
    """编排器配置"""
    name: str = "暖学帮智能助手"
    model: str = "qwen-max"
    temperature: float = 0.7
    max_tokens: int = 1500
    enable_rag: bool = True
    enable_tools: bool = True
    enable_psychology: bool = True
    max_workflow_steps: int = 5
    enable_streaming: bool = True
    enable_reflection: bool = True
    reflection_threshold: float = 0.6

@dataclass
class UserMessage:
    """用户消息"""
    content: str
    session_id: str = "default"
    user_id: Optional[str] = None
    user_type: str = "student"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EmotionInfo:
    """情绪信息"""
    emotion: str = "neutral"
    intensity: float = 0.5
    icon: str = "😌"
    keywords: List[str] = field(default_factory=list)

@dataclass
class AgentResponse:
    """智能体响应"""
    content: str
    mode: ConversationMode = ConversationMode.CHAT
    emotion: Optional[EmotionInfo] = None
    crisis_level: Optional[str] = None
    sources: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.content,
            "mode": self.mode.value,
            "emotion": {
                "emotion": self.emotion.emotion if self.emotion else None,
                "intensity": self.emotion.intensity if self.emotion else None,
                "icon": self.emotion.icon if self.emotion else None,
            } if self.emotion else None,
            "crisis_level": self.crisis_level,
            "sources": self.sources,
            "tool_results": self.tool_results,
            "metadata": self.metadata,
            "execution_time": round(self.execution_time, 3)
        }

class Orchestrator:
    """
    主编排器
    
    职责：
    1. 接收用户消息，协调各模块处理
    2. 管理对话生命周期
    3. 构建最终响应
    
    工作流程：
    1. 意图路由 - 确定对话模式
    2. 并行执行 - 记忆读取、RAG检索、工具调用
    3. 心理学处理（如需要）
    4. LLM生成响应
    5. 反思机制
    6. 更新记忆
    """

    # 心理学关键词
    PSYCHOLOGY_KEYWORDS = [
        "情绪", "心情", "难过", "开心", "生气", "害怕", "焦虑",
        "压力", "紧张", "压抑", "沮喪", "失落", "失眠",
        "心理", "心事", "内心", "人际关系", "亲子关系",
        "考试压力", "学习压力", "被孤立", "被欺负",
        "自卑", "不自信", "绝望", "無助",
    ]

    # 危机关键词
    CRISIS_KEYWORDS = [
        "想死", "不想活", "活不下去", "死了", "輕生", "自殺",
        "自残", "割腕", "伤害自己", "上吊", "跳楼", "喝药",
    ]

    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        memory_manager: Optional["MemoryManager"] = None,
        unified_memory: Optional["UnifiedMemoryManager"] = None,
        context_manager: Optional["ContextManager"] = None,
        tool_registry: Optional["ToolRegistry"] = None,
        psychology_module: Optional["PsychologyModule"] = None,
    ):
        self.config = config or OrchestratorConfig()
        self.memory = memory_manager
        self.unified_memory = unified_memory
        self.context = context_manager
        self.tools = tool_registry
        self.psychology = psychology_module
        
        self._response_cache: Dict[str, tuple] = {}
        self._cache_ttl = 300

    def _is_psychology_message(self, message: str) -> bool:
        """检测消息是否与心理学相关"""
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in self.PSYCHOLOGY_KEYWORDS)

    def _is_crisis_message(self, message: str) -> bool:
        """检测消息是否包含危机信号"""
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in self.CRISIS_KEYWORDS)

    def _determine_mode(self, message: str) -> ConversationMode:
        """确定对话模式"""
        if self._is_crisis_message(message):
            return ConversationMode.CRISIS
        if self._is_psychology_message(message):
            return ConversationMode.PSYCHOLOGY
        return ConversationMode.CHAT

    async def chat(
        self,
        message: str,
        session_id: str = "default",
        user_id: Optional[str] = None,
        user_type: str = "student",
    ) -> AgentResponse:
        """
        处理对话请求
        
        Args:
            message: 用户消息
            session_id: 会话ID
            user_id: 用户ID
            user_type: 用户类型
            
        Returns:
            AgentResponse: 智能体响应
        """
        start_time = time.time()
        sid = session_id or "default"

        # 保存用户消息到记忆
        if self.memory:
            self.memory.add_user_message(message, {"session_id": sid})

        # 1. 确定对话模式
        mode = self._determine_mode(message)

        # 2. 心理学模式处理
        emotion_info = None
        crisis_level = None
        tool_results = []

        if mode in (ConversationMode.PSYCHOLOGY, ConversationMode.CRISIS):
            psych_result = await self._handle_psychology_mode(message, sid, user_type)
            emotion_info = psych_result.get("emotion")
            crisis_level = psych_result.get("crisis_level")
            tool_results = psych_result.get("tool_results", [])

            # 如果是危机模式，直接返回
            if mode == ConversationMode.CRISIS:
                crisis_response = psych_result.get("response", "")
                if self.memory:
                    self.memory.add_assistant_message(crisis_response, {"session_id": sid})
                return AgentResponse(
                    content=crisis_response,
                    mode=mode,
                    emotion=emotion_info,
                    crisis_level=crisis_level,
                    tool_results=tool_results,
                    execution_time=time.time() - start_time
                )

        # 3. RAG 检索（如需要）
        context_results = []
        if self.config.enable_rag:
            context_results = await self._retrieve_context(message, sid)

        # 4. 工具调用（如需要）
        if self.config.enable_tools:
            tool_results.extend(await self._execute_tools(message))

        # 5. 构建 Prompt 并生成响应
        prompt = self._build_prompt(
            message=message,
            session_id=sid,
            context_results=context_results,
            tool_results=tool_results,
            mode=mode
        )

        answer = await self._generate_response(prompt)

        # 6. 反思机制
        if self.config.enable_reflection and context_results:
            answer = await self._reflect(answer, message, context_results, sid)

        # 7. 更新记忆
        if self.memory:
            self.memory.add_assistant_message(answer, {
                "session_id": sid,
                "mode": mode.value,
                "tool_calls": len(tool_results),
            })

        # 8. 构建来源信息
        sources = []
        if context_results:
            for doc in context_results[:3]:
                sources.append({
                    "content": doc.get("content", "")[:150] + "...",
                    "source": doc.get("source", ""),
                    "similarity": doc.get("similarity", 0),
                })

        return AgentResponse(
            content=answer,
            mode=mode,
            emotion=emotion_info,
            crisis_level=crisis_level,
            sources=sources,
            tool_results=tool_results,
            metadata={
                "session_id": sid,
                "need_rag": len(context_results) > 0,
                "need_tools": len(tool_results) > 0,
            },
            execution_time=time.time() - start_time
        )

    async def _handle_psychology_mode(
        self,
        message: str,
        sid: str,
        user_type: str
    ) -> Dict[str, Any]:
        """处理心理学模式"""
        result = {
            "emotion": None,
            "crisis_level": None,
            "response": "",
            "tool_results": []
        }

        # 使用 psychology 模块
        if self.psychology:
            try:
                psych_result = await self.psychology.process(
                    user_input=message,
                    user_type=user_type,
                    context={}
                )
                
                if psych_result.emotion:
                    result["emotion"] = EmotionInfo(
                        emotion=psych_result.emotion.type,
                        intensity=psych_result.emotion.intensity,
                        icon=psych_result.emotion.icon,
                        keywords=psych_result.emotion.keywords
                    )
                
                if psych_result.crisis:
                    result["crisis_level"] = psych_result.crisis.level
                
                if psych_result.empathic_response:
                    result["response"] = psych_result.empathic_response
                    return result
                    
            except Exception:
                pass

        # 兜底：使用内置的情绪检测
        from agent.modules.psychology.emotion import EmotionDetector
        from agent.modules.psychology.crisis import CrisisDetector

        detector = EmotionDetector()
        emotion_result = detector.detect(message)

        crisis_detector = CrisisDetector()
        crisis_result = crisis_detector.check(message)

        result["emotion"] = EmotionInfo(
            emotion=emotion_result.emotion.value,
            intensity=emotion_result.intensity,
            icon="😌",
            keywords=emotion_result.keywords
        )
        result["crisis_level"] = crisis_result.level.value

        # 生成共情回复
        empathic_response = self._generate_empathic_response(
            message, emotion_result, crisis_result
        )
        result["response"] = empathic_response

        return result

    def _generate_empathic_response(
        self,
        message: str,
        emotion_result,
        crisis_result
    ) -> str:
        """生成共情回复"""
        from agent.modules.psychology.empathic import EmpathicGenerator
        
        generator = EmpathicGenerator()
        
        try:
            response = generator.generate(
                user_input=message,
                emotion_type=emotion_result.emotion.value,
                intensity=emotion_result.intensity
            )
            return response
        except Exception:
            # 兜底回复
            emotion_map = {
                "sad": "我听到你说的话，能感受到你现在很难过...",
                "anxious": "我能理解你现在的焦虑和压力...",
                "angry": "听起来你很生气，我理解你的感受...",
                "happy": "真为你高兴！有什么好事发生了吗？",
                "neutral": "嗯，我在听你说话...",
            }
            return emotion_map.get(emotion_result.emotion.value, "我在这里认真倾听...")

    async def _retrieve_context(
        self,
        query: str,
        sid: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """检索知识库上下文"""
        try:
            from vectorstore import query_with_hybrid_search
            results = query_with_hybrid_search(
                query_text=query,
                n_results=n_results,
                rerank=True
            )
            return results
        except Exception:
            return []

    async def _execute_tools(self, message: str) -> List[Dict[str, Any]]:
        """执行匹配的工具"""
        results = []
        if not self.tools:
            return results

        msg_lower = message.lower()
        tool_map = {
            "get_current_time": ["时间", "现在", "几点", "日期"],
            "calculate": ["计算", "等于"],
            "search_web": ["搜索", "查一下"],
        }

        for tool_name, keywords in tool_map.items():
            if any(k in msg_lower for k in keywords):
                try:
                    tr = self.tools.execute(tool_name, query=message)
                    if tr.is_success:
                        results.append({
                            "tool_name": tool_name,
                            "status": "success",
                            "result": tr.result
                        })
                except Exception:
                    pass

        return results

    def _build_prompt(
        self,
        message: str,
        session_id: str,
        context_results: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]],
        mode: ConversationMode
    ) -> str:
        """构建 Prompt"""
        history = ""
        if self.memory:
            history = self.memory.get_conversation_history(limit=10)

        ctx = ""
        if context_results:
            parts = []
            for i, doc in enumerate(context_results[:3]):
                parts.append(f"[知识库 {i+1}]\n{doc.get('content', '')[:500]}")
            ctx = "\n\n".join(parts)

        if tool_results:
            ctx += "\n\n[工具执行结果]\n" + "\n".join([
                f"- {tr.get('tool_name')}: {tr.get('result')}"
                for tr in tool_results
            ])

        system_prompt = self._get_system_prompt(mode)

        return (
            f"{system_prompt}\n\n"
            f"Conversation History:\n{history or 'No previous messages'}\n\n"
            + (f"Additional Context:\n{ctx}\n\n" if ctx else "\n")
            + f"User: {message}\n\nAssistant:"
        )

    def _get_system_prompt(self, mode: ConversationMode) -> str:
        """获取系统提示词"""
        base = "你是暖学帮智能助手，专注于青少年心理关怀和教育辅导。"

        if mode == ConversationMode.PSYCHOLOGY:
            return base + """
重要：你正在心理关怀模式。请：
1. 先共情，理解用户的感受
2. 用温暖的语气回应
3. 适当使用emoji
4. 给予积极的鼓励
"""
        elif mode == ConversationMode.EDUCATION:
            return base + """
重要：你正在教育辅导模式。请：
1. 专业、清晰地解答问题
2. 用易于理解的方式解释
3. 适当举例说明
"""
        return base

    async def _generate_response(self, prompt: str) -> str:
        """生成响应"""
        try:
            import os
            chat_model = os.getenv("CHAT_MODEL", "minimax")
            api_key = os.getenv("MINIMAX_API_KEY") or os.getenv("DASHSCOPE_API_KEY", "")

            if chat_model == "minimax":
                return await self._generate_minimax(prompt, api_key)
            else:
                return await self._generate_dashscope(prompt, api_key)
        except Exception as e:
            return f"生成响应时出错: {str(e)}"

    async def _generate_minimax(self, prompt: str, api_key: str) -> str:
        """MiniMax API 调用"""
        import requests
        import json

        url = "https://api.minimaxi.com/anthropic/v1/messages"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        data = {
            "model": "MiniMax-M2.7",
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": [{"role": "user", "content": prompt}]
        }

        resp = requests.post(url, headers=headers, json=data, timeout=60)
        if resp.status_code == 200:
            result = resp.json()
            for block in result.get("content", []):
                if block.get("type") == "text":
                    return block.get("text", "")
            return str(result)
        elif resp.status_code == 429:
            return "请求过于频繁，请稍后再试。"
        else:
            return f"Error: {resp.status_code}"

    async def _generate_dashscope(self, prompt: str, api_key: str) -> str:
        """DashScope API 调用"""
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        resp = client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        return resp.choices[0].message.content or ""

    async def _reflect(
        self,
        answer: str,
        message: str,
        context_results: List[Dict[str, Any]],
        sid: str
    ) -> str:
        """反思机制"""
        ctx_text = "\n".join([
            f"[{i+1}] {d.get('content', '')[:300]}"
            for i, d in enumerate(context_results[:3])
        ])

        prompt = (
            f"评估以下回答质量（0.0-1.0）：\n\n"
            f"用户问题: {message}\n\n"
            f"知识库内容:\n{ctx_text}\n\n"
            f"当前回答:\n{answer}\n\n"
            f"评分标准：是否引用了知识库内容？是否解决了问题？\n"
            f"如果评分>=0.7，回答：合格\n"
            f"如果评分<0.7，回答：不合格 + 改进建议"
        )

        try:
            review = await self._generate_response(prompt)
            if "合格" in review:
                return answer
            # 尝试改进
            improved = await self._generate_response(
                f"基于以下知识库内容，给出更好的回答：\n{ctx_text}\n\n问题：{message}"
            )
            return improved
        except Exception:
            return answer

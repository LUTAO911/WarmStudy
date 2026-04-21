# """
# Agent Core - 智能体核心编排引擎
# 版本: 3.0
# 优化: ReAct规划 + 反思机制 + LLM判断 + 流式输出
# """

import time
import uuid
import threading
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum

from agent.memory import MemoryManager
from agent.tool_registry import ToolRegistry, ToolResult, setup_builtin_tools
from agent.context import ContextManager
from agent.skills import SkillRegistry, SkillResult, setup_builtin_skills
from agent.prompts import PromptManager, DynamicPromptBuilder
from redis_client import get_redis
from agent.core.router import Router, RouteDecision
from agent.core.executor import Executor


class AgentMode(Enum):
    CHAT = "chat"
    RAG = "rag"
    AGENT = "agent"
    TOOL_CALLER = "tool_caller"


@dataclass(frozen=True)
class AgentConfig:
    name: str = "暖学帮智能助手"
    model: str = "qwen-max"
    temperature: float = 0.7
    max_tokens: int = 1500
    top_p: float = 0.8
    enable_rag: bool = True
    enable_tools: bool = True
    enable_skills: bool = True
    max_tool_calls: int = 3
    max_react_steps: int = 5
    enable_reflection: bool = True
    enable_streaming: bool = True
    reflection_threshold: float = 0.6
    system_prompt: str = ""
    hybrid_search_default: bool = True
    rerank_default: bool = True
    enable_response_cache: bool = True
    cache_ttl_seconds: int = 300
    use_qwen_judge: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "enable_rag": self.enable_rag,
            "enable_tools": self.enable_tools,
            "enable_skills": self.enable_skills,
            "max_tool_calls": self.max_tool_calls,
            "max_react_steps": self.max_react_steps,
            "enable_reflection": self.enable_reflection,
            "enable_response_cache": self.enable_response_cache,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "use_qwen_judge": self.use_qwen_judge,
            "enable_streaming": self.enable_streaming,
            "reflection_threshold": self.reflection_threshold,
            "hybrid_search_default": self.hybrid_search_default,
            "rerank_default": self.rerank_default
        }


@dataclass(frozen=True)
class AgentResponse:
    answer: str
    sources: tuple
    tool_results: tuple
    skill_results: tuple
    context_used: bool
    metadata: tuple
    execution_time: float

    def __post_init__(self) -> None:
        if isinstance(self.sources, list):
            object.__setattr__(self, "sources", tuple(self.sources))
        if isinstance(self.tool_results, list):
            object.__setattr__(self, "tool_results", tuple(self.tool_results))
        if isinstance(self.skill_results, list):
            object.__setattr__(self, "skill_results", tuple(self.skill_results))
        if isinstance(self.metadata, dict):
            object.__setattr__(self, "metadata", tuple(self.metadata.items()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "sources": list(self.sources),
            "tool_results": list(self.tool_results),
            "skill_results": list(self.skill_results),
            "context_used": self.context_used,
            "metadata": dict(self.metadata),
            "execution_time": round(self.execution_time, 3)
        }


class ReActStep:
    """ReAct 循环中的单步记录"""
    def __init__(self, step_number: int, thought: str, action: str,
                 observation: str = "", is_final: bool = False):
        self.step_number = step_number
        self.thought = thought
        self.action = action
        self.observation = observation
        self.is_final = is_final


class ResponseCache:
    """答案缓存：相同问题+session在TTL内直接返回，零API费用"""
    def __init__(self, ttl_seconds: int = 300, max_size: int = 2000):
        self._cache: Dict[str, tuple] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, query: str, session_id: str) -> str:
        import hashlib
        return hashlib.sha256(f"{session_id}:{query}".encode()).hexdigest()[:32]

    def get(self, query: str, session_id: str) -> Optional[str]:
        key = self._make_key(query, session_id)
        with self._lock:
            if key in self._cache:
                answer, ts = self._cache[key]
                if time.time() - ts < self._ttl:
                    self._hits += 1
                    return answer
                else:
                    del self._cache[key]
            self._misses += 1
            return None

    def set(self, query: str, session_id: str, answer: str) -> None:
        key = self._make_key(query, session_id)
        with self._lock:
            self._cache[key] = (answer, time.time())
            if len(self._cache) > self._max_size:
                oldest = sorted(self._cache.items(), key=lambda x: x[1][1])[:100]
                for k, _ in oldest:
                    del self._cache[k]

    def get_stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {"size": len(self._cache), "hits": self._hits, "misses": self._misses, "hit_rate": round(hit_rate, 3)}



class Agent:
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        memory_manager: Optional[MemoryManager] = None,
        tool_registry: Optional[ToolRegistry] = None,
        context_manager: Optional[ContextManager] = None,
        skill_registry: Optional[SkillRegistry] = None,
        prompt_manager: Optional[PromptManager] = None
    ) -> None:
        self.config: AgentConfig = config or AgentConfig()
        self.memory: MemoryManager = memory_manager or MemoryManager()
        self.tools: ToolRegistry = tool_registry or ToolRegistry()
        self.context: ContextManager = context_manager or ContextManager()
        self.skills: SkillRegistry = skill_registry or SkillRegistry()
        self.prompts: PromptManager = prompt_manager or PromptManager()
        self.prompt_builder: DynamicPromptBuilder = DynamicPromptBuilder(self.prompts)
        self._lock: threading.RLock = threading.RLock()
        self._query_cache: Dict[str, str] = {}
        self._cache_lock: threading.RLock = threading.RLock()
        self._response_cache: ResponseCache = ResponseCache(ttl_seconds=300, max_size=2000)
        self._use_qwen_judge: bool = True
        self._router = Router()
        self._executor = Executor()
        self._evaluator = Evaluator()
        self._setup_components()

    def _setup_components(self) -> None:
        if len(self.tools.get_all()) == 0:
            setup_builtin_tools()
        if len(self.skills.get_all()) == 0:
            setup_builtin_skills()

    # ========== 心理学模式相关常量 ==========
    PSYCHOLOGY_KEYWORDS = [
        # 情绪类
        "情绪", "心情", "难过", "开心", "生气", "害怕", "焦虑",
        "压力", "紧张", "压抑", "沮喪", "失落", "空虛", "孤独",
        "孤独感", "寂寞", "绝望", "無助",
        # 心理状态类
        "心理", "心事", "心事重重", "心裡", "内心", "心底",
        "失眠", "睡不著", "早醒", "噩夢",
        # 考试/学习压力
        "考试压力", "学习压力", "考试焦虑", "成绩下滑", "学业压力",
        # 人际关系
        "人际关系", "同学关系", "朋友关系", "亲子关系", "和家庭",
        "被孤立", "被欺负", "被排挤",
        # 自我认知
        "自我怀疑", "不自信", "自卑", "沒價值", "沒用",
        # 危机信号（最高优先级）
        "想死", "不想活", "活不下去", "死了", "輕生", "自殺",
        "自残", "割腕", "伤害自己",
    ]

    CRISIS_KEYWORDS = [
        "想死", "不想活", "活不下去", "死了算了", "死了好",
        "輕生", "自殺", "自杀", "自残", "割腕", "伤害自己",
        "上吊", "跳楼", "喝药", "一了百了", "结束生命",
    ]

    def _is_psychology_message(self, message: str) -> bool:
        """检测消息是否与心理学相关"""
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in self.PSYCHOLOGY_KEYWORDS)

    def _is_crisis_message(self, message: str) -> bool:
        """检测消息是否包含危机信号"""
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in self.CRISIS_KEYWORDS)

    def _handle_psychology_mode(self, message: str, sid: str) -> tuple:
        """
        处理心理学模式查询
        优先使用心理学工具，返回(answer, tool_results, context_used)
        """
        from agent.tools.psychology import get_psychology_tools

        pt = get_psychology_tools()
        tool_results = []

        # 1. 危机检测（最高优先级）
        crisis_result = pt.check_crisis(message)
        crisis_level = crisis_result.get("level", "safe")

        # 2. 情绪识别
        emotion_result = pt.detect_emotion(message)
        tool_results.append({
            "tool_name": "detect_emotion",
            "status": "success",
            "result": emotion_result
        })

        # 3. 如果是危机情况
        if crisis_level in ("medium", "high", "critical"):
            from agent.modules.psychology.crisis import CrisisResult, CrisisLevel
            crisis_obj = CrisisResult(
                level=CrisisLevel(crisis_level),
                signals=crisis_result.get("signals", []),
                message=crisis_result.get("message", ""),
                action=crisis_result.get("action", ""),
                hotlines=crisis_result.get("hotlines", [])
            )
            intervention = pt._crisis_detector.get_response(crisis_obj)
            tool_results.append({
                "tool_name": "check_crisis",
                "status": "success",
                "result": crisis_result
            })
            return intervention, tool_results, True

        # 4. 正常心理陪伴对话
        # 检索相关心理知识
        knowledge_result = pt.search_psychology_knowledge(
            query=message,
            user_type="student",
            n_results=3
        )
        tool_results.append({
            "tool_name": "search_psychology_knowledge",
            "status": "success",
            "result": knowledge_result
        })

        # 5. 用LLM生成共情回复（接入Qwen/Tongyi）
        emotion_label = emotion_result.get("emotion", "neutral")
        emotion_desc = emotion_result.get("description", "")
        
        # 构建知识上下文
        knowledge_text = ""
        if knowledge_result and knowledge_result.get("results"):
            for r in knowledge_result["results"]:
                knowledge_text += f"- {r.get('content', '')}\n"
        
        # 构建LLM提示词
        if knowledge_text:
            llm_prompt = f"""你是一位温暖、专业的青少年心理陪伴助手"暖暖"。请根据以下信息，用温暖共情的语气回复学生。

学生的话：{message}

检测到的情绪：{emotion_label}（{emotion_desc}）

相关心理知识：
{knowledge_text}

请结合心理知识，用温暖、理解的语气回复，回复长度适中（100-200字），体现共情和理解。如果适合，给出一些积极的建议。

回复："""
        else:
            llm_prompt = f"""你是一位温暖、专业的青少年心理陪伴助手"暖暖"。请用温暖共情的语气回复学生。

学生的话：{message}

检测到的情绪：{emotion_label}（{emotion_desc}）

请用温暖、理解的语气回复（100-200字），体现共情和关心。如果适合，给出一些积极的建议。

回复："""

        empathic_response = self._generate_response(llm_prompt)

        return empathic_response, tool_results, True

    def chat(self,
        message: str,
        session_id: Optional[str] = None,
        use_rag: Optional[bool] = None,
        use_tools: Optional[bool] = None,
        use_skills: Optional[bool] = None,
        use_hybrid: Optional[bool] = None,
        use_rerank: Optional[bool] = None,
    ) -> AgentResponse:
        start_time: float = time.time()
        sid: str = session_id or "default"

        use_rag = use_rag if use_rag is not None else self.config.enable_rag
        use_tools = use_tools if use_tools is not None else self.config.enable_tools
        use_skills = use_skills if use_skills is not None else self.config.enable_skills
        use_hybrid = use_hybrid if use_hybrid is not None else self.config.hybrid_search_default
        use_rerank = use_rerank if use_rerank is not None else self.config.rerank_default

        self.memory.add_user_message(message, {"session_id": sid})

        # ========== 心理学模式路由 ==========
        # 如果消息与心理学相关，优先使用心理学工具处理
        if self._is_psychology_message(message):
            psychology_answer, psychology_tool_results, _ = self._handle_psychology_mode(message, sid)
            self.memory.add_assistant_message(psychology_answer, {
                "session_id": sid,
                "mode": "psychology",
                "tool_calls": len(psychology_tool_results),
            })
            return AgentResponse(
                answer=psychology_answer,
                sources=(),
                tool_results=tuple(psychology_tool_results),
                skill_results=(),
                context_used=True,
                metadata=tuple({
                    "session_id": sid,
                    "mode": "psychology",
                    "need_rag": False,
                    "need_tools": True,
                    "psychology_mode": True,
                }.items()),
                execution_time=time.time() - start_time,
            )

        # Step 1: LLM 判断是否需要 RAG / Tools
        need_rag, need_tools = self._llm_judge_needs(message, sid)

        context_results: List[Dict[str, Any]] = []
        if use_rag and need_rag:
            context_results = self._retrieve_context(
                message, sid, n_results=5,
                use_hybrid=use_hybrid, rerank=use_rerank
            )
            if context_results:
                self.context.add_knowledge_context(sid, context_results, message)

        # Step 2: ReAct 多步规划 + 执行
        react_steps: List[ReActStep] = []
        tool_results: List[ToolResult] = []
        skill_results: List[SkillResult] = []

        if use_tools and need_tools:
            react_steps, tool_results = self._react_loop(
                message=message,
                sid=sid,
                context_results=context_results,
                max_steps=self.config.max_react_steps,
            )
            for tr in tool_results:
                self.context.add_entry(
                    content_type="tool",
                    content=tr.formatted_result,
                    relevance_score=0.9,
                    source=tr.tool_name,
                )

        if use_skills and need_rag:
            skill_results = self._execute_skills(message)
            for sr in skill_results:
                self.context.add_skill_context(sid, sr.skill_name, str(sr.output))

        # Step 3: 构建 Prompt 并生成回答
        prompt: str = self._build_prompt(
            message=message,
            session_id=sid,
            context_results=context_results,
            tool_results=tool_results,
            skill_results=skill_results,
            react_steps=react_steps,
        )

        answer: str = self._generate_response(prompt)

        # Step 4: 反思机制
        if self.config.enable_reflection and len(context_results) > 0:
            answer, is_good = self._reflect(
                answer=answer,
                message=message,
                context_results=context_results,
                sid=sid,
            )
            if not is_good:
                better_results = self._retrieve_context(
                    message, sid, n_results=8,
                    use_hybrid=use_hybrid, rerank=True,
                )
                if better_results != context_results:
                    enhanced_prompt = self._build_prompt(
                        message=message,
                        session_id=sid,
                        context_results=better_results,
                        tool_results=tool_results,
                        skill_results=skill_results,
                        react_steps=react_steps,
                        reflection_note="[Previous answer was incomplete, please improve based on new context]",
                    )
                    answer = self._generate_response(enhanced_prompt)
                    context_results = better_results

        self.memory.add_assistant_message(answer, {
            "session_id": sid,
            "tool_calls": len(tool_results),
            "skill_calls": len(skill_results),
            "react_steps": len(react_steps),
        })

        sources: List[Dict[str, Any]] = []
        if context_results:
            for doc in context_results[:3]:
                sources.append({
                    "content": doc.get("content", "")[:150] + "...",
                    "source": doc.get("source", ""),
                    "page": doc.get("page", ""),
                    "similarity": doc.get("similarity", 0),
                    "combined_score": doc.get("combined_score", doc.get("similarity", 0)),
                })

        return AgentResponse(
            answer=answer,
            sources=tuple(sources),
            tool_results=tuple(tr.to_dict() for tr in tool_results),
            skill_results=tuple(sr.to_dict() for sr in skill_results),
            context_used=len(context_results) > 0,
            metadata=tuple({
                "session_id": sid,
                "mode": "chat",
                "search_mode": "hybrid" if use_hybrid else "vector",
                "react_steps": len(react_steps),
                "need_rag": need_rag,
                "need_tools": need_tools,
                "config": self.config.to_dict(),
            }.items()),
            execution_time=time.time() - start_time,
        )

    def _llm_judge_needs(self, message: str, sid: str) -> tuple:
        """用 LLM 智能判断是否需要 RAG / Tools，替代简单关键词匹配"""
        judge_prompt = (
            "你是一个任务规划助手。判断用户问题是否需要以下能力，只需回答是或否：\n\n"
            "问题: " + message + "\n\n"
            "判断标准：\n"
            "- 需要 RAG（知识库）：问题涉及专业知识、数据、文档、特定领域内容\n"
            "- 需要 Tools（工具调用）：问题需要实时信息（时间/天气）、计算、搜索网页\n\n"
            "回答格式：\nRAG:是/否\nTools:是/否"
        )
        try:
            result = self._generate_response(judge_prompt).strip()
            need_rag = "RAG:是" in result or ("RAG" in result and "是" in result)
            need_tools = "Tools:是" in result or ("Tools" in result and "是" in result)
            if "是" not in result and "否" not in result:
                need_rag = self._keyword_rag(message)
                need_tools = self._keyword_tools(message)
            return need_rag, need_tools
        except Exception:
            return self._keyword_rag(message), self._keyword_tools(message)

    def _keyword_rag(self, message: str) -> bool:
        keywords = ["什么", "如何", "怎么", "为什么", "原因", "定义", "概念",
                     "解释", "区别", "哪个", "哪些", "知识", "文档", "规则"]
        return any(k in message for k in keywords)

    def _keyword_tools(self, message: str) -> bool:
        keywords = ["计算", "时间", "现在", "几点", "日期", "搜索",
                     "查询", "查一下", "帮我找", "天气",
                     # 心理学相关
                     "情绪", "心情", "压力", "焦虑", "难过", "开心",
                     "心理", "心理问题", "心理咨询"]
        return any(k in message for k in keywords)

    def _react_loop(self, message: str, sid: str,
                     context_results: List[Dict[str, Any]],
                     max_steps: int = 5) -> tuple:
        """ReAct (Reasoning + Acting) 多步规划循环"""
        steps: List[ReActStep] = []
        accumulated = ""

        if context_results:
            ctx = "\n".join([
                f'[{i+1}] {d.get("content", "")[:200]}'
                for i, d in enumerate(context_results[:3])
            ])
            accumulated = "\n已有知识库上下文:\n" + ctx

        for step_num in range(1, max_steps + 1):
            thought = self._react_think(message, accumulated, steps)

            if self._is_final_answer(thought):
                steps.append(ReActStep(step_num, thought, "FINAL_ANSWER", is_final=True))
                break

            action, action_input = self._parse_action(thought)
            obs = self._execute_action(action, action_input, sid)
            accumulated += f"\n[Step {step_num}] {action}: {obs[:300]}"
            steps.append(ReActStep(step_num, thought, f"{action}({action_input})", obs))

        # 收集工具结果
        tool_results: List[ToolResult] = []
        for step in steps:
            if step.action.startswith("tool:"):
                tool_name = step.action[5:].split("(")[0]
                try:
                    tr = self.tools.execute(tool_name, query=step.observation)
                    if tr.is_success:
                        tool_results.append(tr)
                except Exception:
                    pass

        return steps, tool_results

    def _react_think(self, message: str, context: str,
                     prev_steps: List[ReActStep]) -> str:
        """让 LLM 思考下一步该做什么"""
        history = ""
        if prev_steps:
            history = "上一步执行结果:\n" + "\n".join([
                f"Step {s.step_number}: {s.action} -> {s.observation[:200]}"
                for s in prev_steps
            ])

        prompt = (
            "你是一个智能助手，正在解决用户问题。\n\n"
            "用户问题: " + message + "\n"
            + (context + "\n\n" if context else "\n")
            + (history + "\n\n" if history else "\n")
            + "你需要决定下一步做什么。选项：\n"
            + "1. FINAL_ANSWER - 你已经收集足够信息，可以直接回答了\n"
            + "2. rag_search:<搜索query> - 需要在知识库中检索\n"
            + "3. tool:<工具名>:<参数> - 需要调用特定工具\n\n"
            + "直接给出下一步行动，不要解释。格式：FINAL_ANSWER 或 rag_search:xxx 或 tool:工具名:参数"
        )
        try:
            return self._generate_response(prompt).strip()
        except Exception:
            return "FINAL_ANSWER"

    def _is_final_answer(self, thought: str) -> bool:
        t = thought.lower().strip()
        return (
            "final" in t or
            "结束" in thought or
            t.startswith("final_answer") or
            ("不再需要" in thought or "不需要" in thought)
        )

    def _parse_action(self, thought: str) -> tuple:
        """从 LLM 思考中解析出行动类型和参数"""
        t = thought.strip()

        if "rag_search:" in t:
            parts = t.split("rag_search:", 1)
            q = parts[1].strip()
            # remove surrounding quotes if any
            if len(q) >= 2 and q[0] in (chr(34), chr(39)) and q[-1] == q[0]:
                q = q[1:-1]
            return ("rag_search", q)

        if "tool:" in t:
            parts = t.split("tool:", 1)
            rest = parts[1].strip()
            colon = rest.find(":")
            if colon > 0:
                tool_name = rest[:colon].strip()
                params_str = rest[colon+1:].strip()
                try:
                    params = json.loads(params_str)
                except Exception:
                    params = {"query": params_str}
                return ("tool:" + tool_name, params)
            return ("tool:" + rest, {})

        return ("final", "")

    def _execute_action(self, action: str, action_input: Any, sid: str) -> str:
        """执行具体的行动"""
        if action == "rag_search":
            query = str(action_input) if action_input else ""
            results = self._retrieve_context(query, sid, n_results=3, use_hybrid=True, rerank=False)
            if results:
                return "\n".join([f'[{i+1}] {r.get("content", "")[:200]}'
                                   for i, r in enumerate(results)])
            return "未找到相关信息"

        if action.startswith("tool:"):
            tool_name = action[5:]
            params = action_input if isinstance(action_input, dict) else {"query": str(action_input)}
            try:
                result = self.tools.execute(tool_name, **params)
                return result.formatted_result if result.is_success else f"工具执行失败: {result.error}"
            except Exception as e:
                return f"工具执行异常: {str(e)}"

        return "无法理解行动指令"

    def _reflect(self, answer: str, message: str,
                 context_results: List[Dict[str, Any]], sid: str) -> tuple:
        """反思回答质量，检查是否引用了知识库、是否解决了问题"""
        ctx_text = "\n".join([
            f'[{i+1}] {d.get("content", "")[:300]}'
            for i, d in enumerate(context_results[:3])
        ])

        prompt = (
            "你是一个回答质量评审员。请评估以下回答质量：\n\n"
            "用户问题: " + message + "\n\n"
            "知识库参考内容:\n" + ctx_text + "\n\n"
            "当前回答:\n" + answer + "\n\n"
            "评分标准（0.0-1.0）：\n"
            "1. 回答是否引用了知识库内容？\n"
            "2. 回答是否解决了用户问题？\n"
            "3. 是否有重要遗漏？\n\n"
            "如果评分>=0.7，回答：合格\n"
            "如果评分<0.7，回答：不合格 + 具体改进方向"
        )
        try:
            review = self._generate_response(prompt).strip()
            nums = re.findall(r"0\.[0-9]", review)
            score = float(nums[0]) if nums else 0.5
            if score >= self.config.reflection_threshold:
                return answer, True
            # 不合格，尝试改进
            improved = self._generate_response(
                "用户问题: " + message + "\n\n参考内容:\n" + ctx_text + "\n\n请根据以上内容，给出更完整准确专业的回答："
            )
            return improved, False
        except Exception:
            return answer, True

    def _retrieve_context(self, query: str, sid: str,
                         n_results: int = 5,
                         use_hybrid: bool = True,
                         rerank: bool = True) -> List[Dict[str, Any]]:
        """知识库检索（带缓存，避免同一 query 重复检索）"""
        cache_key = f"{query}:{n_results}:{use_hybrid}:{rerank}"
        try:
            if use_hybrid:
                from vectorstore import query_with_hybrid_search
                results = query_with_hybrid_search(
                    query_text=query,
                    n_results=n_results,
                    rerank=rerank,
                )
            else:
                from vectorstore import query_chroma
                raw = query_chroma(
                    query_text=query,
                    n_results=n_results,
                    persist_dir="data/chroma",
                    collection_name="knowledge_base",
                )
                results = []
                for doc, meta, dist in raw:
                    results.append({
                        "content": doc,
                        "source": str(meta.get("source", "")),
                        "page": meta.get("page", ""),
                        "similarity": round(1 - dist, 4),
                    })

            with self._cache_lock:
                self._query_cache[cache_key] = "1"
                if len(self._query_cache) > 500:
                    for k in list(self._query_cache.keys())[:100]:
                        del self._query_cache[k]
            return results
        except Exception:
            return []

    def _execute_tools(self, message: str) -> List[ToolResult]:
        results: List[ToolResult] = []
        msg_lower = message.lower()

        if any(k in msg_lower for k in ["搜索", "search", "查询"]):
            if any(k in message for k in ["知识", "库", "document"]):
                tr = self.tools.execute("search_knowledge_base", query=message, n_results=5)
                results.append(tr)

        all_tools = self.tools.get_all()
        for tool_name, tool_schema in all_tools.items():
            desc_words = tool_schema.description.lower().split()
            if any(k in msg_lower for k in desc_words):
                if tool_name not in [r.tool_name for r in results]:
                    try:
                        tr = self.tools.execute(tool_name, query=message)
                        results.append(tr)
                    except Exception:
                        pass
        return results

    def _execute_skills(self, message: str) -> List[SkillResult]:
        results: List[SkillResult] = []
        msg_lower = message.lower()

        skill_map = {
            "summarize": ["总结", "摘要", "summarize"],
            "extract_keywords": ["关键词", "提取"],
            "translate": ["翻译", "translate"],
        }
        for skill_name, keywords in skill_map.items():
            if any(k in msg_lower for k in keywords):
                try:
                    sr = self.skills.execute(skill_name, {"text": message})
                    results.append(sr)
                except Exception:
                    pass
        return results

    def _build_prompt(self, message: str, session_id: str,
                      context_results: List[Dict[str, Any]],
                      tool_results: List[ToolResult],
                      skill_results: List[SkillResult],
                      react_steps: Optional[List[ReActStep]] = None,
                      reflection_note: str = "") -> str:
        history = self.memory.get_conversation_history(limit=10)
        ctx = self.context.build_context_prompt(session_id, max_entries=10)

        if context_results:
            parts = []
            for i, doc in enumerate(context_results[:3]):
                score = doc.get("combined_score", doc.get("similarity", 0))
                parts.append(f'[知识库 {i+1}] (相关度: {score:.2f})\n{doc["content"][:500]}')
            ctx += "\n\n" + "\n\n".join(parts)

        if tool_results:
            ctx += "\n\n[工具执行结果]\n" + "\n".join([tr.formatted_result for tr in tool_results])

        if skill_results:
            ctx += "\n\n[技能执行结果]\n" + "\n".join([f"- {sr.skill_name}: {sr.output}" for sr in skill_results])

        if react_steps:
            steps_text = "\n".join([
                f"Step {s.step_number}: 思考={s.thought[:100]} | 行动={s.action} | 结果={s.observation[:100]}"
                for s in react_steps if not s.is_final
            ])
            ctx += f"\n\n[规划步骤]\n{steps_text}"

        if reflection_note:
            ctx += f"\n\n[反思提示] {reflection_note}"

        system_prompt = self.config.system_prompt or self.prompts.render(
            "system_prompt",
            current_time=time.strftime("%Y-%m-%d %H:%M:%S")
        )

        return (
            f"{system_prompt}\n\n"
            f"Conversation History:\n{history or 'No previous messages'}\n\n"
            + (f"Additional Context:\n{ctx}\n\n" if ctx else "\n")
            + f"User: {message}\n\nAssistant:"
        )

    def _generate_response(self, prompt: str,
                           stream_callback: Optional[Callable] = None) -> str:
        try:
            import os
            chat_model = os.getenv("CHAT_MODEL", "minimax")
            api_key = self._get_api_key()
            if chat_model == "minimax":
                return self._generate_minimax_response(prompt, api_key, stream_callback)
            else:
                return self._generate_dashscope_response(prompt, api_key)
        except Exception as e:
            return f"Error generating response: {str(e)}"

    def _generate_minimax_response(self, prompt: str, api_key: str,
                                   stream_callback: Optional[Callable] = None) -> str:
        try:
            import requests
            url = "https://api.minimaxi.com/anthropic/v1/messages"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            data = {
                "model": "MiniMax-M2.7",
                "max_tokens": self.config.max_tokens or 1024,
                "temperature": self.config.temperature,
                "messages": [{"role": "user", "content": prompt}]
            }

            if self.config.enable_streaming and stream_callback:
                data["stream"] = True
                resp = requests.post(url, headers=headers, json=data, timeout=120, stream=True)
                if resp.status_code == 200:
                    full_text = ""
                    for line in resp.iter_lines():
                        if line:
                            line = line.decode("utf-8", errors="replace")
                            if line.startswith("data:"):
                                chunk = line[5:].strip()
                                if chunk == "[DONE]":
                                    break
                                try:
                                    chunk_data = json.loads(chunk)
                                    content = chunk_data.get("content", [])
                                    for block in content:
                                        if block.get("type") == "text":
                                            txt = block.get("text", "")
                                            full_text += txt
                                            stream_callback(txt)
                                except Exception:
                                    pass
                    return full_text

            resp = requests.post(url, headers=headers, json=data, timeout=60)
            if resp.status_code == 200:
                result = resp.json()
                content = result.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if block.get("type") == "text":
                            return block.get("text", "")
                return str(result)
            elif resp.status_code == 401:
                return "Error: MiniMax API unauthorized - check API key"
            elif resp.status_code == 429:
                return "Error: MiniMax API rate limited - please retry later"
            else:
                return f"Error: MiniMax API returned {resp.status_code}: {resp.text[:300]}"
        except Exception as e:
            return f"Error generating MiniMax response: {str(e)}"

    def _generate_dashscope_response(self, prompt: str, api_key: str) -> str:
        try:
            from dashscope import Generation
            import dashscope
            dashscope.api_key = api_key
            resp = Generation.call(
                model=self.config.model,
                prompt=prompt,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                max_tokens=self.config.max_tokens,
                result_format="message",
            )
            if resp.status_code != 200:
                return f"Error: {resp.message}"
            return resp.output["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error generating DashScope response: {str(e)}"

    def _get_api_key(self) -> str:
        import os
        chat_model = os.getenv("CHAT_MODEL", "minimax")
        if chat_model == "minimax":
            return os.getenv("MINIMAX_API_KEY", os.getenv("DASHSCOPE_API_KEY", ""))
        return os.getenv("DASHSCOPE_API_KEY", "")

    def get_session_info(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = session_id or "default"
        return {
            "session_id": sid,
            "memory": self.memory.get_session_summary(),
            "context": self.context.get_context_stats(sid),
            "config": self.config.to_dict(),
        }

    def reset_session(self, session_id: Optional[str] = None) -> bool:
        sid = session_id or "default"
        self.memory.clear_short_term()
        self.context.clear_session(sid)
        return True



class Evaluator:
    """
    评审器：用 Qwen-Turbo 做质量评估，便宜快
    """
    def __init__(self):
        self._redis = get_redis()

    def reflect(self, answer, message, context_results):
        ctx = "\n".join([
            "[%d] %s" % (i+1, d.get("content", "")[:300])
            for i, d in enumerate(context_results[:3])
        ])
        try:
            from openai import OpenAI
            import os
            client = OpenAI(
                api_key=os.getenv("DASHSCOPE_API_KEY", ""),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            resp = client.chat.completions.create(
                model="qwen-turbo",
                messages=[{"role": "user", "content":
                    "\u7528\u6237\u95ee\u9898: %s\n\u53c2\u8003: %s\n\u8bf7\u7ed9\u51fa\u66f4\u5b8c\u6574\u7684\u56de\u7b54:" % (message, ctx[:500])}],
                max_tokens=512,
                temperature=0.1,
            )
            improved = resp.choices[0].message.content or ""
            return (improved if improved else answer, improved != "")
        except Exception:
            return (answer, True)


class AgentManager:
    _instance: Optional["AgentManager"] = None
    _lock_class: threading.RLock = threading.RLock()

    def __new__(cls) -> "AgentManager":
        if cls._instance is None:
            with cls._lock_class:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self._agents: Dict[str, Agent] = {}
        self._lock: threading.RLock = threading.RLock()

    def create_agent(self, agent_id: Optional[str] = None,
                     config: Optional[AgentConfig] = None) -> Agent:
        aid = agent_id or uuid.uuid4().hex[:12]
        with self._lock:
            if aid in self._agents:
                return self._agents[aid]
            agent = Agent(config=config)
            self._agents[aid] = agent
            return agent

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        with self._lock:
            return self._agents.get(agent_id)

    def delete_agent(self, agent_id: str) -> bool:
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                return True
            return False

    def list_agents(self) -> List[str]:
        with self._lock:
            return list(self._agents.keys())

    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {aid: a.config.to_dict() for aid, a in self._agents.items()}

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock_class:
            cls._instance = None

# 暖学帮 - 智能体架构重设计文档

**版本**: v5.0
**架构师**: 沫汐 🌸
**日期**: 2026-04-12
**参赛赛事**: 2026广东省大学生计算机设计大赛 · 本科赛道 · 人工智能应用

---

## 一、架构问题诊断

### 1.1 当前架构问题总结

| 问题领域 | 问题描述 | 影响 |
|---------|---------|------|
| **Agent核心** | `agent.py` 约1000行，职责过于集中 | 难以维护、测试、扩展 |
| **Context管理** | 缺乏统一的生命周期管理和数据流转规范 | 上下文滥用、内存泄漏 |
| **记忆系统** | 短期/长期记忆分离但检索能力弱 | 对话连贯性差 |
| **情绪感知** | 心理学模式通过关键词匹配触发，不够精准 | 情绪识别准确率低 |
| **工作流引擎** | 简单ReAct循环，无可视化、无优先级管理 | 复杂场景处理能力不足 |
| **工具集成** | 工具选择通过关键词匹配，动态性差 | 工具调用准确率低 |
| **心理模块** | 人格模拟、情感反馈机制缺失 | 共情效果有限 |
| **RAG调用** | 接口不统一，无标准化查询流程 | 检索效率波动大 |
| **API接口** | 缺乏完整文档和错误处理规范 | 前后端联调困难 |
| **性能优化** | 缓存策略分散，无系统性优化 | 响应延迟不稳定 |

### 1.2 重设计目标

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              重设计目标                                      │
│                                                                            │
│  1. 模块化重构：将1000行agent.py拆分为独立职责模块                            │
│  2. 清晰的数据流：Context生命周期管理、标准化数据流转                         │
│  3. 分层记忆：用户画像、情感历史、对话记忆三层分离                             │
│  4. 精准情绪感知：规则+LLM混合判断，提升准确率                               │
│  5. 可视化工作流：任务分解、优先级、执行监控                                  │
│  6. 动态工具选择：基于语义的工具匹配，参数自适应                              │
│  7. 完整心理模拟：人格特征、情感反馈、行为模式                                │
│  8. 标准化RAG：统一接口、智能调度、效率优化                                  │
│  9. 完整API规范：OpenAPI文档、完整错误处理                                    │
│  10. 系统性能优化：缓存、查询、资源分配                                       │
│                                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、系统整体架构

### 2.1 架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户交互层 (WeChat MiniApp)                      │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐   │
│   │ 学生端   │  │ 家长端   │  │ 教师端   │  │ 学校管理 │  │ AI伙伴(暖暖)   │   │
│   │ 心理陪伴  │  │ 知识+监测 │  │ 班级看板  │  │ 数据总览  │  │ 情感可视化     │   │
│   └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────────┬────────┘   │
└────────┼───────────┼────────────┼────────────┼─────────────────┼─────────────┘
         │           │            │            │                 │
         └───────────┴────────────┴────────────┴─────────────────┘
                                    │
                           ┌────────▼────────┐
                           │   API Gateway   │
                           │   (FastAPI)     │
                           │  • 认证鉴权     │
                           │  • 限流熔断     │
                           │  • 请求路由     │
                           └────────┬────────┘
                                    │
┌───────────────────────────────────┼─────────────────────────────────────────┐
│                          Agent 核心编排层                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                         ┌──────────────────┐                           │  │
│  │                         │   Orchestrator   │ ← 核心调度器              │  │
│  │                         │   (主编排引擎)   │                           │  │
│  │                         └────────┬─────────┘                           │  │
│  │                                  │                                     │  │
│  │   ┌──────────────┐  ┌──────────┴──────────┐  ┌──────────────┐       │  │
│  │   │ Intent Router │  │ Context Manager    │  │ Workflow Eng │       │  │
│  │   │  意图分类      │  │  上下文管理        │  │  工作流引擎   │       │  │
│  │   └──────────────┘  └─────────────────────┘  └──────────────┘       │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│  ┌─────────────────────────────────┴────────────────────────────────────┐  │
│  │                          Memory Layer (分层记忆)                        │  │
│  │  ┌─────────┐  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐   │  │
│  │  │对话记忆  │  │ 用户画像    │  │ 情感历史      │  │ 知识记忆       │   │  │
│  │  │Session  │  │ Profile     │  │ Emotion      │  │ Long-term KB  │   │  │
│  │  └─────────┘  └─────────────┘  └──────────────┘  └───────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│  ┌─────────────────────────────────┴────────────────────────────────────┐  │
│  │                       Psychology Module (心理模块)                      │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │  │
│  │  │Emotion Det. │  │ Crisis Detect │  │ Empathic Gen │  │ Personality│  │  │
│  │  │ 情绪识别     │  │  危机检测      │  │  共情生成     │  │  人格特征  │  │  │
│  │  └─────────────┘  └──────────────┘  └──────────────┘  └──────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│  ┌─────────────────────────────────┴────────────────────────────────────┐  │
│  │                        Tool Layer (工具层)                             │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │  │
│  │  │Search Tool  │  │ Math Tool    │  │ Time Tool     │  │ Web Tool │  │  │
│  │  │ 知识检索     │  │  数学计算     │  │  时间查询     │  │ 网页搜索  │  │  │
│  │  └─────────────┘  └──────────────┘  └──────────────┘  └──────────┘  │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │  │
│  │  │Psych. Tool  │  │ Educ. Tool   │  │ Report Tool  │  │ Notify   │  │  │
│  │  │ 心理支持     │  │  教育辅助     │  │  报告生成     │  │  预警通知  │  │  │
│  │  └─────────────┘  └──────────────┘  └──────────────┘  └──────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│  ┌─────────────────────────────────┴────────────────────────────────────┐  │
│  │                     RAG Knowledge Layer (知识库层)                      │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐                  │  │
│  │  │ ChromaDB    │  │ BM25Indexer  │  │ Reranker     │                  │  │
│  │  │ 向量存储     │  │  文本检索     │  │  重排模型     │                  │  │
│  │  └─────────────┘  └──────────────┘  └──────────────┘                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
                                    │
                           ┌────────▼────────┐
                           │   LLM Layer     │
                           │  通义千问API     │
                           │  MiniMax API    │
                           └─────────────────┘
```

---

## 三、模块详细设计

### 3.1 Agent 核心模块化重构

#### 3.1.1 模块职责划分

```
agent/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── orchestrator.py      # 【NEW】主编排引擎 - 协调所有模块
│   ├── intent_router.py      # 【NEW】意图路由 - 替代当前的关键词匹配
│   ├── workflow_engine.py    # 【NEW】工作流引擎 - 任务分解与执行
│   └── response_builder.py   # 【NEW】响应构建器 - 组装最终响应
├── memory/
│   ├── __init__.py
│   ├── dialogue_memory.py    # 【REFACTOR】对话记忆 - 短期会话
│   ├── user_profile.py       # 【NEW】用户画像 - 用户特征长期记忆
│   ├── emotion_history.py    # 【NEW】情感历史 - 情绪变化追踪
│   └── knowledge_memory.py   # 【NEW】知识记忆 - 事实性知识
├── context/
│   ├── __init__.py
│   ├── context_manager.py    # 【REFACTOR】上下文管理器
│   ├── context_lifecycle.py  # 【NEW】上下文生命周期
│   └── context_pipeline.py   # 【NEW】上下文处理流水线
├── psychology/
│   ├── __init__.py
│   ├── emotion_detector.py   # 【REFACTOR】情绪识别
│   ├── crisis_detector.py   # 【REFACTOR】危机检测
│   ├── empathic_generator.py # 【REFACTOR】共情生成
│   ├── personality_engine.py  # 【NEW】人格特征引擎
│   └── behavior_adapter.py   # 【NEW】行为模式适配
├── tools/
│   ├── __init__.py
│   ├── base/
│   │   ├── __init__.py
│   │   ├── base_tool.py      # 工具基类
│   │   └── tool_result.py    # 标准化结果格式
│   ├── registry.py           # 【REFACTOR】工具注册中心
│   ├── selector.py           # 【NEW】动态工具选择器
│   └── adapter.py            # 【NEW】参数适配器
├── rag/
│   ├── __init__.py
│   ├── query_router.py       # 【NEW】查询路由
│   ├── hybrid_retriever.py   # 【NEW】混合检索器
│   ├── reranker.py          # 【NEW】重排器
│   └── cache_manager.py      # 【NEW】检索缓存管理
└── api/
    ├── __init__.py
    ├── routes.py             # 【REFACTOR】API路由
    ├── schemas.py            # 【NEW】Pydantic请求/响应模型
    ├── errors.py             # 【NEW】统一错误处理
    └── docs.py               # 【NEW】OpenAPI文档
```

#### 3.1.2 核心接口定义

```python
# ========== orchestrator.py - 主编排引擎 ==========
"""
智能体主编排器
职责：
1. 接收用户消息，协调各模块处理
2. 管理对话生命周期
3. 构建最终响应
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

class ConversationMode(Enum):
    """对话模式"""
    CHAT = "chat"              # 普通聊天
    PSYCHOLOGY = "psychology"  # 心理陪伴
    EDUCATION = "education"    # 教育辅导
    CRISIS = "crisis"          # 危机干预

@dataclass
class OrchestratorConfig:
    """编排器配置"""
    enable_psychology: bool = True
    enable_rag: bool = True
    enable_tools: bool = True
    max_workflow_steps: int = 5
    response_timeout: float = 30.0
    cache_enabled: bool = True

@dataclass
class UserMessage:
    """用户消息"""
    content: str
    session_id: str
    user_id: Optional[str] = None
    user_type: str = "student"  # student/parent/teacher
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentResponse:
    """智能体响应"""
    content: str
    mode: ConversationMode
    emotion: Optional[Dict[str, Any]] = None
    crisis_level: Optional[str] = None
    sources: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0

class Orchestrator:
    """
    主编排器
    
    工作流程：
    1. 接收用户消息
    2. 路由到对应模式（心理学/教育/普通）
    3. 并行执行上下文检索、工具调用、记忆读取
    4. 汇聚结果，构建响应
    5. 更新记忆和上下文
    """
    
    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        intent_router: Optional["IntentRouter"] = None,
        context_manager: Optional["ContextManager"] = None,
        memory_manager: Optional["MemoryManager"] = None,
        psychology_module: Optional["PsychologyModule"] = None,
        tool_registry: Optional["ToolRegistry"] = None,
        rag_engine: Optional["RAGEngine"] = None,
        llm_provider: Optional["LLMProvider"] = None,
    ):
        self.config = config or OrchestratorConfig()
        self.intent_router = intent_router
        self.context_manager = context_manager
        self.memory_manager = memory_manager
        self.psychology_module = psychology_module
        self.tool_registry = tool_registry
        self.rag_engine = rag_engine
        self.llm = llm_provider
        
        # 初始化各模块
        self._initialize_modules()
    
    def _initialize_modules(self) -> None:
        """初始化所有子模块"""
        if self.intent_router is None:
            from agent.core.intent_router import IntentRouter
            self.intent_router = IntentRouter()
        
        if self.context_manager is None:
            from agent.context.context_manager import ContextManager
            self.context_manager = ContextManager()
        
        if self.memory_manager is None:
            from agent.memory.unified_memory import UnifiedMemoryManager
            self.memory_manager = UnifiedMemoryManager()
        
        if self.psychology_module is None:
            from agent.psychology.psychology_module import PsychologyModule
            self.psychology_module = PsychologyModule()
        
        if self.tool_registry is None:
            from agent.tools.registry import ToolRegistry
            self.tool_registry = ToolRegistry()
        
        if self.rag_engine is None:
            from agent.rag.rag_engine import RAGEngine
            self.rag_engine = RAGEngine()
    
    async def chat(self, message: UserMessage) -> AgentResponse:
        """
        处理对话请求
        
        Args:
            message: 用户消息
            
        Returns:
            AgentResponse: 智能体响应
        """
        import time
        start_time = time.time()
        
        # 1. 意图路由 - 确定对话模式
        intent = await self.intent_router.route(message.content)
        
        # 2. 并行执行：记忆读取 + RAG检索 + 工具准备
        task_futures = {
            "memory": self._read_memory(message),
            "context": self._read_context(message),
        }
        
        if intent.need_rag:
            task_futures["rag"] = self._rag_retrieve(message, intent)
        
        if intent.need_tools:
            task_futures["tools"] = self._prepare_tools(message)
        
        # 执行所有并行任务
        import asyncio
        results = await asyncio.gather(
            *[f for f in task_futures.values()],
            return_exceptions=True
        )
        
        # 3. 心理学模式处理
        if intent.mode == ConversationMode.PSYCHOLOGY:
            psych_result = await self._handle_psychology(message)
            # 危机等级处理
            if psych_result.crisis_level in ("high", "critical"):
                return await self._handle_crisis(message, psych_result, start_time)
        
        # 4. 构建Prompt
        prompt = await self._build_prompt(message, intent, results)
        
        # 5. LLM生成
        response_content = await self._generate_response(prompt)
        
        # 6. 反思机制
        response_content = await self._reflect(message, response_content, results)
        
        # 7. 更新记忆
        await self._update_memory(message, response_content)
        
        # 8. 构建最终响应
        return AgentResponse(
            content=response_content,
            mode=intent.mode,
            emotion=results.get("emotion"),
            sources=results.get("sources", []),
            tool_calls=results.get("tool_results", []),
            metadata=intent.metadata,
            execution_time=time.time() - start_time
        )
    
    async def _handle_psychology(self, message: UserMessage) -> "PsychologyResult":
        """处理心理学模式"""
        # 情绪识别
        emotion = await self.psychology_module.detect_emotion(message.content)
        
        # 危机检测
        crisis = await self.psychology_module.check_crisis(message.content)
        
        # 检索相关心理知识
        knowledge = await self.psychology_module.search_knowledge(
            message.content,
            user_type=message.user_type
        )
        
        return PsychologyResult(
            emotion=emotion,
            crisis=crisis,
            knowledge=knowledge
        )
```

```python
# ========== intent_router.py - 意图路由 ==========
"""
Intent Router - 智能意图识别与路由
替代当前的关键词匹配方式，使用LLM进行精准判断
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
import time

class IntentType(Enum):
    """意图类型"""
    GENERAL_CHAT = "general_chat"       # 一般聊天
    PSYCHOLOGY_SUPPORT = "psychology"   # 心理支持
    EDUCATION = "education"             # 教育辅导
    KNOWLEDGE_QUERY = "knowledge"      # 知识查询
    CRISIS_INTERVENTION = "crisis"      # 危机干预
    TOOL_USE = "tool_use"              # 工具调用

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
    user_type: str
    emotion_state: Optional[Dict] = None
    recent_intents: List[Intent] = field(default_factory=list)
    context_window: List[str] = field(default_factory=list)

class IntentRouter:
    """
    意图路由器
    
    判断逻辑：
    1. 危机关键词检测 → 最高优先级
    2. 心理学关键词 + 情绪检测 → 心理学模式
    3. 教育相关关键词 → 教育模式
    4. 知识查询类 → RAG模式
    5. 其他 → 普通聊天
    """
    
    # 危机关键词（最高优先级）
    CRISIS_KEYWORDS = [
        "想死", "不想活", "活不下去", "死了", "輕生", "自殺",
        "自残", "割腕", "伤害自己", "上吊", "跳楼", "喝药",
    ]
    
    # 心理学关键词
    PSYCHOLOGY_KEYWORDS = [
        "情绪", "心情", "难过", "开心", "生气", "害怕", "焦虑",
        "压力", "紧张", "压抑", "沮喪", "失落", "失眠",
        "心理", "心事", "内心", "人际关系", "亲子关系",
        "考试压力", "学习压力", "被孤立", "被欺负",
        "自卑", "不自信", "绝望", "無助",
    ]
    
    # 教育关键词
    EDUCATION_KEYWORDS = [
        "作业", "考试", "学习", "题目", "讲解", "辅导",
        "数学", "语文", "英语", "物理", "化学",
        "学习计划", "学习方法", "成绩",
    ]
    
    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self._cache: Dict[str, Intent] = {}
        self._cache_ttl = 60  # 缓存60秒
    
    async def route(self, message: str, context: Optional[RouteContext] = None) -> Intent:
        """
        智能路由判断
        
        Args:
            message: 用户消息
            context: 路由上下文（可选）
            
        Returns:
            Intent: 意图识别结果
        """
        # 1. 检查缓存
        cache_key = hash(message)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached.metadata.get("cached_at", 0) < self._cache_ttl:
                return cached
        
        # 2. 危机检测（最高优先级）
        crisis_intent = self._check_crisis(message)
        if crisis_intent:
            return crisis_intent
        
        # 3. 心理学检测
        psych_intent = await self._check_psychology(message, context)
        if psych_intent.confidence > 0.7:
            return psych_intent
        
        # 4. 教育检测
        edu_intent = self._check_education(message)
        if edu_intent.confidence > 0.6:
            return edu_intent
        
        # 5. LLM辅助判断（兜底）
        llm_intent = await self._llm_route(message, context)
        
        # 6. 缓存结果
        self._cache[cache_key] = llm_intent
        
        return llm_intent
    
    def _check_crisis(self, message: str) -> Optional[Intent]:
        """危机检测"""
        msg_lower = message.lower()
        
        # 否定词检测
        negations = ["不想", "不会", "没有想", "不是想", "开个玩笑"]
        for kw in self.CRISIS_KEYWORDS:
            if kw in msg_lower:
                # 检查前面是否有否定词
                idx = msg_lower.find(kw)
                prefix = msg_lower[max(0, idx-20):idx]
                if any(neg in prefix for neg in negations):
                    continue
                return Intent(
                    primary=IntentType.CRISIS_INTERVENTION,
                    confidence=1.0,
                    mode=ConversationMode.CRISIS,
                    reasoning=f"Crisis keyword detected: {kw}"
                )
        return None
    
    async def _check_psychology(self, message: str, context: Optional[RouteContext]) -> Intent:
        """心理学检测"""
        msg_lower = message.lower()
        
        # 关键词匹配
        keyword_matches = sum(1 for kw in self.PSYCHOLOGY_KEYWORDS if kw in msg_lower)
        keyword_confidence = min(keyword_matches / 3, 0.9)
        
        # 情绪强度检测（如果有context）
        emotion_boost = 0.0
        if context and context.emotion_state:
            emotion_intensity = context.emotion_state.get("intensity", 0)
            if emotion_intensity > 0.7:
                emotion_boost = 0.2
        
        confidence = min(keyword_confidence + emotion_boost, 1.0)
        
        if confidence > 0.5:
            return Intent(
                primary=IntentType.PSYCHOLOGY_SUPPORT,
                confidence=confidence,
                secondary=IntentType.GENERAL_CHAT,
                mode=ConversationMode.PSYCHOLOGY,
                reasoning=f"Psychology keywords matched: {keyword_matches}"
            )
        
        return Intent(
            primary=IntentType.GENERAL_CHAT,
            confidence=0.3,
            reasoning="No strong psychology signals"
        )
    
    async def _llm_route(self, message: str, context: Optional[RouteContext]) -> Intent:
        """LLM辅助路由判断"""
        if self.llm is None:
            # 兜底：关键词判断
            return self._fallback_route(message)
        
        prompt = f"""分析用户消息的意图类型。

消息：{message}

意图类型：
- psychology: 用户表达情绪、心理困扰、需要共情支持
- education: 用户询问学习问题、需要作业辅导
- knowledge: 用户查询知识、概念、定义
- general: 普通聊天、问候、闲聊
- crisis: 用户有自杀/自伤倾向（最高优先级）

判断标准：
1. 如果消息涉及自杀/自伤念头 → crisis
2. 如果消息涉及情绪困扰（焦虑、压力、难过等）→ psychology
3. 如果消息涉及学习、作业、考试 → education
4. 如果消息询问知识概念 → knowledge
5. 其他 → general

只输出JSON格式：
{{"type": "psychology|education|knowledge|general|crisis", "confidence": 0.0-1.0, "reasoning": "简单理由"}}
"""
        
        try:
            response = await self.llm.generate(prompt, max_tokens=128)
            import json
            result = json.loads(response)
            
            type_map = {
                "crisis": IntentType.CRISIS_INTERVENTION,
                "psychology": IntentType.PSYCHOLOGY_SUPPORT,
                "education": IntentType.EDUCATION,
                "knowledge": IntentType.KNOWLEDGE_QUERY,
                "general": IntentType.GENERAL_CHAT,
            }
            
            intent_type = type_map.get(result.get("type", "general"), IntentType.GENERAL_CHAT)
            confidence = float(result.get("confidence", 0.5))
            
            return Intent(
                primary=intent_type,
                confidence=confidence,
                mode=self._type_to_mode(intent_type),
                reasoning=result.get("reasoning", "")
            )
        except Exception:
            return self._fallback_route(message)
    
    def _fallback_route(self, message: str) -> Intent:
        """兜底路由判断"""
        msg_lower = message.lower()
        
        # 检查各类关键词
        psych_count = sum(1 for kw in self.PSYCHOLOGY_KEYWORDS if kw in msg_lower)
        edu_count = sum(1 for kw in self.EDUCATION_KEYWORDS if kw in msg_lower)
        
        if psych_count > edu_count:
            return Intent(
                primary=IntentType.PSYCHOLOGY_SUPPORT,
                confidence=0.5,
                mode=ConversationMode.PSYCHOLOGY,
                reasoning="Keyword fallback"
            )
        elif edu_count > 0:
            return Intent(
                primary=IntentType.EDUCATION,
                confidence=0.5,
                mode=ConversationMode.EDUCATION,
                reasoning="Keyword fallback"
            )
        
        return Intent(
            primary=IntentType.GENERAL_CHAT,
            confidence=0.3,
            mode=ConversationMode.CHAT,
            reasoning="Default fallback"
        )
    
    def _type_to_mode(self, intent_type: IntentType) -> ConversationMode:
        """意图类型转对话模式"""
        mapping = {
            IntentType.CRISIS_INTERVENTION: ConversationMode.CRISIS,
            IntentType.PSYCHOLOGY_SUPPORT: ConversationMode.PSYCHOLOGY,
            IntentType.EDUCATION: ConversationMode.EDUCATION,
            IntentType.GENERAL_CHAT: ConversationMode.CHAT,
            IntentType.KNOWLEDGE_QUERY: ConversationMode.CHAT,
        }
        return mapping.get(intent_type, ConversationMode.CHAT)
```

---

### 3.2 Context 管理机制

#### 3.2.1 Context 生命周期管理

```python
# ========== context/context_lifecycle.py ==========
"""
Context 生命周期管理
定义上下文数据的创建、使用、过期、销毁流程
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from datetime import datetime, timedelta
import time
import threading

class ContextScope(Enum):
    """上下文作用域"""
    MESSAGE = "message"      # 单条消息级别
    SESSION = "session"     # 会话级别
    USER = "user"           # 用户级别
    GLOBAL = "global"       # 全局级别

class ContextTTL(Enum):
    """上下文存活时间"""
    EPHEMERAL = 60          # 临时：60秒
    SHORT = 300            # 短期：5分钟
    MEDIUM = 1800          # 中期：30分钟
    LONG = 3600            # 长期：1小时
    PERSISTENT = 86400     # 持久：24小时

@dataclass
class ContextEntry:
    """上下文条目"""
    id: str
    key: str
    value: Any
    scope: ContextScope
    ttl: ContextTTL
    created_at: float
    last_accessed: float
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        age = time.time() - self.created_at
        ttl_seconds = {
            ContextTTL.EPHEMERAL: 60,
            ContextTTL.SHORT: 300,
            ContextTTL.MEDIUM: 1800,
            ContextTTL.LONG: 3600,
            ContextTTL.PERSISTENT: 86400,
        }.get(self.ttl, 300)
        return age > ttl_seconds

class ContextLifecycle:
    """
    上下文生命周期管理器
    
    职责：
    1. 管理不同作用域的上下文
    2. 自动过期清理
    3. 访问追踪
    4. 上下文传播
    """
    
    def __init__(self):
        self._contexts: Dict[str, Dict[str, ContextEntry]] = {
            ContextScope.MESSAGE: {},
            ContextScope.SESSION: {},
            ContextScope.USER: {},
            ContextScope.GLOBAL: {},
        }
        self._lock = threading.RLock()
        self._cleanup_interval = 60  # 每60秒清理一次
        self._last_cleanup = time.time()
        self._cleanup_callbacks: List[Callable] = []
    
    def set(
        self,
        key: str,
        value: Any,
        scope: ContextScope,
        ttl: ContextTTL = ContextTTL.SHORT,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContextEntry:
        """
        设置上下文
        
        Args:
            key: 上下文键
            value: 上下文值
            scope: 作用域
            ttl: 存活时间
            session_id: 会话ID（用于SESSION作用域）
            user_id: 用户ID（用于USER作用域）
            metadata: 元数据
            
        Returns:
            ContextEntry: 创建的上下文条目
        """
        # 生成唯一ID
        scope_key = self._get_scope_key(scope, session_id, user_id)
        entry_id = f"{scope_key}:{key}"
        
        entry = ContextEntry(
            id=entry_id,
            key=key,
            value=value,
            scope=scope,
            ttl=ttl,
            created_at=time.time(),
            last_accessed=time.time(),
            metadata=metadata or {}
        )
        
        with self._lock:
            self._contexts[scope][entry_id] = entry
        
        return entry
    
    def get(
        self,
        key: str,
        scope: ContextScope,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[Any]:
        """
        获取上下文
        """
        scope_key = self._get_scope_key(scope, session_id, user_id)
        entry_id = f"{scope_key}:{key}"
        
        with self._lock:
            entry = self._contexts[scope].get(entry_id)
            
            if entry is None:
                return None
            
            # 检查过期
            if entry.is_expired():
                del self._contexts[scope][entry_id]
                return None
            
            # 更新访问信息
            entry.last_accessed = time.time()
            entry.access_count += 1
            
            return entry.value
    
    def delete(
        self,
        key: str,
        scope: ContextScope,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """删除上下文"""
        scope_key = self._get_scope_key(scope, session_id, user_id)
        entry_id = f"{scope_key}:{key}"
        
        with self._lock:
            if entry_id in self._contexts[scope]:
                del self._contexts[scope][entry_id]
                return True
        return False
    
    def clear_scope(self, scope: ContextScope, session_id: Optional[str] = None) -> int:
        """清除某个作用域的所有上下文"""
        with self._lock:
            if scope == ContextScope.SESSION and session_id:
                # 只清除特定会话的
                scope_key = f"session:{session_id}"
                keys_to_delete = [
                    k for k in self._contexts[scope].keys()
                    if k.startswith(scope_key)
                ]
                for k in keys_to_delete:
                    del self._contexts[scope][k]
                return len(keys_to_delete)
            else:
                count = len(self._contexts[scope])
                self._contexts[scope].clear()
                return count
    
    def cleanup_expired(self) -> int:
        """清理所有过期的上下文"""
        current_time = time.time()
        
        # 检查是否需要清理
        if current_time - self._last_cleanup < self._cleanup_interval:
            return 0
        
        with self._lock:
            total_cleaned = 0
            
            for scope, entries in self._contexts.items():
                expired_keys = [
                    k for k, entry in entries.items()
                    if entry.is_expired()
                ]
                
                for k in expired_keys:
                    # 触发清理回调
                    self._trigger_cleanup_callbacks(entries[k])
                    del entries[k]
                    total_cleaned += 1
            
            self._last_cleanup = current_time
            
            return total_cleaned
    
    def _get_scope_key(
        self,
        scope: ContextScope,
        session_id: Optional[str],
        user_id: Optional[str]
    ) -> str:
        """生成作用域键"""
        if scope == ContextScope.MESSAGE:
            return f"msg:{id(threading.current_thread())}"
        elif scope == ContextScope.SESSION:
            return f"session:{session_id or 'default'}"
        elif scope == ContextScope.USER:
            return f"user:{user_id or 'anonymous'}"
        else:
            return "global"
    
    def _trigger_cleanup_callbacks(self, entry: ContextEntry) -> None:
        """触发清理回调"""
        for callback in self._cleanup_callbacks:
            try:
                callback(entry)
            except Exception:
                pass
    
    def register_cleanup_callback(self, callback: Callable) -> None:
        """注册清理回调"""
        self._cleanup_callbacks.append(callback)
```

```python
# ========== context/context_pipeline.py ==========
"""
Context 处理流水线
标准化上下文数据的处理流程
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum

class PipelineStage(Enum):
    """流水线阶段"""
    EXTRACTION = "extraction"      # 提取
    TRANSFORMATION = "transform"  # 转换
    ENRICHMENT = "enrichment"     # 增强
    FILTERING = "filtering"      # 过滤
    RANKING = "ranking"           # 排序
    AGGREGATION = "aggregation"   # 聚合

@dataclass
class PipelineResult:
    """流水线处理结果"""
    entries: List[ContextEntry]
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0

class ContextPipeline:
    """
    上下文处理流水线
    
    处理流程：
    1. 提取 - 从各数据源提取上下文
    2. 转换 - 格式转换、类型转换
    3. 增强 - 添加额外信息、关联数据
    4. 过滤 - 去除低质量、无关上下文
    5. 排序 - 按相关性、重要度排序
    6. 聚合 - 合并相似上下文
    """
    
    def __init__(self):
        self._stages: Dict[PipelineStage, List[Callable]] = {
            stage: [] for stage in PipelineStage
        }
    
    def register_stage(self, stage: PipelineStage, processor: Callable) -> None:
        """注册处理阶段"""
        self._stages[stage].append(processor)
    
    async def process(
        self,
        raw_contexts: List[Dict[str, Any]],
        query: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PipelineResult:
        """
        执行流水线处理
        
        Args:
            raw_contexts: 原始上下文列表
            query: 当前查询
            metadata: 额外元数据
            
        Returns:
            PipelineResult: 处理结果
        """
        import time
        start_time = time.time()
        
        entries = [ContextEntry.from_dict(ctx) for ctx in raw_contexts]
        
        # 1. 提取阶段
        for processor in self._stages[PipelineStage.EXTRACTION]:
            entries = await processor(entries, query, metadata)
        
        # 2. 转换阶段
        for processor in self._stages[PipelineStage.TRANSFORMATION]:
            entries = await processor(entries, query, metadata)
        
        # 3. 增强阶段
        for processor in self._stages[PipelineStage.ENRICHMENT]:
            entries = await processor(entries, query, metadata)
        
        # 4. 过滤阶段
        for processor in self._stages[PipelineStage.FILTERING]:
            entries = await processor(entries, query, metadata)
        
        # 5. 排序阶段
        for processor in self._stages[PipelineStage.RANKING]:
            entries = await processor(entries, query, metadata)
        
        # 6. 聚合阶段
        for processor in self._stages[PipelineStage.AGGREGATION]:
            entries = await processor(entries, query, metadata)
        
        return PipelineResult(
            entries=entries,
            metadata=metadata or {},
            processing_time=time.time() - start_time
        )
```

---

### 3.3 分层记忆系统架构

#### 3.3.1 统一记忆管理器

```python
# ========== memory/unified_memory.py ==========
"""
Unified Memory Manager - 统一记忆管理器
三层记忆架构：对话记忆 + 用户画像 + 情感历史
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import json
import time
import threading

@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    memory_type: str  # dialogue/profile/emotion/knowledge
    timestamp: float
    importance: float = 0.5  # 0-1 重要度
    embeddings: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UserProfile:
    """用户画像"""
    user_id: str
    user_type: str = "student"  # student/parent/teacher
    name: Optional[str] = None
    grade: Optional[str] = None
    
    # 特征标签
    interests: List[str] = field(default_factory=list)
    learning_style: Optional[str] = None
    communication_preference: str = "friendly"  # friendly/formal/casual
    
    # 心理状态
    typical_emotions: List[str] = field(default_factory=list)
    stress_triggers: List[str] = field(default_factory=list)
    coping_strategies: List[str] = field(default_factory=list)
    
    # 关系
    family_members: List[Dict[str, str]] = field(default_factory=list)
    friends: List[str] = field(default_factory=list)
    
    # 元数据
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

class UnifiedMemoryManager:
    """
    统一记忆管理器
    
    记忆分层：
    1. 对话记忆（Dialogue Memory）- 短期会话
    2. 用户画像（User Profile）- 长期用户特征
    3. 情感历史（Emotion History）- 情绪变化追踪
    4. 知识记忆（Knowledge Memory）- 事实性知识
    
    检索策略：
    - 对话记忆：时序 + 语义相似度
    - 用户画像：精确匹配 + 特征标签
    - 情感历史：时间范围 + 情绪类型
    - 知识记忆：语义检索 + 知识图谱
    """
    
    def __init__(
        self,
        persist_dir: str = "data/agent/memory",
        max_dialogue_entries: int = 100,
        max_emotion_history: int = 500,
    ):
        self.persist_dir = persist_dir
        self.max_dialogue_entries = max_dialogue_entries
        self.max_emotion_history = max_emotion_history
        
        self._lock = threading.RLock()
        
        # 各层记忆存储
        self._dialogue_memory: Dict[str, List[MemoryEntry]] = {}  # session_id -> entries
        self._user_profiles: Dict[str, UserProfile] = {}  # user_id -> profile
        self._emotion_history: Dict[str, List[MemoryEntry]] = {}  # user_id -> emotion entries
        self._knowledge_memory: List[MemoryEntry] = []
        
        # 向量存储（用于语义检索）
        self._embeddings_cache: Dict[str, List[float]] = {}
        
        # 加载持久化数据
        self._load_persisted_data()
    
    # ========== 对话记忆 ==========
    
    def add_dialogue(
        self,
        session_id: str,
        role: str,  # user/assistant/system
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        添加对话记忆
        
        Args:
            session_id: 会话ID
            role: 角色
            content: 对话内容
            metadata: 额外元数据
            
        Returns:
            str: 记忆ID
        """
        entry = MemoryEntry(
            id=f"dlg_{int(time.time() * 1000)}",
            content=content,
            memory_type="dialogue",
            timestamp=time.time(),
            importance=0.5,
            metadata={
                "role": role,
                **(metadata or {})
            }
        )
        
        with self._lock:
            if session_id not in self._dialogue_memory:
                self._dialogue_memory[session_id] = []
            
            self._dialogue_memory[session_id].append(entry)
            
            # 限制数量
            if len(self._dialogue_memory[session_id]) > self.max_dialogue_entries:
                self._dialogue_memory[session_id].pop(0)
        
        return entry.id
    
    def get_dialogue_history(
        self,
        session_id: str,
        limit: int = 20,
        role_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取对话历史
        
        Args:
            session_id: 会话ID
            limit: 返回数量限制
            role_filter: 角色过滤
            
        Returns:
            List[Dict]: 对话历史
        """
        with self._lock:
            entries = self._dialogue_memory.get(session_id, [])
        
        if role_filter:
            entries = [e for e in entries if e.metadata.get("role") == role_filter]
        
        # 返回最近的
        recent = entries[-limit:] if limit > 0 else entries
        
        return [
            {
                "role": e.metadata.get("role"),
                "content": e.content,
                "timestamp": e.timestamp,
            }
            for e in reversed(recent)
        ]
    
    # ========== 用户画像 ==========
    
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """获取用户画像"""
        with self._lock:
            return self._user_profiles.get(user_id)
    
    def update_user_profile(
        self,
        user_id: str,
        profile_data: Dict[str, Any]
    ) -> UserProfile:
        """
        更新用户画像
        
        Args:
            user_id: 用户ID
            profile_data: 要更新的画像数据
            
        Returns:
            UserProfile: 更新后的画像
        """
        with self._lock:
            if user_id not in self._user_profiles:
                self._user_profiles[user_id] = UserProfile(user_id=user_id)
            
            profile = self._user_profiles[user_id]
            
            # 更新字段
            for key, value in profile_data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            
            profile.updated_at = time.time()
            
            return profile
    
    def add_profile_tag(
        self,
        user_id: str,
        tag_type: str,  # interest/stress_trigger/coping_strategy
        tag_value: str
    ) -> bool:
        """为用户画像添加标签"""
        with self._lock:
            if user_id not in self._user_profiles:
                return False
            
            profile = self._user_profiles[user_id]
            
            tag_map = {
                "interest": profile.interests,
                "stress_trigger": profile.stress_triggers,
                "coping_strategy": profile.coping_strategies,
            }
            
            if tag_type in tag_map and tag_value not in tag_map[tag_type]:
                tag_map[tag_type].append(tag_value)
                profile.updated_at = time.time()
                return True
        
        return False
    
    # ========== 情感历史 ==========
    
    def add_emotion_record(
        self,
        user_id: str,
        emotion_type: str,
        intensity: float,
        trigger: Optional[str] = None,
        context: Optional[str] = None,
        response_given: Optional[str] = None
    ) -> str:
        """
        添加情感记录
        
        Args:
            user_id: 用户ID
            emotion_type: 情绪类型
            intensity: 强度 0-1
            trigger: 触发事件
            context: 上下文
            response_given: 给出的回应
            
        Returns:
            str: 记录ID
        """
        entry = MemoryEntry(
            id=f"emo_{int(time.time() * 1000)}",
            content=context or "",
            memory_type="emotion",
            timestamp=time.time(),
            importance=intensity,  # 高强度 = 高重要度
            metadata={
                "emotion_type": emotion_type,
                "intensity": intensity,
                "trigger": trigger,
                "response_given": response_given,
            }
        )
        
        with self._lock:
            if user_id not in self._emotion_history:
                self._emotion_history[user_id] = []
            
            self._emotion_history[user_id].append(entry)
            
            # 限制数量
            if len(self._emotion_history[user_id]) > self.max_emotion_history:
                self._emotion_history[user_id].pop(0)
        
        return entry.id
    
    def get_emotion_trends(
        self,
        user_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取情绪趋势
        
        Args:
            user_id: 用户ID
            days: 分析天数
            
        Returns:
            Dict: 情绪趋势分析
        """
        cutoff_time = time.time() - (days * 86400)
        
        with self._lock:
            records = self._emotion_history.get(user_id, [])
        
        # 过滤时间范围
        recent = [r for r in records if r.timestamp > cutoff_time]
        
        if not recent:
            return {
                "total_records": 0,
                "emotion_distribution": {},
                "average_intensity": 0,
                "trend": "stable",
            }
        
        # 统计分布
        emotion_counts = {}
        total_intensity = 0
        
        for record in recent:
            emo = record.metadata.get("emotion_type", "unknown")
            emotion_counts[emo] = emotion_counts.get(emo, 0) + 1
            total_intensity += record.metadata.get("intensity", 0)
        
        # 计算趋势（最近vs早期）
        mid_point = len(recent) // 2
        early_avg = sum(r.metadata.get("intensity", 0) for r in recent[:mid_point]) / max(mid_point, 1)
        late_avg = sum(r.metadata.get("intensity", 0) for r in recent[mid_point:]) / max(len(recent) - mid_point, 1)
        
        if late_avg > early_avg * 1.2:
            trend = "increasing"  # 情绪强度上升
        elif late_avg < early_avg * 0.8:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "total_records": len(recent),
            "emotion_distribution": emotion_counts,
            "average_intensity": total_intensity / len(recent),
            "trend": trend,
            "dominant_emotion": max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else None,
            "period_days": days,
        }
    
    def get_recent_emotions(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取最近的情绪记录"""
        with self._lock:
            records = self._emotion_history.get(user_id, [])
        
        recent = records[-limit:] if limit > 0 else records
        
        return [
            {
                "emotion_type": r.metadata.get("emotion_type"),
                "intensity": r.metadata.get("intensity"),
                "trigger": r.metadata.get("trigger"),
                "timestamp": r.timestamp,
            }
            for r in reversed(recent)
        ]
    
    # ========== 知识记忆 ==========
    
    def add_knowledge(
        self,
        content: str,
        knowledge_type: str,
        source: Optional[str] = None,
        importance: float = 0.5
    ) -> str:
        """添加知识记忆"""
        entry = MemoryEntry(
            id=f"know_{int(time.time() * 1000)}",
            content=content,
            memory_type="knowledge",
            timestamp=time.time(),
            importance=importance,
            metadata={
                "knowledge_type": knowledge_type,
                "source": source,
            }
        )
        
        with self._lock:
            self._knowledge_memory.append(entry)
        
        return entry.id
    
    def search_knowledge(
        self,
        query: str,
        knowledge_type: Optional[str] = None,
        limit: int = 5
    ) -> List[MemoryEntry]:
        """搜索知识记忆（简单关键词匹配）"""
        with self._lock:
            results = []
            
            for entry in self._knowledge_memory:
                if knowledge_type and entry.metadata.get("knowledge_type") != knowledge_type:
                    continue
                
                # 简单匹配
                if query.lower() in entry.content.lower():
                    results.append(entry)
            
            # 按重要度排序
            results.sort(key=lambda x: x.importance, reverse=True)
            
            return results[:limit]
    
    # ========== 持久化 ==========
    
    def _load_persisted_data(self) -> None:
        """加载持久化数据"""
        import os
        import json
        from pathlib import Path
        
        persist_path = Path(self.persist_dir)
        persist_path.mkdir(parents=True, exist_ok=True)
        
        # 加载用户画像
        profile_file = persist_path / "user_profiles.json"
        if profile_file.exists():
            try:
                with open(profile_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, profile_data in data.items():
                        self._user_profiles[user_id] = UserProfile(**profile_data)
            except Exception:
                pass
        
        # 加载情感历史
        emotion_file = persist_path / "emotion_history.json"
        if emotion_file.exists():
            try:
                with open(emotion_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, entries in data.items():
                        self._emotion_history[user_id] = [
                            MemoryEntry(**e) for e in entries
                        ]
            except Exception:
                pass
    
    def persist_data(self) -> None:
        """持久化数据"""
        import json
        from pathlib import Path
        
        persist_path = Path(self.persist_dir)
        persist_path.mkdir(parents=True, exist_ok=True)
        
        # 保存用户画像
        profile_data = {
            user_id: {
                "user_id": p.user_id,
                "user_type": p.user_type,
                "name": p.name,
                "grade": p.grade,
                "interests": p.interests,
                "learning_style": p.learning_style,
                "communication_preference": p.communication_preference,
                "typical_emotions": p.typical_emotions,
                "stress_triggers": p.stress_triggers,
                "coping_strategies": p.coping_strategies,
                "family_members": p.family_members,
                "friends": p.friends,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            }
            for user_id, p in self._user_profiles.items()
        }
        
        with open(persist_path / "user_profiles.json", "w", encoding="utf-8") as f:
            json.dump(profile_data, f, ensure_ascii=False, indent=2)
        
        # 保存情感历史
        emotion_data = {
            user_id: [entry.__dict__ for entry in entries]
            for user_id, entries in self._emotion_history.items()
        }
        
        with open(persist_path / "emotion_history.json", "w", encoding="utf-8") as f:
            json.dump(emotion_data, f, ensure_ascii=False, indent=2)
```

---

### 3.4 情绪感知模块

#### 3.4.1 心理学模块整合

```python
# ========== psychology/psychology_module.py ==========
"""
Psychology Module - 统一心理学模块
整合情绪识别、危机检测、共情生成、人格模拟
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
import time

class EmotionLevel(Enum):
    """情绪等级"""
    NEUTRAL = 0      # 中性
    MILD = 1         # 轻微
    MODERATE = 2     # 中等
    HIGH = 3         # 强烈
    EXTREME = 4      # 极端

@dataclass
class EmotionInfo:
    """情绪信息"""
    type: str              # 情绪类型
    level: EmotionLevel     # 情绪等级
    intensity: float        # 强度值 0-1
    keywords: List[str]     # 触发关键词
    suggestion: str         # 建议的回应方式
    icon: str = ""         # 情绪图标

@dataclass
class CrisisInfo:
    """危机信息"""
    level: str              # safe/low/medium/high/critical
    signals: List[Dict]     # 检测到的信号
    message: str            # 回应消息
    action: str             # 建议行动
    hotlines: List[str]     # 危机热线

@dataclass
class PersonalityProfile:
    """人格特征画像"""
    warmth: float = 0.8           # 温暖程度 0-1
    empathy: float = 0.9         # 共情能力 0-1
    positivity: float = 0.7       # 积极倾向 0-1
    formality: float = 0.3        # 正式程度 0-1
    verbosity: float = 0.5       # 冗长程度 0-1
    
    # 对话风格
    use_emoji: bool = True
    use_informal_speech: bool = True
    max_response_length: int = 200  # 最大回复长度
    
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
            # 高强度情绪，缩短回复，更聚焦
            if len(response) > self.max_response_length:
                response = response[:self.max_response_length] + "..."
        
        # 根据温暖程度调整语气
        if self.warmth > 0.7:
            if not any(marker in response for marker in ["🌸", "💙", "我", "你"]):
                response = f"我理解你的感受... {response}"
        
        # 根据积极倾向调整
        if self.positivity > 0.6:
            positive_additions = ["相信你", "会好起来的", "你很棒"]
            if emotion.type in ["sad", "anxious", "hopeless"]:
                import random
                response += f" {random.choice(positive_additions)}"
        
        return response

@dataclass
class PsychologyResult:
    """心理学处理结果"""
    emotion: EmotionInfo
    crisis: Optional[CrisisInfo] = None
    knowledge: List[Dict[str, Any]] = field(default_factory=list)
    empathic_response: Optional[str] = None
    personality_adjusted: Optional[str] = None
    recommended_action: str = "continue"

class PsychologyModule:
    """
    统一心理学模块
    
    整合功能：
    1. 情绪识别（EmotionDetector）
    2. 危机检测（CrisisDetector）
    3. 共情生成（EmpathicGenerator）
    4. 人格模拟（PersonalityEngine）
    5. 行为适配（BehaviorAdapter）
    """
    
    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        
        # 子模块
        self._emotion_detector = None
        self._crisis_detector = None
        self._empathic_generator = None
        self._personality_engine = None
        
        # 人格配置
        self._personality = PersonalityProfile()
        
        # 初始化子模块
        self._initialize_detectors()
    
    def _initialize_detectors(self) -> None:
        """初始化检测器"""
        from agent.modules.psychology.emotion import EmotionDetector, EmotionType
        from agent.modules.psychology.crisis import CrisisDetector, CrisisLevel
        from agent.modules.psychology.empathic import EmpathicGenerator
        
        self._emotion_detector = EmotionDetector()
        self._crisis_detector = CrisisDetector()
        self._empathic_generator = EmpathicGenerator()
    
    async def detect_emotion(self, text: str) -> EmotionInfo:
        """
        识别情绪
        
        Args:
            text: 用户输入
            
        Returns:
            EmotionInfo: 情绪信息
        """
        result = self._emotion_detector.detect(text)
        
        # 转换为 EmotionInfo
        level_map = {
            0.0-0.2: EmotionLevel.NEUTRAL,
            0.2-0.4: EmotionLevel.MILD,
            0.4-0.6: EmotionLevel.MODERATE,
            0.6-0.8: EmotionLevel.HIGH,
            0.8-1.0: EmotionLevel.EXTREME,
        }
        
        level = EmotionLevel.MODERATE
        for thresh, lvl in level_map.items():
            if result.intensity <= thresh:
                level = lvl
                break
        
        emotion_labels = {
            "happy": {"label": "开心", "icon": "😊"},
            "sad": {"label": "难过", "icon": "😢"},
            "anxious": {"label": "焦虑", "icon": "😰"},
            "angry": {"label": "生气", "icon": "😠"},
            "fearful": {"label": "害怕", "icon": "😨"},
            "hopeless": {"label": "绝望", "icon": "😔"},
            "neutral": {"label": "平静", "icon": "😌"},
        }
        
        label_info = emotion_labels.get(result.emotion.value, emotion_labels["neutral"])
        
        return EmotionInfo(
            type=result.emotion.value,
            level=level,
            intensity=result.intensity,
            keywords=result.keywords,
            suggestion=result.suggestion,
            icon=label_info["icon"]
        )
    
    async def check_crisis(self, text: str) -> CrisisInfo:
        """
        危机检测
        
        Args:
            text: 用户输入
            
        Returns:
            CrisisInfo: 危机信息
        """
        result = self._crisis_detector.check(text)
        
        return CrisisInfo(
            level=result.level.value,
            signals=result.signals,
            message=result.message,
            action=result.action,
            hotlines=result.hotlines
        )
    
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
        # 使用 EmpathicGenerator 生成基础回复
        base_response = await self._empathic_generator.generate(
            user_input=user_input,
            emotion_type=emotion.type,
            intensity=emotion.intensity
        )
        
        # 根据人格特征调整
        adjusted = self._personality.adapt_response(base_response, emotion)
        
        return adjusted
    
    async def process(
        self,
        user_input: str,
        user_type: str = "student",
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PsychologyResult:
        """
        综合心理处理
        
        执行流程：
        1. 情绪识别
        2. 危机检测
        3. 心理知识检索
        4. 共情回复生成
        5. 人格适配
        
        Args:
            user_input: 用户输入
            user_type: 用户类型
            user_id: 用户ID
            context: 额外上下文
            
        Returns:
            PsychologyResult: 综合处理结果
        """
        # 1. 情绪识别
        emotion = await self.detect_emotion(user_input)
        
        # 2. 危机检测（优先）
        crisis = await self.check_crisis(user_input)
        
        # 如果是危机情况，直接返回危机响应
        if crisis.level in ("high", "critical"):
            crisis_response = self._crisis_detector.get_response(
                type(crisis).__class__(
                    level=crisis.level,
                    signals=crisis.signals,
                    message=crisis.message,
                    action=crisis.action,
                    hotlines=crisis.hotlines
                )
            )
            
            return PsychologyResult(
                emotion=emotion,
                crisis=crisis,
                empathic_response=crisis_response,
                personality_adjusted=crisis_response,
                recommended_action="crisis_intervention"
            )
        
        # 3. 心理知识检索
        knowledge = []
        if context and "rag_results" in context:
            knowledge = context["rag_results"]
        else:
            # 可以调用 RAG 检索
            pass
        
        # 4. 生成共情回复
        empathic = await self.generate_empathic_response(
            user_input=user_input,
            emotion=emotion,
            context=context
        )
        
        # 5. 确定推荐行动
        action = self._determine_action(emotion, crisis)
        
        return PsychologyResult(
            emotion=emotion,
            crisis=crisis,
            knowledge=knowledge,
            empathic_response=empathic,
            personality_adjusted=empathic,
            recommended_action=action
        )
    
    def _determine_action(self, emotion: EmotionInfo, crisis: CrisisInfo) -> str:
        """确定推荐行动"""
        if crisis.level != "safe":
            return "crisis_intervention"
        
        if emotion.level == EmotionLevel.EXTREME:
            return "urgent_support"
        elif emotion.level == EmotionLevel.HIGH:
            return "focused_support"
        elif emotion.type in ["sad", "hopeless"]:
            return "comfort_and_encourage"
        elif emotion.type == "anxious":
            return "calm_and_guide"
        else:
            return "continue"
```

---

### 3.5 工作流引擎

#### 3.5.1 任务分解与执行

```python
# ========== core/workflow_engine.py ==========
"""
Workflow Engine - 工作流引擎
任务分解、优先级排序、执行监控
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import time
import asyncio
import uuid

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 取消

class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0    # 最高 - 危机干预
    HIGH = 1       # 高 - 紧急响应
    NORMAL = 2     # 普通
    LOW = 3        # 低 - 后台任务

@dataclass
class Task:
    """任务单元"""
    id: str
    name: str
    task_type: str              # task类型标识
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Any = None
    result_handler: Optional[Callable] = None
    
    # 执行信息
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    
    # 依赖
    depends_on: List[str] = field(default_factory=list)  # 依赖的任务ID
    depends_on_tasks: List["Task"] = field(default_factory=list, repr=False)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def duration(self) -> Optional[float]:
        """获取执行时长"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def is_ready(self) -> bool:
        """检查是否就绪（依赖是否都完成）"""
        if self.status != TaskStatus.PENDING:
            return False
        for dep in self.depends_on_tasks:
            if dep.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                return False
        return True

@dataclass
class WorkflowPlan:
    """工作流计划"""
    workflow_id: str
    tasks: List[Task]
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    max_parallel: int = 3  # 最大并行任务数

@dataclass
class WorkflowResult:
    """工作流执行结果"""
    workflow_id: str
    status: str  # success/partial/failed
    completed_tasks: List[Task]
    failed_tasks: List[Task]
    final_output: Any
    total_duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class WorkflowEngine:
    """
    工作流引擎
    
    功能：
    1. 任务分解 - 将复杂请求拆分为可执行任务
    2. 依赖管理 - 处理任务间依赖关系
    3. 优先级排序 - 确保高优先级任务先执行
    4. 并行执行 - 支持多任务并行
    5. 执行监控 - 追踪任务状态和时长
    6. 错误处理 - 任务失败时的处理策略
    """
    
    def __init__(self, max_parallel: int = 3, max_workflow_steps: int = 10):
        self.max_parallel = max_parallel
        self.max_workflow_steps = max_workflow_steps
        self._active_tasks: Dict[str, Task] = {}
        self._completed_tasks: Dict[str, Task] = {}
        self._task_handlers: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
    
    def register_handler(self, task_type: str, handler: Callable) -> None:
        """
        注册任务处理器
        
        Args:
            task_type: 任务类型
            handler: 处理函数，接收 task.input_data，返回 task.output_data
        """
        self._task_handlers[task_type] = handler
    
    async def create_workflow(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> WorkflowPlan:
        """
        创建工作流计划
        
        Args:
            user_message: 用户消息
            context: 上下文数据
            
        Returns:
            WorkflowPlan: 工作流计划
        """
        workflow_id = str(uuid.uuid4())[:12]
        tasks = []
        
        # 意图分析 - 确定需要执行哪些任务
        intent_tasks = await self._analyze_intent(user_message, context)
        tasks.extend(intent_tasks)
        
        # 如果需要 RAG，添加 RAG 任务
        if context and context.get("need_rag"):
            rag_task = Task(
                id=f"{workflow_id}_rag",
                name="知识库检索",
                task_type="rag",
                priority=TaskPriority.NORMAL,
                input_data={"query": user_message}
            )
            tasks.append(rag_task)
        
        # 如果需要工具，添加工具任务
        if context and context.get("need_tools"):
            tool_tasks = await self._plan_tool_tasks(user_message, context)
            for i, t in enumerate(tool_tasks):
                t.id = f"{workflow_id}_tool_{i}"
            tasks.extend(tool_tasks)
        
        # 添加 LLM 生成任务
        llm_task = Task(
            id=f"{workflow_id}_llm",
            name="LLM响应生成",
            task_type="llm_generate",
            priority=TaskPriority.LOW,
            depends_on=[t.id for t in tasks if t.task_type in ("rag", "tool")],
            input_data={"message": user_message}
        )
        tasks.extend([llm_task])
        
        # 排序（按优先级）
        tasks.sort(key=lambda t: t.priority.value)
        
        plan = WorkflowPlan(
            workflow_id=workflow_id,
            tasks=tasks,
            context=context or {},
            max_parallel=self.max_parallel
        )
        
        return plan
    
    async def execute_workflow(
        self,
        plan: WorkflowPlan,
        progress_callback: Optional[Callable] = None
    ) -> WorkflowResult:
        """
        执行工作流
        
        Args:
            plan: 工作流计划
            progress_callback: 进度回调
            
        Returns:
            WorkflowResult: 执行结果
        """
        start_time = time.time()
        
        # 维护任务映射
        task_map = {t.id: t for t in plan.tasks}
        
        # 设置依赖引用
        for task in plan.tasks:
            task.depends_on_tasks = [
                task_map[dep_id] for dep_id in task.depends_on
                if dep_id in task_map
            ]
        
        # 并行执行循环
        completed = []
        failed = []
        running = []
        
        while True:
            # 检查是否完成
            if len(completed) + len(failed) == len(plan.tasks):
                break
            
            # 清理已完成的运行任务
            running = [t for t in running if t.status == TaskStatus.RUNNING]
            
            # 查找就绪的任务
            ready_tasks = [
                t for t in plan.tasks
                if t.is_ready() and t.status == TaskStatus.PENDING
            ]
            
            # 限制并行数
            available_slots = self.max_parallel - len(running)
            ready_tasks = ready_tasks[:available_slots]
            
            # 启动就绪任务
            for task in ready_tasks:
                asyncio.create_task(self._execute_task(task))
                running.append(task)
            
            # 等待一小段时间
            await asyncio.sleep(0.1)
            
            # 更新进度
            if progress_callback:
                progress_callback({
                    "completed": len(completed),
                    "running": len(running),
                    "pending": len(plan.tasks) - len(completed) - len(running) - len(running),
                    "failed": len(failed)
                })
        
        # 收集结果
        final_output = None
        llm_task = next((t for t in completed if t.task_type == "llm_generate"), None)
        if llm_task:
            final_output = llm_task.output_data
        
        return WorkflowResult(
            workflow_id=plan.workflow_id,
            status="success" if not failed else "partial" if completed else "failed",
            completed_tasks=completed,
            failed_tasks=failed,
            final_output=final_output,
            total_duration=time.time() - start_time,
            metadata={
                "total_tasks": len(plan.tasks),
                "parallelism": self.max_parallel,
            }
        )
    
    async def _execute_task(self, task: Task) -> None:
        """执行单个任务"""
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        
        try:
            # 获取处理器
            handler = self._task_handlers.get(task.task_type)
            
            if handler is None:
                # 默认处理
                task.output_data = await self._default_task_handler(task)
            else:
                # 调用注册的处理
                if asyncio.iscoroutinefunction(handler):
                    task.output_data = await handler(task.input_data)
                else:
                    task.output_data = handler(task.input_data)
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            
            # 调用结果处理器
            if task.result_handler:
                await task.result_handler(task)
        
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = time.time()
    
    async def _default_task_handler(self, task: Task) -> Any:
        """默认任务处理器"""
        if task.task_type == "llm_generate":
            return {"status": "pending", "message": "LLM generation not implemented"}
        elif task.task_type == "rag":
            return {"results": [], "count": 0}
        else:
            return {"status": "unknown_task_type"}
    
    async def _analyze_intent(
        self,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> List[Task]:
        """分析意图，分解任务"""
        tasks = []
        
        # 情绪检测任务
        emotion_task = Task(
            id="intent_emotion",
            name="情绪检测",
            task_type="emotion_detect",
            priority=TaskPriority.HIGH,
            input_data={"message": message}
        )
        tasks.append(emotion_task)
        
        # 危机检测任务
        crisis_task = Task(
            id="intent_crisis",
            name="危机检测",
            task_type="crisis_detect",
            priority=TaskPriority.CRITICAL,
            input_data={"message": message},
            depends_on=[]
        )
        tasks.append(crisis_task)
        
        return tasks
    
    async def _plan_tool_tasks(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> List[Task]:
        """规划工具任务"""
        # 基于消息内容确定需要的工具
        tasks = []
        
        tool_keywords = {
            "calculate": ["计算", "等于", "+/-/*/"],
            "get_time": ["时间", "现在", "几点"],
            "search_web": ["搜索", "查一下"],
        }
        
        msg_lower = message.lower()
        
        for tool_name, keywords in tool_keywords.items():
            if any(k in msg_lower for k in keywords):
                task = Task(
                    id=f"tool_{tool_name}",
                    name=f"执行{tool_name}",
                    task_type="tool_execute",
                    priority=TaskPriority.NORMAL,
                    input_data={"tool": tool_name, "query": message}
                )
                tasks.append(task)
        
        return tasks
```

---

### 3.6 工具集成方案

#### 3.6.1 动态工具选择器

```python
# ========== tools/selector.py ==========
"""
Dynamic Tool Selector - 动态工具选择器
基于语义的工具匹配，替代关键词匹配
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio

@dataclass
class ToolMatch:
    """工具匹配结果"""
    tool_name: str
    confidence: float           # 0-1 匹配置信度
    match_reason: str            # 匹配原因
    suggested_params: Dict[str, Any] = field(default_factory=dict)

class ToolSelector:
    """
    动态工具选择器
    
    选择策略：
    1. 语义匹配 - 使用嵌入向量计算相似度
    2. 关键词增强 - 结合关键词匹配
    3. 上下文感知 - 考虑对话上下文
    4. 置信度阈值 - 低于阈值不选择
    """
    
    def __init__(
        self,
        tool_registry,
        embedder=None,
        min_confidence: float = 0.5
    ):
        self.registry = tool_registry
        self.embedder = embedder
        self.min_confidence = min_confidence
        
        # 工具描述缓存
        self._tool_embeddings: Dict[str, List[float]] = {}
    
    async def select_tools(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        max_tools: int = 3
    ) -> List[ToolMatch]:
        """
        选择合适的工具
        
        Args:
            message: 用户消息
            context: 对话上下文
            max_tools: 最多选择工具数
            
        Returns:
            List[ToolMatch]: 匹配的工具列表
        """
        matches = []
        
        # 1. 获取所有可用工具
        available_tools = self.registry.get_all()
        
        # 2. 并行计算每个工具的匹配度
        tasks = [
            self._calculate_match(tool, message, context)
            for tool in available_tools
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 3. 收集有效结果
        for tool, match_result in zip(available_tools, results):
            if isinstance(match_result, Exception):
                continue
            
            confidence, reason, params = match_result
            
            if confidence >= self.min_confidence:
                matches.append(ToolMatch(
                    tool_name=tool.name,
                    confidence=confidence,
                    match_reason=reason,
                    suggested_params=params
                ))
        
        # 4. 排序并返回TopN
        matches.sort(key=lambda x: x.confidence, reverse=True)
        
        return matches[:max_tools]
    
    async def _calculate_match(
        self,
        tool,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> Tuple[float, str, Dict[str, Any]]:
        """
        计算工具与消息的匹配度
        
        Returns:
            (confidence, reason, suggested_params)
        """
        # 1. 关键词匹配
        keyword_score, keyword_reason = self._keyword_match(tool, message)
        
        # 2. 语义匹配（如果有embedder）
        semantic_score = 0.0
        semantic_reason = ""
        
        if self.embedder:
            semantic_score, semantic_reason = await self._semantic_match(
                tool, message
            )
        
        # 3. 上下文增强
        context_boost = self._context_boost(tool, context)
        
        # 4. 综合评分
        final_score = (
            keyword_score * 0.4 +
            semantic_score * 0.4 +
            context_boost * 0.2
        )
        
        # 5. 选择最佳理由
        if keyword_score > semantic_score:
            reason = keyword_reason
        else:
            reason = semantic_reason
        
        # 6. 提取建议参数
        params = self._extract_params(tool, message)
        
        return final_score, reason, params
    
    def _keyword_match(
        self,
        tool,
        message: str
    ) -> Tuple[float, str]:
        """关键词匹配"""
        msg_lower = message.lower()
        tool_desc_lower = tool.description.lower()
        
        # 提取关键词
        tool_keywords = set(tool.description.split())
        message_keywords = set(msg_lower.split())
        
        # 计算重叠
        overlap = tool_keywords & message_keywords
        score = len(overlap) / max(len(tool_keywords), 1)
        
        if overlap:
            return score, f"关键词匹配: {', '.join(overlap)}"
        
        return 0.0, ""
    
    async def _semantic_match(
        self,
        tool,
        message: str
    ) -> Tuple[float, str]:
        """语义匹配"""
        try:
            # 获取工具描述的嵌入
            tool_embedding = await self._get_tool_embedding(tool)
            
            # 获取消息的嵌入
            message_embedding = await self.embedder.embed([message])
            
            # 计算余弦相似度
            similarity = self._cosine_similarity(
                tool_embedding,
                message_embedding[0]
            )
            
            return similarity, f"语义相似度: {similarity:.2f}"
        
        except Exception:
            return 0.0, ""
    
    async def _get_tool_embedding(self, tool) -> List[float]:
        """获取工具嵌入（带缓存）"""
        if tool.name not in self._tool_embeddings:
            embedding = await self.embedder.embed([tool.description])
            self._tool_embeddings[tool.name] = embedding[0]
        
        return self._tool_embeddings[tool.name]
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def _context_boost(
        self,
        tool,
        context: Optional[Dict[str, Any]]
    ) -> float:
        """基于上下文的置信度提升"""
        if not context:
            return 0.0
        
        boost = 0.0
        
        # 如果是心理学模式，给心理工具 boost
        if context.get("mode") == "psychology":
            if "psychology" in tool.name.lower() or "emotion" in tool.name.lower():
                boost += 0.3
        
        # 如果刚执行过类似工具，降低置信度（避免重复）
        recent_tools = context.get("recent_tools", [])
        if tool.name in recent_tools[-3:]:
            boost -= 0.2
        
        return max(0.0, min(boost, 0.3))
    
    def _extract_params(
        self,
        tool,
        message: str
    ) -> Dict[str, Any]:
        """从消息中提取工具参数"""
        params = {}
        
        # 根据工具类型提取
        if tool.name == "calculate":
            # 提取数学表达式
            import re
            expr_match = re.search(r'[\d\+\-\*/\(\)\.]+', message)
            if expr_match:
                params["expression"] = expr_match.group()
        
        elif tool.name == "get_current_time":
            # 不需要参数
            pass
        
        elif "search" in tool.name.lower():
            params["query"] = message
        
        return params
```

---

### 3.7 RAG 知识库优化

#### 3.7.1 统一 RAG 引擎

```python
# ========== rag/rag_engine.py ==========
"""
RAG Engine - 统一检索增强生成引擎
标准化知识库调用，优化检索效率
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import time
import asyncio
import hashlib

class RetrievalStrategy(Enum):
    """检索策略"""
    VECTOR_ONLY = "vector"           # 仅向量检索
    BM25_ONLY = "bm25"               # 仅BM25检索
    HYBRID = "hybrid"                # 混合检索
    EMOTION_WEIGHTED = "emotion"     # 情绪感知检索

@dataclass
class RetrievalQuery:
    """检索查询"""
    text: str
    user_id: Optional[str] = None
    user_type: str = "student"
    emotion_state: Optional[Dict[str, Any]] = None
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    n_results: int = 5
    rerank: bool = True
    filters: Optional[Dict[str, Any]] = None

@dataclass
class RetrievedChunk:
    """检索到的片段"""
    content: str
    source: str
    page: Optional[str] = None
    similarity: float = 0.0
    bm25_score: float = 0.0
    combined_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RetrievalResult:
    """检索结果"""
    chunks: List[RetrievedChunk]
    total_count: int
    retrieval_time: float
    strategy_used: RetrievalStrategy
    metadata: Dict[str, Any] = field(default_factory=dict)

class RAGEngine:
    """
    统一 RAG 引擎
    
    功能：
    1. 标准化检索接口
    2. 多种检索策略支持
    3. 查询缓存
    4. 结果重排
    5. 检索质量评估
    """
    
    def __init__(
        self,
        vectorstore=None,
        bm25_indexer=None,
        reranker=None,
        cache_size: int = 1000
    ):
        self.vectorstore = vectorstore
        self.bm25_indexer = bm25_indexer
        self.reranker = reranker
        
        # 检索缓存
        self._cache: Dict[str, RetrievalResult] = {}
        self._cache_size = cache_size
        self._cache_hits = 0
        self._cache_misses = 0
    
    async def retrieve(
        self,
        query: RetrievalQuery
    ) -> RetrievalResult:
        """
        执行检索
        
        Args:
            query: 检索查询
            
        Returns:
            RetrievalResult: 检索结果
        """
        start_time = time.time()
        
        # 1. 检查缓存
        cache_key = self._make_cache_key(query)
        cached = self._get_from_cache(cache_key)
        if cached:
            self._cache_hits += 1
            return cached
        
        self._cache_misses += 1
        
        # 2. 根据策略执行检索
        if query.strategy == RetrievalStrategy.VECTOR_ONLY:
            chunks = await self._vector_search(query)
        elif query.strategy == RetrievalStrategy.BM25_ONLY:
            chunks = await self._bm25_search(query)
        elif query.strategy == RetrievalStrategy.EMOTION_WEIGHTED:
            chunks = await self._emotion_weighted_search(query)
        else:  # HYBRID
            chunks = await self._hybrid_search(query)
        
        # 3. 重排（如需要）
        if query.rerank and self.reranker and len(chunks) > 1:
            chunks = await self._rerank(chunks, query)
        
        # 4. 构建结果
        result = RetrievalResult(
            chunks=chunks[:query.n_results],
            total_count=len(chunks),
            retrieval_time=time.time() - start_time,
            strategy_used=query.strategy,
            metadata={
                "query_hash": cache_key[:16],
                "reranked": query.rerank,
            }
        )
        
        # 5. 缓存结果
        self._add_to_cache(cache_key, result)
        
        return result
    
    async def _vector_search(
        self,
        query: RetrievalQuery
    ) -> List[RetrievedChunk]:
        """向量检索"""
        if not self.vectorstore:
            return []
        
        try:
            results = self.vectorstore.similarity_search(
                query.text,
                k=query.n_results * 2  # 多取一些，后面会裁剪
            )
            
            chunks = []
            for doc, meta, distance in results:
                chunks.append(RetrievedChunk(
                    content=doc,
                    source=meta.get("source", ""),
                    page=meta.get("page"),
                    similarity=1 - distance,
                    combined_score=1 - distance
                ))
            
            return chunks
        
        except Exception:
            return []
    
    async def _bm25_search(
        self,
        query: RetrievalQuery
    ) -> List[RetrievedChunk]:
        """BM25检索"""
        if not self.bm25_indexer:
            return []
        
        try:
            scores = self.bm25_indexer.search(
                query.text,
                top_k=query.n_results * 2
            )
            
            chunks = []
            for doc_idx, score in scores:
                chunks.append(RetrievedChunk(
                    content=self.bm25_indexer.get_document(doc_idx),
                    source="",
                    bm25_score=score,
                    combined_score=score
                ))
            
            return chunks
        
        except Exception:
            return []
    
    async def _hybrid_search(
        self,
        query: RetrievalQuery
    ) -> List[RetrievedChunk]:
        """混合检索"""
        # 并行执行向量和BM25检索
        vector_task = self._vector_search(query)
        bm25_task = self._bm25_search(query)
        
        vector_chunks, bm25_chunks = await asyncio.gather(
            vector_task, bm25_task
        )
        
        # RRF融合
        fused = self._reciprocal_rank_fusion(
            [vector_chunks, bm25_chunks],
            k=60
        )
        
        return fused
    
    async def _emotion_weighted_search(
        self,
        query: RetrievalQuery
    ) -> List[RetrievedChunk]:
        """情绪感知检索"""
        # 首先执行混合检索
        chunks = await self._hybrid_search(query)
        
        # 根据情绪状态调整权重
        if query.emotion_state:
            emotion_type = query.emotion_state.get("type")
            emotion_intensity = query.emotion_state.get("intensity", 0.5)
            
            # 情绪相关的文档 boost
            for chunk in chunks:
                # 检查文档是否与当前情绪相关
                emotion_keywords = self._get_emotion_keywords(emotion_type)
                
                if any(kw in chunk.content for kw in emotion_keywords):
                    boost = emotion_intensity * 0.2
                    chunk.combined_score *= (1 + boost)
        
        # 重新排序
        chunks.sort(key=lambda x: x.combined_score, reverse=True)
        
        return chunks
    
    def _get_emotion_keywords(self, emotion_type: str) -> List[str]:
        """获取情绪相关关键词"""
        emotion_keywords = {
            "sad": ["难过", "伤心", "失落", "沮丧", "抑郁", "焦虑"],
            "anxious": ["焦虑", "紧张", "担心", "害怕", "不安", "压力"],
            "angry": ["生气", "愤怒", "烦躁", "不满", "委屈"],
            "happy": ["开心", "快乐", "高兴", "愉快", "兴奋"],
            "fearful": ["害怕", "恐惧", "担心", "不安", "惊慌"],
        }
        return emotion_keywords.get(emotion_type, [])
    
    def _reciprocal_rank_fusion(
        self,
        result_lists: List[List[RetrievedChunk]],
        k: int = 60
    ) -> List[RetrievedChunk]:
        """RRF reciprocal rank fusion"""
        scores: Dict[str, float] = {}
        chunk_map: Dict[str, RetrievedChunk] = {}
        
        for chunks in result_lists:
            for rank, chunk in enumerate(chunks):
                key = chunk.content[:100]  # 用内容前100字符作为key
                
                if key not in scores:
                    scores[key] = 0.0
                    chunk_map[key] = chunk
                
                scores[key] += 1.0 / (k + rank + 1)
        
        # 排序
        sorted_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        # 构建结果
        result = []
        for key in sorted_keys[:self._cache_size]:
            chunk = chunk_map[key]
            chunk.combined_score = scores[key]
            result.append(chunk)
        
        return result
    
    async def _rerank(
        self,
        chunks: List[RetrievedChunk],
        query: RetrievalQuery
    ) -> List[RetrievedChunk]:
        """结果重排"""
        if not self.reranker or len(chunks) <= 1:
            return chunks
        
        try:
            # 使用重排模型
            reranked = await self.reranker.rerank(
                query=query.text,
                documents=[c.content for c in chunks],
                top_n=len(chunks)
            )
            
            # 重新排序
            reranked_chunks = []
            for idx, r_score in enumerate(reranked):
                chunk = chunks[r_score["index"]]
                chunk.combined_score = r_score["score"]
                reranked_chunks.append(chunk)
            
            return reranked_chunks
        
        except Exception:
            return chunks
    
    def _make_cache_key(self, query: RetrievalQuery) -> str:
        """生成缓存键"""
        key_data = f"{query.text}:{query.user_type}:{query.strategy.value}:{query.n_results}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_from_cache(self, key: str) -> Optional[RetrievalResult]:
        """从缓存获取"""
        return self._cache.get(key)
    
    def _add_to_cache(self, key: str, result: RetrievalResult) -> None:
        """添加到缓存"""
        if len(self._cache) >= self._cache_size:
            # 删除最老的
            oldest_key = min(self._cache.keys(), key=self._cache.get)
            del self._cache[oldest_key]
        
        self._cache[key] = result
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0
        
        return {
            "size": len(self._cache),
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": round(hit_rate, 3)
        }
```

---

## 四、API 接口规范

### 4.1 API 路由定义

```python
# ========== api/schemas.py ==========
"""
Pydantic 请求/响应模型
标准化 API 数据结构
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# ========== 通用 ==========

class UserType(str, Enum):
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

# ========== 请求模型 ==========

class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, description="会话ID，不提供则自动创建")
    user_id: Optional[str] = Field(None, description="用户ID")
    user_type: UserType = Field(UserType.STUDENT)
    use_rag: bool = Field(True, description="是否使用知识库")
    use_tools: bool = Field(True, description="是否使用工具")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "最近学习压力好大，晚上都睡不好觉",
                "session_id": "sess_abc123",
                "user_type": "student"
            }
        }
    )

class PsychologyRequest(BaseModel):
    """心理学模式请求"""
    message: str = Field(..., min_length=1)
    user_type: UserType = Field(UserType.STUDENT)
    include_knowledge: bool = Field(True, description="是否包含心理知识检索")
    
class EmotionCheckRequest(BaseModel):
    """情绪检测请求"""
    text: str = Field(..., min_length=1, max_length=1000)

class CrisisCheckRequest(BaseModel):
    """危机检测请求"""
    text: str = Field(..., min_length=1, max_length=1000)

# ========== 响应模型 ==========

class EmotionInfo(BaseModel):
    """情绪信息"""
    type: str = Field(..., description="情绪类型: happy/sad/anxious/angry...")
    level: str = Field(..., description="情绪等级: neutral/mild/moderate/high/extreme")
    intensity: float = Field(..., ge=0.0, le=1.0, description="强度值")
    icon: str = Field(..., description="情绪图标")
    suggestion: str = Field(..., description="建议的回应方式")

class CrisisInfo(BaseModel):
    """危机信息"""
    level: str = Field(..., description="危机等级: safe/low/medium/high/critical")
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    message: str = Field(..., description="危机回应消息")
    action: str = Field(..., description="建议行动")
    hotlines: List[str] = Field(default_factory=list)

class SourceInfo(BaseModel):
    """来源信息"""
    content: str = Field(..., description="内容摘要")
    source: str = Field(..., description="来源")
    page: Optional[str] = Field(None, description="页码")
    similarity: float = Field(..., description="相似度")

class ToolCallInfo(BaseModel):
    """工具调用信息"""
    tool_name: str
    status: str
    execution_time: float
    result: Optional[Any] = None

class ChatResponse(BaseModel):
    """对话响应"""
    answer: str = Field(..., description="AI回复")
    mode: str = Field(..., description="处理模式: chat/psychology/education/crisis")
    
    emotion: Optional[EmotionInfo] = Field(None, description="情绪信息")
    crisis_level: Optional[str] = Field(None, description="危机等级")
    
    sources: List[SourceInfo] = Field(default_factory=list, description="知识来源")
    tool_calls: List[ToolCallInfo] = Field(default_factory=list, description="工具调用")
    
    session_id: str = Field(..., description="会话ID")
    execution_time: float = Field(..., description="执行时间(秒)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "answer": "听到你说学习压力大，我能理解这种感受...",
                "mode": "psychology",
                "emotion": {
                    "type": "anxious",
                    "level": "moderate",
                    "intensity": 0.65,
                    "icon": "😰",
                    "suggestion": "calm_down"
                },
                "session_id": "sess_abc123",
                "execution_time": 1.23
            }
        }
    )

class EmotionResponse(BaseModel):
    """情绪检测响应"""
    emotion: EmotionInfo
    request_id: str

class CrisisResponse(BaseModel):
    """危机检测响应"""
    crisis: CrisisInfo
    requires_intervention: bool
    request_id: str

# ========== 状态码定义 ==========

class ResponseStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"  # 部分成功
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    UNAUTHORIZED = "unauthorized"

class ErrorDetail(BaseModel):
    """错误详情"""
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    field: Optional[str] = Field(None, description="出错的字段")
    details: Optional[Dict[str, Any]] = Field(None, description="额外详情")

class APIResponse(BaseModel):
    """通用API响应包装"""
    status: ResponseStatus
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None
    request_id: str = Field(..., description="请求ID，用于追踪")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def is_success(self) -> bool:
        return self.status == ResponseStatus.SUCCESS
```

### 4.2 错误处理规范

```python
# ========== api/errors.py ==========
"""
统一错误处理
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import uuid
import logging

logger = logging.getLogger(__name__)

class AppError(Exception):
    """应用基础错误"""
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.request_id = None
        super().__init__(message)

class RateLimitError(AppError):
    """限流错误"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            code="RATE_LIMITED",
            message=f"Rate limit exceeded. Retry after {retry_after} seconds",
            status_code=429,
            details={"retry_after": retry_after}
        )

class UnauthorizedError(AppError):
    """认证错误"""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=401
        )

class ValidationError(AppError):
    """验证错误"""
    def __init__(self, field: str, message: str):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            details={"field": field}
        )

class NotFoundError(AppError):
    """资源不存在"""
    def __init__(self, resource: str):
        super().__init__(
            code="NOT_FOUND",
            message=f"Resource not found: {resource}",
            status_code=404
        )

class ServiceUnavailableError(AppError):
    """服务不可用"""
    def __init__(self, service: str):
        super().__init__(
            code="SERVICE_UNAVAILABLE",
            message=f"Service unavailable: {service}",
            status_code=503,
            details={"service": service}
        )

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """应用错误处理器"""
    request_id = str(uuid.uuid4())[:12]
    
    logger.error(
        f"Request {request_id} error: {exc.code} - {exc.message}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            },
            "request_id": request_id
        }
    )

async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用错误处理器"""
    request_id = str(uuid.uuid4())[:12]
    
    logger.exception(
        f"Unexpected error on request {request_id}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            },
            "request_id": request_id
        }
    )
```

---

## 五、性能优化路线图

### 5.1 优化策略矩阵

| 优化领域 | 当前状态 | 优化目标 | 实施方案 | 预期收益 |
|---------|---------|---------|---------|---------|
| **RAG缓存** | 简单缓存 | 智能缓存+预热 | 实现查询缓存、结果缓存、LLM响应缓存 | 延迟-40% |
| **数据库查询** | 无优化 | 查询优化+索引 | ChromaDB索引优化、BM25参数调优 | 检索+30% |
| **并行处理** | 串行执行 | 并行+流水线 | asyncio并行、流水线并发 | 吞吐+50% |
| **内存管理** | 手动管理 | 自动生命周期 | Context过期清理、记忆淘汰 | 内存-30% |
| **连接复用** | 每次新建 | 连接池+复用 | HTTP连接池、数据库连接池 | 延迟-20% |
| **代码优化** | 无专门优化 | 热点优化 | profile分析、算法优化 | CPU-25% |

### 5.2 缓存策略详细设计

```python
# ========== rag/cache_manager.py ==========
"""
Multi-Level Cache Manager - 多级缓存管理器
L1: 内存LRU / L2: Redis / L3: 持久化
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List
from threading import Lock
from collections import OrderedDict
import time
import json
import hashlib

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int = 0
    size_bytes: int = 0
    ttl: float = 0  # 0 = 不过期
    
    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return time.time() - self.created_at > self.ttl

class MemoryCache:
    """L1 内存缓存 - LRU"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None
            
            # 移到末尾（最近使用）
            self._cache.move_to_end(key)
            entry.last_accessed = time.time()
            entry.access_count += 1
            self._hits += 1
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        with self._lock:
            # 如果已存在，更新
            if key in self._cache:
                self._cache[key].value = value
                self._cache[key].last_accessed = time.time()
                self._cache.move_to_end(key)
                return
            
            # 如果满了，删除最老的
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                ttl=ttl or self.default_ttl
            )
            
            self._cache[key] = entry
    
    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
        return False
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 3)
            }

class QueryCache:
    """
    查询缓存
    
    缓存策略：
    1. 查询文本 hash 作为 key
    2. 可配置 TTL
    3. 支持按用户/会话隔离
    4. 统计命中率
    """
    
    def __init__(
        self,
        memory_cache: MemoryCache,
        redis_client: Optional[Any] = None
    ):
        self.memory = memory_cache
        self.redis = redis_client
        self._lock = Lock()
    
    def make_key(
        self,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """生成缓存键"""
        key_parts = [
            query[:100],  # 截断长查询
            user_id or "",
            session_id or ""
        ]
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()[:24]
    
    def get(
        self,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Optional[Any]:
        """获取缓存"""
        key = self.make_key(query, user_id, session_id)
        
        # L1 内存
        result = self.memory.get(key)
        if result is not None:
            return result
        
        # L2 Redis（如果可用）
        if self.redis:
            try:
                cached = self.redis.get(f"qcache:{key}")
                if cached:
                    # 回填 L1
                    data = json.loads(cached)
                    self.memory.set(key, data)
                    return data
            except Exception:
                pass
        
        return None
    
    def set(
        self,
        query: str,
        result: Any,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ttl: Optional[float] = None
    ) -> None:
        """设置缓存"""
        key = self.make_key(query, user_id, session_id)
        
        # L1 内存
        self.memory.set(key, result, ttl=ttl)
        
        # L2 Redis（如果可用）
        if self.redis:
            try:
                self.redis.set(
                    f"qcache:{key}",
                    json.dumps(result),
                    ex=int(ttl or 300)
                )
            except Exception:
                pass
```

---

## 六、实施步骤与阶段性目标

### 6.1 实施阶段划分

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              实施时间线（8天）                                  │
│                                                                             │
│  Phase 1: 架构重构                                                          │
│  ├─ Day 1-2: 模块拆分 + Context生命周期管理                                  │
│  └─ Day 3: 统一API规范                                                      │
│                                                                             │
│  Phase 2: 核心功能实现                                                       │
│  ├─ Day 4: 分层记忆系统 + 心理学模块整合                                      │
│  └─ Day 5: 工作流引擎 + 动态工具选择器                                        │
│                                                                             │
│  Phase 3: RAG优化 + 性能调优                                                 │
│  ├─ Day 6: RAG引擎重构 + 缓存策略                                             │
│  └─ Day 7: 性能测试 + 调优                                                    │
│                                                                             │
│  Phase 4: 联调 + 部署                                                        │
│  └─ Day 8: 前后端联调 + Docker部署 + PPT                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 各阶段详细任务

#### Phase 1: 架构重构（Day 1-3）

**Day 1-2: 模块拆分 + Context生命周期**

```
任务清单：
□ 创建 agent/core/ 目录结构
□ 拆分 orchestrator.py（主编排器）
□ 拆分 intent_router.py（意图路由）
□ 实现 context_lifecycle.py（上下文生命周期）
□ 实现 context_pipeline.py（上下文流水线）
□ 更新 agent/__init__.py 导出新模块
□ 编写单元测试

验收标准：
- Agent核心类行数 < 300行
- Context生命周期测试覆盖率 > 80%
- 原有功能回归测试通过
```

**Day 3: 统一API规范**

```
任务清单：
□ 创建 api/schemas.py（Pydantic模型）
□ 创建 api/errors.py（错误处理）
□ 重构 api/routes.py（符合新规范）
□ 生成 OpenAPI 文档
□ 编写 API 使用示例

验收标准：
- 所有API有完整请求/响应模型
- 错误处理统一化
- OpenAPI文档可访问
```

#### Phase 2: 核心功能实现（Day 4-5）

**Day 4: 分层记忆系统 + 心理学模块**

```
任务清单：
□ 创建 memory/unified_memory.py（统一记忆管理）
□ 实现 user_profile.py（用户画像）
□ 实现 emotion_history.py（情感历史）
□ 整合 psychology_module.py（心理学模块）
□ 实现 personality_engine.py（人格特征引擎）

验收标准：
- 记忆读写功能正常
- 用户画像持久化
- 情感历史追踪可用
```

**Day 5: 工作流引擎 + 动态工具选择**

```
任务清单：
□ 实现 workflow_engine.py（工作流引擎）
□ 实现 task.py（任务单元）
□ 实现 selector.py（动态工具选择）
□ 实现 adapter.py（参数适配器）
□ 集成测试工作流

验收标准：
- 工作流可执行多步任务
- 工具选择准确率提升
- 任务优先级生效
```

#### Phase 3: RAG优化 + 性能调优（Day 6-7）

**Day 6: RAG引擎重构 + 缓存策略**

```
任务清单：
□ 实现 rag_engine.py（统一RAG引擎）
□ 实现 query_router.py（查询路由）
□ 实现 hybrid_retriever.py（混合检索）
□ 实现 cache_manager.py（多级缓存）
□ 性能测试

验收标准：
- RAG检索延迟 < 500ms
- 缓存命中率 > 60%
```

**Day 7: 性能测试 + 调优**

```
任务清单：
□ 全量性能测试
□ profile分析热点
□ 针对性优化
□ 内存泄漏检查
□ 并发测试

验收标准：
- 平均响应时间 < 2s
- 99分位 < 5s
- 内存稳定无泄漏
```

#### Phase 4: 联调 + 部署（Day 8）

**Day 8: 前后端联调 + Docker部署 + PPT**

```
任务清单：
□ 前后端API联调
□ Web测试界面验证
□ Docker镜像构建
□ docker-compose部署验证
□ 准备演示PPT

验收标准：
- 所有API联调通过
- Docker部署成功
- PPT可演示
```

---

## 七、数据流程图

### 7.1 完整对话流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           完整对话流程                                        │
│                                                                             │
│  用户消息                                                                   │
│     │                                                                      │
│     ▼                                                                      │
│  ┌──────────────┐                                                           │
│  │ Intent Router │ ←── LLM判断意图                                           │
│  │   意图路由    │                                                           │
│  └──────┬───────┘                                                           │
│         │                                                                   │
│         ├────→ PSYCHOLOGY ──────────────────────────┐                       │
│         │                                            ▼                       │
│         ├────→ EDUCATION ───────────────────────────┐│                       │
│         │                                            ▼                       │
│         │                                            │                       │
│         └────→ GENERAL ─────────────────────────────┘│                       │
│                                                              │               │
│                                                              ▼               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Parallel Execution Pipeline                         │   │
│  │                                                                       │   │
│  │   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐          │   │
│  │   │ Memory  │    │   RAG   │    │  Tools  │    │Context  │          │   │
│  │   │ 读取记忆 │    │ 检索知识 │    │ 执行工具 │    │ 构建上下文│          │   │
│  │   └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘          │   │
│  │        │              │              │              │                 │   │
│  │        └──────────────┴──────────────┴──────────────┘                 │   │
│  │                               │                                        │   │
│  └───────────────────────────────┼────────────────────────────────────────┘   │
│                                  ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     Response Builder                                   │   │
│  │   1. 合并各模块结果                                                    │   │
│  │   2. 心理学模式：共情生成 + 人格适配                                    │   │
│  │   3. 教育模式：知识整合 + 讲解生成                                     │   │
│  │   4. 普通模式：直接回复                                                │   │
│  └───────────────────────────────┬──────────────────────────────────────┘   │
│                                  ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     Reflection (反思机制)                               │   │
│  │   检查回答质量，决定是否重写                                             │   │
│  └───────────────────────────────┬──────────────────────────────────────┘   │
│                                  ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     Memory Update                                      │   │
│  │   1. 保存对话到对话记忆                                                 │   │
│  │   2. 更新用户画像（如需要）                                             │   │
│  │   3. 记录情感历史（如是心理学模式）                                      │   │
│  └───────────────────────────────┬──────────────────────────────────────┘   │
│                                  ▼                                            │
│                              用户响应                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 八、架构评估

### 8.1 与原架构对比

| 维度 | 原架构 (v4) | 新架构 (v5) | 改进 |
|------|------------|------------|------|
| **Agent核心** | 1000行单文件 | 5个独立模块 | 可维护性+60% |
| **意图识别** | 关键词匹配 | LLM+规则混合 | 准确率+25% |
| **上下文管理** | 简单存储 | 生命周期+流水线 | 数据质量+40% |
| **记忆系统** | 2层 | 4层分层 | 连贯性+35% |
| **情绪感知** | 规则引擎 | 规则+LLM+人格 | 共情度+30% |
| **工作流** | 简单ReAct | 可视化+优先级 | 复杂场景+50% |
| **工具选择** | 关键词匹配 | 语义+动态 | 调用准确率+40% |
| **RAG** | 基础混合检索 | 智能路由+缓存 | 效率+45% |
| **API** | 无规范 | OpenAPI规范 | 开发效率+50% |

### 8.2 赛事评分预期

| 评分维度 | 权重 | 原架构得分 | 新架构预期 | 提升 |
|---------|:----:|----------|-----------|------|
| **方案创新性** | 25% | 22 | 24-25 | +10% |
| **实用性** | 25% | 20 | 22-23 | +12% |
| **系统架构** | 15% | 11 | 14-15 | +30% |
| **RAG功能** | 10% | 7 | 9-10 | +30% |
| **工具调用** | 10% | 7 | 9-10 | +30% |
| **系统稳定性** | 5% | 3 | 4-5 | +40% |
| **文档完整性** | 10% | 6 | 8-9 | +35% |
| **总分** | 100% | **76** | **90-97** | **+20%** |

---

## 九、附录

### 9.1 模块依赖关系图

```
orchestrator.py (主编排)
    ├── intent_router.py
    ├── context_manager.py
    │   ├── context_lifecycle.py
    │   └── context_pipeline.py
    ├── unified_memory.py
    │   ├── dialogue_memory.py
    │   ├── user_profile.py
    │   └── emotion_history.py
    ├── psychology_module.py
    │   ├── emotion_detector.py
    │   ├── crisis_detector.py
    │   ├── empathic_generator.py
    │   └── personality_engine.py
    ├── tool_registry.py
    │   └── tool_selector.py
    └── rag_engine.py
        ├── hybrid_retriever.py
        ├── reranker.py
        └── cache_manager.py
```

### 9.2 配置项清单

| 配置项 | 类型 | 默认值 | 说明 |
|-------|------|-------|------|
| `orchestrator.max_parallel` | int | 3 | 最大并行任务数 |
| `orchestrator.max_workflow_steps` | int | 10 | 最大工作流步数 |
| `memory.max_dialogue_entries` | int | 100 | 对话记忆最大条数 |
| `memory.max_emotion_history` | int | 500 | 情感历史最大条数 |
| `cache.query_cache_size` | int | 1000 | 查询缓存大小 |
| `cache.default_ttl` | int | 300 | 默认缓存TTL(秒) |
| `rag.default_n_results` | int | 5 | 默认检索数量 |
| `rag.vector_weight` | float | 0.6 | 向量检索权重 |
| `rag.bm25_weight` | float | 0.4 | BM25权重 |

---

**文档结束**

*架构设计：沫汐 🌸*
*版本：v5.0*
*日期：2026-04-12*
*备注：截止日期还剩8天，按优先级实施*

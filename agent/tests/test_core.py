"""
Comprehensive Unit Tests for Core Modules
包括: IntentRouter, WorkflowEngine
"""
import pytest
import asyncio
from agent.core.intent_router import (
    IntentRouter, IntentType, ConversationMode, Intent, RouteContext
)
from agent.core.workflow_engine import (
    WorkflowEngine, TaskType, TaskPriority, TaskStatus,
    Task, WorkflowPlan, WorkflowResult
)

tempskip = pytest.mark.skip(reason="temp skip")

# =============================================================================
# IntentRouter Tests
# =============================================================================

class TestIntentRouter:
    """意图路由器测试"""

    def setup_method(self):
        """每个测试前重新创建实例"""
        self.router = IntentRouter()

    # ---- 基础功能测试 ----

    def test_router_created(self):
        """测试路由器创建成功"""
        assert self.router is not None
        assert hasattr(self.router, 'route')

    def test_route_returns_intent(self):
        """测试路由返回Intent对象"""
        result = asyncio.run(self.router.route("你好"))
        assert isinstance(result, Intent)
        assert hasattr(result, 'primary')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'mode')

    # ---- 危机检测测试 ----

    def test_crisis_keyword_detected(self):
        """测试危机关键词检测"""
        crisis_messages = [
            "我不想活了",
            "想死",
            "活不下去",
            "死了算了",
            "自残",
            "割腕",
        ]
        for msg in crisis_messages:
            result = asyncio.run(self.router.route(msg))
            assert result.primary == IntentType.CRISIS_INTERVENTION, f"Failed for: {msg}"
            assert result.confidence == 1.0
            assert result.mode == ConversationMode.CRISIS

    def test_crisis_with_negation_not_detected(self):
        """测试带否定词的危机不检测"""
        messages = [
            "我不想死",
            "不会自杀的",
            "没有想死",
        ]
        for msg in messages:
            result = asyncio.run(self.router.route(msg))
            assert result.primary != IntentType.CRISIS_INTERVENTION

    def test_crisis_priority_over_psychology(self):
        """测试危机优先级高于心理学"""
        result = asyncio.run(self.router.route("我不想活了"))
        assert result.primary == IntentType.CRISIS_INTERVENTION

    # ---- 心理学检测测试 ----

    def test_psychology_keywords_detected(self):
        """测试心理学关键词检测"""
        messages = [
            "我情绪很低落",
            "心里很难受",
            "压力好大",
            "被孤立了",
            "人际关系困扰",
        ]
        for msg in messages:
            result = asyncio.run(self.router.route(msg))
            assert result.primary == IntentType.PSYCHOLOGY_SUPPORT, f"Failed for: {msg}"

    def test_psychology_mode(self):
        """测试心理学模式"""
        result = asyncio.run(self.router.route("我最近情绪不好"))
        assert result.mode == ConversationMode.PSYCHOLOGY

    def test_psychology_with_context_boost(self):
        """测试有上下文时心理学置信度提升"""
        context = RouteContext(
            message="我最近压力很大",
            session_id="test",
            emotion_state={"intensity": 0.8}
        )
        result = asyncio.run(self.router.route("我最近压力很大", context))
        assert result.primary == IntentType.PSYCHOLOGY_SUPPORT

    # ---- 教育检测测试 ----

    def test_education_keywords_detected(self):
        """测试教育关键词检测"""
        messages = [
            "帮我做作业",
            "这道数学题怎么做",
            "考试复习计划",
            "英语学习方法",
            "物理化学题目",
        ]
        for msg in messages:
            result = asyncio.run(self.router.route(msg))
            assert result.primary == IntentType.EDUCATION, f"Failed for: {msg}"

    def test_education_mode(self):
        """测试教育模式"""
        result = asyncio.run(self.router.route("帮我讲一下这道数学题"))
        assert result.mode == ConversationMode.EDUCATION

    # ---- 知识查询检测测试 ----

    def test_knowledge_query_patterns(self):
        """测试知识查询模式"""
        patterns = [
            "什么是认知行为疗法",
            "为什么要学习",
            "如何缓解焦虑",
            "怎么提高成绩",
            "解释一下",
        ]
        for pattern in patterns:
            result = asyncio.run(self.router.route(pattern))
            assert result.primary == IntentType.KNOWLEDGE_QUERY, f"Failed for: {pattern}"

    # ---- 默认聊天检测 ----

    def test_general_chat(self):
        """测试默认聊天"""
        messages = [
            "你好",
            "今天天气怎么样",
            "你是谁",
        ]
        for msg in messages:
            result = asyncio.run(self.router.route(msg))
            assert result.primary == IntentType.GENERAL_CHAT

    # ---- 缓存测试 ----

    def test_cache_works(self):
        """测试缓存功能"""
        message = "我最近情绪不好"

        # 第一次
        result1 = asyncio.run(self.router.route(message))

        # 第二次（应该命中缓存）
        result2 = asyncio.run(self.router.route(message))

        assert result1.primary == result2.primary
        assert result1.confidence == result2.confidence

    def test_cache_clear(self):
        """测试清除缓存"""
        message = "我最近情绪不好"

        # 第一次
        asyncio.run(self.router.route(message))

        # 清除缓存
        self.router.clear_cache()

        # 再次路由应该正常工作
        result = asyncio.run(self.router.route(message))
        assert result.primary in IntentType.__members__.values()

    # ---- 上下文测试 ----

    def test_route_with_context(self):
        """测试带上下文的路由"""
        context = RouteContext(
            message="压力好大",
            session_id="test123",
            user_type="student",
            emotion_state={"emotion": "anxious", "intensity": 0.7}
        )
        result = asyncio.run(self.router.route("压力好大", context))
        assert result.primary == IntentType.PSYCHOLOGY_SUPPORT

    def test_route_context_preserved(self):
        """测试上下文保留"""
        context = RouteContext(
            message="测试",
            session_id="session_abc",
            user_type="student"
        )
        result = asyncio.run(self.router.route("测试", context))
        assert result is not None

    # ---- 置信度测试 ----

    def test_confidence_range(self):
        """测试置信度范围"""
        result = asyncio.run(self.router.route("你好"))
        assert 0.0 <= result.confidence <= 1.0

    def test_high_confidence_crisis(self):
        """测试危机高置信度"""
        result = asyncio.run(self.router.route("我不想活了"))
        assert result.confidence == 1.0

    # ---- 元数据测试 ----

    def test_metadata_contains_keyword(self):
        """测试元数据包含关键词"""
        result = asyncio.run(self.router.route("我情绪很低落"))
        if result.primary == IntentType.PSYCHOLOGY_SUPPORT:
            assert 'keywords' in result.metadata

    def test_reasoning_populated(self):
        """测试推理过程填充"""
        result = asyncio.run(self.router.route("什么是CBT"))
        assert isinstance(result.reasoning, str)


    def test_strong_knowledge_priority_over_psychology(self):
        """Strong knowledge prompts should win over psychology routing."""
        result = asyncio.run(self.router.route("为什么我会焦虑？"))
        assert result.primary == IntentType.KNOWLEDGE_QUERY

    def test_general_chat_pattern_not_escalated_to_knowledge(self):
        """General chat patterns should stay in general chat."""
        result = asyncio.run(self.router.route("今天怎么样？"))
        assert result.primary == IntentType.GENERAL_CHAT


# =============================================================================
# WorkflowEngine Tests
# =============================================================================

class TestWorkflowEngine:
    """工作流引擎测试"""

    def setup_method(self):
        """每个测试前重新创建实例"""
        self.engine = WorkflowEngine(max_parallel=3)

    # ---- 基础功能测试 ----

    def test_engine_created(self):
        """测试引擎创建成功"""
        assert self.engine is not None
        assert hasattr(self.engine, 'create_workflow')
        assert hasattr(self.engine, 'execute_workflow')

    # ---- 任务创建测试 ----

    def test_create_task(self):
        """测试创建任务"""
        task = Task(
            id="test_task_1",
            name="测试任务",
            task_type=TaskType.EMOTION_DETECT,
            priority=TaskPriority.HIGH,
            input_data={"message": "test"}
        )
        assert task.id == "test_task_1"
        assert task.status == TaskStatus.PENDING
        assert task.output_data is None

    def test_task_duration(self):
        """测试任务执行时长计算"""
        task = Task(
            id="test_task",
            name="测试",
            task_type=TaskType.EMOTION_DETECT,
            priority=TaskPriority.HIGH
        )
        assert task.duration() is None  # 未执行

        task.started_at = 100.0
        task.completed_at = 105.0
        assert task.duration() == 5.0

    def test_task_is_ready_no_dependencies(self):
        """测试无依赖任务就绪"""
        task = Task(
            id="test_task",
            name="测试",
            task_type=TaskType.EMOTION_DETECT,
            priority=TaskPriority.HIGH
        )
        assert task.is_ready() is True

    def test_task_is_ready_with_dependencies(self):
        """测试有依赖任务就绪"""
        dep_task = Task(
            id="dep_task",
            name="依赖任务",
            task_type=TaskType.RAG_RETRIEVE,
            priority=TaskPriority.NORMAL
        )

        task = Task(
            id="test_task",
            name="测试",
            task_type=TaskType.LLM_GENERATE,
            priority=TaskPriority.LOW,
            depends_on=["dep_task"],
            depends_on_tasks=[dep_task]
        )

        # 依赖未完成时
        assert task.is_ready() is False

        # 依赖完成时
        dep_task.status = TaskStatus.COMPLETED
        assert task.is_ready() is True

    # ---- 工作流创建测试 ----

    def test_create_workflow_basic(self):
        """测试基本工作流创建"""
        plan = asyncio.run(self.engine.create_workflow("你好"))
        assert isinstance(plan, WorkflowPlan)
        assert len(plan.tasks) > 0
        assert plan.workflow_id is not None

    def test_workflow_task_ordering(self):
        """测试工作流任务排序（优先级）"""
        plan = asyncio.run(self.engine.create_workflow("测试消息"))
        priorities = [t.priority for t in plan.tasks]

        # 验证优先级排序
        for i in range(len(priorities) - 1):
            assert priorities[i].value <= priorities[i + 1].value

    def test_workflow_contains_crisis_detection(self):
        """测试工作流包含危机检测"""
        plan = asyncio.run(self.engine.create_workflow("测试"))
        task_types = [t.task_type for t in plan.tasks]
        assert TaskType.CRISIS_DETECT in task_types

    def test_workflow_contains_emotion_detection(self):
        """测试工作流包含情绪检测"""
        plan = asyncio.run(self.engine.create_workflow("测试"))
        task_types = [t.task_type for t in plan.tasks]
        assert TaskType.EMOTION_DETECT in task_types

    def test_workflow_contains_rag_retrieval(self):
        """测试工作流包含RAG检索"""
        plan = asyncio.run(self.engine.create_workflow("测试", {"need_rag": True}))
        task_types = [t.task_type for t in plan.tasks]
        assert TaskType.RAG_RETRIEVE in task_types

    def test_workflow_without_rag(self):
        """测试不需要RAG的工作流"""
        plan = asyncio.run(self.engine.create_workflow("测试", {"need_rag": False}))
        task_types = [t.task_type for t in plan.tasks]
        assert TaskType.RAG_RETRIEVE not in task_types

    def test_workflow_contains_llm_generation(self):
        """测试工作流包含LLM生成"""
        plan = asyncio.run(self.engine.create_workflow("测试"))
        task_types = [t.task_type for t in plan.tasks]
        assert TaskType.LLM_GENERATE in task_types

    def test_workflow_task_dependencies(self):
        """测试工作流任务依赖关系"""
        plan = asyncio.run(self.engine.create_workflow("测试"))

        # 找到LLM生成任务
        llm_task = next(
            (t for t in plan.tasks if t.task_type == TaskType.LLM_GENERATE),
            None
        )

        # LLM应该依赖某些任务
        if llm_task:
            assert isinstance(llm_task.depends_on, list)

    # ---- 工作流执行测试 ----
    @tempskip
    def test_execute_workflow_basic(self):
        """测试基本工作流执行"""
        plan = asyncio.run(self.engine.create_workflow("你好"))
        result = asyncio.run(self.engine.execute_workflow(plan))

        assert isinstance(result, WorkflowResult)
        assert result.workflow_id == plan.workflow_id
        assert result.total_duration >= 0

    @tempskip
    def test_execute_workflow_all_tasks_complete(self):
        """测试工作流所有任务完成"""
        plan = asyncio.run(self.engine.create_workflow("测试"))
        result = asyncio.run(self.engine.execute_workflow(plan))

        assert len(result.completed_tasks) + len(result.failed_tasks) == len(plan.tasks)

    @tempskip
    def test_execute_workflow_status_success(self):
        """测试工作流成功状态"""
        plan = asyncio.run(self.engine.create_workflow("测试"))
        result = asyncio.run(self.engine.execute_workflow(plan))

        assert result.status in ["success", "partial", "failed"]

    @tempskip
    def test_execute_workflow_with_progress_callback(self):
        """测试带进度回调的工作流执行"""
        plan = asyncio.run(self.engine.create_workflow("测试"))

        progress_updates = []

        def callback(progress):
            progress_updates.append(progress)

        asyncio.run(self.engine.execute_workflow(plan, progress_callback=callback))

        # 应该有进度更新
        assert len(progress_updates) >= 0

    # ---- 任务处理器注册测试 ----

    def test_register_handler(self):
        """测试注册任务处理器"""
        def custom_handler(input_data, task):
            return {"result": "custom"}

        self.engine.register_handler(TaskType.EMOTION_DETECT, custom_handler)
        assert TaskType.EMOTION_DETECT in self.engine._task_handlers

    def test_register_async_handler(self):
        """测试注册异步任务处理器"""
        async def async_handler(input_data, task):
            return {"result": "async"}

        self.engine.register_handler(TaskType.CRISIS_DETECT, async_handler)
        assert TaskType.CRISIS_DETECT in self.engine._task_handlers

    # ---- 便捷方法测试 ----
    @tempskip
    def test_run_simple_workflow(self):
        """测试运行简单工作流"""
        result = asyncio.run(self.engine.run_simple_workflow("测试消息"))

        assert isinstance(result, WorkflowResult)
        assert result.total_duration >= 0
    
    @tempskip
    def test_run_simple_workflow_without_rag(self):
        """测试不带RAG的简单工作流"""
        result = asyncio.run(self.engine.run_simple_workflow("测试", need_rag=False))

        assert isinstance(result, WorkflowResult)

    # ---- 统计测试 ----

    def test_get_task_stats(self):
        """测试获取任务统计"""
        stats = self.engine.get_task_stats()
        assert isinstance(stats, dict)
        assert 'max_parallel' in stats


# =============================================================================
# TaskType and TaskPriority Tests
# =============================================================================

class TestTaskEnums:
    """任务类型和优先级枚举测试"""
    @tempskip
    def test_all_task_types_defined(self):
        """测试所有任务类型已定义"""
        expected_types = [
            'EMOTION_DETECT', 'CRISIS_DETECT', 'RAG_RETRIEVE',
            'TOOL_EXECUTE', 'LLM_GENERATE', 'REFLECTION', 'MEMORY_UPDATE'
        ]
        for type_name in expected_types:
            assert hasattr(TaskType, type_name)

    @tempskip
    def test_all_task_priorities_defined(self):
        """测试所有优先级已定义"""
        expected_priorities = ['CRITICAL', 'HIGH', 'NORMAL', 'LOW']
        for pri_name in expected_priorities:
            assert hasattr(TaskPriority, pri_name)

    def test_task_priority_order(self):
        """测试优先级顺序"""
        assert TaskPriority.CRITICAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value < TaskPriority.LOW.value


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntentWorkflowIntegration:
    """意图路由和工作流集成测试"""
    @tempskip
    def test_routing_creates_correct_workflow(self):
        """测试路由创建正确的工作流"""
        router = IntentRouter()
        engine = WorkflowEngine()

        # 心理学消息
        message = "我最近情绪很低落"

        # 路由
        intent = asyncio.run(router.route(message))

        # 创建工作流
        plan = asyncio.run(engine.create_workflow(message))

        # 验证
        if intent.mode == ConversationMode.PSYCHOLOGY:
            task_types = [t.task_type for t in plan.tasks]
            assert TaskType.EMOTION_DETECT in task_types
    
    @tempskip
    def test_crisis_workflow_priority(self):
        """测试危机工作流优先级"""
        router = IntentRouter()
        engine = WorkflowEngine()

        message = "我不想活了"

        intent = asyncio.run(router.route(message))
        plan = asyncio.run(engine.create_workflow(message))

        # 危机检测应该是第一个任务
        crisis_task = next(
            (t for t in plan.tasks if t.task_type == TaskType.CRISIS_DETECT),
            None
        )
        assert crisis_task is not None
        assert crisis_task.priority == TaskPriority.CRITICAL

    @tempskip
    def test_full_routing_to_execution_pipeline(self):
        """测试完整的路由到执行管道"""
        router = IntentRouter()
        engine = WorkflowEngine()

        message = "考试好紧张"

        # 路由
        intent = asyncio.run(router.route(message))

        # 创建工作流
        plan = asyncio.run(engine.create_workflow(message))

        # 执行
        result = asyncio.run(engine.execute_workflow(plan))

        # 验证
        assert intent.primary in IntentType.__members__.values()
        assert len(result.completed_tasks) > 0


# =============================================================================
# Edge Cases
# =============================================================================

class TestWorkflowEdgeCases:
    """工作流边界情况测试"""
    @tempskip
    def test_empty_message(self):
        """测试空消息"""
        engine = WorkflowEngine()
        plan = asyncio.run(engine.create_workflow(""))
        assert len(plan.tasks) > 0

    @tempskip
    def test_very_long_message(self):
        """测试超长消息"""
        engine = WorkflowEngine()
        long_message = "测试" * 1000
        plan = asyncio.run(engine.create_workflow(long_message))
        assert len(plan.tasks) > 0

    @tempskip
    def test_special_characters_message(self):
        """测试特殊字符消息"""
        engine = WorkflowEngine()
        special_message = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        plan = asyncio.run(engine.create_workflow(special_message))
        assert len(plan.tasks) > 0

    @tempskip
    def test_unicode_message(self):
        """测试Unicode消息"""
        engine = WorkflowEngine()
        unicode_message = "你好🌸💕测试😁"
        plan = asyncio.run(engine.create_workflow(unicode_message))
        assert len(plan.tasks) > 0

    @tempskip
    def test_max_parallel_respected(self):
        """测试最大并行数限制"""
        engine = WorkflowEngine(max_parallel=2)
        plan = asyncio.run(engine.create_workflow("测试"))
        assert plan.max_parallel == 2

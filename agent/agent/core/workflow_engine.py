"""
Workflow Engine - 工作流引擎
任务分解、优先级排序、执行监控
版本: v5.0
"""
import time
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, TYPE_CHECKING
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

if TYPE_CHECKING:
    pass

# ========== 枚举定义 ==========

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0    # 最高 - 危机干预
    HIGH = 1        # 高 - 紧急响应
    NORMAL = 2      # 普通
    LOW = 3         # 低 - 后台任务

class TaskType(Enum):
    """任务类型"""
    EMOTION_DETECT = "emotion_detect"
    CRISIS_DETECT = "crisis_detect"
    RAG_RETRIEVE = "rag_retrieve"
    TOOL_EXECUTE = "tool_execute"
    LLM_GENERATE = "llm_generate"
    REFLECTION = "reflection"
    MEMORY_UPDATE = "memory_update"

# ========== 数据模型 ==========

@dataclass
class Task:
    """任务单元"""
    id: str
    name: str
    task_type: TaskType
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING

    # 输入输出
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Any = None

    # 执行信息
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None

    # 依赖关系
    depends_on: List[str] = field(default_factory=list)  # 依赖的任务ID列表
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
    max_parallel: int = 3


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


# ========== 工作流引擎 ==========

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

    def __init__(
        self,
        max_parallel: int = 3,
        max_workflow_steps: int = 10,
        executor: Optional[ThreadPoolExecutor] = None
    ):
        self.max_parallel = max_parallel
        self.max_workflow_steps = max_workflow_steps
        self._executor = executor or ThreadPoolExecutor(max_workers=4)

        # 任务处理器注册表
        self._task_handlers: Dict[TaskType, Callable] = {}

        # 运行时状态
        self._running_tasks: Dict[str, Task] = {}
        self._completed_tasks: Dict[str, Task] = {}

    def register_handler(self, task_type: TaskType, handler: Callable) -> None:
        """
        注册任务处理器

        Args:
            task_type: 任务类型
            handler: 处理函数，接收 task.input_data，返回 task.output_data
        """
        self._task_handlers[task_type] = handler

    # ========== 任务分解 ==========

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
        tasks: List[Task] = []
        ctx = context or {}

        # 1. 危机检测（最高优先级）
        crisis_task = Task(
            id=f"{workflow_id}_crisis",
            name="危机检测",
            task_type=TaskType.CRISIS_DETECT,
            priority=TaskPriority.CRITICAL,
            input_data={"message": user_message}
        )
        tasks.append(crisis_task)

        # 2. 情绪检测（高优先级）
        emotion_task = Task(
            id=f"{workflow_id}_emotion",
            name="情绪识别",
            task_type=TaskType.EMOTION_DETECT,
            priority=TaskPriority.HIGH,
            input_data={"message": user_message}
        )
        tasks.append(emotion_task)

        # 3. RAG检索（如果有需要）
        if ctx.get("need_rag", True):
            rag_task = Task(
                id=f"{workflow_id}_rag",
                name="知识库检索",
                task_type=TaskType.RAG_RETRIEVE,
                priority=TaskPriority.NORMAL,
                input_data={"query": user_message, "n_results": 5}
            )
            tasks.append(rag_task)

        # 4. LLM生成（依赖RAG和心理学检测）
        llm_task = Task(
            id=f"{workflow_id}_llm",
            name="LLM响应生成",
            task_type=TaskType.LLM_GENERATE,
            priority=TaskPriority.LOW,
            depends_on=[t.id for t in tasks if t.task_type in (TaskType.RAG_RETRIEVE,)],
            input_data={"message": user_message}
        )
        tasks.append(llm_task)

        # 5. 反思（依赖LLM生成）
        reflection_task = Task(
            id=f"{workflow_id}_reflection",
            name="反思机制",
            task_type=TaskType.REFLECTION,
            priority=TaskPriority.LOW,
            depends_on=[llm_task.id],
            input_data={}
        )
        tasks.append(reflection_task)

        # 6. 记忆更新（最后执行）
        memory_task = Task(
            id=f"{workflow_id}_memory",
            name="记忆更新",
            task_type=TaskType.MEMORY_UPDATE,
            priority=TaskPriority.LOW,
            depends_on=[emotion_task.id, llm_task.id],
            input_data={"message": user_message}
        )
        tasks.append(memory_task)

        # 按优先级排序
        tasks.sort(key=lambda t: t.priority.value)

        return WorkflowPlan(
            workflow_id=workflow_id,
            tasks=tasks,
            context=ctx,
            max_parallel=self.max_parallel
        )

    # ========== 工作流执行 ==========

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
        task_map: Dict[str, Task] = {t.id: t for t in plan.tasks}

        # 设置依赖引用
        for task in plan.tasks:
            task.depends_on_tasks = [
                task_map[dep_id] for dep_id in task.depends_on
                if dep_id in task_map
            ]

        # 并行执行循环
        completed: List[Task] = []
        failed: List[Task] = []
        running: List[Task] = []

        while True:
            # 检查是否完成
            finished_count = len(completed) + len(failed)
            if finished_count >= len(plan.tasks):
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

            # 发送进度更新
            if progress_callback:
                progress_callback({
                    "completed": len(completed),
                    "running": len(running),
                    "pending": len(plan.tasks) - finished_count - len(running),
                    "failed": len(failed)
                })

            # 等待一小段时间，避免CPU空转
            await asyncio.sleep(0.05)

        # 收集结果
        final_output = None
        llm_task = next(
            (t for t in completed if t.task_type == TaskType.LLM_GENERATE),
            None
        )
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

            if handler:
                # 调用注册的处理函数
                if asyncio.iscoroutinefunction(handler):
                    task.output_data = await handler(task.input_data, task)
                else:
                    task.output_data = handler(task.input_data, task)
            else:
                # 使用默认处理
                task.output_data = await self._default_handler(task)

            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = time.time()

    async def _default_handler(self, task: Task) -> Any:
        """默认任务处理器"""
        task_type = task.task_type

        if task_type == TaskType.EMOTION_DETECT:
            from agent.modules.psychology.emotion import EmotionDetector
            detector = EmotionDetector()
            result = detector.detect(task.input_data.get("message", ""))
            return {
                "emotion": result.emotion.value,
                "intensity": result.intensity,
                "keywords": result.keywords
            }

        elif task_type == TaskType.CRISIS_DETECT:
            from agent.modules.psychology.crisis import CrisisDetector
            detector = CrisisDetector()
            result = detector.check(task.input_data.get("message", ""))
            return {
                "level": result.level.value,
                "signals": result.signals,
                "action": result.action
            }

        elif task_type == TaskType.RAG_RETRIEVE:
            try:
                from vectorstore import query_with_hybrid_search
                results = query_with_hybrid_search(
                    query_text=task.input_data.get("query", ""),
                    n_results=task.input_data.get("n_results", 5),
                    rerank=True
                )
                return {"results": results, "count": len(results)}
            except Exception:
                return {"results": [], "count": 0}

        elif task_type == TaskType.LLM_GENERATE:
            return {"status": "pending_llm"}

        elif task_type == TaskType.REFLECTION:
            return {"reflected": True}

        elif task_type == TaskType.MEMORY_UPDATE:
            return {"updated": True}

        return {"status": "completed"}

    # ========== 便捷方法 ==========

    async def run_simple_workflow(
        self,
        message: str,
        need_rag: bool = True
    ) -> WorkflowResult:
        """运行简单工作流（用于快速测试）"""
        plan = await self.create_workflow(message, {"need_rag": need_rag})
        return await self.execute_workflow(plan)

    def get_task_stats(self) -> Dict[str, Any]:
        """获取任务统计"""
        return {
            "running": len(self._running_tasks),
            "completed": len(self._completed_tasks),
            "max_parallel": self.max_parallel,
        }

"""
Tools 工具集成框架 - 标准化工具接口和注册机制
线程安全版本，完整类型提示
"""
import asyncio
import json
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Union, TypeVar, Generic
from enum import Enum
from pathlib import Path


@dataclass(frozen=True)
class ToolStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    status: ToolStatus
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: tuple = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if isinstance(self.metadata, dict):
            object.__setattr__(self, 'metadata', tuple(self.metadata.items()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "execution_time": round(self.execution_time, 3),
            "metadata": dict(self.metadata)
        }

    @property
    def is_success(self) -> bool:
        return self.status == ToolStatus.SUCCESS

    @property
    def metadata_dict(self) -> Dict[str, Any]:
        return dict(self.metadata)


@dataclass
class ToolParameter:
    name: str
    type: str
    description: str = ""
    required: bool = False
    default: Any = None


@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: List[ToolParameter]
    is_async: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default
                }
                for p in self.parameters
            ],
            "is_async": self.is_async
        }


class BaseTool(ABC):
    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        pass

    @abstractmethod
    def get_schema(self) -> ToolSchema:
        pass


class Tool:
    def __init__(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
        parameters: Optional[List[ToolParameter]] = None,
        is_async: bool = False
    ) -> None:
        self.name: str = name
        self.description: str = description
        self.func: Callable[..., Any] = func
        self.parameters: List[ToolParameter] = parameters or []
        self.is_async: bool = is_async
        self._lock: threading.RLock = threading.RLock()
        self._execution_count: int = 0
        self._total_execution_time: float = 0.0

    def execute(self, **kwargs: Any) -> ToolResult:
        start_time: float = time.time()
        try:
            valid, msg = self._validate_parameters(kwargs)
            if not valid:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.ERROR,
                    result=None,
                    error=msg,
                    execution_time=time.time() - start_time
                )

            if self.is_async:
                result: Any = asyncio.run(self._async_wrapper(**kwargs))
            else:
                result = self.func(**kwargs)

            with self._lock:
                self._execution_count += 1
                self._total_execution_time += time.time() - start_time

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                result=result,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            with self._lock:
                self._execution_count += 1

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                result=None,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def _async_wrapper(self, **kwargs: Any) -> Any:
        return await self.func(**kwargs)

    def _validate_parameters(self, params: Dict[str, Any]) -> tuple[bool, str]:
        for param_def in self.parameters:
            param_name = param_def.name
            if param_def.required and param_name not in params:
                return False, f"Missing required parameter: {param_name}"
        return True, ""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
            is_async=self.is_async
        )

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "execution_count": self._execution_count,
                "total_execution_time": round(self._total_execution_time, 3),
                "avg_execution_time": round(
                    self._total_execution_time / max(1, self._execution_count), 3
                )
            }


class ToolRegistry:
    _instance: Optional["ToolRegistry"] = None
    _lock_class: threading.RLock = threading.RLock()

    def __new__(cls) -> "ToolRegistry":
        if cls._instance is None:
            with cls._lock_class:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self._tools: Dict[str, Tool] = {}
        self._lock: threading.RLock = threading.RLock()
        self._initialized: bool = False

    def register(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
        parameters: Optional[List[Dict[str, Any]]] = None,
        is_async: bool = False
    ) -> None:
        tool_params: List[ToolParameter] = []
        if parameters:
            for p in parameters:
                tool_params.append(ToolParameter(
                    name=p.get("name", ""),
                    type=p.get("type", "string"),
                    description=p.get("description", ""),
                    required=p.get("required", False),
                    default=p.get("default")
                ))

        with self._lock:
            self._tools[name] = Tool(
                name=name,
                description=description,
                func=func,
                parameters=tool_params,
                is_async=is_async
            )

    def unregister(self, name: str) -> bool:
        with self._lock:
            if name in self._tools:
                del self._tools[name]
                return True
            return False

    def get(self, name: str) -> Optional[Tool]:
        with self._lock:
            return self._tools.get(name)

    def get_all(self) -> List[Tool]:
        with self._lock:
            return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [tool.get_schema().to_dict() for tool in self._tools.values()]

    def execute(self, name: str, **kwargs: Any) -> ToolResult:
        with self._lock:
            tool = self._tools.get(name)

        if tool is None:
            return ToolResult(
                tool_name=name,
                status=ToolStatus.ERROR,
                result=None,
                error=f"Tool '{name}' not found"
            )
        return tool.execute(**kwargs)

    def has_tool(self, name: str) -> bool:
        with self._lock:
            return name in self._tools

    def list_tools(self) -> List[str]:
        with self._lock:
            return list(self._tools.keys())

    def get_all_stats(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [tool.get_stats() for tool in self._tools.values()]

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock_class:
            cls._instance = None


def register_tool(
    name: Optional[str] = None,
    description: str = "",
    parameters: Optional[List[Dict[str, Any]]] = None,
    is_async: bool = False
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        tool_name: str = name or func.__name__
        registry: ToolRegistry = ToolRegistry()
        registry.register(
            name=tool_name,
            description=description or func.__doc__ or "",
            func=func,
            parameters=parameters,
            is_async=is_async
        )
        return func
    return decorator


class SafeCalculator:
    @staticmethod
    def calculate(expression: str) -> Union[float, str]:
        allowed_chars: set = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression"

        import ast
        import operator

        ops: Dict[type, Dict[str, Callable[[Any, Any], Any]]] = {
            ast.Add: {"op": operator.add, "symbol": "+"},
            ast.Sub: {"op": operator.sub, "symbol": "-"},
            ast.Mult: {"op": operator.mul, "symbol": "*"},
            ast.Div: {"op": operator.truediv, "symbol": "/"},
            ast.USub: {"op": operator.neg, "symbol": "-"},
        }

        def eval_node(node: ast.AST) -> Union[float, int]:
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    return node.value
                raise ValueError("Invalid constant")
            elif isinstance(node, ast.BinOp):
                left = eval_node(node.left)
                right = eval_node(node.right)
                op_type = type(node.op)
                if op_type not in ops:
                    raise ValueError(f"Unsupported operator: {op_type}")
                return ops[op_type]["op"](left, right)
            elif isinstance(node, ast.UnaryOp):
                operand = eval_node(node.operand)
                op_type = type(node.op)
                if op_type not in ops:
                    raise ValueError(f"Unsupported unary operator: {op_type}")
                return ops[op_type]["op"](operand)
            else:
                raise ValueError(f"Unsupported AST node: {type(node)}")

        try:
            tree = ast.parse(expression, mode="eval")
            result = eval_node(tree.body)
            return float(result) if isinstance(result, float) else result
        except (ValueError, SyntaxError, ZeroDivisionError) as e:
            return f"Error: {str(e)}"


class BuiltinTools:
    @staticmethod
    def search_knowledge_base(query: str, n_results: int = 5) -> Dict[str, Any]:
        try:
            from vectorstore import query_chroma
            results = query_chroma(
                query_text=query,
                n_results=n_results,
                persist_dir="data/chroma",
                collection_name="knowledge_base"
            )
            output: List[Dict[str, Any]] = []
            for doc, meta, dist in results:
                output.append({
                    "content": doc[:300],
                    "source": str(meta.get("source", "")),
                    "page": meta.get("page", ""),
                    "similarity": round(1 - dist, 4)
                })
            return {"ok": True, "results": output, "count": len(output)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @staticmethod
    def get_current_time() -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def calculate(expression: str) -> str:
        result: Union[float, str] = SafeCalculator.calculate(expression)
        return str(result)

    @staticmethod
    def search_web(query: str, num_results: int = 3) -> Dict[str, Any]:
        return {
            "ok": True,
            "query": query,
            "results": [
                {
                    "title": f"Result for '{query}' - {i+1}",
                    "snippet": f"Web search result {i+1}. Configure web search API for actual results."
                }
                for i in range(min(num_results, 3))
            ],
            "count": min(num_results, 3)
        }


def setup_builtin_tools() -> None:
    registry: ToolRegistry = ToolRegistry()

    registry.register(
        name="search_knowledge_base",
        description="Search the knowledge base for relevant documents.",
        func=BuiltinTools.search_knowledge_base,
        parameters=[
            {"name": "query", "type": "string", "description": "Search query", "required": True},
            {"name": "n_results", "type": "integer", "description": "Number of results", "required": False}
        ]
    )

    registry.register(
        name="get_current_time",
        description="Get the current date and time.",
        func=BuiltinTools.get_current_time,
        parameters=[]
    )

    registry.register(
        name="calculate",
        description="Perform mathematical calculations safely.",
        func=BuiltinTools.calculate,
        parameters=[
            {"name": "expression", "type": "string", "description": "Mathematical expression", "required": True}
        ]
    )

    registry.register(
        name="search_web",
        description="Search the web for information.",
        func=BuiltinTools.search_web,
        parameters=[
            {"name": "query", "type": "string", "description": "Web search query", "required": True},
            {"name": "num_results", "type": "integer", "description": "Number of results", "required": False}
        ]
    )

    _register_education_tools(registry)
    _register_psychology_tools(registry)


def _register_education_tools(registry: ToolRegistry) -> None:
    from agent.tools.education import (
        TeachingAssistant, LearningSupport, AssessmentSystem,
        TeachingManager, MoralEducation
    )

    ta = TeachingAssistant()
    ls = LearningSupport()
    ass = AssessmentSystem()
    tm = TeachingManager()
    me = MoralEducation()

    registry.register(
        name="generate_homework",
        description="Generate homework questions for a given topic.",
        func=ta.generate_homework,
        parameters=[
            {"name": "topic", "type": "string", "description": "Topic for homework", "required": True},
            {"name": "difficulty", "type": "string", "description": "Difficulty level", "required": False},
            {"name": "count", "type": "integer", "description": "Number of questions", "required": False}
        ]
    )

    registry.register(
        name="grade_homework",
        description="Grade student homework answers.",
        func=ta.grade_homework,
        parameters=[
            {"name": "questions", "type": "array", "description": "Questions with answers", "required": True},
            {"name": "student_answers", "type": "array", "description": "Student answers", "required": True}
        ]
    )

    registry.register(
        name="generate_lecture_notes",
        description="Generate lecture notes for a topic.",
        func=ta.generate_lecture_notes,
        parameters=[
            {"name": "topic", "type": "string", "description": "Lecture topic", "required": True}
        ]
    )

    registry.register(
        name="plan_learning_path",
        description="Plan a personalized learning path for a student.",
        func=ls.plan_learning_path,
        parameters=[
            {"name": "student_level", "type": "string", "description": "Student level", "required": True},
            {"name": "goal", "type": "string", "description": "Learning goal", "required": True}
        ]
    )

    registry.register(
        name="explain_concept",
        description="Explain a concept at appropriate level.",
        func=ls.explain_concept,
        parameters=[
            {"name": "concept", "type": "string", "description": "Concept to explain", "required": True},
            {"name": "level", "type": "string", "description": "Explanation level", "required": False}
        ]
    )

    registry.register(
        name="evaluate_answer",
        description="Evaluate a student's answer.",
        func=ass.evaluate_answer,
        parameters=[
            {"name": "question", "type": "string", "description": "The question", "required": True},
            {"name": "correct_answer", "type": "string", "description": "Correct answer", "required": True},
            {"name": "student_answer", "type": "string", "description": "Student's answer", "required": True}
        ]
    )

    registry.register(
        name="generate_feedback",
        description="Generate feedback based on evaluation.",
        func=ass.provide_feedback,
        parameters=[
            {"name": "evaluation", "type": "object", "description": "Evaluation result", "required": True}
        ]
    )

    registry.register(
        name="assess_mental_health",
        description="Assess student mental health from answers.",
        func=me.assess_mental_health,
        parameters=[
            {"name": "answers", "type": "array", "description": "Assessment answers", "required": True}
        ]
    )

    registry.register(
        name="recommend_activities",
        description="Recommend extracurricular activities.",
        func=me.recommend_activities,
        parameters=[
            {"name": "student_profile", "type": "object", "description": "Student profile", "required": True}
        ]
    )


def _register_psychology_tools(registry: ToolRegistry) -> None:
    """注册心理支持相关工具"""
    from agent.tools.psychology import get_psychology_tools

    pt = get_psychology_tools()

    # 情绪识别
    registry.register(
        name="detect_emotion",
        description="Detect user emotion from text input.",
        func=pt.detect_emotion,
        parameters=[
            {"name": "text", "type": "string", "description": "User input text", "required": True}
        ]
    )

    # 危机检测
    registry.register(
        name="check_crisis",
        description="Check for crisis signals (self-harm, suicide ideation).",
        func=pt.check_crisis,
        parameters=[
            {"name": "text", "type": "string", "description": "User input text", "required": True}
        ]
    )

    # 心理知识检索
    registry.register(
        name="search_psychology_knowledge",
        description="Search psychology knowledge base for mental health information.",
        func=pt.search_psychology_knowledge,
        parameters=[
            {"name": "query", "type": "string", "description": "Search query", "required": True},
            {"name": "user_type", "type": "string", "description": "User type (student/parent/teacher)", "required": False},
            {"name": "n_results", "type": "integer", "description": "Number of results", "required": False}
        ]
    )

    # 共情回复生成
    registry.register(
        name="generate_empathic_response",
        description="Generate empathic response for psychological support.",
        func=pt.generate_empathic_response,
        parameters=[
            {"name": "user_input", "type": "string", "description": "User input", "required": True},
            {"name": "emotion", "type": "string", "description": "Detected emotion type", "required": False},
            {"name": "context", "type": "object", "description": "Additional context", "required": False}
        ]
    )

    # 综合心理支持
    registry.register(
        name="psychological_support",
        description="Comprehensive psychological support: emotion detection + crisis check + knowledge retrieval + empathic response.",
        func=pt.psychological_support,
        parameters=[
            {"name": "user_input", "type": "string", "description": "User input", "required": True},
            {"name": "user_type", "type": "string", "description": "User type (student/parent/teacher)", "required": False}
        ]
    )
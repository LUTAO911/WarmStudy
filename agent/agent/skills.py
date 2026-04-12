"""
Skills 技能模块系统 - 模块化的技能注册、调用与组合
线程安全版本，完整类型提示
"""
import time
import uuid
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
import concurrent.futures


class SkillStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True)
class SkillResult:
    skill_name: str
    status: SkillStatus
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: tuple = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if isinstance(self.metadata, dict):
            object.__setattr__(self, 'metadata', tuple(self.metadata.items()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "execution_time": round(self.execution_time, 3),
            "metadata": dict(self.metadata)
        }

    @property
    def is_success(self) -> bool:
        return self.status == SkillStatus.SUCCESS

    @property
    def metadata_dict(self) -> Dict[str, Any]:
        return dict(self.metadata)


@dataclass
class SkillParameter:
    name: str
    type: str
    description: str = ""
    required: bool = False
    default: Any = None


@dataclass
class SkillSchema:
    name: str
    description: str
    version: str
    parameters: List[SkillParameter]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default
                }
                for p in self.parameters
            ]
        }


class BaseSkill(ABC):
    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> SkillResult:
        pass

    @abstractmethod
    def get_schema(self) -> SkillSchema:
        pass


class Skill:
    def __init__(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
        parameters: Optional[List[SkillParameter]] = None,
        required_params: Optional[List[str]] = None,
        is_async: bool = False,
        version: str = "1.0.0"
    ) -> None:
        self.name: str = name
        self.description: str = description
        self.func: Callable[..., Any] = func
        self.parameters: List[SkillParameter] = parameters or []
        self.required_params: List[str] = required_params or []
        self.is_async: bool = is_async
        self.version: str = version
        self._lock: threading.RLock = threading.RLock()
        self._usage_count: int = 0
        self._total_execution_time: float = 0.0

    def validate(self, params: Dict[str, Any]) -> tuple[bool, str]:
        for param_name in self.required_params:
            if param_name not in params:
                return False, f"Missing required parameter: {param_name}"
        return True, ""

    def execute(self, params: Dict[str, Any]) -> SkillResult:
        start_time: float = time.time()
        try:
            valid, msg = self.validate(params)
            if not valid:
                return SkillResult(
                    skill_name=self.name,
                    status=SkillStatus.FAILED,
                    output=None,
                    error=msg,
                    execution_time=time.time() - start_time
                )

            if self.is_async:
                import asyncio
                output: Any = asyncio.run(self.func(**params))
            else:
                output = self.func(**params)

            with self._lock:
                self._usage_count += 1
                self._total_execution_time += time.time() - start_time

            return SkillResult(
                skill_name=self.name,
                status=SkillStatus.SUCCESS,
                output=output,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            with self._lock:
                self._usage_count += 1

            return SkillResult(
                skill_name=self.name,
                status=SkillStatus.FAILED,
                output=None,
                error=str(e),
                execution_time=time.time() - start_time
            )

    def get_schema(self) -> SkillSchema:
        return SkillSchema(
            name=self.name,
            description=self.description,
            version=self.version,
            parameters=self.parameters
        )

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "usage_count": self._usage_count,
                "total_execution_time": round(self._total_execution_time, 3),
                "avg_execution_time": round(
                    self._total_execution_time / max(1, self._usage_count), 3
                )
            }


class SkillRegistry:
    _instance: Optional["SkillRegistry"] = None
    _lock_class: threading.RLock = threading.RLock()

    def __new__(cls) -> "SkillRegistry":
        if cls._instance is None:
            with cls._lock_class:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self._skills: Dict[str, Skill] = {}
        self._categories: Dict[str, List[str]] = {}
        self._lock: threading.RLock = threading.RLock()

    def register(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
        params_schema: Optional[List[Dict[str, Any]]] = None,
        required_params: Optional[List[str]] = None,
        category: str = "general",
        is_async: bool = False,
        version: str = "1.0.0"
    ) -> None:
        skill_params: List[SkillParameter] = []
        if params_schema:
            for p in params_schema:
                skill_params.append(SkillParameter(
                    name=p.get("name", ""),
                    type=p.get("type", "string"),
                    description=p.get("description", ""),
                    required=p.get("required", False),
                    default=p.get("default")
                ))

        with self._lock:
            self._skills[name] = Skill(
                name=name,
                description=description,
                func=func,
                parameters=skill_params,
                required_params=required_params,
                is_async=is_async,
                version=version
            )

            if category not in self._categories:
                self._categories[category] = []
            if name not in self._categories[category]:
                self._categories[category].append(name)

    def unregister(self, name: str) -> bool:
        with self._lock:
            if name in self._skills:
                del self._skills[name]
                for cat_list in self._categories.values():
                    if name in cat_list:
                        cat_list.remove(name)
                return True
            return False

    def get(self, name: str) -> Optional[Skill]:
        with self._lock:
            return self._skills.get(name)

    def get_all(self) -> List[Skill]:
        with self._lock:
            return list(self._skills.values())

    def get_by_category(self, category: str) -> List[Skill]:
        with self._lock:
            skill_names = self._categories.get(category, [])
            return [self._skills[name] for name in skill_names if name in self._skills]

    def list_categories(self) -> List[str]:
        with self._lock:
            return list(self._categories.keys())

    def get_all_schemas(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "categories": {
                    cat: [self._skills[name].get_schema().to_dict() for name in names]
                    for cat, names in self._categories.items()
                },
                "skills": {
                    name: skill.get_schema().to_dict()
                    for name, skill in self._skills.items()
                }
            }

    def execute(self, name: str, params: Dict[str, Any]) -> SkillResult:
        with self._lock:
            skill = self._skills.get(name)

        if skill is None:
            return SkillResult(
                skill_name=name,
                status=SkillStatus.FAILED,
                output=None,
                error=f"Skill '{name}' not found"
            )
        return skill.execute(params)

    def has_skill(self, name: str) -> bool:
        with self._lock:
            return name in self._skills

    def list_skills(self) -> List[str]:
        with self._lock:
            return list(self._skills.keys())

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock_class:
            cls._instance = None


def register_skill(
    name: Optional[str] = None,
    description: str = "",
    params_schema: Optional[List[Dict[str, Any]]] = None,
    required_params: Optional[List[str]] = None,
    category: str = "general",
    is_async: bool = False,
    version: str = "1.0.0"
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        skill_name: str = name or func.__name__
        registry: SkillRegistry = SkillRegistry()
        registry.register(
            name=skill_name,
            description=description or func.__doc__ or "",
            func=func,
            params_schema=params_schema,
            required_params=required_params,
            category=category,
            is_async=is_async,
            version=version
        )
        return func
    return decorator


class SkillComposer:
    def __init__(self, registry: SkillRegistry) -> None:
        self.registry: SkillRegistry = registry

    def compose_sequential(
        self,
        skill_names: List[str],
        initial_input: Any,
        param_generator: Optional[Callable[[str, Any], Dict[str, Any]]] = None
    ) -> List[SkillResult]:
        results: List[SkillResult] = []
        current_input: Any = initial_input

        for skill_name in skill_names:
            params: Dict[str, Any] = param_generator(skill_name, current_input) if param_generator else {}
            result: SkillResult = self.registry.execute(skill_name, params)
            results.append(result)

            if not result.is_success:
                break

            current_input = result.output

        return results

    def compose_parallel(
        self,
        skill_names: List[str],
        params: Dict[str, Dict[str, Any]]
    ) -> List[SkillResult]:
        results: List[SkillResult] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(skill_names)) as executor:
            future_to_skill: Dict[concurrent.futures.Future, str] = {}
            for skill_name in skill_names:
                skill_params: Dict[str, Any] = params.get(skill_name, {})
                future = executor.submit(self.registry.execute, skill_name, skill_params)
                future_to_skill[future] = skill_name

            for future in concurrent.futures.as_completed(future_to_skill):
                skill_name = future_to_skill[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(SkillResult(
                        skill_name=skill_name,
                        status=SkillStatus.FAILED,
                        output=None,
                        error=str(e)
                    ))

        return results


class BuiltinSkills:
    @staticmethod
    def summarize_text(text: str, max_length: int = 200) -> str:
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."

    @staticmethod
    def extract_keywords(text: str, num: int = 5) -> List[str]:
        words = text.split()
        word_freq: Dict[str, int] = {}
        for word in words:
            if len(word) > 2:
                word_freq[word] = word_freq.get(word, 0) + 1
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [w[0] for w in sorted_words[:num]]

    @staticmethod
    def format_response(data: Dict[str, Any], format_type: str = "json") -> str:
        if format_type == "json":
            import json
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif format_type == "text":
            lines: List[str] = []
            for key, value in data.items():
                lines.append(f"{key}: {value}")
            return "\n".join(lines)
        return str(data)


def setup_builtin_skills() -> None:
    registry: SkillRegistry = SkillRegistry()

    registry.register(
        name="summarize",
        description="Summarize long text into shorter form",
        func=BuiltinSkills.summarize_text,
        params_schema=[
            {"name": "text", "type": "string", "description": "Text to summarize"},
            {"name": "max_length", "type": "integer", "description": "Maximum length"}
        ],
        required_params=["text"],
        category="text_processing"
    )

    registry.register(
        name="extract_keywords",
        description="Extract keywords from text",
        func=BuiltinSkills.extract_keywords,
        params_schema=[
            {"name": "text", "type": "string", "description": "Text to extract from"},
            {"name": "num", "type": "integer", "description": "Number of keywords"}
        ],
        required_params=["text"],
        category="text_processing"
    )

    registry.register(
        name="format_response",
        description="Format data into different output formats",
        func=BuiltinSkills.format_response,
        params_schema=[
            {"name": "data", "type": "object", "description": "Data to format"},
            {"name": "format_type", "type": "string", "description": "Output format"}
        ],
        required_params=["data"],
        category="utilities"
    )
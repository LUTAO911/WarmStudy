"""
Prompts 提示词工程 - 优化的提示词模板与管理机制
线程安全版本，完整类型提示
"""
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Iterator
from string import Template


@dataclass(frozen=True)
class PromptTemplate:
    name: str
    template: str
    description: str = ""
    variables: tuple = field(default_factory=tuple)
    metadata: tuple = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if isinstance(self.variables, list):
            object.__setattr__(self, 'variables', tuple(self.variables))
        if isinstance(self.metadata, dict):
            object.__setattr__(self, 'metadata', tuple(self.metadata.items()))

    def render(self, **kwargs: Any) -> str:
        try:
            template_obj = Template(self.template)
            return template_obj.safe_substitute(**kwargs)
        except Exception as e:
            return f"Error rendering template: {e}"

    def validate_variables(self, **kwargs: Any) -> tuple[bool, List[str]]:
        missing: List[str] = []
        for var in self.variables:
            if var not in kwargs:
                missing.append(var)
        return len(missing) == 0, missing

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "variables": list(self.variables),
            "metadata": dict(self.metadata),
            "template_preview": self.template[:200] + "..." if len(self.template) > 200 else self.template
        }


class PromptManager:
    _instance: Optional["PromptManager"] = None
    _lock_class: threading.RLock = threading.RLock()

    def __new__(cls) -> "PromptManager":
        if cls._instance is None:
            with cls._lock_class:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self._templates: Dict[str, PromptTemplate] = {}
        self._lock: threading.RLock = threading.RLock()
        self._initialized: bool = False
        self._setup_default_templates()

    def _setup_default_templates(self) -> None:
        self.register(PromptTemplate(
            name="system_prompt",
            template="""You are a helpful AI assistant developed for the "暖学帮" (Warm Learning Helper) educational platform.
Your goal is to provide accurate, informative, and educational responses to users.
Current time: ${current_time}
""",
            description="Default system prompt for the AI assistant",
            variables=("current_time",)
        ))

        self.register(PromptTemplate(
            name="rag_prompt",
            template="""Based on the following context from the knowledge base, answer the user's question.

---
Context:
${context}
---

Question: ${question}

Please provide a helpful and accurate response based on the context above. If the context doesn't contain relevant information, say so honestly.""",
            description="Prompt template for RAG-based question answering",
            variables=("context", "question")
        ))

        self.register(PromptTemplate(
            name="agent_prompt",
            template="""You are an intelligent agent with access to various tools and skills.

Available Tools:
${tools_info}

Conversation History:
${history}

Relevant Context:
${context}

Current Task: ${task}

Think step by step and use the appropriate tools when needed. Provide a clear and helpful response.""",
            description="Prompt template for agent with tool usage",
            variables=("tools_info", "history", "context", "task")
        ))

        self.register(PromptTemplate(
            name="skill_prompt",
            template="""Execute the following skill: ${skill_name}

Skill Description: ${skill_description}

Input Parameters:
${parameters}

Please execute the skill and provide the result.""",
            description="Prompt for skill execution",
            variables=("skill_name", "skill_description", "parameters")
        ))

        self.register(PromptTemplate(
            name="summarization_prompt",
            template="""Please summarize the following text concisely:

${text}

Summary (in ${max_length} characters or less):""",
            description="Prompt for text summarization",
            variables=("text", "max_length")
        ))

        self.register(PromptTemplate(
            name="analysis_prompt",
            template="""Analyze the following content and provide insights:

${content}

Please provide:
1. Key points
2. Main conclusions
3. Any relevant recommendations""",
            description="Prompt for content analysis",
            variables=("content",)
        ))

        self.register(PromptTemplate(
            name="code_generation_prompt",
            template="""Generate code for the following task:

Task: ${task}
Language/Framework: ${language}
Additional Requirements: ${requirements}

Please provide well-commented, production-ready code.""",
            description="Prompt for code generation",
            variables=("task", "language", "requirements")
        ))

    def register(self, template: PromptTemplate) -> None:
        with self._lock:
            self._templates[template.name] = template

    def get(self, name: str) -> Optional[PromptTemplate]:
        with self._lock:
            return self._templates.get(name)

    def unregister(self, name: str) -> bool:
        with self._lock:
            if name in self._templates:
                del self._templates[name]
                return True
            return False

    def render(self, name: str, **kwargs: Any) -> str:
        with self._lock:
            template = self._templates.get(name)

        if template is None:
            return f"Template '{name}' not found"

        valid, missing = template.validate_variables(**kwargs)
        if not valid:
            return f"Missing required variables: {', '.join(missing)}"

        return template.render(**kwargs)

    def list_templates(self) -> List[str]:
        with self._lock:
            return list(self._templates.keys())

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [t.get_schema() for t in self._templates.values()]

    def update_template(self, name: str, template: PromptTemplate) -> bool:
        with self._lock:
            if name in self._templates:
                self._templates[name] = template
                return True
            return False

    def create_custom_template(
        self,
        name: str,
        template_string: str,
        description: str = "",
        auto_detect_variables: bool = True
    ) -> Optional[PromptTemplate]:
        variables: tuple = ()
        if auto_detect_variables:
            found = re.findall(r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}', template_string)
            variables = tuple(found)

        template = PromptTemplate(
            name=name,
            template=template_string,
            description=description,
            variables=variables
        )
        self.register(template)
        return template

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock_class:
            cls._instance = None


class DynamicPromptBuilder:
    def __init__(self, prompt_manager: PromptManager) -> None:
        self.prompt_manager: PromptManager = prompt_manager

    def build_rag_prompt(
        self,
        question: str,
        context_results: List[Dict[str, Any]],
        include_sources: bool = True
    ) -> str:
        if not context_results:
            context: str = "No relevant context found in the knowledge base."
        else:
            context_parts: List[str] = []
            for i, result in enumerate(context_results):
                source: str = result.get("source", "Unknown")
                page: str = result.get("page", "N/A")
                content: str = result.get("content", "")
                similarity: float = result.get("similarity", 0)

                context_parts.append(
                    f"[Source {i+1}] (Similarity: {similarity:.2%})\n"
                    f"File: {source} (Page {page})\n"
                    f"Content: {content[:500]}"
                )
            context = "\n\n".join(context_parts)

        prompt: str = self.prompt_manager.render("rag_prompt", context=context, question=question)

        if include_sources and context_results:
            sources_info: str = "\n\n".join(
                f"{i+1}. {r.get('source', 'Unknown')}"
                for i, r in enumerate(context_results[:3])
            )
            prompt += f"\n\nRelevant Sources:\n{sources_info}"

        return prompt

    def build_agent_prompt(
        self,
        task: str,
        tools_schemas: List[Dict[str, Any]],
        history: str = "",
        context: str = ""
    ) -> str:
        tools_info: str = "\n".join(
            f"- {t['name']}: {t['description']}"
            for t in tools_schemas
        )

        return self.prompt_manager.render(
            "agent_prompt",
            tools_info=tools_info or "No tools available",
            history=history or "No conversation history",
            context=context or "No additional context",
            task=task
        )

    def build_multi_turn_prompt(
        self,
        current_message: str,
        history: List[Dict[str, str]],
        system_context: str = ""
    ) -> str:
        history_text: str = ""
        if history:
            for msg in history[-10:]:
                role: str = msg.get("role", "user")
                content: str = msg.get("content", "")
                history_text += f"\n{role.capitalize()}: {content}"

        full_prompt: str = f"{system_context}\n\nConversation History:{history_text}\n\nUser: {current_message}\n\nAssistant:"
        return full_prompt


def create_react_prompt(question: str, tools_info: str, context: str = "") -> str:
    context_section: str = f"Context from knowledge base:\n{context}" if context else ""
    return f"""You are a reasoning agent that uses a think-act-observe loop.

Task: {question}

Available Tools:
{tools_info}

{context_section}

Follow this format:
Thought: Think about what to do
Action: Execute a tool (e.g., search_knowledge_base, calculate)
Observation: Observe the result
... (repeat as needed)
Final Answer: Provide the final response

Let's begin:
Thought:"""
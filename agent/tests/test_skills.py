"""
Unit tests for Skills module
"""
import pytest
from typing import Dict, Any

from agent.skills import (
    SkillResult,
    SkillStatus,
    SkillParameter,
    SkillSchema,
    Skill,
    SkillRegistry,
    BuiltinSkills,
    SkillComposer,
    setup_builtin_skills,
)


class TestSkillResult:
    """Tests for SkillResult dataclass."""

    def test_success_result(self) -> None:
        """Test creating a successful skill result."""
        result = SkillResult(
            skill_name="summarize",
            status=SkillStatus.SUCCESS,
            output="Summary text",
            execution_time=0.5,
        )
        assert result.is_success is True
        assert result.output == "Summary text"

    def test_failed_result(self) -> None:
        """Test creating a failed skill result."""
        result = SkillResult(
            skill_name="process",
            status=SkillStatus.FAILED,
            output=None,
            error="Processing failed",
            execution_time=0.1,
        )
        assert result.is_success is False
        assert result.error == "Processing failed"


class TestSkillParameter:
    """Tests for SkillParameter dataclass."""

    def test_create_parameter(self) -> None:
        """Test creating a skill parameter."""
        param = SkillParameter(
            name="text",
            type="string",
            description="Text to process",
            required=True,
        )
        assert param.name == "text"
        assert param.required is True


class TestSkillSchema:
    """Tests for SkillSchema."""

    def test_schema_to_dict(self) -> None:
        """Test converting schema to dictionary."""
        schema = SkillSchema(
            name="format",
            description="Format data",
            version="1.0.0",
            parameters=[],
        )
        data = schema.to_dict()
        assert data["name"] == "format"
        assert data["version"] == "1.0.0"


class TestSkill:
    """Tests for Skill class."""

    def test_execute_success(self) -> None:
        """Test successful skill execution."""
        def upper(text: str) -> str:
            return text.upper()

        skill = Skill(
            name="uppercase",
            description="Convert text to uppercase",
            func=upper,
            required_params=["text"],
        )
        result = skill.execute({"text": "hello"})
        assert result.is_success is True
        assert result.output == "HELLO"

    def test_execute_with_missing_params(self) -> None:
        """Test execution with missing parameters."""
        def add(a: int, b: int) -> int:
            return a + b

        skill = Skill(
            name="add",
            description="Add two numbers",
            func=add,
            required_params=["a", "b"],
        )
        result = skill.execute({"a": 5})
        assert result.is_success is False
        assert "Missing required parameter" in result.error

    def test_execute_with_exception(self) -> None:
        """Test execution that raises an exception."""
        def fail() -> None:
            raise RuntimeError("Skill failed")

        skill = Skill(name="failing", description="Always fails", func=fail)
        result = skill.execute({})
        assert result.is_success is False
        assert "Skill failed" in result.error


class TestSkillRegistry:
    """Tests for SkillRegistry singleton."""

    def test_singleton_pattern(self) -> None:
        """Test that registry is a singleton."""
        registry1 = SkillRegistry()
        registry2 = SkillRegistry()
        assert registry1 is registry2

    def test_register_and_execute(self) -> None:
        """Test registering and executing a skill."""
        registry = SkillRegistry()
        registry.reset_instance()

        def greet(name: str) -> str:
            return f"Hello, {name}!"

        registry.register(
            name="greet",
            description="Greet someone",
            func=greet,
            params_schema=[{"name": "name", "type": "string", "required": True}],
            required_params=["name"],
        )

        result = registry.execute("greet", {"name": "Alice"})
        assert result.is_success is True
        assert "Alice" in result.output

    def test_execute_nonexistent_skill(self) -> None:
        """Test executing a skill that doesn't exist."""
        registry = SkillRegistry()
        registry.reset_instance()
        result = registry.execute("nonexistent", {})
        assert result.is_success is False
        assert "not found" in result.error

    def test_get_by_category(self) -> None:
        """Test getting skills by category."""
        registry = SkillRegistry()
        registry.reset_instance()

        registry.register(
            name="skill1",
            description="Text skill",
            func=lambda: None,
            category="text",
        )
        registry.register(
            name="skill2",
            description="Data skill",
            func=lambda: None,
            category="data",
        )

        text_skills = registry.get_by_category("text")
        assert len(text_skills) == 1


class TestBuiltinSkills:
    """Tests for BuiltinSkills."""

    def test_summarize_text(self) -> None:
        """Test text summarization."""
        text = "A" * 300
        result = BuiltinSkills.summarize_text(text, max_length=100)
        assert len(result) <= 103
        assert result.endswith("...")

    def test_summarize_short_text(self) -> None:
        """Test summarizing short text (no change needed)."""
        text = "Short text"
        result = BuiltinSkills.summarize_text(text, max_length=100)
        assert result == "Short text"

    def test_extract_keywords(self) -> None:
        """Test keyword extraction."""
        text = "Python Python Python Java Java Ruby"
        keywords = BuiltinSkills.extract_keywords(text, num=2)
        assert len(keywords) == 2
        assert "Python" in keywords

    def test_format_response_json(self) -> None:
        """Test JSON formatting."""
        data = {"name": "test", "value": 42}
        result = BuiltinSkills.format_response(data, "json")
        assert "name" in result
        assert "test" in result

    def test_format_response_text(self) -> None:
        """Test text formatting."""
        data = {"name": "test", "value": 42}
        result = BuiltinSkills.format_response(data, "text")
        assert "name: test" in result
        assert "value: 42" in result


class TestSkillComposer:
    """Tests for SkillComposer."""

    def test_compose_sequential(self) -> None:
        """Test sequential skill composition."""
        registry = SkillRegistry()
        registry.reset_instance()

        registry.register(
            name="double",
            description="Double a number",
            func=lambda x: x * 2,
            required_params=["x"],
        )
        registry.register(
            name="add_one",
            description="Add one to a number",
            func=lambda x: x + 1,
            required_params=["x"],
        )

        composer = SkillComposer(registry)
        results = composer.compose_sequential(
            ["double", "add_one"],
            initial_input=5,
            param_generator=lambda skill, prev: {"x": prev}
        )

        assert len(results) == 2
        assert results[0].output == 10
        assert results[1].output == 11

    def test_compose_sequential_stops_on_failure(self) -> None:
        """Test that sequential composition stops on failure."""
        registry = SkillRegistry()
        registry.reset_instance()

        def succeed(x: int) -> int:
            return x * 2

        def fail(x: int) -> int:
            raise ValueError("Intentional failure")

        registry.register(name="success", description="Succeeds", func=succeed, required_params=["x"])
        registry.register(name="fail", description="Fails", func=fail, required_params=["x"])

        composer = SkillComposer(registry)
        results = composer.compose_sequential(
            ["success", "fail", "success"],
            initial_input=5,
            param_generator=lambda skill, prev: {"x": prev}
        )

        assert len(results) == 2
        assert results[1].is_success is False
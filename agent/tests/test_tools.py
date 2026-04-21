"""
Unit tests for Tools module
"""
import pytest
from typing import Dict, Any

from agent.tools import (
    ToolResult,
    ToolStatus,
    ToolParameter,
    ToolSchema,
    Tool,
    ToolRegistry,
    BuiltinTools,
    SafeCalculator,
    setup_builtin_tools,
)


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_success_result(self) -> None:
        """Test creating a successful result."""
        result = ToolResult(
            tool_name="test_tool",
            status=ToolStatus.SUCCESS,
            result={"output": "success"},
            execution_time=0.5,
        )
        assert result.is_success is True
        assert result.result == {"output": "success"}

    def test_error_result(self) -> None:
        """Test creating an error result."""
        result = ToolResult(
            tool_name="test_tool",
            status=ToolStatus.ERROR,
            result=None,
            error="Something went wrong",
            execution_time=0.1,
        )
        assert result.is_success is False
        assert result.error == "Something went wrong"

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        result = ToolResult(
            tool_name="my_tool",
            status=ToolStatus.SUCCESS,
            result="data",
            execution_time=1.0,
            metadata={"key": "value"},
        )
        data = result.to_dict()
        assert data["tool_name"] == "my_tool"
        assert data["status"] == "success"
        assert data["metadata"] == {"key": "value"}


class TestToolParameter:
    """Tests for ToolParameter dataclass."""

    def test_create_parameter(self) -> None:
        """Test creating a tool parameter."""
        param = ToolParameter(
            name="query",
            type="string",
            description="Search query",
            required=True,
        )
        assert param.name == "query"
        assert param.required is True


class TestToolSchema:
    """Tests for ToolSchema."""

    def test_schema_to_dict(self) -> None:
        """Test converting schema to dictionary."""
        schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            parameters=[],
            is_async=False,
        )
        data = schema.to_dict()
        assert data["name"] == "test_tool"
        assert data["description"] == "A test tool"


class TestTool:
    """Tests for Tool class."""

    def test_execute_success(self) -> None:
        """Test successful tool execution."""
        def multiply(a: int, b: int) -> int:
            return a * b

        tool = Tool(
            name="multiply",
            description="Multiply two numbers",
            func=multiply,
        )
        result = tool.execute(a=5, b=3)
        assert result.is_success is True
        assert result.result == 15

    def test_execute_with_missing_params(self) -> None:
        """Test execution with missing required parameters."""
        def add(a: int, b: int) -> int:
            return a + b

        tool = Tool(
            name="add",
            description="Add two numbers",
            func=add,
            parameters=[
                ToolParameter(name="a", type="int", required=True),
                ToolParameter(name="b", type="int", required=True),
            ],
        )
        result = tool.execute(a=5)
        assert result.is_success is False
        assert "Missing required parameter" in result.error

    def test_execute_with_exception(self) -> None:
        """Test execution that raises an exception."""
        def failing_function() -> None:
            raise ValueError("Intentional error")

        tool = Tool(name="fail", description="Always fails", func=failing_function)
        result = tool.execute()
        assert result.is_success is False
        assert "Intentional error" in result.error


class TestToolRegistry:
    """Tests for ToolRegistry singleton."""

    def test_singleton_pattern(self) -> None:
        """Test that registry is a singleton."""
        registry1 = ToolRegistry()
        registry2 = ToolRegistry()
        assert registry1 is registry2

    def test_register_and_get(self) -> None:
        """Test registering and retrieving a tool."""
        registry = ToolRegistry()
        registry.reset_instance()

        def dummy_tool() -> str:
            return "dummy"

        registry.register(
            name="dummy",
            description="A dummy tool",
            func=dummy_tool,
        )
        tool = registry.get("dummy")
        assert tool is not None
        assert tool.name == "dummy"

    def test_execute_registered_tool(self) -> None:
        """Test executing a registered tool."""
        registry = ToolRegistry()
        registry.reset_instance()

        def echo(message: str) -> str:
            return message

        registry.register(
            name="echo",
            description="Echo a message",
            func=echo,
            parameters=[{"name": "message", "type": "string", "required": True}],
        )
        result = registry.execute("echo", message="Hello!")
        assert result.is_success is True
        assert result.result == "Hello!"

    def test_execute_nonexistent_tool(self) -> None:
        """Test executing a tool that doesn't exist."""
        registry = ToolRegistry()
        registry.reset_instance()
        result = registry.execute("nonexistent")
        assert result.is_success is False
        assert "not found" in result.error


class TestSafeCalculator:
    """Tests for SafeCalculator."""

    def test_basic_arithmetic(self) -> None:
        """Test basic arithmetic operations."""
        assert SafeCalculator.calculate("2 + 3") == 5.0
        assert SafeCalculator.calculate("10 - 4") == 6.0
        assert SafeCalculator.calculate("3 * 4") == 12.0
        assert SafeCalculator.calculate("15 / 3") == 5.0

    def test_order_of_operations(self) -> None:
        """Test that order of operations is correct."""
        assert SafeCalculator.calculate("2 + 3 * 4") == 14.0
        assert SafeCalculator.calculate("(2 + 3) * 4") == 20.0

    def test_decimal_result(self) -> None:
        """Test decimal results."""
        result = SafeCalculator.calculate("10 / 4")
        assert result == 2.5

    def test_negative_numbers(self) -> None:
        """Test negative numbers."""
        assert SafeCalculator.calculate("-5 + 3") == -2.0
        assert SafeCalculator.calculate("-3 * -2") == 6.0

    def test_invalid_characters(self) -> None:
        """Test that invalid characters are rejected."""
        result = SafeCalculator.calculate("2 + abc")
        assert isinstance(result, str)
        assert "Invalid characters" in result

    def test_division_by_zero(self) -> None:
        """Test division by zero handling."""
        result = SafeCalculator.calculate("5 / 0")
        assert isinstance(result, str)
        assert "Error" in result


class TestBuiltinTools:
    """Tests for BuiltinTools."""

    def test_get_current_time(self) -> None:
        """Test getting current time."""
        result = BuiltinTools.get_current_time()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_calculate(self) -> None:
        """Test calculate tool."""
        result = BuiltinTools.calculate("2 + 3 * 4")
        assert result == "14.0"

    def test_search_web(self) -> None:
        """Test web search placeholder."""
        result = BuiltinTools.search_web("python", num_results=3)
        assert result["ok"] is True
        assert result["count"] == 3

    def test_search_knowledge_base_no_results(self) -> None:
        """Test knowledge base search with no results."""
        result = BuiltinTools.search_knowledge_base("nonexistent query")
        assert result["ok"] is False or result["count"] == 0
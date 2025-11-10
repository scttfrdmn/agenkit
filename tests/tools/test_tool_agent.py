"""
Comprehensive tests for tool registry and tool agent.

Tests verify:
- ToolRegistry (register, get, list, descriptions, duplicate names, validation)
- ToolAgent (execute tools, handle tool calls, error handling, pass-through behavior, format results)
"""

import pytest
from agenkit.interfaces import Agent, Message, Tool, ToolResult
from agenkit.tools import ToolRegistry, ToolAgent


# ============================================
# Test Helper Tools
# ============================================


class CalculatorTool(Tool):
    """Tool for basic arithmetic operations."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Performs basic arithmetic operations"

    async def execute(self, operation: str, a: float, b: float) -> ToolResult:
        try:
            if operation == "add":
                result = a + b
            elif operation == "subtract":
                result = a - b
            elif operation == "multiply":
                result = a * b
            elif operation == "divide":
                if b == 0:
                    return ToolResult(success=False, data=None, error="Division by zero")
                result = a / b
            else:
                return ToolResult(success=False, data=None, error=f"Unknown operation: {operation}")

            return ToolResult(success=True, data={"result": result})
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))


class SearchTool(Tool):
    """Tool for searching information."""

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Searches for information"

    async def execute(self, query: str) -> ToolResult:
        if not query:
            return ToolResult(success=False, data=None, error="Query cannot be empty")

        # Simulate search results
        results = [
            {"title": f"Result for {query}", "url": f"http://example.com/{query}"}
        ]
        return ToolResult(success=True, data={"results": results})


class ErrorTool(Tool):
    """Tool that always fails."""

    @property
    def name(self) -> str:
        return "error_tool"

    @property
    def description(self) -> str:
        return "Tool that always fails"

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=False, data=None, error="This tool always fails")


class ValidationTool(Tool):
    """Tool with parameter validation."""

    @property
    def name(self) -> str:
        return "validator"

    @property
    def description(self) -> str:
        return "Tool with validation"

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "value": {"type": "number", "minimum": 0, "maximum": 100}
            },
            "required": ["value"]
        }

    async def validate(self, **kwargs) -> bool:
        if "value" not in kwargs:
            return False
        value = kwargs["value"]
        return 0 <= value <= 100

    async def execute(self, value: float) -> ToolResult:
        if not await self.validate(value=value):
            return ToolResult(success=False, data=None, error="Invalid value")
        return ToolResult(success=True, data={"validated": value})


class CounterTool(Tool):
    """Tool that counts occurrences."""

    @property
    def name(self) -> str:
        return "counter"

    @property
    def description(self) -> str:
        return "Counts occurrences"

    async def execute(self, text: str, substring: str) -> ToolResult:
        count = text.count(substring)
        return ToolResult(success=True, data={"count": count})


class EchoTool(Tool):
    """Tool that echoes back input."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echoes back input"

    async def execute(self, message: str) -> ToolResult:
        return ToolResult(success=True, data={"echo": message})


class SimpleAgent(Agent):
    """Simple agent for testing."""

    @property
    def name(self) -> str:
        return "simple"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Simple response to: {message.content}")


# ============================================
# ToolRegistry Tests
# ============================================


@pytest.mark.asyncio
async def test_tool_registry_register():
    """Test registering a tool."""
    registry = ToolRegistry()
    tool = CalculatorTool()

    registry.register(tool)

    assert registry.get("calculator") is tool


@pytest.mark.asyncio
async def test_tool_registry_register_multiple():
    """Test registering multiple tools."""
    registry = ToolRegistry()
    calc_tool = CalculatorTool()
    search_tool = SearchTool()

    registry.register(calc_tool)
    registry.register(search_tool)

    assert registry.get("calculator") is calc_tool
    assert registry.get("search") is search_tool


@pytest.mark.asyncio
async def test_tool_registry_register_none_raises():
    """Test registering None raises error."""
    registry = ToolRegistry()

    with pytest.raises(ValueError, match="cannot be None"):
        registry.register(None)  # type: ignore


@pytest.mark.asyncio
async def test_tool_registry_register_duplicate_name_raises():
    """Test registering tool with duplicate name raises error."""
    registry = ToolRegistry()
    tool1 = CalculatorTool()
    tool2 = CalculatorTool()

    registry.register(tool1)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool2)


@pytest.mark.asyncio
async def test_tool_registry_get_nonexistent():
    """Test getting nonexistent tool returns None."""
    registry = ToolRegistry()

    result = registry.get("nonexistent")

    assert result is None


@pytest.mark.asyncio
async def test_tool_registry_get_empty():
    """Test getting from empty registry returns None."""
    registry = ToolRegistry()

    result = registry.get("anything")

    assert result is None


@pytest.mark.asyncio
async def test_tool_registry_list_empty():
    """Test listing tools from empty registry."""
    registry = ToolRegistry()

    result = registry.list()

    assert result == []


@pytest.mark.asyncio
async def test_tool_registry_list_multiple():
    """Test listing multiple registered tools."""
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(SearchTool())
    registry.register(EchoTool())

    result = registry.list()

    assert len(result) == 3
    assert "calculator" in result
    assert "search" in result
    assert "echo" in result


@pytest.mark.asyncio
async def test_tool_registry_get_tool_descriptions_empty():
    """Test getting descriptions from empty registry."""
    registry = ToolRegistry()

    result = registry.get_tool_descriptions()

    assert "No tools available" in result


@pytest.mark.asyncio
async def test_tool_registry_get_tool_descriptions():
    """Test getting descriptions of all tools."""
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(SearchTool())

    result = registry.get_tool_descriptions()

    assert "calculator" in result
    assert "search" in result
    assert "Performs basic arithmetic" in result
    assert "Searches for information" in result


@pytest.mark.asyncio
async def test_tool_registry_get_tool_descriptions_format():
    """Test format of tool descriptions."""
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    result = registry.get_tool_descriptions()

    assert "Available tools:" in result
    assert "- calculator:" in result


@pytest.mark.asyncio
async def test_tool_registry_duplicate_register_error_message():
    """Test error message for duplicate registration."""
    registry = ToolRegistry()
    tool = CalculatorTool()

    registry.register(tool)

    with pytest.raises(ValueError) as exc_info:
        registry.register(tool)

    assert "calculator" in str(exc_info.value)
    assert "already registered" in str(exc_info.value)


# ============================================
# ToolAgent Tests
# ============================================


@pytest.mark.asyncio
async def test_tool_agent_basic_creation():
    """Test creating a tool agent."""
    agent = SimpleAgent()
    registry = ToolRegistry()
    tool_agent = ToolAgent(agent, registry)

    assert tool_agent.name == "simple"


@pytest.mark.asyncio
async def test_tool_agent_capabilities():
    """Test tool agent adds tool_calling capability."""
    class CapableAgent(Agent):
        @property
        def name(self) -> str:
            return "capable"

        @property
        def capabilities(self) -> list[str]:
            return ["search"]

        async def process(self, message: Message) -> Message:
            return message

    registry = ToolRegistry()
    tool_agent = ToolAgent(CapableAgent(), registry)

    caps = tool_agent.capabilities

    assert "search" in caps
    assert "tool_calling" in caps


@pytest.mark.asyncio
async def test_tool_agent_pass_through_no_tool_calls():
    """Test tool agent passes through message when no tool calls present."""
    agent = SimpleAgent()
    registry = ToolRegistry()
    tool_agent = ToolAgent(agent, registry)

    msg = Message(role="user", content="Hello")
    result = await tool_agent.process(msg)

    assert "Simple response" in result.content


@pytest.mark.asyncio
async def test_tool_agent_execute_single_tool():
    """Test tool agent executes single tool call."""
    agent = SimpleAgent()
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    tool_agent = ToolAgent(agent, registry)

    msg = Message(
        role="user",
        content="calculate",
        metadata={
            "tool_calls": [
                {
                    "tool_name": "calculator",
                    "parameters": {"operation": "add", "a": 2, "b": 3}
                }
            ]
        }
    )

    result = await tool_agent.process(msg)

    assert result.role == "agent"
    assert "Success: {'result': 5}" in result.content
    assert "tool_results" in result.metadata


@pytest.mark.asyncio
async def test_tool_agent_execute_multiple_tools():
    """Test tool agent executes multiple tool calls."""
    agent = SimpleAgent()
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(EchoTool())

    tool_agent = ToolAgent(agent, registry)

    msg = Message(
        role="user",
        content="execute",
        metadata={
            "tool_calls": [
                {
                    "tool_name": "calculator",
                    "parameters": {"operation": "multiply", "a": 4, "b": 5}
                },
                {
                    "tool_name": "echo",
                    "parameters": {"message": "hello"}
                }
            ]
        }
    )

    result = await tool_agent.process(msg)

    assert "Success: {'result': 20}" in result.content
    assert "Success: {'echo': 'hello'}" in result.content
    assert len(result.metadata["tool_results"]) == 2


@pytest.mark.asyncio
async def test_tool_agent_tool_failure_handled():
    """Test tool agent handles tool failure gracefully."""
    agent = SimpleAgent()
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    tool_agent = ToolAgent(agent, registry)

    msg = Message(
        role="user",
        content="calculate",
        metadata={
            "tool_calls": [
                {
                    "tool_name": "calculator",
                    "parameters": {"operation": "divide", "a": 1, "b": 0}
                }
            ]
        }
    )

    result = await tool_agent.process(msg)

    assert "Error: Division by zero" in result.content


@pytest.mark.asyncio
async def test_tool_agent_tool_not_found():
    """Test tool agent error when tool not found."""
    agent = SimpleAgent()
    registry = ToolRegistry()

    tool_agent = ToolAgent(agent, registry)

    msg = Message(
        role="user",
        content="calculate",
        metadata={
            "tool_calls": [
                {
                    "tool_name": "nonexistent",
                    "parameters": {}
                }
            ]
        }
    )

    result = await tool_agent.process(msg)

    assert "Error:" in result.content
    assert "not found" in result.content


@pytest.mark.asyncio
async def test_tool_agent_mixed_success_and_failure():
    """Test tool agent with mixed success and failure results."""
    agent = SimpleAgent()
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(ErrorTool())

    tool_agent = ToolAgent(agent, registry)

    msg = Message(
        role="user",
        content="execute",
        metadata={
            "tool_calls": [
                {
                    "tool_name": "calculator",
                    "parameters": {"operation": "add", "a": 1, "b": 1}
                },
                {
                    "tool_name": "error_tool",
                    "parameters": {}
                }
            ]
        }
    )

    result = await tool_agent.process(msg)

    assert "Success: {'result': 2}" in result.content
    assert "Error: This tool always fails" in result.content


@pytest.mark.asyncio
async def test_tool_agent_tool_results_metadata():
    """Test tool agent includes tool results in metadata."""
    agent = SimpleAgent()
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    tool_agent = ToolAgent(agent, registry)

    msg = Message(
        role="user",
        content="calculate",
        metadata={
            "tool_calls": [
                {
                    "tool_name": "calculator",
                    "parameters": {"operation": "add", "a": 5, "b": 3}
                }
            ]
        }
    )

    result = await tool_agent.process(msg)

    assert "tool_results" in result.metadata
    tool_results = result.metadata["tool_results"]
    assert len(tool_results) == 1
    assert tool_results[0]["success"] is True
    assert tool_results[0]["data"]["result"] == 8


@pytest.mark.asyncio
async def test_tool_agent_invalid_tool_calls_not_list():
    """Test tool agent error when tool_calls is not a list."""
    agent = SimpleAgent()
    registry = ToolRegistry()

    tool_agent = ToolAgent(agent, registry)

    msg = Message(
        role="user",
        content="execute",
        metadata={
            "tool_calls": "not_a_list"
        }
    )

    # ToolAgent raises ValueError when tool_calls is not a list
    with pytest.raises(ValueError, match="tool_calls must be a list"):
        await tool_agent.process(msg)


@pytest.mark.asyncio
async def test_tool_agent_invalid_tool_calls_missing_name():
    """Test tool agent error when tool call missing name."""
    agent = SimpleAgent()
    registry = ToolRegistry()

    tool_agent = ToolAgent(agent, registry)

    msg = Message(
        role="user",
        content="execute",
        metadata={
            "tool_calls": [
                {
                    "parameters": {}
                }
            ]
        }
    )

    # ToolAgent raises ValueError when tool_name is missing
    with pytest.raises(ValueError, match="tool_name"):
        await tool_agent.process(msg)


@pytest.mark.asyncio
async def test_tool_agent_invalid_tool_calls_missing_parameters():
    """Test tool agent error when tool call missing parameters."""
    agent = SimpleAgent()
    registry = ToolRegistry()

    tool_agent = ToolAgent(agent, registry)

    msg = Message(
        role="user",
        content="execute",
        metadata={
            "tool_calls": [
                {
                    "tool_name": "calculator"
                }
            ]
        }
    )

    # ToolAgent raises ValueError when parameters are missing
    with pytest.raises(ValueError, match="parameters"):
        await tool_agent.process(msg)


@pytest.mark.asyncio
async def test_tool_agent_format_results():
    """Test tool agent formats results correctly."""
    agent = SimpleAgent()
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(SearchTool())

    tool_agent = ToolAgent(agent, registry)

    msg = Message(
        role="user",
        content="execute",
        metadata={
            "tool_calls": [
                {
                    "tool_name": "calculator",
                    "parameters": {"operation": "add", "a": 10, "b": 20}
                },
                {
                    "tool_name": "search",
                    "parameters": {"query": "python"}
                }
            ]
        }
    )

    result = await tool_agent.process(msg)

    assert "Tool execution results:" in result.content
    assert "1. Success:" in result.content
    assert "2. Success:" in result.content


@pytest.mark.asyncio
async def test_tool_agent_get_registry():
    """Test getting registry from tool agent."""
    agent = SimpleAgent()
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    tool_agent = ToolAgent(agent, registry)

    retrieved_registry = tool_agent.get_registry()

    assert retrieved_registry is registry
    assert retrieved_registry.get("calculator") is not None


@pytest.mark.asyncio
async def test_tool_agent_complex_parameters():
    """Test tool agent with complex parameters."""
    agent = SimpleAgent()
    registry = ToolRegistry()
    registry.register(CounterTool())

    tool_agent = ToolAgent(agent, registry)

    msg = Message(
        role="user",
        content="count",
        metadata={
            "tool_calls": [
                {
                    "tool_name": "counter",
                    "parameters": {
                        "text": "hello world hello",
                        "substring": "hello"
                    }
                }
            ]
        }
    )

    result = await tool_agent.process(msg)

    assert "Success: {'count': 2}" in result.content


@pytest.mark.asyncio
async def test_tool_agent_empty_tool_calls_list():
    """Test tool agent with empty tool calls list."""
    agent = SimpleAgent()
    registry = ToolRegistry()

    tool_agent = ToolAgent(agent, registry)

    msg = Message(
        role="user",
        content="execute",
        metadata={
            "tool_calls": []
        }
    )

    result = await tool_agent.process(msg)

    assert result.content == "Tool execution results:"


@pytest.mark.asyncio
async def test_tool_agent_validation_tool():
    """Test tool agent with tool that has validation."""
    agent = SimpleAgent()
    registry = ToolRegistry()
    registry.register(ValidationTool())

    tool_agent = ToolAgent(agent, registry)

    msg = Message(
        role="user",
        content="validate",
        metadata={
            "tool_calls": [
                {
                    "tool_name": "validator",
                    "parameters": {"value": 50}
                }
            ]
        }
    )

    result = await tool_agent.process(msg)

    assert "Success: {'validated': 50}" in result.content


@pytest.mark.asyncio
async def test_tool_agent_validation_tool_invalid():
    """Test tool agent with invalid validation."""
    agent = SimpleAgent()
    registry = ToolRegistry()
    registry.register(ValidationTool())

    tool_agent = ToolAgent(agent, registry)

    msg = Message(
        role="user",
        content="validate",
        metadata={
            "tool_calls": [
                {
                    "tool_name": "validator",
                    "parameters": {"value": 150}
                }
            ]
        }
    )

    result = await tool_agent.process(msg)

    assert "Error: Invalid value" in result.content


@pytest.mark.asyncio
async def test_tool_agent_names_match():
    """Test tool agent name matches underlying agent."""
    class CustomAgent(Agent):
        @property
        def name(self) -> str:
            return "custom_name"

        async def process(self, message: Message) -> Message:
            return message

    registry = ToolRegistry()
    tool_agent = ToolAgent(CustomAgent(), registry)

    assert tool_agent.name == "custom_name"


@pytest.mark.asyncio
async def test_tool_agent_sequential_execution():
    """Test tool agent executes tools sequentially."""
    agent = SimpleAgent()
    registry = ToolRegistry()
    registry.register(CounterTool())

    tool_agent = ToolAgent(agent, registry)

    msg = Message(
        role="user",
        content="count",
        metadata={
            "tool_calls": [
                {
                    "tool_name": "counter",
                    "parameters": {"text": "aaa", "substring": "a"}
                },
                {
                    "tool_name": "counter",
                    "parameters": {"text": "bbb", "substring": "b"}
                },
                {
                    "tool_name": "counter",
                    "parameters": {"text": "ccc", "substring": "c"}
                }
            ]
        }
    )

    result = await tool_agent.process(msg)

    assert "1. Success: {'count': 3}" in result.content
    assert "2. Success: {'count': 3}" in result.content
    assert "3. Success: {'count': 3}" in result.content
    assert len(result.metadata["tool_results"]) == 3

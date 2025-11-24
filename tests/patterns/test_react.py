"""
Tests for ReAct (Reasoning + Acting) Agent pattern.
"""

import pytest

from agenkit import Message
from agenkit.patterns import ReActAgent, ReActStep, ToolRegistry, ToolResult

# ============================================================================
# Mock Tools
# ============================================================================


class MockCalculator:
    """Mock calculator tool for testing."""

    name = "calculator"
    description = "Performs calculations"

    async def execute(self, input: str) -> str:
        """Execute calculation."""
        # Simple mock: just return the input
        if "error" in input:
            raise ValueError("Calculation error")
        return f"Result: {input}"


class MockSearch:
    """Mock search tool for testing."""

    name = "search"
    description = "Searches for information"

    async def execute(self, query: str) -> str:
        """Execute search."""
        return f"Search results for: {query}"


class FailingTool:
    """Tool that always fails for testing error handling."""

    name = "failing"
    description = "Always fails"

    async def execute(self, **kwargs) -> str:
        """Always raises an error."""
        raise RuntimeError("Tool failure")


# ============================================================================
# Mock LLM
# ============================================================================


class MockReActLLM:
    """Mock LLM for testing ReAct pattern."""

    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0
        self.last_messages = None

    async def chat(self, messages):
        """Return pre-programmed responses."""
        self.call_count += 1
        self.last_messages = messages.copy()

        if self.call_count <= len(self.responses):
            return Message(role="assistant", content=self.responses[self.call_count - 1])

        # Default: final answer
        return Message(
            role="assistant",
            content="Thought: Done\nAction: Final Answer\nAction Input: Complete",
        )


# ============================================================================
# ToolResult Tests
# ============================================================================


def test_tool_result_success():
    """Test ToolResult for successful execution."""
    result = ToolResult(tool_name="test", result="success", execution_time=0.1)
    assert result.success
    assert result.error is None
    assert result.result == "success"


def test_tool_result_error():
    """Test ToolResult for failed execution."""
    result = ToolResult(tool_name="test", error="Failed", execution_time=0.1)
    assert not result.success
    assert result.error == "Failed"
    assert result.result is None


# ============================================================================
# ToolRegistry Tests
# ============================================================================


def test_tool_registry_register():
    """Test registering tools."""
    registry = ToolRegistry()
    tool = MockCalculator()

    registry.register(tool)
    assert "calculator" in registry.list_tools()
    assert registry.get_tool("calculator") == tool


def test_tool_registry_duplicate_registration():
    """Test that registering duplicate tool names raises error."""
    registry = ToolRegistry()
    tool1 = MockCalculator()
    tool2 = MockCalculator()

    registry.register(tool1)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool2)


def test_tool_registry_unregister():
    """Test unregistering tools."""
    registry = ToolRegistry()
    tool = MockCalculator()

    registry.register(tool)
    assert "calculator" in registry.list_tools()

    registry.unregister("calculator")
    assert "calculator" not in registry.list_tools()


def test_tool_registry_get_tool():
    """Test getting tools by name."""
    registry = ToolRegistry()
    tool = MockCalculator()

    registry.register(tool)

    assert registry.get_tool("calculator") == tool
    assert registry.get_tool("nonexistent") is None


def test_tool_registry_list_tools():
    """Test listing all tools."""
    registry = ToolRegistry()
    registry.register(MockCalculator())
    registry.register(MockSearch())

    tools = registry.list_tools()
    assert "calculator" in tools
    assert "search" in tools
    assert len(tools) == 2


def test_tool_registry_get_tools_description():
    """Test getting formatted tool descriptions."""
    registry = ToolRegistry()
    registry.register(MockCalculator())

    desc = registry.get_tools_description()
    assert "calculator" in desc
    assert "Performs calculations" in desc


def test_tool_registry_empty_description():
    """Test description when no tools registered."""
    registry = ToolRegistry()
    desc = registry.get_tools_description()
    assert "No tools available" in desc


@pytest.mark.asyncio
async def test_tool_registry_execute_success():
    """Test successful tool execution."""
    registry = ToolRegistry()
    registry.register(MockCalculator())

    result = await registry.execute("calculator", input="2+2")

    assert result.success
    assert result.tool_name == "calculator"
    assert "2+2" in result.result
    assert result.execution_time >= 0


@pytest.mark.asyncio
async def test_tool_registry_execute_not_found():
    """Test executing non-existent tool."""
    registry = ToolRegistry()

    result = await registry.execute("nonexistent", input="test")

    assert not result.success
    assert "not found" in result.error


@pytest.mark.asyncio
async def test_tool_registry_execute_tool_error():
    """Test tool execution that raises error."""
    registry = ToolRegistry()
    registry.register(MockCalculator())

    result = await registry.execute("calculator", input="error")

    assert not result.success
    assert "Calculation error" in result.error
    assert result.execution_time >= 0


# ============================================================================
# ReActAgent Tests
# ============================================================================


@pytest.mark.asyncio
async def test_react_agent_basic():
    """Test basic ReActAgent functionality."""
    registry = ToolRegistry()
    registry.register(MockCalculator())

    # Program LLM to: use calculator, then give final answer
    llm = MockReActLLM(
        responses=[
            "Thought: Need calculator\nAction: calculator\nAction Input: 2+2",
            "Thought: Got result\nAction: Final Answer\nAction Input: The answer is 4",
        ]
    )

    agent = ReActAgent(llm_client=llm, tool_registry=registry, max_iterations=5)

    response = await agent.process(Message(role="user", content="Calculate 2+2"))

    assert "4" in response.content
    assert len(agent.get_steps()) == 1  # One tool execution
    assert agent.get_steps()[0].action == "calculator"


@pytest.mark.asyncio
async def test_react_agent_immediate_answer():
    """Test agent giving immediate answer without tools."""
    registry = ToolRegistry()

    llm = MockReActLLM(
        responses=["Thought: Can answer directly\nAction: Final Answer\nAction Input: Hello!"]
    )

    agent = ReActAgent(llm_client=llm, tool_registry=registry, max_iterations=5)

    response = await agent.process(Message(role="user", content="Say hello"))

    assert "Hello" in response.content
    assert len(agent.get_steps()) == 0  # No tools used


@pytest.mark.asyncio
async def test_react_agent_multiple_steps():
    """Test agent using multiple tools."""
    registry = ToolRegistry()
    registry.register(MockCalculator())
    registry.register(MockSearch())

    llm = MockReActLLM(
        responses=[
            "Thought: Need calculator\nAction: calculator\nAction Input: 2+2",
            "Thought: Need search\nAction: search\nAction Input: test query",
            "Thought: Done\nAction: Final Answer\nAction Input: Complete",
        ]
    )

    agent = ReActAgent(llm_client=llm, tool_registry=registry, max_iterations=5)

    await agent.process(Message(role="user", content="Test"))

    assert len(agent.get_steps()) == 2  # Two tool executions
    assert agent.get_steps()[0].action == "calculator"
    assert agent.get_steps()[1].action == "search"


@pytest.mark.asyncio
async def test_react_agent_max_iterations():
    """Test that agent stops at max iterations."""
    registry = ToolRegistry()
    registry.register(MockCalculator())

    # LLM never gives final answer
    llm = MockReActLLM(
        responses=[
            "Thought: Use calculator\nAction: calculator\nAction Input: test",
        ]
        * 10  # More than max_iterations
    )

    agent = ReActAgent(llm_client=llm, tool_registry=registry, max_iterations=3)

    response = await agent.process(Message(role="user", content="Test"))

    # Should stop at max iterations
    assert "couldn't complete" in response.content.lower()
    assert len(agent.get_steps()) <= 3


@pytest.mark.asyncio
async def test_react_agent_tool_error():
    """Test agent handling tool errors."""
    registry = ToolRegistry()
    registry.register(FailingTool())

    llm = MockReActLLM(
        responses=[
            "Thought: Use tool\nAction: failing\nAction Input: test",
            "Thought: Tool failed\nAction: Final Answer\nAction Input: Error occurred",
        ]
    )

    agent = ReActAgent(llm_client=llm, tool_registry=registry, max_iterations=5)

    await agent.process(Message(role="user", content="Test"))

    # Check that error was recorded
    assert len(agent.get_steps()) == 1
    assert "Error" in agent.get_steps()[0].observation


@pytest.mark.asyncio
async def test_react_agent_verbose_mode():
    """Test verbose mode includes reasoning steps."""
    registry = ToolRegistry()
    registry.register(MockCalculator())

    llm = MockReActLLM(
        responses=[
            "Thought: Calculate\nAction: calculator\nAction Input: 2+2",
            "Thought: Done\nAction: Final Answer\nAction Input: Result is 4",
        ]
    )

    agent = ReActAgent(llm_client=llm, tool_registry=registry, max_iterations=5, verbose=True)

    response = await agent.process(Message(role="user", content="Calculate 2+2"))

    # Verbose mode should include steps in response
    assert "Step" in response.content
    assert "Thought" in response.content
    assert "Action" in response.content


@pytest.mark.asyncio
async def test_react_agent_non_verbose_mode():
    """Test non-verbose mode only shows final answer."""
    registry = ToolRegistry()
    registry.register(MockCalculator())

    llm = MockReActLLM(
        responses=[
            "Thought: Calculate\nAction: calculator\nAction Input: 2+2",
            "Thought: Done\nAction: Final Answer\nAction Input: Result is 4",
        ]
    )

    agent = ReActAgent(llm_client=llm, tool_registry=registry, max_iterations=5, verbose=False)

    response = await agent.process(Message(role="user", content="Calculate 2+2"))

    # Non-verbose should not include steps
    assert "Step" not in response.content
    assert "Result is 4" in response.content


@pytest.mark.asyncio
async def test_react_agent_get_steps():
    """Test retrieving reasoning steps."""
    registry = ToolRegistry()
    registry.register(MockCalculator())

    llm = MockReActLLM(
        responses=[
            "Thought: Calculate\nAction: calculator\nAction Input: 2+2",
            "Thought: Done\nAction: Final Answer\nAction Input: 4",
        ]
    )

    agent = ReActAgent(llm_client=llm, tool_registry=registry, max_iterations=5)

    await agent.process(Message(role="user", content="Calculate 2+2"))

    steps = agent.get_steps()
    assert len(steps) == 1
    assert isinstance(steps[0], ReActStep)
    assert steps[0].thought == "Calculate"
    assert steps[0].action == "calculator"


@pytest.mark.asyncio
async def test_react_agent_clear_steps():
    """Test clearing reasoning steps."""
    registry = ToolRegistry()
    registry.register(MockCalculator())

    llm = MockReActLLM(
        responses=[
            "Thought: Calculate\nAction: calculator\nAction Input: 2+2",
            "Thought: Done\nAction: Final Answer\nAction Input: 4",
        ]
    )

    agent = ReActAgent(llm_client=llm, tool_registry=registry, max_iterations=5)

    await agent.process(Message(role="user", content="Calculate 2+2"))
    assert len(agent.get_steps()) > 0

    agent.clear_steps()
    assert len(agent.get_steps()) == 0


@pytest.mark.asyncio
async def test_react_agent_custom_system_prompt():
    """Test using custom system prompt."""
    registry = ToolRegistry()

    custom_prompt = "You are a test assistant."

    llm = MockReActLLM(responses=["Thought: Answer\nAction: Final Answer\nAction Input: OK"])

    agent = ReActAgent(
        llm_client=llm,
        tool_registry=registry,
        max_iterations=5,
        system_prompt=custom_prompt,
    )

    await agent.process(Message(role="user", content="Test"))

    # Check that custom prompt was used
    assert llm.last_messages[0].role == "system"
    assert llm.last_messages[0].content == custom_prompt


@pytest.mark.asyncio
async def test_react_agent_name_property():
    """Test agent name property."""
    registry = ToolRegistry()
    llm = MockReActLLM()

    agent = ReActAgent(llm_client=llm, tool_registry=registry)

    assert agent.name == "ReActAgent"


@pytest.mark.asyncio
async def test_react_agent_action_input_dict_parsing():
    """Test parsing action input as dict."""
    registry = ToolRegistry()
    registry.register(MockCalculator())

    llm = MockReActLLM(
        responses=[
            'Thought: Test\nAction: calculator\nAction Input: {"input": "test"}',
            "Thought: Done\nAction: Final Answer\nAction Input: OK",
        ]
    )

    agent = ReActAgent(llm_client=llm, tool_registry=registry, max_iterations=5)

    await agent.process(Message(role="user", content="Test"))

    steps = agent.get_steps()
    assert len(steps) == 1
    assert isinstance(steps[0].action_input, dict)


@pytest.mark.asyncio
async def test_react_agent_steps_reset_on_new_task():
    """Test that steps are reset for each new task."""
    registry = ToolRegistry()
    registry.register(MockCalculator())

    llm = MockReActLLM(
        responses=[
            "Thought: First\nAction: calculator\nAction Input: 1",
            "Thought: Done\nAction: Final Answer\nAction Input: OK",
        ]
    )

    agent = ReActAgent(llm_client=llm, tool_registry=registry, max_iterations=5)

    # First task
    await agent.process(Message(role="user", content="Task 1"))
    assert len(agent.get_steps()) == 1

    # Reset LLM for second task
    llm.call_count = 0
    llm.responses = [
        "Thought: Second\nAction: calculator\nAction Input: 2",
        "Thought: Done\nAction: Final Answer\nAction Input: OK",
    ]

    # Second task should reset steps
    await agent.process(Message(role="user", content="Task 2"))
    steps = agent.get_steps()
    assert len(steps) == 1
    assert "2" in steps[0].action_input["input"]


def test_react_step_dataclass():
    """Test ReActStep dataclass."""
    step = ReActStep(
        thought="Test thought",
        action="test_action",
        action_input={"key": "value"},
        observation="Test observation",
        step_number=1,
    )

    assert step.thought == "Test thought"
    assert step.action == "test_action"
    assert step.action_input == {"key": "value"}
    assert step.observation == "Test observation"
    assert step.step_number == 1
    assert step.timestamp is not None

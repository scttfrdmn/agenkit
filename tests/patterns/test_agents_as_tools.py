"""
Tests for Agents-as-Tools Pattern.

Coverage:
- AgentTool basic operation
- agent_as_tool convenience function
- Input/output formatting
- Integration with tool registries
- Error handling
- Parameter validation
"""

import pytest

from agenkit.interfaces import Message
from agenkit.patterns import AgentTool, agent_as_tool


# Mock agents for testing
class MockSpecialistAgent:
    """Mock specialist agent."""

    def __init__(self, specialty: str = "general", response: str = "Mock response"):
        self.specialty = specialty
        self.response = response
        self.call_count = 0
        self.last_message = None
        self.name = f"{specialty.title()}Specialist"
        self.capabilities = [specialty]

    async def process(self, message: Message) -> Message:
        """Process message and return response."""
        self.call_count += 1
        self.last_message = message

        return Message(
            role="assistant",
            content=self.response,
            metadata={"specialty": self.specialty, "call_count": self.call_count},
        )


# Tests


@pytest.mark.asyncio
async def test_agent_tool_basic():
    """Test basic AgentTool operation."""
    agent = MockSpecialistAgent(specialty="code", response="def hello(): pass")

    tool = AgentTool(
        agent=agent, name="code_specialist", description="Expert in programming", input_key="query"
    )

    result = await tool.execute(query="Write a hello function")

    assert result == "def hello(): pass"
    assert agent.call_count == 1
    assert agent.last_message.content == "Write a hello function"


@pytest.mark.asyncio
async def test_agent_tool_with_agent_as_tool():
    """Test agent_as_tool convenience function."""
    agent = MockSpecialistAgent(specialty="math", response="42")

    tool = agent_as_tool(agent=agent, name="math_expert", description="Expert in mathematics")

    result = await tool.execute(query="What is 6 * 7?")

    assert result == "42"
    assert tool.name == "math_expert"
    assert tool.description == "Expert in mathematics"


@pytest.mark.asyncio
async def test_agent_tool_output_format_str():
    """Test string output format (default)."""
    agent = MockSpecialistAgent(response="String output")

    tool = AgentTool(
        agent=agent,
        name="test_tool",
        description="Test tool",
        output_format="str",
    )

    result = await tool.execute(query="Test")

    assert isinstance(result, str)
    assert result == "String output"


@pytest.mark.asyncio
async def test_agent_tool_output_format_dict():
    """Test dictionary output format."""
    agent = MockSpecialistAgent(response="Dict output")

    tool = AgentTool(
        agent=agent,
        name="test_tool",
        description="Test tool",
        output_format="dict",
        include_metadata=False,
    )

    result = await tool.execute(query="Test")

    assert isinstance(result, dict)
    assert result["content"] == "Dict output"
    assert "metadata" not in result


@pytest.mark.asyncio
async def test_agent_tool_output_format_dict_with_metadata():
    """Test dictionary output format with metadata."""
    agent = MockSpecialistAgent(response="Dict with metadata")

    tool = AgentTool(
        agent=agent,
        name="test_tool",
        description="Test tool",
        output_format="dict",
        include_metadata=True,
    )

    result = await tool.execute(query="Test")

    assert isinstance(result, dict)
    assert result["content"] == "Dict with metadata"
    assert "metadata" in result
    assert result["metadata"]["specialty"] == "general"


@pytest.mark.asyncio
async def test_agent_tool_output_format_message():
    """Test message output format."""
    agent = MockSpecialistAgent(response="Message output")

    tool = AgentTool(
        agent=agent,
        name="test_tool",
        description="Test tool",
        output_format="message",
    )

    result = await tool.execute(query="Test")

    assert isinstance(result, Message)
    assert result.content == "Message output"
    assert result.role == "assistant"


@pytest.mark.asyncio
async def test_agent_tool_custom_input_key():
    """Test custom input parameter key."""
    agent = MockSpecialistAgent(response="Custom key response")

    tool = AgentTool(
        agent=agent,
        name="test_tool",
        description="Test tool",
        input_key="task",  # Custom key instead of "query"
    )

    result = await tool.execute(task="Do something")

    assert result == "Custom key response"
    assert agent.last_message.content == "Do something"


@pytest.mark.asyncio
async def test_agent_tool_missing_input_parameter():
    """Test error when required input parameter is missing."""
    agent = MockSpecialistAgent()

    tool = AgentTool(agent=agent, name="test_tool", description="Test tool", input_key="query")

    with pytest.raises(ValueError, match="Missing required parameter 'query'"):
        await tool.execute(wrong_param="Test")


@pytest.mark.asyncio
async def test_agent_tool_multiple_calls():
    """Test tool can be called multiple times."""
    agent = MockSpecialistAgent(response="Response")

    tool = AgentTool(agent=agent, name="test_tool", description="Test tool")

    # Call 1
    result1 = await tool.execute(query="First call")
    assert result1 == "Response"
    assert agent.call_count == 1

    # Call 2
    result2 = await tool.execute(query="Second call")
    assert result2 == "Response"
    assert agent.call_count == 2

    # Call 3
    result3 = await tool.execute(query="Third call")
    assert result3 == "Response"
    assert agent.call_count == 3


@pytest.mark.asyncio
async def test_agent_tool_with_tool_registry():
    """Test integration with ToolRegistry."""
    from agenkit.patterns import ToolRegistry

    agent = MockSpecialistAgent(specialty="code", response="Code output")

    tool = agent_as_tool(agent=agent, name="code_expert", description="Programming expert")

    # Register tool
    registry = ToolRegistry()
    registry.register(tool)

    # Execute via registry
    result = await registry.execute("code_expert", query="Write code")

    assert result.success
    assert result.result == "Code output"


@pytest.mark.asyncio
async def test_agent_tool_integration_react_pattern():
    """Test integration with ReAct pattern."""
    from agenkit.patterns import ToolRegistry

    # Create specialist agents
    code_agent = MockSpecialistAgent(specialty="code", response="print('Hello, World!')")
    math_agent = MockSpecialistAgent(specialty="math", response="The answer is 42")

    # Wrap as tools
    code_tool = agent_as_tool(
        agent=code_agent, name="code_specialist", description="Expert in programming"
    )
    math_tool = agent_as_tool(
        agent=math_agent, name="math_specialist", description="Expert in mathematics"
    )

    # Create registry
    registry = ToolRegistry()
    registry.register(code_tool)
    registry.register(math_tool)

    # Verify tools are registered
    assert "code_specialist" in registry.list_tools()
    assert "math_specialist" in registry.list_tools()

    # Verify tool descriptions
    tools_desc = registry.get_tools_description()
    assert "code_specialist" in tools_desc
    assert "math_specialist" in tools_desc


def test_agent_tool_validation_empty_name():
    """Test validation of empty tool name."""
    agent = MockSpecialistAgent()

    with pytest.raises(ValueError, match="Tool name cannot be empty"):
        AgentTool(agent=agent, name="", description="Test tool")


def test_agent_tool_validation_empty_description():
    """Test validation of empty tool description."""
    agent = MockSpecialistAgent()

    with pytest.raises(ValueError, match="Tool description cannot be empty"):
        AgentTool(agent=agent, name="test_tool", description="")


def test_agent_tool_repr():
    """Test __repr__ method."""
    agent = MockSpecialistAgent(specialty="code")

    tool = AgentTool(agent=agent, name="code_tool", description="Code specialist")

    repr_str = repr(tool)
    assert "AgentTool" in repr_str
    assert "code_tool" in repr_str
    assert "CodeSpecialist" in repr_str  # Agent name


@pytest.mark.asyncio
async def test_agent_tool_preserves_agent_capabilities():
    """Test that tool preserves underlying agent capabilities."""
    agent = MockSpecialistAgent(specialty="code")

    AgentTool(agent=agent, name="code_tool", description="Code tool")

    # Agent capabilities should still be accessible
    assert agent.capabilities == ["code"]
    assert agent.name == "CodeSpecialist"


@pytest.mark.asyncio
async def test_agent_as_tool_all_parameters():
    """Test agent_as_tool with all parameters specified."""
    agent = MockSpecialistAgent(response="Full params response")

    tool = agent_as_tool(
        agent=agent,
        name="full_tool",
        description="Tool with all params",
        input_key="task",
        output_format="dict",
        include_metadata=True,
    )

    result = await tool.execute(task="Do work")

    assert isinstance(result, dict)
    assert result["content"] == "Full params response"
    assert "metadata" in result
    assert tool.input_key == "task"


@pytest.mark.asyncio
async def test_hierarchical_agent_delegation():
    """Test hierarchical agent delegation pattern."""
    # Create specialist agents
    python_agent = MockSpecialistAgent(specialty="python", response="Python code here")
    rust_agent = MockSpecialistAgent(specialty="rust", response="Rust code here")
    general_agent = MockSpecialistAgent(specialty="general", response="General response")

    # Wrap as tools
    python_tool = agent_as_tool(
        agent=python_agent, name="python_expert", description="Python specialist"
    )
    rust_tool = agent_as_tool(agent=rust_agent, name="rust_expert", description="Rust specialist")

    # Simulate supervisor delegating to specialists
    # (In real usage, supervisor would be a ReActAgent that decides which tool to use)

    # Delegate Python task
    python_result = await python_tool.execute(query="Write Python code")
    assert python_result == "Python code here"
    assert python_agent.call_count == 1

    # Delegate Rust task
    rust_result = await rust_tool.execute(query="Write Rust code")
    assert rust_result == "Rust code here"
    assert rust_agent.call_count == 1

    # General agent not called
    assert general_agent.call_count == 0


@pytest.mark.asyncio
async def test_agent_tool_error_propagation():
    """Test that agent errors propagate through tool."""

    class ErrorAgent:
        name = "ErrorAgent"
        capabilities = []

        async def process(self, message: Message) -> Message:
            raise ValueError("Agent error")

    agent = ErrorAgent()
    tool = AgentTool(agent=agent, name="error_tool", description="Tool that errors")

    with pytest.raises(ValueError, match="Agent error"):
        await tool.execute(query="Trigger error")


@pytest.mark.asyncio
async def test_agent_tool_different_agents():
    """Test multiple tools wrapping different agents."""
    agent1 = MockSpecialistAgent(specialty="code", response="Agent 1 response")
    agent2 = MockSpecialistAgent(specialty="data", response="Agent 2 response")
    agent3 = MockSpecialistAgent(specialty="research", response="Agent 3 response")

    tool1 = agent_as_tool(agent=agent1, name="tool1", description="Tool 1")
    tool2 = agent_as_tool(agent=agent2, name="tool2", description="Tool 2")
    tool3 = agent_as_tool(agent=agent3, name="tool3", description="Tool 3")

    # Execute each tool
    result1 = await tool1.execute(query="Task 1")
    result2 = await tool2.execute(query="Task 2")
    result3 = await tool3.execute(query="Task 3")

    # Verify correct responses
    assert result1 == "Agent 1 response"
    assert result2 == "Agent 2 response"
    assert result3 == "Agent 3 response"

    # Verify each agent called once
    assert agent1.call_count == 1
    assert agent2.call_count == 1
    assert agent3.call_count == 1


@pytest.mark.asyncio
async def test_agent_tool_unknown_output_format():
    """Test unknown output format defaults to string."""
    agent = MockSpecialistAgent(response="Unknown format response")

    tool = AgentTool(
        agent=agent,
        name="test_tool",
        description="Test tool",
        output_format="unknown_format",
    )

    result = await tool.execute(query="Test")

    # Should default to string
    assert isinstance(result, str)
    assert result == "Unknown format response"

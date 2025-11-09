"""
Tests for core interfaces.

Tests verify:
- Message and ToolResult creation and validation
- Agent and Tool interface contracts
- Edge cases and error handling
"""

import pytest
from datetime import datetime, timezone

from agenkit.interfaces import Agent, Message, Tool, ToolResult


# ============================================
# Message Tests
# ============================================


def test_message_creation():
    """Test basic message creation."""
    msg = Message(role="user", content="Hello")

    assert msg.role == "user"
    assert msg.content == "Hello"
    assert isinstance(msg.metadata, dict)
    assert len(msg.metadata) == 0
    assert isinstance(msg.timestamp, datetime)


def test_message_with_metadata():
    """Test message with custom metadata."""
    msg = Message(
        role="agent",
        content="Response",
        metadata={"source": "test", "confidence": 0.95}
    )

    assert msg.metadata["source"] == "test"
    assert msg.metadata["confidence"] == 0.95


def test_message_flexible_content():
    """Test message with different content types."""
    # String content
    msg1 = Message(role="user", content="string")
    assert msg1.content == "string"

    # Dict content
    msg2 = Message(role="user", content={"key": "value"})
    assert msg2.content == {"key": "value"}

    # List content
    msg3 = Message(role="user", content=[1, 2, 3])
    assert msg3.content == [1, 2, 3]


def test_message_immutable():
    """Test that messages are immutable."""
    msg = Message(role="user", content="test")

    with pytest.raises(Exception):  # dataclass frozen
        msg.role = "agent"  # type: ignore


def test_message_empty_role_raises():
    """Test that empty role raises ValueError."""
    with pytest.raises(ValueError, match="role cannot be empty"):
        Message(role="", content="test")


# ============================================
# ToolResult Tests
# ============================================


def test_tool_result_success():
    """Test successful tool result."""
    result = ToolResult(success=True, data={"answer": 42})

    assert result.success is True
    assert result.data == {"answer": 42}
    assert result.error is None
    assert isinstance(result.metadata, dict)


def test_tool_result_failure():
    """Test failed tool result."""
    result = ToolResult(success=False, data=None, error="Connection timeout")

    assert result.success is False
    assert result.data is None
    assert result.error == "Connection timeout"


def test_tool_result_failure_without_error_raises():
    """Test that failed result without error message raises."""
    with pytest.raises(ValueError, match="must have error message"):
        ToolResult(success=False, data=None)


def test_tool_result_immutable():
    """Test that tool results are immutable."""
    result = ToolResult(success=True, data="test")

    with pytest.raises(Exception):  # dataclass frozen
        result.success = False  # type: ignore


# ============================================
# Tool Interface Tests
# ============================================


class MockTool(Tool):
    """Mock tool for testing."""

    @property
    def name(self) -> str:
        return "mock_tool"

    @property
    def description(self) -> str:
        return "A mock tool for testing"

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data=kwargs)


@pytest.mark.asyncio
async def test_tool_basic():
    """Test basic tool functionality."""
    tool = MockTool()

    assert tool.name == "mock_tool"
    assert tool.description == "A mock tool for testing"

    result = await tool.execute(arg1="value1", arg2=42)
    assert result.success is True
    assert result.data == {"arg1": "value1", "arg2": 42}


@pytest.mark.asyncio
async def test_tool_default_methods():
    """Test tool default method implementations."""
    tool = MockTool()

    # Default parameters_schema is None
    assert tool.parameters_schema is None

    # Default validate returns True
    assert await tool.validate(any="args") is True


class ToolWithSchema(Tool):
    """Tool with parameter schema."""

    @property
    def name(self) -> str:
        return "schema_tool"

    @property
    def description(self) -> str:
        return "Tool with schema"

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data=kwargs)


@pytest.mark.asyncio
async def test_tool_with_schema():
    """Test tool with custom schema."""
    tool = ToolWithSchema()

    schema = tool.parameters_schema
    assert schema is not None
    assert schema["type"] == "object"
    assert "query" in schema["properties"]


# ============================================
# Agent Interface Tests
# ============================================


class MockAgent(Agent):
    """Mock agent for testing."""

    @property
    def name(self) -> str:
        return "mock_agent"

    async def process(self, message: Message) -> Message:
        return Message(
            role="agent",
            content=f"Processed: {message.content}"
        )


@pytest.mark.asyncio
async def test_agent_basic():
    """Test basic agent functionality."""
    agent = MockAgent()

    assert agent.name == "mock_agent"

    msg = Message(role="user", content="Hello")
    response = await agent.process(msg)

    assert response.role == "agent"
    assert response.content == "Processed: Hello"


@pytest.mark.asyncio
async def test_agent_default_methods():
    """Test agent default method implementations."""
    agent = MockAgent()

    # Default capabilities is empty list
    assert agent.capabilities == []

    # Default unwrap returns self
    assert agent.unwrap() is agent

    # Default stream raises NotImplementedError
    msg = Message(role="user", content="test")
    with pytest.raises(NotImplementedError):
        async for _ in agent.stream(msg):
            pass


class AgentWithCapabilities(Agent):
    """Agent with capabilities."""

    @property
    def name(self) -> str:
        return "capable_agent"

    @property
    def capabilities(self) -> list[str]:
        return ["search", "summarize"]

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content="response")


@pytest.mark.asyncio
async def test_agent_with_capabilities():
    """Test agent with custom capabilities."""
    agent = AgentWithCapabilities()

    caps = agent.capabilities
    assert "search" in caps
    assert "summarize" in caps


class StreamingAgent(Agent):
    """Agent that supports streaming."""

    @property
    def name(self) -> str:
        return "streaming_agent"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content="final")

    async def stream(self, message: Message):
        """Yield multiple messages."""
        for i in range(3):
            yield Message(role="agent", content=f"chunk_{i}")


@pytest.mark.asyncio
async def test_agent_streaming():
    """Test agent with streaming support."""
    agent = StreamingAgent()

    msg = Message(role="user", content="test")
    chunks = []

    async for chunk in agent.stream(msg):
        chunks.append(chunk.content)

    assert len(chunks) == 3
    assert chunks == ["chunk_0", "chunk_1", "chunk_2"]


class AgentWithUnwrap(Agent):
    """Agent with custom unwrap."""

    def __init__(self, native_obj):
        self._native = native_obj

    @property
    def name(self) -> str:
        return "wrapped_agent"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content="response")

    def unwrap(self):
        """Return native object."""
        return self._native


@pytest.mark.asyncio
async def test_agent_unwrap():
    """Test agent with custom unwrap."""
    native = {"type": "native", "value": 42}
    agent = AgentWithUnwrap(native)

    unwrapped = agent.unwrap()
    assert unwrapped is native
    assert unwrapped["value"] == 42

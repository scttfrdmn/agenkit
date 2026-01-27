"""Tests for AG-UI Standard protocol implementation."""

import pytest

from agenkit import Agent, Message, Tool, ToolResult
from agenkit.protocols.agui import (
    AGUIAdapter,
    EventType,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StateManager,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallTracker,
    ToolRegistry,
)


# ============================================================================
# Test Fixtures
# ============================================================================


class SimpleAgent(Agent):
    """Simple test agent that echoes messages."""

    @property
    def name(self) -> str:
        return "SimpleAgent"

    async def process(self, message: Message) -> Message:
        """Echo the input message."""
        return Message(
            role="assistant",
            content=f"Echo: {message.content}",
            metadata={"original": message.content},
        )


class ErrorAgent(Agent):
    """Agent that always raises an error."""

    @property
    def name(self) -> str:
        return "ErrorAgent"

    async def process(self, message: Message) -> Message:
        """Raise an error."""
        raise ValueError("Test error")


class SearchTool(Tool):
    """Simple search tool for testing."""

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Search for information"

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        return ToolResult(
            success=True,
            data={"results": [f"Result for {query}"]},
            metadata={"query": query},
        )


# ============================================================================
# Event Tests
# ============================================================================


def test_event_creation():
    """Test creating AG-UI events."""
    # RunStarted
    event = RunStartedEvent(
        thread_id="thread-1",
        run_id="run-1",
    )
    assert event.type == EventType.RUN_STARTED
    assert event.thread_id == "thread-1"
    assert event.run_id == "run-1"
    assert event.timestamp is not None

    # TextMessageStart
    event = TextMessageStartEvent(
        message_id="msg-1",
        role="assistant",
    )
    assert event.type == EventType.TEXT_MESSAGE_START
    assert event.message_id == "msg-1"
    assert event.role == "assistant"

    # TextMessageContent
    event = TextMessageContentEvent(
        message_id="msg-1",
        delta="Hello",
    )
    assert event.type == EventType.TEXT_MESSAGE_CONTENT
    assert event.message_id == "msg-1"
    assert event.delta == "Hello"


def test_event_serialization():
    """Test event serialization to dict."""
    event = RunStartedEvent(
        thread_id="thread-1",
        run_id="run-1",
        parent_run_id="parent-1",
    )

    data = event.model_dump(exclude_none=True)
    assert data["type"] == "run_started"
    assert data["thread_id"] == "thread-1"
    assert data["run_id"] == "run-1"
    assert data["parent_run_id"] == "parent-1"
    assert "timestamp" in data


# ============================================================================
# Adapter Tests
# ============================================================================


@pytest.mark.asyncio
async def test_adapter_basic_streaming():
    """Test basic streaming with AGUIAdapter."""
    agent = SimpleAgent()
    adapter = AGUIAdapter(agent, chunk_size=5)

    message = Message(role="user", content="Hello")
    events = []

    async for event in adapter.stream_events(
        message=message,
        thread_id="thread-1",
        run_id="run-1",
    ):
        events.append(event)

    # Verify event sequence
    assert len(events) >= 5  # RunStarted, TextStart, Content(s), TextEnd, RunFinished

    # Check event types
    assert isinstance(events[0], RunStartedEvent)
    assert isinstance(events[1], TextMessageStartEvent)
    assert any(isinstance(e, TextMessageContentEvent) for e in events)
    assert isinstance(events[-2], TextMessageEndEvent)
    assert isinstance(events[-1], RunFinishedEvent)

    # Verify RunStarted
    assert events[0].thread_id == "thread-1"
    assert events[0].run_id == "run-1"

    # Verify TextMessageStart
    assert events[1].role == "assistant"

    # Collect all content
    content = "".join(
        e.delta for e in events if isinstance(e, TextMessageContentEvent)
    )
    assert "Echo: Hello" in content


@pytest.mark.asyncio
async def test_adapter_error_handling():
    """Test adapter handles agent errors."""
    agent = ErrorAgent()
    adapter = AGUIAdapter(agent)

    message = Message(role="user", content="Test")
    events = []

    async for event in adapter.stream_events(
        message=message,
        thread_id="thread-1",
    ):
        events.append(event)

    # Should have RunStarted and RunError
    assert len(events) == 2
    assert isinstance(events[0], RunStartedEvent)
    assert isinstance(events[1], RunErrorEvent)

    # Verify error details
    error_event = events[1]
    assert "Test error" in error_event.message
    assert error_event.code == "ValueError"


@pytest.mark.asyncio
async def test_adapter_with_metadata():
    """Test adapter preserves metadata."""
    agent = SimpleAgent()
    adapter = AGUIAdapter(agent)

    message = Message(role="user", content="Test")
    events = []

    async for event in adapter.stream_events(
        message=message,
        thread_id="thread-1",
        input_data={"extra": "data"},
    ):
        events.append(event)

    # Check RunStarted has input data
    run_started = events[0]
    assert run_started.input is not None
    assert run_started.input.get("extra") == "data"

    # Check TextMessageEnd has metadata
    text_end = [e for e in events if isinstance(e, TextMessageEndEvent)][0]
    assert text_end.metadata is not None
    assert text_end.metadata.get("original") == "Test"


# ============================================================================
# State Management Tests
# ============================================================================


def test_state_manager_basic():
    """Test basic state management."""
    manager = StateManager({"count": 0})

    # Get initial state
    state = manager.get_state()
    assert state == {"count": 0}

    # Update state
    manager.update("/count", 1)
    state = manager.get_state()
    assert state == {"count": 1}

    # Get delta
    delta_event = manager.get_delta_event()
    assert delta_event is not None
    assert len(delta_event.delta) == 1
    assert delta_event.delta[0]["op"] == "replace"
    assert delta_event.delta[0]["path"] == "/count"
    assert delta_event.delta[0]["value"] == 1


def test_state_manager_nested_updates():
    """Test nested state updates."""
    manager = StateManager()

    # Add nested value
    manager.update("/user/name", "Alice")
    manager.update("/user/age", 30)

    state = manager.get_state()
    assert state == {"user": {"name": "Alice", "age": 30}}

    # Get deltas
    delta_event = manager.get_delta_event()
    assert len(delta_event.delta) == 2


def test_state_manager_remove():
    """Test removing state values."""
    manager = StateManager({"temp": "data", "keep": "this"})

    manager.remove("/temp")

    state = manager.get_state()
    assert "temp" not in state
    assert "keep" in state

    delta_event = manager.get_delta_event()
    assert delta_event.delta[0]["op"] == "remove"


def test_state_manager_snapshot():
    """Test state snapshots."""
    manager = StateManager({"count": 5, "items": ["a", "b"]})

    snapshot_event = manager.get_snapshot_event()
    assert snapshot_event.snapshot == {"count": 5, "items": ["a", "b"]}


def test_state_manager_no_change():
    """Test that no delta is generated when state doesn't change."""
    manager = StateManager({"count": 1})

    # Update to same value
    manager.update("/count", 1)

    delta_event = manager.get_delta_event()
    assert delta_event is None


# ============================================================================
# Tool Tests
# ============================================================================


@pytest.mark.asyncio
async def test_tool_call_tracker():
    """Test tool call tracking."""
    tracker = ToolCallTracker()
    tool = SearchTool()

    events = []
    async for event in tracker.track_call(
        tool=tool,
        args={"query": "test"},
        parent_message_id="msg-1",
    ):
        events.append(event)

    # Should have: Start, Args, End, Result
    assert len(events) == 4

    # Verify types
    assert events[0].type == EventType.TOOL_CALL_START
    assert events[1].type == EventType.TOOL_CALL_ARGS
    assert events[2].type == EventType.TOOL_CALL_END
    assert events[3].type == EventType.TOOL_CALL_RESULT

    # Verify tool call ID consistency
    tool_call_id = events[0].tool_call_id
    assert events[1].tool_call_id == tool_call_id
    assert events[2].tool_call_id == tool_call_id
    assert events[3].tool_call_id == tool_call_id

    # Verify tool name
    assert events[0].tool_call_name == "search"

    # Verify result
    assert events[3].content is not None


def test_tool_registry():
    """Test tool registry."""
    registry = ToolRegistry()

    # Register tools
    search_tool = SearchTool()
    registry.register(search_tool)

    # Get tool
    tool = registry.get("search")
    assert tool is not None
    assert tool.name == "search"

    # Get all tools
    all_tools = registry.get_all()
    assert len(all_tools) == 1

    # Get metadata
    metadata = registry.get_metadata()
    assert len(metadata) == 1
    assert metadata[0]["name"] == "search"
    assert metadata[0]["description"] == "Search for information"


def test_tool_registry_not_found():
    """Test registry returns None for unknown tools."""
    registry = ToolRegistry()

    tool = registry.get("nonexistent")
    assert tool is None


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_streaming_flow():
    """Test complete streaming flow."""
    agent = SimpleAgent()
    adapter = AGUIAdapter(agent, chunk_size=10)

    events = []
    async for event in adapter.stream_events(
        message=Message(role="user", content="Test message"),
        thread_id="integration-test",
    ):
        events.append(event)

    # Verify we have a complete flow
    event_types = [e.type for e in events]

    assert EventType.RUN_STARTED in event_types
    assert EventType.TEXT_MESSAGE_START in event_types
    assert EventType.TEXT_MESSAGE_CONTENT in event_types
    assert EventType.TEXT_MESSAGE_END in event_types
    assert EventType.RUN_FINISHED in event_types

    # Verify no errors
    assert EventType.RUN_ERROR not in event_types


@pytest.mark.asyncio
async def test_state_and_streaming():
    """Test using state manager alongside streaming."""
    agent = SimpleAgent()
    adapter = AGUIAdapter(agent)
    state_manager = StateManager({"messages_count": 0})

    # Process message
    events = []
    async for event in adapter.stream_events(
        message=Message(role="user", content="Hello"),
        thread_id="state-test",
    ):
        events.append(event)

    # Update state
    state_manager.update("/messages_count", 1)
    state_manager.update("/last_message", "Hello")

    # Get state delta
    delta = state_manager.get_delta_event()
    assert delta is not None
    assert len(delta.delta) == 2

    # Verify we can get both streaming and state events
    assert len(events) > 0
    assert delta is not None

"""
Tests for orchestration patterns - core composition primitives.

Tests SequentialPattern, ParallelPattern, and RouterPattern.
"""

import asyncio

import pytest

from agenkit import Message
from agenkit.patterns.orchestration import ParallelPattern, RouterPattern, SequentialPattern

# ============================================================================
# Mock Agents
# ============================================================================


class MockAgent:
    """Simple mock agent for testing."""

    def __init__(self, name="mock", response="Success", delay=0, capabilities=None):
        self._name = name
        self.response = response
        self.delay = delay
        self._capabilities = capabilities or []
        self.call_count = 0
        self.last_message = None

    @property
    def name(self):
        return self._name

    @property
    def capabilities(self):
        return self._capabilities

    async def process(self, message: Message) -> Message:
        """Process message with optional delay."""
        self.call_count += 1
        self.last_message = message

        if self.delay > 0:
            await asyncio.sleep(self.delay)

        # Append agent name to content for pipeline tracking
        if isinstance(message.content, str):
            new_content = f"{message.content} -> {self._name}"
        else:
            new_content = self.response

        return Message(
            role="assistant",
            content=new_content,
            metadata={"agent": self._name, "call_count": self.call_count},
        )


class FailingAgent:
    """Agent that always fails."""

    def __init__(self, name="failing", error_message="Agent failed"):
        self._name = name
        self.error_message = error_message
        self.call_count = 0

    @property
    def name(self):
        return self._name

    @property
    def capabilities(self):
        return ["fail"]

    async def process(self, message: Message) -> Message:
        """Always raises an error."""
        self.call_count += 1
        raise RuntimeError(self.error_message)


# ============================================================================
# SequentialPattern Creation Tests
# ============================================================================


def test_sequential_creation():
    """Test basic sequential pattern creation."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    seq = SequentialPattern([agent1, agent2])

    assert seq._agents == [agent1, agent2]
    assert seq.name == "sequential"


def test_sequential_empty_agents_raises():
    """Test that empty agents list raises ValueError."""
    with pytest.raises(ValueError, match="at least one agent"):
        SequentialPattern([])


def test_sequential_custom_name():
    """Test sequential pattern with custom name."""
    agent = MockAgent("agent")
    seq = SequentialPattern([agent], name="custom_pipeline")

    assert seq.name == "custom_pipeline"


def test_sequential_with_hooks():
    """Test sequential pattern with hooks."""
    agent = MockAgent("agent")
    before_hook = lambda agent, msg: None  # noqa: E731
    after_hook = lambda agent, msg: None  # noqa: E731

    seq = SequentialPattern([agent], before_agent=before_hook, after_agent=after_hook)

    assert seq._before_agent is before_hook
    assert seq._after_agent is after_hook


# ============================================================================
# SequentialPattern Capabilities Tests
# ============================================================================


def test_sequential_capabilities_combined():
    """Test that capabilities are combined from all agents."""
    agent1 = MockAgent("agent1", capabilities=["search", "read"])
    agent2 = MockAgent("agent2", capabilities=["write", "format"])

    seq = SequentialPattern([agent1, agent2])
    caps = seq.capabilities

    # Should have all unique capabilities
    assert "search" in caps
    assert "read" in caps
    assert "write" in caps
    assert "format" in caps


def test_sequential_capabilities_deduplication():
    """Test that duplicate capabilities are deduplicated."""
    agent1 = MockAgent("agent1", capabilities=["search", "read"])
    agent2 = MockAgent("agent2", capabilities=["search", "write"])

    seq = SequentialPattern([agent1, agent2])
    caps = seq.capabilities

    # "search" should appear only once
    assert caps.count("search") == 1


# ============================================================================
# SequentialPattern Processing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_sequential_basic_processing():
    """Test basic sequential processing."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")
    agent3 = MockAgent("agent3")

    seq = SequentialPattern([agent1, agent2, agent3])

    message = Message(role="user", content="input")
    result = await seq.process(message)

    # Content should show pipeline progression
    assert result.content == "input -> agent1 -> agent2 -> agent3"

    # All agents should have been called
    assert agent1.call_count == 1
    assert agent2.call_count == 1
    assert agent3.call_count == 1


@pytest.mark.asyncio
async def test_sequential_message_flow():
    """Test that message flows through pipeline correctly."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    seq = SequentialPattern([agent1, agent2])

    message = Message(role="user", content="start")
    await seq.process(message)

    # Agent1 should receive original message
    assert agent1.last_message.content == "start"

    # Agent2 should receive agent1's output
    assert agent2.last_message.content == "start -> agent1"


@pytest.mark.asyncio
async def test_sequential_hooks_called():
    """Test that hooks are called during execution."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    before_calls = []
    after_calls = []

    def before_hook(agent, msg):
        before_calls.append((agent.name, msg.content))

    def after_hook(agent, msg):
        after_calls.append((agent.name, msg.content))

    seq = SequentialPattern([agent1, agent2], before_agent=before_hook, after_agent=after_hook)

    message = Message(role="user", content="input")
    await seq.process(message)

    # Before hooks should be called for both agents
    assert len(before_calls) == 2
    assert before_calls[0] == ("agent1", "input")
    assert before_calls[1] == ("agent2", "input -> agent1")

    # After hooks should be called for both agents
    assert len(after_calls) == 2
    assert after_calls[0] == ("agent1", "input -> agent1")
    assert after_calls[1] == ("agent2", "input -> agent1 -> agent2")


@pytest.mark.asyncio
async def test_sequential_error_propagates():
    """Test that errors propagate through pipeline."""
    agent1 = MockAgent("agent1")
    failing = FailingAgent("failing")
    agent3 = MockAgent("agent3")

    seq = SequentialPattern([agent1, failing, agent3])

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match="Agent failed"):
        await seq.process(message)

    # Agent1 should have been called
    assert agent1.call_count == 1

    # Agent3 should not have been called
    assert agent3.call_count == 0


# ============================================================================
# SequentialPattern Unwrap Tests
# ============================================================================


def test_sequential_unwrap():
    """Test unwrap returns copy of agents list."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    seq = SequentialPattern([agent1, agent2])
    unwrapped = seq.unwrap()

    assert unwrapped == [agent1, agent2]
    assert unwrapped is not seq._agents  # Should be a copy


# ============================================================================
# ParallelPattern Creation Tests
# ============================================================================


def test_parallel_creation():
    """Test basic parallel pattern creation."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    parallel = ParallelPattern([agent1, agent2])

    assert parallel._agents == [agent1, agent2]
    assert parallel.name == "parallel"


def test_parallel_empty_agents_raises():
    """Test that empty agents list raises ValueError."""
    with pytest.raises(ValueError, match="at least one agent"):
        ParallelPattern([])


def test_parallel_custom_name():
    """Test parallel pattern with custom name."""
    agent = MockAgent("agent")
    parallel = ParallelPattern([agent], name="custom_parallel")

    assert parallel.name == "custom_parallel"


def test_parallel_custom_aggregator():
    """Test parallel pattern with custom aggregator."""
    agent = MockAgent("agent")

    def custom_agg(messages):
        return messages[0]

    parallel = ParallelPattern([agent], aggregator=custom_agg)

    assert parallel._aggregator is custom_agg


# ============================================================================
# ParallelPattern Capabilities Tests
# ============================================================================


def test_parallel_capabilities_combined():
    """Test that capabilities are combined from all agents."""
    agent1 = MockAgent("agent1", capabilities=["search", "read"])
    agent2 = MockAgent("agent2", capabilities=["write", "format"])

    parallel = ParallelPattern([agent1, agent2])
    caps = parallel.capabilities

    # Should have all unique capabilities
    assert "search" in caps
    assert "read" in caps
    assert "write" in caps
    assert "format" in caps


def test_parallel_capabilities_deduplication():
    """Test that duplicate capabilities are deduplicated."""
    agent1 = MockAgent("agent1", capabilities=["search", "read"])
    agent2 = MockAgent("agent2", capabilities=["search", "write"])

    parallel = ParallelPattern([agent1, agent2])
    caps = parallel.capabilities

    # "search" should appear only once
    assert caps.count("search") == 1


# ============================================================================
# ParallelPattern Processing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_parallel_basic_processing():
    """Test basic parallel processing."""
    agent1 = MockAgent("agent1", response="Response1")
    agent2 = MockAgent("agent2", response="Response2")
    agent3 = MockAgent("agent3", response="Response3")

    parallel = ParallelPattern([agent1, agent2, agent3])

    message = Message(role="user", content="input")
    result = await parallel.process(message)

    # All agents should have been called
    assert agent1.call_count == 1
    assert agent2.call_count == 1
    assert agent3.call_count == 1

    # Default aggregator returns first result
    assert result.content == "input -> agent1"


@pytest.mark.asyncio
async def test_parallel_same_input_to_all():
    """Test that all agents receive the same input."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    parallel = ParallelPattern([agent1, agent2])

    message = Message(role="user", content="shared_input")
    await parallel.process(message)

    # All agents should receive same message
    assert agent1.last_message.content == "shared_input"
    assert agent2.last_message.content == "shared_input"


@pytest.mark.asyncio
async def test_parallel_concurrent_execution():
    """Test that agents execute concurrently."""
    # Agents with delays - if sequential, would take 0.3s total
    agent1 = MockAgent("agent1", delay=0.1)
    agent2 = MockAgent("agent2", delay=0.1)
    agent3 = MockAgent("agent3", delay=0.1)

    parallel = ParallelPattern([agent1, agent2, agent3])

    message = Message(role="user", content="input")

    start = asyncio.get_event_loop().time()
    await parallel.process(message)
    elapsed = asyncio.get_event_loop().time() - start

    # Should complete in ~0.1s (parallel) not 0.3s (sequential)
    # Allow some margin for overhead
    assert elapsed < 0.25


@pytest.mark.asyncio
async def test_parallel_default_aggregator():
    """Test default aggregator adds parallel_results to metadata."""
    agent1 = MockAgent("agent1", response="Response1")
    agent2 = MockAgent("agent2", response="Response2")

    parallel = ParallelPattern([agent1, agent2])

    message = Message(role="user", content="input")
    result = await parallel.process(message)

    # Should have parallel_results in metadata
    assert "parallel_results" in result.metadata
    parallel_results = result.metadata["parallel_results"]

    assert len(parallel_results) == 2
    assert parallel_results[0]["content"] == "input -> agent1"
    assert parallel_results[1]["content"] == "input -> agent2"


@pytest.mark.asyncio
async def test_parallel_custom_aggregator_used():
    """Test that custom aggregator is used."""
    agent1 = MockAgent("agent1", response="A")
    agent2 = MockAgent("agent2", response="B")

    def count_aggregator(messages):
        return Message(
            role="assistant",
            content=f"Aggregated {len(messages)} results",
            metadata={"count": len(messages)},
        )

    parallel = ParallelPattern([agent1, agent2], aggregator=count_aggregator)

    message = Message(role="user", content="input")
    result = await parallel.process(message)

    assert result.content == "Aggregated 2 results"
    assert result.metadata["count"] == 2


@pytest.mark.asyncio
async def test_parallel_error_propagates():
    """Test that errors from any agent propagate."""
    agent1 = MockAgent("agent1")
    failing = FailingAgent("failing")

    parallel = ParallelPattern([agent1, failing])

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match="Agent failed"):
        await parallel.process(message)


# ============================================================================
# ParallelPattern Unwrap Tests
# ============================================================================


def test_parallel_unwrap():
    """Test unwrap returns copy of agents list."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    parallel = ParallelPattern([agent1, agent2])
    unwrapped = parallel.unwrap()

    assert unwrapped == [agent1, agent2]
    assert unwrapped is not parallel._agents  # Should be a copy


# ============================================================================
# RouterPattern Creation Tests
# ============================================================================


def test_router_creation():
    """Test basic router pattern creation."""

    def route_fn(msg: Message) -> str:
        return "handler1"

    agent1 = MockAgent("agent1")

    router = RouterPattern(router=route_fn, handlers={"handler1": agent1})

    assert router._router is route_fn
    assert router._handlers == {"handler1": agent1}
    assert router.name == "router"


def test_router_empty_handlers_raises():
    """Test that empty handlers dict raises ValueError."""

    def route_fn(msg: Message) -> str:
        return "handler1"

    with pytest.raises(ValueError, match="at least one handler"):
        RouterPattern(router=route_fn, handlers={})


def test_router_custom_name():
    """Test router pattern with custom name."""

    def route_fn(msg: Message) -> str:
        return "handler1"

    agent = MockAgent("agent")
    router = RouterPattern(router=route_fn, handlers={"handler1": agent}, name="custom_router")

    assert router.name == "custom_router"


def test_router_with_default():
    """Test router pattern with default handler."""

    def route_fn(msg: Message) -> str:
        return "handler1"

    agent1 = MockAgent("agent1")
    default = MockAgent("default")

    router = RouterPattern(router=route_fn, handlers={"handler1": agent1}, default=default)

    assert router._default is default
    assert router._has_default is True


# ============================================================================
# RouterPattern Capabilities Tests
# ============================================================================


def test_router_capabilities_combined():
    """Test that capabilities are combined from all handlers."""

    def route_fn(msg: Message) -> str:
        return "handler1"

    agent1 = MockAgent("agent1", capabilities=["search", "read"])
    agent2 = MockAgent("agent2", capabilities=["write", "format"])

    router = RouterPattern(router=route_fn, handlers={"handler1": agent1, "handler2": agent2})
    caps = router.capabilities

    # Should have all unique capabilities
    assert "search" in caps
    assert "read" in caps
    assert "write" in caps
    assert "format" in caps


def test_router_capabilities_with_default():
    """Test that default handler capabilities are included."""

    def route_fn(msg: Message) -> str:
        return "handler1"

    agent1 = MockAgent("agent1", capabilities=["search"])
    default = MockAgent("default", capabilities=["fallback"])

    router = RouterPattern(router=route_fn, handlers={"handler1": agent1}, default=default)
    caps = router.capabilities

    # Should include both handler and default capabilities
    assert "search" in caps
    assert "fallback" in caps


# ============================================================================
# RouterPattern Processing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_router_basic_routing():
    """Test basic routing to correct handler."""

    def route_fn(msg: Message) -> str:
        if "code" in msg.content:
            return "code_handler"
        return "general_handler"

    code_agent = MockAgent("code_agent", response="Code response")
    general_agent = MockAgent("general_agent", response="General response")

    router = RouterPattern(
        router=route_fn, handlers={"code_handler": code_agent, "general_handler": general_agent}
    )

    # Test code routing
    message1 = Message(role="user", content="Write code for me")
    result1 = await router.process(message1)

    assert code_agent.call_count == 1
    assert general_agent.call_count == 0
    assert "code_agent" in result1.content

    # Test general routing
    message2 = Message(role="user", content="Hello there")
    result2 = await router.process(message2)

    assert code_agent.call_count == 1
    assert general_agent.call_count == 1
    assert "general_agent" in result2.content


@pytest.mark.asyncio
async def test_router_function_called():
    """Test that router function is called."""
    call_count = [0]

    def route_fn(msg: Message) -> str:
        call_count[0] += 1
        return "handler1"

    agent = MockAgent("agent")
    router = RouterPattern(router=route_fn, handlers={"handler1": agent})

    message = Message(role="user", content="test")
    await router.process(message)

    assert call_count[0] == 1


@pytest.mark.asyncio
async def test_router_default_handler_used():
    """Test that default handler is used for unknown keys."""

    def route_fn(msg: Message) -> str:
        return "unknown_handler"

    agent1 = MockAgent("agent1")
    default = MockAgent("default")

    router = RouterPattern(router=route_fn, handlers={"handler1": agent1}, default=default)

    message = Message(role="user", content="input")
    result = await router.process(message)

    # Should route to default
    assert agent1.call_count == 0
    assert default.call_count == 1
    assert "default" in result.content


@pytest.mark.asyncio
async def test_router_unknown_key_no_default_raises():
    """Test that unknown key without default raises KeyError."""

    def route_fn(msg: Message) -> str:
        return "unknown_handler"

    agent = MockAgent("agent")
    router = RouterPattern(router=route_fn, handlers={"handler1": agent})

    message = Message(role="user", content="input")

    with pytest.raises(KeyError, match="unknown key 'unknown_handler'"):
        await router.process(message)


@pytest.mark.asyncio
async def test_router_error_propagates():
    """Test that errors from handlers propagate."""

    def route_fn(msg: Message) -> str:
        return "failing_handler"

    failing = FailingAgent("failing")
    router = RouterPattern(router=route_fn, handlers={"failing_handler": failing})

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match="Agent failed"):
        await router.process(message)


# ============================================================================
# RouterPattern Unwrap Tests
# ============================================================================


def test_router_unwrap():
    """Test unwrap returns copy of handlers dict."""

    def route_fn(msg: Message) -> str:
        return "handler1"

    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    router = RouterPattern(router=route_fn, handlers={"handler1": agent1, "handler2": agent2})
    unwrapped = router.unwrap()

    assert unwrapped == {"handler1": agent1, "handler2": agent2}
    assert unwrapped is not router._handlers  # Should be a copy


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_nested_patterns():
    """Test nesting patterns within patterns."""
    # Create inner sequential pattern
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")
    inner = SequentialPattern([agent1, agent2])

    # Create outer parallel pattern
    agent3 = MockAgent("agent3")
    outer = ParallelPattern([inner, agent3])

    message = Message(role="user", content="input")
    await outer.process(message)

    # Both branches should execute
    assert agent1.call_count == 1
    assert agent2.call_count == 1
    assert agent3.call_count == 1


@pytest.mark.asyncio
async def test_router_with_patterns():
    """Test router routing to other patterns."""
    # Create sequential pattern
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")
    seq = SequentialPattern([agent1, agent2])

    # Create parallel pattern
    agent3 = MockAgent("agent3")
    agent4 = MockAgent("agent4")
    parallel = ParallelPattern([agent3, agent4])

    # Create router
    def route_fn(msg: Message) -> str:
        if "sequential" in msg.content:
            return "seq"
        return "parallel"

    router = RouterPattern(router=route_fn, handlers={"seq": seq, "parallel": parallel})

    # Test sequential routing
    message1 = Message(role="user", content="sequential task")
    await router.process(message1)

    assert agent1.call_count == 1
    assert agent2.call_count == 1
    assert agent3.call_count == 0
    assert agent4.call_count == 0

    # Test parallel routing
    message2 = Message(role="user", content="parallel task")
    await router.process(message2)

    assert agent1.call_count == 1  # No change
    assert agent2.call_count == 1  # No change
    assert agent3.call_count == 1
    assert agent4.call_count == 1

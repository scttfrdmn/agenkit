"""
Tests for orchestration patterns.

Tests verify:
- Sequential execution order and correctness
- Parallel concurrent execution and aggregation
- Router dispatch logic
- Edge cases and error handling
- Hook functionality
"""

import pytest
import asyncio
from typing import Optional

from agenkit.interfaces import Agent, Message
from agenkit.patterns import ParallelPattern, RouterPattern, SequentialPattern


# ============================================
# Test Agents
# ============================================


class EchoAgent(Agent):
    """Agent that echoes with prefix."""

    def __init__(self, prefix: str):
        self._prefix = prefix

    @property
    def name(self) -> str:
        return f"echo_{self._prefix}"

    async def process(self, message: Message) -> Message:
        return Message(
            role="agent",
            content=f"{self._prefix}: {message.content}"
        )


class UpperAgent(Agent):
    """Agent that uppercases content."""

    @property
    def name(self) -> str:
        return "upper"

    async def process(self, message: Message) -> Message:
        return Message(
            role="agent",
            content=str(message.content).upper()
        )


class SlowAgent(Agent):
    """Agent that introduces delay."""

    def __init__(self, delay: float, name: str = "slow"):
        self._delay = delay
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(self._delay)
        return Message(
            role="agent",
            content=f"slow: {message.content}"
        )


class ErrorAgent(Agent):
    """Agent that raises an error."""

    @property
    def name(self) -> str:
        return "error"

    async def process(self, message: Message) -> Message:
        raise RuntimeError("Intentional error")


# ============================================
# SequentialPattern Tests
# ============================================


@pytest.mark.asyncio
async def test_sequential_basic():
    """Test basic sequential execution."""
    agent1 = EchoAgent("first")
    agent2 = EchoAgent("second")
    agent3 = EchoAgent("third")

    seq = SequentialPattern([agent1, agent2, agent3])

    msg = Message(role="user", content="hello")
    result = await seq.process(msg)

    # Should apply each transformation in order
    assert result.content == "third: second: first: hello"


@pytest.mark.asyncio
async def test_sequential_single_agent():
    """Test sequential with single agent."""
    agent = UpperAgent()
    seq = SequentialPattern([agent])

    msg = Message(role="user", content="hello")
    result = await seq.process(msg)

    assert result.content == "HELLO"


def test_sequential_empty_raises():
    """Test that empty agent list raises."""
    with pytest.raises(ValueError, match="at least one agent"):
        SequentialPattern([])


@pytest.mark.asyncio
async def test_sequential_error_propagates():
    """Test that errors propagate from agents."""
    agent1 = UpperAgent()
    agent2 = ErrorAgent()
    agent3 = UpperAgent()  # Never reached

    seq = SequentialPattern([agent1, agent2, agent3])

    msg = Message(role="user", content="hello")
    with pytest.raises(RuntimeError, match="Intentional error"):
        await seq.process(msg)


@pytest.mark.asyncio
async def test_sequential_hooks():
    """Test before/after hooks."""
    agent1 = UpperAgent()
    agent2 = EchoAgent("echo")

    calls = []

    def before(agent: Agent, message: Message) -> None:
        calls.append(("before", agent.name, message.content))

    def after(agent: Agent, message: Message) -> None:
        calls.append(("after", agent.name, message.content))

    seq = SequentialPattern(
        [agent1, agent2],
        before_agent=before,
        after_agent=after
    )

    msg = Message(role="user", content="hello")
    await seq.process(msg)

    # Should have before/after for each agent
    assert len(calls) == 4
    assert calls[0] == ("before", "upper", "hello")
    assert calls[1] == ("after", "upper", "HELLO")
    assert calls[2] == ("before", "echo_echo", "HELLO")
    assert calls[3] == ("after", "echo_echo", "echo: HELLO")


@pytest.mark.asyncio
async def test_sequential_capabilities():
    """Test combined capabilities."""
    class CapAgent1(Agent):
        @property
        def name(self) -> str:
            return "cap1"

        @property
        def capabilities(self) -> list[str]:
            return ["search", "code"]

        async def process(self, message: Message) -> Message:
            return message

    class CapAgent2(Agent):
        @property
        def name(self) -> str:
            return "cap2"

        @property
        def capabilities(self) -> list[str]:
            return ["summarize", "code"]

        async def process(self, message: Message) -> Message:
            return message

    seq = SequentialPattern([CapAgent1(), CapAgent2()])
    caps = seq.capabilities

    assert "search" in caps
    assert "code" in caps
    assert "summarize" in caps
    assert len([c for c in caps if c == "code"]) == 1  # De-duplicated


@pytest.mark.asyncio
async def test_sequential_unwrap():
    """Test unwrap returns agents list."""
    agent1 = UpperAgent()
    agent2 = EchoAgent("echo")

    seq = SequentialPattern([agent1, agent2])
    agents = seq.unwrap()

    assert len(agents) == 2
    assert agents[0] is agent1
    assert agents[1] is agent2


# ============================================
# ParallelPattern Tests
# ============================================


@pytest.mark.asyncio
async def test_parallel_basic():
    """Test basic parallel execution."""
    agent1 = EchoAgent("first")
    agent2 = EchoAgent("second")
    agent3 = EchoAgent("third")

    parallel = ParallelPattern([agent1, agent2, agent3])

    msg = Message(role="user", content="hello")
    result = await parallel.process(msg)

    # Default aggregator returns first result
    assert result.content == "first: hello"

    # But all results are in metadata
    all_results = result.metadata["parallel_results"]
    assert len(all_results) == 3


@pytest.mark.asyncio
async def test_parallel_custom_aggregator():
    """Test parallel with custom aggregator."""
    agent1 = EchoAgent("A")
    agent2 = EchoAgent("B")
    agent3 = EchoAgent("C")

    def combine(messages: list[Message]) -> Message:
        # Combine all content
        combined = " | ".join(msg.content for msg in messages)
        return Message(role="agent", content=combined)

    parallel = ParallelPattern(
        [agent1, agent2, agent3],
        aggregator=combine
    )

    msg = Message(role="user", content="x")
    result = await parallel.process(msg)

    # Results combined
    assert "A: x" in result.content
    assert "B: x" in result.content
    assert "C: x" in result.content


@pytest.mark.asyncio
async def test_parallel_concurrent_execution():
    """Test that parallel actually runs concurrently."""
    import time

    # Three agents that each take 0.1s
    agent1 = SlowAgent(0.1, "slow1")
    agent2 = SlowAgent(0.1, "slow2")
    agent3 = SlowAgent(0.1, "slow3")

    parallel = ParallelPattern([agent1, agent2, agent3])

    msg = Message(role="user", content="test")

    start = time.time()
    await parallel.process(msg)
    elapsed = time.time() - start

    # If sequential, would take 0.3s
    # If parallel, should take ~0.1s
    assert elapsed < 0.2, "Parallel execution should be concurrent"


def test_parallel_empty_raises():
    """Test that empty agent list raises."""
    with pytest.raises(ValueError, match="at least one agent"):
        ParallelPattern([])


@pytest.mark.asyncio
async def test_parallel_error_cancels_all():
    """Test that error in one agent cancels all."""
    agent1 = SlowAgent(1.0, "slow1")  # Would take 1s
    agent2 = ErrorAgent()  # Fails immediately
    agent3 = SlowAgent(1.0, "slow3")  # Would take 1s

    parallel = ParallelPattern([agent1, agent2, agent3])

    msg = Message(role="user", content="test")

    import time
    start = time.time()

    with pytest.raises(RuntimeError, match="Intentional error"):
        await parallel.process(msg)

    elapsed = time.time() - start

    # Should fail fast, not wait for slow agents
    assert elapsed < 0.5, "Should cancel other agents on error"


@pytest.mark.asyncio
async def test_parallel_unwrap():
    """Test unwrap returns agents list."""
    agent1 = UpperAgent()
    agent2 = EchoAgent("echo")

    parallel = ParallelPattern([agent1, agent2])
    agents = parallel.unwrap()

    assert len(agents) == 2
    # Order not guaranteed in parallel, just check both present
    assert agent1 in agents
    assert agent2 in agents


# ============================================
# RouterPattern Tests
# ============================================


@pytest.mark.asyncio
async def test_router_basic():
    """Test basic routing."""
    agent1 = EchoAgent("route1")
    agent2 = EchoAgent("route2")

    def router(message: Message) -> str:
        content = str(message.content)
        if "first" in content:
            return "route1"
        return "route2"

    pattern = RouterPattern(
        router=router,
        handlers={"route1": agent1, "route2": agent2}
    )

    # Route to first
    msg1 = Message(role="user", content="use first")
    result1 = await pattern.process(msg1)
    assert result1.content == "route1: use first"

    # Route to second
    msg2 = Message(role="user", content="use second")
    result2 = await pattern.process(msg2)
    assert result2.content == "route2: use second"


@pytest.mark.asyncio
async def test_router_unknown_key_raises():
    """Test that unknown key without default raises."""
    agent1 = EchoAgent("route1")

    def router(message: Message) -> str:
        return "unknown_route"

    pattern = RouterPattern(
        router=router,
        handlers={"route1": agent1}
    )

    msg = Message(role="user", content="test")
    with pytest.raises(KeyError, match="unknown key"):
        await pattern.process(msg)


@pytest.mark.asyncio
async def test_router_unknown_key_uses_default():
    """Test that unknown key uses default handler."""
    agent1 = EchoAgent("route1")
    default_agent = EchoAgent("default")

    def router(message: Message) -> str:
        return "unknown_route"

    pattern = RouterPattern(
        router=router,
        handlers={"route1": agent1},
        default=default_agent
    )

    msg = Message(role="user", content="test")
    result = await pattern.process(msg)
    assert result.content == "default: test"


def test_router_empty_handlers_raises():
    """Test that empty handlers dict raises."""
    def router(message: Message) -> str:
        return "any"

    with pytest.raises(ValueError, match="at least one handler"):
        RouterPattern(router=router, handlers={})


@pytest.mark.asyncio
async def test_router_unwrap():
    """Test unwrap returns handlers dict."""
    agent1 = EchoAgent("route1")
    agent2 = EchoAgent("route2")

    def router(message: Message) -> str:
        return "route1"

    pattern = RouterPattern(
        router=router,
        handlers={"route1": agent1, "route2": agent2}
    )

    handlers = pattern.unwrap()
    assert len(handlers) == 2
    assert handlers["route1"] is agent1
    assert handlers["route2"] is agent2


# ============================================
# Pattern Composition Tests
# ============================================


@pytest.mark.asyncio
async def test_patterns_compose():
    """Test that patterns can be composed (patterns of patterns)."""
    # Build nested structure:
    # Sequential [
    #   Parallel [agent1, agent2],
    #   Router {key1 → agent3, key2 → agent4}
    # ]

    agent1 = EchoAgent("A")
    agent2 = EchoAgent("B")
    agent3 = EchoAgent("C")
    agent4 = EchoAgent("D")

    # Parallel pattern
    parallel = ParallelPattern(
        [agent1, agent2],
        aggregator=lambda msgs: Message(role="agent", content="parallel_done")
    )

    # Router pattern
    def router(msg: Message) -> str:
        return "key1"

    router_pattern = RouterPattern(
        router=router,
        handlers={"key1": agent3, "key2": agent4}
    )

    # Sequential composing both
    seq = SequentialPattern([parallel, router_pattern])

    msg = Message(role="user", content="test")
    result = await seq.process(msg)

    assert result.content == "C: parallel_done"

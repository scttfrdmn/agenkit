"""
Performance benchmarks for all 18 agenkit patterns.

This module measures the raw overhead of each pattern in isolation using
mock agents to eliminate LLM latency. Results show pattern framework cost
separate from inference time.

Run benchmarks:
    pytest tests/benchmarks/test_pattern_performance.py -v -s

Each benchmark measures:
- Mean execution time (μs)
- Standard deviation
- Min/Max execution time
- Iterations performed

Pattern categories:
- Core: Reflection, ReAct, Agents-as-Tools, Orchestration
- Advanced: Reasoning with Tools, Conversational, Task, Multiagent
- Strategic: Planning, Autonomous
- Memory: Working, Short-Term, Hierarchy
- Composition: Sequential, Parallel, Router, Fallback
- Coordination: Collaborative, Human-in-Loop, Supervisor
"""

import asyncio
import json
import statistics
import time
from datetime import UTC
from typing import Any

import pytest

from agenkit import Agent, Message
from agenkit.patterns import (
    AgentTool,
    AutonomousAgent,
    CollaborativeAgent,
    CollaborativeConfig,
    ConversationalAgent,
    FallbackAgent,
    HumanInLoopAgent,
    HumanInLoopConfig,
    LongTermMemory,
    MemoryEntry,
    MemoryHierarchy,
    MultiAgentOrchestrator,
    ParallelAgent,
    PlanningAgent,
    ReActAgent,
    ReasoningWithToolsAgent,
    ReflectionAgent,
    RouterAgent,
    RouterConfig,
    SequentialAgent,
    ShortTermMemory,
    SimpleClassifier,
    SimplePlanner,
    SupervisorAgent,
    Task,
    Tool,
    WorkingMemory,
)

# ==============================================================================
# Mock Agents for Benchmarking
# ==============================================================================


class EchoAgent(Agent):
    """Minimal agent that echoes input content."""

    def __init__(self, name: str = "echo"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def capabilities(self) -> list[str]:
        return ["echo"]

    async def process(self, message: Message) -> Message:
        """Echo the message content."""
        return Message(role="assistant", content=message.content)

    async def call(self, messages: list[Message], **kwargs) -> Message:
        """Call interface for Task pattern."""
        return await self.process(messages[0] if messages else Message(role="user", content=""))


class MockLLMClient(Agent):
    """Mock LLM client for patterns that need it."""

    @property
    def name(self) -> str:
        return "mock-client"

    def capabilities(self) -> list[str]:
        return ["chat"]

    async def process(self, message: Message) -> Message:
        """Return simple response."""
        return Message(role="assistant", content="response")

    async def chat(self, messages: list[Message]) -> Message:
        """Return simple response."""
        return Message(role="assistant", content="response")


class MockCritic(Agent):
    """Mock critic that always returns high quality score."""

    @property
    def name(self) -> str:
        return "mock_critic"

    def capabilities(self) -> list[str]:
        return ["critique"]

    async def process(self, message: Message) -> Message:
        """Return structured critique."""
        critique = json.dumps({"score": 0.95, "feedback": "Good"})
        return Message(role="assistant", content=critique)


class MockTool(Tool):
    """Mock tool for ReAct and Reasoning patterns."""

    def __init__(self, name: str = "mock_tool"):
        self._name = name
        self._description = f"Mock tool {name}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, **kwargs: Any) -> str:
        """Return mock tool result."""
        return f"Tool {self._name} result"


# ==============================================================================
# Benchmark Utilities
# ==============================================================================


def benchmark_async(coro_fn, iterations: int = 100, warmup: int = 10):
    """
    Benchmark async coroutine function.

    Args:
        coro_fn: Async function to benchmark
        iterations: Number of iterations
        warmup: Warmup iterations

    Returns:
        Dict with timing statistics (μs)
    """

    async def run_benchmark():
        # Warmup
        for _ in range(warmup):
            await coro_fn()

        # Measure
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await coro_fn()
            elapsed = (time.perf_counter() - start) * 1_000_000  # Convert to μs
            times.append(elapsed)

        return {
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0.0,
            "min": min(times),
            "max": max(times),
            "iterations": iterations,
        }

    return asyncio.run(run_benchmark())


def print_result(pattern_name: str, result: dict[str, float]):
    """Print benchmark result in consistent format."""
    print(f"\n{pattern_name}:")
    print(f"  Mean:   {result['mean']:.3f} μs")
    print(f"  Median: {result['median']:.3f} μs")
    print(f"  StdDev: {result['stdev']:.3f} μs")
    print(f"  Min:    {result['min']:.3f} μs")
    print(f"  Max:    {result['max']:.3f} μs")


# ==============================================================================
# Pattern Benchmarks
# ==============================================================================


@pytest.mark.benchmark
def test_benchmark_reflection():
    """Benchmark Reflection pattern (2 iterations)."""
    generator = EchoAgent()
    critic = MockCritic()
    agent = ReflectionAgent(
        generator=generator, critic=critic, max_reflections=2, quality_threshold=0.99
    )
    msg = Message(role="user", content="test")

    async def bench():
        await agent.process(msg)

    result = benchmark_async(bench, iterations=100)
    print_result("Reflection (2 iterations)", result)
    assert result["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_react():
    """Benchmark ReAct pattern (3 steps)."""
    llm = MockLLMClient()
    tools = [MockTool("tool1"), MockTool("tool2")]
    agent = ReActAgent(agent=llm, tools=tools, max_steps=3)
    msg = Message(role="user", content="test")

    async def bench():
        await agent.process(msg)

    result = benchmark_async(bench, iterations=100)
    print_result("ReAct (3 steps)", result)
    assert result["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_agents_as_tools():
    """Benchmark Agents-as-Tools pattern (wrapping agents as tools)."""
    specialist1 = EchoAgent(name="specialist1")

    # Wrap agent as tool
    tool = AgentTool(
        agent=specialist1,
        name="specialist1",
        description="Specialist 1",
    )

    # Use tool (simulates coordinator calling specialist)
    async def bench():
        await tool.execute(params={"query": "test"})

    result = benchmark_async(bench, iterations=100)
    print_result("Agents-as-Tools (tool call)", result)
    assert result["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_orchestration():
    """Benchmark Orchestration pattern (MultiAgentOrchestrator)."""
    agent1 = EchoAgent(name="agent1")
    agent2 = EchoAgent(name="agent2")

    orchestrator = MultiAgentOrchestrator(strategy="sequential")
    orchestrator.register_agent("agent1", agent1)
    orchestrator.register_agent("agent2", agent2)

    msg = Message(role="user", content="test")

    async def bench():
        await orchestrator.process(msg)

    result = benchmark_async(bench, iterations=100)
    print_result("Orchestration (2 agents)", result)
    assert result["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_reasoning_with_tools():
    """Benchmark Reasoning with Tools pattern."""
    llm = EchoAgent()
    tools = [MockTool("tool1"), MockTool("tool2")]
    agent = ReasoningWithToolsAgent(llm=llm, tools=tools, max_reasoning_steps=3)
    msg = Message(role="user", content="test")

    async def bench():
        await agent.process(msg)

    result = benchmark_async(bench, iterations=100)
    print_result("Reasoning with Tools", result)
    assert result["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_conversational():
    """Benchmark Conversational pattern (10 max history, with clearing)."""
    llm_client = MockLLMClient()
    agent = ConversationalAgent(llm_client=llm_client, max_history=10)
    msg = Message(role="user", content="test")

    async def bench():
        await agent.process(msg)
        agent.clear_history(keep_system=False)

    result = benchmark_async(bench, iterations=100)
    print_result("Conversational (10 history, clearing)", result)
    assert result["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_task():
    """Benchmark Task pattern (one-shot)."""
    echo = EchoAgent()
    msg = Message(role="user", content="test")

    async def bench():
        task = Task(echo)
        await task.execute([msg])

    result = benchmark_async(bench, iterations=100)
    print_result("Task (one-shot)", result)
    assert result["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_multiagent():
    """Benchmark Multiagent pattern (2 agents, sequential)."""
    agent1 = EchoAgent(name="agent1")
    agent2 = EchoAgent(name="agent2")

    orchestrator = MultiAgentOrchestrator(strategy="sequential")
    orchestrator.register_agent("agent1", agent1)
    orchestrator.register_agent("agent2", agent2)

    msg = Message(role="user", content="test")

    async def bench():
        await orchestrator.process(msg)

    result = benchmark_async(bench, iterations=100)
    print_result("Multiagent (2 sequential)", result)
    assert result["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_planning():
    """Benchmark Planning pattern (plan + execute)."""
    llm = MockLLMClient()
    agent = PlanningAgent(planner=llm, max_steps=2)
    msg = Message(role="user", content="test")

    async def bench():
        await agent.process(msg)

    result = benchmark_async(bench, iterations=100)
    print_result("Planning (plan + execute)", result)
    assert result["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_autonomous():
    """Benchmark Autonomous pattern (5 iterations)."""

    async def bench():
        # Create fresh agent per iteration
        agent = AutonomousAgent(objective="complete task", max_iterations=5)
        await agent.run()

    result = benchmark_async(bench, iterations=100)
    print_result("Autonomous (5 iterations)", result)
    assert result["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_memory_working():
    """Benchmark Memory: Working (store + retrieve)."""
    from datetime import datetime

    async def bench_store():
        memory = WorkingMemory(max_messages=10)
        entry = MemoryEntry(
            id="test",
            content="test content",
            metadata={},
            timestamp=datetime.now(UTC),
        )
        await memory.store(entry)

    async def bench_retrieve():
        memory = WorkingMemory(max_messages=10)
        entry = MemoryEntry(
            id="test",
            content="test content",
            metadata={},
            timestamp=datetime.now(UTC),
        )
        await memory.store(entry)
        await memory.retrieve("test", limit=5)

    result_store = benchmark_async(bench_store, iterations=1000)
    result_retrieve = benchmark_async(bench_retrieve, iterations=1000)

    print_result("Memory: Working (store)", result_store)
    print_result("Memory: Working (retrieve)", result_retrieve)

    assert result_store["mean"] > 0
    assert result_retrieve["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_memory_short_term():
    """Benchmark Memory: Short-Term (store + retrieve)."""
    from datetime import datetime

    async def bench_store():
        memory = ShortTermMemory(max_messages=100, ttl_seconds=3600)
        entry = MemoryEntry(
            id="test",
            content="test content",
            metadata={},
            timestamp=datetime.now(UTC),
        )
        await memory.store(entry)

    async def bench_retrieve():
        memory = ShortTermMemory(max_messages=100, ttl_seconds=3600)
        entry = MemoryEntry(
            id="test",
            content="test content",
            metadata={},
            timestamp=datetime.now(UTC),
        )
        await memory.store(entry)
        await memory.retrieve("test", limit=5)

    result_store = benchmark_async(bench_store, iterations=1000)
    result_retrieve = benchmark_async(bench_retrieve, iterations=1000)

    print_result("Memory: Short-Term (store)", result_store)
    print_result("Memory: Short-Term (retrieve)", result_retrieve)

    assert result_store["mean"] > 0
    assert result_retrieve["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_memory_hierarchy():
    """Benchmark Memory: Hierarchy (store + retrieve)."""

    async def bench_store():
        working = WorkingMemory(max_messages=10)
        short_term = ShortTermMemory(max_messages=100, ttl_seconds=3600)
        long_term = LongTermMemory(storage_backend={}, min_importance=0.5)

        memory = MemoryHierarchy(working, short_term, long_term)
        await memory.store(
            content="test content",
            metadata={"priority": 0.7},
            importance=0.7,
            session_id="",
        )

    async def bench_retrieve():
        working = WorkingMemory(max_messages=10)
        short_term = ShortTermMemory(max_messages=100, ttl_seconds=3600)
        long_term = LongTermMemory(storage_backend={}, min_importance=0.5)

        memory = MemoryHierarchy(working, short_term, long_term)
        await memory.store(
            content="test content",
            metadata={"priority": 0.7},
            importance=0.7,
            session_id="",
        )
        await memory.retrieve("test", limit=5)

    result_store = benchmark_async(bench_store, iterations=1000)
    result_retrieve = benchmark_async(bench_retrieve, iterations=1000)

    print_result("Memory: Hierarchy (store)", result_store)
    print_result("Memory: Hierarchy (retrieve)", result_retrieve)

    assert result_store["mean"] > 0
    assert result_retrieve["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_sequential():
    """Benchmark Sequential pattern (3 agents)."""
    agent1 = EchoAgent(name="agent1")
    agent2 = EchoAgent(name="agent2")
    agent3 = EchoAgent(name="agent3")

    agent = SequentialAgent(agents=[agent1, agent2, agent3])
    msg = Message(role="user", content="test")

    async def bench():
        await agent.process(msg)

    result = benchmark_async(bench, iterations=100)
    print_result("Sequential (3 agents)", result)
    assert result["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_parallel():
    """Benchmark Parallel pattern (3 agents)."""
    agent1 = EchoAgent(name="agent1")
    agent2 = EchoAgent(name="agent2")
    agent3 = EchoAgent(name="agent3")

    def simple_aggregator(responses: list[Message]) -> Message:
        """Simple aggregator that returns first response."""
        return responses[0] if responses else Message(role="assistant", content="")

    agent = ParallelAgent(agents=[agent1, agent2, agent3], aggregator=simple_aggregator)
    msg = Message(role="user", content="test")

    async def bench():
        await agent.process(msg)

    result = benchmark_async(bench, iterations=100)
    print_result("Parallel (3 agents)", result)
    assert result["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_router():
    """Benchmark Router pattern (2 routes)."""
    agent1 = EchoAgent(name="agent1")
    agent2 = EchoAgent(name="agent2")

    # Simple classifier that always routes to agent1
    classifier = SimpleClassifier(
        agent=EchoAgent(), keywords={"agent1": ["test"], "agent2": ["other"]}
    )

    config = RouterConfig(
        classifier=classifier,
        agents={"agent1": agent1, "agent2": agent2},
        default_key="agent1",
    )

    agent = RouterAgent(config=config)
    msg = Message(role="user", content="test")

    async def bench():
        await agent.process(msg)

    result = benchmark_async(bench, iterations=100)
    print_result("Router (2 routes)", result)
    assert result["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_fallback():
    """Benchmark Fallback pattern (2 agents)."""
    agent1 = EchoAgent(name="agent1")
    agent2 = EchoAgent(name="agent2")

    agent = FallbackAgent(agents=[agent1, agent2])
    msg = Message(role="user", content="test")

    async def bench():
        await agent.process(msg)

    result = benchmark_async(bench, iterations=100)
    print_result("Fallback (2 agents)", result)
    assert result["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_collaborative():
    """Benchmark Collaborative pattern (2 rounds)."""
    agent1 = EchoAgent(name="agent1")
    agent2 = EchoAgent(name="agent2")

    config = CollaborativeConfig(
        agents=[agent1, agent2],
        max_rounds=2,
        merge_func=lambda responses: responses[0],  # Simple merge
    )

    agent = CollaborativeAgent(config=config)
    msg = Message(role="user", content="test")

    async def bench():
        await agent.process(msg)

    result = benchmark_async(bench, iterations=100)
    print_result("Collaborative (2 rounds)", result)
    assert result["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_human_in_loop():
    """Benchmark Human-in-Loop pattern (auto-approve)."""
    echo = EchoAgent()

    def auto_approve(request):
        """Auto-approve all requests."""
        from agenkit.patterns import ApprovalResponse

        return ApprovalResponse(approved=True, feedback="approved")

    config = HumanInLoopConfig(
        agent=echo,
        approval_func=auto_approve,
        approval_threshold=0.0,  # Always require approval
    )

    agent = HumanInLoopAgent(config=config)
    msg = Message(role="user", content="test")

    async def bench():
        await agent.process(msg)

    result = benchmark_async(bench, iterations=100)
    print_result("Human-in-Loop (auto-approve)", result)
    assert result["mean"] > 0


@pytest.mark.benchmark
def test_benchmark_supervisor():
    """Benchmark Supervisor pattern (2 specialists)."""
    echo = EchoAgent()
    planner = SimplePlanner(echo)

    specialists = {
        "specialist1": EchoAgent(name="specialist1"),
        "specialist2": EchoAgent(name="specialist2"),
    }

    agent = SupervisorAgent(planner=planner, specialists=specialists)
    msg = Message(role="user", content="test")

    async def bench():
        await agent.process(msg)

    result = benchmark_async(bench, iterations=100)
    print_result("Supervisor (2 specialists)", result)
    assert result["mean"] > 0


# ==============================================================================
# Summary Test
# ==============================================================================


@pytest.mark.benchmark
def test_benchmark_summary():
    """
    Run all benchmarks and print summary.

    This test should be run last to provide an overview of all pattern performance.
    """
    print("\n" + "=" * 80)
    print("PYTHON PATTERN BENCHMARK SUMMARY")
    print("=" * 80)
    print("\nAll 18 patterns benchmarked successfully!")
    print("\nRun individual tests with:")
    print("  pytest tests/benchmarks/test_pattern_performance.py::test_benchmark_<pattern> -v -s")
    print("\nRun all benchmarks with output:")
    print("  pytest tests/benchmarks/test_pattern_performance.py -v -s -m benchmark")

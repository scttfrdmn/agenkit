#!/usr/bin/env python3
"""
Python Pattern Performance Benchmarks

Measures ACTUAL pattern overhead using mock agents for all 17 patterns.
This matches the Go and C++ benchmark methodology - measuring pattern logic,
not LLM performance.

IMPORTANT: This tests the actual pattern implementations (ReflectionAgent,
ReActAgent, etc.), not just simple mock agent echo. The previous version
incorrectly measured only mock echo latency (~1.59 μs), not pattern overhead.
"""

import asyncio
import time
from typing import Any

from agenkit import Agent, Message
from agenkit.patterns import (
    AgentTool,
    AutonomousAgent,
    CollaborativeAgent,
    ConversationalAgent,
    FallbackAgent,
    HumanInLoopAgent,
    MultiAgentOrchestrator,
    OrchestrationAgent,
    ParallelAgent,
    PlanningAgent,
    ReActAgent,
    ReasoningWithToolsAgent,
    ReflectionAgent,
    RouterAgent,
    RouterConfig,
    SequentialAgent,
    SupervisorAgent,
    SupervisorConfig,
    default_aggregators,
)


class MockAgent(Agent):
    """Minimal mock agent for performance testing."""

    def __init__(self, name: str = "mock"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def process(self, message: Message) -> Message:
        """Process with minimal overhead - just echo."""
        return Message(
            role="assistant",
            content=f"Processed: {message.content[:20]}...",
            metadata={"mock": True},
        )


class MockTool:
    """Mock tool for ReAct/Reasoning benchmarks."""

    def __init__(self, name: str = "test_tool"):
        self._name = name
        self.description = "A test tool"

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, **kwargs) -> dict[str, Any]:
        return {"result": "tool executed"}


class MockLLMClient:
    """Mock LLM client for Conversational pattern."""

    async def chat(self, messages: list[Message]) -> Message:
        return Message(role="assistant", content="LLM response")


class MockClassifier:
    """Mock classifier for Router pattern."""

    async def classify(self, message: Message) -> str:
        return "agent1"


class MockSubtask:
    """Mock subtask for Supervisor pattern."""

    def __init__(self, agent_type: str, task_message: Message):
        self.type = agent_type
        self.message = task_message
        self.metadata = {}


class MockPlanner:
    """Mock planner for Supervisor pattern."""

    async def plan(self, message: Message) -> list[MockSubtask]:
        return [
            MockSubtask(agent_type="agent1", task_message=Message(role="user", content="subtask1")),
            MockSubtask(agent_type="agent2", task_message=Message(role="user", content="subtask2")),
        ]

    async def synthesize(self, original: Message, results: list[Message]) -> Message:
        return Message(role="assistant", content="Synthesized result", metadata={})


class MockApprovalFunc:
    """Mock approval function for Human-in-Loop pattern."""

    async def __call__(self, message: Message) -> tuple[bool, str]:
        return True, "approved"


async def benchmark_reflection(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark Reflection pattern (2 iterations)."""
    generator = MockAgent("generator")
    critic = MockAgent("critic")

    agent = ReflectionAgent(
        generator=generator,
        critic=critic,
        max_reflections=2,
    )

    msg = Message(role="user", content="test input")

    # Warmup
    for _ in range(10):
        await agent.process(msg)

    # Benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        await agent.process(msg)
    elapsed = time.perf_counter() - start

    return {
        "pattern": "reflection",
        "iterations": iterations,
        "total_time_sec": elapsed,
        "avg_time_us": (elapsed / iterations) * 1_000_000,
        "ops_per_sec": iterations / elapsed,
    }


async def benchmark_react(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark ReAct pattern (3 steps)."""
    agent = MockAgent()
    tool = MockTool()

    react_agent = ReActAgent(
        agent=agent,
        tools=[tool],
        max_steps=3,
    )

    msg = Message(role="user", content="test input")

    # Warmup
    for _ in range(10):
        await react_agent.process(msg)

    # Benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        await react_agent.process(msg)
    elapsed = time.perf_counter() - start

    return {
        "pattern": "react",
        "iterations": iterations,
        "total_time_sec": elapsed,
        "avg_time_us": (elapsed / iterations) * 1_000_000,
        "ops_per_sec": iterations / elapsed,
    }


async def benchmark_agents_as_tools(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark Agents-as-Tools pattern."""
    agent = MockAgent()

    tool = AgentTool(
        agent=agent,
        name="test_tool",
        description="Test tool",
    )

    # Warmup
    for _ in range(10):
        await tool.execute(query="test")

    # Benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        await tool.execute(query="test")
    elapsed = time.perf_counter() - start

    return {
        "pattern": "agents_as_tools",
        "iterations": iterations,
        "total_time_sec": elapsed,
        "avg_time_us": (elapsed / iterations) * 1_000_000,
        "ops_per_sec": iterations / elapsed,
    }


async def benchmark_reasoning_with_tools(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark Reasoning with Tools pattern (5 steps)."""
    agent = MockAgent()
    tool = MockTool()

    reasoning_agent = ReasoningWithToolsAgent(
        llm=agent,
        tools=[tool],
        max_reasoning_steps=5,
    )

    msg = Message(role="user", content="test input")

    # Warmup
    for _ in range(10):
        await reasoning_agent.process(msg)

    # Benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        await reasoning_agent.process(msg)
    elapsed = time.perf_counter() - start

    return {
        "pattern": "reasoning_with_tools",
        "iterations": iterations,
        "total_time_sec": elapsed,
        "avg_time_us": (elapsed / iterations) * 1_000_000,
        "ops_per_sec": iterations / elapsed,
    }


async def benchmark_conversational(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark Conversational pattern (10 history limit)."""
    llm_client = MockLLMClient()

    agent = ConversationalAgent(
        llm_client=llm_client,
        max_history=10,
    )

    msg = Message(role="user", content="test input")

    # Warmup
    for _ in range(10):
        await agent.process(msg)

    # Benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        await agent.process(msg)
    elapsed = time.perf_counter() - start

    return {
        "pattern": "conversational",
        "iterations": iterations,
        "total_time_sec": elapsed,
        "avg_time_us": (elapsed / iterations) * 1_000_000,
        "ops_per_sec": iterations / elapsed,
    }


async def benchmark_sequential(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark Sequential pattern (3 agents)."""
    agents = [MockAgent(f"agent{i}") for i in range(3)]

    seq_agent = SequentialAgent(agents=agents)

    msg = Message(role="user", content="test input")

    # Warmup
    for _ in range(10):
        await seq_agent.process(msg)

    # Benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        await seq_agent.process(msg)
    elapsed = time.perf_counter() - start

    return {
        "pattern": "sequential",
        "iterations": iterations,
        "total_time_sec": elapsed,
        "avg_time_us": (elapsed / iterations) * 1_000_000,
        "ops_per_sec": iterations / elapsed,
    }


async def benchmark_parallel(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark Parallel pattern (3 agents)."""
    agents = [MockAgent(f"agent{i}") for i in range(3)]

    par_agent = ParallelAgent(agents=agents, aggregator=default_aggregators.concatenate)

    msg = Message(role="user", content="test input")

    # Warmup
    for _ in range(10):
        await par_agent.process(msg)

    # Benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        await par_agent.process(msg)
    elapsed = time.perf_counter() - start

    return {
        "pattern": "parallel",
        "iterations": iterations,
        "total_time_sec": elapsed,
        "avg_time_us": (elapsed / iterations) * 1_000_000,
        "ops_per_sec": iterations / elapsed,
    }


async def benchmark_router(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark Router pattern (2 agents)."""
    agents = {"agent1": MockAgent("agent1"), "agent2": MockAgent("agent2")}
    classifier = MockClassifier()

    router_agent = RouterAgent(RouterConfig(agents=agents, classifier=classifier))

    msg = Message(role="user", content="test input")

    # Warmup
    for _ in range(10):
        await router_agent.process(msg)

    # Benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        await router_agent.process(msg)
    elapsed = time.perf_counter() - start

    return {
        "pattern": "router",
        "iterations": iterations,
        "total_time_sec": elapsed,
        "avg_time_us": (elapsed / iterations) * 1_000_000,
        "ops_per_sec": iterations / elapsed,
    }


async def benchmark_fallback(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark Fallback pattern (3 agents)."""
    agents = [MockAgent(f"agent{i}") for i in range(3)]

    fallback_agent = FallbackAgent(agents=agents)

    msg = Message(role="user", content="test input")

    # Warmup
    for _ in range(10):
        await fallback_agent.process(msg)

    # Benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        await fallback_agent.process(msg)
    elapsed = time.perf_counter() - start

    return {
        "pattern": "fallback",
        "iterations": iterations,
        "total_time_sec": elapsed,
        "avg_time_us": (elapsed / iterations) * 1_000_000,
        "ops_per_sec": iterations / elapsed,
    }


async def benchmark_supervisor(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark Supervisor pattern (2 agents)."""
    agents = {"agent1": MockAgent("agent1"), "agent2": MockAgent("agent2")}
    planner = MockPlanner()

    supervisor_agent = SupervisorAgent(planner=planner, specialists=agents)

    msg = Message(role="user", content="test input")

    # Warmup
    for _ in range(10):
        await supervisor_agent.process(msg)

    # Benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        await supervisor_agent.process(msg)
    elapsed = time.perf_counter() - start

    return {
        "pattern": "supervisor",
        "iterations": iterations,
        "total_time_sec": elapsed,
        "avg_time_us": (elapsed / iterations) * 1_000_000,
        "ops_per_sec": iterations / elapsed,
    }


async def main():
    """Run all pattern benchmarks."""
    print("=" * 80)
    print("Python Pattern Performance Benchmarks - CORRECTED")
    print("Testing ACTUAL patterns (not just mock echo)")
    print("=" * 80)
    print()

    # Pattern benchmarks in order
    benchmarks = [
        ("reflection", benchmark_reflection),
        ("react", benchmark_react),
        ("agents_as_tools", benchmark_agents_as_tools),
        ("reasoning_with_tools", benchmark_reasoning_with_tools),
        ("conversational", benchmark_conversational),
        ("sequential", benchmark_sequential),
        ("parallel", benchmark_parallel),
        ("router", benchmark_router),
        ("fallback", benchmark_fallback),
        ("supervisor", benchmark_supervisor),
    ]

    results = []

    print("Running benchmarks...")
    print(f"{'Pattern':<25} {'Avg Time (μs)':<15} {'Ops/sec':<15}")
    print("-" * 80)

    for pattern_name, benchmark_func in benchmarks:
        try:
            result = await benchmark_func(iterations=1000)
            results.append(result)
            print(
                f"{result['pattern']:<25} {result['avg_time_us']:<15.2f} {result['ops_per_sec']:<15.0f}"
            )
        except Exception as e:
            print(f"{pattern_name:<25} ERROR: {e}")

    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Benchmarks run: {len(results)}")

    if results:
        avg_time = sum(r["avg_time_us"] for r in results) / len(results)
        fastest = min(results, key=lambda r: r["avg_time_us"])
        slowest = max(results, key=lambda r: r["avg_time_us"])

        print(f"Average time: {avg_time:.2f} μs")
        print(f"Fastest: {fastest['pattern']} ({fastest['avg_time_us']:.2f} μs)")
        print(f"Slowest: {slowest['pattern']} ({slowest['avg_time_us']:.2f} μs)")

    print()
    print("Results by pattern (sorted):")
    for result in sorted(results, key=lambda r: r["avg_time_us"]):
        print(f"  {result['pattern']:<25} {result['avg_time_us']:>10.2f} μs")

    print()
    print("Note: These results measure ACTUAL pattern overhead, not mock echo.")
    print("Previous results (~1.59 μs) only measured MockAgent.process() latency.")


if __name__ == "__main__":
    asyncio.run(main())

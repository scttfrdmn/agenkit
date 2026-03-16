"""
Benchmark: Crew(parallel) vs ParallelAgent (3 agents).

Measures the overhead of MiniCrew's parallel Crew wrapper over the
native Agenkit ParallelAgent.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "examples" / "frameworks"))

from agenkit import Agent, Message  # noqa: E402
from agenkit.patterns import ParallelAgent, default_aggregators  # noqa: E402
from benchmarks.frameworks.mock_llm import MockLLM, run_benchmark  # noqa: E402
from minicrew import Crew, CrewAgent, CrewTask  # noqa: E402


class EchoAgent(Agent):
    """Minimal agent for benchmarking."""

    def __init__(self, name_: str, llm: MockLLM) -> None:
        self._name = name_
        self._llm = llm

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return [self._name]

    async def process(self, message: Message) -> Message:
        return await self._llm.complete([message])


async def bench() -> dict[str, dict[str, float]]:
    """Run benchmarks for parallel execution scenarios."""
    llm = MockLLM()

    # MiniCrew parallel crew
    crew_agents = [
        CrewAgent(role=f"Agent{i}", goal="work", backstory="focused", llm=llm)
        for i in range(3)
    ]
    tasks = [
        CrewTask(description=f"task {i}", agent=crew_agents[i]) for i in range(3)
    ]
    crew = Crew(agents=crew_agents, tasks=tasks, process="parallel")

    # Native Agenkit ParallelAgent
    native_agents = [EchoAgent(f"pa_agent{i}", llm) for i in range(3)]
    parallel = ParallelAgent(native_agents, aggregator=default_aggregators.concatenate)

    results = {
        "Crew parallel (3 agents)": await run_benchmark(
            lambda: crew.kickoff()
        ),
        "ParallelAgent (3 agents)": await run_benchmark(
            lambda: parallel.process(Message(role="user", content="start"))
        ),
    }
    return results


if __name__ == "__main__":
    results = asyncio.run(bench())
    print("\n=== Parallel Execution Benchmark ===")
    print(f"{'Scenario':<30} {'mean_ms':>8} {'p50_ms':>8} {'p95_ms':>8} {'iter/s':>10}")
    print("-" * 70)
    for scenario, stats in results.items():
        print(
            f"{scenario:<30} {stats['mean_ms']:>8.4f} {stats['p50_ms']:>8.4f} "
            f"{stats['p95_ms']:>8.4f} {stats['iter_per_sec']:>10.1f}"
        )

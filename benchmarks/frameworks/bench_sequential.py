"""
Benchmark: SequentialChain vs SequentialAgent (3 agents).

Measures the overhead of MiniChain's SequentialChain wrapper over the
native Agenkit SequentialAgent.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "examples" / "frameworks"))

from agenkit import Agent, Message  # noqa: E402
from agenkit.patterns import SequentialAgent  # noqa: E402
from benchmarks.frameworks.mock_llm import MockLLM, run_benchmark  # noqa: E402
from minichain import SequentialChain  # noqa: E402


class PassThroughAgent(Agent):
    """Agent that echoes its input (minimal overhead)."""

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
    """Run benchmarks for sequential pipeline scenarios."""
    llm = MockLLM()
    agents = [PassThroughAgent(f"step{i}", llm) for i in range(3)]

    minichain_agents = [PassThroughAgent(f"mc_step{i}", llm) for i in range(3)]
    chain = SequentialChain(agents=minichain_agents)

    native_agents = [PassThroughAgent(f"na_step{i}", llm) for i in range(3)]
    native_seq = SequentialAgent(native_agents)

    results = {
        "SequentialChain (3 agents)": await run_benchmark(
            lambda: chain.run("start input")
        ),
        "SequentialAgent (3 agents)": await run_benchmark(
            lambda: native_seq.process(Message(role="user", content="start input"))
        ),
    }
    return results


if __name__ == "__main__":
    results = asyncio.run(bench())
    print("\n=== Sequential Pipeline Benchmark ===")
    print(f"{'Scenario':<30} {'mean_ms':>8} {'p50_ms':>8} {'p95_ms':>8} {'iter/s':>10}")
    print("-" * 70)
    for scenario, stats in results.items():
        print(
            f"{scenario:<30} {stats['mean_ms']:>8.4f} {stats['p50_ms']:>8.4f} "
            f"{stats['p95_ms']:>8.4f} {stats['iter_per_sec']:>10.1f}"
        )

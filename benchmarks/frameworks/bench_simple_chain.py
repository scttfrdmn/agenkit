"""
Benchmark: LLMChain.run vs direct LLM call vs Agent.process.

Measures the overhead introduced by the LLMChain abstraction.
"""

import asyncio
import sys
from pathlib import Path

# Inject examples/frameworks/ into path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "examples" / "frameworks"))

from agenkit import Agent, Message  # noqa: E402
from benchmarks.frameworks.mock_llm import MockLLM, run_benchmark  # noqa: E402
from minichain import LLMChain  # noqa: E402


class DirectAgent(Agent):
    """Minimal agent that calls LLM directly."""

    def __init__(self, llm: MockLLM) -> None:
        self._llm = llm

    @property
    def name(self) -> str:
        return "direct_agent"

    @property
    def capabilities(self) -> list[str]:
        return ["direct"]

    async def process(self, message: Message) -> Message:
        return await self._llm.complete([message])


async def bench() -> dict[str, dict[str, float]]:
    """Run benchmarks for simple chain scenarios."""
    llm = MockLLM()
    chain = LLMChain(llm=llm, prompt="Answer: {question}")
    agent = DirectAgent(llm)
    msg = Message(role="user", content="test question")

    results = {
        "LLMChain.run": await run_benchmark(
            lambda: chain.run(question="what is AI?")
        ),
        "direct_llm_complete": await run_benchmark(
            lambda: llm.complete([msg])
        ),
        "agent_process": await run_benchmark(
            lambda: agent.process(msg)
        ),
    }
    return results


if __name__ == "__main__":
    results = asyncio.run(bench())
    print("\n=== Simple Chain Benchmark ===")
    print(f"{'Scenario':<25} {'mean_ms':>8} {'p50_ms':>8} {'p95_ms':>8} {'iter/s':>10}")
    print("-" * 65)
    for scenario, stats in results.items():
        print(
            f"{scenario:<25} {stats['mean_ms']:>8.4f} {stats['p50_ms']:>8.4f} "
            f"{stats['p95_ms']:>8.4f} {stats['iter_per_sec']:>10.1f}"
        )

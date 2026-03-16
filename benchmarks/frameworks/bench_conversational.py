"""
Benchmark: ConversationChain vs ConversationalAgent (10 turns).

Measures the overhead of MiniChain's ConversationChain wrapper over the
native Agenkit ConversationalAgent.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "examples" / "frameworks"))

from agenkit import Message  # noqa: E402
from agenkit.patterns import ConversationalAgent, ConversationalAgentConfig  # noqa: E402
from benchmarks.frameworks.mock_llm import MockLLM, run_benchmark  # noqa: E402
from minichain import ConversationChain  # noqa: E402

TURNS = 10


async def run_minichain_conversation(chain: ConversationChain) -> None:
    """Run one complete 10-turn conversation and reset."""
    chain.clear_history()
    for i in range(TURNS):
        await chain.run(f"message {i}")


async def run_native_conversation(llm: MockLLM) -> None:
    """Run one complete 10-turn native conversation."""

    class LLMClientAdapter:
        def __init__(self, llm_instance: MockLLM) -> None:
            self.llm_instance = llm_instance

        async def chat(self, messages: list[Message]) -> Message:
            return await self.llm_instance.complete(messages)

    config = ConversationalAgentConfig(llm_client=LLMClientAdapter(llm), max_history=10)
    agent = ConversationalAgent(config)
    for i in range(TURNS):
        await agent.process(Message(role="user", content=f"message {i}"))


async def bench() -> dict[str, dict[str, float]]:
    """Run benchmarks for 10-turn conversation scenarios."""
    llm = MockLLM()
    chain = ConversationChain(llm=llm, max_history=10)

    results = {
        "ConversationChain (10 turns)": await run_benchmark(
            lambda: run_minichain_conversation(chain),
            iterations=50,
            warmup=5,
        ),
        "ConversationalAgent (10 turns)": await run_benchmark(
            lambda: run_native_conversation(llm),
            iterations=50,
            warmup=5,
        ),
    }
    return results


if __name__ == "__main__":
    results = asyncio.run(bench())
    print("\n=== Conversational Benchmark (10 turns) ===")
    print(f"{'Scenario':<35} {'mean_ms':>8} {'p50_ms':>8} {'p95_ms':>8} {'iter/s':>10}")
    print("-" * 75)
    for scenario, stats in results.items():
        print(
            f"{scenario:<35} {stats['mean_ms']:>8.4f} {stats['p50_ms']:>8.4f} "
            f"{stats['p95_ms']:>8.4f} {stats['iter_per_sec']:>10.1f}"
        )

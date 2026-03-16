"""
Benchmark: RouterChain vs RouterAgent (100 requests).

Measures the overhead of MiniChain's RouterChain wrapper over the
native Agenkit RouterAgent.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "examples" / "frameworks"))

from agenkit import Agent, Message  # noqa: E402
from agenkit.patterns import RouterAgent, RouterConfig, SimpleClassifier  # noqa: E402
from benchmarks.frameworks.mock_llm import MockLLM, run_benchmark  # noqa: E402
from minichain import RouterChain  # noqa: E402

# Reuse minichain's RouterChain and import MockClassifier from frameworks fixtures
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests"))
from frameworks.fixtures.mock_providers import MockAgent, MockClassifier  # noqa: E402


async def bench() -> dict[str, dict[str, float]]:
    """Run benchmarks for routing scenarios."""
    llm = MockLLM()

    # MiniChain RouterChain
    classifier = MockClassifier(
        rules={
            "billing": ["payment", "invoice"],
            "technical": ["error", "bug"],
        },
        default_category="general",
    )
    routes = {
        "billing": MockAgent("billing", "billing response"),
        "technical": MockAgent("technical", "tech response"),
        "general": MockAgent("general", "general response"),
    }
    chain = RouterChain(
        classifier=classifier,
        routes=routes,
        default_route="general",
    )

    # Native Agenkit RouterAgent using SimpleClassifier
    class NativeEchoAgent(Agent):
        def __init__(self, name_: str) -> None:
            self._name = name_

        @property
        def name(self) -> str:
            return self._name

        @property
        def capabilities(self) -> list[str]:
            return [self._name]

        async def process(self, message: Message) -> Message:
            return Message(role="agent", content=f"{self._name} response")

    native_classifier = SimpleClassifier(
        agent=NativeEchoAgent("classifier"),
        keywords={
            "billing": ["payment", "invoice"],
            "technical": ["error", "bug"],
        },
    )
    native_config = RouterConfig(
        classifier=native_classifier,
        agents={
            "billing": NativeEchoAgent("billing"),
            "technical": NativeEchoAgent("technical"),
        },
        default_key=None,
    )
    native_router = RouterAgent(native_config)

    results = {
        "RouterChain": await run_benchmark(
            lambda: chain.run("I have a payment question")
        ),
        "RouterAgent": await run_benchmark(
            lambda: native_router.process(Message(role="user", content="I have a payment question"))
        ),
    }
    return results


if __name__ == "__main__":
    results = asyncio.run(bench())
    print("\n=== Router Benchmark ===")
    print(f"{'Scenario':<20} {'mean_ms':>8} {'p50_ms':>8} {'p95_ms':>8} {'iter/s':>10}")
    print("-" * 60)
    for scenario, stats in results.items():
        print(
            f"{scenario:<20} {stats['mean_ms']:>8.4f} {stats['p50_ms']:>8.4f} "
            f"{stats['p95_ms']:>8.4f} {stats['iter_per_sec']:>10.1f}"
        )

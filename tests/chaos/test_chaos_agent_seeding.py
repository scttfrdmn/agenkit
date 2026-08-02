"""
Tests for ChaosAgent RNG seeding (#787).

The chaos agents used to draw from the `random` module globals, which
pytest-randomly reseeds per run. A chaos test that failed therefore could not be
reproduced from its output — the failure that prompted #787 had to be diagnosed
by simulation because re-running it could not reproduce it.

These tests cover the `seed` parameter itself: without them it is an affordance
nothing exercises, which is the same class of problem as the untested doc
examples in #778.
"""

import random

import pytest

from agenkit.interfaces import Agent, Message
from tests.chaos.chaos_agents import ChaosAgent, ChaosMode, OverloadedAgent


class _EchoAgent(Agent):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def capabilities(self) -> list[str]:
        return ["test"]

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Processed: {message.content}")


async def _count_successes(agent: Agent, n: int = 40) -> int:
    message = Message(role="user", content="Test")
    successes = 0
    for _ in range(n):
        try:
            await agent.process(message)
            successes += 1
        except Exception:
            pass  # Counting injected failures is the point of these helpers.
    return successes


def _seeded(seed: int | None) -> ChaosAgent:
    return ChaosAgent(_EchoAgent(), chaos_mode=ChaosMode.INTERMITTENT, failure_rate=0.5, seed=seed)


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_same_seed_gives_same_failures():
    """Two agents with the same seed must fail on exactly the same requests."""
    assert await _count_successes(_seeded(7)) == await _count_successes(_seeded(7))


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_seeding_is_immune_to_global_rng_state():
    """
    The point of an instance RNG rather than the module globals.

    A seeded agent must produce the same sequence no matter what else has touched
    `random` — which is what makes a seed printed in a failure message actually
    reproduce that failure under pytest-randomly.
    """
    random.seed(1)
    first = await _count_successes(_seeded(99))

    random.seed(424242)
    for _ in range(17):  # advance the global stream
        random.random()
    second = await _count_successes(_seeded(99))

    assert first == second


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_different_seeds_diverge():
    """
    Guards against the seed being pinned to a constant.

    The two tests above only require *equality*, so they are both satisfied by
    `random.Random(0)` — an implementation that ignores the caller's seed
    entirely. Divergence is what proves the argument reaches the RNG.

    Verified by reverting: `random.Random(0)` fails this test and
    test_unseeded_agents_still_vary while the equality tests above still pass;
    `random.Random()` (no seed) fails those two instead. The four together pin
    the behaviour from both sides.
    """
    results = {await _count_successes(_seeded(s)) for s in (1, 2, 3, 4, 5, 6, 7, 8)}
    assert len(results) > 1, f"every seed produced {results.pop()} successes; seed is ignored"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_unseeded_agents_still_vary():
    """seed=None must stay genuinely arbitrary rather than collapsing to a fixed stream."""
    results = {await _count_successes(_seeded(None)) for _ in range(12)}
    assert len(results) > 1, "unseeded agents produced identical results; seed=None is not random"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_overloaded_agent_is_seedable():
    """OverloadedAgent draws from the same RNG and takes the same parameter."""
    same = [
        await _count_successes(
            OverloadedAgent(_EchoAgent(), overload_threshold=5, overload_failure_rate=0.5, seed=3)
        )
        for _ in range(2)
    ]
    assert same[0] == same[1]

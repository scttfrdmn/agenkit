"""
End-to-end tests that per-call temperature reaches the LLM (#801).

`SelfConsistency` accepted a `temperature` in six of the nine cores and applied it
in none. Python's carried a literal `# TODO: If temperature supported, pass it to
agent`. The technique works by sampling the same prompt N times and taking a
majority vote, so sample diversity is not a nicety — it is the mechanism. A
`temperature` that silently does nothing makes the technique quietly weaker while
the API claims otherwise.

These tests assert against the value the **LLM** received, not against anything the
wrapper recorded on its way past. A test that only checks the wrapper's own state
would pass even if the plumbing stopped one layer short, which is exactly the bug.
"""

import pytest

from agenkit import Agent, CallOptions, Message
from agenkit.techniques.reasoning import (
    ChainOfThought,
    GraphOfThought,
    LeastToMost,
    PlanAndSolve,
    SelfConsistency,
    TreeOfThought,
)

from .conftest import ContractLLM


class TemperatureRecordingLLM(ContractLLM):
    """Records the temperature each call arrives with, or None if absent."""

    def __init__(self) -> None:
        super().__init__()
        self.temperatures: list[float | None] = []

    async def complete(self, messages, **kwargs):  # type: ignore[no-untyped-def]
        self.temperatures.append(kwargs.get("temperature"))
        return await super().complete(messages, **kwargs)

    def respond(self, prompt: str) -> str:
        return "1. First step\n2. Second step\nTherefore, the answer is 42"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "make_technique",
    [
        pytest.param(lambda llm: ChainOfThought(llm=llm), id="chain_of_thought"),
        pytest.param(
            lambda llm: TreeOfThought(llm=llm, branching_factor=2, max_depth=1),
            id="tree_of_thought",
        ),
        pytest.param(lambda llm: PlanAndSolve(llm=llm), id="plan_and_solve"),
        pytest.param(lambda llm: LeastToMost(llm=llm), id="least_to_most"),
        pytest.param(lambda llm: GraphOfThought(llm=llm, max_nodes=3), id="graph_of_thought"),
    ],
)
async def test_technique_forwards_temperature_to_llm(make_technique):
    """
    Every technique must forward per-call options to the LLM.

    Asserted on *every* call rather than just the first: these techniques make
    several LLM calls per invocation through different internal paths (planning vs
    execution, premises vs conclusion), and threading options through only some of
    them would make the feature silently partial.
    """
    llm = TemperatureRecordingLLM()
    technique = make_technique(llm)

    await technique.process_with(
        Message(role="user", content="What is 15 * 24?"), CallOptions(temperature=0.9)
    )

    assert llm.temperatures, "technique never called the LLM"
    assert all(t == 0.9 for t in llm.temperatures), (
        f"expected every call at 0.9, got {llm.temperatures} — "
        "an internal call path is not threading options (#801)"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "make_technique",
    [
        pytest.param(lambda llm: ChainOfThought(llm=llm), id="chain_of_thought"),
        pytest.param(lambda llm: PlanAndSolve(llm=llm), id="plan_and_solve"),
        pytest.param(lambda llm: LeastToMost(llm=llm), id="least_to_most"),
    ],
)
async def test_process_sends_no_temperature(make_technique):
    """
    Plain process() must not send a temperature at all.

    Not "must send the default" — must not send the key. Otherwise every existing
    caller would start overriding whatever the LLM was configured with, which is
    the same class of silent-wrong bug in the opposite direction.
    """
    llm = TemperatureRecordingLLM()
    technique = make_technique(llm)

    await technique.process(Message(role="user", content="Q"))

    assert llm.temperatures
    assert all(t is None for t in llm.temperatures), (
        f"process() leaked a temperature: {llm.temperatures}"
    )


@pytest.mark.asyncio
async def test_zero_temperature_is_forwarded_not_treated_as_unset():
    """temperature=0.0 is greedy decoding, a real request — not an absence."""
    llm = TemperatureRecordingLLM()
    cot = ChainOfThought(llm=llm)

    await cot.process_with(Message(role="user", content="Q"), CallOptions(temperature=0.0))

    assert llm.temperatures == [0.0]


@pytest.mark.asyncio
async def test_all_techniques_advertise_the_capability():
    """
    Each technique must report supports_options, or wrappers will skip it.

    `SelfConsistency` checks this to decide whether to use the options path, so a
    technique that plumbed options but forgot to override `process_with` would be
    called through `process()` and never receive them.
    """
    llm = TemperatureRecordingLLM()
    for technique in (
        ChainOfThought(llm=llm),
        TreeOfThought(llm=llm),
        PlanAndSolve(llm=llm),
        LeastToMost(llm=llm),
        GraphOfThought(llm=llm),
    ):
        assert technique.supports_options is True, f"{technique.name} does not advertise options"


class TestSelfConsistencyTemperature:
    """The wrapper case this issue was filed about."""

    @pytest.mark.asyncio
    async def test_temperature_reaches_the_llm_through_the_wrapper(self):
        """
        The end-to-end assertion: SelfConsistency -> CoT -> LLM.

        This is the one that was impossible before. SelfConsistency wraps an
        arbitrary Agent, so it had no way to reach the LLM two layers down.
        """
        llm = TemperatureRecordingLLM()
        sc = SelfConsistency(agent=ChainOfThought(llm=llm), num_samples=3, temperature=0.8)

        await sc.process(Message(role="user", content="What is 15 * 24?"))

        assert len(llm.temperatures) == 3, f"expected 3 samples, got {len(llm.temperatures)}"
        assert all(t == 0.8 for t in llm.temperatures), llm.temperatures

    @pytest.mark.asyncio
    async def test_no_temperature_sends_none(self):
        """Without a temperature, behaviour must be unchanged from before #801."""
        llm = TemperatureRecordingLLM()
        sc = SelfConsistency(agent=ChainOfThought(llm=llm), num_samples=2)

        await sc.process(Message(role="user", content="Q"))

        assert llm.temperatures == [None, None]

    @pytest.mark.asyncio
    async def test_wrapping_a_capability_less_agent_still_works(self):
        """
        The compatibility guarantee for the optional-capability design.

        An agent that never heard of CallOptions must keep working when wrapped,
        temperature or not. This is what makes the change additive rather than a
        breaking protocol change across ~500 implementations.
        """

        class LegacyAgent(Agent):
            def __init__(self):
                self.calls = 0

            @property
            def name(self) -> str:
                return "legacy"

            async def process(self, message: Message) -> Message:
                self.calls += 1
                return Message(role="agent", content="Therefore, the answer is 42")

        agent = LegacyAgent()
        sc = SelfConsistency(agent=agent, num_samples=3, temperature=0.8)

        response = await sc.process(Message(role="user", content="Q"))

        assert agent.calls == 3
        assert "42" in response.content

    @pytest.mark.asyncio
    async def test_temperature_applied_reports_false_for_legacy_agent(self):
        """
        A dropped temperature must be *visible*, not silent.

        The whole complaint in #801 is that the value was accepted and ignored with
        no way to tell. The optional-capability design reintroduces that risk for
        agents lacking the capability, so it has to be reportable.
        """

        class LegacyAgent(Agent):
            @property
            def name(self) -> str:
                return "legacy"

            async def process(self, message: Message) -> Message:
                return Message(role="agent", content="Therefore, 42")

        sc = SelfConsistency(agent=LegacyAgent(), num_samples=2, temperature=0.8)
        assert sc.temperature_applied is False

        response = await sc.process(Message(role="user", content="Q"))
        assert response.metadata["temperature_applied"] is False
        assert response.metadata["temperature"] == 0.8

    @pytest.mark.asyncio
    async def test_temperature_applied_true_for_capable_agent(self):
        llm = TemperatureRecordingLLM()
        sc = SelfConsistency(agent=ChainOfThought(llm=llm), num_samples=2, temperature=0.8)

        assert sc.temperature_applied is True

        response = await sc.process(Message(role="user", content="Q"))
        assert response.metadata["temperature_applied"] is True

    @pytest.mark.asyncio
    async def test_temperature_applied_true_when_unset(self):
        """Nothing to apply means nothing is being dropped."""

        class LegacyAgent(Agent):
            @property
            def name(self) -> str:
                return "legacy"

            async def process(self, message: Message) -> Message:
                return Message(role="agent", content="Therefore, 42")

        assert SelfConsistency(agent=LegacyAgent(), num_samples=2).temperature_applied is True

    def test_invalid_temperature_rejected_at_construction(self):
        """
        Fail at construction, not on the first sample.

        Bounds live in CallOptions so SelfConsistency and the LLM layer cannot
        disagree about what a valid temperature is.
        """

        class LegacyAgent(Agent):
            @property
            def name(self) -> str:
                return "legacy"

            async def process(self, message: Message) -> Message:
                return Message(role="agent", content="x")

        with pytest.raises(ValueError, match="temperature must be between 0 and 2"):
            SelfConsistency(agent=LegacyAgent(), temperature=5.0)

    @pytest.mark.asyncio
    async def test_concurrent_samples_do_not_share_mutable_option_state(self):
        """
        Options are passed as an argument, never stashed on the agent.

        Samples run concurrently through asyncio.gather on the *same* agent
        instance. Had the temperature been written to a field before each call, the
        samples would race and some would run at another sample's temperature —
        wrong, and invisible.
        """
        llm = TemperatureRecordingLLM()
        cot = ChainOfThought(llm=llm)
        sc = SelfConsistency(agent=cot, num_samples=8, temperature=1.5)

        await sc.process(Message(role="user", content="Q"))

        assert len(llm.temperatures) == 8
        assert set(llm.temperatures) == {1.5}, llm.temperatures

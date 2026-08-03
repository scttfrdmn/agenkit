"""
Tests for CallOptions and the optional Agent.process_with capability (#801).

`CallOptions` is the per-call channel a wrapper uses to influence how one
invocation runs. It exists because `SelfConsistency` samples the same prompt N
times and votes — sample diversity *is* the technique — but it wraps an arbitrary
`Agent` and so had no way to reach the LLM underneath. Its `temperature` was
accepted and dropped for as long as the class existed.

The capability is optional by design: `process_with` defaults to ignoring options
and delegating to `process()`, so the ~500 existing implementations across the nine
cores keep working untouched. The cost of that choice is that a successful return
does not prove the options were applied, which is why `supports_options` exists and
is tested here.
"""

from dataclasses import FrozenInstanceError

import pytest

from agenkit import Agent, CallOptions, Message


class TestCallOptionsValidation:
    """Options are validated at construction, where the mistake is."""

    def test_empty_by_default(self):
        assert CallOptions().is_empty()

    def test_not_empty_when_set(self):
        assert not CallOptions(temperature=0.5).is_empty()

    def test_extra_alone_counts_as_non_empty(self):
        assert not CallOptions(extra={"custom": 1}).is_empty()

    @pytest.mark.parametrize("value", [0.0, 1.0, 2.0])
    def test_temperature_bounds_accepted(self, value):
        assert CallOptions(temperature=value).temperature == value

    @pytest.mark.parametrize("value", [-0.1, 2.1, 100.0])
    def test_temperature_out_of_range_rejected(self, value):
        with pytest.raises(ValueError, match="temperature must be between 0 and 2"):
            CallOptions(temperature=value)

    def test_temperature_wrong_type_rejected(self):
        with pytest.raises(ValueError, match="temperature must be a number"):
            CallOptions(temperature="hot")

    def test_temperature_bool_rejected(self):
        """`True` is an int in Python; accepting it would send temperature=1."""
        with pytest.raises(ValueError, match="temperature must be a number"):
            CallOptions(temperature=True)

    def test_max_tokens_must_be_positive(self):
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            CallOptions(max_tokens=0)

    def test_max_tokens_wrong_type_rejected(self):
        with pytest.raises(ValueError, match="max_tokens must be an integer"):
            CallOptions(max_tokens=1.5)

    def test_top_p_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="top_p must be between 0 and 1"):
            CallOptions(top_p=1.5)

    def test_seed_wrong_type_rejected(self):
        with pytest.raises(ValueError, match="seed must be an integer"):
            CallOptions(seed="abc")

    def test_frozen(self):
        """Immutable so a shared options object can't be mutated mid-fan-out."""
        options = CallOptions(temperature=0.5)
        with pytest.raises(FrozenInstanceError):
            options.temperature = 0.9  # type: ignore[misc]


class TestToKwargs:
    """Unset options must be omitted, not passed as None."""

    def test_empty_produces_no_kwargs(self):
        assert CallOptions().to_kwargs() == {}

    def test_unset_fields_omitted(self):
        """
        The core invariant: None means "caller didn't ask", not "use 0/null".

        If unset fields were forwarded, every call through a wrapper would override
        whatever the agent or provider was configured with — the same silent-wrong
        failure this issue is about, just relocated.
        """
        kwargs = CallOptions(temperature=0.7).to_kwargs()
        assert kwargs == {"temperature": 0.7}
        assert "max_tokens" not in kwargs
        assert "top_p" not in kwargs

    def test_zero_temperature_is_forwarded(self):
        """0.0 is a real, meaningful value — greedy decoding — not an absence."""
        assert CallOptions(temperature=0.0).to_kwargs() == {"temperature": 0.0}

    def test_all_fields(self):
        kwargs = CallOptions(
            temperature=0.7, max_tokens=100, top_p=0.9, seed=42, stop=("END",)
        ).to_kwargs()
        assert kwargs == {
            "temperature": 0.7,
            "max_tokens": 100,
            "top_p": 0.9,
            "seed": 42,
            "stop": ["END"],
        }

    def test_extra_merged(self):
        kwargs = CallOptions(temperature=0.5, extra={"provider_flag": True}).to_kwargs()
        assert kwargs == {"temperature": 0.5, "provider_flag": True}


class PlainAgent(Agent):
    """Agent that does not implement the capability — the common case."""

    def __init__(self):
        self.calls = 0

    @property
    def name(self) -> str:
        return "plain"

    async def process(self, message: Message) -> Message:
        self.calls += 1
        return Message(role="agent", content="plain")


class TunableAgent(Agent):
    """Agent that implements the capability."""

    def __init__(self):
        self.received: list[CallOptions] = []

    @property
    def name(self) -> str:
        return "tunable"

    async def process(self, message: Message) -> Message:
        return await self.process_with(message, CallOptions())

    async def process_with(self, message: Message, options: CallOptions) -> Message:
        self.received.append(options)
        return Message(role="agent", content="tunable")


class TestProcessWithDefault:
    """The default must be additive: accept options, delegate, break nothing."""

    @pytest.mark.asyncio
    async def test_default_delegates_to_process(self):
        agent = PlainAgent()

        response = await agent.process_with(Message(role="user", content="Q"), CallOptions())

        assert response.content == "plain"
        assert agent.calls == 1

    @pytest.mark.asyncio
    async def test_default_ignores_options_without_error(self):
        """An agent that can't honour options must not fail when given them."""
        agent = PlainAgent()

        response = await agent.process_with(
            Message(role="user", content="Q"), CallOptions(temperature=0.9)
        )

        assert response.content == "plain"

    def test_supports_options_false_when_not_overridden(self):
        assert PlainAgent().supports_options is False

    def test_supports_options_true_when_overridden(self):
        assert TunableAgent().supports_options is True

    @pytest.mark.asyncio
    async def test_override_receives_options(self):
        agent = TunableAgent()

        await agent.process_with(Message(role="user", content="Q"), CallOptions(temperature=0.3))

        assert len(agent.received) == 1
        assert agent.received[0].temperature == 0.3

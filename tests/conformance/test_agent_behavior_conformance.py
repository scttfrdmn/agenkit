"""Layer B: behavioral, instance-level conformance for instantiable agents.

Runs against real instances built from ``registry.AGENT_CASES`` (a
zero-arg factory per class, following the factory-lambda idiom in
``tests/techniques/reasoning/test_temperature_plumbing.py``). Complements
Layer A's static checks with assertions that only make sense against a
live object: ``introspect()`` returning consistent data, ``stream()``
actually behaving like an async generator, etc.
"""

from __future__ import annotations

import inspect

import pytest

from agenkit.interfaces import Agent, IntrospectionResult, Message

from .registry import AGENT_CASES


@pytest.fixture(params=AGENT_CASES)
def agent(request) -> Agent:
    return request.param()


class TestAgentBehaviorConformance:
    def test_name_is_a_nonempty_string(self, agent: Agent):
        assert isinstance(agent.name, str)
        assert agent.name

    def test_capabilities_is_a_list_of_strings_not_a_bound_method(self, agent: Agent):
        caps = agent.capabilities
        # The second failure mode of the #904 bug shape: introspect() reads
        # self.capabilities un-called, so a method-shaped override would
        # silently put a bound method object where a list is expected.
        assert not callable(caps), (
            f"{type(agent).__name__}.capabilities returned a callable "
            f"({caps!r}) instead of a list -- likely defined as a method, "
            f"not a @property"
        )
        assert isinstance(caps, list)
        assert all(isinstance(c, str) for c in caps)

    @pytest.mark.asyncio
    async def test_process_returns_a_message(self, agent: Agent):
        response = await agent.process(Message(role="user", content="conformance probe"))
        assert isinstance(response, Message)

    def test_introspect_capabilities_matches_the_property(self, agent: Agent):
        result = agent.introspect()
        assert isinstance(result, IntrospectionResult)
        assert result.capabilities == agent.capabilities
        assert result.agent_name == agent.name

    def test_supports_options_matches_whether_process_with_is_overridden(self, agent: Agent):
        overridden = type(agent).process_with is not Agent.process_with
        assert agent.supports_options == overridden

    def test_unwrap_returns_something(self, agent: Agent):
        assert agent.unwrap() is not None

    @pytest.mark.asyncio
    async def test_stream_yields_messages_or_raises_not_implemented(self, agent: Agent):
        if not inspect.isasyncgenfunction(type(agent).stream):
            # Inherits the base Agent.stream, which raises by contract.
            with pytest.raises(NotImplementedError):
                async for _ in agent.stream(Message(role="user", content="probe")):
                    pass
            return

        try:
            async for chunk in agent.stream(Message(role="user", content="probe")):
                assert isinstance(chunk, Message)
        except NotImplementedError:
            pass  # An override may still choose to raise for this input shape.

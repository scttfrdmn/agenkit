"""Shared test double for the conformance suite.

``ContractAgent`` mirrors ``tests/techniques/reasoning/conftest.py``'s
``ContractLLM``: subclass the real base class rather than duck-typing it, so
a caller that misuses the contract fails the same way it would against a
real agent, not silently.
"""

from __future__ import annotations

from agenkit.interfaces import Agent, Message


class ContractAgent(Agent):
    """Minimal, contract-correct Agent double for tests that need a real
    instance rather than a class under test.

    Returns ``metadata={}`` by default, not ``metadata=None``. This is a
    deliberate choice, not an oversight: several patterns do
    ``if x.metadata is None: x.metadata = {}``, which raises
    ``FrozenInstanceError`` against a frozen ``Message`` (#919) -- a double
    that returned ``metadata=None`` would trip all of those sites at once
    and turn this suite into an unplanned 13-file behavioral refactor. See
    ``test_metadata_none_known_gap.py`` for the explicit,
    non-parametrized acknowledgment of that known gap.
    """

    def __init__(self, name: str = "contract-agent", response: str = "ok") -> None:
        self._name = name
        self._response = response

    @property
    def name(self) -> str:
        return self._name

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=self._response, metadata={})

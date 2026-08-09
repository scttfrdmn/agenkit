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

    Returns ``metadata={}`` explicitly, though this is no longer required
    for correctness: ``Message.__post_init__`` normalizes ``metadata=None``
    to ``{}`` at construction (#919 fix), so ``metadata`` is never
    observably ``None`` regardless of what a double returns. See
    ``test_metadata_none_known_gap.py`` for the regression test that
    covers the fixed behavior.
    """

    def __init__(self, name: str = "contract-agent", response: str = "ok") -> None:
        self._name = name
        self._response = response

    @property
    def name(self) -> str:
        return self._name

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=self._response, metadata={})

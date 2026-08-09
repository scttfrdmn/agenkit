"""Regression test for the #919 fix.

This test used to document a *known, deliberately-tripwired gap*:
``metadata=None`` reaching ``SequentialAgent`` raised ``FrozenInstanceError``
because downstream patterns did ``if x.metadata is None: x.metadata = {}``
against a frozen ``Message``. ``ContractAgent`` (conftest.py) worked around
it by never returning ``metadata=None``.

#919 fixed this at the source: ``Message.__post_init__`` now normalizes
``metadata=None`` to ``{}`` at construction time (see
``agenkit/interfaces.py``), so ``metadata`` is never observably ``None`` on
any ``Message`` instance, and all 13 downstream ``is None`` guards became
unreachable and were removed. This test now asserts the *fixed* behavior --
that the same path no longer raises -- so a future regression trips a red
test instead of silently reverting to the old failure mode.
"""

from __future__ import annotations

import asyncio

import pytest

from agenkit.interfaces import Agent, Message
from agenkit.patterns.sequential import SequentialAgent


class _ReturnsNoneMetadata(Agent):
    @property
    def name(self) -> str:
        return "returns-none-metadata"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content="x", metadata=None)


def test_metadata_none_no_longer_raises_frozen_instance_error():
    """Regression test for #919: metadata=None must not crash SequentialAgent.

    ``Message(metadata=None)`` is normalized to ``metadata={}`` at
    construction (agenkit/interfaces.py), so a child agent returning
    ``metadata=None`` no longer raises ``FrozenInstanceError`` when
    ``SequentialAgent`` (agenkit/patterns/sequential.py:136, one of the 13
    sites #919 tracked) writes pipeline metadata onto the result.
    """
    seq = SequentialAgent([_ReturnsNoneMetadata()])

    result = asyncio.run(seq.process(Message(role="user", content="probe")))

    assert result.metadata is not None
    assert result.metadata["pipeline_stages"]


@pytest.mark.parametrize(
    "ctor_metadata",
    [None, {}],
)
def test_message_metadata_is_never_none(ctor_metadata: dict | None) -> None:
    """Regression test for #919: Message.metadata is never observably None.

    Constructing with either ``metadata=None`` or omitting it entirely
    (default ``metadata={}``) must both yield a dict, never ``None``.
    """
    msg = Message(role="user", content="x", metadata=ctor_metadata)
    assert msg.metadata is not None
    assert msg.metadata == {}

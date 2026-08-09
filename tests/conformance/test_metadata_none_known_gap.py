"""One dedicated, non-parametrized acknowledgment of the #919 gap.

``ContractAgent`` (conftest.py) deliberately returns ``metadata={}``, not
``metadata=None`` -- see its docstring for why. This test makes the
trade-off explicit rather than silent: it proves the ``metadata=None`` path
*does* currently raise, so a future reader can't mistake the double's
choice for an oversight.
"""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError

import pytest

from agenkit.interfaces import Agent, Message
from agenkit.patterns.sequential import SequentialAgent


class _ReturnsNoneMetadata(Agent):
    @property
    def name(self) -> str:
        return "returns-none-metadata"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content="x", metadata=None)


def test_metadata_none_currently_raises_frozen_instance_error():
    """Documents the known #919 gap this suite's double deliberately avoids.

    A Message with metadata=None is a legal construction today (metadata
    has no validation), but every `if x.metadata is None: x.metadata = {}`
    site raises FrozenInstanceError the moment it fires -- proven here
    against agenkit.patterns.sequential.SequentialAgent:136, one of the 13
    sites #919 tracks.
    """
    seq = SequentialAgent([_ReturnsNoneMetadata()])

    with pytest.raises(FrozenInstanceError):
        asyncio.run(seq.process(Message(role="user", content="probe")))

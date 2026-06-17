"""
ReasoningMemory: a Memory that also persists reasoning artifacts.

Mirrors the Go ``ReasoningMemory`` interface (memory.Memory + StoreArtifact /
RetrieveArtifacts). Flat message storage destroys the structure of a reasoning
tree/graph/sample-set; this interface lets backends persist the structured
:class:`~agenkit.reasoning.artifact.ReasoningArtifact` alongside conversation
history so prior reasoning can be loaded and built on.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from ..interfaces import Message
from ..memory.base import Memory

if TYPE_CHECKING:
    from .artifact import ReasoningArtifact


class ReasoningMemory(Memory):
    """
    A :class:`~agenkit.memory.base.Memory` extended with artifact persistence.

    Implementations store and retrieve :class:`ReasoningArtifact` objects keyed
    by session, filterable by technique, in addition to the normal message
    store/retrieve contract.
    """

    @abstractmethod
    async def store_artifact(self, session_id: str, artifact: ReasoningArtifact) -> None:
        """Persist a reasoning artifact for ``session_id``."""
        raise NotImplementedError

    @abstractmethod
    async def retrieve_artifacts(
        self, session_id: str, technique: str | None = None
    ) -> list[ReasoningArtifact]:
        """
        Return artifacts for ``session_id``.

        Args:
            session_id: Session to read from.
            technique: If given, return only artifacts from that technique;
                otherwise return all artifacts for the session.

        Returns:
            Artifacts in insertion order (oldest first).
        """
        raise NotImplementedError


class InMemoryReasoningMemory(ReasoningMemory):
    """
    In-memory :class:`ReasoningMemory` for tests and single-process use.

    Messages and artifacts are kept in plain dicts keyed by session id. Not
    persistent and not thread/host shared — see RedisMemory/EndlessMemory for
    durable backends.
    """

    def __init__(self) -> None:
        self._messages: dict[str, list[Message]] = {}
        self._artifacts: dict[str, list[ReasoningArtifact]] = {}

    # --- Memory contract ---------------------------------------------------

    async def store(self, session_id: str, message: Message, metadata: dict | None = None) -> None:
        self._messages.setdefault(session_id, []).append(message)

    async def retrieve(
        self, session_id: str, query: str | None = None, limit: int = 10, **kwargs
    ) -> list[Message]:
        msgs = self._messages.get(session_id, [])
        # Most recent first, capped at limit (mirrors the other backends).
        return list(reversed(msgs))[:limit]

    async def summarize(self, session_id: str, **kwargs) -> Message:
        msgs = self._messages.get(session_id, [])
        if not msgs:
            return Message(role="system", content=f"No messages in session {session_id}.")
        return Message(
            role="system",
            content=f"Session {session_id}: {len(msgs)} messages.",
        )

    async def clear(self, session_id: str) -> None:
        self._messages.pop(session_id, None)
        self._artifacts.pop(session_id, None)

    # --- ReasoningMemory contract -----------------------------------------

    async def store_artifact(self, session_id: str, artifact: ReasoningArtifact) -> None:
        self._artifacts.setdefault(session_id, []).append(artifact)

    async def retrieve_artifacts(
        self, session_id: str, technique: str | None = None
    ) -> list[ReasoningArtifact]:
        artifacts = self._artifacts.get(session_id, [])
        if technique is None:
            return list(artifacts)
        return [a for a in artifacts if a.technique == technique]

    @property
    def capabilities(self) -> list[str]:
        return ["message_store", "reasoning_artifacts"]

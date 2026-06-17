"""
ReasoningArtifact: structured intermediate reasoning output.

All reasoning techniques ultimately return a final answer, but the structure
they computed along the way — the candidates explored and their scores — is
useful information that is otherwise discarded. A ``ReasoningArtifact`` captures
that structure so it can be persisted (see :mod:`agenkit.reasoning.memory`),
inspected, or resumed.

Mirrors the Go ``ReasoningArtifact`` interface and ``ScoredCandidate`` struct.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ScoredCandidate:
    """A candidate answer paired with its evaluation score."""

    text: str
    score: float = 0.0


@dataclass(frozen=True)
class ReasoningArtifact:
    """
    Structured intermediate reasoning output from a technique.

    Attributes:
        technique: Technique name, e.g. ``"tree_of_thought"``,
            ``"chain_of_thought"``, ``"self_consistency"``.
        session_id: Session this artifact belongs to.
        candidates: The scored candidates the technique explored.
        metadata: Arbitrary technique-specific metadata.
    """

    technique: str
    session_id: str
    candidates: list[ScoredCandidate] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def best_candidate(self) -> ScoredCandidate | None:
        """
        Return the highest-scoring candidate, or ``None`` if there are none.

        Mirrors the Go ``BestCandidate`` (which returns a zero value); here a
        missing best is represented as ``None`` per Python idiom.
        """
        if not self.candidates:
            return None
        return max(self.candidates, key=lambda c: c.score)

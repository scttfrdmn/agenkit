"""
Verifier: exact, binary checking of a candidate answer against ground truth.

Mirrors the Go ``Verifier`` interface and ``VerificationResult`` struct. Unlike
an evaluator heuristic (a float used to prune branches during search), a
verifier produces ground truth — for code generation the only honest verifier
is execution (``build && test``), which is binary, not approximate.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationResult:
    """
    Outcome of a :class:`Verifier` check.

    Attributes:
        passed: Whether the answer is considered correct.
        score: Confidence in [0.0, 1.0]; 1.0 = fully correct.
        reason: Human-readable explanation of the verdict.
    """

    passed: bool
    score: float = 0.0
    reason: str = ""


class Verifier(ABC):
    """
    Checks a candidate answer against ground truth.

    Exact and binary, in contrast to the heuristic float scores produced by an
    evaluator function. Implementations might run code, check a known answer,
    or call a stricter model.
    """

    @abstractmethod
    async def verify(self, question: str, answer: str) -> VerificationResult:
        """
        Verify ``answer`` for ``question``.

        Args:
            question: The original problem statement.
            answer: The candidate answer to check.

        Returns:
            A :class:`VerificationResult`.
        """
        raise NotImplementedError

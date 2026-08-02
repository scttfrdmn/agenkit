"""
Verifier: exact checking of a candidate answer against ground truth.

Mirrors the Go ``Verifier`` interface and ``VerificationResult`` struct. Unlike
an evaluator heuristic (a float used to prune branches during search), a
verifier produces ground truth — for code generation the only honest verifier
is execution (``build && test``), which is exact, not approximate.

A verdict has *three* states, not two. See :class:`Verdict`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum


class Verdict(StrEnum):
    """
    Outcome of a verification, as a three-state enum.

    ``NOT_ASSESSED`` is a genuine third state and must not be collapsed into
    ``FAILED``. "We did not check" and "we checked and it was wrong" support
    opposite decisions: the first says the answer might be fine and it is worth
    spending budget to verify, the second says the answer is wrong and to stop
    or retry differently. A boolean destroys that distinction at the point of
    creation, so no downstream consumer can recover it.

    A ``StrEnum``, so the members serialise as their wire values and compare
    equal to them — ``Verdict.PASSED == "passed"`` is ``True``, and ``str()``
    and f-strings render ``passed`` rather than ``Verdict.PASSED``. Those values
    are exactly the three specified for the ``agenkit.verifier.verdict`` span
    attribute in ``docs/OTEL_CONVENTION.md``, so a verdict can be recorded on a
    span without translation.
    """

    PASSED = "passed"
    """Verified and correct."""

    FAILED = "failed"
    """Verified and incorrect."""

    NOT_ASSESSED = "not_assessed"
    """No verification was attempted. Not the same as ``FAILED``."""


@dataclass(frozen=True)
class VerificationResult:
    """
    Outcome of a :class:`Verifier` check.

    Construct with either ``verdict`` or ``passed``; they are kept consistent
    automatically, so existing two-state callers need no change:

        >>> VerificationResult(passed=True).verdict
        <Verdict.PASSED: 'passed'>
        >>> VerificationResult(verdict=Verdict.FAILED).passed
        False
        >>> VerificationResult(verdict=Verdict.NOT_ASSESSED).passed
        False

    Note the last case: ``passed`` is ``False`` for a not-assessed result,
    because a caller asking a yes/no question about an unverified answer cannot
    be told "yes". Code that needs to distinguish the two must read ``verdict``
    — which is the whole point of it existing. ``if not result.passed`` treats
    not-assessed as failed, so prefer an explicit ``verdict`` comparison
    wherever the difference changes the decision.

    Attributes:
        verdict: The three-state outcome. Defaults to ``NOT_ASSESSED``, so a
            default-constructed result claims nothing rather than claiming
            failure.
        score: Confidence in [0.0, 1.0]; 1.0 = fully correct. Meaningless when
            the verdict is ``NOT_ASSESSED`` — note that ``0.0`` is both the
            default and a legitimate score, so it cannot be used to detect
            "unset". Read ``verdict`` for that.
        reason: Human-readable explanation of the verdict.
    """

    verdict: Verdict = Verdict.NOT_ASSESSED
    score: float = 0.0
    reason: str = ""
    passed: bool = field(default=False)

    def __init__(
        self,
        passed: bool | None = None,
        score: float = 0.0,
        reason: str = "",
        verdict: Verdict | str | None = None,
    ) -> None:
        """
        Build a result from ``verdict``, ``passed``, or neither.

        ``passed`` stays the first positional parameter so that existing
        ``VerificationResult(True, 0.9, "ok")`` call sites keep working.

        Args:
            passed: Two-state outcome. ``True`` → ``PASSED``, ``False`` →
                ``FAILED``. Omit to leave the verdict to ``verdict``.
            score: Confidence in [0.0, 1.0].
            reason: Human-readable explanation.
            verdict: Three-state outcome, including ``NOT_ASSESSED``. Takes
                precedence over ``passed``.

        Raises:
            ValueError: If ``verdict`` and ``passed`` are both given and
                disagree. Silently preferring one would make a contradictory
                call site look correct.
        """
        if verdict is not None:
            verdict = Verdict(verdict)
            if passed is not None and passed != (verdict is Verdict.PASSED):
                raise ValueError(
                    f"passed={passed} contradicts verdict={verdict.value!r}; "
                    f"pass only one, or make them agree"
                )
        elif passed is not None:
            verdict = Verdict.PASSED if passed else Verdict.FAILED
        else:
            verdict = Verdict.NOT_ASSESSED

        # frozen=True blocks normal attribute assignment.
        object.__setattr__(self, "verdict", verdict)
        object.__setattr__(self, "score", score)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "passed", verdict is Verdict.PASSED)

    @property
    def assessed(self) -> bool:
        """Whether verification was actually attempted."""
        return self.verdict is not Verdict.NOT_ASSESSED


class Verifier(ABC):
    """
    Checks a candidate answer against ground truth.

    Exact, in contrast to the heuristic float scores produced by an evaluator
    function. Implementations might run code, check a known answer, or call a
    stricter model.

    An implementation that cannot reach a conclusion — no ground truth
    available, the check itself was skipped — should return
    ``VerificationResult(verdict=Verdict.NOT_ASSESSED, reason=...)`` rather
    than ``passed=False``, which would assert the answer is wrong.
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

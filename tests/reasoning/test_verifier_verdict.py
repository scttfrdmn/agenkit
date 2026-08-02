"""
Tests for the three-state Verdict on VerificationResult (#769).

The distinction under test is that "not assessed" must survive construction as
something other than "failed". A boolean `passed` cannot carry it, so these
tests are mostly about what `verdict` preserves that `passed` throws away.
"""

from __future__ import annotations

import dataclasses

import pytest

from agenkit.reasoning import VerificationResult, Verifier
from agenkit.reasoning.verifier import Verdict

# ============================================
# The third state
# ============================================


def test_not_assessed_is_distinguishable_from_failed():
    """The whole point of #769: these two must not be the same value."""
    not_checked = VerificationResult(verdict=Verdict.NOT_ASSESSED, reason="no ground truth")
    checked_and_wrong = VerificationResult(passed=False, reason="wrong answer")

    # `passed` collapses them — which is why it cannot be the only signal.
    assert not_checked.passed is False
    assert checked_and_wrong.passed is False

    # `verdict` keeps them apart.
    assert not_checked.verdict is Verdict.NOT_ASSESSED
    assert checked_and_wrong.verdict is Verdict.FAILED
    assert not_checked.verdict != checked_and_wrong.verdict
    assert not_checked != checked_and_wrong


def test_default_result_asserts_nothing():
    """A default-constructed result must not claim the answer is wrong."""
    result = VerificationResult()

    assert result.verdict is Verdict.NOT_ASSESSED
    assert result.assessed is False
    # Not FAILED — that would be a claim nobody made.
    assert result.verdict is not Verdict.FAILED


def test_assessed_property():
    assert VerificationResult(passed=True).assessed is True
    assert VerificationResult(passed=False).assessed is True
    assert VerificationResult(verdict=Verdict.NOT_ASSESSED).assessed is False


def test_score_zero_does_not_imply_not_assessed():
    """
    0.0 is both the default score and a legitimate one, so it cannot be used to
    detect "unset". This is exactly the sentinel collision `verdict` replaces.
    """
    scored_zero = VerificationResult(passed=False, score=0.0, reason="scored zero")
    unassessed = VerificationResult()

    assert scored_zero.score == unassessed.score == 0.0
    # Identical scores, different verdicts. Read the verdict.
    assert scored_zero.verdict is not unassessed.verdict


# ============================================
# Backwards compatibility with the two-state API
# ============================================


def test_legacy_positional_construction_still_works():
    """`VerificationResult(True, 0.9, "ok")` predates `verdict`; keep it working."""
    result = VerificationResult(True, 0.9, "ok")

    assert result.passed is True
    assert result.score == 0.9
    assert result.reason == "ok"
    assert result.verdict is Verdict.PASSED


@pytest.mark.parametrize(
    ("passed", "expected"),
    [(True, Verdict.PASSED), (False, Verdict.FAILED)],
)
def test_passed_derives_verdict(passed, expected):
    assert VerificationResult(passed=passed).verdict is expected


@pytest.mark.parametrize(
    ("verdict", "expected"),
    [
        (Verdict.PASSED, True),
        (Verdict.FAILED, False),
        (Verdict.NOT_ASSESSED, False),
    ],
)
def test_verdict_derives_passed(verdict, expected):
    assert VerificationResult(verdict=verdict).passed is expected


def test_verdict_accepts_a_bare_string():
    """Deserialising from JSON or a span attribute shouldn't need the enum."""
    assert VerificationResult(verdict="passed").verdict is Verdict.PASSED
    assert VerificationResult(verdict="not_assessed").assessed is False

    with pytest.raises(ValueError, match="not a valid Verdict"):
        VerificationResult(verdict="probably")


def test_contradiction_is_an_error_not_a_silent_preference():
    """
    Preferring one field over the other would make a contradictory call site
    look correct. Fail loudly instead.
    """
    with pytest.raises(ValueError, match="contradicts verdict"):
        VerificationResult(passed=True, verdict=Verdict.FAILED)

    with pytest.raises(ValueError, match="contradicts verdict"):
        VerificationResult(passed=False, verdict=Verdict.PASSED)

    with pytest.raises(ValueError, match="contradicts verdict"):
        VerificationResult(passed=True, verdict=Verdict.NOT_ASSESSED)

    # Agreeing is fine, if redundant.
    assert VerificationResult(passed=True, verdict=Verdict.PASSED).passed is True


def test_result_is_still_frozen_and_hashable():
    result = VerificationResult(passed=True, score=1.0)

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.passed = False  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.verdict = Verdict.FAILED  # type: ignore[misc]

    # Equality and hashing still work, so results stay usable as dict keys.
    assert VerificationResult(passed=True, score=1.0) == result
    assert len({result, VerificationResult(passed=True, score=1.0)}) == 1


# ============================================
# Wire values match the OTEL convention
# ============================================


def test_wire_values_match_otel_convention():
    """
    docs/OTEL_CONVENTION.md specifies agenkit.verifier.verdict as exactly these
    three strings. A verdict must be recordable on a span without translation.
    """
    assert Verdict.PASSED.value == "passed"
    assert Verdict.FAILED.value == "failed"
    assert Verdict.NOT_ASSESSED.value == "not_assessed"
    assert {v.value for v in Verdict} == {"passed", "failed", "not_assessed"}


def test_verdict_compares_equal_to_its_string():
    """`StrEnum`, so no `.value` needed at the call site."""
    assert Verdict.PASSED == "passed"
    assert VerificationResult(passed=True).verdict == "passed"


def test_verdict_renders_as_its_wire_value():
    """
    `StrEnum` — not `(str, Enum)` — so `str()` gives the wire value rather than
    `Verdict.NOT_ASSESSED`. That matters because a span attribute or log field
    set from an interpolated verdict must not carry the repr. Go's
    `Verdict.String()` is the counterpart.
    """
    assert str(Verdict.NOT_ASSESSED) == "not_assessed"
    assert f"{Verdict.NOT_ASSESSED}" == "not_assessed"
    assert f"verdict={VerificationResult().verdict}" == "verdict=not_assessed"


# ============================================
# Verifier implementations can return the third state
# ============================================


@pytest.mark.asyncio
async def test_verifier_can_report_not_assessed():
    """
    A verifier with no ground truth to check against must be able to say so
    without asserting the answer is wrong — the round-trip quarry needs (#711).
    """

    class PartialVerifier(Verifier):
        """Only knows the answer to one question."""

        async def verify(self, question: str, answer: str) -> VerificationResult:
            if question != "2+2":
                return VerificationResult(
                    verdict=Verdict.NOT_ASSESSED,
                    reason=f"no ground truth for {question!r}",
                )
            return VerificationResult(passed=answer.strip() == "4", score=1.0)

    verifier = PartialVerifier()

    known_good = await verifier.verify("2+2", "4")
    assert known_good.verdict is Verdict.PASSED

    known_bad = await verifier.verify("2+2", "5")
    assert known_bad.verdict is Verdict.FAILED

    unknown = await verifier.verify("meaning of life", "42")
    assert unknown.verdict is Verdict.NOT_ASSESSED
    assert unknown.assessed is False
    # The caller can tell this apart from known_bad, which is the requirement.
    assert unknown.verdict is not known_bad.verdict
    assert "no ground truth" in unknown.reason

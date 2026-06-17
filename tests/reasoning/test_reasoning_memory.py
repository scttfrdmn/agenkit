"""Tests for reasoning memory: Verifier, ReasoningArtifact, ReasoningMemory."""

import pytest

from agenkit.interfaces import Message
from agenkit.reasoning import (
    InMemoryReasoningMemory,
    ReasoningArtifact,
    ScoredCandidate,
    VerificationResult,
    Verifier,
)

# ---------------------------------------------------------------------------
# ScoredCandidate / ReasoningArtifact
# ---------------------------------------------------------------------------


def test_scored_candidate_defaults() -> None:
    c = ScoredCandidate(text="answer")
    assert c.text == "answer"
    assert c.score == 0.0


def test_artifact_fields() -> None:
    art = ReasoningArtifact(
        technique="tree_of_thought",
        session_id="s1",
        candidates=[ScoredCandidate("a", 0.2), ScoredCandidate("b", 0.9)],
        metadata={"depth": 3},
    )
    assert art.technique == "tree_of_thought"
    assert art.session_id == "s1"
    assert len(art.candidates) == 2
    assert art.metadata["depth"] == 3


def test_best_candidate_returns_highest_score() -> None:
    art = ReasoningArtifact(
        technique="self_consistency",
        session_id="s1",
        candidates=[
            ScoredCandidate("low", 0.1),
            ScoredCandidate("high", 0.95),
            ScoredCandidate("mid", 0.5),
        ],
    )
    best = art.best_candidate()
    assert best is not None
    assert best.text == "high"
    assert best.score == 0.95


def test_best_candidate_empty_is_none() -> None:
    art = ReasoningArtifact(technique="chain_of_thought", session_id="s1")
    assert art.best_candidate() is None


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------


class _EqualityVerifier(Verifier):
    """Passes iff the answer equals the expected ground truth."""

    def __init__(self, expected: str) -> None:
        self._expected = expected

    async def verify(self, question: str, answer: str) -> VerificationResult:
        if answer.strip() == self._expected:
            return VerificationResult(passed=True, score=1.0, reason="exact match")
        return VerificationResult(passed=False, score=0.0, reason="mismatch")


@pytest.mark.asyncio
async def test_verifier_pass() -> None:
    v = _EqualityVerifier("42")
    result = await v.verify("what is 6*7?", "42")
    assert result.passed is True
    assert result.score == 1.0
    assert result.reason == "exact match"


@pytest.mark.asyncio
async def test_verifier_fail() -> None:
    v = _EqualityVerifier("42")
    result = await v.verify("what is 6*7?", "41")
    assert result.passed is False
    assert result.score == 0.0


def test_verification_result_defaults() -> None:
    r = VerificationResult(passed=True)
    assert r.passed is True
    assert r.score == 0.0
    assert r.reason == ""


# ---------------------------------------------------------------------------
# InMemoryReasoningMemory
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_memory_store_and_retrieve_messages() -> None:
    mem = InMemoryReasoningMemory()
    await mem.store("s1", Message(role="user", content="hello"))
    await mem.store("s1", Message(role="assistant", content="hi"))
    msgs = await mem.retrieve("s1", limit=10)
    assert len(msgs) == 2
    # Most recent first
    assert msgs[0].content == "hi"


@pytest.mark.asyncio
async def test_memory_retrieve_respects_limit() -> None:
    mem = InMemoryReasoningMemory()
    for i in range(5):
        await mem.store("s1", Message(role="user", content=f"m{i}"))
    msgs = await mem.retrieve("s1", limit=2)
    assert len(msgs) == 2


@pytest.mark.asyncio
async def test_store_and_retrieve_artifacts() -> None:
    mem = InMemoryReasoningMemory()
    art = ReasoningArtifact(
        technique="tree_of_thought",
        session_id="s1",
        candidates=[ScoredCandidate("x", 0.7)],
    )
    await mem.store_artifact("s1", art)
    out = await mem.retrieve_artifacts("s1")
    assert len(out) == 1
    assert out[0].technique == "tree_of_thought"


@pytest.mark.asyncio
async def test_retrieve_artifacts_filters_by_technique() -> None:
    mem = InMemoryReasoningMemory()
    await mem.store_artifact("s1", ReasoningArtifact(technique="tot", session_id="s1"))
    await mem.store_artifact("s1", ReasoningArtifact(technique="cot", session_id="s1"))
    await mem.store_artifact("s1", ReasoningArtifact(technique="tot", session_id="s1"))

    assert len(await mem.retrieve_artifacts("s1")) == 3
    assert len(await mem.retrieve_artifacts("s1", technique="tot")) == 2
    assert len(await mem.retrieve_artifacts("s1", technique="cot")) == 1
    assert len(await mem.retrieve_artifacts("s1", technique="missing")) == 0


@pytest.mark.asyncio
async def test_artifacts_are_session_isolated() -> None:
    mem = InMemoryReasoningMemory()
    await mem.store_artifact("s1", ReasoningArtifact(technique="tot", session_id="s1"))
    await mem.store_artifact("s2", ReasoningArtifact(technique="tot", session_id="s2"))
    assert len(await mem.retrieve_artifacts("s1")) == 1
    assert len(await mem.retrieve_artifacts("s2")) == 1
    assert await mem.retrieve_artifacts("nonexistent") == []


@pytest.mark.asyncio
async def test_clear_removes_messages_and_artifacts() -> None:
    mem = InMemoryReasoningMemory()
    await mem.store("s1", Message(role="user", content="hi"))
    await mem.store_artifact("s1", ReasoningArtifact(technique="tot", session_id="s1"))
    await mem.clear("s1")
    assert await mem.retrieve("s1") == []
    assert await mem.retrieve_artifacts("s1") == []


@pytest.mark.asyncio
async def test_is_usable_as_memory() -> None:
    from agenkit.memory.base import Memory

    mem = InMemoryReasoningMemory()
    assert isinstance(mem, Memory)  # ReasoningMemory is a Memory
    assert "reasoning_artifacts" in mem.capabilities
    summary = await mem.summarize("empty")
    assert summary.role == "system"

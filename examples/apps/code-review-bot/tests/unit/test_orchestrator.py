"""Unit tests for review orchestrator."""

import pytest
from unittest.mock import AsyncMock, patch

from agenkit.interfaces import Message
from python.agents.orchestrator import ReviewOrchestrator


@pytest.mark.asyncio
async def test_orchestrator_conducts_parallel_reviews():
    """Test that orchestrator runs reviews in parallel."""
    orchestrator = ReviewOrchestrator(
        anthropic_key="test-key-1",
        openai_key="test-key-2",
        google_key="test-key-3",
    )

    # Mock LLM responses
    mock_responses = {
        "claude": Message(
            role="assistant", content="Security review: No SQL injection found."
        ),
        "gpt4": Message(
            role="assistant", content="Architecture review: Good separation of concerns."
        ),
        "gemini": Message(role="assistant", content="Style review: Follows PEP 8."),
    }

    with patch.object(
        orchestrator, "_review_with_llm", new_callable=AsyncMock
    ) as mock_review:
        mock_review.side_effect = lambda name, llm, prompt: {
            "reviewer": name,
            "content": mock_responses[name].content,
            "success": True,
        }

        code = "def hello(): return 'world'"
        message = Message(role="user", content=code)

        result = await orchestrator.process(message)

        # Verify all reviewers were called
        assert mock_review.call_count == 3

        # Verify result structure
        assert result.role == "assistant"
        assert "Code Review Report" in str(result.content)
        assert result.metadata["num_reviews"] == 3
        assert result.metadata["consensus_score"] == 1.0  # All successful


@pytest.mark.asyncio
async def test_orchestrator_handles_llm_failures():
    """Test that orchestrator handles individual LLM failures gracefully."""
    orchestrator = ReviewOrchestrator(
        anthropic_key="test-key-1",
        openai_key="test-key-2",
        google_key="test-key-3",
    )

    # Mock mixed success/failure responses
    def mock_review_side_effect(name, llm, prompt):
        if name == "claude":
            return {"reviewer": "claude", "content": "Security review complete", "success": True}
        elif name == "gpt4":
            return {"reviewer": "gpt4", "error": "API timeout", "success": False}
        else:
            return {"reviewer": "gemini", "content": "Style review complete", "success": True}

    with patch.object(
        orchestrator, "_review_with_llm", new_callable=AsyncMock
    ) as mock_review:
        mock_review.side_effect = mock_review_side_effect

        code = "def test(): pass"
        message = Message(role="user", content=code)

        result = await orchestrator.process(message)

        # Only 2 successful reviews
        assert result.metadata["num_reviews"] == 2
        assert result.metadata["consensus_score"] == pytest.approx(2/3, abs=0.01)


def test_consensus_calculation():
    """Test consensus score calculation."""
    orchestrator = ReviewOrchestrator(
        anthropic_key="test-key", openai_key="test-key", google_key="test-key"
    )

    # All successful
    reviews = [
        {"reviewer": "claude", "success": True},
        {"reviewer": "gpt4", "success": True},
        {"reviewer": "gemini", "success": True},
    ]
    assert orchestrator._calculate_consensus(reviews) == 1.0

    # Mixed success
    reviews = [
        {"reviewer": "claude", "success": True},
        {"reviewer": "gpt4", "success": False},
        {"reviewer": "gemini", "success": True},
    ]
    assert orchestrator._calculate_consensus(reviews) == pytest.approx(2/3, abs=0.01)

    # All failed
    reviews = [
        {"reviewer": "claude", "success": False},
        {"reviewer": "gpt4", "success": False},
    ]
    assert orchestrator._calculate_consensus(reviews) == 0.0

    # Empty
    assert orchestrator._calculate_consensus([]) == 0.0


def test_synthesize_reviews():
    """Test review synthesis into report."""
    orchestrator = ReviewOrchestrator(
        anthropic_key="test-key", openai_key="test-key", google_key="test-key"
    )

    reviews = [
        {"reviewer": "claude", "content": "Security looks good", "success": True},
        {"reviewer": "gpt4", "content": "Architecture is clean", "success": True},
    ]

    report = orchestrator._synthesize_reviews(reviews, consensus=0.85)

    assert "Code Review Report" in report
    assert "Consensus Score" in report
    assert "0.85" in report
    assert "CLAUDE Review" in report
    assert "GPT4 Review" in report
    assert "Security looks good" in report


def test_synthesize_reviews_low_consensus():
    """Test that low consensus triggers warning."""
    orchestrator = ReviewOrchestrator(
        anthropic_key="test-key", openai_key="test-key", google_key="test-key"
    )

    reviews = [
        {"reviewer": "claude", "content": "Some issues found", "success": True},
    ]

    report = orchestrator._synthesize_reviews(reviews, consensus=0.33)

    assert "Low consensus" in report
    assert "Manual review recommended" in report


def test_create_specialized_prompts():
    """Test that specialized prompts are created correctly."""
    orchestrator = ReviewOrchestrator(
        anthropic_key="test-key", openai_key="test-key", google_key="test-key"
    )

    code = "def authenticate(user, password): pass"

    # Security prompt
    security_prompt = orchestrator._create_security_prompt(code)
    assert "security" in security_prompt.lower()
    assert "SQL injection" in security_prompt
    assert code in security_prompt

    # Architecture prompt
    arch_prompt = orchestrator._create_architecture_prompt(code)
    assert "architecture" in arch_prompt.lower()
    assert "design patterns" in arch_prompt
    assert code in arch_prompt

    # Style prompt
    style_prompt = orchestrator._create_style_prompt(code)
    assert "style" in style_prompt.lower()
    assert "naming" in style_prompt
    assert code in style_prompt

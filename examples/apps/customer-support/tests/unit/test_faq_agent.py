"""Unit tests for FAQAgent."""

from unittest.mock import AsyncMock, patch

import pytest
from python.agents import FAQAgent

from agenkit.interfaces import Message


@pytest.mark.asyncio
async def test_faq_returns_database_answer():
    """Test FAQ agent returns answer from database."""
    faq = FAQAgent(anthropic_api_key="test-key")

    message = Message(role="user", content="How do I reset my password?")
    result = await faq.process(message)

    assert result.metadata["source"] == "faq_database"
    assert result.metadata["confidence"] == 0.95
    assert result.metadata["cached"] is True
    assert "password" in str(result.content).lower()


@pytest.mark.asyncio
async def test_faq_uses_llm_for_unknown_question():
    """Test FAQ agent uses Claude for questions not in database."""
    faq = FAQAgent(anthropic_api_key="test-key")

    with patch.object(faq._llm, 'complete', new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = Message(
            role="assistant",
            content="Here's the answer to your question..."
        )

        message = Message(role="user", content="What is quantum computing?")
        result = await faq.process(message)

        assert result.metadata["source"] == "llm"
        assert result.metadata["cached"] is False
        mock_complete.assert_called_once()


@pytest.mark.asyncio
async def test_faq_handles_llm_error():
    """Test FAQ agent handles LLM errors gracefully."""
    faq = FAQAgent(anthropic_api_key="test-key")

    with patch.object(faq._llm, 'complete', side_effect=Exception("API error")):
        message = Message(role="user", content="Unknown question")
        result = await faq.process(message)

        assert result.metadata["source"] == "error"
        assert "trouble" in str(result.content).lower()
        assert result.metadata["confidence"] == 0.0


@pytest.mark.asyncio
async def test_faq_matches_multiple_keywords():
    """Test FAQ agent matches various keyword patterns."""
    faq = FAQAgent(anthropic_api_key="test-key")

    test_cases = [
        ("password reset help", "faq_database"),
        ("how to login", "faq_database"),
        ("premium plan features", "faq_database"),
        ("cancel subscription", "faq_database"),
    ]

    for query, expected_source in test_cases:
        message = Message(role="user", content=query)
        result = await faq.process(message)
        assert result.metadata["source"] == expected_source

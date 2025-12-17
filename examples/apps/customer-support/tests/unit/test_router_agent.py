"""Unit tests for RouterAgent."""

import pytest
from unittest.mock import AsyncMock, patch

from agenkit.interfaces import Message
from python.agents import RouterAgent


@pytest.mark.asyncio
async def test_router_classifies_faq_query():
    """Test router correctly classifies FAQ query."""
    router = RouterAgent(anthropic_api_key="test-key")

    # Mock Claude response
    with patch.object(router._llm, 'complete', new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = Message(
            role="assistant",
            content="faq|0.95"
        )

        message = Message(role="user", content="How do I reset my password?")
        result = await router.process(message)

        assert result.metadata["route"] == "faq"
        assert result.metadata["confidence"] >= 0.9


@pytest.mark.asyncio
async def test_router_classifies_specialist_query():
    """Test router correctly classifies specialist query."""
    router = RouterAgent(anthropic_api_key="test-key")

    with patch.object(router._llm, 'complete', new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = Message(
            role="assistant",
            content="specialist|0.85"
        )

        message = Message(role="user", content="I need advanced API integration help")
        result = await router.process(message)

        assert result.metadata["route"] == "specialist"
        assert result.metadata["confidence"] >= 0.8


@pytest.mark.asyncio
async def test_router_fallback_on_error():
    """Test router uses fallback classification on LLM error."""
    router = RouterAgent(anthropic_api_key="test-key")

    with patch.object(router._llm, 'complete', side_effect=Exception("API error")):
        message = Message(role="user", content="password reset")
        result = await router.process(message)

        # Should fallback to keyword matching
        assert result.metadata["route"] in ["faq", "specialist", "escalation"]
        assert "confidence" in result.metadata


@pytest.mark.asyncio
async def test_router_escalation_keywords():
    """Test router identifies escalation keywords."""
    router = RouterAgent(anthropic_api_key="test-key")

    with patch.object(router._llm, 'complete', side_effect=Exception("Force fallback")):
        message = Message(role="user", content="I want a refund immediately!")
        result = await router.process(message)

        assert result.metadata["route"] == "escalation"

"""Tests for LiteLLM adapter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agenkit.interfaces import Message

# Skip all tests if litellm not installed
pytest.importorskip("litellm")

from agenkit.adapters.llm import LiteLLMLLM


# Unit Tests (Mocked)
@pytest.mark.asyncio
async def test_complete_success(simple_test_message):
    """Test successful completion with mocked LiteLLM."""
    llm = LiteLLMLLM(model="gpt-4")

    # Mock litellm.acompletion
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Hello! I'm doing well, thank you for asking."))
    ]
    mock_response.model = "gpt-4"
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=15, total_tokens=25)

    with patch("litellm.acompletion", new=AsyncMock(return_value=mock_response)):
        response = await llm.complete(simple_test_message)

        assert response.role == "agent"
        assert response.content == "Hello! I'm doing well, thank you for asking."
        assert "usage" in response.metadata
        assert response.metadata["usage"]["prompt_tokens"] == 10


def test_message_conversion(test_messages):
    """Test Agenkit Message to LiteLLM (OpenAI-style) format conversion."""
    llm = LiteLLMLLM(model="gpt-4")

    converted = llm._convert_messages(test_messages)

    assert len(converted) == 2
    assert converted[0]["role"] == "system"
    assert converted[1]["role"] == "user"


def test_message_conversion_agent_role():
    """Test agent role is converted to assistant."""
    llm = LiteLLMLLM(model="gpt-4")
    messages = [Message(role="agent", content="Hello from agent")]

    converted = llm._convert_messages(messages)

    assert converted[0]["role"] == "assistant"


def test_model_property():
    """Test model property returns configured model."""
    llm = LiteLLMLLM(model="claude-3-5-sonnet-20241022")
    assert llm.model == "claude-3-5-sonnet-20241022"


def test_various_provider_formats():
    """Test that various provider model formats are accepted."""
    # OpenAI
    llm = LiteLLMLLM(model="gpt-4")
    assert llm.model == "gpt-4"

    # Anthropic
    llm = LiteLLMLLM(model="claude-3-5-sonnet-20241022")
    assert llm.model == "claude-3-5-sonnet-20241022"

    # Bedrock
    llm = LiteLLMLLM(model="bedrock/anthropic.claude-v2")
    assert llm.model == "bedrock/anthropic.claude-v2"

    # Ollama
    llm = LiteLLMLLM(model="ollama/llama2")
    assert llm.model == "ollama/llama2"


def test_unwrap():
    """Test unwrap returns None (LiteLLM is functional API)."""
    llm = LiteLLMLLM(model="gpt-4")
    assert llm.unwrap() is None


# Integration Tests (Real API)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_litellm_with_openai(openai_api_key, simple_test_message):
    """Integration test using LiteLLM with OpenAI."""
    llm = LiteLLMLLM(model="gpt-4o-mini", api_key=openai_api_key)

    response = await llm.complete(simple_test_message, max_tokens=50)

    assert response.role == "agent"
    assert len(response.content) > 0
    assert "model" in response.metadata


@pytest.mark.integration
@pytest.mark.asyncio
async def test_litellm_streaming(openai_api_key, simple_test_message):
    """Integration test for streaming via LiteLLM."""
    llm = LiteLLMLLM(model="gpt-4o-mini", api_key=openai_api_key)

    chunks = []
    async for chunk in llm.stream(simple_test_message, max_tokens=50):
        assert chunk.role == "agent"
        assert chunk.metadata["streaming"] is True
        chunks.append(chunk.content)

    assert len(chunks) > 0
    assert len("".join(chunks)) > 0

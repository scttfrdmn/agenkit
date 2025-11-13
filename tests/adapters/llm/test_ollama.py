"""Tests for Ollama LLM adapter."""

import pytest

from agenkit.interfaces import Message

# Skip all tests if ollama not installed
pytest.importorskip("ollama")

from agenkit.adapters.llm import OllamaLLM


# Unit Tests (Mocked)
@pytest.mark.asyncio
async def test_complete_success(mock_ollama_response, simple_test_message):
    """Test successful completion with mocked API."""
    from unittest.mock import AsyncMock

    llm = OllamaLLM(model="llama2")
    llm._client.chat = AsyncMock(return_value=mock_ollama_response)

    response = await llm.complete(simple_test_message)

    assert response.role == "agent"
    assert response.content == "Hello! I'm doing well, thank you for asking."
    assert "eval_count" in response.metadata
    assert response.metadata["eval_count"] == 15


def test_message_conversion(test_messages):
    """Test Agenkit Message to Ollama format conversion."""
    llm = OllamaLLM(model="llama2")

    converted = llm._convert_messages(test_messages)

    assert len(converted) == 2
    assert converted[0]["role"] == "system"
    assert converted[0]["content"] == "You are a helpful assistant."
    assert converted[1]["role"] == "user"


def test_message_conversion_agent_role():
    """Test agent role is converted to assistant."""
    llm = OllamaLLM(model="llama2")
    messages = [Message(role="agent", content="Hello from agent")]

    converted = llm._convert_messages(messages)

    assert converted[0]["role"] == "assistant"


def test_model_property():
    """Test model property returns configured model."""
    llm = OllamaLLM(model="mistral")
    assert llm.model == "mistral"


def test_unwrap():
    """Test unwrap returns underlying AsyncClient."""
    llm = OllamaLLM(model="llama2")
    client = llm.unwrap()
    assert client is llm._client


# Integration Tests (Real API - requires Ollama running)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_ollama_integration(ollama_available, simple_test_message):
    """Integration test with local Ollama."""
    llm = OllamaLLM(model="llama2")

    response = await llm.complete(simple_test_message, max_tokens=50)

    assert response.role == "agent"
    assert len(response.content) > 0
    assert "model" in response.metadata


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ollama_streaming_integration(ollama_available, simple_test_message):
    """Integration test for streaming with local Ollama."""
    llm = OllamaLLM(model="llama2")

    chunks = []
    async for chunk in llm.stream(simple_test_message, max_tokens=50):
        assert chunk.role == "agent"
        assert chunk.metadata["streaming"] is True
        chunks.append(chunk.content)

    assert len(chunks) > 0
    assert len("".join(chunks)) > 0

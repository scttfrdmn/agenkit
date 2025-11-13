"""Tests for Google Gemini LLM adapter."""

import pytest

from agenkit.interfaces import Message

# Skip all tests if google-genai not installed
pytest.importorskip("google.genai")

from agenkit.adapters.llm import GeminiLLM


# Unit Tests (Mocked)
@pytest.mark.asyncio
async def test_complete_success(mock_gemini_client, simple_test_message):
    """Test successful completion with mocked API."""
    llm = GeminiLLM(api_key="test-key")
    llm._client = mock_gemini_client

    response = await llm.complete(simple_test_message)

    assert response.role == "agent"
    assert response.content == "Hello! I'm doing well, thank you for asking."
    assert "usage" in response.metadata
    assert response.metadata["usage"]["prompt_tokens"] == 10
    assert response.metadata["usage"]["completion_tokens"] == 15


def test_message_conversion(test_messages):
    """Test Agenkit Message to Gemini format conversion."""
    llm = GeminiLLM(api_key="test-key")

    converted = llm._convert_messages(test_messages)

    assert len(converted) == 2
    # System message converted to user in Gemini
    assert converted[0]["role"] == "user"
    assert converted[0]["parts"][0]["text"] == "You are a helpful assistant."
    assert converted[1]["role"] == "user"


def test_message_conversion_agent_role():
    """Test agent role is converted to model."""
    llm = GeminiLLM(api_key="test-key")
    messages = [Message(role="agent", content="Hello from agent")]

    converted = llm._convert_messages(messages)

    assert converted[0]["role"] == "model"


def test_model_property():
    """Test model property returns configured model."""
    llm = GeminiLLM(api_key="test-key", model="gemini-pro")
    assert llm.model == "gemini-pro"


def test_unwrap():
    """Test unwrap returns underlying client."""
    llm = GeminiLLM(api_key="test-key")
    client = llm.unwrap()
    assert client is llm._client


# Integration Tests (Real API)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_gemini_integration(gemini_api_key, simple_test_message):
    """Integration test with real Gemini API."""
    llm = GeminiLLM(api_key=gemini_api_key, model="gemini-2.0-flash-exp")

    response = await llm.complete(simple_test_message, max_tokens=50)

    assert response.role == "agent"
    assert len(response.content) > 0
    # Usage metadata is optional in Gemini
    if "usage" in response.metadata:
        assert response.metadata["usage"]["total_tokens"] > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gemini_streaming_integration(gemini_api_key, simple_test_message):
    """Integration test for streaming with real Gemini API."""
    llm = GeminiLLM(api_key=gemini_api_key, model="gemini-2.0-flash-exp")

    chunks = []
    async for chunk in llm.stream(simple_test_message, max_tokens=50):
        assert chunk.role == "agent"
        assert chunk.metadata["streaming"] is True
        chunks.append(chunk.content)

    assert len(chunks) > 0
    assert len("".join(chunks)) > 0

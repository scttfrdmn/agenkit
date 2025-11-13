"""Tests for OpenAI LLM adapter."""

import pytest

from agenkit.interfaces import Message

# Skip all tests if openai not installed
pytest.importorskip("openai")

from agenkit.adapters.llm import OpenAILLM


# Unit Tests (Mocked)
@pytest.mark.asyncio
async def test_complete_success(mock_openai_client, simple_test_message):
    """Test successful completion with mocked API."""
    llm = OpenAILLM(api_key="test-key")
    llm._client = mock_openai_client

    response = await llm.complete(simple_test_message)

    assert response.role == "agent"
    assert response.content == "Hello! I'm doing well, thank you for asking."
    assert "usage" in response.metadata
    assert response.metadata["usage"]["prompt_tokens"] == 10
    assert response.metadata["usage"]["completion_tokens"] == 15


@pytest.mark.asyncio
async def test_complete_with_options(mock_openai_client, simple_test_message):
    """Test completion with temperature and max_tokens."""
    llm = OpenAILLM(api_key="test-key")
    llm._client = mock_openai_client

    await llm.complete(simple_test_message, temperature=0.5, max_tokens=100)

    call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0.5
    assert call_kwargs["max_tokens"] == 100


def test_message_conversion(test_messages):
    """Test Agenkit Message to OpenAI format conversion."""
    llm = OpenAILLM(api_key="test-key")

    converted = llm._convert_messages(test_messages)

    assert len(converted) == 2
    assert converted[0]["role"] == "system"
    assert converted[0]["content"] == "You are a helpful assistant."
    assert converted[1]["role"] == "user"
    assert converted[1]["content"] == "Hello, how are you?"


def test_message_conversion_agent_role():
    """Test agent role is converted to assistant."""
    llm = OpenAILLM(api_key="test-key")
    messages = [Message(role="agent", content="Hello from agent")]

    converted = llm._convert_messages(messages)

    assert converted[0]["role"] == "assistant"


def test_model_property():
    """Test model property returns configured model."""
    llm = OpenAILLM(api_key="test-key", model="gpt-4")
    assert llm.model == "gpt-4"


def test_unwrap():
    """Test unwrap returns underlying client."""
    llm = OpenAILLM(api_key="test-key")
    client = llm.unwrap()
    assert client is llm._client


# Integration Tests (Real API)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_integration(openai_api_key, simple_test_message):
    """Integration test with real OpenAI API."""
    llm = OpenAILLM(api_key=openai_api_key, model="gpt-4o-mini")

    response = await llm.complete(simple_test_message, max_tokens=50)

    assert response.role == "agent"
    assert len(response.content) > 0
    assert "usage" in response.metadata
    assert response.metadata["usage"]["prompt_tokens"] > 0
    assert response.metadata["usage"]["completion_tokens"] > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_streaming_integration(openai_api_key, simple_test_message):
    """Integration test for streaming with real OpenAI API."""
    llm = OpenAILLM(api_key=openai_api_key, model="gpt-4o-mini")

    chunks = []
    async for chunk in llm.stream(simple_test_message, max_tokens=50):
        assert chunk.role == "agent"
        assert chunk.metadata["streaming"] is True
        chunks.append(chunk.content)

    assert len(chunks) > 0
    assert len("".join(chunks)) > 0

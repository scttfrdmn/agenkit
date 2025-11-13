"""Tests for Anthropic LLM adapter."""

import pytest

from agenkit.interfaces import Message

# Skip all tests if anthropic not installed
pytest.importorskip("anthropic")

from agenkit.adapters.llm import AnthropicLLM


# Unit Tests (Mocked)
@pytest.mark.asyncio
async def test_complete_success(mock_anthropic_client, simple_test_message):
    """Test successful completion with mocked API."""
    llm = AnthropicLLM(api_key="test-key")
    llm._client = mock_anthropic_client

    response = await llm.complete(simple_test_message)

    assert response.role == "agent"
    assert response.content == "Hello! I'm doing well, thank you for asking."
    assert "usage" in response.metadata
    assert response.metadata["usage"]["input_tokens"] == 10
    assert response.metadata["usage"]["output_tokens"] == 15


@pytest.mark.asyncio
async def test_complete_with_options(mock_anthropic_client, simple_test_message):
    """Test completion with temperature and max_tokens."""
    llm = AnthropicLLM(api_key="test-key")
    llm._client = mock_anthropic_client

    await llm.complete(simple_test_message, temperature=0.5, max_tokens=100)

    # Verify the mock was called with correct parameters
    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0.5
    assert call_kwargs["max_tokens"] == 100


def test_message_conversion_user(simple_test_message):
    """Test Agenkit Message to Anthropic format conversion."""
    llm = AnthropicLLM(api_key="test-key")

    converted = llm._convert_messages(simple_test_message)

    assert len(converted) == 1
    assert converted[0]["role"] == "user"
    assert converted[0]["content"] == "Hello!"


def test_message_conversion_with_system(test_messages):
    """Test system message extraction."""
    llm = AnthropicLLM(api_key="test-key")

    converted = llm._convert_messages(test_messages)
    system = llm._extract_system_message(test_messages)

    # System message should be extracted
    assert system == "You are a helpful assistant."
    # And not in converted messages
    assert len(converted) == 1
    assert converted[0]["role"] == "user"


def test_message_conversion_agent_role():
    """Test agent role is converted to assistant."""
    llm = AnthropicLLM(api_key="test-key")
    messages = [Message(role="agent", content="Hello from agent")]

    converted = llm._convert_messages(messages)

    assert converted[0]["role"] == "assistant"


def test_model_property():
    """Test model property returns configured model."""
    llm = AnthropicLLM(api_key="test-key", model="claude-3-opus-20240229")
    assert llm.model == "claude-3-opus-20240229"


def test_unwrap():
    """Test unwrap returns underlying client."""
    llm = AnthropicLLM(api_key="test-key")
    client = llm.unwrap()
    # Should return AsyncAnthropic instance
    assert client is llm._client


# Integration Tests (Real API)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_anthropic_integration(anthropic_api_key, simple_test_message):
    """Integration test with real Anthropic API."""
    llm = AnthropicLLM(api_key=anthropic_api_key, model="claude-3-haiku-20240307")

    response = await llm.complete(simple_test_message, max_tokens=50)

    assert response.role == "agent"
    assert len(response.content) > 0
    assert "usage" in response.metadata
    assert response.metadata["usage"]["input_tokens"] > 0
    assert response.metadata["usage"]["output_tokens"] > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_anthropic_streaming_integration(anthropic_api_key, simple_test_message):
    """Integration test for streaming with real Anthropic API."""
    llm = AnthropicLLM(api_key=anthropic_api_key, model="claude-3-haiku-20240307")

    chunks = []
    async for chunk in llm.stream(simple_test_message, max_tokens=50):
        assert chunk.role == "agent"
        assert chunk.metadata["streaming"] is True
        chunks.append(chunk.content)

    # Should have received multiple chunks
    assert len(chunks) > 0
    # Combined content should be non-empty
    assert len("".join(chunks)) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_anthropic_with_system_message(anthropic_api_key, test_messages):
    """Test that system messages are handled correctly."""
    llm = AnthropicLLM(api_key=anthropic_api_key, model="claude-3-haiku-20240307")

    response = await llm.complete(test_messages, max_tokens=50)

    assert response.role == "agent"
    assert len(response.content) > 0

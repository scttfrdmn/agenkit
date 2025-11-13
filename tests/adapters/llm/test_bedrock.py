"""Tests for Amazon Bedrock LLM adapter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agenkit.interfaces import Message

# Skip all tests if boto3 not installed
pytest.importorskip("boto3")

from agenkit.adapters.llm import BedrockLLM


# Unit Tests (Mocked)
@pytest.mark.asyncio
async def test_complete_success(mock_bedrock_response, simple_test_message):
    """Test successful completion with mocked API."""
    llm = BedrockLLM(model_id="anthropic.claude-3-haiku-20240307-v1:0")

    with patch.object(llm._client, "converse", return_value=mock_bedrock_response):
        response = await llm.complete(simple_test_message)

        assert response.role == "agent"
        assert response.content == "Hello! I'm doing well, thank you for asking."
        assert "usage" in response.metadata
        assert response.metadata["usage"]["prompt_tokens"] == 10
        assert response.metadata["usage"]["completion_tokens"] == 15


def test_message_conversion(test_messages):
    """Test Agenkit Message to Bedrock format conversion."""
    llm = BedrockLLM(model_id="anthropic.claude-3-haiku-20240307-v1:0")

    bedrock_messages, system_prompts = llm._convert_messages(test_messages)

    # System message should be extracted
    assert len(system_prompts) == 1
    assert system_prompts[0]["text"] == "You are a helpful assistant."

    # User message in bedrock format
    assert len(bedrock_messages) == 1
    assert bedrock_messages[0]["role"] == "user"
    assert bedrock_messages[0]["content"][0]["text"] == "Hello, how are you?"


def test_message_conversion_agent_role():
    """Test agent role is converted to assistant."""
    llm = BedrockLLM(model_id="anthropic.claude-3-haiku-20240307-v1:0")
    messages = [Message(role="agent", content="Hello from agent")]

    bedrock_messages, _ = llm._convert_messages(messages)

    assert bedrock_messages[0]["role"] == "assistant"


def test_model_property():
    """Test model property returns configured model ID."""
    llm = BedrockLLM(model_id="meta.llama3-70b-instruct-v1:0")
    assert llm.model == "meta.llama3-70b-instruct-v1:0"


def test_unwrap():
    """Test unwrap returns underlying boto3 client."""
    llm = BedrockLLM(model_id="anthropic.claude-3-haiku-20240307-v1:0")
    client = llm.unwrap()
    assert client is llm._client


def test_aws_profile_initialization():
    """Test initialization with AWS profile."""
    llm = BedrockLLM(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        profile_name="aws",
    )
    assert llm.model == "anthropic.claude-3-haiku-20240307-v1:0"


# Integration Tests (Real API)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_bedrock_integration(aws_profile, simple_test_message):
    """Integration test with real Bedrock API."""
    llm = BedrockLLM(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        profile_name=aws_profile,
        region_name="us-east-1",
    )

    response = await llm.complete(simple_test_message, max_tokens=50)

    assert response.role == "agent"
    assert len(response.content) > 0
    assert "usage" in response.metadata
    assert response.metadata["usage"]["prompt_tokens"] > 0
    assert response.metadata["usage"]["completion_tokens"] > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bedrock_streaming_integration(aws_profile, simple_test_message):
    """Integration test for streaming with real Bedrock API."""
    llm = BedrockLLM(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        profile_name=aws_profile,
        region_name="us-east-1",
    )

    chunks = []
    async for chunk in llm.stream(simple_test_message, max_tokens=50):
        assert chunk.role == "agent"
        assert chunk.metadata["streaming"] is True
        chunks.append(chunk.content)

    assert len(chunks) > 0
    assert len("".join(chunks)) > 0

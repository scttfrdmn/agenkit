"""Tests for LLM base interface."""

import pytest

from agenkit.adapters.llm.base import LLM
from agenkit.interfaces import Message


class ConcreteLLM(LLM):
    """Concrete implementation for testing."""

    async def complete(self, messages, **kwargs):
        return Message(role="agent", content="Test response")

    async def stream(self, messages, **kwargs):
        yield Message(role="agent", content="Test")
        yield Message(role="agent", content=" response")


def test_llm_is_abstract():
    """Test that LLM cannot be instantiated directly."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        LLM()  # type: ignore


@pytest.mark.asyncio
async def test_concrete_implementation():
    """Test that concrete implementations work."""
    llm = ConcreteLLM()

    # Test complete
    messages = [Message(role="user", content="Hello")]
    response = await llm.complete(messages)
    assert response.role == "agent"
    assert response.content == "Test response"

    # Test stream
    chunks = []
    async for chunk in llm.stream(messages):
        chunks.append(chunk.content)
    assert "".join(chunks) == "Test response"


def test_model_property_default():
    """Test default model property."""
    llm = ConcreteLLM()
    assert llm.model == "unknown"


def test_unwrap_default():
    """Test default unwrap returns self."""
    llm = ConcreteLLM()
    assert llm.unwrap() == llm


def test_llm_interface_signature():
    """Test that LLM has expected methods."""
    assert hasattr(LLM, "complete")
    assert hasattr(LLM, "stream")
    assert hasattr(LLM, "model")
    assert hasattr(LLM, "unwrap")

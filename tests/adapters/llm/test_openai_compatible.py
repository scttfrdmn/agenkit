"""
Tests for OpenAI-compatible LLM adapter.

This test suite verifies that the OpenAICompatibleLLM adapter correctly:
1. Initializes with required and optional parameters
2. Converts Agenkit messages to OpenAI format
3. Makes proper API calls to OpenAI-compatible services
4. Handles responses and streams correctly
5. Includes provider metadata in responses
6. Handles errors appropriately
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("openai", reason="openai package not installed — skipping LLM adapter tests")

from agenkit.adapters.llm.openai_compatible import OpenAICompatibleLLM
from agenkit.interfaces import Message


class TestInitialization:
    """Test adapter initialization with various configurations."""

    def test_init_with_required_params(self):
        """Test initialization with only required parameters."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
        )

        assert llm.model == "llama-2-7b"
        assert llm._base_url == "http://localhost:8000/v1"
        assert llm._provider is None
        assert llm._client is not None

    def test_init_with_api_key(self):
        """Test initialization with optional API key."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
            api_key="test-key",
        )

        assert llm._client is not None
        # API key is stored in client but not directly accessible

    def test_init_with_provider(self):
        """Test initialization with provider name for metadata."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
            provider="vllm",
        )

        assert llm._provider == "vllm"

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
            timeout_ms=120000,
        )

        assert llm._client is not None
        # Timeout is passed to client but not directly verifiable

    def test_init_without_api_key_defaults(self):
        """Test that missing API key defaults to 'not-needed'."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
        )

        # Verify client was created (would fail if api_key was required)
        assert llm._client is not None


class TestMessageConversion:
    """Test conversion of Agenkit messages to OpenAI format."""

    def test_convert_single_user_message(self):
        """Test converting a single user message."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
        )

        messages = [Message(role="user", content="Hello")]
        converted = llm._convert_messages(messages)

        assert len(converted) == 1
        assert converted[0]["role"] == "user"
        assert converted[0]["content"] == "Hello"

    def test_convert_system_message(self):
        """Test converting a system message."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
        )

        messages = [Message(role="system", content="You are helpful")]
        converted = llm._convert_messages(messages)

        assert converted[0]["role"] == "system"
        assert converted[0]["content"] == "You are helpful"

    def test_convert_agent_to_assistant(self):
        """Test that 'agent' role is converted to 'assistant'."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
        )

        messages = [Message(role="agent", content="I can help")]
        converted = llm._convert_messages(messages)

        assert converted[0]["role"] == "assistant"
        assert converted[0]["content"] == "I can help"

    def test_convert_conversation(self):
        """Test converting a multi-turn conversation."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
        )

        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
            Message(role="agent", content="Hi there!"),
            Message(role="user", content="How are you?"),
        ]
        converted = llm._convert_messages(messages)

        assert len(converted) == 4
        assert converted[0]["role"] == "system"
        assert converted[1]["role"] == "user"
        assert converted[2]["role"] == "assistant"
        assert converted[3]["role"] == "user"

    def test_convert_tool_message(self):
        """Test that 'tool' role is preserved."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
        )

        messages = [Message(role="tool", content="Tool result")]
        converted = llm._convert_messages(messages)

        assert converted[0]["role"] == "tool"


class TestComplete:
    """Test the complete() method with mocked API calls."""

    @pytest.mark.asyncio
    async def test_complete_basic(self):
        """Test basic completion with minimal parameters."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
            provider="vllm",
        )

        # Mock the API call
        mock_choice = MagicMock()
        mock_choice.message.content = "Hello! How can I help?"
        mock_choice.finish_reason = "stop"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 30

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "llama-2-7b"
        mock_response.usage = mock_usage
        mock_response.id = "test-id-123"

        with patch.object(
            llm._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            messages = [Message(role="user", content="Hello")]
            response = await llm.complete(messages)

            assert response.role == "agent"
            assert response.content == "Hello! How can I help?"
            assert response.metadata["model"] == "llama-2-7b"
            assert response.metadata["provider"] == "vllm"
            assert response.metadata["base_url"] == "http://localhost:8000/v1"
            assert response.metadata["usage"]["total_tokens"] == 30
            assert response.metadata["finish_reason"] == "stop"
            assert response.metadata["id"] == "test-id-123"

    @pytest.mark.asyncio
    async def test_complete_with_temperature(self):
        """Test completion with custom temperature."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
        )

        mock_choice = MagicMock()
        mock_choice.message.content = "Response"
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "llama-2-7b"
        mock_response.usage = None
        mock_response.id = "test-id"

        mock_create = AsyncMock(return_value=mock_response)

        with patch.object(llm._client.chat.completions, "create", mock_create):
            messages = [Message(role="user", content="Hello")]
            await llm.complete(messages, temperature=0.7)

            # Verify temperature was passed
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["temperature"] == 0.7

    @pytest.mark.asyncio
    async def test_complete_with_max_tokens(self):
        """Test completion with max_tokens parameter."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
        )

        mock_choice = MagicMock()
        mock_choice.message.content = "Response"
        mock_choice.finish_reason = "length"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "llama-2-7b"
        mock_response.usage = None
        mock_response.id = "test-id"

        mock_create = AsyncMock(return_value=mock_response)

        with patch.object(llm._client.chat.completions, "create", mock_create):
            messages = [Message(role="user", content="Hello")]
            response = await llm.complete(messages, max_tokens=100)

            # Verify max_tokens was passed
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["max_tokens"] == 100
            assert response.metadata["finish_reason"] == "length"

    @pytest.mark.asyncio
    async def test_complete_forwards_seed_and_stop(self):
        """
        seed and stop must reach the outgoing request (#818).

        OpenAICompatibleLLM wraps the same AsyncOpenAI SDK as OpenAILLM, which
        supports both "seed" and "stop" natively under those exact names, so
        vLLM/llama.cpp/SGLang/etc. servers that honor them receive the values
        unchanged.
        """
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
        )

        mock_choice = MagicMock()
        mock_choice.message.content = "Response"
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "llama-2-7b"
        mock_response.usage = None
        mock_response.id = "test-id"

        mock_create = AsyncMock(return_value=mock_response)

        with patch.object(llm._client.chat.completions, "create", mock_create):
            messages = [Message(role="user", content="Hello")]
            await llm.complete(messages, seed=918273645, stop=["END", "STOP"])

            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["seed"] == 918273645
            assert call_kwargs["stop"] == ["END", "STOP"]

    @pytest.mark.asyncio
    async def test_complete_without_usage(self):
        """Test completion when service doesn't return usage stats."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
        )

        mock_choice = MagicMock()
        mock_choice.message.content = "Response"
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "llama-2-7b"
        mock_response.usage = None  # No usage stats
        mock_response.id = "test-id"

        with patch.object(
            llm._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            messages = [Message(role="user", content="Hello")]
            response = await llm.complete(messages)

            # Should default to 0 for all token counts
            assert response.metadata["usage"]["prompt_tokens"] == 0
            assert response.metadata["usage"]["completion_tokens"] == 0
            assert response.metadata["usage"]["total_tokens"] == 0

    @pytest.mark.asyncio
    async def test_complete_default_provider_name(self):
        """Test that provider defaults to 'openai_compatible' if not specified."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
            # No provider specified
        )

        mock_choice = MagicMock()
        mock_choice.message.content = "Response"
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "llama-2-7b"
        mock_response.usage = None
        mock_response.id = "test-id"

        with patch.object(
            llm._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            messages = [Message(role="user", content="Hello")]
            response = await llm.complete(messages)

            assert response.metadata["provider"] == "openai_compatible"


class TestStream:
    """Test the stream() method with mocked API calls."""

    @pytest.mark.asyncio
    async def test_stream_basic(self):
        """Test basic streaming with multiple chunks."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
            provider="vllm",
        )

        # Create mock chunks
        chunks = []
        for content in ["Hello", " there", "!"]:
            mock_choice = MagicMock()
            mock_choice.delta.content = content

            mock_chunk = MagicMock()
            mock_chunk.choices = [mock_choice]
            chunks.append(mock_chunk)

        # Mock the async generator
        async def mock_stream():
            for chunk in chunks:
                yield chunk

        mock_create = AsyncMock(return_value=mock_stream())

        with patch.object(llm._client.chat.completions, "create", mock_create):
            messages = [Message(role="user", content="Hello")]
            result_chunks = []

            async for chunk in llm.stream(messages):
                result_chunks.append(chunk)

            # Verify chunks
            assert len(result_chunks) == 3
            assert result_chunks[0].content == "Hello"
            assert result_chunks[1].content == " there"
            assert result_chunks[2].content == "!"

            # Verify metadata
            for chunk in result_chunks:
                assert chunk.role == "agent"
                assert chunk.metadata["streaming"] is True
                assert chunk.metadata["model"] == "llama-2-7b"
                assert chunk.metadata["provider"] == "vllm"

    @pytest.mark.asyncio
    async def test_stream_accumulate_content(self):
        """Test accumulating streamed content into full response."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
        )

        chunks = []
        for content in ["The", " answer", " is", " 42"]:
            mock_choice = MagicMock()
            mock_choice.delta.content = content

            mock_chunk = MagicMock()
            mock_chunk.choices = [mock_choice]
            chunks.append(mock_chunk)

        async def mock_stream():
            for chunk in chunks:
                yield chunk

        mock_create = AsyncMock(return_value=mock_stream())

        with patch.object(llm._client.chat.completions, "create", mock_create):
            messages = [Message(role="user", content="What is the answer?")]
            accumulated = []

            async for chunk in llm.stream(messages):
                accumulated.append(chunk.content)

            full_response = "".join(accumulated)
            assert full_response == "The answer is 42"

    @pytest.mark.asyncio
    async def test_stream_skip_empty_chunks(self):
        """Test that empty chunks (no content) are skipped."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
        )

        chunks = []
        # Mix of chunks with and without content
        for content in ["Hello", None, "", "World"]:
            mock_choice = MagicMock()
            mock_choice.delta.content = content

            mock_chunk = MagicMock()
            mock_chunk.choices = [mock_choice]
            chunks.append(mock_chunk)

        async def mock_stream():
            for chunk in chunks:
                yield chunk

        mock_create = AsyncMock(return_value=mock_stream())

        with patch.object(llm._client.chat.completions, "create", mock_create):
            messages = [Message(role="user", content="Hello")]
            result_chunks = []

            async for chunk in llm.stream(messages):
                result_chunks.append(chunk.content)

            # Only chunks with content should be yielded
            assert result_chunks == ["Hello", "World"]

    @pytest.mark.asyncio
    async def test_stream_with_temperature(self):
        """Test streaming with custom temperature."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
        )

        async def mock_stream():
            mock_choice = MagicMock()
            mock_choice.delta.content = "Test"
            mock_chunk = MagicMock()
            mock_chunk.choices = [mock_choice]
            yield mock_chunk

        mock_create = AsyncMock(return_value=mock_stream())

        with patch.object(llm._client.chat.completions, "create", mock_create):
            messages = [Message(role="user", content="Hello")]

            async for _ in llm.stream(messages, temperature=0.5):
                pass

            # Verify parameters
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["temperature"] == 0.5
            assert call_kwargs["stream"] is True


class TestUnwrap:
    """Test the unwrap() method."""

    def test_unwrap_returns_client(self):
        """Test that unwrap returns the AsyncOpenAI client."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="llama-2-7b",
        )

        client = llm.unwrap()

        # Verify it's the AsyncOpenAI client
        assert client is llm._client
        from openai import AsyncOpenAI

        assert isinstance(client, AsyncOpenAI)


class TestIntegration:
    """Integration tests simulating real service behavior."""

    @pytest.mark.asyncio
    async def test_vllm_simulation(self):
        """Simulate interaction with vLLM service."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8000/v1",
            model="meta-llama/Llama-2-7b-chat-hf",
            provider="vllm",
        )

        # Simulate vLLM response
        mock_choice = MagicMock()
        mock_choice.message.content = "Machine learning is a subset of AI..."
        mock_choice.finish_reason = "stop"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 25
        mock_usage.completion_tokens = 150
        mock_usage.total_tokens = 175

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "meta-llama/Llama-2-7b-chat-hf"
        mock_response.usage = mock_usage
        mock_response.id = "cmpl-vllm-123"

        with patch.object(
            llm._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            messages = [Message(role="user", content="What is machine learning?")]
            response = await llm.complete(messages, temperature=0.7)

            assert response.content.startswith("Machine learning")
            assert response.metadata["provider"] == "vllm"
            assert response.metadata["model"] == "meta-llama/Llama-2-7b-chat-hf"
            assert response.metadata["usage"]["total_tokens"] == 175

    @pytest.mark.asyncio
    async def test_llamacpp_simulation(self):
        """Simulate interaction with llama.cpp server."""
        llm = OpenAICompatibleLLM(
            base_url="http://localhost:8080/v1",
            model="llama-2-7b-chat",
            provider="llamacpp",
        )

        # llama.cpp may not return usage stats
        mock_choice = MagicMock()
        mock_choice.message.content = "The capital of France is Paris."
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "llama-2-7b-chat"
        mock_response.usage = None  # llama.cpp might not return this
        mock_response.id = "llamacpp-123"

        with patch.object(
            llm._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            messages = [Message(role="user", content="What is the capital of France?")]
            response = await llm.complete(messages)

            assert "Paris" in response.content
            assert response.metadata["provider"] == "llamacpp"
            # Usage should default to 0
            assert response.metadata["usage"]["total_tokens"] == 0

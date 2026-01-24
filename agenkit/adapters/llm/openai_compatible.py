"""
OpenAI-compatible LLM adapter for Agenkit.

This module provides a generic adapter for any inference service that implements
the OpenAI Chat Completions API. This includes popular local/self-hosted engines:

Supported services:
- vLLM: High-throughput inference engine
- llama.cpp server: Lightweight C++ implementation
- SGLang: Optimized for complex prompts
- TensorRT-LLM: NVIDIA GPU-optimized inference
- OpenLLM: Multi-model serving platform
- MLC LLM: Mobile and edge deployment
- Text Generation Inference (TGI): HuggingFace inference server
- Inferflow: High-performance inference

Key benefits:
- Single adapter works with 8+ inference engines
- Zero additional dependencies (uses existing openai SDK)
- Consistent API across local and cloud deployments
- Easy migration from OpenAI to self-hosted

Example:
    >>> from agenkit.adapters.llm import OpenAICompatibleLLM
    >>> from agenkit import Message
    >>>
    >>> # Connect to local vLLM server
    >>> llm = OpenAICompatibleLLM(
    ...     base_url="http://localhost:8000/v1",
    ...     model="meta-llama/Llama-2-7b-chat-hf",
    ...     provider="vllm"
    ... )
    >>>
    >>> messages = [Message(role="user", content="Hello!")]
    >>> response = await llm.complete(messages)
    >>> print(response.content)
"""

from collections.abc import AsyncIterator
from typing import Any

from agenkit.adapters.llm.base import LLM
from agenkit.interfaces import Message

try:
    from openai import AsyncOpenAI
except ImportError as e:
    raise ImportError(
        "The openai package is required to use OpenAICompatibleLLM. "
        "Install it with: pip install openai>=1.50.0"
    ) from e


class OpenAICompatibleLLM(LLM):
    """
    Generic adapter for OpenAI-compatible inference services.

    This adapter enables Agenkit to work with any service implementing the
    OpenAI Chat Completions API by wrapping the AsyncOpenAI SDK with a custom
    base_url parameter. This provides a consistent interface across different
    local and self-hosted inference engines.

    Args:
        base_url: Base URL of the inference service (e.g., "http://localhost:8000/v1").
            Must include the /v1 suffix for most services.
        model: Model name/identifier used by the inference service. Format varies
            by service (e.g., "meta-llama/Llama-2-7b-chat-hf" for vLLM,
            "llama-2-7b-chat" for llama.cpp).
        api_key: Optional API key. Most local services don't require authentication,
            so this defaults to "not-needed" if not provided.
        provider: Optional provider name for metadata and debugging (e.g., "vllm",
            "llamacpp", "sglang"). Helps identify which service is being used.
        timeout: Request timeout in seconds (default: 60.0). Increase for larger
            models or slower hardware.
        **client_kwargs: Additional arguments passed to AsyncOpenAI client for
            advanced configuration (e.g., max_retries, http_client).

    Raises:
        ImportError: If openai package is not installed

    Example - vLLM local deployment:
        >>> llm = OpenAICompatibleLLM(
        ...     base_url="http://localhost:8000/v1",
        ...     model="meta-llama/Llama-2-7b-chat-hf",
        ...     provider="vllm"
        ... )
        >>> response = await llm.complete([
        ...     Message(role="user", content="What is machine learning?")
        ... ])

    Example - llama.cpp server:
        >>> llm = OpenAICompatibleLLM(
        ...     base_url="http://localhost:8080/v1",
        ...     model="llama-2-7b-chat",
        ...     provider="llamacpp"
        ... )

    Example - SGLang with custom timeout:
        >>> llm = OpenAICompatibleLLM(
        ...     base_url="http://localhost:30000/v1",
        ...     model="meta-llama/Llama-2-13b-chat-hf",
        ...     provider="sglang",
        ...     timeout=120.0  # Larger model needs more time
        ... )

    Example - TensorRT-LLM with API key:
        >>> llm = OpenAICompatibleLLM(
        ...     base_url="https://api.example.com/v1",
        ...     model="llama-2-70b",
        ...     api_key="your-api-key",
        ...     provider="tensorrt"
        ... )

    Note:
        The response metadata includes both the provider name and base_url
        to help with debugging and monitoring in production deployments.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        provider: str | None = None,
        timeout: float = 60.0,
        **client_kwargs: Any,
    ) -> None:
        """Initialize OpenAI-compatible LLM adapter."""
        # Many local services don't require authentication
        if api_key is None:
            api_key = "not-needed"

        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            **client_kwargs,
        )
        self._model = model
        self._provider = provider
        self._base_url = base_url

    @property
    def model(self) -> str:
        """Return the model identifier."""
        return self._model

    async def complete(
        self,
        messages: list[Message],
        temperature: float = 1.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> Message:
        """
        Generate a completion from the OpenAI-compatible service.

        Args:
            messages: Conversation history as Agenkit Messages
            temperature: Sampling temperature (0.0-2.0). Lower values make output
                more deterministic, higher values more creative.
            max_tokens: Maximum tokens to generate. None uses service default.
            **kwargs: Additional service-specific options (top_p, frequency_penalty,
                presence_penalty, stop, etc.). Passed directly to the service.

        Returns:
            Response as Agenkit Message with metadata including:
            - model: Model identifier used
            - usage: Token counts (prompt_tokens, completion_tokens, total_tokens)
            - finish_reason: Why generation stopped (stop, length, etc.)
            - provider: Provider name if specified during initialization
            - base_url: Service URL for debugging
            - id: Response ID from the service

        Raises:
            openai.APIError: For service-specific errors (connection, timeout, etc.)

        Example:
            >>> messages = [
            ...     Message(role="system", content="You are a helpful assistant."),
            ...     Message(role="user", content="What is 2+2?")
            ... ]
            >>> response = await llm.complete(messages, temperature=0.2)
            >>> print(response.content)
            >>> print(f"Tokens used: {response.metadata['usage']['total_tokens']}")
            >>> print(f"Provider: {response.metadata['provider']}")

        Example - streaming alternative:
            >>> # For real-time responses, use stream() instead
            >>> async for chunk in llm.stream(messages):
            ...     print(chunk.content, end="", flush=True)
        """
        # Convert Agenkit Messages to OpenAI format
        openai_messages = self._convert_messages(messages)

        # Call OpenAI-compatible API
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        # Convert response to Agenkit Message with provider metadata
        return Message(
            role="agent",
            content=response.choices[0].message.content or "",
            metadata={
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                "finish_reason": response.choices[0].finish_reason,
                "provider": self._provider or "openai_compatible",
                "base_url": self._base_url,
                "id": response.id,
            },
        )

    async def stream(
        self,
        messages: list[Message],
        temperature: float = 1.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Message]:
        """
        Stream completion chunks from the OpenAI-compatible service.

        This method streams response chunks as they're generated by the service,
        enabling real-time display and lower perceived latency for users.

        Args:
            messages: Conversation history as Agenkit Messages
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional service-specific options

        Yields:
            Message chunks as they arrive from the service. Each chunk contains:
            - role: "agent"
            - content: Partial text (may be a single token or character)
            - metadata: {"streaming": True, "model": model_name, "provider": provider_name}

        Raises:
            openai.APIError: For service-specific errors

        Example:
            >>> messages = [Message(role="user", content="Count to 10")]
            >>> async for chunk in llm.stream(messages):
            ...     print(chunk.content, end="", flush=True)
            1, 2, 3, 4, 5, 6, 7, 8, 9, 10

        Example - accumulate full response:
            >>> chunks = []
            >>> async for chunk in llm.stream(messages):
            ...     chunks.append(chunk.content)
            >>> full_response = "".join(chunks)

        Note:
            Not all OpenAI-compatible services support streaming. If the service
            doesn't support it, you'll get an error from the underlying service.
        """
        # Convert messages
        openai_messages = self._convert_messages(messages)

        # Stream from OpenAI-compatible API
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )

        async for chunk in stream:
            # Extract content from delta
            delta = chunk.choices[0].delta
            if delta.content:
                yield Message(
                    role="agent",
                    content=delta.content,
                    metadata={
                        "streaming": True,
                        "model": self._model,
                        "provider": self._provider or "openai_compatible",
                    },
                )

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        """
        Convert Agenkit Messages to OpenAI format.

        OpenAI-compatible services expect messages in the format:
        - role: "system", "user", or "assistant"
        - content: str

        Agenkit uses "agent" role which gets mapped to "assistant" for compatibility.

        Args:
            messages: List of Agenkit Messages

        Returns:
            List of message dicts in OpenAI format

        Note:
            The "tool" role is preserved as-is since many services support it.
        """
        openai_messages = []
        for msg in messages:
            # Map roles for OpenAI compatibility
            if msg.role in ("system", "user", "tool"):
                role = msg.role
            else:
                # Map "agent" and others to "assistant"
                role = "assistant"

            openai_messages.append({"role": role, "content": str(msg.content)})

        return openai_messages

    def unwrap(self) -> AsyncOpenAI:
        """
        Get the underlying AsyncOpenAI client.

        This provides an escape hatch for accessing OpenAI-specific features
        not exposed by the minimal LLM interface. Useful for advanced use cases
        like custom request handling or service-specific features.

        Returns:
            The AsyncOpenAI client configured with custom base_url

        Example:
            >>> llm = OpenAICompatibleLLM(
            ...     base_url="http://localhost:8000/v1",
            ...     model="llama-2-7b"
            ... )
            >>> client = llm.unwrap()
            >>> # Use OpenAI SDK features directly
            >>> response = await client.chat.completions.create(
            ...     model="llama-2-7b",
            ...     messages=[{"role": "user", "content": "Hello"}],
            ...     stream=True
            ... )

        Warning:
            Using unwrap() breaks provider portability. Code that uses unwrap()
            will need changes when switching between services or providers.
        """
        return self._client

"""
Google Gemini adapter for Agenkit.

This module provides an adapter for Google's Gemini models using the
official google-genai Python SDK.
"""

from collections.abc import AsyncIterator
from typing import Any

from agenkit.adapters.llm.base import LLM
from agenkit.interfaces import Message

try:
    from google import genai
    from google.genai import types
except ImportError as e:
    raise ImportError(
        "The google-genai package is required to use GeminiLLM. "
        "Install it with: pip install google-genai>=0.3.0"
    ) from e


class GeminiLLM(LLM):
    """
    Google Gemini adapter.

    Wraps the official Google GenAI SDK to provide a consistent Agenkit interface
    for Gemini models. Supports both completion and streaming.

    Args:
        api_key: Google API key. If not provided, will use GEMINI_API_KEY or
            GOOGLE_API_KEY environment variable.
        model: Model identifier (default: gemini-2.0-flash-exp)
        **client_kwargs: Additional arguments passed to genai.Client

    Example:
        >>> from agenkit.adapters.llm import GeminiLLM
        >>> from agenkit import Message
        >>>
        >>> llm = GeminiLLM(api_key="...")
        >>> messages = [Message(role="user", content="Hello!")]
        >>> response = await llm.complete(messages)
        >>> print(response.content)

    Streaming example:
        >>> async for chunk in llm.stream(messages):
        ...     print(chunk.content, end="", flush=True)

    Provider-specific options:
        >>> response = await llm.complete(
        ...     messages,
        ...     temperature=0.7,
        ...     max_tokens=1024,
        ...     top_p=0.9,
        ...     top_k=40
        ... )
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-2.0-flash-exp",
        **client_kwargs: Any,
    ):
        """Initialize Gemini LLM adapter."""
        # Initialize client with API key if provided
        if api_key:
            client_kwargs["api_key"] = api_key
        self._client = genai.Client(**client_kwargs)
        self._model = model

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
        Generate a completion from Gemini.

        Args:
            messages: Conversation history as Agenkit Messages
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate (None for model default)
            **kwargs: Additional Gemini API options (top_p, top_k, etc.)

        Returns:
            Response as Agenkit Message with metadata including:
            - model: Model used
            - usage: Token counts if available
            - finish_reason: Why generation stopped

        Example:
            >>> messages = [
            ...     Message(role="system", content="You are a helpful assistant."),
            ...     Message(role="user", content="What is 2+2?")
            ... ]
            >>> response = await llm.complete(messages, temperature=0.2)
            >>> print(response.content)
            >>> print(response.metadata.get("usage"))
        """
        # Convert Agenkit Messages to Gemini format
        gemini_messages = self._convert_messages(messages)

        # Build config
        config = self._build_config(temperature, max_tokens, kwargs)

        # Call Gemini API
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=gemini_messages,
            config=config,
        )

        # Build metadata
        metadata: dict[str, Any] = {
            "model": self._model,
        }

        # Add usage if available
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            metadata["usage"] = {
                "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                "completion_tokens": getattr(
                    response.usage_metadata, "candidates_token_count", 0
                ),
                "total_tokens": getattr(response.usage_metadata, "total_token_count", 0),
            }

        # Add finish reason if available
        if (
            hasattr(response, "candidates")
            and response.candidates
            and hasattr(response.candidates[0], "finish_reason")
        ):
            metadata["finish_reason"] = str(response.candidates[0].finish_reason)

        # Convert response to Agenkit Message
        return Message(
            role="agent",
            content=response.text or "",
            metadata=metadata,
        )

    async def stream(
        self,
        messages: list[Message],
        temperature: float = 1.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Message]:
        """
        Stream completion chunks from Gemini.

        Args:
            messages: Conversation history as Agenkit Messages
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Gemini API options

        Yields:
            Message chunks as they arrive from Gemini

        Example:
            >>> messages = [Message(role="user", content="Count to 10")]
            >>> async for chunk in llm.stream(messages):
            ...     print(chunk.content, end="", flush=True)
        """
        # Convert messages
        gemini_messages = self._convert_messages(messages)

        # Build config
        config = self._build_config(temperature, max_tokens, kwargs)

        # Stream from Gemini API
        async for chunk in await self._client.aio.models.generate_content_stream(
            model=self._model,
            contents=gemini_messages,
            config=config,
        ):
            # Extract content from chunk
            if hasattr(chunk, "text") and chunk.text:
                yield Message(
                    role="agent",
                    content=chunk.text,
                    metadata={"streaming": True, "model": self._model},
                )

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """
        Convert Agenkit Messages to Gemini format.

        Gemini expects:
        - role: "user" or "model"
        - parts: list of content parts

        System messages are converted to user messages with special formatting.
        """
        gemini_messages = []

        for msg in messages:
            # Map roles
            if msg.role == "user":
                role = "user"
            elif msg.role == "system":
                # Gemini doesn't have system role - prepend to first user message
                # or convert to user message
                role = "user"
            else:
                # Map "agent" and others to "model"
                role = "model"

            gemini_messages.append({"role": role, "parts": [{"text": str(msg.content)}]})

        return gemini_messages

    def _build_config(
        self, temperature: float, max_tokens: int | None, kwargs: dict[str, Any]
    ) -> types.GenerateContentConfig:
        """Build Gemini generation config."""
        config_params: dict[str, Any] = {
            "temperature": temperature,
        }

        # Add max_tokens if specified
        if max_tokens is not None:
            config_params["max_output_tokens"] = max_tokens

        # Merge additional kwargs
        config_params.update(kwargs)

        return types.GenerateContentConfig(**config_params)

    def unwrap(self) -> genai.Client:
        """
        Get the underlying Gemini client.

        Returns:
            The genai.Client for direct API access

        Example:
            >>> llm = GeminiLLM()
            >>> client = llm.unwrap()
            >>> # Use Gemini-specific features
            >>> response = await client.aio.models.generate_content(...)
        """
        return self._client

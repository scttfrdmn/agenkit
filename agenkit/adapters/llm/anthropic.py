"""
Anthropic Claude adapter for Agenkit.

This module provides an adapter for Anthropic's Claude models using the
official anthropic Python SDK.
"""

from collections.abc import AsyncIterator
from typing import Any

from agenkit.adapters.llm.base import LLM
from agenkit.interfaces import Message

try:
    from anthropic import AsyncAnthropic
except ImportError as e:
    raise ImportError(
        "The anthropic package is required to use AnthropicLLM. "
        "Install it with: pip install anthropic>=0.40.0"
    ) from e


class AnthropicLLM(LLM):
    """
    Anthropic Claude adapter.

    Wraps the official Anthropic SDK to provide a consistent Agenkit interface
    for Claude models. Supports both completion and streaming.

    Args:
        api_key: Anthropic API key. If not provided, will use ANTHROPIC_API_KEY
            environment variable.
        model: Model identifier (default: claude-3-5-sonnet-20241022)
        **client_kwargs: Additional arguments passed to AsyncAnthropic client

    Example:
        >>> from agenkit.adapters.llm import AnthropicLLM
        >>> from agenkit import Message
        >>>
        >>> llm = AnthropicLLM(api_key="...")
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
        ...     stop_sequences=["Human:", "Assistant:"]
        ... )
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-3-5-sonnet-20241022",
        **client_kwargs: Any,
    ):
        """Initialize Anthropic LLM adapter."""
        self._client = AsyncAnthropic(api_key=api_key, **client_kwargs)
        self._model = model

    @property
    def model(self) -> str:
        """Return the model identifier."""
        return self._model

    async def complete(
        self,
        messages: list[Message],
        temperature: float = 1.0,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> Message:
        """
        Generate a completion from Claude.

        Args:
            messages: Conversation history as Agenkit Messages
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Anthropic API options (top_p, top_k, stop_sequences, etc.)

        Returns:
            Response as Agenkit Message with metadata including:
            - model: Model used
            - usage: Input and output token counts
            - stop_reason: Why generation stopped

        Example:
            >>> messages = [
            ...     Message(role="system", content="You are a helpful assistant."),
            ...     Message(role="user", content="What is 2+2?")
            ... ]
            >>> response = await llm.complete(messages, temperature=0.2)
            >>> print(response.content)
            >>> print(response.metadata["usage"])
        """
        # Convert Agenkit Messages to Anthropic format
        anthropic_messages = self._convert_messages(messages)

        # Extract system message if present
        system_message = self._extract_system_message(messages)

        # Call Anthropic API
        response = await self._client.messages.create(
            model=self._model,
            messages=anthropic_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            system=system_message or "",
            **kwargs,
        )

        # Convert response to Agenkit Message
        return Message(
            role="agent",
            content=response.content[0].text,
            metadata={
                "model": self._model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                "stop_reason": response.stop_reason,
                "id": response.id,
            },
        )

    async def stream(
        self,
        messages: list[Message],
        temperature: float = 1.0,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[Message]:
        """
        Stream completion chunks from Claude.

        Args:
            messages: Conversation history as Agenkit Messages
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Anthropic API options

        Yields:
            Message chunks as they arrive from Claude

        Example:
            >>> messages = [Message(role="user", content="Count to 10")]
            >>> async for chunk in llm.stream(messages):
            ...     print(chunk.content, end="", flush=True)
        """
        # Convert messages
        anthropic_messages = self._convert_messages(messages)
        system_message = self._extract_system_message(messages)

        # Stream from Anthropic API
        async with self._client.messages.stream(
            model=self._model,
            messages=anthropic_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            system=system_message or "",
            **kwargs,
        ) as stream:
            async for chunk in stream.text_stream:
                yield Message(
                    role="agent",
                    content=chunk,
                    metadata={"streaming": True, "model": self._model},
                )

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        """
        Convert Agenkit Messages to Anthropic format.

        Anthropic expects:
        - role: "user" or "assistant"
        - content: str

        System messages are handled separately via the system parameter.
        """
        anthropic_messages = []
        for msg in messages:
            # Skip system messages (handled separately)
            if msg.role == "system":
                continue

            # Map roles
            role = "user" if msg.role == "user" else "assistant"

            anthropic_messages.append(
                {"role": role, "content": str(msg.content)}
            )

        return anthropic_messages

    def _extract_system_message(self, messages: list[Message]) -> str | None:
        """
        Extract system message content if present.

        Anthropic handles system messages separately from the conversation.
        """
        for msg in messages:
            if msg.role == "system":
                return str(msg.content)
        return None

    def unwrap(self) -> AsyncAnthropic:
        """
        Get the underlying Anthropic client.

        Returns:
            The AsyncAnthropic client for direct API access

        Example:
            >>> llm = AnthropicLLM()
            >>> client = llm.unwrap()
            >>> # Use Anthropic-specific features
            >>> response = await client.messages.create(...)
        """
        return self._client

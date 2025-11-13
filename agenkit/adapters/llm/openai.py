"""
OpenAI GPT adapter for Agenkit.

This module provides an adapter for OpenAI's GPT models using the
official openai Python SDK.
"""

from collections.abc import AsyncIterator
from typing import Any

from agenkit.adapters.llm.base import LLM
from agenkit.interfaces import Message

try:
    from openai import AsyncOpenAI
except ImportError as e:
    raise ImportError(
        "The openai package is required to use OpenAILLM. "
        "Install it with: pip install openai>=1.50.0"
    ) from e


class OpenAILLM(LLM):
    """
    OpenAI GPT adapter.

    Wraps the official OpenAI SDK to provide a consistent Agenkit interface
    for GPT models. Supports both completion and streaming.

    Args:
        api_key: OpenAI API key. If not provided, will use OPENAI_API_KEY
            environment variable.
        model: Model identifier (default: gpt-4-turbo)
        **client_kwargs: Additional arguments passed to AsyncOpenAI client

    Example:
        >>> from agenkit.adapters.llm import OpenAILLM
        >>> from agenkit import Message
        >>>
        >>> llm = OpenAILLM(api_key="...")
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
        ...     frequency_penalty=0.5,
        ...     presence_penalty=0.5
        ... )
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4-turbo",
        **client_kwargs: Any,
    ):
        """Initialize OpenAI LLM adapter."""
        self._client = AsyncOpenAI(api_key=api_key, **client_kwargs)
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
        Generate a completion from GPT.

        Args:
            messages: Conversation history as Agenkit Messages
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate (None for model default)
            **kwargs: Additional OpenAI API options (top_p, frequency_penalty,
                presence_penalty, stop, etc.)

        Returns:
            Response as Agenkit Message with metadata including:
            - model: Model used
            - usage: Token counts (prompt, completion, total)
            - finish_reason: Why generation stopped

        Example:
            >>> messages = [
            ...     Message(role="system", content="You are a helpful assistant."),
            ...     Message(role="user", content="What is 2+2?")
            ... ]
            >>> response = await llm.complete(messages, temperature=0.2)
            >>> print(response.content)
            >>> print(response.metadata["usage"])
        """
        # Convert Agenkit Messages to OpenAI format
        openai_messages = self._convert_messages(messages)

        # Call OpenAI API
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        # Convert response to Agenkit Message
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
        Stream completion chunks from GPT.

        Args:
            messages: Conversation history as Agenkit Messages
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI API options

        Yields:
            Message chunks as they arrive from GPT

        Example:
            >>> messages = [Message(role="user", content="Count to 10")]
            >>> async for chunk in llm.stream(messages):
            ...     print(chunk.content, end="", flush=True)
        """
        # Convert messages
        openai_messages = self._convert_messages(messages)

        # Stream from OpenAI API
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
                    metadata={"streaming": True, "model": self._model},
                )

    def _convert_messages(
        self, messages: list[Message]
    ) -> list[dict[str, str]]:
        """
        Convert Agenkit Messages to OpenAI format.

        OpenAI expects:
        - role: "system", "user", "assistant", or "tool"
        - content: str
        """
        openai_messages = []
        for msg in messages:
            # Map roles
            if msg.role in ("system", "user", "tool"):
                role = msg.role
            else:
                # Map "agent" and others to "assistant"
                role = "assistant"

            openai_messages.append(
                {"role": role, "content": str(msg.content)}
            )

        return openai_messages

    def unwrap(self) -> AsyncOpenAI:
        """
        Get the underlying OpenAI client.

        Returns:
            The AsyncOpenAI client for direct API access

        Example:
            >>> llm = OpenAILLM()
            >>> client = llm.unwrap()
            >>> # Use OpenAI-specific features
            >>> response = await client.chat.completions.create(...)
        """
        return self._client

"""
Base LLM interface for Agenkit.

This module defines the minimal contract that all LLM adapters must implement.
The interface is intentionally small to maximize flexibility while ensuring
consistency across providers.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from agenkit.interfaces import Message


class LLM(ABC):
    """
    Minimal LLM interface for agent-LLM interaction.

    This interface provides a consistent way to interact with any LLM provider,
    whether commercial (Anthropic, OpenAI, etc.) or local (Ollama, llama.cpp).

    Design principles:
    - **Minimal**: Only 2 required methods (complete, stream)
    - **Flexible**: Accepts **kwargs for provider-specific options
    - **Consistent**: Works with Agenkit Message interface
    - **Swappable**: Change providers without changing agent code
    - **Escape hatch**: unwrap() for advanced provider features

    The interface is intentionally NOT a full-featured LLM client. It focuses
    on the minimal contract needed for agent-LLM interaction, leaving advanced
    features to provider-specific implementations accessible via unwrap().

    Example:
        >>> from agenkit.adapters.llm import AnthropicLLM
        >>> from agenkit import Message
        >>>
        >>> llm = AnthropicLLM(api_key="...")
        >>> messages = [
        ...     Message(role="system", content="You are helpful."),
        ...     Message(role="user", content="Hello!")
        ... ]
        >>> response = await llm.complete(messages, temperature=0.7)
        >>> print(response.content)

    Swapping providers:
        >>> # Same code, different provider
        >>> llm = OpenAILLM(api_key="...")
        >>> response = await llm.complete(messages, temperature=0.7)

    Streaming:
        >>> async for chunk in llm.stream(messages):
        ...     print(chunk.content, end="", flush=True)
    """

    @abstractmethod
    async def complete(
        self, messages: list[Message], **kwargs: Any
    ) -> Message:
        """
        Generate a single completion from the LLM.

        This method sends a list of messages to the LLM and returns a single
        response message. The conversation history is passed as a list of
        Agenkit Messages, which the adapter converts to the provider's format.

        Args:
            messages: Conversation history as Agenkit Messages. Typically includes
                system messages, user messages, and agent responses.
            **kwargs: Provider-specific options (e.g., temperature, max_tokens,
                top_p, etc.). These are passed directly to the provider's API.

        Returns:
            Response from the LLM as an Agenkit Message. The Message will have:
            - role: "agent"
            - content: The generated text
            - metadata: Provider-specific data (usage stats, model name, etc.)

        Raises:
            Provider-specific exceptions for API errors (auth, rate limits, etc.).
            Adapters should let these propagate rather than catching and wrapping.

        Example:
            >>> messages = [
            ...     Message(role="system", content="You are a coding assistant."),
            ...     Message(role="user", content="Write a Python hello world.")
            ... ]
            >>> response = await llm.complete(
            ...     messages,
            ...     temperature=0.2,  # Lower temp for code
            ...     max_tokens=1024
            ... )
            >>> print(response.content)
            print("Hello, World!")
        """
        pass

    @abstractmethod
    async def stream(
        self, messages: list[Message], **kwargs: Any
    ) -> AsyncIterator[Message]:
        """
        Stream completion chunks from the LLM.

        This method sends messages to the LLM and streams back response chunks
        as they're generated. Each chunk is yielded as an Agenkit Message.

        Args:
            messages: Conversation history as Agenkit Messages
            **kwargs: Provider-specific options

        Yields:
            Message chunks as they arrive from the LLM. Each chunk contains:
            - role: "agent"
            - content: Partial text (may be a single token or character)
            - metadata: {"streaming": True, ...}

        Raises:
            Provider-specific exceptions for API errors

        Example:
            >>> messages = [Message(role="user", content="Count to 10")]
            >>> async for chunk in llm.stream(messages):
            ...     print(chunk.content, end="", flush=True)
            1, 2, 3, 4, 5, 6, 7, 8, 9, 10

        Note:
            This method must be an async generator. If streaming is not supported,
            raise NotImplementedError rather than falling back to complete().
        """
        # Make this an async generator (required for type checking)
        if False:
            yield  # type: ignore[unreachable]
        raise NotImplementedError(f"{self.__class__.__name__} does not support streaming")

    @property
    def model(self) -> str:
        """
        Model identifier for this LLM instance.

        Returns:
            Model name/identifier (e.g., "claude-3-5-sonnet-20241022", "gpt-4-turbo")

        Example:
            >>> llm = AnthropicLLM(model="claude-3-5-sonnet-20241022")
            >>> print(llm.model)
            claude-3-5-sonnet-20241022
        """
        return "unknown"

    def unwrap(self) -> Any:
        """
        Get the underlying provider client for advanced features.

        This is an escape hatch that allows access to provider-specific features
        not exposed by the minimal LLM interface. Use this when you need
        capabilities beyond complete() and stream().

        Returns:
            The native provider client (anthropic.Anthropic, openai.OpenAI, etc.)

        Example:
            >>> llm = AnthropicLLM()
            >>> native_client = llm.unwrap()
            >>> # Now use Anthropic-specific features
            >>> response = await native_client.messages.create(...)

        Warning:
            Using unwrap() breaks provider portability. Code that uses unwrap()
            will need changes when switching providers.
        """
        return self

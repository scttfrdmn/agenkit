"""
LiteLLM adapter for Agenkit.

This module provides an adapter for LiteLLM, which supports 100+ LLM providers
through a unified interface.
"""

from collections.abc import AsyncIterator
from typing import Any

from agenkit.adapters.llm.base import LLM
from agenkit.interfaces import Message

try:
    import litellm
except ImportError as e:
    raise ImportError(
        "The litellm package is required to use LiteLLMLLM. "
        "Install it with: pip install litellm>=1.50.0"
    ) from e


class LiteLLMLLM(LLM):
    """
    LiteLLM adapter - supports 100+ providers.

    Wraps the LiteLLM library to provide access to any LLM provider through
    a consistent Agenkit interface. LiteLLM handles routing to the correct
    provider based on the model string.

    Supported providers include:
    - OpenAI (gpt-4, gpt-3.5-turbo)
    - Anthropic (claude-3-5-sonnet-20241022)
    - AWS Bedrock (bedrock/anthropic.claude-v2)
    - Google Gemini (gemini/gemini-pro)
    - Azure OpenAI (azure/gpt-4)
    - Cohere (command-r-plus)
    - Local models (ollama/llama2, ollama/mistral)
    - And 100+ more!

    Args:
        model: Model identifier in LiteLLM format. Examples:
            - "gpt-4" - OpenAI GPT-4
            - "claude-3-5-sonnet-20241022" - Anthropic Claude
            - "bedrock/anthropic.claude-v2" - AWS Bedrock
            - "gemini/gemini-pro" - Google Gemini
            - "ollama/llama2" - Local Ollama
        **kwargs: Configuration passed to all LiteLLM calls

    Example:
        >>> from agenkit.adapters.llm import LiteLLMLLM
        >>> from agenkit import Message
        >>>
        >>> # OpenAI
        >>> llm = LiteLLMLLM(model="gpt-4")
        >>>
        >>> # Anthropic
        >>> llm = LiteLLMLLM(model="claude-3-5-sonnet-20241022")
        >>>
        >>> # AWS Bedrock
        >>> llm = LiteLLMLLM(model="bedrock/anthropic.claude-v2")
        >>>
        >>> # Local Ollama
        >>> llm = LiteLLMLLM(model="ollama/llama2")
        >>>
        >>> messages = [Message(role="user", content="Hello!")]
        >>> response = await llm.complete(messages)

    Provider-specific configuration:
        >>> # Configure API keys, base URLs, etc.
        >>> llm = LiteLLMLLM(
        ...     model="gpt-4",
        ...     api_key="...",
        ...     api_base="...",
        ...     timeout=30
        ... )

    See: https://docs.litellm.ai/docs/providers for full provider list
    """

    def __init__(self, model: str, **kwargs: Any):
        """
        Initialize LiteLLM adapter.

        Args:
            model: Model identifier (e.g., "gpt-4", "claude-3-5-sonnet-20241022")
            **kwargs: Configuration for LiteLLM (api_key, api_base, etc.)
        """
        self._model = model
        self._config = kwargs

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
        Generate a completion via LiteLLM.

        LiteLLM automatically routes to the correct provider based on the
        model string.

        Args:
            messages: Conversation history as Agenkit Messages
            temperature: Sampling temperature (provider-dependent range)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific options

        Returns:
            Response as Agenkit Message with metadata including:
            - model: Model used (may differ from requested)
            - usage: Token counts (if provided by provider)

        Example:
            >>> messages = [Message(role="user", content="What is 2+2?")]
            >>> response = await llm.complete(messages, temperature=0.2)
            >>> print(response.content)
        """
        # Convert Agenkit Messages to LiteLLM format
        litellm_messages = self._convert_messages(messages)

        # Merge config and call-specific kwargs
        call_kwargs = {**self._config, **kwargs}
        if max_tokens is not None:
            call_kwargs["max_tokens"] = max_tokens

        # Call LiteLLM (handles routing to correct provider)
        response = await litellm.acompletion(
            model=self._model,
            messages=litellm_messages,
            temperature=temperature,
            **call_kwargs,
        )

        # Build metadata
        metadata: dict[str, Any] = {
            "model": response.model,
        }

        # Add usage if available
        if hasattr(response, "usage") and response.usage:
            metadata["usage"] = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0),
            }

        # Convert response to Agenkit Message
        return Message(
            role="agent",
            content=response.choices[0].message.content or "",
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
        Stream completion chunks via LiteLLM.

        Args:
            messages: Conversation history as Agenkit Messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific options

        Yields:
            Message chunks as they arrive

        Example:
            >>> messages = [Message(role="user", content="Count to 10")]
            >>> async for chunk in llm.stream(messages):
            ...     print(chunk.content, end="", flush=True)
        """
        # Convert messages
        litellm_messages = self._convert_messages(messages)

        # Merge config and call-specific kwargs
        call_kwargs = {**self._config, **kwargs}
        if max_tokens is not None:
            call_kwargs["max_tokens"] = max_tokens

        # Stream from LiteLLM
        response = await litellm.acompletion(
            model=self._model,
            messages=litellm_messages,
            temperature=temperature,
            stream=True,
            **call_kwargs,
        )

        async for chunk in response:
            # Extract content from delta
            if hasattr(chunk.choices[0], "delta") and chunk.choices[0].delta.content:
                yield Message(
                    role="agent",
                    content=chunk.choices[0].delta.content,
                    metadata={"streaming": True, "model": self._model},
                )

    def _convert_messages(
        self, messages: list[Message]
    ) -> list[dict[str, str]]:
        """
        Convert Agenkit Messages to LiteLLM format.

        LiteLLM uses OpenAI-style message format:
        - role: "system", "user", "assistant"
        - content: str
        """
        litellm_messages = []
        for msg in messages:
            # Map roles to OpenAI-style
            if msg.role in ("system", "user"):
                role = msg.role
            else:
                # Map "agent" and others to "assistant"
                role = "assistant"

            litellm_messages.append(
                {"role": role, "content": str(msg.content)}
            )

        return litellm_messages

    def unwrap(self) -> None:
        """
        LiteLLM doesn't have a client object to unwrap.

        Returns:
            None - LiteLLM is a functional API, not a client

        Note:
            To use LiteLLM directly, import and use litellm.acompletion()
        """
        return None

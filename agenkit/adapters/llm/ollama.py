"""
Ollama adapter for Agenkit.

This module provides an adapter for Ollama, the popular local LLM tool.
Supports running models locally for development, testing, and on-premises deployments.
"""

from collections.abc import AsyncIterator
from typing import Any

from agenkit.adapters.llm.base import LLM
from agenkit.interfaces import Message

try:
    from ollama import AsyncClient
except ImportError as e:
    raise ImportError(
        "The ollama package is required to use OllamaLLM. "
        "Install it with: pip install ollama>=0.1.0"
    ) from e


class OllamaLLM(LLM):
    """
    Ollama adapter for local LLM inference.

    Wraps the Ollama Python SDK to provide local model access through the
    Agenkit interface. Ideal for development, testing, and on-premises deployments.

    Args:
        model: Model identifier (e.g., "llama2", "mistral", "codellama")
        base_url: Ollama server URL (default: http://localhost:11434)
        **client_kwargs: Additional arguments passed to AsyncClient

    Example:
        >>> from agenkit.adapters.llm import OllamaLLM
        >>> from agenkit import Message
        >>>
        >>> # Basic usage (assumes Ollama running locally)
        >>> llm = OllamaLLM(model="llama2")
        >>> messages = [Message(role="user", content="Hello!")]
        >>> response = await llm.complete(messages)
        >>> print(response.content)

    Remote Ollama server:
        >>> llm = OllamaLLM(
        ...     model="mistral",
        ...     base_url="http://ollama-server:11434"
        ... )

    Streaming example:
        >>> async for chunk in llm.stream(messages):
        ...     print(chunk.content, end="", flush=True)

    Popular models:
        - llama2 - Meta's Llama 2 (7B, 13B, 70B)
        - llama3 - Meta's Llama 3
        - mistral - Mistral 7B
        - codellama - Code-focused Llama
        - phi - Microsoft's small efficient model
        - gemma - Google's open model
        - qwen - Alibaba's Qwen
        - neural-chat - Intel's fine-tuned model

    Setup:
        1. Install Ollama: https://ollama.ai/download
        2. Pull a model: `ollama pull llama2`
        3. Verify: `ollama list`
        4. Use with Agenkit!
    """

    def __init__(
        self,
        model: str = "llama2",
        base_url: str = "http://localhost:11434",
        **client_kwargs: Any,
    ):
        """Initialize Ollama LLM adapter."""
        self._model = model
        self._client = AsyncClient(host=base_url, **client_kwargs)

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
        Generate a completion from Ollama.

        Args:
            messages: Conversation history as Agenkit Messages
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate (None for model default)
            **kwargs: Additional Ollama options (top_p, top_k, etc.)

        Returns:
            Response as Agenkit Message with metadata including:
            - model: Model used
            - eval_count: Number of tokens in response
            - total_duration: Total inference time (ns)

        Example:
            >>> messages = [
            ...     Message(role="system", content="You are a helpful assistant."),
            ...     Message(role="user", content="What is 2+2?")
            ... ]
            >>> response = await llm.complete(messages, temperature=0.2)
            >>> print(response.content)
        """
        # Convert Agenkit Messages to Ollama format
        ollama_messages = self._convert_messages(messages)

        # Build options
        options: dict[str, Any] = {
            "temperature": temperature,
        }

        # Add num_predict (Ollama's max_tokens)
        if max_tokens is not None:
            options["num_predict"] = max_tokens

        # Merge additional kwargs
        options.update(kwargs)

        # Call Ollama API
        response = await self._client.chat(
            model=self._model,
            messages=ollama_messages,
            options=options,
        )

        # Build metadata
        metadata: dict[str, Any] = {
            "model": response.get("model", self._model),
        }

        # Add performance metrics if available
        if "eval_count" in response:
            metadata["eval_count"] = response["eval_count"]
        if "total_duration" in response:
            metadata["total_duration"] = response["total_duration"]
        if "load_duration" in response:
            metadata["load_duration"] = response["load_duration"]

        # Extract message content
        message_content = response.get("message", {})
        content = message_content.get("content", "")

        # Convert response to Agenkit Message
        return Message(
            role="agent",
            content=content,
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
        Stream completion chunks from Ollama.

        Args:
            messages: Conversation history as Agenkit Messages
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Ollama options

        Yields:
            Message chunks as they arrive from Ollama

        Example:
            >>> messages = [Message(role="user", content="Count to 10")]
            >>> async for chunk in llm.stream(messages):
            ...     print(chunk.content, end="", flush=True)
        """
        # Convert messages
        ollama_messages = self._convert_messages(messages)

        # Build options
        options: dict[str, Any] = {
            "temperature": temperature,
        }

        if max_tokens is not None:
            options["num_predict"] = max_tokens

        options.update(kwargs)

        # Stream from Ollama API
        async for chunk in await self._client.chat(
            model=self._model,
            messages=ollama_messages,
            options=options,
            stream=True,
        ):
            # Extract content from chunk
            message_content = chunk.get("message", {})
            content = message_content.get("content", "")

            if content:
                yield Message(
                    role="agent",
                    content=content,
                    metadata={"streaming": True, "model": self._model},
                )

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        """
        Convert Agenkit Messages to Ollama format.

        Ollama expects:
        - role: "system", "user", or "assistant"
        - content: str
        """
        ollama_messages = []

        for msg in messages:
            # Map roles
            if msg.role in ("system", "user"):
                role = msg.role
            else:
                # Map "agent" and others to "assistant"
                role = "assistant"

            ollama_messages.append({"role": role, "content": str(msg.content)})

        return ollama_messages

    def unwrap(self) -> AsyncClient:
        """
        Get the underlying Ollama AsyncClient.

        Returns:
            The AsyncClient for direct API access

        Example:
            >>> llm = OllamaLLM()
            >>> client = llm.unwrap()
            >>> # Use Ollama-specific features
            >>> models = await client.list()
            >>> await client.pull("mistral")
        """
        return self._client

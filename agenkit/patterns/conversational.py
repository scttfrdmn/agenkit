"""
Conversational Agent Pattern

A conversational agent maintains context across multiple turns of conversation,
managing message history and ensuring responses take into account previous exchanges.

Key Features:
- Message history management
- Context window limiting
- Automatic history pruning
- Support for different history strategies
"""

import warnings
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from agenkit import Agent, CallOptions, Message
from agenkit._llm_protocol import can_carry_options, complete_messages, stream_messages


@runtime_checkable
class LLMClient(Protocol):
    """
    Protocol for LLM clients usable with :class:`ConversationalAgent`.

    Declares ``complete()`` — the :class:`~agenkit.adapters.llm.LLM` contract that
    every shipped adapter implements. Until v0.86.0 this protocol declared
    ``chat()`` instead, which **no** shipped adapter had, so
    :class:`ConversationalAgent` could not be used with any real LLM (#805).

    An :class:`~agenkit.Agent` (``process()``) is also accepted, so any agent — a
    reasoning technique, another pattern — can serve as a conversational backend.
    ``chat()`` is still accepted for one deprecation cycle and warns.

    Typed as a ``Protocol`` rather than an ABC because adapters must not be forced
    to inherit from a pattern module, and because the accepted set is deliberately
    wider than any single protocol can express.
    """

    async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
        """Generate a response given a conversation history."""
        ...


@dataclass
class ConversationalAgentConfig:
    """
    Configuration for ConversationalAgent.

    Use this class to configure ConversationalAgent in a way that is consistent
    across all languages in the agenkit toolkit.

    Example:
        ```python
        config = ConversationalAgentConfig(
            llm_client=llm,
            max_history=10,
            system_prompt="You are a helpful assistant.",
        )
        agent = ConversationalAgent(config)
        ```
    """

    llm_client: LLMClient
    max_history: int = 10
    system_prompt: str | None = None
    include_system: bool = True


class ConversationalAgent(Agent):
    """
    Agent that maintains conversation history for context-aware responses.

    This agent stores previous messages and includes them when processing new messages,
    allowing the LLM to maintain context across multiple turns.

    Recommended usage (config-based, matches all other languages):
        ```python
        from agenkit.patterns import ConversationalAgent, ConversationalAgentConfig
        from my_llm import MyLLMClient

        llm = MyLLMClient(model="gpt-4")
        config = ConversationalAgentConfig(
            llm_client=llm,
            max_history=10,
            system_prompt="You are a helpful assistant.",
        )
        agent = ConversationalAgent(config)
        ```

    Deprecated usage (direct kwargs, will be removed in v2.0):
        ```python
        agent = ConversationalAgent(
            llm_client=llm,
            max_history=10,
            system_prompt="You are a helpful assistant.",
        )
        ```

    Args:
        config: Configuration object (recommended, matches other languages)
        llm_client: (Deprecated) LLM client that implements the chat interface
        max_history: (Deprecated) Maximum number of messages to retain (default: 10)
        system_prompt: (Deprecated) Optional system prompt to prepend to conversations
        include_system: (Deprecated) Whether to include system prompt in history (default: True)
    """

    def __init__(
        self,
        config: ConversationalAgentConfig | None = None,
        *,
        llm_client: LLMClient | None = None,  # deprecated
        max_history: int = 10,  # deprecated
        system_prompt: str | None = None,  # deprecated
        include_system: bool = True,  # deprecated
    ):
        """
        Initialize ConversationalAgent.

        Args:
            config: Configuration object (recommended, matches all other languages)
            llm_client: (Deprecated) LLM client that implements the chat interface
            max_history: (Deprecated) Maximum number of messages to retain
            system_prompt: (Deprecated) Optional system prompt to prepend
            include_system: (Deprecated) Whether to include system prompt in history

        Examples:
            >>> # Recommended: config-based (matches all other languages)
            >>> config = ConversationalAgentConfig(llm_client=llm, max_history=20)
            >>> agent = ConversationalAgent(config)
            >>>
            >>> # Deprecated: direct parameters (will be removed in v2.0)
            >>> agent = ConversationalAgent(llm_client=llm, max_history=20)

        Migration:
            Old code:
                agent = ConversationalAgent(
                    llm_client=llm,
                    max_history=20,
                    system_prompt="You are helpful.",
                )

            New code:
                config = ConversationalAgentConfig(
                    llm_client=llm,
                    max_history=20,
                    system_prompt="You are helpful.",
                )
                agent = ConversationalAgent(config)
        """
        # Handle positional LLM client passed in the old style: ConversationalAgent(my_llm)
        if config is not None and not isinstance(config, ConversationalAgentConfig):
            llm_client = config  # type: ignore[assignment]
            config = None

        if config is not None:
            # New config-based API (recommended)
            self.llm = config.llm_client
            self.max_history = config.max_history
            self.system_prompt = config.system_prompt
            self.include_system = config.include_system
        elif llm_client is not None:
            # Old direct-parameter API (deprecated)
            warnings.warn(
                "Direct parameters for ConversationalAgent are deprecated and will be removed in v2.0. "
                "Use ConversationalAgentConfig instead: "
                "ConversationalAgent(ConversationalAgentConfig(llm_client=...)). "
                "See migration guide for details.",
                DeprecationWarning,
                stacklevel=2,
            )
            self.llm = llm_client
            self.max_history = max_history
            self.system_prompt = system_prompt
            self.include_system = include_system
        else:
            raise ValueError(
                "Either 'config' or 'llm_client' must be provided. "
                "Recommended: Use ConversationalAgentConfig for cross-language API consistency."
            )

        self.history: list[Message] = []

        # Add system prompt to history if provided
        if self.system_prompt and self.include_system:
            self.history.append(Message(role="system", content=self.system_prompt))

    @property
    def name(self) -> str:
        """Return the agent's name."""
        return "ConversationalAgent"

    @property
    def supports_options(self) -> bool:
        """
        Whether per-call options can reach the underlying LLM (#801).

        False for a ``chat()``-only client: the deprecated protocol has no parameter
        to carry them. Reported rather than silently ignored so a caller can tell
        the difference between "applied" and "accepted and dropped".
        """
        return can_carry_options(self.llm)

    async def process(self, message: Message) -> Message:
        """
        Process a message with full conversation context.

        Equivalent to :meth:`process_with` with no options set.

        Args:
            message: The incoming user message

        Returns:
            The agent's response message

        Note:
            Both the input message and the response are added to history.
            If history exceeds max_history, oldest non-system messages are removed.
        """
        return await self.process_with(message, CallOptions())

    async def process_with(self, message: Message, options: CallOptions) -> Message:
        """
        Process a message with full conversation context and per-call options.

        The message is added to history, and the LLM generates a response
        considering all previous messages within the history limit.

        Args:
            message: The incoming user message
            options: Per-call inference options forwarded to the LLM (#801).
                Check :attr:`supports_options` to know whether they can be applied.

        Returns:
            The agent's response message
        """
        # Add user message to history
        self.history.append(message)

        # Prune history if needed (keep system prompt if present)
        self._prune_history()

        # Generate response with full context. Dispatch is shared with the reasoning
        # techniques so a client that works with one works with the other (#805).
        response = await complete_messages(self.llm, self.history, options)

        # Add response to history
        self.history.append(response)

        # Prune again after adding response
        self._prune_history()

        return response

    def _prune_history(self) -> None:
        """
        Prune history to stay within max_history limit.

        System messages are preserved, and oldest user/assistant messages
        are removed first.
        """
        if len(self.history) <= self.max_history:
            return

        # Separate system messages from conversation
        system_messages = [msg for msg in self.history if msg.role == "system"]
        conversation_messages = [msg for msg in self.history if msg.role != "system"]

        # Keep only the most recent conversation messages
        messages_to_keep = self.max_history - len(system_messages)
        if messages_to_keep > 0:
            conversation_messages = conversation_messages[-messages_to_keep:]
        else:
            conversation_messages = []

        # Rebuild history with system messages first
        self.history = system_messages + conversation_messages

    def clear_history(self, keep_system: bool = True) -> None:
        """
        Clear conversation history.

        Args:
            keep_system: If True, preserves system prompt (default: True)
        """
        if keep_system and self.system_prompt and self.include_system:
            self.history = [Message(role="system", content=self.system_prompt)]
        else:
            self.history = []

    def get_history(self) -> list[Message]:
        """
        Get a copy of the current conversation history.

        Returns:
            List of messages in conversation history
        """
        return self.history.copy()

    def get_context_length(self) -> int:
        """
        Get the current number of messages in history.

        Returns:
            Number of messages in history
        """
        return len(self.history)

    def export_history(self) -> list[dict]:
        """
        Export history in a serializable format.

        Returns:
            List of message dictionaries
        """
        return [
            {"role": msg.role, "content": msg.content, "metadata": msg.metadata}
            for msg in self.history
        ]

    def import_history(self, history: list[dict]) -> None:
        """
        Import conversation history from serialized format.

        Useful for resuming conversations or testing.

        Args:
            history: List of message dictionaries with role and content
        """
        self.history = [
            Message(
                role=msg["role"],
                content=msg["content"],
                metadata=msg.get("metadata", {}),
            )
            for msg in history
        ]


class StreamingConversationalAgent(ConversationalAgent):
    """
    Conversational agent with streaming response support.

    Extends ConversationalAgent to support streaming responses from the LLM,
    useful for providing real-time feedback to users.

    Example:
        ```python
        agent = StreamingConversationalAgent(llm_client=llm)

        async for chunk in agent.stream(
            Message(role="user", content="Tell me a story")
        ):
            print(chunk.content, end="", flush=True)
        ```
    """

    async def stream(
        self, message: Message, options: CallOptions | None = None
    ) -> AsyncIterator[Message]:
        """
        Process message and stream response chunks.

        Args:
            message: The incoming user message
            options: Optional per-call inference options forwarded to the LLM (#801)

        Yields:
            Message chunks as they are generated

        Raises:
            AttributeError: If the client does not implement ``stream()``. Only the
                :class:`~agenkit.adapters.llm.LLM` contract declares it — a
                ``chat()``-only or ``process()``-only client cannot stream, and
                before #805 that failed with a bare missing-attribute error.

        Note:
            The complete response is added to history after streaming completes.
        """
        # Add user message to history
        self.history.append(message)
        self._prune_history()

        # Collect chunks for history
        response_chunks = []

        # Stream response
        async for chunk in stream_messages(self.llm, self.history, options):
            response_chunks.append(chunk)
            yield chunk

        # Combine chunks into full response
        full_content = "".join(chunk.content for chunk in response_chunks)
        full_response = Message(role="assistant", content=full_content)

        # Add to history
        self.history.append(full_response)
        self._prune_history()

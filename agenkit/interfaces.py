"""
Core interfaces for agenkit.

Design principles:
1. Minimal: Only what's REQUIRED for interoperability
2. Unopinionated: No framework opinions leak in
3. Extensible: Metadata dict for anything custom
4. Type-safe: Full typing, mypy strict compliant
5. Async-first: Modern Python standard for I/O

Performance characteristics:
- Interface overhead: <5% (benchmarked)
- Hot path: Direct method call, no dynamic dispatch
- Memory: Single allocation per Message/ToolResult
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from agenkit.introspection import IntrospectionResult

__all__ = ["Agent", "CallOptions", "IntrospectionResult", "Message", "Tool", "ToolResult"]


# ============================================
# Core Data Types
# ============================================


@dataclass(frozen=True)
class CallOptions:
    """
    Per-call inference options for a single agent invocation.

    The channel a caller uses to influence *how* one call runs, as opposed to
    ``Message``, which carries *what* the call is about. It exists because
    wrappers need to vary inference settings per invocation of an agent they did
    not construct: ``SelfConsistency`` samples the same prompt N times and takes a
    majority vote, so sample diversity is the technique, and temperature is the
    knob that produces it (#801).

    Passed via the optional :meth:`Agent.process_with` capability rather than by
    widening ``process()``. Agents that do not implement it fall back to
    ``process()`` and ignore the options, so nothing breaks — but a caller can
    check with ``hasattr``/``supports_options`` when it needs to know.

    Every field is optional and ``None`` means "unset", not a default. This is the
    difference that matters: an agent must be able to tell "the caller did not ask
    for a temperature" from "the caller asked for 0.0". Sending a defaulted value
    downstream would silently override whatever the agent or provider was
    configured with.

    Field names and bounds deliberately match
    :meth:`agenkit.adapters.llm.base.LLM._validate_llm_params`, so options pass
    through to a provider without translation.

    Attributes:
        temperature: Sampling temperature, 0.0-2.0. Higher is more random.
        max_tokens: Maximum tokens to generate. Must be positive.
        top_p: Nucleus sampling probability mass, 0.0-1.0.
        seed: Provider-side sampling seed, for reproducible sampling where the
            provider supports it.
        stop: Sequences that end generation.
        extra: Provider-specific options with no cross-provider meaning. Kept
            separate from the named fields so that a typo in a portable option is
            a ``TypeError`` rather than a silently ignored key.

    Usage:
        >>> options = CallOptions(temperature=0.9)
        >>> response = await agent.process_with(message, options)
    """

    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    seed: int | None = None
    stop: tuple[str, ...] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """
        Validate options at construction.

        Validated here rather than at the provider so a bad value fails at the
        call site that set it, where the fix is, instead of several layers down.

        Raises:
            ValueError: If any option is outside its documented range.
        """
        if self.temperature is not None:
            if not isinstance(self.temperature, (int, float)) or isinstance(self.temperature, bool):
                raise ValueError(
                    f"temperature must be a number, got {type(self.temperature).__name__}"
                )
            if not 0.0 <= self.temperature <= 2.0:
                raise ValueError(f"temperature must be between 0 and 2, got {self.temperature}")

        if self.max_tokens is not None:
            if not isinstance(self.max_tokens, int) or isinstance(self.max_tokens, bool):
                raise ValueError(
                    f"max_tokens must be an integer, got {type(self.max_tokens).__name__}"
                )
            if self.max_tokens <= 0:
                raise ValueError(f"max_tokens must be positive, got {self.max_tokens}")

        if self.top_p is not None:
            if not isinstance(self.top_p, (int, float)) or isinstance(self.top_p, bool):
                raise ValueError(f"top_p must be a number, got {type(self.top_p).__name__}")
            if not 0.0 <= self.top_p <= 1.0:
                raise ValueError(f"top_p must be between 0 and 1, got {self.top_p}")

        if self.seed is not None and (
            not isinstance(self.seed, int) or isinstance(self.seed, bool)
        ):
            raise ValueError(f"seed must be an integer, got {type(self.seed).__name__}")

    def to_kwargs(self) -> dict[str, Any]:
        """
        Render as keyword arguments for :meth:`agenkit.adapters.llm.base.LLM.complete`.

        Unset (``None``) fields are omitted rather than passed as ``None``, so an
        option the caller never set cannot override the agent's or provider's own
        default.

        Returns:
            Keyword arguments containing only the options that were set.

        Example:
            >>> CallOptions(temperature=0.7).to_kwargs()
            {'temperature': 0.7}
        """
        kwargs: dict[str, Any] = {}
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens
        if self.top_p is not None:
            kwargs["top_p"] = self.top_p
        if self.seed is not None:
            kwargs["seed"] = self.seed
        if self.stop is not None:
            kwargs["stop"] = list(self.stop)
        kwargs.update(self.extra)
        return kwargs

    def is_empty(self) -> bool:
        """
        Report whether any option is set.

        Lets a caller skip the ``process_with`` path entirely when it has nothing
        to say, rather than sending an all-``None`` options object.

        Returns:
            True if no option is set.
        """
        return (
            self.temperature is None
            and self.max_tokens is None
            and self.top_p is None
            and self.seed is None
            and self.stop is None
            and not self.extra
        )


@dataclass(frozen=True)
class Message:
    """
    Universal message format for agent communication.

    Design decisions:
    - role: Identifies message source ("user", "agent", "system", "tool")
    - content: Flexible type - str, dict, list, or any serializable data
    - metadata: Extension point for framework-specific data
    - timestamp: UTC timestamp for ordering and debugging
    - frozen: Reassigning a field (e.g. ``msg.content = x`` or
      ``msg.metadata = x``) raises ``FrozenInstanceError``

    Immutability here is shallow, not deep. ``frozen=True`` only blocks
    rebinding a field to a different object; it does not stop mutation of
    the object a field already points to. ``metadata`` is an ordinary
    mutable ``dict``, and several first-party patterns (sequential,
    fallback, parallel, router, collaborative, supervisor, human_in_loop,
    orchestration) deliberately mutate ``message.metadata`` in place rather
    than constructing a new ``Message`` - this is expected, supported usage,
    not a workaround. ``content`` is typed ``Any``; if you pass it a mutable
    object (list, dict, etc.), the same caveat applies to it.

    Practical implications for API consumers:
    - Holding a reference to a ``Message`` does not guarantee its
      ``metadata``/``content`` won't change out from under you - the
      "frozen" guarantee is limited to field reassignment, not the
      transitive contents of mutable fields.
    - Do not rely on this class for caching keys or set/dict membership:
      because ``metadata`` is an unhashable ``dict``, ``hash(message)``
      raises ``TypeError`` at call time, even though ``@dataclass(frozen=True)``
      would otherwise auto-generate ``__hash__``. Two ``Message`` instances
      with equal field values are ``==``, but neither is hashable.

    Usage:
        >>> msg = Message(role="user", content="Hello, agent!")
        >>> response = await agent.process(msg)
        >>> print(response.content)
    """

    role: str
    content: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate message after initialization."""
        # Role validation
        if not self.role:
            raise ValueError("Message role cannot be empty")
        if len(self.role) > 20:
            raise ValueError(
                f"Message role exceeds maximum length of 20 characters (got {len(self.role)})"
            )

        # Validate role is one of the allowed values
        allowed_roles = {"user", "assistant", "system", "tool", "agent"}
        if self.role not in allowed_roles:
            raise ValueError(f"Invalid message role: {self.role}. Must be one of {allowed_roles}")

        # Content validation - max 16MB (allows for large payloads in testing and production)
        if self.content is not None:
            content_str = str(self.content)
            content_size = len(content_str.encode("utf-8"))
            max_content_size = 16 * 1024 * 1024  # 16MB
            if content_size > max_content_size:
                raise ValueError(
                    f"Message content exceeds maximum size of {max_content_size} bytes "
                    f"(got {content_size} bytes)"
                )

        # Metadata validation
        if self.metadata:
            # Max 100 keys
            if len(self.metadata) > 100:
                raise ValueError(
                    f"Message metadata exceeds maximum of 100 keys (got {len(self.metadata)})"
                )

            # Validate each key and value
            max_key_length = 50
            max_value_size = 16 * 1024 * 1024  # 16MB - match content size limit

            for key, value in self.metadata.items():
                # Key length validation
                if len(key) > max_key_length:
                    raise ValueError(
                        f"Metadata key '{key[:20]}...' exceeds maximum length of {max_key_length} "
                        f"characters (got {len(key)})"
                    )

                # Value size validation
                value_str = str(value)
                value_size = len(value_str.encode("utf-8"))
                if value_size > max_value_size:
                    raise ValueError(
                        f"Metadata value for key '{key}' exceeds maximum size of {max_value_size} bytes "
                        f"(got {value_size} bytes)"
                    )


@dataclass(frozen=True)
class ToolResult:
    """
    Universal tool execution result.

    Design decisions:
    - success: Explicit success/failure (no exceptions in data)
    - data: The actual result (any type)
    - error: Optional error message if success=False
    - metadata: Extension point for execution details (timing, etc.)
    - frozen: Immutable for thread safety

    Usage:
        >>> result = ToolResult(success=True, data={"answer": 42})
        >>> if result.success:
        ...     print(result.data)
    """

    success: bool
    data: Any
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate tool result after initialization."""
        if not self.success and self.error is None:
            raise ValueError("Failed ToolResult must have error message")


# ============================================
# Core Interfaces
# ============================================


class Tool(ABC):
    """
    Tool interface - minimal contract for executable tools.

    Design decisions:
    - Only 3 required methods (name, description, execute)
    - Optional methods for extended functionality
    - No state in interface (tools manage their own state)
    - Async execute (most tools do I/O)

    Performance characteristics:
    - No dynamic dispatch overhead
    - No metaclass magic
    - Direct method calls

    Usage:
        >>> class SearchTool(Tool):
        ...     @property
        ...     def name(self) -> str:
        ...         return "search"
        ...
        ...     @property
        ...     def description(self) -> str:
        ...         return "Search the web"
        ...
        ...     async def execute(self, params: dict[str, Any]) -> ToolResult:
        ...         query = params.get("query", "")
        ...         results = await search_api(query)
        ...         return ToolResult(success=True, data=results)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Tool identifier. Must be unique within a tool set.

        Returns:
            Unique tool name (e.g., "search", "calculator")
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        What this tool does. Used by LLMs to decide when to call it.

        Returns:
            Human-readable description of tool functionality
        """
        pass

    @abstractmethod
    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given parameters.

        As of v0.50.0, tools receive parameters as an explicit dictionary
        instead of **kwargs. This provides better type safety and clearer APIs.

        Args:
            params: Dictionary of tool-specific parameters

        Returns:
            ToolResult with success status and data/error

        Raises:
            Should not raise - return ToolResult(success=False, error=str(exc))
        """
        pass

    @property
    def parameters_schema(self) -> dict[str, Any] | None:
        """
        JSON schema for tool parameters. Override if needed.

        Returns:
            JSON schema dict or None if no schema validation
        """
        return None

    async def validate(self, **kwargs: Any) -> bool:
        """
        Validate inputs before execution. Override if needed.

        Args:
            **kwargs: Tool parameters to validate

        Returns:
            True if valid, False otherwise
        """
        return True


class Agent(ABC):
    """
    Agent interface - minimal contract for agent communication.

    Design decisions:
    - Only 2 required methods (name, process)
    - Optional streaming support
    - No state in interface (agents manage their own state)
    - Async process (agents typically do I/O)

    Performance characteristics:
    - <5% overhead vs direct function call (benchmarked)
    - No dynamic dispatch on hot path
    - Single allocation per message

    Usage:
        >>> class SimpleAgent(Agent):
        ...     @property
        ...     def name(self) -> str:
        ...         return "simple"
        ...
        ...     async def process(self, message: Message) -> Message:
        ...         result = f"Processed: {message.content}"
        ...         return Message(role="agent", content=result)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Agent identifier.

        Returns:
            Unique agent name
        """
        pass

    @abstractmethod
    async def process(self, message: Message) -> Message:
        """
        Process a message and return a response.

        This is the core contract. Everything else is optional.

        Args:
            message: Input message to process

        Returns:
            Response message

        Raises:
            Can raise exceptions - caller handles error recovery
        """
        pass

    async def process_with(self, message: Message, options: CallOptions) -> Message:
        """
        Process a message with per-call inference options. Override if supported.

        This is an optional capability, in the same spirit as :meth:`stream` and
        :meth:`introspect`: the core contract stays ``process(message)``, and an
        agent that can honour per-call options advertises that by overriding this
        method. Widening ``process()`` itself was rejected — roughly 500
        implementations across the nine cores would have had to change, and every
        one of Go's would break at compile time, to add something most agents have
        no use for.

        The default implementation **ignores the options and delegates to**
        :meth:`process`. That makes the capability additive: existing agents keep
        working untouched. The trade-off is that a caller cannot tell from a
        successful return whether its options were applied, so check
        :attr:`supports_options` when that matters.

        Args:
            message: Input message to process
            options: Per-call inference options. May be empty.

        Returns:
            Response message

        Example:
            >>> class TunableAgent(Agent):
            ...     @property
            ...     def name(self) -> str:
            ...         return "tunable"
            ...
            ...     async def process(self, message: Message) -> Message:
            ...         return await self.process_with(message, CallOptions())
            ...
            ...     async def process_with(
            ...         self, message: Message, options: CallOptions
            ...     ) -> Message:
            ...         response = await self.llm.complete(
            ...             [message], **options.to_kwargs()
            ...         )
            ...         return response
        """
        return await self.process(message)

    @property
    def supports_options(self) -> bool:
        """
        Report whether this agent honours :class:`CallOptions`.

        True when :meth:`process_with` is overridden — i.e. the agent does
        something with the options rather than inheriting the ignoring default.
        Checked structurally rather than requiring agents to declare a flag, so it
        cannot fall out of sync with the implementation.

        A caller that needs its options to actually take effect should check this
        rather than assume, since the default ``process_with`` accepts and discards
        them.

        Returns:
            True if the agent applies per-call options.
        """
        return type(self).process_with is not Agent.process_with

    async def stream(self, message: Message) -> AsyncIterator[Message]:
        """
        Stream response messages. Override if supported.

        Default implementation raises NotImplementedError.

        Args:
            message: Input message to process

        Yields:
            Response messages as they're generated

        Raises:
            NotImplementedError: If agent doesn't support streaming
        """
        # Make this an async generator by using if False: yield
        # This ensures the function is an async generator, not a coroutine
        if False:
            yield  # type: ignore[unreachable]
        raise NotImplementedError(f"{self.name} does not support streaming")

    @property
    def capabilities(self) -> list[str]:
        """
        What this agent can do. Override if meaningful.

        Returns:
            List of capability strings (e.g., ["code", "search"])
        """
        return []

    def unwrap(self) -> Any:
        """
        Get underlying implementation. Override to provide escape hatch.

        This allows users to access framework-specific features when needed.

        Returns:
            Native object (default: self)
        """
        return self

    def introspect(self) -> IntrospectionResult:
        """
        Examine agent's internal state, memory, and capabilities.

        This is introspection (examining "what I know"), not reflection
        (analyzing "how I did"). Returns a snapshot of current internal state.

        Introspection is useful for:
        - Debugging: Examine agent state during development
        - Monitoring: Track agent state in production
        - Coordination: Agents can inspect each other's capabilities
        - Testing: Verify agent state in tests
        - Explainability: Understand what an agent "knows"

        Returns:
            IntrospectionResult with current state information

        Example:
            >>> result = agent.introspect()
            >>> print(f"Agent: {result.agent_name}")
            >>> print(f"Capabilities: {result.capabilities}")
            >>> if result.memory_state:
            ...     print(f"Memory entries: {len(result.memory_state)}")
        """
        return IntrospectionResult(
            timestamp=datetime.now(UTC),
            agent_name=self.name,
            capabilities=self.capabilities,
            memory_state=self._get_memory_state(),
            internal_state=self._get_internal_state(),
            metadata={},
        )

    def _get_memory_state(self) -> dict[str, Any] | None:
        """
        Get memory state for introspection. Override to provide memory contents.

        This method should return the current contents of the agent's memory,
        if applicable. For agents without memory, this returns None.

        Returns:
            Dictionary of memory contents, or None if no memory

        Example:
            >>> def _get_memory_state(self) -> dict[str, Any] | None:
            ...     if hasattr(self, 'memory'):
            ...         return {
            ...             'short_term': len(self.memory.short_term),
            ...             'long_term': len(self.memory.long_term),
            ...             'working': len(self.memory.working),
            ...         }
            ...     return None
        """
        return None

    def _get_internal_state(self) -> dict[str, Any]:
        """
        Get agent-specific internal state for introspection. Override to provide details.

        This method should return any agent-specific state that is relevant
        for introspection. Examples: configuration, counters, status flags, etc.

        Returns:
            Dictionary of internal state (empty dict if no state)

        Example:
            >>> def _get_internal_state(self) -> dict[str, Any]:
            ...     return {
            ...         'model': self.model_name,
            ...         'temperature': self.temperature,
            ...         'max_tokens': self.max_tokens,
            ...         'messages_processed': self.message_count,
            ...     }
        """
        return {}

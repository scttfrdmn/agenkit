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
from datetime import datetime, timezone
from typing import Any

__all__ = ["Agent", "Message", "Tool", "ToolResult"]


# ============================================
# Core Data Types
# ============================================


@dataclass(frozen=True)
class Message:
    """
    Universal message format for agent communication.

    Design decisions:
    - role: Identifies message source ("user", "agent", "system", "tool")
    - content: Flexible type - str, dict, list, or any serializable data
    - metadata: Extension point for framework-specific data
    - timestamp: UTC timestamp for ordering and debugging
    - frozen: Immutable for thread safety and caching

    Usage:
        >>> msg = Message(role="user", content="Hello, agent!")
        >>> response = await agent.process(msg)
        >>> print(response.content)
    """

    role: str
    content: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate message after initialization."""
        if not self.role:
            raise ValueError("Message role cannot be empty")
        # Content can be anything - no validation
        # Metadata can be anything - no validation


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
        ...     async def execute(self, query: str) -> ToolResult:
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
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

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

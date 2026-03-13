"""
MCP Tool Management.

Handles registration and execution of MCP tools (actions).

Tools are callable functions with JSON schemas for parameters.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from .schema import MCPToolInfo, validate_json_schema


@dataclass
class Tool:
    """
    MCP Tool.

    Represents an action that can be invoked with parameters.
    """

    name: str
    description: str
    handler: Callable[[dict[str, Any]], Awaitable[Any]]
    input_schema: dict[str, Any]
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    async def execute(self, params: dict[str, Any]) -> Any:
        """
        Execute tool with parameters.

        Args:
            params: Tool parameters

        Returns:
            Tool result

        Raises:
            ValueError: If parameters don't match schema
        """
        # Validate parameters against schema
        if not validate_json_schema(params, self.input_schema):
            raise ValueError(f"Invalid parameters for tool {self.name}")

        return await self.handler(params)

    def to_info(self) -> MCPToolInfo:
        """Convert to MCPToolInfo."""
        return MCPToolInfo(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
            metadata=self.metadata,
        )


class ToolRegistry:
    """
    Registry for MCP tools.

    Manages tool registration and execution.
    """

    def __init__(self):
        """Initialize empty registry."""
        self.tools: dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: Callable[[dict[str, Any]], Awaitable[Any]],
        input_schema: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> Tool:
        """
        Register a tool.

        Args:
            name: Tool name
            description: Tool description
            handler: Async function that executes the tool
            input_schema: JSON schema for tool parameters
            metadata: Additional metadata

        Returns:
            Registered Tool

        Example:
            >>> async def search(params):
            ...     query = params["query"]
            ...     return {"results": [...]}
            >>>
            >>> registry.register(
            ...     name="search",
            ...     description="Search the web",
            ...     handler=search,
            ...     input_schema={
            ...         "type": "object",
            ...         "properties": {
            ...             "query": {"type": "string"}
            ...         },
            ...         "required": ["query"]
            ...     }
            ... )
        """
        tool = Tool(
            name=name,
            description=description,
            handler=handler,
            input_schema=input_schema,
            metadata=metadata or {},
        )

        self.tools[name] = tool
        return tool

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool.

        Args:
            name: Tool name to remove

        Returns:
            True if removed, False if not found
        """
        if name in self.tools:
            del self.tools[name]
            return True
        return False

    def get(self, name: str) -> Tool | None:
        """
        Get tool by name.

        Args:
            name: Tool name

        Returns:
            Tool if found, None otherwise
        """
        return self.tools.get(name)

    def list(self) -> list[MCPToolInfo]:
        """
        List all registered tools.

        Returns:
            List of tool information
        """
        return [tool.to_info() for tool in self.tools.values()]

    async def execute(self, name: str, params: dict[str, Any] | None = None) -> Any:
        """
        Execute a tool.

        Args:
            name: Tool name
            params: Tool parameters

        Returns:
            Tool result

        Raises:
            ValueError: If tool not found or invalid parameters
        """
        tool = self.get(name)
        if tool is None:
            raise ValueError(f"Tool not found: {name}")

        return await tool.execute(params or {})

    def has_tool(self, name: str) -> bool:
        """
        Check if tool exists.

        Args:
            name: Tool name

        Returns:
            True if tool exists
        """
        return name in self.tools

    def clear(self):
        """Clear all registered tools."""
        self.tools.clear()

    def __len__(self) -> int:
        """Return number of registered tools."""
        return len(self.tools)


def tool_decorator(
    name: str,
    description: str,
    input_schema: dict[str, Any],
    metadata: dict[str, Any] | None = None,
):
    """
    Decorator for registering tools.

    Args:
        name: Tool name
        description: Tool description
        input_schema: JSON schema for parameters
        metadata: Additional metadata

    Example:
        >>> registry = ToolRegistry()
        >>>
        >>> @tool_decorator(
        ...     name="calculate",
        ...     description="Perform calculation",
        ...     input_schema={
        ...         "type": "object",
        ...         "properties": {
        ...             "expression": {"type": "string"}
        ...         }
        ...     }
        ... )
        ... async def calculate(params):
        ...     # WARNING: Never use eval() with untrusted input in production.
        ...     # This example is for illustration only. Use a safe expression
        ...     # evaluator (e.g., asteval, numexpr, or a sandboxed subprocess).
        ...     return {"result": eval(params["expression"])}  # noqa: S307
    """

    def decorator(func: Callable[[dict[str, Any]], Awaitable[Any]]):
        # Store registration info on function
        func._mcp_tool = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "metadata": metadata or {},
        }
        return func

    return decorator

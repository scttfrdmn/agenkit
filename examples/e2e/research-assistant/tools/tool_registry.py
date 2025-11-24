"""Tool registry for managing available tools."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ToolResult:
    """Result from tool execution."""

    success: bool
    output: Any
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0


@dataclass
class Tool:
    """
    A tool that can be used by the autonomous agent.

    Tools are functions that the agent can call to interact with
    external systems, perform calculations, or access information.
    """

    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema for parameters
    function: Callable[..., Awaitable[ToolResult]]
    cost: float = 0.0  # Cost per invocation (for budget tracking)
    category: str = "general"
    usage_count: int = 0
    total_execution_time: float = 0.0

    def get_schema(self) -> dict[str, Any]:
        """Get OpenAI function calling schema for this tool."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Parameters for the tool

        Returns:
            ToolResult with execution outcome
        """
        start_time = datetime.now()

        try:
            result = await self.function(**kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()

            # Update statistics
            self.usage_count += 1
            self.total_execution_time += execution_time

            result.execution_time = execution_time
            result.metadata["tool_name"] = self.name
            result.metadata["cost"] = self.cost

            return result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.usage_count += 1
            self.total_execution_time += execution_time

            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                metadata={
                    "tool_name": self.name,
                    "cost": self.cost,
                },
                execution_time=execution_time,
            )

    def __repr__(self) -> str:
        return f"Tool(name={self.name}, category={self.category}, used={self.usage_count})"


class ToolRegistry:
    """
    Registry for managing available tools.

    Provides tool registration, discovery, and execution tracking.

    Example:
        ```python
        registry = ToolRegistry()

        # Register a tool
        async def search_web(query: str) -> ToolResult:
            results = await perform_search(query)
            return ToolResult(success=True, output=results)

        registry.register(
            name="search",
            description="Search the web for information",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            },
            function=search_web,
            cost=0.001
        )

        # Execute tool
        result = await registry.execute("search", query="python tutorials")
        ```
    """

    def __init__(self):
        """Initialize tool registry."""
        self.tools: dict[str, Tool] = {}
        self._execution_history: list[dict[str, Any]] = []

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        function: Callable[..., Awaitable[ToolResult]],
        cost: float = 0.0,
        category: str = "general",
    ) -> Tool:
        """
        Register a new tool.

        Args:
            name: Tool name
            description: What the tool does
            parameters: JSON schema for parameters
            function: Async function to execute
            cost: Cost per invocation
            category: Tool category

        Returns:
            The registered Tool
        """
        if name in self.tools:
            raise ValueError(f"Tool '{name}' already registered")

        tool = Tool(
            name=name,
            description=description,
            parameters=parameters,
            function=function,
            cost=cost,
            category=category,
        )

        self.tools[name] = tool
        return tool

    def register_tool(self, tool: Tool) -> Tool:
        """
        Register an already-created Tool object.

        Args:
            tool: The Tool to register

        Returns:
            The registered Tool
        """
        if tool.name in self.tools:
            raise ValueError(f"Tool '{tool.name}' already registered")

        self.tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Tool | None:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool or None if not found
        """
        return self.tools.get(name)

    def list_tools(self, category: str | None = None) -> list[Tool]:
        """
        List all available tools.

        Args:
            category: Optional filter by category

        Returns:
            List of tools
        """
        tools = list(self.tools.values())

        if category:
            tools = [t for t in tools if t.category == category]

        return sorted(tools, key=lambda t: t.name)

    def get_schemas(self, category: str | None = None) -> list[dict[str, Any]]:
        """
        Get OpenAI function calling schemas for all tools.

        Args:
            category: Optional filter by category

        Returns:
            List of tool schemas
        """
        tools = self.list_tools(category=category)
        return [tool.get_schema() for tool in tools]

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Parameters for the tool

        Returns:
            ToolResult with execution outcome
        """
        tool = self.get(tool_name)

        if not tool:
            return ToolResult(
                success=False,
                output=None,
                error=f"Tool '{tool_name}' not found",
            )

        result = await tool.execute(**kwargs)

        # Record execution in history
        self._execution_history.append(
            {
                "tool_name": tool_name,
                "timestamp": datetime.now().isoformat(),
                "success": result.success,
                "execution_time": result.execution_time,
                "cost": tool.cost,
            }
        )

        return result

    def get_statistics(self) -> dict[str, Any]:
        """
        Get usage statistics for all tools.

        Returns:
            Dict with statistics
        """
        total_executions = sum(t.usage_count for t in self.tools.values())
        total_cost = sum(t.usage_count * t.cost for t in self.tools.values())
        total_time = sum(t.total_execution_time for t in self.tools.values())

        by_tool = {
            name: {
                "usage_count": tool.usage_count,
                "total_time": tool.total_execution_time,
                "avg_time": (
                    tool.total_execution_time / tool.usage_count if tool.usage_count > 0 else 0.0
                ),
                "total_cost": tool.usage_count * tool.cost,
            }
            for name, tool in self.tools.items()
        }

        return {
            "total_tools": len(self.tools),
            "total_executions": total_executions,
            "total_cost": total_cost,
            "total_time": total_time,
            "by_tool": by_tool,
        }

    def get_execution_history(self, limit: int | None = None) -> list[dict[str, Any]]:
        """
        Get execution history.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of execution records
        """
        if limit:
            return self._execution_history[-limit:]
        return self._execution_history.copy()

    def clear_history(self):
        """Clear execution history."""
        self._execution_history.clear()

    def __len__(self) -> int:
        """Return number of registered tools."""
        return len(self.tools)

    def __repr__(self) -> str:
        return f"ToolRegistry(tools={len(self.tools)}, executions={len(self._execution_history)})"

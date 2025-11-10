"""Tool registry for managing available tools."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from agenkit.interfaces import Tool


@dataclass
class ToolCall:
    """Request to execute a tool."""

    tool_name: str
    parameters: Dict[str, any]


class ToolRegistry:
    """Registry for managing available tools."""

    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Add a tool to the registry.

        Args:
            tool: Tool to register

        Raises:
            ValueError: If tool is None, has empty name, or name already registered
        """
        if tool is None:
            raise ValueError("Tool cannot be None")
        if not tool.name:
            raise ValueError("Tool name cannot be empty")
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")

        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Retrieve a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def list(self) -> List[str]:
        """Return all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_tool_descriptions(self) -> str:
        """Return formatted description of all available tools.

        Returns:
            String with tool names and descriptions
        """
        if not self._tools:
            return "No tools available."

        lines = ["Available tools:"]
        for name in sorted(self._tools.keys()):
            tool = self._tools[name]
            lines.append(f"- {name}: {tool.description}")

        return "\n".join(lines)

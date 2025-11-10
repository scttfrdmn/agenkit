"""Tool agent wrapper for adding tool calling capabilities."""

from typing import Any, Dict, List

from agenkit.interfaces import Agent, Message, ToolResult

from .tool_registry import ToolCall, ToolRegistry


class ToolAgent(Agent):
    """Agent wrapper that adds tool calling capabilities.

    This agent checks incoming messages for tool calls in metadata
    and executes them. If no tool calls are present, it passes the
    message to the underlying agent.
    """

    def __init__(self, agent: Agent, registry: ToolRegistry):
        """Initialize tool agent.

        Args:
            agent: Underlying agent to wrap
            registry: Tool registry with available tools
        """
        self._agent = agent
        self._registry = registry

    @property
    def name(self) -> str:
        """Return the name of the underlying agent."""
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        """Return capabilities of underlying agent plus tool support."""
        caps = self._agent.capabilities.copy()
        caps.append("tool_calling")
        return caps

    async def process(self, message: Message) -> Message:
        """Handle a message with tool calling support.

        If the message contains tool calls in metadata, executes them and returns results.
        Otherwise, passes the message to the underlying agent.

        Args:
            message: Input message

        Returns:
            Response message with tool results or agent response

        Raises:
            Exception: If tool parsing fails
        """
        # Check if message contains tool calls
        if "tool_calls" not in message.metadata:
            # No tool calls - pass through to underlying agent
            return await self._agent.process(message)

        # Parse tool calls
        tool_calls = self._parse_tool_calls(message.metadata["tool_calls"])

        # Execute tool calls
        results = []
        for call in tool_calls:
            try:
                result = await self._execute_tool(call)
                results.append(result)
            except Exception as e:
                results.append(ToolResult(success=False, data=None, error=str(e)))

        # Create response with tool results
        response = Message(role="agent", content=self._format_tool_results(results))
        response.metadata["tool_results"] = [
            {"success": r.success, "data": r.data, "error": r.error, "metadata": r.metadata} for r in results
        ]
        return response

    def _parse_tool_calls(self, data: Any) -> List[ToolCall]:
        """Convert metadata to ToolCall structures.

        Args:
            data: Tool calls data from metadata

        Returns:
            List of ToolCall objects

        Raises:
            ValueError: If data format is invalid
        """
        if not isinstance(data, list):
            raise ValueError("tool_calls must be a list")

        tool_calls = []
        for item in data:
            if not isinstance(item, dict):
                raise ValueError("Each tool call must be a dict")
            if "tool_name" not in item:
                raise ValueError("Each tool call must have 'tool_name'")
            if "parameters" not in item:
                raise ValueError("Each tool call must have 'parameters'")

            tool_calls.append(ToolCall(tool_name=item["tool_name"], parameters=item["parameters"]))

        return tool_calls

    async def _execute_tool(self, call: ToolCall) -> ToolResult:
        """Execute a single tool call.

        Args:
            call: Tool call to execute

        Returns:
            Tool result

        Raises:
            ValueError: If tool not found
        """
        tool = self._registry.get(call.tool_name)
        if not tool:
            raise ValueError(f"Tool '{call.tool_name}' not found")

        return await tool.execute(**call.parameters)

    def _format_tool_results(self, results: List[ToolResult]) -> str:
        """Format tool results into a readable message.

        Args:
            results: List of tool results

        Returns:
            Formatted string with all results
        """
        lines = ["Tool execution results:"]
        for i, result in enumerate(results, 1):
            if result.success:
                lines.append(f"{i}. Success: {result.data}")
            else:
                lines.append(f"{i}. Error: {result.error}")

        return "\n".join(lines)

    def get_registry(self) -> ToolRegistry:
        """Return the tool registry for this agent.

        Returns:
            Tool registry
        """
        return self._registry

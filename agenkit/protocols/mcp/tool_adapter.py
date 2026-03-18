"""Bridge MCP tools to the agenkit Tool interface.

MCPToolAdapter wraps a single MCPTool so it can be passed to any agenkit
agent that accepts agenkit.Tool instances.

tools_from_client() is the high-level factory: it calls list_tools() on a
client and returns a list of ready-to-use agenkit Tool objects.

Example::

    async with mcp.StdioClient("npx", [...]) as client:
        tools = await mcp.tools_from_client(client)
        agent = ReActAgent(llm, tools)
"""

from __future__ import annotations

from typing import Any

from agenkit.interfaces import Tool, ToolResult
from agenkit.protocols.mcp.types import MCPClient, MCPTool, _text_content


class MCPToolAdapter(Tool):
    """Wraps an MCPTool advertised by an MCP server as an agenkit Tool.

    Args:
        client: The MCPClient used to call the tool.
        tool: The MCPTool descriptor returned by the server.
    """

    def __init__(self, client: MCPClient, tool: MCPTool) -> None:
        self._client = client
        self._tool = tool

    @property
    def name(self) -> str:
        return self._tool.name

    @property
    def description(self) -> str:
        return self._tool.description

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        result = await self._client.call_tool(self._tool.name, params)
        data = _text_content(result.content)
        if result.is_error:
            return ToolResult(success=False, data=data, error=data)
        return ToolResult(success=True, data=data)


async def tools_from_client(client: MCPClient) -> list[Tool]:
    """Return all tools advertised by *client* as agenkit Tool objects.

    Args:
        client: An already-initialised MCPClient (StdioClient or HTTPClient).

    Returns:
        A list of Tool objects, one per MCP tool advertised by the server.

    Example::

        tools = await mcp.tools_from_client(client)
        agent = ReActAgent(llm, tools)
    """
    mcp_tools = await client.list_tools()
    return [MCPToolAdapter(client, t) for t in mcp_tools]

"""Model Context Protocol (MCP) support for agenkit agents.

MCP is a JSON-RPC 2.0 based protocol for AI tool integrations used by
Claude Code, Cursor, and thousands of community tools. This package
provides both client and server implementations using stdlib + httpx
(no external MCP library required).

Client usage — stdio (subprocess)::

    from agenkit.protocols import mcp

    async with mcp.StdioClient("npx", ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]) as client:
        tools = await mcp.tools_from_client(client)
        agent = ReActAgent(llm, tools)

Client usage — HTTP::

    async with mcp.HTTPClient("http://localhost:3000") as client:
        tools = await mcp.tools_from_client(client)

Server usage — expose agenkit tools via MCP::

    server = mcp.MCPServer(name="my-agent", version="1.0.0", tools=[my_tool])
    await server.serve_stdio()
"""

from agenkit.protocols.mcp.client import HTTPClient, StdioClient
from agenkit.protocols.mcp.server import MCPServer
from agenkit.protocols.mcp.tool_adapter import MCPToolAdapter, tools_from_client
from agenkit.protocols.mcp.types import (
    MCPClient,
    MCPContent,
    MCPServerInfo,
    MCPTool,
    MCPToolResult,
)

__all__ = [
    "HTTPClient",
    # Types
    "MCPClient",
    "MCPContent",
    # Server
    "MCPServer",
    "MCPServerInfo",
    "MCPTool",
    # Tool adapter
    "MCPToolAdapter",
    "MCPToolResult",
    # Clients
    "StdioClient",
    "tools_from_client",
]

"""
Model Context Protocol (MCP) Implementation.

Anthropic's open standard for connecting AI assistants to external data
sources and tools.

This module provides:
- MCP Server: Expose resources and tools via MCP protocol
- MCP Client: Connect to MCP servers
- Adapters: Integration with Agenkit agents
- Transports: HTTP, SSE, stdio

References:
    - Specification: https://modelcontextprotocol.io/
    - Claude Desktop: https://docs.anthropic.com/claude/docs/mcp

Example (Server):
    >>> from agenkit.techniques.protocols.mcp import MCPServer
    >>>
    >>> server = MCPServer(name="my-server")
    >>>
    >>> @server.resource("user://profile")
    >>> async def get_user_profile(params):
    ...     return {"name": "John", "email": "john@example.com"}
    >>>
    >>> @server.tool("search", description="Search", input_schema={...})
    >>> async def search_tool(params):
    ...     return {"results": [...]}
    >>>
    >>> await server.start(transport="stdio")  # For Claude Desktop

Example (Agenkit Integration):
    >>> from agenkit.techniques.protocols.mcp import MCPAdapter, AgentMCPServer
    >>> from agenkit.patterns import ReActAgent
    >>>
    >>> # Expose Agenkit agent as MCP server
    >>> agent = ReActAgent(llm=my_llm, tools=[...])
    >>> mcp_wrapper = AgentMCPServer(agent)
    >>> await mcp_wrapper.run()  # Claude Desktop can now use this agent
"""

# Core components
from .adapter import AgentMCPServer, MCPAdapter
from .client import MCPClient
# Message types
from .message import (MCPMessage, MCPNotification, MCPRequest, MCPResponse,
                      create_error_response, create_notification,
                      create_request, create_response)
# Registries
from .resources import Resource, ResourceRegistry
# Schema and types
from .schema import (MCPMessageType, MCPMethod, MCPPromptInfo, MCPResourceInfo,
                     MCPToolInfo, create_resource_schema, create_tool_schema)
from .server import MCPServer
from .tools import Tool, ToolRegistry
# Transports
from .transports import HTTPTransport, SSETransport, StdioTransport, Transport

__all__ = [
    "AgentMCPServer",
    "HTTPTransport",
    # Adapters
    "MCPAdapter",
    "MCPClient",
    # Messages
    "MCPMessage",
    # Schema
    "MCPMessageType",
    "MCPMethod",
    "MCPNotification",
    "MCPPromptInfo",
    "MCPRequest",
    "MCPResourceInfo",
    "MCPResponse",
    # Server and Client
    "MCPServer",
    "MCPToolInfo",
    "Resource",
    # Registries
    "ResourceRegistry",
    "SSETransport",
    "StdioTransport",
    "Tool",
    "ToolRegistry",
    # Transports
    "Transport",
    "create_error_response",
    "create_notification",
    "create_request",
    "create_resource_schema",
    "create_response",
    "create_tool_schema",
]

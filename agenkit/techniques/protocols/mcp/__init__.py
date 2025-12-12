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
from .server import MCPServer
from .client import MCPClient
from .adapter import MCPAdapter, AgentMCPServer

# Schema and types
from .schema import (
    MCPMessageType,
    MCPMethod,
    MCPResourceInfo,
    MCPToolInfo,
    MCPPromptInfo,
    create_tool_schema,
    create_resource_schema
)

# Message types
from .message import (
    MCPMessage,
    MCPRequest,
    MCPResponse,
    MCPNotification,
    create_request,
    create_response,
    create_error_response,
    create_notification
)

# Registries
from .resources import ResourceRegistry, Resource
from .tools import ToolRegistry, Tool

# Transports
from .transports import Transport, StdioTransport, HTTPTransport, SSETransport

__all__ = [
    # Server and Client
    "MCPServer",
    "MCPClient",
    # Adapters
    "MCPAdapter",
    "AgentMCPServer",
    # Schema
    "MCPMessageType",
    "MCPMethod",
    "MCPResourceInfo",
    "MCPToolInfo",
    "MCPPromptInfo",
    "create_tool_schema",
    "create_resource_schema",
    # Messages
    "MCPMessage",
    "MCPRequest",
    "MCPResponse",
    "MCPNotification",
    "create_request",
    "create_response",
    "create_error_response",
    "create_notification",
    # Registries
    "ResourceRegistry",
    "Resource",
    "ToolRegistry",
    "Tool",
    # Transports
    "Transport",
    "StdioTransport",
    "HTTPTransport",
    "SSETransport",
]

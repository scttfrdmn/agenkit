"""
MCP Server Implementation.

Implements an MCP server that exposes resources and tools via the MCP protocol.

References:
    - MCP Specification: https://modelcontextprotocol.io/
"""

from typing import Dict, Any, Optional, Callable, Awaitable, List
import asyncio
import uuid
from .schema import MCPMethod
from .message import (
    MCPRequest, MCPResponse, create_response, create_error_response,
    ERROR_METHOD_NOT_FOUND, ERROR_INVALID_PARAMS, ERROR_INTERNAL_ERROR
)
from .resources import ResourceRegistry, resource_decorator
from .tools import ToolRegistry, tool_decorator


class MCPServer:
    """
    MCP Server.

    Exposes resources and tools via Model Context Protocol.

    Example:
        >>> server = MCPServer(name="my-agent-server")
        >>>
        >>> @server.resource("user://profile")
        >>> async def get_user_profile(params):
        ...     return {"name": "John", "email": "john@example.com"}
        >>>
        >>> @server.tool("search", input_schema={...})
        >>> async def search_tool(params):
        ...     return {"results": [...]}
        >>>
        >>> await server.start(transport="http", port=3000)
    """

    def __init__(
        self,
        name: str,
        version: str = "1.0",
        capabilities: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize MCP server.

        Args:
            name: Server name
            version: Server version
            capabilities: Server capabilities
        """
        self.name = name
        self.version = version
        self.capabilities = capabilities or {
            "resources": True,
            "tools": True
        }

        self.resources = ResourceRegistry()
        self.tools = ToolRegistry()
        self.transport = None
        self.initialized = False

    def resource(
        self,
        uri: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        mime_type: str = "text/plain",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Decorator to register a resource handler.

        Args:
            uri: Resource URI
            name: Resource name (defaults to URI)
            description: Resource description
            mime_type: MIME type
            metadata: Additional metadata

        Example:
            >>> @server.resource("file://doc.txt")
            >>> async def get_document(params):
            ...     return "Document content"
        """
        def decorator(func: Callable[[Dict[str, Any]], Awaitable[Any]]):
            resource_name = name or uri
            self.resources.register(
                uri=uri,
                name=resource_name,
                handler=func,
                description=description,
                mime_type=mime_type,
                metadata=metadata
            )
            return func
        return decorator

    def tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Decorator to register a tool handler.

        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON schema for parameters
            metadata: Additional metadata

        Example:
            >>> @server.tool(
            ...     name="search",
            ...     description="Search the web",
            ...     input_schema={
            ...         "type": "object",
            ...         "properties": {
            ...             "query": {"type": "string"}
            ...         }
            ...     }
            ... )
            >>> async def search_tool(params):
            ...     return {"results": [...]}
        """
        def decorator(func: Callable[[Dict[str, Any]], Awaitable[Any]]):
            self.tools.register(
                name=name,
                description=description,
                handler=func,
                input_schema=input_schema,
                metadata=metadata
            )
            return func
        return decorator

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        Handle an MCP request.

        Args:
            request: MCP request

        Returns:
            MCP response

        Example:
            >>> request = MCPRequest(
            ...     id="req-1",
            ...     method="resources/list"
            ... )
            >>> response = await server.handle_request(request)
        """
        try:
            method = request.method
            params = request.params or {}

            # Handle initialize
            if method == MCPMethod.INITIALIZE.value:
                return await self._handle_initialize(request)

            # Handle resources/list
            elif method == MCPMethod.RESOURCES_LIST.value:
                return await self._handle_resources_list(request)

            # Handle resources/read
            elif method == MCPMethod.RESOURCES_READ.value:
                return await self._handle_resources_read(request)

            # Handle tools/list
            elif method == MCPMethod.TOOLS_LIST.value:
                return await self._handle_tools_list(request)

            # Handle tools/call
            elif method == MCPMethod.TOOLS_CALL.value:
                return await self._handle_tools_call(request)

            else:
                return create_error_response(
                    request_id=request.id,
                    code=ERROR_METHOD_NOT_FOUND,
                    message=f"Method not found: {method}"
                )

        except Exception as e:
            return create_error_response(
                request_id=request.id,
                code=ERROR_INTERNAL_ERROR,
                message=str(e)
            )

    async def _handle_initialize(self, request: MCPRequest) -> MCPResponse:
        """Handle initialize request."""
        self.initialized = True

        return create_response(
            request_id=request.id,
            result={
                "protocolVersion": "1.0",
                "serverInfo": {
                    "name": self.name,
                    "version": self.version
                },
                "capabilities": self.capabilities
            }
        )

    async def _handle_resources_list(self, request: MCPRequest) -> MCPResponse:
        """Handle resources/list request."""
        resources = self.resources.list()

        return create_response(
            request_id=request.id,
            result={
                "resources": [
                    {
                        "uri": r.uri,
                        "name": r.name,
                        "description": r.description,
                        "mimeType": r.mime_type
                    }
                    for r in resources
                ]
            }
        )

    async def _handle_resources_read(self, request: MCPRequest) -> MCPResponse:
        """Handle resources/read request."""
        params = request.params or {}
        uri = params.get("uri")

        if not uri:
            return create_error_response(
                request_id=request.id,
                code=ERROR_INVALID_PARAMS,
                message="Missing required parameter: uri"
            )

        try:
            data = await self.resources.fetch(uri, params)

            return create_response(
                request_id=request.id,
                result={
                    "contents": [{
                        "uri": uri,
                        "mimeType": self.resources.get(uri).mime_type,
                        "text": str(data) if not isinstance(data, dict) else None,
                        "blob": None  # Binary data support could be added
                    }]
                }
            )

        except ValueError as e:
            return create_error_response(
                request_id=request.id,
                code=ERROR_INVALID_PARAMS,
                message=str(e)
            )

    async def _handle_tools_list(self, request: MCPRequest) -> MCPResponse:
        """Handle tools/list request."""
        tools = self.tools.list()

        return create_response(
            request_id=request.id,
            result={
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": t.input_schema
                    }
                    for t in tools
                ]
            }
        )

    async def _handle_tools_call(self, request: MCPRequest) -> MCPResponse:
        """Handle tools/call request."""
        params = request.params or {}
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name:
            return create_error_response(
                request_id=request.id,
                code=ERROR_INVALID_PARAMS,
                message="Missing required parameter: name"
            )

        try:
            result = await self.tools.execute(name, arguments)

            return create_response(
                request_id=request.id,
                result={
                    "content": [{
                        "type": "text",
                        "text": str(result) if not isinstance(result, dict) else None
                    }] if result is not None else [],
                    "isError": False
                }
            )

        except ValueError as e:
            return create_error_response(
                request_id=request.id,
                code=ERROR_INVALID_PARAMS,
                message=str(e)
            )

    async def start(
        self,
        transport: str = "http",
        host: str = "localhost",
        port: int = 3000,
        **kwargs
    ):
        """
        Start the MCP server.

        Args:
            transport: Transport type ("http", "sse", "stdio")
            host: Host to bind to (for HTTP/SSE)
            port: Port to bind to (for HTTP/SSE)
            **kwargs: Additional transport-specific options

        Example:
            >>> await server.start(transport="http", port=3000)
        """
        # Import transport dynamically to avoid circular imports
        from .transports import create_transport

        self.transport = create_transport(
            transport_type=transport,
            server=self,
            host=host,
            port=port,
            **kwargs
        )

        await self.transport.start()

    async def stop(self):
        """Stop the MCP server."""
        if self.transport:
            await self.transport.stop()

    def info(self) -> Dict[str, Any]:
        """
        Get server information.

        Returns:
            Server info dictionary
        """
        return {
            "name": self.name,
            "version": self.version,
            "capabilities": self.capabilities,
            "resources_count": len(self.resources),
            "tools_count": len(self.tools)
        }

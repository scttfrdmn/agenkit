"""
MCP Transport Implementations.

Implements HTTP, SSE, and stdio transports for MCP protocol.

References:
    - MCP Specification: https://modelcontextprotocol.io/
"""

from typing import Optional, TYPE_CHECKING
import asyncio
import sys
import json
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from .server import MCPServer

from .message import MCPRequest, MCPResponse


class Transport(ABC):
    """Base class for MCP transports."""

    def __init__(self, server: "MCPServer"):
        """
        Initialize transport.

        Args:
            server: MCP server instance
        """
        self.server = server

    @abstractmethod
    async def start(self):
        """Start the transport."""
        pass

    @abstractmethod
    async def stop(self):
        """Stop the transport."""
        pass


class StdioTransport(Transport):
    """
    Standard input/output transport.

    Used by Claude Desktop and other applications that spawn MCP servers
    as subprocesses and communicate via stdin/stdout.

    This is the primary transport for Claude Desktop integration.
    """

    def __init__(self, server: "MCPServer"):
        """
        Initialize stdio transport.

        Args:
            server: MCP server instance
        """
        super().__init__(server)
        self.running = False

    async def start(self):
        """Start stdio transport."""
        self.running = True

        # Write server info to stderr for debugging
        sys.stderr.write(f"MCP Server '{self.server.name}' starting on stdio\n")
        sys.stderr.flush()

        try:
            # Read requests from stdin
            while self.running:
                try:
                    # Read line from stdin
                    line = await asyncio.get_event_loop().run_in_executor(
                        None, sys.stdin.readline
                    )

                    if not line:
                        # EOF reached
                        break

                    line = line.strip()
                    if not line:
                        continue

                    # Parse request
                    request_data = json.loads(line)
                    request = MCPRequest.from_dict(request_data)

                    # Handle request
                    response = await self.server.handle_request(request)

                    # Write response to stdout
                    response_json = response.to_json()
                    sys.stdout.write(response_json + "\n")
                    sys.stdout.flush()

                except json.JSONDecodeError as e:
                    sys.stderr.write(f"JSON decode error: {e}\n")
                    sys.stderr.flush()
                except Exception as e:
                    sys.stderr.write(f"Error handling request: {e}\n")
                    sys.stderr.flush()

        finally:
            self.running = False

    async def stop(self):
        """Stop stdio transport."""
        self.running = False


class HTTPTransport(Transport):
    """
    HTTP transport for MCP.

    Simple HTTP server that handles MCP requests via POST to a single endpoint.
    """

    def __init__(
        self,
        server: "MCPServer",
        host: str = "localhost",
        port: int = 3000
    ):
        """
        Initialize HTTP transport.

        Args:
            server: MCP server instance
            host: Host to bind to
            port: Port to bind to
        """
        super().__init__(server)
        self.host = host
        self.port = port
        self.http_server = None

    async def start(self):
        """Start HTTP transport."""
        try:
            from aiohttp import web
        except ImportError:
            raise ImportError(
                "aiohttp is required for HTTP transport. "
                "Install with: pip install aiohttp"
            )

        app = web.Application()
        app.router.add_post("/mcp", self._handle_http_request)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        self.http_server = runner

        print(f"MCP Server '{self.server.name}' listening on http://{self.host}:{self.port}/mcp")

    async def _handle_http_request(self, http_request):
        """Handle HTTP request."""
        from aiohttp import web

        try:
            # Parse request body
            request_data = await http_request.json()
            request = MCPRequest.from_dict(request_data)

            # Handle request
            response = await self.server.handle_request(request)

            # Return response
            return web.json_response(response.to_dict())

        except Exception as e:
            return web.json_response(
                {"error": str(e)},
                status=500
            )

    async def stop(self):
        """Stop HTTP transport."""
        if self.http_server:
            await self.http_server.cleanup()


class SSETransport(Transport):
    """
    Server-Sent Events (SSE) transport for MCP.

    Allows streaming responses and notifications from server to client.
    """

    def __init__(
        self,
        server: "MCPServer",
        host: str = "localhost",
        port: int = 3000
    ):
        """
        Initialize SSE transport.

        Args:
            server: MCP server instance
            host: Host to bind to
            port: Port to bind to
        """
        super().__init__(server)
        self.host = host
        self.port = port
        self.http_server = None
        self.clients = set()

    async def start(self):
        """Start SSE transport."""
        try:
            from aiohttp import web
            from aiohttp.web import StreamResponse
        except ImportError:
            raise ImportError(
                "aiohttp is required for SSE transport. "
                "Install with: pip install aiohttp"
            )

        app = web.Application()
        app.router.add_get("/mcp/events", self._handle_sse_connection)
        app.router.add_post("/mcp", self._handle_http_request)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        self.http_server = runner

        print(f"MCP Server '{self.server.name}' with SSE on http://{self.host}:{self.port}/mcp")

    async def _handle_sse_connection(self, http_request):
        """Handle SSE connection."""
        from aiohttp.web import StreamResponse

        response = StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'

        await response.prepare(http_request)

        # Add client
        self.clients.add(response)

        try:
            # Keep connection alive
            while True:
                await asyncio.sleep(30)
                await response.write(b': keepalive\n\n')
        finally:
            # Remove client
            self.clients.discard(response)

    async def _handle_http_request(self, http_request):
        """Handle HTTP request (same as HTTPTransport)."""
        from aiohttp import web

        try:
            request_data = await http_request.json()
            request = MCPRequest.from_dict(request_data)

            response = await self.server.handle_request(request)

            return web.json_response(response.to_dict())

        except Exception as e:
            return web.json_response(
                {"error": str(e)},
                status=500
            )

    async def stop(self):
        """Stop SSE transport."""
        if self.http_server:
            await self.http_server.cleanup()


def create_transport(
    transport_type: str,
    server: "MCPServer",
    **kwargs
) -> Transport:
    """
    Create a transport instance.

    Args:
        transport_type: Type of transport ("stdio", "http", "sse")
        server: MCP server instance
        **kwargs: Transport-specific options

    Returns:
        Transport instance

    Raises:
        ValueError: If transport type is unknown

    Example:
        >>> transport = create_transport("stdio", server)
        >>> await transport.start()
    """
    if transport_type == "stdio":
        return StdioTransport(server)
    elif transport_type == "http":
        return HTTPTransport(server, **kwargs)
    elif transport_type == "sse":
        return SSETransport(server, **kwargs)
    else:
        raise ValueError(f"Unknown transport type: {transport_type}")

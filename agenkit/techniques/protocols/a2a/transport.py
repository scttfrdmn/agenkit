"""
A2A Transport Layer.

Implements transport mechanisms for Agent-to-Agent communication.
Supports HTTP, gRPC, and WebSocket transports.
"""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .message import A2AMessage


class Transport(ABC):
    """Base class for A2A transports."""

    @abstractmethod
    async def send(self, message: "A2AMessage", endpoint: str) -> "A2AMessage":
        """
        Send message to endpoint.

        Args:
            message: Message to send
            endpoint: Destination endpoint

        Returns:
            Response message
        """
        pass

    @abstractmethod
    async def start_server(
        self, handler: Callable[["A2AMessage"], Awaitable["A2AMessage"]], host: str, port: int
    ):
        """
        Start transport server.

        Args:
            handler: Message handler function
            host: Host to bind to
            port: Port to bind to
        """
        pass

    @abstractmethod
    async def stop_server(self):
        """Stop transport server."""
        pass


class HTTPTransport(Transport):
    """
    HTTP transport for A2A.

    Uses HTTP POST requests to send/receive messages.
    """

    def __init__(self, timeout: float = 30.0):
        """
        Initialize HTTP transport.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.server = None

    async def send(self, message: "A2AMessage", endpoint: str) -> "A2AMessage":
        """
        Send message via HTTP POST.

        Args:
            message: Message to send
            endpoint: HTTP endpoint URL

        Returns:
            Response message
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for HTTP transport. Install with: pip install httpx"
            )

        from .message import A2AMessage

        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, json=message.to_dict(), timeout=self.timeout)

            response.raise_for_status()
            response_data = response.json()

            return A2AMessage.from_dict(response_data)

    async def start_server(
        self,
        handler: Callable[["A2AMessage"], Awaitable["A2AMessage"]],
        host: str = "0.0.0.0",  # noqa: S104 - Server must bind to all interfaces for deployment
        port: int = 8080,
    ):
        """
        Start HTTP server.

        Args:
            handler: Message handler
            host: Host to bind to
            port: Port to bind to
        """
        try:
            from aiohttp import web
        except ImportError:
            raise ImportError(
                "aiohttp is required for HTTP server. Install with: pip install aiohttp"
            )

        from .message import A2AMessage

        async def handle_request(http_request):
            """Handle HTTP request."""
            try:
                # Parse request body
                request_data = await http_request.json()
                message = A2AMessage.from_dict(request_data)

                # Handle message
                response = await handler(message)

                # Return response
                return web.json_response(response.to_dict())

            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        app = web.Application()
        app.router.add_post("/a2a", handle_request)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, host, port)
        await site.start()

        self.server = runner

        print(f"A2A HTTP server listening on http://{host}:{port}/a2a")

    async def stop_server(self):
        """Stop HTTP server."""
        if self.server:
            await self.server.cleanup()


class WebSocketTransport(Transport):
    """
    WebSocket transport for A2A.

    Provides persistent bidirectional connections for real-time communication.
    """

    def __init__(self, timeout: float = 30.0):
        """
        Initialize WebSocket transport.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.server = None
        self.connections = set()

    async def send(self, message: "A2AMessage", endpoint: str) -> "A2AMessage":
        """
        Send message via WebSocket.

        Args:
            message: Message to send
            endpoint: WebSocket endpoint URL

        Returns:
            Response message
        """
        try:
            import websockets
        except ImportError:
            raise ImportError(
                "websockets is required for WebSocket transport. "
                "Install with: pip install websockets"
            )

        from .message import A2AMessage

        async with websockets.connect(endpoint) as websocket:
            # Send message
            await websocket.send(message.to_json())

            # Wait for response with timeout
            response_str = await asyncio.wait_for(websocket.recv(), timeout=self.timeout)

            return A2AMessage.from_json(response_str)

    async def start_server(
        self,
        handler: Callable[["A2AMessage"], Awaitable["A2AMessage"]],
        host: str = "0.0.0.0",  # noqa: S104 - Server must bind to all interfaces for deployment
        port: int = 8765,
    ):
        """
        Start WebSocket server.

        Args:
            handler: Message handler
            host: Host to bind to
            port: Port to bind to
        """
        try:
            import websockets
        except ImportError:
            raise ImportError(
                "websockets is required for WebSocket server. Install with: pip install websockets"
            )

        from .message import A2AMessage

        async def handle_connection(websocket, path):
            """Handle WebSocket connection."""
            self.connections.add(websocket)

            try:
                async for message_str in websocket:
                    try:
                        # Parse message
                        message = A2AMessage.from_json(message_str)

                        # Handle message
                        response = await handler(message)

                        # Send response
                        await websocket.send(response.to_json())

                    except Exception as e:
                        # Send error response
                        error_response = {"error": str(e)}
                        await websocket.send(str(error_response))

            finally:
                self.connections.discard(websocket)

        self.server = await websockets.serve(handle_connection, host, port)

        print(f"A2A WebSocket server listening on ws://{host}:{port}")

    async def stop_server(self):
        """Stop WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()


class GRPCTransport(Transport):
    """
    gRPC transport for A2A.

    High-performance RPC protocol for agent communication.
    """

    def __init__(self, timeout: float = 30.0):
        """
        Initialize gRPC transport.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.server = None

    async def send(self, message: "A2AMessage", endpoint: str) -> "A2AMessage":
        """
        Send message via gRPC.

        Args:
            message: Message to send
            endpoint: gRPC endpoint (host:port)

        Returns:
            Response message
        """
        try:
            import grpc
        except ImportError:
            raise ImportError(
                "grpcio is required for gRPC transport. Install with: pip install grpcio"
            )

        # Create channel
        async with grpc.aio.insecure_channel(endpoint):
            # Note: In production, you'd generate proper gRPC stubs
            # For now, we'll use a simplified approach

            # Serialize message
            message.to_json().encode("utf-8")

            # Make unary call (simplified - would use proper RPC in production)
            # This is a placeholder - actual gRPC requires proto definitions
            # and generated stubs

            raise NotImplementedError(
                "gRPC transport requires proto definitions and generated stubs. "
                "Use HTTP or WebSocket transport for now, or implement gRPC stubs."
            )

    async def start_server(
        self,
        handler: Callable[["A2AMessage"], Awaitable["A2AMessage"]],
        host: str = "0.0.0.0",  # noqa: S104 - Server must bind to all interfaces for deployment
        port: int = 50051,
    ):
        """
        Start gRPC server.

        Args:
            handler: Message handler
            host: Host to bind to
            port: Port to bind to
        """
        import importlib.util

        if importlib.util.find_spec("grpc") is None:
            raise ImportError(
                "grpcio is required for gRPC server. Install with: pip install grpcio"
            )

        # Note: This is a placeholder
        # Actual gRPC server requires proto definitions and generated stubs

        raise NotImplementedError(
            "gRPC server requires proto definitions and generated stubs. "
            "Use HTTP or WebSocket transport for now, or implement gRPC stubs."
        )

    async def stop_server(self):
        """Stop gRPC server."""
        if self.server:
            await self.server.stop(grace=5)


def create_transport(transport_type: str, timeout: float = 30.0) -> Transport:
    """
    Create transport instance.

    Args:
        transport_type: Transport type ("http", "websocket", "grpc")
        timeout: Request timeout in seconds

    Returns:
        Transport instance

    Raises:
        ValueError: If transport type is unknown
    """
    if transport_type == "http":
        return HTTPTransport(timeout=timeout)
    elif transport_type == "websocket":
        return WebSocketTransport(timeout=timeout)
    elif transport_type == "grpc":
        return GRPCTransport(timeout=timeout)
    else:
        raise ValueError(f"Unknown transport type: {transport_type}")

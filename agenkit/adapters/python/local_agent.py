"""Local agent server for protocol adapter."""

import asyncio
import logging
import os
import struct
from pathlib import Path
from typing import Any

from websockets.asyncio.server import ServerConnection, serve

from agenkit.interfaces import Agent

from .codec import (
    create_error_envelope,
    create_response_envelope,
    create_stream_chunk_envelope,
    create_stream_end_envelope,
    decode_bytes,
    decode_message,
    encode_bytes,
    encode_message,
)
from .errors import InvalidMessageError, ProtocolError
from .transport import Transport

logger = logging.getLogger(__name__)


class LocalAgent:
    """Server-side wrapper for exposing a local agent over the protocol adapter.

    This class listens for incoming requests and forwards them to the wrapped agent.
    """

    def __init__(
        self,
        agent: Agent,
        endpoint: str | None = None,
        transport: Transport | None = None,
    ):
        """Initialize local agent server.

        Args:
            agent: The local agent to expose
            endpoint: Endpoint URL (e.g., "unix:///tmp/agent.sock")
            transport: Custom transport (if endpoint not provided)

        Raises:
            ValueError: If neither endpoint nor transport is provided
        """
        if endpoint is None and transport is None:
            raise ValueError("Either endpoint or transport must be provided")

        self._agent = agent
        self._endpoint = endpoint
        self._transport = transport
        self._server: asyncio.Server | None = None
        self._ws_server: Any = None  # WebSocket server instance
        self._running = False
        self._tasks: set[asyncio.Task[Any]] = set()

    def _create_unix_server(self, socket_path: str) -> asyncio.Server:
        """Create Unix socket server (synchronous wrapper).

        This is a helper to work around the async context manager requirement.

        Args:
            socket_path: Path to Unix socket

        Returns:
            Server object
        """
        # Ensure directory exists
        socket_dir = Path(socket_path).parent
        socket_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Remove existing socket file if present
        if os.path.exists(socket_path):
            os.remove(socket_path)

        # This will be awaited in start()
        return socket_path  # type: ignore

    async def start(self) -> None:
        """Start the agent server.

        Raises:
            RuntimeError: If server is already running
            ValueError: If endpoint format is not supported
        """
        if self._running:
            raise RuntimeError("Server is already running")

        if self._endpoint:
            # Create server based on endpoint type
            if self._endpoint.startswith("unix://"):
                socket_path = self._endpoint[7:]  # Remove "unix://" prefix

                # Ensure directory exists
                socket_dir = Path(socket_path).parent
                socket_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

                # Remove existing socket file if present
                if os.path.exists(socket_path):
                    os.remove(socket_path)

                # Start Unix socket server
                self._server = await asyncio.start_unix_server(
                    self._handle_client, path=socket_path
                )

                # Set socket permissions
                os.chmod(socket_path, 0o600)

                logger.info(f"Agent '{self._agent.name}' listening on {socket_path}")
            elif self._endpoint.startswith("tcp://"):
                # Parse TCP endpoint: tcp://host:port
                tcp_parts = self._endpoint[6:]  # Remove "tcp://" prefix
                if ":" not in tcp_parts:
                    raise ValueError(f"Invalid TCP endpoint format: {self._endpoint}")

                host, port_str = tcp_parts.rsplit(":", 1)
                try:
                    port = int(port_str)
                except ValueError:
                    raise ValueError(f"Invalid port in endpoint: {self._endpoint}")

                # Start TCP server
                self._server = await asyncio.start_server(
                    self._handle_client, host=host, port=port
                )

                logger.info(f"Agent '{self._agent.name}' listening on {host}:{port}")
            elif self._endpoint.startswith("ws://") or self._endpoint.startswith("wss://"):
                # Parse WebSocket endpoint: ws://host:port or wss://host:port
                url_parts = self._endpoint.split("://", 1)[1]  # Remove ws:// or wss:// prefix
                if ":" not in url_parts:
                    raise ValueError(f"Invalid WebSocket endpoint format: {self._endpoint}")

                host, port_str = url_parts.rsplit(":", 1)
                try:
                    port = int(port_str)
                except ValueError:
                    raise ValueError(f"Invalid port in endpoint: {self._endpoint}")

                # Start WebSocket server
                self._ws_server = await serve(
                    self._handle_websocket_client,
                    host=host,
                    port=port,
                    max_size=10 * 1024 * 1024,  # 10 MB max message size
                )

                logger.info(f"Agent '{self._agent.name}' listening on WebSocket {host}:{port}")
            else:
                raise ValueError(f"Unsupported endpoint format: {self._endpoint}")
        elif self._transport:
            # For custom transports (like in-memory), don't create a server
            # Just mark as running and wait for direct calls
            logger.info(f"Agent '{self._agent.name}' using custom transport")

        self._running = True

    async def stop(self) -> None:
        """Stop the agent server."""
        if not self._running:
            return

        self._running = False

        # Cancel all active client tasks
        for task in self._tasks:
            task.cancel()

        # Wait for all tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        # Close server if using endpoint-based server
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        # Close WebSocket server if running
        if self._ws_server:
            self._ws_server.close()
            await self._ws_server.wait_closed()
            self._ws_server = None

        # Clean up Unix socket file
        if self._endpoint and self._endpoint.startswith("unix://"):
            socket_path = self._endpoint[7:]
            if os.path.exists(socket_path):
                os.remove(socket_path)

        logger.info(f"Agent '{self._agent.name}' stopped")

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a client connection.

        Args:
            reader: Stream reader for receiving data
            writer: Stream writer for sending data
        """
        client_addr = writer.get_extra_info("peername")
        logger.debug(f"Client connected: {client_addr}")

        # Create a task for this client
        task = asyncio.create_task(self._handle_client_requests(reader, writer))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _handle_client_requests(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle requests from a client connection.

        Args:
            reader: Stream reader for receiving data
            writer: Stream writer for sending data
        """
        try:
            while self._running:
                # Read length prefix (4 bytes)
                try:
                    length_bytes = await asyncio.wait_for(reader.readexactly(4), timeout=60.0)
                except asyncio.TimeoutError:
                    # No data for 60 seconds - close connection
                    break
                except asyncio.IncompleteReadError:
                    # Connection closed
                    break

                if not length_bytes:
                    break

                # Parse length
                import struct

                length = struct.unpack(">I", length_bytes)[0]

                # Read payload
                try:
                    payload_bytes = await reader.readexactly(length)
                except asyncio.IncompleteReadError:
                    logger.error("Incomplete message received")
                    break

                # Check if this is a streaming request
                try:
                    request = decode_bytes(payload_bytes)
                    method = request.get("payload", {}).get("method")

                    if method == "stream":
                        # Handle streaming request
                        await self._process_stream_request(request, writer)
                    else:
                        # Handle regular request
                        response_bytes = await self._process_request(payload_bytes)

                        # Send response with length prefix
                        response_length = struct.pack(">I", len(response_bytes))
                        writer.write(response_length + response_bytes)
                        await writer.drain()
                except Exception as e:
                    logger.error(f"Error processing request: {e}", exc_info=True)
                    # Try to send error response
                    try:
                        error_response = create_error_envelope(
                            "unknown", "INTERNAL_ERROR", f"Internal server error: {e}"
                        )
                        error_bytes = encode_bytes(error_response)
                        error_length = struct.pack(">I", len(error_bytes))
                        writer.write(error_length + error_bytes)
                        await writer.drain()
                    except Exception:
                        pass  # Best effort
                    break

        finally:
            writer.close()
            await writer.wait_closed()
            logger.debug("Client disconnected")

    async def _process_request(self, request_bytes: bytes) -> bytes:
        """Process a single request.

        Args:
            request_bytes: Request bytes

        Returns:
            Response bytes

        Raises:
            ProtocolError: If request is invalid
        """
        try:
            # Decode request
            request = decode_bytes(request_bytes)

            if request["type"] != "request":
                raise InvalidMessageError(
                    f"Expected 'request' but got '{request['type']}'", {"request": request}
                )

            request_id = request["id"]
            payload = request["payload"]
            method = payload.get("method")

            # Handle different methods
            if method == "process":
                # Process message through agent
                input_message = decode_message(payload["message"])
                output_message = await self._agent.process(input_message)

                # Create response
                response = create_response_envelope(
                    request_id, {"message": encode_message(output_message)}
                )
                return encode_bytes(response)

            else:
                raise InvalidMessageError(f"Unknown method: {method}", {"method": method})

        except ProtocolError as e:
            # Return error response
            error_response = create_error_envelope(
                request.get("id", "unknown"), e.code, e.message, e.details
            )
            return encode_bytes(error_response)
        except Exception as e:
            # Unexpected error - return generic error
            logger.error(f"Unexpected error: {e}", exc_info=True)
            error_response = create_error_envelope(
                request.get("id", "unknown") if "request" in locals() else "unknown",
                "INTERNAL_ERROR",
                str(e),
            )
            return encode_bytes(error_response)

    async def _process_stream_request(
        self, request: dict[str, Any], writer: asyncio.StreamWriter
    ) -> None:
        """Process a streaming request.

        Args:
            request: Decoded request envelope
            writer: Stream writer for sending responses

        Raises:
            ProtocolError: If request is invalid
        """

        try:
            if request["type"] != "request":
                raise InvalidMessageError(
                    f"Expected 'request' but got '{request['type']}'", {"request": request}
                )

            request_id = request["id"]
            payload = request["payload"]
            method = payload.get("method")

            if method != "stream":
                raise InvalidMessageError(
                    f"Expected 'stream' but got '{method}'", {"method": method}
                )

            # Decode input message
            input_message = decode_message(payload["message"])

            # Stream through agent
            async for chunk in self._agent.stream(input_message):
                # Create stream chunk envelope
                chunk_envelope = create_stream_chunk_envelope(request_id, encode_message(chunk))
                chunk_bytes = encode_bytes(chunk_envelope)

                # Send chunk with length prefix
                chunk_length = struct.pack(">I", len(chunk_bytes))
                writer.write(chunk_length + chunk_bytes)
                await writer.drain()

            # Send stream end
            end_envelope = create_stream_end_envelope(request_id)
            end_bytes = encode_bytes(end_envelope)
            end_length = struct.pack(">I", len(end_bytes))
            writer.write(end_length + end_bytes)
            await writer.drain()

        except ProtocolError as e:
            # Send error response
            error_response = create_error_envelope(
                request.get("id", "unknown"), e.code, e.message, e.details
            )
            error_bytes = encode_bytes(error_response)
            error_length = struct.pack(">I", len(error_bytes))
            writer.write(error_length + error_bytes)
            await writer.drain()
        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected error in stream: {e}", exc_info=True)
            error_response = create_error_envelope(
                request.get("id", "unknown"),
                "INTERNAL_ERROR",
                str(e),
            )
            error_bytes = encode_bytes(error_response)
            error_length = struct.pack(">I", len(error_bytes))
            writer.write(error_length + error_bytes)
            await writer.drain()

    async def _handle_websocket_client(self, websocket: ServerConnection) -> None:
        """Handle a WebSocket client connection.

        Args:
            websocket: WebSocket connection
        """
        client_addr = websocket.remote_address
        logger.debug(f"WebSocket client connected: {client_addr}")

        try:
            async for message in websocket:
                # Ensure we have bytes
                message_bytes = message.encode('utf-8') if isinstance(message, str) else message

                # Check if this is a streaming request
                try:
                    request = decode_bytes(message_bytes)
                    method = request.get("payload", {}).get("method")

                    if method == "stream":
                        # Handle streaming request
                        await self._process_websocket_stream_request(request, websocket)
                    else:
                        # Handle regular request
                        response_bytes = await self._process_request(message_bytes)

                        # Send response as binary message
                        await websocket.send(response_bytes)
                except Exception as e:
                    logger.error(f"Error processing WebSocket request: {e}", exc_info=True)
                    # Try to send error response
                    try:
                        error_response = create_error_envelope(
                            "unknown", "INTERNAL_ERROR", f"Internal server error: {e}"
                        )
                        error_bytes = encode_bytes(error_response)
                        await websocket.send(error_bytes)
                    except Exception:
                        pass  # Best effort
                    break

        except Exception as e:
            logger.error(f"WebSocket connection error: {e}", exc_info=True)
        finally:
            logger.debug(f"WebSocket client disconnected: {client_addr}")

    async def _process_websocket_stream_request(
        self, request: dict[str, Any], websocket: ServerConnection
    ) -> None:
        """Process a streaming request over WebSocket.

        Args:
            request: Decoded request envelope
            websocket: WebSocket connection for sending responses

        Raises:
            ProtocolError: If request is invalid
        """
        try:
            if request["type"] != "request":
                raise InvalidMessageError(
                    f"Expected 'request' but got '{request['type']}'", {"request": request}
                )

            request_id = request["id"]
            payload = request["payload"]
            method = payload.get("method")

            if method != "stream":
                raise InvalidMessageError(
                    f"Expected 'stream' but got '{method}'", {"method": method}
                )

            # Decode input message
            input_message = decode_message(payload["message"])

            # Stream through agent
            async for chunk in self._agent.stream(input_message):
                # Create stream chunk envelope
                chunk_envelope = create_stream_chunk_envelope(request_id, encode_message(chunk))
                chunk_bytes = encode_bytes(chunk_envelope)

                # Send chunk as binary message
                await websocket.send(chunk_bytes)

            # Send stream end
            end_envelope = create_stream_end_envelope(request_id)
            end_bytes = encode_bytes(end_envelope)
            await websocket.send(end_bytes)

        except ProtocolError as e:
            # Send error response
            error_response = create_error_envelope(
                request.get("id", "unknown"), e.code, e.message, e.details
            )
            error_bytes = encode_bytes(error_response)
            await websocket.send(error_bytes)
        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected error in WebSocket stream: {e}", exc_info=True)
            error_response = create_error_envelope(
                request.get("id", "unknown"),
                "INTERNAL_ERROR",
                str(e),
            )
            error_bytes = encode_bytes(error_response)
            await websocket.send(error_bytes)

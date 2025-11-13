"""gRPC transport implementation for protocol adapter."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import grpc
from grpc import aio

from proto import agent_pb2, agent_pb2_grpc

from .errors import ConnectionClosedError, InvalidMessageError, MalformedPayloadError
from .errors import ConnectionError as ConnError
from .transport import Transport


class GRPCTransport(Transport):
    """gRPC transport for agent communication.

    This transport implements the Transport interface using gRPC for communication.
    It converts between agenkit's JSON protocol and protobuf messages.

    Supported URL format: grpc://host:port

    Example:
        >>> transport = GRPCTransport("grpc://localhost:50051")
        >>> await transport.connect()
        >>> await transport.send_framed(b'{"type": "request", ...}')
        >>> response = await transport.receive_framed()
    """

    def __init__(self, url: str):
        """Initialize gRPC transport.

        Args:
            url: gRPC endpoint URL (e.g., "grpc://localhost:50051")

        Raises:
            ValueError: If URL format is invalid
        """
        self._url = url
        self._channel: aio.Channel | None = None
        self._stub: agent_pb2_grpc.AgentServiceStub | None = None
        self._connected = False
        self._response_queue: asyncio.Queue[bytes] | None = None
        self._lock = asyncio.Lock()

        # Parse URL
        parsed = urlparse(url)
        if parsed.scheme != "grpc":
            raise ValueError(f"Invalid gRPC URL scheme: {parsed.scheme}")

        if not parsed.hostname:
            raise ValueError(f"Missing hostname in gRPC URL: {url}")

        self._host = parsed.hostname
        self._port = parsed.port or 50051  # Default gRPC port

    async def connect(self) -> None:
        """Establish gRPC connection.

        Raises:
            ConnectionError: If connection fails
        """
        if self._connected:
            return

        try:
            # Create async gRPC channel
            target = f"{self._host}:{self._port}"
            self._channel = aio.insecure_channel(target)

            # Create stub
            self._stub = agent_pb2_grpc.AgentServiceStub(self._channel)

            # Test connection by checking channel state
            # Note: gRPC channels are lazy, so we'll mark as connected
            # and let actual RPC calls fail if the server is unavailable
            self._connected = True
            self._response_queue = asyncio.Queue()

        except Exception as e:
            raise ConnError(
                f"Failed to connect to gRPC server at {self._host}:{self._port}: {e}"
            ) from e

    async def send(self, data: bytes) -> None:
        """Send data over gRPC (not used - gRPC has native framing).

        This method is not used for gRPC transport as gRPC has native framing.
        Use send_framed() instead.

        Args:
            data: Bytes to send

        Raises:
            NotImplementedError: Always raised as this method is not used
        """
        raise NotImplementedError("Use send_framed() for gRPC transport")

    async def receive(self) -> bytes:
        """Receive data from gRPC (not used - gRPC has native framing).

        This method is not used for gRPC transport as gRPC has native framing.
        Use receive_framed() instead.

        Returns:
            Received bytes

        Raises:
            NotImplementedError: Always raised as this method is not used
        """
        raise NotImplementedError("Use receive_framed() for gRPC transport")

    async def send_framed(self, data: bytes) -> None:
        """Send length-prefixed framed data via gRPC.

        This method converts the JSON envelope to a protobuf Request,
        makes the appropriate gRPC call (Process or ProcessStream),
        and stores the response for later retrieval.

        Args:
            data: JSON-encoded request envelope

        Raises:
            ConnectionError: If not connected or RPC fails
            MalformedPayloadError: If data cannot be decoded
        """
        if not self.is_connected:
            raise ConnError("Not connected")

        assert self._stub is not None
        assert self._response_queue is not None

        try:
            # Decode JSON envelope
            envelope = json.loads(data.decode("utf-8"))

            # Convert JSON envelope to protobuf Request
            pb_request = self._json_to_protobuf_request(envelope)

            # Determine if this is a streaming request
            method = envelope.get("payload", {}).get("method", "process")
            is_streaming = method == "stream"

            async with self._lock:
                if is_streaming:
                    # Use ProcessStream RPC
                    try:
                        stream = self._stub.ProcessStream(pb_request, timeout=30.0)

                        # Process stream chunks
                        async for chunk in stream:
                            # Convert protobuf StreamChunk to JSON envelope
                            json_envelope = self._protobuf_chunk_to_json(chunk)
                            json_bytes = json.dumps(json_envelope).encode("utf-8")
                            await self._response_queue.put(json_bytes)

                    except grpc.aio.AioRpcError as e:
                        # Convert gRPC error to JSON error envelope
                        error_envelope = self._create_error_envelope(
                            envelope.get("id", "unknown"),
                            self._grpc_status_to_error_code(e.code()),
                            e.details() or str(e)
                        )
                        error_bytes = json.dumps(error_envelope).encode("utf-8")
                        await self._response_queue.put(error_bytes)

                else:
                    # Use unary Process RPC
                    try:
                        pb_response: agent_pb2.Response = await self._stub.Process(
                            pb_request, timeout=30.0
                        )

                        # Convert protobuf Response to JSON envelope
                        json_envelope = self._protobuf_response_to_json(pb_response)
                        json_bytes = json.dumps(json_envelope).encode("utf-8")
                        await self._response_queue.put(json_bytes)

                    except grpc.aio.AioRpcError as e:
                        # Convert gRPC error to JSON error envelope
                        error_envelope = self._create_error_envelope(
                            envelope.get("id", "unknown"),
                            self._grpc_status_to_error_code(e.code()),
                            e.details() or str(e)
                        )
                        error_bytes = json.dumps(error_envelope).encode("utf-8")
                        await self._response_queue.put(error_bytes)

        except json.JSONDecodeError as e:
            raise MalformedPayloadError(f"Failed to decode JSON: {e}") from e
        except Exception as e:
            raise ConnError(f"Failed to send data via gRPC: {e}") from e

    async def receive_framed(self) -> bytes:
        """Receive length-prefixed framed data via gRPC.

        This method retrieves the response that was stored during send_framed().

        Returns:
            Received data (JSON-encoded response envelope)

        Raises:
            ConnectionError: If not connected
            ConnectionClosedError: If connection is closed
        """
        if not self.is_connected:
            raise ConnError("Not connected")

        assert self._response_queue is not None

        try:
            # Get response from queue (with timeout to detect disconnection)
            data = await asyncio.wait_for(self._response_queue.get(), timeout=60.0)
            return data

        except asyncio.TimeoutError:
            raise ConnectionClosedError("Response timeout - connection may be closed")
        except Exception as e:
            raise ConnError(f"Failed to receive data via gRPC: {e}") from e

    async def receive_exactly(self, n: int) -> bytes:
        """Receive exactly n bytes (not used for gRPC).

        gRPC has native framing, so this method is not needed.

        Args:
            n: Number of bytes to receive

        Returns:
            Exactly n bytes

        Raises:
            NotImplementedError: Always raised as this method is not used
        """
        raise NotImplementedError("gRPC has native framing - use receive_framed()")

    async def close(self) -> None:
        """Close the gRPC connection."""
        if self._channel:
            await self._channel.close()
        self._channel = None
        self._stub = None
        self._connected = False
        self._response_queue = None

    @property
    def is_connected(self) -> bool:
        """Check if gRPC transport is connected.

        Returns:
            True if connected, False otherwise
        """
        return self._connected and self._channel is not None and self._stub is not None

    def _json_to_protobuf_request(self, envelope: dict[str, Any]) -> agent_pb2.Request:
        """Convert JSON request envelope to protobuf Request.

        Args:
            envelope: JSON request envelope

        Returns:
            Protobuf Request message

        Raises:
            InvalidMessageError: If envelope is invalid
        """
        try:
            payload = envelope.get("payload", {})

            # Create protobuf Request
            request = agent_pb2.Request(
                version=envelope.get("version", "1.0"),
                id=envelope.get("id", ""),
                timestamp=envelope.get("timestamp", datetime.now(timezone.utc).isoformat()),
                method=payload.get("method", "process"),
                agent_name=payload.get("agent_name", "")
            )

            # Convert messages if present (support both "message" and "messages")
            if "message" in payload:
                # Single message format
                msg = payload["message"]
                pb_msg = agent_pb2.Message(
                    role=msg.get("role", ""),
                    content=self._serialize_content(msg.get("content")),
                    timestamp=msg.get("timestamp", "")
                )
                # Add metadata
                if "metadata" in msg:
                    for key, value in msg["metadata"].items():
                        pb_msg.metadata[key] = str(value)
                request.messages.append(pb_msg)
            elif "messages" in payload:
                # Multiple messages format
                for msg in payload["messages"]:
                    pb_msg = agent_pb2.Message(
                        role=msg.get("role", ""),
                        content=self._serialize_content(msg.get("content")),
                        timestamp=msg.get("timestamp", "")
                    )
                    # Add metadata
                    if "metadata" in msg:
                        for key, value in msg["metadata"].items():
                            pb_msg.metadata[key] = str(value)
                    request.messages.append(pb_msg)

            # Convert tool_call if present
            if "tool_call" in payload:
                tool_call = payload["tool_call"]
                pb_tool_call = agent_pb2.ToolCall(
                    name=tool_call.get("name", ""),
                    arguments=json.dumps(tool_call.get("arguments", {}))
                )
                if "metadata" in tool_call:
                    for key, value in tool_call["metadata"].items():
                        pb_tool_call.metadata[key] = str(value)
                request.tool_call.CopyFrom(pb_tool_call)

            # Add metadata
            if "metadata" in payload:
                for key, value in payload["metadata"].items():
                    request.metadata[key] = str(value)

            return request

        except Exception as e:
            raise InvalidMessageError(f"Failed to convert JSON to protobuf: {e}") from e

    def _protobuf_response_to_json(self, response: agent_pb2.Response) -> dict[str, Any]:
        """Convert protobuf Response to JSON response envelope.

        Args:
            response: Protobuf Response message

        Returns:
            JSON response envelope
        """
        payload: dict[str, Any] = {}

        # Handle different response types
        if response.type == agent_pb2.RESPONSE_TYPE_MESSAGE and response.HasField("message"):
            payload["message"] = {
                "role": response.message.role,
                "content": self._deserialize_content(response.message.content),
                "metadata": dict(response.message.metadata),
                "timestamp": response.message.timestamp
            }

        elif (
            response.type == agent_pb2.RESPONSE_TYPE_TOOL_RESULT
            and response.HasField("tool_result")
        ):
            payload["tool_result"] = {
                "success": response.tool_result.success,
                "data": self._deserialize_content(response.tool_result.data),
                "error": response.tool_result.error if response.tool_result.error else None,
                "metadata": dict(response.tool_result.metadata)
            }

        elif response.type == agent_pb2.RESPONSE_TYPE_ERROR and response.HasField("error"):
            return {
                "version": response.version,
                "type": "error",
                "id": response.id,
                "timestamp": response.timestamp,
                "payload": {
                    "error_code": response.error.code,
                    "error_message": response.error.message,
                    "error_details": dict(response.error.details)
                }
            }

        # Add metadata
        if response.metadata:
            payload["metadata"] = dict(response.metadata)

        return {
            "version": response.version,
            "type": "response",
            "id": response.id,
            "timestamp": response.timestamp,
            "payload": payload
        }

    def _protobuf_chunk_to_json(self, chunk: agent_pb2.StreamChunk) -> dict[str, Any]:
        """Convert protobuf StreamChunk to JSON stream envelope.

        Args:
            chunk: Protobuf StreamChunk message

        Returns:
            JSON stream envelope (stream_chunk or stream_end)
        """
        if chunk.type == agent_pb2.CHUNK_TYPE_END:
            return {
                "version": chunk.version,
                "type": "stream_end",
                "id": chunk.id,
                "timestamp": chunk.timestamp,
                "payload": {}
            }

        elif chunk.type == agent_pb2.CHUNK_TYPE_ERROR and chunk.HasField("error"):
            return {
                "version": chunk.version,
                "type": "error",
                "id": chunk.id,
                "timestamp": chunk.timestamp,
                "payload": {
                    "error_code": chunk.error.code,
                    "error_message": chunk.error.message,
                    "error_details": dict(chunk.error.details)
                }
            }

        elif chunk.type == agent_pb2.CHUNK_TYPE_MESSAGE and chunk.HasField("message"):
            return {
                "version": chunk.version,
                "type": "stream_chunk",
                "id": chunk.id,
                "timestamp": chunk.timestamp,
                "payload": {
                    "message": {
                        "role": chunk.message.role,
                        "content": self._deserialize_content(chunk.message.content),
                        "metadata": dict(chunk.message.metadata),
                        "timestamp": chunk.message.timestamp
                    }
                }
            }

        else:
            # Unknown chunk type
            return {
                "version": chunk.version,
                "type": "stream_chunk",
                "id": chunk.id,
                "timestamp": chunk.timestamp,
                "payload": {}
            }

    def _serialize_content(self, content: Any) -> str:
        """Serialize content to string for protobuf.

        Args:
            content: Content to serialize

        Returns:
            String representation of content
        """
        if isinstance(content, str):
            return content
        else:
            return json.dumps(content)

    def _deserialize_content(self, content: str) -> Any:
        """Deserialize content from string.

        Args:
            content: String content

        Returns:
            Deserialized content (str or parsed JSON)
        """
        if not content:
            return content

        # Try to parse as JSON, fall back to string
        try:
            return json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return content

    def _create_error_envelope(
        self, request_id: str, error_code: str, error_message: str
    ) -> dict[str, Any]:
        """Create a JSON error envelope.

        Args:
            request_id: Request ID
            error_code: Error code
            error_message: Error message

        Returns:
            JSON error envelope
        """
        return {
            "version": "1.0",
            "type": "error",
            "id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "error_code": error_code,
                "error_message": error_message,
                "error_details": {}
            }
        }

    def _grpc_status_to_error_code(self, status_code: grpc.StatusCode) -> str:
        """Convert gRPC status code to error code string.

        Args:
            status_code: gRPC status code

        Returns:
            Error code string
        """
        mapping = {
            grpc.StatusCode.UNAVAILABLE: "CONNECTION_FAILED",
            grpc.StatusCode.DEADLINE_EXCEEDED: "CONNECTION_TIMEOUT",
            grpc.StatusCode.CANCELLED: "CONNECTION_CLOSED",
            grpc.StatusCode.NOT_FOUND: "AGENT_NOT_FOUND",
            grpc.StatusCode.INVALID_ARGUMENT: "INVALID_MESSAGE",
            grpc.StatusCode.FAILED_PRECONDITION: "AGENT_UNAVAILABLE",
            grpc.StatusCode.UNIMPLEMENTED: "UNSUPPORTED_VERSION",
        }
        return mapping.get(status_code, "CONNECTION_FAILED")

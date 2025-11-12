"""Tests for gRPC transport implementation."""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest

from agenkit.adapters.python.errors import (
    ConnectionClosedError,
    ConnectionError as ConnError,
    InvalidMessageError,
    MalformedPayloadError,
)
from agenkit.adapters.python.grpc_transport import GRPCTransport
from proto import agent_pb2


class TestGRPCTransportInit:
    """Tests for GRPCTransport initialization."""

    def test_valid_url(self):
        """Test initialization with valid gRPC URL."""
        transport = GRPCTransport("grpc://localhost:50051")
        assert transport._host == "localhost"
        assert transport._port == 50051

    def test_valid_url_default_port(self):
        """Test initialization with default port."""
        transport = GRPCTransport("grpc://example.com")
        assert transport._host == "example.com"
        assert transport._port == 50051

    def test_invalid_scheme(self):
        """Test initialization with invalid scheme."""
        with pytest.raises(ValueError, match="Invalid gRPC URL scheme"):
            GRPCTransport("http://localhost:50051")

    def test_missing_hostname(self):
        """Test initialization with missing hostname."""
        with pytest.raises(ValueError, match="Missing hostname"):
            GRPCTransport("grpc://")


class TestGRPCTransportConnection:
    """Tests for gRPC transport connection management."""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection."""
        transport = GRPCTransport("grpc://localhost:50051")

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel") as mock_channel:
            mock_channel.return_value = MagicMock()
            await transport.connect()

            assert transport.is_connected
            mock_channel.assert_called_once_with("localhost:50051")

    @pytest.mark.asyncio
    async def test_connect_already_connected(self):
        """Test connecting when already connected."""
        transport = GRPCTransport("grpc://localhost:50051")

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel") as mock_channel:
            mock_channel.return_value = MagicMock()
            await transport.connect()
            await transport.connect()  # Should not create new channel

            assert mock_channel.call_count == 1

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure."""
        transport = GRPCTransport("grpc://localhost:50051")

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel") as mock_channel:
            mock_channel.side_effect = Exception("Connection failed")

            with pytest.raises(ConnError, match="Failed to connect"):
                await transport.connect()

            assert not transport.is_connected

    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing connection."""
        transport = GRPCTransport("grpc://localhost:50051")

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel") as mock_channel:
            mock_ch = MagicMock()
            mock_ch.close = AsyncMock()
            mock_channel.return_value = mock_ch

            await transport.connect()
            assert transport.is_connected

            await transport.close()
            assert not transport.is_connected
            mock_ch.close.assert_called_once()


class TestGRPCTransportUnaryRPC:
    """Tests for unary RPC operations."""

    @pytest.mark.asyncio
    async def test_send_receive_unary_success(self):
        """Test successful unary RPC."""
        transport = GRPCTransport("grpc://localhost:50051")

        # Create request envelope
        request_envelope = {
            "version": "1.0",
            "type": "request",
            "id": "test-123",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "method": "process",
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello",
                        "metadata": {},
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                ]
            }
        }

        # Create mock response
        mock_response = agent_pb2.Response(
            version="1.0",
            id="test-123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=agent_pb2.RESPONSE_TYPE_MESSAGE,
            message=agent_pb2.Message(
                role="assistant",
                content="Hello back!",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        )

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel") as mock_channel:
            mock_ch = MagicMock()
            mock_stub = MagicMock()
            mock_stub.Process = AsyncMock(return_value=mock_response)
            mock_channel.return_value = mock_ch

            with patch("agenkit.adapters.python.grpc_transport.agent_pb2_grpc.AgentServiceStub") as mock_stub_class:
                mock_stub_class.return_value = mock_stub

                await transport.connect()

                # Send request
                request_bytes = json.dumps(request_envelope).encode("utf-8")
                await transport.send_framed(request_bytes)

                # Receive response
                response_bytes = await transport.receive_framed()
                response = json.loads(response_bytes.decode("utf-8"))

                assert response["type"] == "response"
                assert response["id"] == "test-123"
                assert response["payload"]["message"]["role"] == "assistant"
                assert response["payload"]["message"]["content"] == "Hello back!"

    @pytest.mark.asyncio
    async def test_send_not_connected(self):
        """Test sending when not connected."""
        transport = GRPCTransport("grpc://localhost:50051")

        request_envelope = {
            "version": "1.0",
            "type": "request",
            "id": "test-123",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"method": "process", "messages": []}
        }

        request_bytes = json.dumps(request_envelope).encode("utf-8")

        with pytest.raises(ConnError, match="Not connected"):
            await transport.send_framed(request_bytes)

    @pytest.mark.asyncio
    async def test_receive_not_connected(self):
        """Test receiving when not connected."""
        transport = GRPCTransport("grpc://localhost:50051")

        with pytest.raises(ConnError, match="Not connected"):
            await transport.receive_framed()

    @pytest.mark.asyncio
    async def test_send_invalid_json(self):
        """Test sending invalid JSON."""
        transport = GRPCTransport("grpc://localhost:50051")

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel"):
            await transport.connect()

            with pytest.raises(MalformedPayloadError, match="Failed to decode JSON"):
                await transport.send_framed(b"invalid json")

    @pytest.mark.asyncio
    async def test_unary_rpc_error(self):
        """Test handling gRPC errors in unary RPC."""
        transport = GRPCTransport("grpc://localhost:50051")

        request_envelope = {
            "version": "1.0",
            "type": "request",
            "id": "test-123",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"method": "process", "messages": []}
        }

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel") as mock_channel:
            mock_ch = MagicMock()
            mock_stub = MagicMock()
            mock_stub.Process = AsyncMock(
                side_effect=grpc.aio.AioRpcError(
                    code=grpc.StatusCode.UNAVAILABLE,
                    initial_metadata=None,
                    trailing_metadata=None,
                    details="Service unavailable"
                )
            )
            mock_channel.return_value = mock_ch

            with patch("agenkit.adapters.python.grpc_transport.agent_pb2_grpc.AgentServiceStub") as mock_stub_class:
                mock_stub_class.return_value = mock_stub

                await transport.connect()

                request_bytes = json.dumps(request_envelope).encode("utf-8")
                await transport.send_framed(request_bytes)

                response_bytes = await transport.receive_framed()
                response = json.loads(response_bytes.decode("utf-8"))

                assert response["type"] == "error"
                assert response["payload"]["error_code"] == "CONNECTION_FAILED"


class TestGRPCTransportStreamingRPC:
    """Tests for streaming RPC operations."""

    @pytest.mark.asyncio
    async def test_send_receive_streaming_success(self):
        """Test successful streaming RPC."""
        transport = GRPCTransport("grpc://localhost:50051")

        request_envelope = {
            "version": "1.0",
            "type": "request",
            "id": "test-123",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "method": "stream",
                "messages": [
                    {
                        "role": "user",
                        "content": "Stream me",
                        "metadata": {},
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                ]
            }
        }

        # Create mock stream chunks
        chunks = [
            agent_pb2.StreamChunk(
                version="1.0",
                id="test-123",
                timestamp=datetime.now(timezone.utc).isoformat(),
                type=agent_pb2.CHUNK_TYPE_MESSAGE,
                message=agent_pb2.Message(
                    role="assistant",
                    content="Chunk 1",
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
            ),
            agent_pb2.StreamChunk(
                version="1.0",
                id="test-123",
                timestamp=datetime.now(timezone.utc).isoformat(),
                type=agent_pb2.CHUNK_TYPE_MESSAGE,
                message=agent_pb2.Message(
                    role="assistant",
                    content="Chunk 2",
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
            ),
            agent_pb2.StreamChunk(
                version="1.0",
                id="test-123",
                timestamp=datetime.now(timezone.utc).isoformat(),
                type=agent_pb2.CHUNK_TYPE_END
            )
        ]

        async def mock_stream(*args, **kwargs):
            for chunk in chunks:
                yield chunk

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel") as mock_channel:
            mock_ch = MagicMock()
            mock_stub = MagicMock()
            mock_stub.ProcessStream = mock_stream
            mock_channel.return_value = mock_ch

            with patch("agenkit.adapters.python.grpc_transport.agent_pb2_grpc.AgentServiceStub") as mock_stub_class:
                mock_stub_class.return_value = mock_stub

                await transport.connect()

                # Send request
                request_bytes = json.dumps(request_envelope).encode("utf-8")
                await transport.send_framed(request_bytes)

                # Receive chunks
                chunk1_bytes = await transport.receive_framed()
                chunk1 = json.loads(chunk1_bytes.decode("utf-8"))
                assert chunk1["type"] == "stream_chunk"
                assert chunk1["payload"]["message"]["content"] == "Chunk 1"

                chunk2_bytes = await transport.receive_framed()
                chunk2 = json.loads(chunk2_bytes.decode("utf-8"))
                assert chunk2["type"] == "stream_chunk"
                assert chunk2["payload"]["message"]["content"] == "Chunk 2"

                end_bytes = await transport.receive_framed()
                end = json.loads(end_bytes.decode("utf-8"))
                assert end["type"] == "stream_end"

    @pytest.mark.asyncio
    async def test_streaming_rpc_error(self):
        """Test handling gRPC errors in streaming RPC."""
        transport = GRPCTransport("grpc://localhost:50051")

        request_envelope = {
            "version": "1.0",
            "type": "request",
            "id": "test-123",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"method": "stream", "messages": []}
        }

        async def mock_stream_error(*args, **kwargs):
            # Make this an async generator that immediately raises
            if False:
                yield  # Make it a generator
            raise grpc.aio.AioRpcError(
                code=grpc.StatusCode.DEADLINE_EXCEEDED,
                initial_metadata=None,
                trailing_metadata=None,
                details="Deadline exceeded"
            )

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel") as mock_channel:
            mock_ch = MagicMock()
            mock_stub = MagicMock()
            mock_stub.ProcessStream = mock_stream_error
            mock_channel.return_value = mock_ch

            with patch("agenkit.adapters.python.grpc_transport.agent_pb2_grpc.AgentServiceStub") as mock_stub_class:
                mock_stub_class.return_value = mock_stub

                await transport.connect()

                request_bytes = json.dumps(request_envelope).encode("utf-8")
                await transport.send_framed(request_bytes)

                response_bytes = await transport.receive_framed()
                response = json.loads(response_bytes.decode("utf-8"))

                assert response["type"] == "error"
                assert response["payload"]["error_code"] == "CONNECTION_TIMEOUT"


class TestGRPCTransportProtocolConversion:
    """Tests for protocol conversion between JSON and protobuf."""

    @pytest.mark.asyncio
    async def test_convert_request_with_tool_call(self):
        """Test converting request with tool call."""
        transport = GRPCTransport("grpc://localhost:50051")

        request_envelope = {
            "version": "1.0",
            "type": "request",
            "id": "test-123",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "method": "execute",
                "tool_call": {
                    "name": "calculator",
                    "arguments": {"op": "add", "x": 1, "y": 2},
                    "metadata": {"priority": "high"}
                }
            }
        }

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel"):
            await transport.connect()

            pb_request = transport._json_to_protobuf_request(request_envelope)

            assert pb_request.method == "execute"
            assert pb_request.tool_call.name == "calculator"
            assert "add" in pb_request.tool_call.arguments
            assert pb_request.tool_call.metadata["priority"] == "high"

    @pytest.mark.asyncio
    async def test_convert_response_with_tool_result(self):
        """Test converting response with tool result."""
        transport = GRPCTransport("grpc://localhost:50051")

        pb_response = agent_pb2.Response(
            version="1.0",
            id="test-123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=agent_pb2.RESPONSE_TYPE_TOOL_RESULT,
            tool_result=agent_pb2.ToolResult(
                success=True,
                data='{"result": 3}',
                error=""
            )
        )

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel"):
            await transport.connect()

            json_envelope = transport._protobuf_response_to_json(pb_response)

            assert json_envelope["type"] == "response"
            assert json_envelope["payload"]["tool_result"]["success"] is True
            assert json_envelope["payload"]["tool_result"]["data"]["result"] == 3

    @pytest.mark.asyncio
    async def test_convert_error_response(self):
        """Test converting error response."""
        transport = GRPCTransport("grpc://localhost:50051")

        pb_response = agent_pb2.Response(
            version="1.0",
            id="test-123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=agent_pb2.RESPONSE_TYPE_ERROR,
            error=agent_pb2.Error(
                code="AGENT_NOT_FOUND",
                message="Agent not found",
                details={"agent_name": "missing"}
            )
        )

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel"):
            await transport.connect()

            json_envelope = transport._protobuf_response_to_json(pb_response)

            assert json_envelope["type"] == "error"
            assert json_envelope["payload"]["error_code"] == "AGENT_NOT_FOUND"
            assert json_envelope["payload"]["error_details"]["agent_name"] == "missing"

    @pytest.mark.asyncio
    async def test_convert_stream_chunk_with_message(self):
        """Test converting stream chunk with message."""
        transport = GRPCTransport("grpc://localhost:50051")

        pb_chunk = agent_pb2.StreamChunk(
            version="1.0",
            id="test-123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=agent_pb2.CHUNK_TYPE_MESSAGE,
            message=agent_pb2.Message(
                role="assistant",
                content='{"text": "Hello"}',
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        )

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel"):
            await transport.connect()

            json_envelope = transport._protobuf_chunk_to_json(pb_chunk)

            assert json_envelope["type"] == "stream_chunk"
            assert json_envelope["payload"]["message"]["role"] == "assistant"
            assert json_envelope["payload"]["message"]["content"]["text"] == "Hello"

    @pytest.mark.asyncio
    async def test_convert_stream_end(self):
        """Test converting stream end chunk."""
        transport = GRPCTransport("grpc://localhost:50051")

        pb_chunk = agent_pb2.StreamChunk(
            version="1.0",
            id="test-123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=agent_pb2.CHUNK_TYPE_END
        )

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel"):
            await transport.connect()

            json_envelope = transport._protobuf_chunk_to_json(pb_chunk)

            assert json_envelope["type"] == "stream_end"
            assert json_envelope["payload"] == {}

    @pytest.mark.asyncio
    async def test_serialize_deserialize_content(self):
        """Test content serialization and deserialization."""
        transport = GRPCTransport("grpc://localhost:50051")

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel"):
            await transport.connect()

            # Test string content
            assert transport._serialize_content("hello") == "hello"
            assert transport._deserialize_content("hello") == "hello"

            # Test JSON content
            json_content = {"key": "value", "number": 42}
            serialized = transport._serialize_content(json_content)
            assert isinstance(serialized, str)
            deserialized = transport._deserialize_content(serialized)
            assert deserialized == json_content

            # Test empty content
            assert transport._deserialize_content("") == ""


class TestGRPCTransportErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_grpc_status_to_error_code(self):
        """Test gRPC status code to error code conversion."""
        transport = GRPCTransport("grpc://localhost:50051")

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel"):
            await transport.connect()

            assert transport._grpc_status_to_error_code(grpc.StatusCode.UNAVAILABLE) == "CONNECTION_FAILED"
            assert transport._grpc_status_to_error_code(grpc.StatusCode.DEADLINE_EXCEEDED) == "CONNECTION_TIMEOUT"
            assert transport._grpc_status_to_error_code(grpc.StatusCode.CANCELLED) == "CONNECTION_CLOSED"
            assert transport._grpc_status_to_error_code(grpc.StatusCode.NOT_FOUND) == "AGENT_NOT_FOUND"
            assert transport._grpc_status_to_error_code(grpc.StatusCode.INVALID_ARGUMENT) == "INVALID_MESSAGE"
            assert transport._grpc_status_to_error_code(grpc.StatusCode.UNKNOWN) == "CONNECTION_FAILED"

    @pytest.mark.asyncio
    async def test_send_not_implemented(self):
        """Test that send() raises NotImplementedError."""
        transport = GRPCTransport("grpc://localhost:50051")

        with pytest.raises(NotImplementedError, match="Use send_framed"):
            await transport.send(b"data")

    @pytest.mark.asyncio
    async def test_receive_not_implemented(self):
        """Test that receive() raises NotImplementedError."""
        transport = GRPCTransport("grpc://localhost:50051")

        with pytest.raises(NotImplementedError, match="Use receive_framed"):
            await transport.receive()

    @pytest.mark.asyncio
    async def test_receive_exactly_not_implemented(self):
        """Test that receive_exactly() raises NotImplementedError."""
        transport = GRPCTransport("grpc://localhost:50051")

        with pytest.raises(NotImplementedError, match="gRPC has native framing"):
            await transport.receive_exactly(100)

    @pytest.mark.asyncio
    async def test_receive_timeout(self):
        """Test receive timeout."""
        transport = GRPCTransport("grpc://localhost:50051")

        with patch("agenkit.adapters.python.grpc_transport.aio.insecure_channel"):
            await transport.connect()

            # Don't send anything, just try to receive (should timeout)
            # Note: asyncio.wait_for raises TimeoutError in Python 3.14+
            with pytest.raises((ConnectionClosedError, TimeoutError)):
                await asyncio.wait_for(transport.receive_framed(), timeout=0.1)

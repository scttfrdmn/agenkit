"""gRPC server implementation for protocol adapter."""

import json
import logging
from datetime import datetime, timezone
from typing import Any

import grpc
from grpc import aio

from agenkit.interfaces import Agent
from proto import agent_pb2, agent_pb2_grpc

logger = logging.getLogger(__name__)


class GRPCServer(agent_pb2_grpc.AgentServiceServicer):
    """gRPC server for exposing agents over gRPC.

    This server implements the AgentService protocol, handling both unary
    and streaming RPCs. It converts between protobuf messages and agenkit's
    internal Message format.

    Example:
        >>> agent = MyAgent()
        >>> server = GRPCServer(agent, "localhost:50051")
        >>> await server.start()
        >>> # ... server is running ...
        >>> await server.stop()
    """

    def __init__(self, agent: Agent, address: str):
        """Initialize gRPC server.

        Args:
            agent: The agent to expose over gRPC
            address: Address to bind to (e.g., "localhost:50051")
        """
        self._agent = agent
        self._address = address
        self._server: aio.Server | None = None
        self._running = False

    async def start(self) -> None:
        """Start the gRPC server.

        Raises:
            RuntimeError: If server is already running
        """
        if self._running:
            raise RuntimeError("Server is already running")

        # Create async gRPC server
        self._server = aio.server()
        agent_pb2_grpc.add_AgentServiceServicer_to_server(self, self._server)

        # Bind to address
        self._server.add_insecure_port(self._address)

        # Start serving
        await self._server.start()
        self._running = True

        logger.info(f"gRPC server for agent '{self._agent.name}' started on {self._address}")

    async def stop(self) -> None:
        """Stop the gRPC server gracefully."""
        if not self._running:
            return

        self._running = False

        if self._server:
            await self._server.stop(grace=5.0)
            self._server = None

        logger.info(f"gRPC server for agent '{self._agent.name}' stopped")

    async def wait_for_termination(self) -> None:
        """Wait for the server to terminate."""
        if self._server:
            await self._server.wait_for_termination()

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running

    async def Process(
        self, request: agent_pb2.Request, context: grpc.aio.ServicerContext
    ) -> agent_pb2.Response:
        """Handle unary Process RPC.

        Args:
            request: Protobuf request message
            context: gRPC context

        Returns:
            Protobuf response message
        """
        try:
            # Convert protobuf request to agenkit Message
            message = self._protobuf_request_to_message(request)

            # Process with agent
            response_message = await self._agent.process(message)

            # Convert response to protobuf
            return self._message_to_protobuf_response(request.id, response_message)

        except Exception as e:
            logger.error(f"Error in Process RPC: {e}", exc_info=True)
            return self._create_error_response(request.id, "AGENT_ERROR", str(e))

    async def ProcessStream(
        self, request: agent_pb2.Request, context: grpc.aio.ServicerContext
    ) -> None:
        """Handle streaming ProcessStream RPC.

        Args:
            request: Protobuf request message
            context: gRPC context

        Yields:
            Protobuf StreamChunk messages
        """
        try:
            # Convert protobuf request to agenkit Message
            message = self._protobuf_request_to_message(request)

            # Check if agent supports streaming
            if hasattr(self._agent, 'stream'):
                # Stream with agent
                async for chunk in self._agent.stream(message):
                    # Convert chunk to protobuf
                    pb_chunk = self._message_to_protobuf_chunk(request.id, chunk)
                    yield pb_chunk

                # Send end chunk
                yield agent_pb2.StreamChunk(
                    version="1.0",
                    id=request.id,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    type=agent_pb2.CHUNK_TYPE_END
                )
            else:
                # Fall back to unary processing
                response_message = await self._agent.process(message)

                # Convert response to stream chunk
                pb_chunk = self._message_to_protobuf_chunk(request.id, response_message)
                yield pb_chunk

                # Send end chunk
                yield agent_pb2.StreamChunk(
                    version="1.0",
                    id=request.id,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    type=agent_pb2.CHUNK_TYPE_END
                )

        except Exception as e:
            logger.error(f"Error in ProcessStream RPC: {e}", exc_info=True)
            # Send error chunk
            yield agent_pb2.StreamChunk(
                version="1.0",
                id=request.id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                type=agent_pb2.CHUNK_TYPE_ERROR,
                error=agent_pb2.Error(
                    code="AGENT_ERROR",
                    message=str(e)
                )
            )

    def _protobuf_request_to_message(self, request: agent_pb2.Request) -> Any:
        """Convert protobuf Request to agenkit Message.

        Args:
            request: Protobuf request message

        Returns:
            agenkit Message object
        """
        from agenkit import Message

        # For simplicity, we'll use the first message in the request
        # In a real implementation, you might want to handle multiple messages
        if request.messages:
            pb_msg = request.messages[0]
            return Message(
                role=pb_msg.role,
                content=self._deserialize_content(pb_msg.content),
                metadata=dict(pb_msg.metadata)
            )
        else:
            # Return empty message if no messages in request
            return Message(role="user", content="")

    def _message_to_protobuf_response(
        self, request_id: str, message: Any
    ) -> agent_pb2.Response:
        """Convert agenkit Message to protobuf Response.

        Args:
            request_id: Request ID
            message: agenkit Message object

        Returns:
            Protobuf response message
        """
        pb_message = agent_pb2.Message(
            role=message.role,
            content=self._serialize_content(message.content),
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # Add metadata
        if hasattr(message, 'metadata') and message.metadata:
            for key, value in message.metadata.items():
                pb_message.metadata[key] = str(value)

        return agent_pb2.Response(
            version="1.0",
            id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=agent_pb2.RESPONSE_TYPE_MESSAGE,
            message=pb_message
        )

    def _message_to_protobuf_chunk(
        self, request_id: str, message: Any
    ) -> agent_pb2.StreamChunk:
        """Convert agenkit Message to protobuf StreamChunk.

        Args:
            request_id: Request ID
            message: agenkit Message object

        Returns:
            Protobuf stream chunk message
        """
        pb_message = agent_pb2.Message(
            role=message.role,
            content=self._serialize_content(message.content),
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # Add metadata
        if hasattr(message, 'metadata') and message.metadata:
            for key, value in message.metadata.items():
                pb_message.metadata[key] = str(value)

        return agent_pb2.StreamChunk(
            version="1.0",
            id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=agent_pb2.CHUNK_TYPE_MESSAGE,
            message=pb_message
        )

    def _create_error_response(
        self, request_id: str, error_code: str, error_message: str
    ) -> agent_pb2.Response:
        """Create an error response.

        Args:
            request_id: Request ID
            error_code: Error code
            error_message: Error message

        Returns:
            Protobuf error response
        """
        return agent_pb2.Response(
            version="1.0",
            id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=agent_pb2.RESPONSE_TYPE_ERROR,
            error=agent_pb2.Error(
                code=error_code,
                message=error_message
            )
        )

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

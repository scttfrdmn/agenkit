"""Remote agent client for protocol adapter."""

import asyncio
from collections.abc import AsyncIterator

from agenkit.interfaces import Agent, Message

from .codec import (
    create_request_envelope,
    decode_bytes,
    decode_message,
    encode_bytes,
    encode_message,
)
from .errors import (
    AgentTimeoutError,
    ConnectionError,
    InvalidMessageError,
    ProtocolError,
    RemoteExecutionError,
)
from .transport import Transport, parse_endpoint


class RemoteAgent(Agent):
    """Client-side proxy for a remote agent.

    This class implements the Agent interface and forwards all calls to a remote
    agent over the protocol adapter. It can be used as a drop-in replacement for
    a local agent.
    """

    def __init__(
        self,
        name: str,
        endpoint: str | None = None,
        transport: Transport | None = None,
        timeout: float = 30.0,
    ):
        """Initialize remote agent client.

        Args:
            name: Name of the remote agent
            endpoint: Endpoint URL (e.g., "unix:///tmp/agent.sock")
            transport: Custom transport (if endpoint not provided)
            timeout: Request timeout in seconds

        Raises:
            ValueError: If neither endpoint nor transport is provided
        """
        if endpoint is None and transport is None:
            raise ValueError("Either endpoint or transport must be provided")

        self._name = name
        self._endpoint = endpoint
        self._transport = transport or self._create_transport(endpoint)  # type: ignore
        self._timeout = timeout
        self._connected = False
        self._lock = asyncio.Lock()  # Serialize requests on same connection

    def _create_transport(self, endpoint: str) -> Transport:
        """Create transport from endpoint URL.

        Supports unix://, tcp://, http://, https://, h2c://, and h3:// protocols.

        Args:
            endpoint: Endpoint URL

        Returns:
            Transport instance

        Raises:
            ValueError: If endpoint format is not supported
        """
        return parse_endpoint(endpoint)

    async def _ensure_connected(self) -> None:
        """Ensure transport is connected."""
        if not self._connected:
            await self._transport.connect()
            self._connected = True

    @property
    def name(self) -> str:
        """Get agent name.

        Returns:
            Agent name
        """
        return self._name

    async def process(self, message: Message) -> Message:
        """Process a message through the remote agent.

        Args:
            message: Input message

        Returns:
            Response message from remote agent

        Raises:
            ConnectionError: If connection fails
            AgentTimeoutError: If request times out
            RemoteExecutionError: If remote agent raises an error
            ProtocolError: If protocol error occurs
        """
        await self._ensure_connected()

        # Create request envelope
        request = create_request_envelope(
            method="process", agent_name=self._name, payload={"message": encode_message(message)}
        )

        # Serialize requests on same connection to prevent interleaving
        async with self._lock:
            try:
                # Send request
                request_bytes = encode_bytes(request)
                await asyncio.wait_for(
                    self._transport.send_framed(request_bytes), timeout=self._timeout
                )

                # Receive response
                response_bytes = await asyncio.wait_for(
                    self._transport.receive_framed(), timeout=self._timeout
                )
                response = decode_bytes(response_bytes)

                # Handle response
                if response["type"] == "error":
                    error_payload = response["payload"]
                    raise RemoteExecutionError(
                        self._name,
                        error_payload["error_message"],
                        error_payload.get("error_details"),
                    )

                if response["type"] != "response":
                    raise InvalidMessageError(
                        f"Expected 'response' but got '{response['type']}'", {"response": response}
                    )

                # Decode and return message
                return decode_message(response["payload"]["message"])

            except asyncio.TimeoutError as e:
                raise AgentTimeoutError(self._name, self._timeout) from e
            except (ConnectionError, ProtocolError):
                # Re-raise protocol/connection errors as-is
                raise
            except Exception as e:
                # Wrap unexpected errors
                raise RemoteExecutionError(self._name, str(e)) from e

    async def stream(self, message: Message) -> AsyncIterator[Message]:
        """Stream responses from remote agent.

        Args:
            message: Input message

        Yields:
            Response messages from remote agent

        Raises:
            ConnectionError: If connection fails
            AgentTimeoutError: If request times out
            RemoteExecutionError: If remote agent raises an error
            ProtocolError: If protocol error occurs
        """
        await self._ensure_connected()

        # Create stream request envelope
        request = create_request_envelope(
            method="stream", agent_name=self._name, payload={"message": encode_message(message)}
        )

        # Serialize requests on same connection to prevent interleaving
        async with self._lock:
            try:
                # Send request
                request_bytes = encode_bytes(request)
                await asyncio.wait_for(
                    self._transport.send_framed(request_bytes), timeout=self._timeout
                )

                # Receive stream chunks
                while True:
                    # Receive next frame
                    response_bytes = await asyncio.wait_for(
                        self._transport.receive_framed(), timeout=self._timeout
                    )
                    response = decode_bytes(response_bytes)

                    # Handle response type
                    if response["type"] == "error":
                        error_payload = response["payload"]
                        raise RemoteExecutionError(
                            self._name,
                            error_payload["error_message"],
                            error_payload.get("error_details"),
                        )

                    elif response["type"] == "stream_chunk":
                        # Yield chunk message
                        chunk = decode_message(response["payload"]["message"])
                        yield chunk

                    elif response["type"] == "stream_end":
                        # Stream complete
                        break

                    else:
                        raise InvalidMessageError(
                            f"Expected 'stream_chunk' or 'stream_end' but got '{response['type']}'",
                            {"response": response},
                        )

            except asyncio.TimeoutError as e:
                raise AgentTimeoutError(self._name, self._timeout) from e
            except (ConnectionError, ProtocolError):
                # Re-raise protocol/connection errors as-is
                raise
            except Exception as e:
                # Wrap unexpected errors
                raise RemoteExecutionError(self._name, str(e)) from e

    @property
    def capabilities(self) -> list[str]:
        """Get agent capabilities.

        Note: Capability querying not yet implemented in v0.1.0.

        Returns:
            Empty list (capabilities not yet supported)
        """
        return []

    async def close(self) -> None:
        """Close connection to remote agent."""
        if self._connected:
            await self._transport.close()
            self._connected = False

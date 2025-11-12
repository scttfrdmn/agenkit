"""WebSocket transport implementation with automatic reconnection and keepalive."""

import asyncio
from typing import Optional

import websockets
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosed, WebSocketException
from websockets.protocol import State

from .errors import ConnectionClosedError
from .errors import ConnectionError as ConnError
from .transport import Transport


class WebSocketTransport(Transport):
    """WebSocket transport with automatic reconnection and keepalive.

    Supports both ws:// and wss:// URLs.
    Uses binary frames for data transmission.
    Implements automatic reconnection with exponential backoff.
    Includes ping/pong keepalive mechanism.
    """

    def __init__(
        self,
        url: str,
        max_retries: int = 5,
        initial_retry_delay: float = 1.0,
        ping_interval: float = 30.0,
        ping_timeout: float = 10.0,
    ):
        """Initialize WebSocket transport.

        Args:
            url: WebSocket URL (ws:// or wss://)
            max_retries: Maximum number of reconnection attempts (default: 5)
            initial_retry_delay: Initial delay between retries in seconds (default: 1.0)
            ping_interval: Interval between ping frames in seconds (default: 30.0)
            ping_timeout: Timeout for ping/pong in seconds (default: 10.0)
        """
        self._url = url
        self._max_retries = max_retries
        self._initial_retry_delay = initial_retry_delay
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._websocket: Optional[ClientConnection] = None
        self._connected = False
        self._reconnect_lock = asyncio.Lock()
        self._receive_buffer = bytearray()

    async def connect(self) -> None:
        """Establish WebSocket connection with retry logic.

        Raises:
            ConnectionError: If connection fails after all retries
        """
        await self._connect_with_retry()

    async def _connect_with_retry(self) -> None:
        """Connect with exponential backoff retry logic."""
        last_error = None
        retry_delay = self._initial_retry_delay

        for attempt in range(self._max_retries):
            try:
                self._websocket = await websockets.connect(
                    self._url,
                    ping_interval=self._ping_interval,
                    ping_timeout=self._ping_timeout,
                    max_size=10 * 1024 * 1024,  # 10 MB max message size
                )
                self._connected = True
                self._receive_buffer.clear()
                return

            except (OSError, WebSocketException, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff

        raise ConnError(
            f"Failed to connect to {self._url} after {self._max_retries} attempts: {last_error}"
        )

    async def _ensure_connected(self) -> None:
        """Ensure connection is established, reconnect if necessary.

        Raises:
            ConnectionError: If reconnection fails
        """
        if not self.is_connected:
            async with self._reconnect_lock:
                # Double-check after acquiring lock
                if not self.is_connected:
                    await self._connect_with_retry()

    async def send(self, data: bytes) -> None:
        """Send data over WebSocket using binary frames.

        Args:
            data: Bytes to send

        Raises:
            ConnectionError: If send fails or not connected
            ConnectionClosedError: If connection is closed
        """
        await self._ensure_connected()

        assert self._websocket is not None
        try:
            await self._websocket.send(data)
        except ConnectionClosed as e:
            self._connected = False
            self._websocket = None
            raise ConnectionClosedError(f"Connection closed during send: {e}") from e
        except (OSError, WebSocketException) as e:
            self._connected = False
            self._websocket = None
            raise ConnError(f"Failed to send data: {e}") from e

    async def send_framed(self, data: bytes) -> None:
        """Send data over WebSocket (no length prefix needed - WebSocket handles framing).

        Args:
            data: Data to send

        Raises:
            ValueError: If data exceeds maximum message size
            ConnectionError: If send fails
        """
        # Check size limit
        if len(data) > 10 * 1024 * 1024:  # 10 MB max
            raise ValueError(f"Message size {len(data)} exceeds maximum 10 MB")

        # WebSocket provides its own framing, so just send the data directly
        await self.send(data)

    async def receive(self) -> bytes:
        """Receive data from WebSocket.

        Returns:
            Received bytes (up to one complete message)

        Raises:
            ConnectionError: If receive fails or not connected
            ConnectionClosedError: If connection is closed
        """
        await self._ensure_connected()

        assert self._websocket is not None
        try:
            message = await self._websocket.recv()
            # Ensure we return bytes (message could be str if server sends text)
            if isinstance(message, str):
                return message.encode('utf-8')
            return message
        except ConnectionClosed as e:
            self._connected = False
            self._websocket = None
            raise ConnectionClosedError(f"Connection closed during receive: {e}") from e
        except (OSError, WebSocketException) as e:
            self._connected = False
            self._websocket = None
            raise ConnError(f"Failed to receive data: {e}") from e

    async def receive_framed(self) -> bytes:
        """Receive data from WebSocket (no length prefix needed - WebSocket handles framing).

        Returns:
            Received data

        Raises:
            ConnectionError: If receive fails
            MalformedPayloadError: If frame is invalid
        """
        # WebSocket provides its own framing, so just receive the data directly
        data = await self.receive()

        # Check size limit
        if len(data) > 10 * 1024 * 1024:  # 10 MB max
            from .errors import MalformedPayloadError
            raise MalformedPayloadError(
                f"Message size {len(data)} exceeds maximum 10 MB", {"length": len(data)}
            )

        return data

    async def receive_exactly(self, n: int) -> bytes:
        """Receive exactly n bytes from WebSocket.

        This method buffers data from WebSocket messages until we have
        at least n bytes, then returns exactly n bytes.

        Args:
            n: Number of bytes to receive

        Returns:
            Exactly n bytes

        Raises:
            ConnectionError: If receive fails or not connected
            ConnectionClosedError: If connection closes before receiving all bytes
        """
        await self._ensure_connected()

        # Fill buffer until we have enough bytes
        while len(self._receive_buffer) < n:
            try:
                # Receive next message
                chunk = await self.receive()
                self._receive_buffer.extend(chunk)
            except ConnectionClosedError:
                if len(self._receive_buffer) > 0:
                    raise ConnectionClosedError(
                        f"Connection closed while expecting {n - len(self._receive_buffer)} more bytes"
                    )
                raise

        # Extract exactly n bytes from buffer
        result = bytes(self._receive_buffer[:n])
        del self._receive_buffer[:n]
        return result

    async def close(self) -> None:
        """Close WebSocket connection gracefully."""
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception:
                # Ignore errors during close
                pass
            finally:
                self._websocket = None
                self._connected = False
                self._receive_buffer.clear()

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected.

        Returns:
            True if connected, False otherwise
        """
        return (
            self._connected
            and self._websocket is not None
            and self._websocket.state == State.OPEN
        )

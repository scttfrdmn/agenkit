"""Transport layer for protocol adapter."""

import asyncio
import struct
from abc import ABC, abstractmethod

from .errors import ConnectionClosedError, MalformedPayloadError
from .errors import ConnectionError as ConnError

MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10 MB


class Transport(ABC):
    """Abstract transport layer for agent communication."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def send(self, data: bytes) -> None:
        """Send data over the transport.

        Args:
            data: Bytes to send

        Raises:
            ConnectionError: If send fails
            ConnectionClosedError: If connection is closed
        """
        pass

    @abstractmethod
    async def receive(self) -> bytes:
        """Receive data from the transport.

        Returns:
            Received bytes

        Raises:
            ConnectionError: If receive fails
            ConnectionClosedError: If connection is closed
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the connection."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if transport is connected.

        Returns:
            True if connected, False otherwise
        """
        pass

    async def send_framed(self, data: bytes) -> None:
        """Send length-prefixed framed data.

        Frame format: [4-byte length (big-endian)] + [data]

        Args:
            data: Data to send

        Raises:
            ValueError: If data exceeds maximum message size
            ConnectionError: If send fails
        """
        if len(data) > MAX_MESSAGE_SIZE:
            raise ValueError(f"Message size {len(data)} exceeds maximum {MAX_MESSAGE_SIZE}")

        # Pack length as 4-byte big-endian unsigned integer
        length_prefix = struct.pack(">I", len(data))
        await self.send(length_prefix + data)

    async def receive_framed(self) -> bytes:
        """Receive length-prefixed framed data.

        Returns:
            Received data (without length prefix)

        Raises:
            ConnectionError: If receive fails
            MalformedPayloadError: If frame is invalid
        """
        # Read 4-byte length prefix
        length_bytes = await self.receive_exactly(4)
        length = struct.unpack(">I", length_bytes)[0]

        if length > MAX_MESSAGE_SIZE:
            raise MalformedPayloadError(
                f"Message size {length} exceeds maximum {MAX_MESSAGE_SIZE}", {"length": length}
            )

        # Read exact payload
        return await self.receive_exactly(length)

    @abstractmethod
    async def receive_exactly(self, n: int) -> bytes:
        """Receive exactly n bytes.

        Args:
            n: Number of bytes to receive

        Returns:
            Exactly n bytes

        Raises:
            ConnectionError: If receive fails
            ConnectionClosedError: If connection closes before receiving all bytes
        """
        pass


class UnixSocketTransport(Transport):
    """Unix domain socket transport."""

    def __init__(self, socket_path: str):
        """Initialize Unix socket transport.

        Args:
            socket_path: Path to Unix domain socket
        """
        self._socket_path = socket_path
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        """Connect to Unix socket.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            self._reader, self._writer = await asyncio.open_unix_connection(self._socket_path)
        except (OSError, ConnectionRefusedError, FileNotFoundError) as e:
            raise ConnError(f"Failed to connect to {self._socket_path}: {e}") from e

    async def send(self, data: bytes) -> None:
        """Send data over Unix socket.

        Args:
            data: Bytes to send

        Raises:
            ConnectionError: If not connected or send fails
        """
        if not self.is_connected:
            raise ConnError("Not connected")

        assert self._writer is not None
        try:
            self._writer.write(data)
            await self._writer.drain()
        except (OSError, ConnectionError) as e:
            raise ConnError(f"Failed to send data: {e}") from e

    async def receive(self) -> bytes:
        """Receive data from Unix socket.

        Returns:
            Received bytes (up to 64KB)

        Raises:
            ConnectionError: If not connected or receive fails
            ConnectionClosedError: If connection is closed
        """
        if not self.is_connected:
            raise ConnError("Not connected")

        assert self._reader is not None
        try:
            data = await self._reader.read(65536)  # Read up to 64KB
            if not data:
                raise ConnectionClosedError("Connection closed by peer")
            return data
        except (OSError, ConnectionError) as e:
            raise ConnError(f"Failed to receive data: {e}") from e

    async def receive_exactly(self, n: int) -> bytes:
        """Receive exactly n bytes from Unix socket.

        Args:
            n: Number of bytes to receive

        Returns:
            Exactly n bytes

        Raises:
            ConnectionError: If not connected or receive fails
            ConnectionClosedError: If connection closes before receiving all bytes
        """
        if not self.is_connected:
            raise ConnError("Not connected")

        assert self._reader is not None
        try:
            data = await self._reader.readexactly(n)
            return data
        except asyncio.IncompleteReadError as e:
            raise ConnectionClosedError(
                f"Connection closed while expecting {n - len(e.partial)} more bytes"
            ) from e
        except (OSError, ConnectionError) as e:
            raise ConnError(f"Failed to receive data: {e}") from e

    async def close(self) -> None:
        """Close Unix socket connection."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        self._reader = None
        self._writer = None

    @property
    def is_connected(self) -> bool:
        """Check if Unix socket is connected.

        Returns:
            True if connected, False otherwise
        """
        return self._reader is not None and self._writer is not None


class TCPTransport(Transport):
    """TCP socket transport."""

    def __init__(self, host: str, port: int):
        """Initialize TCP transport.

        Args:
            host: Hostname or IP address
            port: Port number
        """
        self._host = host
        self._port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        """Connect to TCP socket.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            self._reader, self._writer = await asyncio.open_connection(self._host, self._port)
        except (OSError, ConnectionRefusedError) as e:
            raise ConnError(f"Failed to connect to {self._host}:{self._port}: {e}") from e

    async def send(self, data: bytes) -> None:
        """Send data over TCP socket.

        Args:
            data: Bytes to send

        Raises:
            ConnectionError: If not connected or send fails
        """
        if not self.is_connected:
            raise ConnError("Not connected")

        assert self._writer is not None
        try:
            self._writer.write(data)
            await self._writer.drain()
        except (OSError, ConnectionError) as e:
            raise ConnError(f"Failed to send data: {e}") from e

    async def receive(self) -> bytes:
        """Receive data from TCP socket.

        Returns:
            Received bytes (up to 64KB)

        Raises:
            ConnectionError: If not connected or receive fails
            ConnectionClosedError: If connection is closed
        """
        if not self.is_connected:
            raise ConnError("Not connected")

        assert self._reader is not None
        try:
            data = await self._reader.read(65536)  # Read up to 64KB
            if not data:
                raise ConnectionClosedError("Connection closed by peer")
            return data
        except (OSError, ConnectionError) as e:
            raise ConnError(f"Failed to receive data: {e}") from e

    async def receive_exactly(self, n: int) -> bytes:
        """Receive exactly n bytes from TCP socket.

        Args:
            n: Number of bytes to receive

        Returns:
            Exactly n bytes

        Raises:
            ConnectionError: If not connected or receive fails
            ConnectionClosedError: If connection closes before receiving all bytes
        """
        if not self.is_connected:
            raise ConnError("Not connected")

        assert self._reader is not None
        try:
            data = await self._reader.readexactly(n)
            return data
        except asyncio.IncompleteReadError as e:
            raise ConnectionClosedError(
                f"Connection closed while expecting {n - len(e.partial)} more bytes"
            ) from e
        except (OSError, ConnectionError) as e:
            raise ConnError(f"Failed to receive data: {e}") from e

    async def close(self) -> None:
        """Close TCP socket connection."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        self._reader = None
        self._writer = None

    @property
    def is_connected(self) -> bool:
        """Check if TCP socket is connected.

        Returns:
            True if connected, False otherwise
        """
        return self._reader is not None and self._writer is not None


class InMemoryTransport(Transport):
    """In-memory transport for testing."""

    def __init__(self, send_queue: asyncio.Queue[bytes], receive_queue: asyncio.Queue[bytes]):
        """Initialize in-memory transport.

        Args:
            send_queue: Queue for sending data
            receive_queue: Queue for receiving data
        """
        self._send_queue = send_queue
        self._receive_queue = receive_queue
        self._connected = False

    async def connect(self) -> None:
        """Mark as connected."""
        self._connected = True

    async def send(self, data: bytes) -> None:
        """Send data to send queue.

        Args:
            data: Bytes to send

        Raises:
            ConnectionError: If not connected
        """
        if not self.is_connected:
            raise ConnError("Not connected")

        await self._send_queue.put(data)

    async def receive(self) -> bytes:
        """Receive data from receive queue.

        Returns:
            Received bytes

        Raises:
            ConnectionError: If not connected
        """
        if not self.is_connected:
            raise ConnError("Not connected")

        return await self._receive_queue.get()

    async def receive_exactly(self, n: int) -> bytes:
        """Receive exactly n bytes from receive queue.

        For in-memory transport, we assume messages are complete.

        Args:
            n: Number of bytes to receive

        Returns:
            Exactly n bytes

        Raises:
            ConnectionError: If not connected
            ConnectionClosedError: If not enough data available
        """
        if not self.is_connected:
            raise ConnError("Not connected")

        data = await self._receive_queue.get()
        if len(data) < n:
            raise ConnectionClosedError(f"Expected {n} bytes but only got {len(data)}")
        return data[:n]

    async def close(self) -> None:
        """Mark as disconnected."""
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected.

        Returns:
            True if connected, False otherwise
        """
        return self._connected


def create_memory_transport_pair() -> tuple[InMemoryTransport, InMemoryTransport]:
    """Create a pair of connected in-memory transports for testing.

    Returns:
        Tuple of (server_transport, client_transport)
    """
    # Create two queues - one for each direction
    server_to_client: asyncio.Queue[bytes] = asyncio.Queue()
    client_to_server: asyncio.Queue[bytes] = asyncio.Queue()

    # Server sends to server_to_client, receives from client_to_server
    server_transport = InMemoryTransport(server_to_client, client_to_server)

    # Client sends to client_to_server, receives from server_to_client
    client_transport = InMemoryTransport(client_to_server, server_to_client)

    return server_transport, client_transport


def parse_endpoint(endpoint: str) -> Transport:
    """Parse endpoint string and return appropriate transport.

    Supported formats:
        - unix:///path/to/socket -> UnixSocketTransport
        - tcp://host:port -> TCPTransport
        - http://host:port -> HTTPTransport (HTTP/1.1 with HTTP/2 upgrade)
        - https://host:port -> HTTPTransport (HTTPS with HTTP/2 upgrade)
        - h2c://host:port -> HTTPTransport (HTTP/2 cleartext)
        - h3://host:port -> HTTPTransport (HTTP/3 over QUIC)

    Args:
        endpoint: Endpoint string

    Returns:
        Appropriate Transport instance

    Raises:
        ValueError: If endpoint format is unsupported
    """
    if endpoint.startswith("unix://"):
        socket_path = endpoint[7:]
        return UnixSocketTransport(socket_path)

    if endpoint.startswith("tcp://"):
        tcp_part = endpoint[6:]
        # Find last colon to split host:port
        colon_idx = tcp_part.rfind(':')
        if colon_idx == -1:
            raise ValueError(f"Invalid TCP endpoint format: {endpoint}")
        host = tcp_part[:colon_idx]
        try:
            port = int(tcp_part[colon_idx + 1:])
        except ValueError:
            raise ValueError(f"Invalid port in TCP endpoint: {endpoint}")
        if not (0 < port <= 65535):
            raise ValueError(f"Invalid port in endpoint: {endpoint}")
        return TCPTransport(host, port)

    if endpoint.startswith(("http://", "https://", "h2c://", "h3://")):
        # Import here to avoid circular dependency
        from .http_transport import HTTPTransport
        return HTTPTransport(endpoint)

    raise ValueError(f"Unsupported endpoint format: {endpoint}")

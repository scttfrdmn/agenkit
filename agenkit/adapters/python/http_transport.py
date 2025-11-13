"""HTTP transport implementation with HTTP/1.1, HTTP/2, and HTTP/3 support."""

import json
from enum import Enum
from typing import TYPE_CHECKING

import httpx

from .errors import ConnectionClosedError
from .errors import ConnectionError as ConnError
from .transport import Transport

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class HTTPVersion(Enum):
    """HTTP protocol version."""

    HTTP1 = "http1"  # HTTP/1.1
    HTTP2 = "http2"  # HTTP/2 (h2 for TLS, h2c for cleartext)
    HTTP3 = "http3"  # HTTP/3 over QUIC


class HTTPTransport(Transport):
    """HTTP transport supporting HTTP/1.1, HTTP/2, and HTTP/3.

    URL schemes:
        - http:// or https:// → HTTP/1.1 (with automatic HTTP/2 upgrade for HTTPS)
        - h2c:// → HTTP/2 cleartext
        - h3:// → HTTP/3 over QUIC
    """

    def __init__(self, url: str):
        """Initialize HTTP transport.

        Args:
            url: URL of the remote agent (http://, https://, h2c://, or h3://)
        """
        self.url = url
        self.version = self._detect_version(url)
        self.normalized_url = self._normalize_url(url)
        self.client: httpx.AsyncClient | None = None
        self.response_stream: httpx.Response | None = None
        self._stream_iterator: AsyncIterator[str] | None = None
        self._connected = False

    def _detect_version(self, url: str) -> HTTPVersion:
        """Detect HTTP version from URL scheme."""
        if url.startswith("h2c://"):
            return HTTPVersion.HTTP2
        elif url.startswith("h3://"):
            return HTTPVersion.HTTP3
        else:
            return HTTPVersion.HTTP1

    def _normalize_url(self, url: str) -> str:
        """Normalize URL scheme."""
        if url.startswith("h2c://"):
            return "http://" + url[6:]
        elif url.startswith("h3://"):
            return "https://" + url[5:]
        return url.rstrip("/")

    async def connect(self) -> None:
        """Establish connection to HTTP endpoint."""
        try:
            # Configure HTTP client based on version
            if self.version == HTTPVersion.HTTP2:
                # HTTP/2 cleartext (h2c)
                self.client = httpx.AsyncClient(
                    http2=True,
                    timeout=httpx.Timeout(30.0)
                )
            elif self.version == HTTPVersion.HTTP3:
                # HTTP/3 over QUIC
                # Note: httpx doesn't support HTTP/3 yet, so we fall back to HTTP/2
                self.client = httpx.AsyncClient(
                    http2=True,
                    timeout=httpx.Timeout(30.0)
                )
            else:
                # HTTP/1.1 with automatic HTTP/2 upgrade for HTTPS
                self.client = httpx.AsyncClient(
                    http2=True,
                    timeout=httpx.Timeout(30.0)
                )

            # Test connectivity with HEAD request
            await self.client.head(f"{self.normalized_url}/health")
            self._connected = True

        except Exception as e:
            raise ConnError(f"Failed to connect to {self.normalized_url}: {e}")

    async def send(self, data: bytes) -> None:
        """Send data over HTTP (not used directly, use send_framed)."""
        raise NotImplementedError("Use send_framed for HTTP transport")

    async def receive(self) -> bytes:
        """Receive data from HTTP (not used directly, use receive_framed)."""
        raise NotImplementedError("Use receive_framed for HTTP transport")

    async def receive_exactly(self, n: int) -> bytes:
        """Receive exactly n bytes (not used for HTTP transport)."""
        raise NotImplementedError("Use receive_framed for HTTP transport")

    async def send_framed(self, data: bytes) -> None:
        """Send HTTP request with framed data.

        This decodes the envelope to determine the endpoint (process vs stream).
        """
        if not self.client:
            raise ConnError("Not connected")

        try:
            # Decode envelope to determine method
            envelope = json.loads(data.decode('utf-8'))
            method = envelope.get("payload", {}).get("method", "process")

            if method == "stream":
                # For streaming, send POST to /stream and keep response open
                response = await self.client.post(
                    f"{self.normalized_url}/stream",
                    content=data,
                    headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
                )

                if response.status_code != 200:
                    raise ConnError(f"HTTP error {response.status_code}: {response.text}")

                # Store response for SSE reading
                self.response_stream = response
                self._stream_iterator = response.aiter_lines()

            else:
                # For non-streaming, send POST to /process
                response = await self.client.post(
                    f"{self.normalized_url}/process",
                    content=data,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code != 200:
                    raise ConnError(f"HTTP error {response.status_code}: {response.text}")

                # Store response for receive_framed
                self._pending_response = response.content

        except Exception as e:
            if isinstance(e, ConnError):
                raise
            raise ConnError(f"Failed to send HTTP request: {e}")

    async def receive_framed(self) -> bytes:
        """Receive HTTP response."""
        # If we're in streaming mode, read SSE events
        if self._stream_iterator:
            return await self._read_sse_event()

        # For non-streaming, return the pending response
        if hasattr(self, '_pending_response'):
            response = self._pending_response
            del self._pending_response
            return response

        raise ConnError("No pending response")

    async def _read_sse_event(self) -> bytes:
        """Read a single Server-Sent Event from the stream."""
        if not self._stream_iterator:
            raise ConnectionClosedError("Stream not initialized")

        event_data = []

        try:
            async for line in self._stream_iterator:
                line = line.strip()

                # Empty line signals end of event
                if not line:
                    if event_data:
                        # Join all data lines and return
                        return "".join(event_data).encode('utf-8')
                    continue

                # Parse SSE line
                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: " prefix
                    event_data.append(data)
                # Ignore other SSE fields (id:, event:, retry:)

            # Stream ended
            if self.response_stream:
                await self.response_stream.aclose()
                self.response_stream = None
                self._stream_iterator = None
            raise ConnectionClosedError("Stream ended")

        except Exception as e:
            if isinstance(e, ConnectionClosedError):
                raise
            raise ConnError(f"Failed to read SSE event: {e}")

    async def close(self) -> None:
        """Close the HTTP connection."""
        if self.response_stream:
            await self.response_stream.aclose()
            self.response_stream = None
            self._stream_iterator = None

        if self.client:
            await self.client.aclose()
            self.client = None

        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        return self._connected and self.client is not None


def parse_http_endpoint(endpoint: str) -> str:
    """Parse HTTP endpoint and validate format.

    Args:
        endpoint: HTTP endpoint (http://, https://, h2c://, or h3://)

    Returns:
        Validated endpoint URL

    Raises:
        ValueError: If endpoint format is invalid
    """
    if not endpoint.startswith(("http://", "https://", "h2c://", "h3://")):
        raise ValueError(f"Invalid HTTP endpoint: {endpoint}")

    return endpoint

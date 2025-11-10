"""HTTP server implementation for protocol adapter."""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from aiohttp import web
from aiohttp.web import Request, Response, StreamResponse

from ...interfaces import Agent
from .codec import decode_message, encode_message
from .errors import InvalidMessageError

logger = logging.getLogger(__name__)


class HTTPAgentServer:
    """HTTP server wrapper for exposing agents over HTTP.

    Provides HTTP/1.1 and HTTP/2 support with Server-Sent Events (SSE) for streaming.
    """

    def __init__(self, agent: Agent, host: str = "localhost", port: int = 8080,
                 enable_http2: bool = False):
        """Initialize HTTP agent server.

        Args:
            agent: The local agent to expose
            host: Server host address
            port: Server port
            enable_http2: Enable HTTP/2 support (requires SSL/TLS)
        """
        self.agent = agent
        self.host = host
        self.port = port
        self.enable_http2 = enable_http2
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None

        # Register routes (add_get automatically adds HEAD)
        self.app.router.add_get("/health", self.handle_health)
        self.app.router.add_post("/process", self.handle_process)
        self.app.router.add_post("/stream", self.handle_stream)

    async def start(self) -> None:
        """Start the HTTP server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        protocol = "http"
        if self.enable_http2:
            protocol += " (HTTP/2)"

        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        logger.info(f"Agent '{self.agent.name}' listening on {protocol}://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the HTTP server."""
        if self.site:
            await self.site.stop()
            self.site = None

        if self.runner:
            await self.runner.cleanup()
            self.runner = None

        logger.info(f"Agent '{self.agent.name}' stopped")

    async def handle_health(self, request: Request) -> Response:
        """Handle health check requests."""
        return Response(status=200)

    async def handle_process(self, request: Request) -> Response:
        """Handle process requests."""
        try:
            # Read request body
            body = await request.read()
            envelope = json.loads(body.decode('utf-8'))

            # Extract message
            message_data = envelope.get("payload", {}).get("message")
            if not message_data:
                return self._error_response(
                    envelope.get("id", "unknown"),
                    "INVALID_MESSAGE",
                    "Missing message in payload",
                    400
                )

            # Decode message
            input_message = decode_message(message_data)

            # Process through agent
            result = await self.agent.process(input_message)

            # Create response envelope
            response_payload = {
                "message": encode_message(result)
            }
            response_envelope = {
                "id": envelope.get("id", ""),
                "type": "response",
                "version": "1.0",
                "payload": response_payload
            }

            return Response(
                body=json.dumps(response_envelope).encode('utf-8'),
                content_type="application/json",
                status=200
            )

        except InvalidMessageError as e:
            return self._error_response(
                envelope.get("id", "unknown"),
                "INVALID_MESSAGE",
                str(e),
                400
            )
        except Exception as e:
            return self._error_response(
                envelope.get("id", "unknown"),
                "EXECUTION_ERROR",
                str(e),
                500
            )

    async def handle_stream(self, request: Request) -> StreamResponse:
        """Handle streaming requests with Server-Sent Events."""
        try:
            # Read request body
            body = await request.read()
            envelope = json.loads(body.decode('utf-8'))

            # Extract message
            message_data = envelope.get("payload", {}).get("message")
            if not message_data:
                return self._error_response(
                    envelope.get("id", "unknown"),
                    "INVALID_MESSAGE",
                    "Missing message in payload",
                    400
                )

            # Decode message
            input_message = decode_message(message_data)

            # Check if agent supports streaming
            if not hasattr(self.agent, 'stream'):
                return self._error_response(
                    envelope.get("id", "unknown"),
                    "NOT_IMPLEMENTED",
                    "Agent does not support streaming",
                    501
                )

            # Set up SSE response
            response = StreamResponse(
                status=200,
                reason='OK',
                headers={
                    'Content-Type': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                }
            )
            await response.prepare(request)

            # Start streaming
            try:
                async for chunk in self.agent.stream(input_message):
                    # Send chunk as SSE
                    chunk_envelope = {
                        "id": envelope.get("id", ""),
                        "type": "stream_chunk",
                        "version": "1.0",
                        "payload": {
                            "message": encode_message(chunk)
                        }
                    }
                    await self._send_sse_event(response, chunk_envelope)

                # Send stream end event
                end_envelope = {
                    "id": envelope.get("id", ""),
                    "type": "stream_end",
                    "version": "1.0",
                    "payload": {}
                }
                await self._send_sse_event(response, end_envelope)

            except Exception as e:
                # Send error as SSE
                error_envelope = {
                    "id": envelope.get("id", ""),
                    "type": "error",
                    "version": "1.0",
                    "payload": {
                        "error": {
                            "code": "STREAM_ERROR",
                            "message": str(e)
                        }
                    }
                }
                await self._send_sse_event(response, error_envelope)

            return response

        except Exception as e:
            return self._error_response(
                envelope.get("id", "unknown"),
                "INTERNAL_ERROR",
                str(e),
                500
            )

    async def _send_sse_event(self, response: StreamResponse, data: Dict[str, Any]) -> None:
        """Send a Server-Sent Event."""
        json_data = json.dumps(data)
        await response.write(f"data: {json_data}\n\n".encode('utf-8'))
        await response.drain()

    def _error_response(self, id: str, code: str, message: str, status: int) -> Response:
        """Create an error response."""
        envelope = {
            "id": id,
            "type": "error",
            "version": "1.0",
            "payload": {
                "error": {
                    "code": code,
                    "message": message
                }
            }
        }

        return Response(
            body=json.dumps(envelope).encode('utf-8'),
            content_type="application/json",
            status=status
        )

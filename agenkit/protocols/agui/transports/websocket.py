#!/usr/bin/env python3
"""
AG-UI WebSocket Transport

Implements bidirectional WebSocket transport for AG-UI protocol.
Provides lower latency and bidirectional communication compared to HTTP/SSE.

Reference: https://docs.ag-ui.com/protocol/transports

Example (FastAPI):
    from fastapi import FastAPI, WebSocket
    from agenkit.protocols.agui.transports.websocket import AGUIWebSocketHandler

    app = FastAPI()

    @app.websocket("/chat")
    async def chat_endpoint(websocket: WebSocket):
        handler = AGUIWebSocketHandler(agent=my_agent)
        await handler.handle(websocket)

Example (aiohttp):
    from aiohttp import web
    from agenkit.protocols.agui.transports.websocket import create_websocket_handler

    async def chat_handler(request):
        return await create_websocket_handler(my_agent, request)

    app = web.Application()
    app.router.add_get("/chat", chat_handler)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from agenkit.protocols.agui.events import AGUIEvent

from agenkit import Agent, Message
from agenkit.protocols.agui.adapter import AGUIAdapter


class WebSocketMessageFormat:
    """
    Formats AG-UI events for WebSocket transmission.

    WebSocket messages are JSON objects with the event data.
    """

    @staticmethod
    def format_event(event: "AGUIEvent") -> str:  # noqa: UP037
        """
        Format AG-UI event as WebSocket message (JSON string).

        Args:
            event: AG-UI event to format

        Returns:
            JSON string for WebSocket transmission
        """
        event_dict = event.to_dict()
        return json.dumps(event_dict)

    @staticmethod
    def parse_message(message: str) -> dict[str, Any]:
        """
        Parse WebSocket message (JSON string) to dictionary.

        Args:
            message: JSON string from WebSocket

        Returns:
            Parsed dictionary

        Raises:
            ValueError: If message is not valid JSON
        """
        try:
            result = json.loads(message)
            return dict(result) if isinstance(result, dict) else {"data": result}
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in WebSocket message: {e}") from e


class AGUIWebSocketStream:
    """
    Manages streaming AG-UI events over WebSocket.

    Handles bidirectional communication, allowing both sending events
    to the client and receiving messages from the client.
    """

    def __init__(
        self,
        adapter: AGUIAdapter,
        send_callback: Any,  # Callback to send messages to WebSocket
        heartbeat_interval: float | None = 30.0,
    ) -> None:
        """
        Initialize WebSocket stream.

        Args:
            adapter: AG-UI adapter wrapping the agent
            send_callback: Async function to send messages to WebSocket
            heartbeat_interval: Seconds between heartbeat events (None = no heartbeats)
        """
        self._adapter = adapter
        self._send_callback = send_callback
        self._heartbeat_interval = heartbeat_interval
        self._formatter = WebSocketMessageFormat()

    async def stream_events(self, message: Message) -> AsyncIterator[AGUIEvent]:
        """
        Stream AG-UI events for a message.

        Args:
            message: Input message to process

        Yields:
            AG-UI events from agent's response
        """
        async for event in self._adapter.stream_events(message):
            yield event

    async def send_event(self, event: AGUIEvent) -> None:
        """
        Send AG-UI event over WebSocket.

        Args:
            event: Event to send
        """
        formatted = self._formatter.format_event(event)
        await self._send_callback(formatted)


# FastAPI WebSocket integration
try:
    from fastapi import WebSocket, WebSocketDisconnect  # type: ignore[import-not-found]

    class AGUIWebSocketHandler:
        """
        FastAPI WebSocket handler for AG-UI protocol.

        Handles bidirectional WebSocket communication with automatic
        event streaming and message processing.

        Usage:
            from fastapi import FastAPI, WebSocket

            app = FastAPI()

            @app.websocket("/chat")
            async def chat_endpoint(websocket: WebSocket):
                handler = AGUIWebSocketHandler(agent=my_agent)
                await handler.handle(websocket)
        """

        def __init__(
            self,
            agent: Agent,
            agent_name: str | None = None,
            send_metadata: bool = True,
        ) -> None:
            """
            Initialize WebSocket handler.

            Args:
                agent: Agent to serve over WebSocket
                agent_name: Optional agent name
                send_metadata: Whether to send metadata event on connect
            """
            self._agent = agent
            self._agent_name = agent_name
            self._send_metadata = send_metadata
            self._adapter = AGUIAdapter(agent, agent_name=agent_name)
            self._formatter = WebSocketMessageFormat()

        async def handle(self, websocket: WebSocket) -> None:
            """
            Handle WebSocket connection.

            Args:
                websocket: FastAPI WebSocket connection
            """
            # Accept connection
            await websocket.accept()

            try:
                # Send metadata on connect
                if self._send_metadata:
                    async for event in self._adapter.stream_events(
                        Message(role="system", content=""), emit_metadata=True
                    ):
                        # Only send metadata event
                        if event.__class__.__name__ == "MetadataEvent":
                            await websocket.send_text(self._formatter.format_event(event))
                            break

                # Message loop
                while True:
                    # Receive message from client
                    data = await websocket.receive_text()

                    # Parse message
                    try:
                        message_dict = self._formatter.parse_message(data)
                    except ValueError as e:
                        # Send error event
                        error_msg = json.dumps(
                            {
                                "event_type": "error",
                                "error_code": "INVALID_MESSAGE",
                                "error_message": str(e),
                            }
                        )
                        await websocket.send_text(error_msg)
                        continue

                    # Extract message content
                    message_content = message_dict.get("message", message_dict.get("content", ""))

                    if not message_content:
                        # Send error for empty message
                        error_msg = json.dumps(
                            {
                                "event_type": "error",
                                "error_code": "EMPTY_MESSAGE",
                                "error_message": "Message content is required",
                            }
                        )
                        await websocket.send_text(error_msg)
                        continue

                    # Create message and stream events
                    user_message = Message(role="user", content=message_content)

                    async for event in self._adapter.stream_events(
                        user_message, emit_metadata=False
                    ):
                        formatted = self._formatter.format_event(event)
                        await websocket.send_text(formatted)

            except WebSocketDisconnect:
                # Client disconnected
                pass
            except Exception as e:
                # Send error event before closing
                try:
                    error_msg = json.dumps(
                        {
                            "event_type": "error",
                            "error_code": "INTERNAL_ERROR",
                            "error_message": str(e),
                        }
                    )
                    await websocket.send_text(error_msg)
                except Exception:  # noqa: S110
                    pass  # Connection might be closed - expected failure
                raise

    FASTAPI_WEBSOCKET_AVAILABLE = True

except ImportError:
    FASTAPI_WEBSOCKET_AVAILABLE = False

    class AGUIWebSocketHandler:  # type: ignore[no-redef]
        """Placeholder when FastAPI not available."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ImportError(
                "FastAPI is required for AGUIWebSocketHandler. Install with: pip install fastapi"
            )


# aiohttp WebSocket integration
try:
    from collections.abc import Callable, Coroutine  # noqa: TC003

    from aiohttp import WSMsgType, web

    def create_websocket_handler(
        agent: Agent,
        agent_name: str | None = None,
        send_metadata: bool = True,
    ) -> Callable[[Any], Coroutine[Any, Any, Any]]:
        """
        Create aiohttp WebSocket handler for AG-UI protocol.

        Usage:
            from aiohttp import web

            handler = create_websocket_handler(my_agent)
            app = web.Application()
            app.router.add_get("/chat", handler)

        Args:
            agent: Agent to serve
            agent_name: Optional agent name
            send_metadata: Send metadata on connect

        Returns:
            Async handler function for aiohttp
        """

        async def handler(request: Any) -> Any:
            """Handle WebSocket request."""
            ws = web.WebSocketResponse()
            await ws.prepare(request)

            adapter = AGUIAdapter(agent, agent_name=agent_name)
            formatter = WebSocketMessageFormat()

            try:
                # Send metadata on connect
                if send_metadata:
                    async for event in adapter.stream_events(
                        Message(role="system", content=""), emit_metadata=True
                    ):
                        if event.__class__.__name__ == "MetadataEvent":
                            await ws.send_str(formatter.format_event(event))
                            break

                # Message loop
                async for msg in ws:
                    if msg.type == WSMsgType.TEXT:
                        # Parse message
                        try:
                            message_dict = formatter.parse_message(msg.data)
                        except ValueError as e:
                            error_msg = json.dumps(
                                {
                                    "event_type": "error",
                                    "error_code": "INVALID_MESSAGE",
                                    "error_message": str(e),
                                }
                            )
                            await ws.send_str(error_msg)
                            continue

                        # Extract message content
                        message_content = message_dict.get(
                            "message", message_dict.get("content", "")
                        )

                        if not message_content:
                            error_msg = json.dumps(
                                {
                                    "event_type": "error",
                                    "error_code": "EMPTY_MESSAGE",
                                    "error_message": "Message content is required",
                                }
                            )
                            await ws.send_str(error_msg)
                            continue

                        # Stream events
                        user_message = Message(role="user", content=message_content)

                        async for event in adapter.stream_events(user_message, emit_metadata=False):
                            formatted = formatter.format_event(event)
                            await ws.send_str(formatted)

                    elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                        break

            except Exception as e:
                # Send error before closing
                try:
                    error_msg = json.dumps(
                        {
                            "event_type": "error",
                            "error_code": "INTERNAL_ERROR",
                            "error_message": str(e),
                        }
                    )
                    await ws.send_str(error_msg)
                except Exception:  # noqa: S110
                    pass  # Connection might be closed - expected failure

            await ws.close()
            return ws

        return handler

    AIOHTTP_WEBSOCKET_AVAILABLE = True

except ImportError:
    AIOHTTP_WEBSOCKET_AVAILABLE = False

    def create_websocket_handler(*args: Any, **kwargs: Any) -> None:  # type: ignore[misc]
        """Placeholder when aiohttp not available."""
        raise ImportError(
            "aiohttp is required for WebSocket handlers. Install with: pip install aiohttp"
        )


__all__ = [
    "AGUIWebSocketHandler",
    "AGUIWebSocketStream",
    "WebSocketMessageFormat",
    "create_websocket_handler",
]

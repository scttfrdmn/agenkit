#!/usr/bin/env python3
"""
AG-UI HTTP/SSE Transport

Implements Server-Sent Events (SSE) transport for AG-UI protocol over HTTP.
Provides FastAPI and aiohttp integrations for serving AG-UI event streams.

Reference: https://docs.ag-ui.com/protocol/transports

Example (FastAPI):
    from fastapi import FastAPI
    from agenkit.protocols.agui.transports.http import AGUISSEEndpoint

    app = FastAPI()
    endpoint = AGUISSEEndpoint(agent=my_agent)
    app.add_route("/chat", endpoint, methods=["POST"])

Example (aiohttp):
    from aiohttp import web
    from agenkit.protocols.agui.transports.http import create_sse_handler

    handler = create_sse_handler(agent=my_agent)
    app = web.Application()
    app.router.add_post("/chat", handler)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Coroutine

    from fastapi import Request

    from agenkit.protocols.agui.events import AGUIEvent

from agenkit import Agent, Message
from agenkit.protocols.agui.adapter import AGUIAdapter


class SSEFormatter:
    """
    Formats AG-UI events as Server-Sent Events (SSE).

    SSE format:
        data: {"event_type": "text_message_chunk", ...}\n\n

    With event name:
        event: text_message_chunk
        data: {...}\n\n
    """

    @staticmethod
    def format_event(event: AGUIEvent, include_event_name: bool = False) -> str:
        """
        Format AG-UI event as SSE message.

        Args:
            event: AG-UI event to format
            include_event_name: Whether to include "event:" line

        Returns:
            SSE-formatted string

        Example:
            >>> event = TextMessageChunk(content="Hello")
            >>> SSEFormatter.format_event(event)
            'data: {"event_type": "text_message_chunk", "content": "Hello", ...}\\n\\n'
        """
        event_dict = event.to_dict()
        event_json = json.dumps(event_dict)

        if include_event_name:
            event_name = event.event_type.value
            return f"event: {event_name}\ndata: {event_json}\n\n"
        else:
            return f"data: {event_json}\n\n"

    @staticmethod
    def format_comment(comment: str) -> str:
        """
        Format SSE comment (keeps connection alive).

        Args:
            comment: Comment text

        Returns:
            SSE comment line
        """
        return f": {comment}\n\n"

    @staticmethod
    def format_retry(milliseconds: int) -> str:
        """
        Format SSE retry directive.

        Args:
            milliseconds: Reconnection time in milliseconds

        Returns:
            SSE retry line
        """
        return f"retry: {milliseconds}\n\n"


class AGUISSEStream:
    """
    Async iterator that produces SSE-formatted AG-UI events.

    Can be used directly with FastAPI StreamingResponse or aiohttp streaming.
    """

    def __init__(
        self,
        adapter: AGUIAdapter,
        message: Message,
        include_event_names: bool = False,
        ping_interval: float | None = None,
    ) -> None:
        """
        Initialize SSE stream.

        Args:
            adapter: AG-UI adapter wrapping the agent
            message: Input message to process
            include_event_names: Whether to include "event:" lines
            ping_interval: Seconds between ping comments (None = no pings)
        """
        self._adapter = adapter
        self._message = message
        self._include_event_names = include_event_names
        self._ping_interval = ping_interval
        self._formatter = SSEFormatter()

    async def __aiter__(self) -> AsyncIterator[str]:
        """Stream SSE-formatted events."""
        try:
            async for event in self._adapter.stream_events(self._message):
                yield self._formatter.format_event(event, self._include_event_names)

            # Send final comment to indicate completion
            yield self._formatter.format_comment("stream_complete")

        except Exception as e:
            # Send error as SSE comment
            yield self._formatter.format_comment(f"error: {e}")
            raise


def create_sse_response_iterator(
    agent: Agent,
    message: Message,
    agent_name: str | None = None,
    include_event_names: bool = False,
) -> AsyncIterator[str]:
    """
    Create SSE iterator from agent and message.

    Convenience function for quickly creating SSE streams.

    Args:
        agent: Agent to wrap
        message: Message to process
        agent_name: Optional agent name
        include_event_names: Whether to include "event:" lines

    Returns:
        Async iterator yielding SSE-formatted strings

    Example:
        from fastapi.responses import StreamingResponse

        @app.post("/chat")
        async def chat(user_message: str):
            message = Message(role="user", content=user_message)
            iterator = create_sse_response_iterator(my_agent, message)
            return StreamingResponse(iterator, media_type="text/event-stream")
    """
    adapter = AGUIAdapter(agent, agent_name=agent_name)
    stream = AGUISSEStream(adapter, message, include_event_names)
    return stream.__aiter__()


# FastAPI integration
try:
    from fastapi.responses import StreamingResponse  # type: ignore[import-not-found]

    class AGUISSEEndpoint:
        """
        FastAPI endpoint for AG-UI SSE streaming.

        Usage:
            from fastapi import FastAPI

            app = FastAPI()
            endpoint = AGUISSEEndpoint(agent=my_agent)
            app.add_route("/chat", endpoint, methods=["POST"])

        Request body:
            {
                "message": "User message text",
                "message_id": "optional-msg-id"
            }

        Response:
            Server-Sent Events stream of AG-UI events
        """

        def __init__(
            self,
            agent: Agent,
            agent_name: str | None = None,
            include_event_names: bool = False,
            cors_origins: list[str] | None = None,
        ) -> None:
            """
            Initialize FastAPI SSE endpoint.

            Args:
                agent: Agent to serve
                agent_name: Optional agent name
                include_event_names: Include "event:" lines in SSE
                cors_origins: Allowed CORS origins (None = no CORS)
            """
            self._agent = agent
            self._agent_name = agent_name
            self._include_event_names = include_event_names
            self._cors_origins = cors_origins or []
            self._adapter = AGUIAdapter(agent, agent_name=agent_name)

        async def __call__(self, request: Request) -> StreamingResponse:
            """
            Handle POST request and return SSE stream.

            Args:
                request: FastAPI request with JSON body

            Returns:
                StreamingResponse with SSE stream
            """
            # Parse request body
            body = await request.json()
            message_content = body.get("message", "")
            # message_id = body.get("message_id")  # Reserved for future use

            # Create message
            message = Message(role="user", content=message_content)

            # Create SSE stream
            stream = AGUISSEStream(
                self._adapter,
                message,
                include_event_names=self._include_event_names,
            )

            # Create streaming response
            response = StreamingResponse(
                stream,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                },
            )

            # Add CORS headers if configured
            if self._cors_origins:
                origin = request.headers.get("origin", "")
                if origin in self._cors_origins or "*" in self._cors_origins:
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"

            return response

    FASTAPI_AVAILABLE = True

except ImportError:
    FASTAPI_AVAILABLE = False

    class AGUISSEEndpoint:  # type: ignore[no-redef]
        """Placeholder when FastAPI not available."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ImportError(
                "FastAPI is required for AGUISSEEndpoint. Install with: pip install fastapi"
            )


# aiohttp integration
try:
    from aiohttp import web

    def create_sse_handler(
        agent: Agent,
        agent_name: str | None = None,
        include_event_names: bool = False,
    ) -> Callable[[Any], Coroutine[Any, Any, Any]]:
        """
        Create aiohttp handler for AG-UI SSE streaming.

        Usage:
            from aiohttp import web

            handler = create_sse_handler(my_agent)
            app = web.Application()
            app.router.add_post("/chat", handler)

        Note: This is a simplified handler. For production, implement
        proper request parsing and error handling.
        """

        async def handler(request: Any) -> Any:
            """Handle SSE request."""
            # Parse request body
            body = await request.json()
            message_content = body.get("message", "")

            # Create message
            message = Message(role="user", content=message_content)

            # Create adapter and stream
            adapter = AGUIAdapter(agent, agent_name=agent_name)
            stream = AGUISSEStream(adapter, message, include_event_names)

            # Create streaming response
            response = web.StreamResponse(
                status=200,
                reason="OK",
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

            await response.prepare(request)

            # Stream events
            async for sse_chunk in stream:
                await response.write(sse_chunk.encode("utf-8"))

            await response.write_eof()
            return response

        return handler

    AIOHTTP_AVAILABLE = True

except ImportError:
    AIOHTTP_AVAILABLE = False

    async def create_sse_handler(*args: Any, **kwargs: Any) -> None:  # type: ignore[misc]
        """Placeholder when aiohttp not available."""
        raise ImportError("aiohttp is required for SSE handlers. Install with: pip install aiohttp")


__all__ = [
    "AGUISSEEndpoint",
    "AGUISSEStream",
    "SSEFormatter",
    "create_sse_handler",
    "create_sse_response_iterator",
]

"""Server-Sent Events (SSE) transport for AG-UI Standard.

SSE is the primary transport mechanism for AG-UI Standard protocol,
providing unidirectional streaming from server to client over HTTP.

This is the transport used by CopilotKit and other AG-UI frontends.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, AsyncIterator

if TYPE_CHECKING:
    from agenkit.protocols.agui.events import Event


class SSEMessageFormat:
    """Formats AG-UI events as Server-Sent Events.

    SSE format:
        data: {"type": "run_started", ...}

        data: {"type": "text_message_content", ...}


    Each event is prefixed with 'data: ' and followed by double newlines.

    Example:
        ```python
        formatter = SSEMessageFormat()
        event = TextMessageContentEvent(message_id="msg-1", delta="Hello")
        sse_line = formatter.format_event(event)
        # Returns: 'data: {"type": "text_message_content", "message_id": "msg-1", "delta": "Hello"}\\n\\n'
        ```
    """

    def format_event(self, event: Event) -> str:
        """Format a single event as SSE.

        Args:
            event: The AG-UI event to format

        Returns:
            SSE-formatted string with 'data: ' prefix and double newlines
        """
        # Serialize event to JSON
        event_dict = event.model_dump(exclude_none=True)
        event_json = json.dumps(event_dict, separators=(",", ":"))

        # Format as SSE
        return f"data: {event_json}\n\n"

    async def format_stream(self, events: AsyncIterator[Event]) -> AsyncIterator[str]:
        """Format a stream of events as SSE.

        Args:
            events: Async iterator of AG-UI events

        Yields:
            SSE-formatted strings
        """
        async for event in events:
            yield self.format_event(event)


class SSETransport:
    """SSE transport for AG-UI Standard protocol.

    This transport handles POST requests and streams AG-UI events
    back to the client using Server-Sent Events.

    Usage with FastAPI:
        ```python
        from fastapi import FastAPI, Request
        from fastapi.responses import StreamingResponse
        from agenkit import Agent, Message
        from agenkit.protocols.agui import AGUIAdapter
        from agenkit.protocols.agui.transports import SSETransport

        app = FastAPI()
        agent = MyAgent()
        adapter = AGUIAdapter(agent)
        transport = SSETransport(adapter)

        @app.post("/agui")
        async def agui_endpoint(request: Request):
            return await transport.handle_request(request)
        ```
    """

    def __init__(self, adapter):
        """Initialize SSE transport.

        Args:
            adapter: AGUIAdapter instance
        """
        self.adapter = adapter
        self.formatter = SSEMessageFormat()

    async def handle_request(self, request):
        """Handle an AG-UI request and return SSE response.

        This method expects a POST request with JSON body containing:
        - thread_id: Conversation thread identifier
        - run_id: Optional run identifier
        - message: User message content
        - messages: Optional list of messages
        - tools: Optional list of available tools

        Args:
            request: FastAPI Request object

        Returns:
            StreamingResponse with SSE events

        Example request body:
            ```json
            {
                "thread_id": "thread-abc-123",
                "run_id": "run-def-456",
                "message": "What's the weather like?",
                "messages": [
                    {"role": "user", "content": "What's the weather like?"}
                ],
                "tools": [
                    {
                        "name": "get_weather",
                        "description": "Get current weather",
                        "parameters": {...}
                    }
                ]
            }
            ```
        """
        # Import here to avoid circular imports
        from fastapi.responses import StreamingResponse

        from agenkit import Message

        # Parse request body
        body = await request.json()
        thread_id = body.get("thread_id")
        run_id = body.get("run_id")
        message_content = body.get("message", "")
        messages = body.get("messages", [])
        tools = body.get("tools", [])

        # Use the last message if messages array is provided
        if messages:
            last_message = messages[-1]
            message_content = last_message.get("content", message_content)

        # Create Message object
        message = Message(role="user", content=message_content)

        # Stream events
        async def event_generator():
            async for event in self.adapter.stream_events(
                message=message,
                thread_id=thread_id,
                run_id=run_id,
                input_data={"messages": messages, "tools": tools},
            ):
                yield self.formatter.format_event(event)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )


__all__ = ["SSEMessageFormat", "SSETransport"]

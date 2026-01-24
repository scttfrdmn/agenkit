#!/usr/bin/env python3
"""
AG-UI HITL with HTTP/SSE Transport Example.

Demonstrates Human-in-the-Loop with Server-Sent Events (SSE) transport.
Shows how approval Interrupt events are streamed to frontend clients via HTTP.

Key concepts:
- SSE streaming of HITL events
- Interrupt events sent as server-sent events
- Client-side event handling
- Real-world HTTP deployment

This example shows:
- HTTP server with SSE endpoint
- HITL adapter streaming via SSE
- Interrupt event formatting in SSE
- Client-side consumption (simulated)

Requirements:
    pip install aiohttp

Usage:
    # Terminal 1: Start server
    python 02_sse_transport_hitl.py

    # Terminal 2: Test with curl
    curl http://localhost:8080/chat/stream
"""

import asyncio
import json
import sys
from typing import Any

try:
    from aiohttp import web
except ImportError:
    print("Error: aiohttp not installed. Run: pip install aiohttp")
    sys.exit(1)

from agenkit import Agent, Message
from agenkit.patterns.human_in_loop import (
    ApprovalRequest,
    ApprovalResponse,
    HumanInLoopAgent,
    HumanInLoopConfig,
)
from agenkit.protocols.agui.events import (
    Interrupt,
    MetadataEvent,
    TextMessageChunk,
    TextMessageComplete,
    TextMessageStart,
)
from agenkit.protocols.agui.hitl import AGUIHumanInLoopAdapter


class ChatAgent(Agent):
    """Simple chat agent with confidence-based responses."""

    def __init__(self, name: str = "ChatAgent"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["chat", "qa"]

    async def process(self, message: Message) -> Message:
        """Process message and determine confidence."""
        content = message.content.lower()

        # High confidence for simple questions
        if any(word in content for word in ["hello", "hi", "what", "when", "where"]):
            confidence = 0.95
            response = "I'm confident I can help with that!"
        # Low confidence for complex/uncertain topics
        elif any(word in content for word in ["should", "advice", "recommend", "best"]):
            confidence = 0.6
            response = "Let me think about that carefully..."
        else:
            confidence = 0.7
            response = "I'll do my best to help."

        return Message(
            role="assistant",
            content=f"{response} (User asked: {message.content})",
            metadata={"confidence": confidence, "topic": "general"},
        )


async def approval_func(request: ApprovalRequest) -> ApprovalResponse:
    """Approval function for HITL decisions."""
    confidence = request.confidence

    # Simulate human review time
    await asyncio.sleep(0.2)

    # Auto-approve for this demo
    print(f"[Approval] Confidence: {confidence:.2f} - Approved")

    return ApprovalResponse(
        approved=True,
        feedback=f"Human approved (confidence: {confidence:.2f})",
    )


def format_sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format data as SSE event."""
    event_str = f"event: {event_type}\n"
    data_str = f"data: {json.dumps(data)}\n\n"
    return event_str + data_str


async def stream_handler(request: web.Request) -> web.StreamResponse:
    """Handle SSE streaming endpoint with HITL support."""
    response = web.StreamResponse()
    response.headers["Content-Type"] = "text/event-stream"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"

    await response.prepare(request)

    # Get message from query params or use default
    user_message = request.query.get("message", "Should I do this?")

    print(f"\n[SSE] Client connected - Message: {user_message}")

    # Create HITL-enabled agent
    chat_agent = ChatAgent()
    hil_agent = HumanInLoopAgent(
        HumanInLoopConfig(
            agent=chat_agent,
            approval_func=approval_func,
            approval_threshold=0.8,
        )
    )

    # Wrap with AG-UI HITL adapter
    adapter = AGUIHumanInLoopAdapter(hil_agent, agent_name="SSE-ChatAgent")

    # Stream events
    message = Message(role="user", content=user_message)

    try:
        async for event in adapter.stream_events(message):
            # Format event as SSE
            if isinstance(event, MetadataEvent):
                sse_data = format_sse_event(
                    "metadata",
                    {
                        "agent_name": event.data.get("agent_name"),
                        "capabilities": event.data.get("capabilities"),
                        "supports_hitl": event.data.get("supports_hitl"),
                    },
                )
                await response.write(sse_data.encode("utf-8"))
                print("[SSE] Sent metadata event")

            elif isinstance(event, Interrupt):
                sse_data = format_sse_event(
                    "interrupt",
                    {
                        "interrupt_id": event.interrupt_id,
                        "reason": event.reason.value,
                        "message": event.message,
                        "context": event.context,
                    },
                )
                await response.write(sse_data.encode("utf-8"))
                print(f"[SSE] ⚠️  Sent interrupt event - Status: {event.context.get('approval_status')}")

            elif isinstance(event, TextMessageStart):
                sse_data = format_sse_event(
                    "message_start",
                    {
                        "message_id": event.message_id,
                        "role": event.role,
                    },
                )
                await response.write(sse_data.encode("utf-8"))
                print("[SSE] Message started")

            elif isinstance(event, TextMessageChunk):
                sse_data = format_sse_event(
                    "message_chunk",
                    {
                        "message_id": event.message_id,
                        "content": event.content,
                    },
                )
                await response.write(sse_data.encode("utf-8"))

            elif isinstance(event, TextMessageComplete):
                sse_data = format_sse_event(
                    "message_complete",
                    {
                        "message_id": event.message_id,
                        "content": event.content,
                        "finish_reason": event.finish_reason,
                        "metadata": event.metadata,
                    },
                )
                await response.write(sse_data.encode("utf-8"))
                print("[SSE] Message completed")

        # Send completion
        sse_data = format_sse_event("done", {"status": "complete"})
        await response.write(sse_data.encode("utf-8"))
        print("[SSE] Stream completed\n")

    except Exception as e:
        print(f"[SSE] Error: {e}")
        sse_data = format_sse_event("error", {"message": str(e)})
        await response.write(sse_data.encode("utf-8"))

    return response


async def health_handler(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.Response(text="OK", status=200)


async def index_handler(request: web.Request) -> web.Response:
    """Serve simple HTML client."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AG-UI HITL SSE Demo</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #333; }
            .event { margin: 10px 0; padding: 10px; border-left: 3px solid #ccc; }
            .metadata { border-color: #3498db; background: #ecf0f1; }
            .interrupt { border-color: #e74c3c; background: #fadbd8; }
            .message { border-color: #2ecc71; background: #d5f4e6; }
            input { padding: 10px; width: 70%; margin-right: 10px; }
            button { padding: 10px 20px; background: #3498db; color: white; border: none; cursor: pointer; }
            button:hover { background: #2980b9; }
            pre { background: #f8f9fa; padding: 10px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>🎯 AG-UI HITL SSE Demo</h1>
        <p>Test Human-in-the-Loop with Server-Sent Events</p>

        <div>
            <input type="text" id="message" value="Should I make this decision?" placeholder="Enter message...">
            <button onclick="startStream()">Send</button>
        </div>

        <div id="events" style="margin-top: 20px;"></div>

        <script>
            let eventSource = null;

            function startStream() {
                const message = document.getElementById('message').value;
                const eventsDiv = document.getElementById('events');
                eventsDiv.innerHTML = '<p>Connecting...</p>';

                if (eventSource) {
                    eventSource.close();
                }

                const url = `/chat/stream?message=${encodeURIComponent(message)}`;
                eventSource = new EventSource(url);

                eventSource.addEventListener('metadata', (e) => {
                    const data = JSON.parse(e.data);
                    eventsDiv.innerHTML += `
                        <div class="event metadata">
                            <strong>📋 Metadata</strong><br>
                            Agent: ${data.agent_name}<br>
                            HITL: ${data.supports_hitl ? '✓' : '✗'}
                        </div>
                    `;
                });

                eventSource.addEventListener('interrupt', (e) => {
                    const data = JSON.parse(e.data);
                    eventsDiv.innerHTML += `
                        <div class="event interrupt">
                            <strong>⚠️ Interrupt - ${data.reason}</strong><br>
                            ${data.message}<br>
                            <pre>${JSON.stringify(data.context, null, 2)}</pre>
                        </div>
                    `;
                });

                eventSource.addEventListener('message_start', (e) => {
                    eventsDiv.innerHTML += '<div class="event message"><strong>💬 Message:</strong><br><span id="content"></span></div>';
                });

                eventSource.addEventListener('message_chunk', (e) => {
                    const data = JSON.parse(e.data);
                    const contentSpan = document.getElementById('content');
                    if (contentSpan) {
                        contentSpan.textContent += data.content;
                    }
                });

                eventSource.addEventListener('message_complete', (e) => {
                    const data = JSON.parse(e.data);
                    eventsDiv.innerHTML += `
                        <div class="event metadata">
                            <strong>✓ Complete</strong><br>
                            Finish: ${data.finish_reason}
                        </div>
                    `;
                });

                eventSource.addEventListener('done', (e) => {
                    eventsDiv.innerHTML += '<p><strong>✅ Stream complete</strong></p>';
                    eventSource.close();
                });

                eventSource.onerror = (e) => {
                    eventsDiv.innerHTML += '<div class="event interrupt"><strong>❌ Error</strong></div>';
                    eventSource.close();
                };
            }
        </script>
    </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html")


async def start_server() -> None:
    """Start HTTP server with SSE endpoint."""
    app = web.Application()

    # Routes
    app.router.add_get("/", index_handler)
    app.router.add_get("/health", health_handler)
    app.router.add_get("/chat/stream", stream_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "localhost", 8080)
    await site.start()

    print("=" * 70)
    print("🚀 AG-UI HITL SSE Server Started")
    print("=" * 70)
    print("\nEndpoints:")
    print("  • Web UI:      http://localhost:8080/")
    print("  • SSE Stream:  http://localhost:8080/chat/stream")
    print("  • Health:      http://localhost:8080/health")
    print("\nTest commands:")
    print('  curl "http://localhost:8080/chat/stream?message=Hello"')
    print('  curl "http://localhost:8080/chat/stream?message=Should+I+do+this?"')
    print("\nPress Ctrl+C to stop\n")

    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(start_server())

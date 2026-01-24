#!/usr/bin/env python3
"""
AG-UI HITL with WebSocket Transport Example.

Demonstrates Human-in-the-Loop with WebSocket bidirectional communication.
Shows how Interrupt events can be sent to clients and (future) how clients
can respond with InterruptResponse messages.

Key concepts:
- WebSocket bidirectional streaming
- Interrupt events sent to clients
- Full-duplex communication for HITL
- Real-time approval workflow

This example shows:
- WebSocket server with HITL support
- Interrupt event broadcasting
- Client message handling
- Bidirectional message flow

Requirements:
    pip install websockets

Usage:
    # Terminal 1: Start server
    python 03_websocket_hitl.py

    # Terminal 2: Test with websocat (install: cargo install websocat)
    echo '{"type": "message", "content": "Should I proceed?"}' | websocat ws://localhost:8765
"""

import asyncio
import json
import sys
from typing import Any

try:
    import websockets  # type: ignore[import-not-found]
    from websockets.server import WebSocketServerProtocol  # type: ignore[import-not-found]
except ImportError:
    print("Error: websockets not installed. Run: pip install websockets")
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


class DecisionAgent(Agent):
    """Agent that makes decisions with varying confidence."""

    def __init__(self, name: str = "DecisionAgent"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["decision-making", "analysis"]

    async def process(self, message: Message) -> Message:
        """Process decision request."""
        content = message.content.lower()

        # Analyze request complexity
        if "critical" in content or "important" in content or "should" in content:
            confidence = 0.5  # Low confidence for critical decisions
            response = "This requires careful consideration."
        elif "simple" in content or "easy" in content:
            confidence = 0.95  # High confidence for simple decisions
            response = "This is straightforward."
        else:
            confidence = 0.7
            response = "I'll analyze this carefully."

        return Message(
            role="assistant",
            content=f"{response} Regarding: {message.content}",
            metadata={
                "confidence": confidence,
                "decision_type": "critical" if confidence < 0.8 else "routine",
            },
        )


async def approval_func(request: ApprovalRequest) -> ApprovalResponse:
    """Approval function with detailed logging."""
    confidence = request.confidence
    decision_type = request.context.get("decision_type", "unknown")

    print("\n[Approval System]")
    print(f"  Confidence: {confidence:.2f}")
    print(f"  Decision Type: {decision_type}")
    print(f"  Threshold: {request.context.get('approval_threshold')}")
    print(f"  Shortfall: {request.context.get('confidence_shortfall'):.2f}")

    # Simulate human review
    await asyncio.sleep(0.3)

    # For demo, auto-approve
    approved = True
    feedback = f"Approved by supervisor (confidence: {confidence:.2f})"

    print(f"  Decision: {'✅ Approved' if approved else '❌ Rejected'}")
    print(f"  Feedback: {feedback}\n")

    return ApprovalResponse(approved=approved, feedback=feedback)


async def handle_client(websocket: WebSocketServerProtocol, path: str) -> None:
    """Handle WebSocket client connection."""
    client_id = id(websocket)
    print(f"\n[WebSocket] Client {client_id} connected from {websocket.remote_address}")

    try:
        # Create HITL-enabled agent
        decision_agent = DecisionAgent()
        hil_agent = HumanInLoopAgent(
            HumanInLoopConfig(
                agent=decision_agent,
                approval_func=approval_func,
                approval_threshold=0.8,
            )
        )

        # Wrap with AG-UI HITL adapter
        adapter = AGUIHumanInLoopAdapter(hil_agent, agent_name="WebSocket-DecisionAgent")

        # Listen for messages
        async for raw_message in websocket:
            try:
                # Parse client message
                client_msg = json.loads(raw_message)
                msg_type = client_msg.get("type", "unknown")

                print(f"[WebSocket] Received {msg_type} from client {client_id}")

                if msg_type == "message":
                    # Process user message
                    content = client_msg.get("content", "")
                    print(f"  Content: {content}")

                    message = Message(role="user", content=content)

                    # Stream events back to client
                    async for event in adapter.stream_events(message):
                        # Convert event to JSON
                        event_data: dict[str, Any] = {
                            "type": event.__class__.__name__,
                        }

                        if isinstance(event, MetadataEvent):
                            event_data.update(
                                {
                                    "agent_name": event.data.get("agent_name"),
                                    "capabilities": event.data.get("capabilities"),
                                    "supports_hitl": event.data.get("supports_hitl"),
                                }
                            )

                        elif isinstance(event, Interrupt):
                            event_data.update(
                                {
                                    "interrupt_id": event.interrupt_id,
                                    "reason": event.reason.value,
                                    "message": event.message,
                                    "context": event.context,
                                    "actions": [a.value for a in event.actions],
                                }
                            )
                            print(f"  ⚠️  Sending Interrupt: {event.context.get('approval_status')}")

                        elif isinstance(event, TextMessageStart):
                            event_data.update(
                                {
                                    "message_id": event.message_id,
                                    "role": event.role,
                                }
                            )

                        elif isinstance(event, TextMessageChunk):
                            event_data.update(
                                {
                                    "message_id": event.message_id,
                                    "content": event.content,
                                }
                            )

                        elif isinstance(event, TextMessageComplete):
                            event_data.update(
                                {
                                    "message_id": event.message_id,
                                    "content": event.content,
                                    "finish_reason": event.finish_reason,
                                    "metadata": event.metadata,
                                }
                            )

                        # Send event to client
                        await websocket.send(json.dumps(event_data))

                    # Send completion marker
                    await websocket.send(json.dumps({"type": "StreamComplete"}))
                    print("  ✓ Stream completed")

                elif msg_type == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))

                else:
                    print(f"  Unknown message type: {msg_type}")

            except json.JSONDecodeError as e:
                error_msg = json.dumps({"type": "error", "message": f"Invalid JSON: {e}"})
                await websocket.send(error_msg)

            except Exception as e:
                print(f"  Error processing message: {e}")
                error_msg = json.dumps({"type": "error", "message": str(e)})
                await websocket.send(error_msg)

    except websockets.exceptions.ConnectionClosed:
        print(f"[WebSocket] Client {client_id} disconnected")

    except Exception as e:
        print(f"[WebSocket] Error: {e}")

    finally:
        print(f"[WebSocket] Client {client_id} connection closed\n")


async def start_server() -> None:
    """Start WebSocket server."""
    print("=" * 70)
    print("🚀 AG-UI HITL WebSocket Server Starting...")
    print("=" * 70)

    server = await websockets.serve(handle_client, "localhost", 8765)

    print("\n✅ Server running on ws://localhost:8765")
    print("\nTest commands:")
    print('  echo \'{"type": "message", "content": "Should I proceed?"}\' | websocat ws://localhost:8765')
    print('  echo \'{"type": "message", "content": "This is a critical decision"}\' | websocat ws://localhost:8765')
    print('  echo \'{"type": "message", "content": "Simple task"}\' | websocat ws://localhost:8765')
    print("\nMessage format:")
    print('  {"type": "message", "content": "your message here"}')
    print("\nPress Ctrl+C to stop\n")

    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        server.close()
        await server.wait_closed()


# Simple Python WebSocket client for testing
async def test_client() -> None:
    """Test client that demonstrates full interaction."""
    print("\n" + "=" * 70)
    print("🧪 Test Client - Demonstrating HITL Workflow")
    print("=" * 70 + "\n")

    uri = "ws://localhost:8765"

    async with websockets.connect(uri) as websocket:
        # Test 1: High confidence (no approval needed)
        print("Test 1: High confidence message")
        print("-" * 50)
        await websocket.send(
            json.dumps({"type": "message", "content": "This is a simple task"})
        )

        interrupt_count = 0
        while True:
            response = await websocket.recv()
            data = json.loads(response)

            if data["type"] == "StreamComplete":
                break
            elif data["type"] == "Interrupt":
                interrupt_count += 1
                print(f"  ⚠️  Interrupt received: {data.get('context', {}).get('approval_status')}")

        print(f"  Interrupts: {interrupt_count} (expected: 0)\n")

        # Test 2: Low confidence (approval required)
        print("\nTest 2: Low confidence message")
        print("-" * 50)
        await websocket.send(
            json.dumps({"type": "message", "content": "This is a critical decision"})
        )

        interrupt_count = 0
        while True:
            response = await websocket.recv()
            data = json.loads(response)

            if data["type"] == "StreamComplete":
                break
            elif data["type"] == "Interrupt":
                interrupt_count += 1
                print("  ⚠️  Interrupt received!")
                print(f"     Reason: {data.get('reason')}")
                print(f"     Status: {data.get('context', {}).get('approval_status')}")
                print(f"     Confidence: {data.get('context', {}).get('confidence')}")

        print(f"  Interrupts: {interrupt_count} (expected: 1)\n")

    print("✅ Test client completed!")


async def main() -> None:
    """Main entry point with mode selection."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run test client
        await test_client()
    else:
        # Run server
        await start_server()


if __name__ == "__main__":
    asyncio.run(main())

"""AG-UI Standard Protocol Implementation.

This module implements the full AG-UI (Agent-User Interface) specification,
enabling Agenkit agents to connect with AG-UI-compatible frontends like
CopilotKit, LangGraph Studio, and other ecosystem tools.

AG-UI is an open, lightweight, event-based protocol that standardizes how
AI agents connect to user-facing applications.

Specification: https://docs.ag-ui.com/

Basic Usage:
    ```python
    from agenkit import Agent, Message
    from agenkit.protocols.agui import AGUIAdapter, SSETransport
    from fastapi import FastAPI, Request

    app = FastAPI()
    agent = MyAgent()
    adapter = AGUIAdapter(agent)
    transport = SSETransport(adapter)

    @app.post("/agui")
    async def agui_endpoint(request: Request):
        return await transport.handle_request(request)
    ```

Key Differences from AG-UI Simple:
- Full AG-UI spec compliance (CopilotKit-compatible)
- SSE transport over POST (industry standard)
- Rich lifecycle events (runs, steps)
- Tool call tracking (start, args, end, result)
- State management with JSON Patch
- 15+ event types vs 5 in Simple

When to use AG-UI Standard:
- CopilotKit integration
- Production deployments
- Complex multi-step workflows
- Tool-heavy agents
- Ecosystem interoperability

For learning and prototyping, see: agenkit.protocols.agui_simple
"""

from agenkit.protocols.agui.adapter import AGUIAdapter
from agenkit.protocols.agui.events import (
    ActivityDeltaEvent,
    ActivitySnapshotEvent,
    BaseEvent,
    CustomEvent,
    Event,
    EventType,
    MessagesSnapshotEvent,
    RawEvent,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StateDeltaEvent,
    StateSnapshotEvent,
    StepFinishedEvent,
    StepStartedEvent,
    TextMessageChunkEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallChunkEvent,
    ToolCallEndEvent,
    ToolCallProgressEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from agenkit.protocols.agui.state import StateManager
from agenkit.protocols.agui.tools import ProgressReporter, ToolCallTracker, ToolRegistry

__all__ = [
    "AGUIAdapter",
    # State & Tools
    "StateManager",
    "ProgressReporter",
    "ToolCallTracker",
    "ToolRegistry",
    # Event types
    "EventType",
    "BaseEvent",
    "Event",
    # Lifecycle
    "RunStartedEvent",
    "RunFinishedEvent",
    "RunErrorEvent",
    "StepStartedEvent",
    "StepFinishedEvent",
    # Text Messages
    "TextMessageStartEvent",
    "TextMessageContentEvent",
    "TextMessageEndEvent",
    "TextMessageChunkEvent",
    # Tool Calls
    "ToolCallStartEvent",
    "ToolCallArgsEvent",
    "ToolCallEndEvent",
    "ToolCallProgressEvent",
    "ToolCallResultEvent",
    "ToolCallChunkEvent",
    # State Management
    "StateSnapshotEvent",
    "StateDeltaEvent",
    "MessagesSnapshotEvent",
    # Activity
    "ActivitySnapshotEvent",
    "ActivityDeltaEvent",
    # Special
    "RawEvent",
    "CustomEvent",
]

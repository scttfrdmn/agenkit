"""
AG-UI (Agent-User Interaction) Protocol

Provides streaming agent-to-frontend communication using the AG-UI protocol.

Reference: https://docs.ag-ui.com
"""

from agenkit.protocols.agui.adapter import (
    AGUIAdapter,
    StreamingAGUIAdapter,
    wrap_agent_as_agui,
)
from agenkit.protocols.agui.events import (
    AGUIEvent,
    Attachment,
    AttachmentType,
    BaseEvent,
    ErrorEvent,
    EventType,
    HeartbeatEvent,
    Interrupt,
    InterruptAction,
    InterruptReason,
    InterruptResponse,
    MetadataEvent,
    StateDelta,
    TextMessageChunk,
    TextMessageComplete,
    TextMessageStart,
    ToolCallChunk,
    ToolCallComplete,
    ToolCallStart,
    parse_event,
)
from agenkit.protocols.agui.transports.http import (
    AGUISSEEndpoint,
    AGUISSEStream,
    SSEFormatter,
    create_sse_handler,
    create_sse_response_iterator,
)

__all__ = [
    "AGUIAdapter",
    "AGUIEvent",
    "AGUISSEEndpoint",
    "AGUISSEStream",
    "Attachment",
    "AttachmentType",
    "BaseEvent",
    "ErrorEvent",
    "EventType",
    "HeartbeatEvent",
    "Interrupt",
    "InterruptAction",
    "InterruptReason",
    "InterruptResponse",
    "MetadataEvent",
    "SSEFormatter",
    "StateDelta",
    "StreamingAGUIAdapter",
    "TextMessageChunk",
    "TextMessageComplete",
    "TextMessageStart",
    "ToolCallChunk",
    "ToolCallComplete",
    "ToolCallStart",
    "create_sse_handler",
    "create_sse_response_iterator",
    "parse_event",
    "wrap_agent_as_agui",
]

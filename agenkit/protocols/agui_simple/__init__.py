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
from agenkit.protocols.agui.hitl import AGUIHumanInLoopAdapter
from agenkit.protocols.agui.transports.http import (
    AGUISSEEndpoint,
    AGUISSEStream,
    SSEFormatter,
    create_sse_handler,
    create_sse_response_iterator,
)
from agenkit.protocols.agui.transports.websocket import (
    AGUIWebSocketHandler,
    AGUIWebSocketStream,
    WebSocketMessageFormat,
    create_websocket_handler,
)

__all__ = [
    "AGUIAdapter",
    "AGUIEvent",
    "AGUIHumanInLoopAdapter",
    "AGUISSEEndpoint",
    "AGUISSEStream",
    "AGUIWebSocketHandler",
    "AGUIWebSocketStream",
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
    "WebSocketMessageFormat",
    "create_sse_handler",
    "create_sse_response_iterator",
    "create_websocket_handler",
    "parse_event",
    "wrap_agent_as_agui",
]

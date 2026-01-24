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

__all__ = [
    "AGUIAdapter",
    "AGUIEvent",
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
    "StateDelta",
    "StreamingAGUIAdapter",
    "TextMessageChunk",
    "TextMessageComplete",
    "TextMessageStart",
    "ToolCallChunk",
    "ToolCallComplete",
    "ToolCallStart",
    "parse_event",
    "wrap_agent_as_agui",
]

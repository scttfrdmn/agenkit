#!/usr/bin/env python3
"""
AG-UI Protocol Event Types and Data Structures

Implements the AG-UI (Agent-User Interaction) protocol event types
for streaming agent interactions with frontends.

Reference: https://docs.ag-ui.com/protocol/events

Event Types Implemented:
- TEXT_MESSAGE_START, TEXT_MESSAGE_CHUNK, TEXT_MESSAGE_COMPLETE
- TOOL_CALL_START, TOOL_CALL_CHUNK, TOOL_CALL_COMPLETE
- STATE_DELTA (shared state synchronization)
- INTERRUPT (human-in-the-loop)
- ERROR (error reporting)
- ATTACHMENT (multimodal support)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, cast


class EventType(str, Enum):
    """AG-UI event type enumeration."""

    # Text message events
    TEXT_MESSAGE_START = "text_message_start"
    TEXT_MESSAGE_CHUNK = "text_message_chunk"
    TEXT_MESSAGE_COMPLETE = "text_message_complete"

    # Tool call events
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_CHUNK = "tool_call_chunk"
    TOOL_CALL_COMPLETE = "tool_call_complete"

    # State management
    STATE_DELTA = "state_delta"

    # Human-in-the-loop
    INTERRUPT = "interrupt"

    # Error handling
    ERROR = "error"

    # Multimodal
    ATTACHMENT = "attachment"

    # Metadata events
    METADATA = "metadata"
    HEARTBEAT = "heartbeat"


class InterruptReason(str, Enum):
    """Reasons for agent interruption (HITL)."""

    APPROVAL_REQUIRED = "approval_required"
    CLARIFICATION_NEEDED = "clarification_needed"
    TOOL_CONFIRMATION = "tool_confirmation"
    ESCALATION = "escalation"
    USER_REQUESTED = "user_requested"


class InterruptAction(str, Enum):
    """Actions user can take in response to interruption."""

    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"
    RETRY = "retry"
    ESCALATE = "escalate"
    CANCEL = "cancel"


class AttachmentType(str, Enum):
    """Types of attachments for multimodal support."""

    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    TRANSCRIPT = "transcript"


@dataclass
class BaseEvent:
    """Base class for all AG-UI events."""

    event_type: EventType
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z")
    )
    event_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return asdict(self)

    def to_json_line(self) -> str:
        """Convert event to JSON line format (JSONL)."""
        import json

        return json.dumps(self.to_dict())


@dataclass
class TextMessageStart(BaseEvent):
    """
    Start of a text message from the agent.

    Signals that the agent is beginning to generate a text response.
    """

    event_type: EventType = field(default=EventType.TEXT_MESSAGE_START, init=False)
    message_id: str | None = None
    role: str = "assistant"


@dataclass
class TextMessageChunk(BaseEvent):
    """
    Chunk of text message content (streaming).

    Contains incremental text content as the agent generates the response.
    """

    event_type: EventType = field(default=EventType.TEXT_MESSAGE_CHUNK, init=False)
    message_id: str | None = None
    content: str = ""


@dataclass
class TextMessageComplete(BaseEvent):
    """
    Complete text message from the agent.

    Signals that the agent has finished generating the text response.
    """

    event_type: EventType = field(default=EventType.TEXT_MESSAGE_COMPLETE, init=False)
    message_id: str | None = None
    content: str = ""
    finish_reason: str | None = None


@dataclass
class ToolCallStart(BaseEvent):
    """
    Start of a tool call execution.

    Signals that the agent is beginning to execute a tool.
    """

    event_type: EventType = field(default=EventType.TOOL_CALL_START, init=False)
    tool_call_id: str | None = None
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCallChunk(BaseEvent):
    """
    Chunk of tool call execution progress (streaming).

    Contains incremental updates about tool execution progress.
    """

    event_type: EventType = field(default=EventType.TOOL_CALL_CHUNK, init=False)
    tool_call_id: str | None = None
    progress: str = ""
    percentage: float | None = None


@dataclass
class ToolCallComplete(BaseEvent):
    """
    Complete tool call result.

    Contains the final result of tool execution.
    """

    event_type: EventType = field(default=EventType.TOOL_CALL_COMPLETE, init=False)
    tool_call_id: str | None = None
    tool_name: str = ""
    result: Any = None
    success: bool = True
    error: str | None = None


@dataclass
class StateDelta(BaseEvent):
    """
    Incremental state update (event sourcing pattern).

    Contains partial state changes to synchronize agent and frontend state.
    Instead of sending full state snapshots, only changes are transmitted.

    Example:
        StateDelta(
            path=["user", "preferences", "theme"],
            operation="set",
            value="dark"
        )
    """

    event_type: EventType = field(default=EventType.STATE_DELTA, init=False)
    path: list[str] = field(default_factory=list)
    operation: str = "set"  # set, delete, append, merge
    value: Any = None
    previous_value: Any = None


@dataclass
class Interrupt(BaseEvent):
    """
    Human-in-the-loop interruption request.

    Agent requests human intervention before proceeding.

    Example:
        Interrupt(
            reason=InterruptReason.APPROVAL_REQUIRED,
            message="About to delete 100 files. Approve?",
            context={"file_count": 100, "directory": "/tmp/data"},
            actions=[InterruptAction.APPROVE, InterruptAction.REJECT]
        )
    """

    event_type: EventType = field(default=EventType.INTERRUPT, init=False)
    interrupt_id: str | None = None
    reason: InterruptReason = InterruptReason.APPROVAL_REQUIRED
    message: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    actions: list[InterruptAction] = field(
        default_factory=lambda: [InterruptAction.APPROVE, InterruptAction.REJECT]
    )
    timeout_seconds: float | None = None


@dataclass
class InterruptResponse:
    """
    User's response to an interrupt request.

    Not an event itself, but a data structure for handling interrupt responses.
    """

    interrupt_id: str
    action: InterruptAction
    response: str | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorEvent(BaseEvent):
    """
    Error event for reporting failures.

    Reports errors that occur during agent execution.
    """

    event_type: EventType = field(default=EventType.ERROR, init=False)
    error_code: str | None = None
    error_message: str = ""
    error_details: dict[str, Any] = field(default_factory=dict)
    recoverable: bool = True


@dataclass
class Attachment(BaseEvent):
    """
    Multimodal attachment (images, audio, files, etc.).

    Example:
        Attachment(
            attachment_type=AttachmentType.IMAGE,
            content_url="https://example.com/image.png",
            content_type="image/png",
            metadata={"width": 800, "height": 600}
        )
    """

    event_type: EventType = field(default=EventType.ATTACHMENT, init=False)
    attachment_id: str | None = None
    attachment_type: AttachmentType = AttachmentType.FILE
    content_url: str | None = None
    content_data: str | None = None  # Base64 encoded for inline data
    content_type: str | None = None  # MIME type
    filename: str | None = None
    size_bytes: int | None = None


@dataclass
class MetadataEvent(BaseEvent):
    """
    Metadata event for passing arbitrary metadata.

    Used for agent metadata, configuration, capabilities, etc.
    """

    event_type: EventType = field(default=EventType.METADATA, init=False)
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class HeartbeatEvent(BaseEvent):
    """
    Heartbeat event to keep connection alive.

    Useful for long-running processes or to detect connection issues.
    """

    event_type: EventType = field(default=EventType.HEARTBEAT, init=False)
    sequence: int = 0


# Type alias for any AG-UI event
AGUIEvent = (
    TextMessageStart
    | TextMessageChunk
    | TextMessageComplete
    | ToolCallStart
    | ToolCallChunk
    | ToolCallComplete
    | StateDelta
    | Interrupt
    | ErrorEvent
    | Attachment
    | MetadataEvent
    | HeartbeatEvent
)


def parse_event(event_dict: dict[str, Any]) -> AGUIEvent:
    """
    Parse a dictionary into the appropriate AG-UI event type.

    Args:
        event_dict: Dictionary representation of an event

    Returns:
        Parsed event object

    Raises:
        ValueError: If event_type is unknown
    """
    event_type_str = event_dict.get("event_type")

    if not event_type_str:
        raise ValueError("Event dictionary missing 'event_type' field")

    try:
        event_type = EventType(event_type_str)
    except ValueError as e:
        raise ValueError(f"Unknown event type: {event_type_str}") from e

    # Map event types to their corresponding classes
    event_class_map = {
        EventType.TEXT_MESSAGE_START: TextMessageStart,
        EventType.TEXT_MESSAGE_CHUNK: TextMessageChunk,
        EventType.TEXT_MESSAGE_COMPLETE: TextMessageComplete,
        EventType.TOOL_CALL_START: ToolCallStart,
        EventType.TOOL_CALL_CHUNK: ToolCallChunk,
        EventType.TOOL_CALL_COMPLETE: ToolCallComplete,
        EventType.STATE_DELTA: StateDelta,
        EventType.INTERRUPT: Interrupt,
        EventType.ERROR: ErrorEvent,
        EventType.ATTACHMENT: Attachment,
        EventType.METADATA: MetadataEvent,
        EventType.HEARTBEAT: HeartbeatEvent,
    }

    event_class = event_class_map.get(event_type)

    if not event_class:
        raise ValueError(f"No class mapping for event type: {event_type}")

    # Remove event_type from dict since it's set by the class
    event_data = {k: v for k, v in event_dict.items() if k != "event_type"}

    return cast("AGUIEvent", event_class(**event_data))

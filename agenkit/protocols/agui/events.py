"""AG-UI Standard Protocol Event Types.

This module implements the full AG-UI specification with Pydantic models.
AG-UI (Agent-User Interface) is an open, lightweight, event-based protocol
that standardizes how AI agents connect to user-facing applications.

Specification: https://docs.ag-ui.com/

Event Categories:
- Lifecycle: RunStarted, RunFinished, RunError, StepStarted, StepFinished
- Text Messages: TextMessageStart, TextMessageContent, TextMessageEnd
- Tool Calls: ToolCallStart, ToolCallArgs, ToolCallEnd, ToolCallResult
- State Management: StateSnapshot, StateDelta, MessagesSnapshot
- Activity: ActivitySnapshot, ActivityDelta
- Special: Raw, Custom
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field, ConfigDict


class EventType(str, Enum):
    """AG-UI Standard event types."""

    # Lifecycle events
    RUN_STARTED = "run_started"
    RUN_FINISHED = "run_finished"
    RUN_ERROR = "run_error"
    STEP_STARTED = "step_started"
    STEP_FINISHED = "step_finished"

    # Text message events
    TEXT_MESSAGE_START = "text_message_start"
    TEXT_MESSAGE_CONTENT = "text_message_content"
    TEXT_MESSAGE_END = "text_message_end"
    TEXT_MESSAGE_CHUNK = "text_message_chunk"  # Convenience wrapper

    # Tool call events
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_ARGS = "tool_call_args"
    TOOL_CALL_END = "tool_call_end"
    TOOL_CALL_RESULT = "tool_call_result"
    TOOL_CALL_PROGRESS = "tool_call_progress"
    TOOL_CALL_CHUNK = "tool_call_chunk"  # Convenience wrapper

    # State management events
    STATE_SNAPSHOT = "state_snapshot"
    STATE_DELTA = "state_delta"
    MESSAGES_SNAPSHOT = "messages_snapshot"

    # Activity events
    ACTIVITY_SNAPSHOT = "activity_snapshot"
    ACTIVITY_DELTA = "activity_delta"

    # Special events
    RAW = "raw"
    CUSTOM = "custom"


class BaseEvent(BaseModel):
    """Base class for all AG-UI events."""

    model_config = ConfigDict(use_enum_values=True)

    type: EventType
    timestamp: Optional[int] = Field(
        default_factory=lambda: int(datetime.now(UTC).timestamp() * 1000),
        description="Unix timestamp in milliseconds",
    )


# ============================================================================
# Lifecycle Events
# ============================================================================


class RunStartedEvent(BaseEvent):
    """Initiates an agent run with execution context."""

    type: Literal[EventType.RUN_STARTED] = EventType.RUN_STARTED
    thread_id: str = Field(description="Unique identifier for the conversation thread")
    run_id: str = Field(description="Unique identifier for this execution run")
    parent_run_id: Optional[str] = Field(
        default=None, description="Parent run ID for nested executions"
    )
    input: Optional[dict[str, Any]] = Field(
        default=None, description="Initial input parameters for the run"
    )


class RunFinishedEvent(BaseEvent):
    """Signals the successful completion of an agent run."""

    type: Literal[EventType.RUN_FINISHED] = EventType.RUN_FINISHED
    thread_id: str = Field(description="Thread identifier")
    run_id: str = Field(description="Run identifier")
    result: Optional[dict[str, Any]] = Field(
        default=None, description="Final result of the run"
    )


class RunErrorEvent(BaseEvent):
    """Indicates premature termination due to failure."""

    type: Literal[EventType.RUN_ERROR] = EventType.RUN_ERROR
    message: str = Field(description="Error message")
    code: Optional[str] = Field(default=None, description="Error code")
    details: Optional[dict[str, Any]] = Field(default=None, description="Additional error details")


class StepStartedEvent(BaseEvent):
    """Marks beginning of a discrete processing phase."""

    type: Literal[EventType.STEP_STARTED] = EventType.STEP_STARTED
    step_name: str = Field(description="Name of the processing step")
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Additional step metadata"
    )


class StepFinishedEvent(BaseEvent):
    """Marks completion of a processing phase."""

    type: Literal[EventType.STEP_FINISHED] = EventType.STEP_FINISHED
    step_name: str = Field(description="Name of the completed step")
    result: Optional[dict[str, Any]] = Field(default=None, description="Step result")


# ============================================================================
# Text Message Events
# ============================================================================


class TextMessageStartEvent(BaseEvent):
    """Initiates streaming textual content delivery."""

    type: Literal[EventType.TEXT_MESSAGE_START] = EventType.TEXT_MESSAGE_START
    message_id: str = Field(description="Unique message identifier")
    role: str = Field(description="Message role (assistant, user, system)")
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Message metadata"
    )


class TextMessageContentEvent(BaseEvent):
    """Delivers incremental parts of the message text."""

    type: Literal[EventType.TEXT_MESSAGE_CONTENT] = EventType.TEXT_MESSAGE_CONTENT
    message_id: str = Field(description="Message identifier")
    delta: str = Field(description="Incremental text content")


class TextMessageEndEvent(BaseEvent):
    """Signals completion of message transmission."""

    type: Literal[EventType.TEXT_MESSAGE_END] = EventType.TEXT_MESSAGE_END
    message_id: str = Field(description="Message identifier")
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Final message metadata"
    )


class TextMessageChunkEvent(BaseEvent):
    """Convenience wrapper combining start, content, and end.

    Use this for simpler streaming where you don't need separate
    start/content/end events.
    """

    type: Literal[EventType.TEXT_MESSAGE_CHUNK] = EventType.TEXT_MESSAGE_CHUNK
    message_id: Optional[str] = Field(
        default=None, description="Message ID (required for first chunk)"
    )
    role: Optional[str] = Field(default=None, description="Role (for first chunk)")
    delta: Optional[str] = Field(default=None, description="Text content delta")
    is_first: bool = Field(default=False, description="Whether this is the first chunk")
    is_last: bool = Field(default=False, description="Whether this is the last chunk")


# ============================================================================
# Tool Call Events
# ============================================================================


class ToolCallStartEvent(BaseEvent):
    """Announces tool invocation with parameters."""

    type: Literal[EventType.TOOL_CALL_START] = EventType.TOOL_CALL_START
    tool_call_id: str = Field(description="Unique tool call identifier")
    tool_call_name: str = Field(description="Name of the tool being called")
    parent_message_id: Optional[str] = Field(
        default=None, description="Parent message ID"
    )


class ToolCallArgsEvent(BaseEvent):
    """Delivers incremental parts of the tool's arguments."""

    type: Literal[EventType.TOOL_CALL_ARGS] = EventType.TOOL_CALL_ARGS
    tool_call_id: str = Field(description="Tool call identifier")
    delta: str = Field(description="Incremental argument JSON")


class ToolCallEndEvent(BaseEvent):
    """Marks argument transmission completion."""

    type: Literal[EventType.TOOL_CALL_END] = EventType.TOOL_CALL_END
    tool_call_id: str = Field(description="Tool call identifier")


class ToolCallProgressEvent(BaseEvent):
    """Reports progress during tool execution."""

    type: Literal[EventType.TOOL_CALL_PROGRESS] = EventType.TOOL_CALL_PROGRESS
    tool_call_id: str = Field(description="Tool call identifier")
    progress: float = Field(
        description="Progress percentage (0.0 to 1.0)", ge=0.0, le=1.0
    )
    status: Optional[str] = Field(
        default=None, description="Human-readable status message"
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Additional progress metadata"
    )


class ToolCallResultEvent(BaseEvent):
    """Provides tool execution output."""

    type: Literal[EventType.TOOL_CALL_RESULT] = EventType.TOOL_CALL_RESULT
    message_id: str = Field(description="Message identifier")
    tool_call_id: str = Field(description="Tool call identifier")
    content: Any = Field(description="Tool execution result")
    role: Optional[str] = Field(default="tool", description="Message role")


class ToolCallChunkEvent(BaseEvent):
    """Convenience wrapper for tool call streaming."""

    type: Literal[EventType.TOOL_CALL_CHUNK] = EventType.TOOL_CALL_CHUNK
    tool_call_id: str = Field(description="Tool call identifier")
    tool_call_name: Optional[str] = Field(
        default=None, description="Tool name (for first chunk)"
    )
    delta: Optional[str] = Field(default=None, description="Argument delta")
    is_first: bool = Field(default=False, description="Whether this is the first chunk")
    is_last: bool = Field(default=False, description="Whether this is the last chunk")


# ============================================================================
# State Management Events
# ============================================================================


class StateSnapshotEvent(BaseEvent):
    """Delivers a comprehensive representation of the agent's current state."""

    type: Literal[EventType.STATE_SNAPSHOT] = EventType.STATE_SNAPSHOT
    snapshot: dict[str, Any] = Field(description="Complete state snapshot")


class StateDeltaEvent(BaseEvent):
    """Applies incremental modifications using JSON Patch (RFC 6902)."""

    type: Literal[EventType.STATE_DELTA] = EventType.STATE_DELTA
    delta: list[dict[str, Any]] = Field(description="JSON Patch operations")


class MessagesSnapshotEvent(BaseEvent):
    """Provides complete conversation history."""

    type: Literal[EventType.MESSAGES_SNAPSHOT] = EventType.MESSAGES_SNAPSHOT
    messages: list[dict[str, Any]] = Field(description="List of messages")


# ============================================================================
# Activity Events
# ============================================================================


class ActivitySnapshotEvent(BaseEvent):
    """Delivers structured in-progress activity updates."""

    type: Literal[EventType.ACTIVITY_SNAPSHOT] = EventType.ACTIVITY_SNAPSHOT
    message_id: str = Field(description="Message identifier")
    activity_type: str = Field(description="Type of activity")
    content: Any = Field(description="Activity content")
    replace: Optional[bool] = Field(
        default=False, description="Whether to replace previous activity"
    )


class ActivityDeltaEvent(BaseEvent):
    """Applies incremental activity modifications."""

    type: Literal[EventType.ACTIVITY_DELTA] = EventType.ACTIVITY_DELTA
    message_id: str = Field(description="Message identifier")
    activity_type: str = Field(description="Type of activity")
    patch: list[dict[str, Any]] = Field(description="JSON Patch operations")


# ============================================================================
# Special Events
# ============================================================================


class RawEvent(BaseEvent):
    """Acts as a container for events originating from external systems."""

    type: Literal[EventType.RAW] = EventType.RAW
    event: dict[str, Any] = Field(description="Raw event data")
    source: Optional[str] = Field(default=None, description="Event source")


class CustomEvent(BaseEvent):
    """Enables protocol extensions for application-specific functionality."""

    type: Literal[EventType.CUSTOM] = EventType.CUSTOM
    name: str = Field(description="Custom event name")
    value: Any = Field(description="Custom event data")


# ============================================================================
# Discriminated Union of All Events
# ============================================================================

Event = Union[
    # Lifecycle
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    StepStartedEvent,
    StepFinishedEvent,
    # Text Messages
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageChunkEvent,
    # Tool Calls
    ToolCallStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallProgressEvent,
    ToolCallResultEvent,
    ToolCallChunkEvent,
    # State Management
    StateSnapshotEvent,
    StateDeltaEvent,
    MessagesSnapshotEvent,
    # Activity
    ActivitySnapshotEvent,
    ActivityDeltaEvent,
    # Special
    RawEvent,
    CustomEvent,
]


__all__ = [
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

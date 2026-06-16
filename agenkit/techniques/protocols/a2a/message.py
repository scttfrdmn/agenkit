"""
A2A Message Types.

Defines message format for Agent-to-Agent (A2A) protocol communication.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class MessageType(Enum):
    """A2A message types."""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class MessagePriority(Enum):
    """Message priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class A2AMessage:
    """
    Agent-to-Agent message.

    Standardized message format for cross-platform agent communication.

    Example:
        >>> message = A2AMessage(
        ...     from_agent="analyzer-001",
        ...     to_agent="summarizer-001",
        ...     action="summarize",
        ...     content={"text": "Analyze this document..."}
        ... )
    """

    # Routing
    from_agent: str
    to_agent: str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Message type and action
    message_type: MessageType = MessageType.REQUEST
    action: str = ""

    # Content
    content: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Priority and tracking
    priority: MessagePriority = MessagePriority.NORMAL
    correlation_id: str | None = None  # For request/response correlation
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    # Timeout and retry
    timeout_ms: int | None = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "message_id": self.message_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type.value,
            "action": self.action,
            "content": self.content,
            "metadata": self.metadata,
            "priority": self.priority.value,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "timeout_ms": self.timeout_ms,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "A2AMessage":
        """Create message from dictionary."""
        return A2AMessage(
            message_id=data.get("message_id", str(uuid.uuid4())),
            from_agent=data["from_agent"],
            to_agent=data["to_agent"],
            message_type=MessageType(data.get("message_type", "request")),
            action=data.get("action", ""),
            content=data.get("content", {}),
            metadata=data.get("metadata", {}),
            priority=MessagePriority(data.get("priority", "normal")),
            correlation_id=data.get("correlation_id"),
            timestamp=data.get("timestamp", datetime.now(UTC).isoformat()),
            timeout_ms=data.get("timeout_ms"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )

    def to_json(self) -> str:
        """Serialize to JSON."""
        import json

        return json.dumps(self.to_dict())

    @staticmethod
    def from_json(json_str: str) -> "A2AMessage":
        """Deserialize from JSON."""
        import json

        return A2AMessage.from_dict(json.loads(json_str))

    @staticmethod
    def from_agenkit_message(
        msg, from_agent: str, to_agent: str, action: str = "process"
    ) -> "A2AMessage":
        """
        Convert Agenkit Message to A2A Message.

        Args:
            msg: Agenkit Message
            from_agent: Sender agent ID
            to_agent: Recipient agent ID
            action: Action to perform

        Returns:
            A2A message
        """
        return A2AMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            action=action,
            content={"role": msg.role, "content": msg.content},
            metadata=msg.metadata or {},
        )

    def to_agenkit_message(self):
        """
        Convert A2A Message to Agenkit Message.

        Returns:
            Agenkit Message
        """
        from agenkit import Message

        # Extract content
        role = self.content.get("role", "user")
        content = self.content.get("content", "")

        # If content is just a string, use it directly
        if isinstance(self.content, str):
            content = self.content
        elif "text" in self.content:
            content = self.content["text"]

        return Message(
            role=role,
            content=content,
            metadata={
                **self.metadata,
                "a2a_message_id": self.message_id,
                "a2a_from_agent": self.from_agent,
                "a2a_action": self.action,
            },
        )

    def create_response(
        self, content: dict[str, Any], metadata: dict[str, Any] | None = None
    ) -> "A2AMessage":
        """
        Create response message for this request.

        Args:
            content: Response content
            metadata: Optional metadata

        Returns:
            Response message
        """
        return A2AMessage(
            from_agent=self.to_agent,
            to_agent=self.from_agent,
            message_type=MessageType.RESPONSE,
            action=self.action,
            content=content,
            metadata=metadata or {},
            correlation_id=self.message_id,  # Link to request
            priority=self.priority,
        )

    def create_error(
        self, error_code: str, error_message: str, details: dict[str, Any] | None = None
    ) -> "A2AMessage":
        """
        Create error response for this request.

        Args:
            error_code: Error code
            error_message: Error message
            details: Optional error details

        Returns:
            Error message
        """
        return A2AMessage(
            from_agent=self.to_agent,
            to_agent=self.from_agent,
            message_type=MessageType.ERROR,
            action=self.action,
            content={
                "error_code": error_code,
                "error_message": error_message,
                "details": details or {},
            },
            correlation_id=self.message_id,
            priority=self.priority,
        )


@dataclass
class AgentInfo:
    """
    Information about an agent in the A2A network.

    Used for agent discovery and capability advertisement.
    """

    agent_id: str
    name: str
    capabilities: list[str]
    endpoint: str  # URL or address
    transport: str = "http"  # "http", "grpc", "websocket"
    status: str = "online"  # "online", "offline", "busy"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "capabilities": self.capabilities,
            "endpoint": self.endpoint,
            "transport": self.transport,
            "status": self.status,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AgentInfo":
        """Create from dictionary."""
        return AgentInfo(
            agent_id=data["agent_id"],
            name=data["name"],
            capabilities=data.get("capabilities", []),
            endpoint=data["endpoint"],
            transport=data.get("transport", "http"),
            status=data.get("status", "online"),
            metadata=data.get("metadata", {}),
        )


def create_request(
    from_agent: str,
    to_agent: str,
    action: str,
    content: dict[str, Any],
    priority: MessagePriority = MessagePriority.NORMAL,
    timeout_ms: int | None = None,
) -> A2AMessage:
    """
    Create request message.

    Args:
        from_agent: Sender agent ID
        to_agent: Recipient agent ID
        action: Action to perform
        content: Message content
        priority: Message priority
        timeout_ms: Optional timeout in milliseconds

    Returns:
        Request message
    """
    return A2AMessage(
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=MessageType.REQUEST,
        action=action,
        content=content,
        priority=priority,
        timeout_ms=timeout_ms,
    )


def create_notification(
    from_agent: str, to_agent: str, action: str, content: dict[str, Any]
) -> A2AMessage:
    """
    Create notification message (fire-and-forget).

    Args:
        from_agent: Sender agent ID
        to_agent: Recipient agent ID
        action: Action type
        content: Notification content

    Returns:
        Notification message
    """
    return A2AMessage(
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=MessageType.NOTIFICATION,
        action=action,
        content=content,
    )

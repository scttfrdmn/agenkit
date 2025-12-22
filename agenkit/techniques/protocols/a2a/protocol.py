"""
A2A Protocol Core.

Core protocol definitions and utilities for Agent-to-Agent communication.
"""

from enum import Enum
from typing import Any


class A2AVersion(Enum):
    """A2A protocol versions."""
    V1_0 = "1.0"
    V1_1 = "1.1"


class A2AAction(Enum):
    """Standard A2A actions."""
    # Core actions
    PROCESS = "process"  # Process message
    QUERY = "query"  # Query for information
    COMMAND = "command"  # Execute command

    # Coordination actions
    DELEGATE = "delegate"  # Delegate task
    COLLABORATE = "collaborate"  # Collaborative work
    NEGOTIATE = "negotiate"  # Negotiate parameters

    # Status actions
    PING = "ping"  # Health check
    STATUS = "status"  # Get status
    CAPABILITIES = "capabilities"  # Get capabilities

    # Lifecycle actions
    INITIALIZE = "initialize"  # Initialize session
    TERMINATE = "terminate"  # Terminate session


class A2ACapability(Enum):
    """Common agent capabilities."""
    # Processing
    TEXT_ANALYSIS = "text-analysis"
    SENTIMENT_ANALYSIS = "sentiment"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"

    # Reasoning
    QUESTION_ANSWERING = "question-answering"
    REASONING = "reasoning"
    PLANNING = "planning"

    # Generation
    TEXT_GENERATION = "text-generation"
    CODE_GENERATION = "code-generation"
    IMAGE_GENERATION = "image-generation"

    # Search and retrieval
    SEARCH = "search"
    RETRIEVAL = "retrieval"
    RECOMMENDATION = "recommendation"

    # Tools
    CALCULATION = "calculation"
    DATA_PROCESSING = "data-processing"
    API_INTEGRATION = "api-integration"


class ErrorCode(Enum):
    """A2A error codes."""
    # Client errors (4xx)
    BAD_REQUEST = "400"
    UNAUTHORIZED = "401"
    FORBIDDEN = "403"
    NOT_FOUND = "404"
    TIMEOUT = "408"
    TOO_MANY_REQUESTS = "429"

    # Server errors (5xx)
    INTERNAL_ERROR = "500"
    NOT_IMPLEMENTED = "501"
    SERVICE_UNAVAILABLE = "503"

    # Protocol errors (6xx)
    PROTOCOL_ERROR = "600"
    VERSION_MISMATCH = "601"
    INVALID_MESSAGE = "602"
    CAPABILITY_NOT_SUPPORTED = "603"


# Protocol constants
PROTOCOL_VERSION = A2AVersion.V1_0.value
DEFAULT_TIMEOUT_MS = 30000  # 30 seconds
DEFAULT_PORT_HTTP = 8080
DEFAULT_PORT_GRPC = 50051
DEFAULT_PORT_WEBSOCKET = 8765

# Message size limits
MAX_MESSAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
MAX_CONTENT_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

# Discovery
DISCOVERY_REFRESH_INTERVAL_SEC = 60  # 1 minute
AGENT_HEARTBEAT_INTERVAL_SEC = 30  # 30 seconds
AGENT_TIMEOUT_SEC = 90  # 1.5 minutes


def validate_agent_id(agent_id: str) -> bool:
    """
    Validate agent ID format.

    Args:
        agent_id: Agent identifier

    Returns:
        True if valid
    """
    if not agent_id or not isinstance(agent_id, str):
        return False

    # Agent ID should be alphanumeric with hyphens/underscores
    import re
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', agent_id))


def validate_capability(capability: str) -> bool:
    """
    Validate capability format.

    Args:
        capability: Capability string

    Returns:
        True if valid
    """
    if not capability or not isinstance(capability, str):
        return False

    # Capability should be lowercase alphanumeric with hyphens
    import re
    return bool(re.match(r'^[a-z0-9-]+$', capability))


def get_error_message(error_code: ErrorCode) -> str:
    """
    Get human-readable error message for error code.

    Args:
        error_code: Error code

    Returns:
        Error message
    """
    messages = {
        ErrorCode.BAD_REQUEST: "Invalid request format or parameters",
        ErrorCode.UNAUTHORIZED: "Authentication required",
        ErrorCode.FORBIDDEN: "Access denied",
        ErrorCode.NOT_FOUND: "Agent or resource not found",
        ErrorCode.TIMEOUT: "Request timeout",
        ErrorCode.TOO_MANY_REQUESTS: "Rate limit exceeded",
        ErrorCode.INTERNAL_ERROR: "Internal server error",
        ErrorCode.NOT_IMPLEMENTED: "Action not implemented",
        ErrorCode.SERVICE_UNAVAILABLE: "Service temporarily unavailable",
        ErrorCode.PROTOCOL_ERROR: "Protocol error",
        ErrorCode.VERSION_MISMATCH: "Protocol version mismatch",
        ErrorCode.INVALID_MESSAGE: "Invalid message format",
        ErrorCode.CAPABILITY_NOT_SUPPORTED: "Capability not supported"
    }
    return messages.get(error_code, "Unknown error")


class A2AError(Exception):
    """Base exception for A2A protocol errors."""

    def __init__(
        self,
        error_code: ErrorCode,
        message: str | None = None,
        details: dict[str, Any] | None = None
    ):
        """
        Initialize exception.

        Args:
            error_code: Error code
            message: Optional error message
            details: Optional error details
        """
        self.error_code = error_code
        self.message = message or get_error_message(error_code)
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "details": self.details
        }


class TimeoutError(A2AError):
    """Request timeout error."""

    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.TIMEOUT, message, details)


class AgentNotFoundError(A2AError):
    """Agent not found error."""

    def __init__(self, agent_id: str):
        super().__init__(
            ErrorCode.NOT_FOUND,
            f"Agent not found: {agent_id}",
            {"agent_id": agent_id}
        )


class CapabilityNotSupportedError(A2AError):
    """Capability not supported error."""

    def __init__(self, capability: str):
        super().__init__(
            ErrorCode.CAPABILITY_NOT_SUPPORTED,
            f"Capability not supported: {capability}",
            {"capability": capability}
        )


class ProtocolError(A2AError):
    """Protocol error."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.PROTOCOL_ERROR, message, details)


class RateLimitError(A2AError):
    """Rate limit exceeded error."""

    def __init__(self, retry_after_ms: int | None = None):
        details = {}
        if retry_after_ms:
            details["retry_after_ms"] = retry_after_ms
        super().__init__(ErrorCode.TOO_MANY_REQUESTS, None, details)


def create_capabilities_response(capabilities: list) -> dict[str, Any]:
    """
    Create standard capabilities response.

    Args:
        capabilities: List of capability strings

    Returns:
        Capabilities response
    """
    return {
        "protocol_version": PROTOCOL_VERSION,
        "capabilities": capabilities,
        "timestamp": None  # Will be set by message
    }


def create_status_response(
    status: str,
    agent_id: str,
    load: float | None = None,
    uptime_sec: int | None = None
) -> dict[str, Any]:
    """
    Create standard status response.

    Args:
        status: Agent status ("online", "busy", "offline")
        agent_id: Agent identifier
        load: Optional load percentage (0.0-1.0)
        uptime_sec: Optional uptime in seconds

    Returns:
        Status response
    """
    response = {
        "status": status,
        "agent_id": agent_id
    }

    if load is not None:
        response["load"] = load

    if uptime_sec is not None:
        response["uptime_sec"] = uptime_sec

    return response


def create_ping_response(agent_id: str, latency_ms: float | None = None) -> dict[str, Any]:
    """
    Create standard ping response.

    Args:
        agent_id: Agent identifier
        latency_ms: Optional round-trip latency

    Returns:
        Ping response
    """
    response = {
        "agent_id": agent_id,
        "timestamp": None  # Will be set by message
    }

    if latency_ms is not None:
        response["latency_ms"] = latency_ms

    return response

"""Error types for Python protocol adapter."""

from enum import Enum
from typing import Any


class ProtocolErrorCode(str, Enum):
    """Standard error codes for protocol-level errors."""

    # Connection errors
    CONNECTION_FAILED = "CONNECTION_FAILED"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    CONNECTION_CLOSED = "CONNECTION_CLOSED"

    # Protocol errors
    INVALID_MESSAGE = "INVALID_MESSAGE"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    MALFORMED_PAYLOAD = "MALFORMED_PAYLOAD"

    # Agent errors
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_UNAVAILABLE = "AGENT_UNAVAILABLE"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"

    # Tool errors
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"

    # Registry errors
    REGISTRATION_FAILED = "REGISTRATION_FAILED"
    DUPLICATE_AGENT = "DUPLICATE_AGENT"


class ProtocolError(Exception):
    """Base exception for protocol adapter errors."""

    def __init__(
        self, code: ProtocolErrorCode, message: str, details: dict[str, Any] | None = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"{code}: {message}")


class ConnectionError(ProtocolError):
    """Connection-related errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ProtocolErrorCode.CONNECTION_FAILED, message, details)


class ConnectionTimeoutError(ProtocolError):
    """Connection timeout errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ProtocolErrorCode.CONNECTION_TIMEOUT, message, details)


class ConnectionClosedError(ProtocolError):
    """Connection closed errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ProtocolErrorCode.CONNECTION_CLOSED, message, details)


class InvalidMessageError(ProtocolError):
    """Invalid message format errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ProtocolErrorCode.INVALID_MESSAGE, message, details)


class UnsupportedVersionError(ProtocolError):
    """Unsupported protocol version errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ProtocolErrorCode.UNSUPPORTED_VERSION, message, details)


class MalformedPayloadError(ProtocolError):
    """Malformed payload errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ProtocolErrorCode.MALFORMED_PAYLOAD, message, details)


class AgentNotFoundError(ProtocolError):
    """Agent not found in registry errors."""

    def __init__(self, agent_name: str, details: dict[str, Any] | None = None):
        message = f"Agent '{agent_name}' not found in registry"
        super().__init__(ProtocolErrorCode.AGENT_NOT_FOUND, message, details)


class AgentUnavailableError(ProtocolError):
    """Agent unavailable errors."""

    def __init__(self, agent_name: str, details: dict[str, Any] | None = None):
        message = f"Agent '{agent_name}' is unavailable"
        super().__init__(ProtocolErrorCode.AGENT_UNAVAILABLE, message, details)


class AgentTimeoutError(ProtocolError):
    """Agent timeout errors."""

    def __init__(self, agent_name: str, timeout: float, details: dict[str, Any] | None = None):
        message = f"Agent '{agent_name}' timed out after {timeout}s"
        super().__init__(ProtocolErrorCode.AGENT_TIMEOUT, message, details)


class ToolNotFoundError(ProtocolError):
    """Tool not found errors."""

    def __init__(self, tool_name: str, details: dict[str, Any] | None = None):
        message = f"Tool '{tool_name}' not found"
        super().__init__(ProtocolErrorCode.TOOL_NOT_FOUND, message, details)


class ToolExecutionFailedError(ProtocolError):
    """Tool execution failed errors."""

    def __init__(self, tool_name: str, reason: str, details: dict[str, Any] | None = None):
        message = f"Tool '{tool_name}' execution failed: {reason}"
        super().__init__(ProtocolErrorCode.TOOL_EXECUTION_FAILED, message, details)


class RegistrationFailedError(ProtocolError):
    """Registration failed errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ProtocolErrorCode.REGISTRATION_FAILED, message, details)


class DuplicateAgentError(ProtocolError):
    """Duplicate agent registration errors."""

    def __init__(self, agent_name: str, details: dict[str, Any] | None = None):
        message = f"Agent '{agent_name}' is already registered"
        super().__init__(ProtocolErrorCode.DUPLICATE_AGENT, message, details)


class RemoteExecutionError(Exception):
    """Error occurred during remote agent execution."""

    def __init__(self, agent_name: str, original_error: str, details: dict[str, Any] | None = None):
        self.agent_name = agent_name
        self.original_error = original_error
        self.details = details or {}
        super().__init__(f"Remote execution failed on agent '{agent_name}': {original_error}")

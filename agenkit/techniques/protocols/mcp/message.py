"""
MCP Message Types.

Implements MCP protocol message format for requests, responses, and notifications.

References:
    - MCP Specification: https://modelcontextprotocol.io/
"""

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .schema import MCPMethod


@dataclass
class MCPMessage:
    """
    Base MCP message.

    All MCP messages follow JSON-RPC 2.0 format with method and params.
    """
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str | None = None
    params: dict[str, Any] | None = None
    result: Any | None = None
    error: dict[str, Any] | None = None

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = {k: v for k, v in asdict(self).items() if v is not None}
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> "MCPMessage":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCPMessage":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class MCPRequest(MCPMessage):
    """
    MCP request message.

    Represents a request to a server with method and parameters.
    """
    method: str = ""
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate request has method."""
        if not self.method:
            raise ValueError("Request must have a method")


@dataclass
class MCPResponse(MCPMessage):
    """
    MCP response message.

    Represents a response from server with result or error.
    """
    id: str | int = ""

    def __post_init__(self):
        """Validate response has id."""
        if not self.id:
            raise ValueError("Response must have an id")

    @property
    def is_error(self) -> bool:
        """Check if response is an error."""
        return self.error is not None

    @property
    def is_success(self) -> bool:
        """Check if response is successful."""
        return self.result is not None and self.error is None


@dataclass
class MCPNotification(MCPMessage):
    """
    MCP notification message.

    One-way message that doesn't expect a response.
    """
    method: str = ""
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate notification has method and no id."""
        if not self.method:
            raise ValueError("Notification must have a method")
        if self.id is not None:
            raise ValueError("Notification must not have an id")


def create_request(
    method: str | MCPMethod,
    params: dict[str, Any] | None = None,
    request_id: str | int | None = None
) -> MCPRequest:
    """
    Create an MCP request.

    Args:
        method: Method name or MCPMethod enum
        params: Request parameters
        request_id: Optional request ID

    Returns:
        MCPRequest instance

    Example:
        >>> request = create_request(
        ...     method=MCPMethod.RESOURCES_LIST,
        ...     request_id="req-1"
        ... )
    """
    if isinstance(method, MCPMethod):
        method = method.value

    return MCPRequest(
        id=request_id,
        method=method,
        params=params or {}
    )


def create_response(
    request_id: str | int,
    result: Any = None,
    error: dict[str, Any] | None = None
) -> MCPResponse:
    """
    Create an MCP response.

    Args:
        request_id: ID of the request being responded to
        result: Response result (if successful)
        error: Error details (if failed)

    Returns:
        MCPResponse instance

    Example:
        >>> response = create_response(
        ...     request_id="req-1",
        ...     result={"data": "..."}
        ... )
    """
    return MCPResponse(
        id=request_id,
        result=result,
        error=error
    )


def create_error_response(
    request_id: str | int,
    code: int,
    message: str,
    data: Any | None = None
) -> MCPResponse:
    """
    Create an error response.

    Args:
        request_id: ID of the request that failed
        code: Error code
        message: Error message
        data: Additional error data

    Returns:
        MCPResponse with error

    Example:
        >>> response = create_error_response(
        ...     request_id="req-1",
        ...     code=-32600,
        ...     message="Invalid request"
        ... )
    """
    error = {
        "code": code,
        "message": message
    }
    if data is not None:
        error["data"] = data

    return MCPResponse(
        id=request_id,
        error=error
    )


def create_notification(
    method: str | MCPMethod,
    params: dict[str, Any] | None = None
) -> MCPNotification:
    """
    Create an MCP notification.

    Args:
        method: Method name or MCPMethod enum
        params: Notification parameters

    Returns:
        MCPNotification instance

    Example:
        >>> notification = create_notification(
        ...     method="progress",
        ...     params={"progress": 50}
        ... )
    """
    if isinstance(method, MCPMethod):
        method = method.value

    return MCPNotification(
        method=method,
        params=params or {}
    )


# Standard error codes (JSON-RPC 2.0)
ERROR_PARSE_ERROR = -32700
ERROR_INVALID_REQUEST = -32600
ERROR_METHOD_NOT_FOUND = -32601
ERROR_INVALID_PARAMS = -32602
ERROR_INTERNAL_ERROR = -32603
ERROR_SERVER_ERROR = -32000  # Server-defined errors start here

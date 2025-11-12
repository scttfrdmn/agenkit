"""Python protocol adapter for agenkit.

This module provides cross-process and cross-language communication for agenkit agents.
"""

from .errors import (
    AgentNotFoundError,
    AgentTimeoutError,
    AgentUnavailableError,
    ConnectionClosedError,
    ConnectionError,
    ConnectionTimeoutError,
    DuplicateAgentError,
    InvalidMessageError,
    MalformedPayloadError,
    ProtocolError,
    ProtocolErrorCode,
    RegistrationFailedError,
    RemoteExecutionError,
    ToolExecutionFailedError,
    ToolNotFoundError,
    UnsupportedVersionError,
)
from .local_agent import LocalAgent
from .registry import AgentRegistration, AgentRegistry, heartbeat_loop
from .remote_agent import RemoteAgent
from .grpc_transport import GRPCTransport
from .grpc_server import GRPCServer
from .transport import (
    InMemoryTransport,
    TCPTransport,
    Transport,
    UnixSocketTransport,
    create_memory_transport_pair,
)
from .websocket_transport import WebSocketTransport

__all__ = [
    # Core classes
    "LocalAgent",
    "RemoteAgent",
    # Registry
    "AgentRegistry",
    "AgentRegistration",
    "heartbeat_loop",
    # Transports
    "Transport",
    "UnixSocketTransport",
    "TCPTransport",
    "GRPCTransport",
    "GRPCServer",
    "WebSocketTransport",
    "InMemoryTransport",
    "create_memory_transport_pair",
    # Errors
    "ProtocolError",
    "ProtocolErrorCode",
    "ConnectionError",
    "ConnectionTimeoutError",
    "ConnectionClosedError",
    "InvalidMessageError",
    "UnsupportedVersionError",
    "MalformedPayloadError",
    "AgentNotFoundError",
    "AgentUnavailableError",
    "AgentTimeoutError",
    "ToolNotFoundError",
    "ToolExecutionFailedError",
    "RegistrationFailedError",
    "DuplicateAgentError",
    "RemoteExecutionError",
]

__version__ = "0.1.0"

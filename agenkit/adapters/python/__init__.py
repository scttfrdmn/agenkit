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
from .grpc_server import GRPCServer
from .grpc_transport import GRPCTransport
from .local_agent import LocalAgent
from .registry import AgentRegistration, AgentRegistry, heartbeat_loop
from .remote_agent import RemoteAgent
from .transport import (
    InMemoryTransport,
    TCPTransport,
    Transport,
    UnixSocketTransport,
    create_memory_transport_pair,
)
from .websocket_transport import WebSocketTransport

__all__ = [
    # Errors
    "AgentNotFoundError",
    # Registry
    "AgentRegistration",
    "AgentRegistry",
    "AgentTimeoutError",
    "AgentUnavailableError",
    "ConnectionClosedError",
    "ConnectionError",
    "ConnectionTimeoutError",
    "DuplicateAgentError",
    # Transports
    "GRPCServer",
    "GRPCTransport",
    "InMemoryTransport",
    "InvalidMessageError",
    # Core classes
    "LocalAgent",
    "MalformedPayloadError",
    "ProtocolError",
    "ProtocolErrorCode",
    "RegistrationFailedError",
    "RemoteAgent",
    "RemoteExecutionError",
    "TCPTransport",
    "ToolExecutionFailedError",
    "ToolNotFoundError",
    "Transport",
    "UnixSocketTransport",
    "UnsupportedVersionError",
    "WebSocketTransport",
    "create_memory_transport_pair",
    "heartbeat_loop",
]

__version__ = "0.1.0"

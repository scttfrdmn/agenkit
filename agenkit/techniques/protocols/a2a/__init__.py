"""
Agent-to-Agent (A2A) Protocol.

Cross-platform protocol for agent communication and coordination.

This module provides:
- A2A message format and protocol
- Transport layers (HTTP, WebSocket, gRPC)
- Agent communication primitives
- Platform integration adapters

Note: This is Part 1 of the A2A implementation (Foundation).
Part 2 will include: Agent, Server, Discovery, and Platform Adapters.

Example (Foundation):
    >>> from agenkit.techniques.protocols.a2a import A2AMessage, create_request
    >>>
    >>> # Create request message
    >>> message = create_request(
    ...     from_agent="analyzer-001",
    ...     to_agent="summarizer-001",
    ...     action="summarize",
    ...     content={"text": "Document to summarize..."}
    ... )
    >>>
    >>> # Send via HTTP transport
    >>> from agenkit.techniques.protocols.a2a import HTTPTransport
    >>> transport = HTTPTransport()
    >>> response = await transport.send(message, "http://agent:8080/a2a")

References:
    - Vertex AI Agents: https://cloud.google.com/vertex-ai/docs/agents
    - AWS Bedrock Agents: https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html
"""

# Message types
from .message import (
    A2AMessage,
    AgentInfo,
    MessageType,
    MessagePriority,
    create_request,
    create_notification
)

# Protocol
from .protocol import (
    A2AVersion,
    A2AAction,
    A2ACapability,
    ErrorCode,
    A2AException,
    TimeoutError,
    AgentNotFoundError,
    CapabilityNotSupportedError,
    ProtocolError,
    RateLimitError,
    PROTOCOL_VERSION,
    validate_agent_id,
    validate_capability,
    create_capabilities_response,
    create_status_response,
    create_ping_response
)

# Transport
from .transport import (
    Transport,
    HTTPTransport,
    WebSocketTransport,
    GRPCTransport,
    create_transport
)

__all__ = [
    # Message
    "A2AMessage",
    "AgentInfo",
    "MessageType",
    "MessagePriority",
    "create_request",
    "create_notification",
    # Protocol
    "A2AVersion",
    "A2AAction",
    "A2ACapability",
    "ErrorCode",
    "A2AException",
    "TimeoutError",
    "AgentNotFoundError",
    "CapabilityNotSupportedError",
    "ProtocolError",
    "RateLimitError",
    "PROTOCOL_VERSION",
    "validate_agent_id",
    "validate_capability",
    "create_capabilities_response",
    "create_status_response",
    "create_ping_response",
    # Transport
    "Transport",
    "HTTPTransport",
    "WebSocketTransport",
    "GRPCTransport",
    "create_transport",
]

__version__ = "0.1.0"  # Part 1: Foundation

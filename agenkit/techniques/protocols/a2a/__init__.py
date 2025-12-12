"""
Agent-to-Agent (A2A) Protocol.

Cross-platform protocol for agent communication and coordination.

This module provides:
- A2A message format and protocol
- Transport layers (HTTP, WebSocket, gRPC)
- Agent communication primitives
- Discovery service integration
- Platform integration adapters (Vertex AI, Bedrock)

Example (Agent Communication):
    >>> from agenkit.techniques.protocols.a2a import A2AAgent, create_request
    >>>
    >>> # Create A2A agent
    >>> agent = A2AAgent(
    ...     agent_id="analyzer-001",
    ...     capabilities=["text-analysis", "sentiment"]
    ... )
    >>>
    >>> # Send message
    >>> message = create_request(
    ...     from_agent=agent.agent_id,
    ...     to_agent="summarizer-001",
    ...     action="summarize",
    ...     content={"text": "Document..."}
    ... )
    >>> response = await agent.send(message, "http://summarizer:8080/a2a")

Example (Expose Agenkit Agent):
    >>> from agenkit.patterns import ReActAgent
    >>> from agenkit.techniques.protocols.a2a import AgentA2AServer
    >>>
    >>> react_agent = ReActAgent(llm=my_llm, tools=[...])
    >>> server = AgentA2AServer(react_agent, agent_id="react-001")
    >>> await server.run(transport="http", port=8080)

Example (Platform Integration):
    >>> from agenkit.techniques.protocols.a2a import VertexAIAdapter
    >>>
    >>> adapter = VertexAIAdapter.from_agent(
    ...     agent=my_agent,
    ...     project_id="my-project",
    ...     location="us-central1"
    ... )
    >>> await adapter.deploy()

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

# Agent
from .agent import A2AAgent

# Server
from .server import A2AServer, AgentA2AServer

# Discovery
from .discovery import A2ADiscoveryClient, InMemoryDiscoveryService

# Platform Adapters
from .adapters import (
    VertexAIAdapter,
    create_vertex_agent,
    BedrockAdapter,
    create_bedrock_agent
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
    # Agent
    "A2AAgent",
    # Server
    "A2AServer",
    "AgentA2AServer",
    # Discovery
    "A2ADiscoveryClient",
    "InMemoryDiscoveryService",
    # Platform Adapters
    "VertexAIAdapter",
    "create_vertex_agent",
    "BedrockAdapter",
    "create_bedrock_agent",
]

__version__ = "1.0.0"  # Complete implementation

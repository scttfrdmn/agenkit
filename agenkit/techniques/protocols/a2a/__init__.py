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
# Platform Adapters
from .adapters import BedrockAdapter, VertexAIAdapter, create_bedrock_agent, create_vertex_agent

# Agent
from .agent import A2AAgent

# Discovery
from .discovery import A2ADiscoveryClient, InMemoryDiscoveryService
from .message import (
    A2AMessage,
    AgentInfo,
    MessagePriority,
    MessageType,
    create_notification,
    create_request,
)

# Protocol
from .protocol import (
    PROTOCOL_VERSION,
    A2AAction,
    A2ACapability,
    A2AException,
    A2AVersion,
    AgentNotFoundError,
    CapabilityNotSupportedError,
    ErrorCode,
    ProtocolError,
    RateLimitError,
    TimeoutError,
    create_capabilities_response,
    create_ping_response,
    create_status_response,
    validate_agent_id,
    validate_capability,
)

# Server
from .server import A2AServer, AgentA2AServer

# Transport
from .transport import GRPCTransport, HTTPTransport, Transport, WebSocketTransport, create_transport

__all__ = [
    "PROTOCOL_VERSION",
    "A2AAction",
    # Agent
    "A2AAgent",
    "A2ACapability",
    # Discovery
    "A2ADiscoveryClient",
    "A2AException",
    # Message
    "A2AMessage",
    # Server
    "A2AServer",
    # Protocol
    "A2AVersion",
    "AgentA2AServer",
    "AgentInfo",
    "AgentNotFoundError",
    "BedrockAdapter",
    "CapabilityNotSupportedError",
    "ErrorCode",
    "GRPCTransport",
    "HTTPTransport",
    "InMemoryDiscoveryService",
    "MessagePriority",
    "MessageType",
    "ProtocolError",
    "RateLimitError",
    "TimeoutError",
    # Transport
    "Transport",
    # Platform Adapters
    "VertexAIAdapter",
    "WebSocketTransport",
    "create_bedrock_agent",
    "create_capabilities_response",
    "create_notification",
    "create_ping_response",
    "create_request",
    "create_status_response",
    "create_transport",
    "create_vertex_agent",
    "validate_agent_id",
    "validate_capability",
]

__version__ = "1.0.0"  # Complete implementation

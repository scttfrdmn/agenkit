"""
Introspection capability for examining agent internal state.

This module provides introspection support - the ability for agents to examine
their own internal state, memory, and capabilities. This is distinct from the
Reflection pattern, which is about analyzing past performance.

Key distinctions:
- Introspection (this module): "What do I know?" - State examination
- Reflection (pattern): "How did I do?" - Performance analysis

References:
- Issue #301: Add Introspection Capability to Agent Interface
- ArXiv: Introspection of Thought Helps AI Agents (https://arxiv.org/abs/2507.08664)
- Biswas & Talukdar: Building Agentic AI Systems
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

__all__ = ["IntrospectionResult"]


@dataclass(frozen=True)
class IntrospectionResult:
    """
    Result of agent introspection - a snapshot of internal state.

    This provides a structured view into an agent's current state, including
    its capabilities, memory contents, and any agent-specific internal state.

    Design decisions:
    - frozen: Immutable snapshot (thread-safe, cacheable)
    - timestamp: When this snapshot was taken (UTC)
    - agent_name: Which agent was introspected
    - capabilities: What the agent can do
    - memory_state: Contents of agent's memory (if applicable)
    - internal_state: Agent-specific state information
    - metadata: Extension point for additional information

    Attributes:
        timestamp: UTC timestamp when introspection was performed
        agent_name: Name of the agent that was introspected
        capabilities: List of capability strings this agent supports
        memory_state: Dictionary of memory contents (None if no memory)
        internal_state: Dictionary of agent-specific internal state
        metadata: Additional introspection metadata

    Example:
        >>> result = agent.introspect()
        >>> print(f"Agent: {result.agent_name}")
        >>> print(f"Capabilities: {result.capabilities}")
        >>> print(f"Memory entries: {len(result.memory_state or {})}")
        >>> print(f"Internal state keys: {list(result.internal_state.keys())}")

    Usage:
        Introspection is useful for:
        - Debugging: Examine agent state during development
        - Monitoring: Track agent state in production
        - Coordination: Agents can inspect each other's capabilities
        - Testing: Verify agent state in tests
        - Explainability: Understand what an agent "knows"
    """

    timestamp: datetime
    agent_name: str
    capabilities: list[str]
    memory_state: dict[str, Any] | None
    internal_state: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate introspection result."""
        if not self.agent_name:
            raise ValueError("agent_name cannot be empty")
        if not isinstance(self.capabilities, list):
            raise TypeError("capabilities must be a list")
        if not isinstance(self.internal_state, dict):
            raise TypeError("internal_state must be a dict")
        if self.memory_state is not None and not isinstance(self.memory_state, dict):
            raise TypeError("memory_state must be a dict or None")

"""
agenkit: The foundation layer for AI agents.

Minimal, perfect primitives for agent communication.
"""

from agenkit.composition import (ConditionalAgent, FallbackAgent,
                                 ParallelAgent, SequentialAgent)
from agenkit.interfaces import (Agent, IntrospectionResult, Message, Tool,
                                ToolResult)
from agenkit.patterns import Task

__version__ = "0.10.0"

__all__ = [
    # Core interfaces
    "Agent",
    # Composition patterns
    "ConditionalAgent",
    "FallbackAgent",
    # Introspection
    "IntrospectionResult",
    "Message",
    "ParallelAgent",
    "SequentialAgent",
    # Agent patterns
    "Task",
    "Tool",
    "ToolResult",
]

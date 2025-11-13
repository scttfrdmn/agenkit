"""
agenkit: The foundation layer for AI agents.

Minimal, perfect primitives for agent communication.
"""

from agenkit.composition import (
    ConditionalAgent,
    FallbackAgent,
    ParallelAgent,
    SequentialAgent,
)
from agenkit.interfaces import Agent, Message, Tool, ToolResult
from agenkit.patterns import Task

__version__ = "0.1.0"

__all__ = [
    # Core interfaces
    "Agent",
    "Message",
    "Tool",
    "ToolResult",
    # Composition patterns
    "ConditionalAgent",
    "FallbackAgent",
    "ParallelAgent",
    "SequentialAgent",
    # Agent patterns
    "Task",
]

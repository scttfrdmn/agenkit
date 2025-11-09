"""
agenkit: The foundation layer for AI agents.

Minimal, perfect primitives for agent communication.
"""

from agenkit.interfaces import Agent, Message, Tool, ToolResult
from agenkit.patterns import ParallelPattern, RouterPattern, SequentialPattern

__version__ = "0.1.0"

__all__ = [
    # Core interfaces
    "Agent",
    "Tool",
    "Message",
    "ToolResult",
    # Patterns
    "SequentialPattern",
    "ParallelPattern",
    "RouterPattern",
]

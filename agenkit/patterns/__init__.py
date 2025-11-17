"""
Agent patterns for common use cases.

This module provides high-level patterns for working with agents, including:
- Task: One-shot agent execution with lifecycle management
- Sequential, Parallel, Router: Orchestration patterns
- ConversationalAgent: Maintains conversation history for context-aware responses
"""

from agenkit.patterns.task import Task
from agenkit.patterns.orchestration import (
    SequentialPattern,
    ParallelPattern,
    RouterPattern
)
from agenkit.patterns.conversational import (
    ConversationalAgent,
    StreamingConversationalAgent,
    LLMClient,
)

__all__ = [
    "Task",
    "SequentialPattern",
    "ParallelPattern",
    "RouterPattern",
    "ConversationalAgent",
    "StreamingConversationalAgent",
    "LLMClient",
]

"""
Agent patterns for common use cases.

This module provides high-level patterns for working with agents, including:
- Task: One-shot agent execution with lifecycle management
- Sequential, Parallel, Router: Orchestration patterns
"""

from agenkit.patterns.task import Task
from agenkit.patterns.orchestration import (
    SequentialPattern,
    ParallelPattern,
    RouterPattern
)

__all__ = [
    "Task",
    "SequentialPattern",
    "ParallelPattern",
    "RouterPattern"
]

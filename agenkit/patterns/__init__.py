"""
Agent patterns for common use cases.

This module provides high-level patterns for working with agents, including:
- Task: One-shot agent execution with lifecycle management
- Workflow: Orchestration of multiple agents/tasks (future)
"""

from agenkit.patterns.task import Task

__all__ = ["Task"]

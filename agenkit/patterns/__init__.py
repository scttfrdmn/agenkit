"""
Agent patterns for common use cases.

This module provides high-level patterns for working with agents, including:
- Task: One-shot agent execution with lifecycle management
- Sequential, Parallel, Router: Orchestration patterns
- ConversationalAgent: Maintains conversation history for context-aware responses
- ReActAgent: Reasoning and acting with tools (ReAct pattern)
- PlanningAgent: Creates and executes multi-step plans
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
from agenkit.patterns.react import (
    ReActAgent,
    Tool,
    ToolResult,
    ToolRegistry,
    ReActStep,
)
from agenkit.patterns.planning import (
    PlanningAgent,
    Plan,
    PlanStep,
    StepStatus,
    StepExecutor,
)

__all__ = [
    "Task",
    "SequentialPattern",
    "ParallelPattern",
    "RouterPattern",
    "ConversationalAgent",
    "StreamingConversationalAgent",
    "LLMClient",
    "ReActAgent",
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "ReActStep",
    "PlanningAgent",
    "Plan",
    "PlanStep",
    "StepStatus",
    "StepExecutor",
]

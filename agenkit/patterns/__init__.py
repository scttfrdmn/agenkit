"""
Agent patterns for common use cases.

This module provides high-level patterns for working with agents, including:
- Task: One-shot agent execution with lifecycle management
- Sequential, Parallel, Router: Orchestration patterns
- ConversationalAgent: Maintains conversation history for context-aware responses
- ReActAgent: Reasoning and acting with tools (ReAct pattern)
- PlanningAgent: Creates and executes multi-step plans
"""

from agenkit.patterns.autonomous import (
    AutonomousAgent,
    Goal,
)
from agenkit.patterns.conversational import (
    ConversationalAgent,
    LLMClient,
    StreamingConversationalAgent,
)
from agenkit.patterns.multiagent import (
    AgentTask,
    ConsensusAgent,
    MultiAgentOrchestrator,
)
from agenkit.patterns.orchestration import ParallelPattern, RouterPattern, SequentialPattern
from agenkit.patterns.planning import (
    Plan,
    PlanningAgent,
    PlanStep,
    StepExecutor,
    StepStatus,
)
from agenkit.patterns.react import (
    ReActAgent,
    ReActStep,
    Tool,
    ToolRegistry,
    ToolResult,
)
from agenkit.patterns.task import Task

__all__ = [
    "AgentTask",
    "AutonomousAgent",
    "ConsensusAgent",
    "ConversationalAgent",
    "Goal",
    "LLMClient",
    "MultiAgentOrchestrator",
    "ParallelPattern",
    "Plan",
    "PlanStep",
    "PlanningAgent",
    "ReActAgent",
    "ReActStep",
    "RouterPattern",
    "SequentialPattern",
    "StepExecutor",
    "StepStatus",
    "StreamingConversationalAgent",
    "Task",
    "Tool",
    "ToolRegistry",
    "ToolResult",
]

"""
Agent patterns for common use cases.

This module provides high-level patterns for working with agents, including:

Core Patterns:
- Task: One-shot agent execution with lifecycle management
- Sequential, Parallel, Router: Orchestration patterns
- ConversationalAgent: Maintains conversation history for context-aware responses
- ReActAgent: Reasoning and acting with tools (ReAct pattern)
- PlanningAgent: Creates and executes multi-step plans
- ReflectionAgent: Self-critique and iterative refinement (NEW in v0.12.0)
- AgentTool: Agents-as-Tools for hierarchical delegation (NEW in v0.12.0)
- MemoryHierarchy: Multi-tier memory system (NEW in v0.12.0)
- ReasoningWithToolsAgent: Interleaved reasoning and tool usage (NEW in v0.13.0)
"""

from agenkit.patterns.agents_as_tools import (
    AgentTool,
    agent_as_tool,
)
from agenkit.patterns.autonomous import (
    AutonomousAgent,
    Goal,
)
from agenkit.patterns.conversational import (
    ConversationalAgent,
    LLMClient,
    StreamingConversationalAgent,
)
from agenkit.patterns.memory import (
    LongTermMemory,
    MemoryEntry,
    MemoryHierarchy,
    MemoryStore,
    ShortTermMemory,
    WorkingMemory,
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
from agenkit.patterns.reasoning_with_tools import (
    ReasoningStep,
    ReasoningStepType,
    ReasoningTrace,
    ReasoningWithToolsAgent,
)
from agenkit.patterns.reflection import (
    CritiqueFormat,
    ReflectionAgent,
    ReflectionStep,
    StopReason,
)
from agenkit.patterns.task import Task

__all__ = [
    # Agents-as-Tools Pattern (NEW)
    "AgentTool",
    "agent_as_tool",
    # Core Patterns
    "AgentTask",
    "AutonomousAgent",
    "ConsensusAgent",
    "ConversationalAgent",
    # Critique/Reflection (NEW)
    "CritiqueFormat",
    "Goal",
    "LLMClient",
    # Memory Hierarchy Pattern (NEW)
    "LongTermMemory",
    "MemoryEntry",
    "MemoryHierarchy",
    "MemoryStore",
    # Orchestration
    "MultiAgentOrchestrator",
    "ParallelPattern",
    # Planning
    "Plan",
    "PlanStep",
    "PlanningAgent",
    # ReAct
    "ReActAgent",
    "ReActStep",
    # Reasoning with Tools (NEW in v0.13.0)
    "ReasoningStep",
    "ReasoningStepType",
    "ReasoningTrace",
    "ReasoningWithToolsAgent",
    # Reflection Pattern (NEW)
    "ReflectionAgent",
    "ReflectionStep",
    # Orchestration (continued)
    "RouterPattern",
    "SequentialPattern",
    # Memory (continued)
    "ShortTermMemory",
    # Planning (continued)
    "StepExecutor",
    "StepStatus",
    # Reflection (continued)
    "StopReason",
    # Conversational
    "StreamingConversationalAgent",
    # Task
    "Task",
    # Tools
    "Tool",
    "ToolRegistry",
    "ToolResult",
    # Memory (continued)
    "WorkingMemory",
]

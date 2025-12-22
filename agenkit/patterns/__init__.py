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

Pattern Library (NEW in v0.32.0):
- SequentialAgent: Pipeline-style agent composition
- ParallelAgent: Concurrent execution with result aggregation
- SupervisorAgent: Hierarchical coordination with task decomposition
- RouterAgent: Conditional agent selection based on classification
- CollaborativeAgent: Peer-to-peer collaboration with iterative refinement
- HumanInLoopAgent: Human approval gates for high-stakes decisions
- FallbackAgent: Sequential retry across multiple agents
"""

from agenkit.patterns.agents_as_tools import AgentTool, agent_as_tool
from agenkit.patterns.autonomous import AutonomousAgent, AutonomousConfig, Goal
from agenkit.patterns.collaborative import (CollaborativeAgent,
                                            CollaborativeConfig, ConsensusFunc,
                                            MergeFunc, default_consensus_funcs,
                                            default_merge_funcs)
from agenkit.patterns.conversational import (ConversationalAgent, LLMClient,
                                             StreamingConversationalAgent)
from agenkit.patterns.fallback import (FallbackAgent, RecoveryAgent,
                                       RecoveryFunc, default_recovery,
                                       with_recovery)
from agenkit.patterns.human_in_loop import (ApprovalFunc, ApprovalRequest,
                                            ApprovalResponse, HumanInLoopAgent,
                                            HumanInLoopConfig,
                                            confidence_based_approval_func,
                                            simple_approval_func)
from agenkit.patterns.memory import (LongTermMemory, MemoryEntry,
                                     MemoryHierarchy, MemoryStore,
                                     ShortTermMemory, WorkingMemory)
from agenkit.patterns.multiagent import (AgentTask, ConsensusAgent,
                                         ConsensusConfig, MultiAgentConfig,
                                         MultiAgentOrchestrator)
from agenkit.patterns.orchestration import (OrchestrationAgent,
                                            OrchestrationConfig,
                                            ParallelPattern, RouterPattern,
                                            SequentialPattern)
from agenkit.patterns.parallel import (AggregatorFunc, ParallelAgent,
                                       default_aggregators)
from agenkit.patterns.planning import (Plan, PlanningAgent, PlanningConfig,
                                       PlanStep, StepExecutor, StepStatus)
from agenkit.patterns.react import (ReActAgent, ReActConfig, ReActStep, Tool,
                                    ToolResult)
from agenkit.patterns.reasoning_with_tools import (ReasoningStep,
                                                   ReasoningStepType,
                                                   ReasoningTrace,
                                                   ReasoningWithToolsAgent)
from agenkit.patterns.reflection import (CritiqueFormat, ReflectionAgent,
                                         ReflectionConfig, ReflectionStep,
                                         StopReason)
from agenkit.patterns.router import (ClassifierAgent, LLMClassifier,
                                     RouterAgent, RouterConfig,
                                     SimpleClassifier)
from agenkit.patterns.sequential import SequentialAgent
from agenkit.patterns.supervisor import (PlannerAgent, SimplePlanner, Subtask,
                                         SupervisorAgent, SupervisorConfig)
from agenkit.patterns.task import Task

__all__ = [
    # Core Patterns
    "AgentTask",
    # Agents-as-Tools Pattern (NEW)
    "AgentTool",
    # Pattern Library - Collaborative (NEW in v0.32.0)
    "AggregatorFunc",
    # Pattern Library - Human Approval (NEW in v0.32.0)
    "ApprovalFunc",
    "ApprovalRequest",
    "ApprovalResponse",
    "AutonomousAgent",
    "AutonomousConfig",
    # Pattern Library - Router (NEW in v0.32.0)
    "ClassifierAgent",
    # Pattern Library - Collaborative (NEW in v0.32.0)
    "CollaborativeAgent",
    "CollaborativeConfig",
    "ConsensusAgent",
    "ConsensusConfig",
    # Pattern Library - Collaborative (NEW in v0.32.0)
    "ConsensusFunc",
    "ConversationalAgent",
    # Critique/Reflection (NEW)
    "CritiqueFormat",
    # Pattern Library - Fallback (NEW in v0.32.0)
    "FallbackAgent",
    "Goal",
    # Pattern Library - Human Approval (NEW in v0.32.0)
    "HumanInLoopAgent",
    "HumanInLoopConfig",
    "LLMClassifier",
    "LLMClient",
    # Memory Hierarchy Pattern (NEW)
    "LongTermMemory",
    "MemoryEntry",
    "MemoryHierarchy",
    "MemoryStore",
    # Pattern Library - Collaborative (NEW in v0.32.0)
    "MergeFunc",
    # Orchestration
    "MultiAgentConfig",
    "MultiAgentOrchestrator",
    "OrchestrationAgent",
    "OrchestrationConfig",
    # Pattern Library - Parallel (NEW in v0.32.0)
    "ParallelAgent",
    "ParallelPattern",
    # Planning
    "Plan",
    "PlanStep",
    # Pattern Library - Supervisor (NEW in v0.32.0)
    "PlannerAgent",
    "PlanningAgent",
    "PlanningConfig",
    # ReAct
    "ReActAgent",
    "ReActConfig",
    "ReActStep",
    # Reasoning with Tools (NEW in v0.13.0)
    "ReasoningStep",
    "ReasoningStepType",
    "ReasoningTrace",
    "ReasoningWithToolsAgent",
    # Pattern Library - Fallback (NEW in v0.32.0)
    "RecoveryAgent",
    "RecoveryFunc",
    # Reflection Pattern (NEW)
    "ReflectionAgent",
    "ReflectionConfig",
    "ReflectionStep",
    # Pattern Library - Router (NEW in v0.32.0)
    "RouterAgent",
    "RouterConfig",
    # Orchestration (continued)
    "RouterPattern",
    # Pattern Library - Sequential (NEW in v0.32.0)
    "SequentialAgent",
    "SequentialPattern",
    # Memory (continued)
    "ShortTermMemory",
    # Pattern Library - Router (NEW in v0.32.0)
    "SimpleClassifier",
    # Pattern Library - Supervisor (NEW in v0.32.0)
    "SimplePlanner",
    # Planning (continued)
    "StepExecutor",
    "StepStatus",
    # Reflection (continued)
    "StopReason",
    # Conversational
    "StreamingConversationalAgent",
    # Pattern Library - Supervisor (NEW in v0.32.0)
    "Subtask",
    # Pattern Library - Supervisor (NEW in v0.32.0)
    "SupervisorAgent",
    "SupervisorConfig",
    # Task
    "Task",
    # Tools
    "Tool",
    "ToolResult",
    # Memory (continued)
    "WorkingMemory",
    "agent_as_tool",
    "confidence_based_approval_func",
    "default_aggregators",
    "default_consensus_funcs",
    "default_merge_funcs",
    "default_recovery",
    # Pattern Library - Human Approval (NEW in v0.32.0)
    "simple_approval_func",
    # Pattern Library - Fallback (NEW in v0.32.0)
    "with_recovery",
]

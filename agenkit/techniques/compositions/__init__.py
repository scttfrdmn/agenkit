"""
Composition Techniques for AI Agents.

This module provides simple compositions that combine existing patterns and
primitives. Compositions are intentionally simple (10-80 LOC) to demonstrate
that many "features" marketed by frameworks are just straightforward wiring.

Key Distinction:
    - **Patterns** (agenkit/patterns/): Non-trivial, reusable coordination solutions
    - **Compositions** (agenkit/techniques/compositions/): Simple wiring of primitives

Both are valuable! Compositions are perfect for prototyping and learning.
Patterns are for production systems requiring robustness and configuration.

Available Compositions:
    - SimpleApprovalTool: Basic human approval via input()
    - simple_approval: Convenience function for sync approval
    - SimpleRAG: Basic retrieval-augmented generation
    - CitedRAG: RAG with citation tracking
    - Document: Document with metadata for citations
    - ContextOptimizer: Token limit management via summarization
    - TaskQueue: Priority queue for task management
    - PriorityTaskExecutor: Task execution with prioritization
    - GoalMonitor: Monitor progress toward goal
    - ExplorationStrategy: UCB-based exploration-exploitation
    - LearningFromFeedback: Experience-based learning with memory
    - ActorCriticVariation: Demonstrates equivalence to Reflection pattern

References:
    See README.md in this directory for detailed comparisons and philosophy.

    Book Sources:
        - Gulli (2025): "Agentic Design Patterns"
        - Alto (2025): "AI Agents in Practice"
        - Rothman (2025): "Context Engineering for Multi-Agent Systems"
        - Albada (2025): "Building Applications with AI Agents"
"""

from .actor_critic_variation import ActorCriticVariation, why_use_reflection_instead
from .context_optimization import ContextOptimizer
from .exploration import ActionStats, ExplorationStrategy
from .goal_monitoring import GoalMonitor
from .learning_feedback import Interaction, LearningFromFeedback
from .prioritization import PrioritizedTask, PriorityTaskExecutor, TaskQueue
from .rag import SimpleRAG
from .rag_with_citations import CitedRAG, Document
from .simple_human_approval import SimpleApprovalTool, simple_approval

__all__ = [
    "ActionStats",
    # Actor-Critic Variation
    "ActorCriticVariation",
    # RAG with Citations
    "CitedRAG",
    # Context Optimization
    "ContextOptimizer",
    "Document",
    # Exploration
    "ExplorationStrategy",
    # Goal Monitoring
    "GoalMonitor",
    "Interaction",
    # Learning from Feedback
    "LearningFromFeedback",
    "PrioritizedTask",
    "PriorityTaskExecutor",
    # Simple Human Approval
    "SimpleApprovalTool",
    # RAG
    "SimpleRAG",
    # Prioritization
    "TaskQueue",
    "simple_approval",
    "why_use_reflection_instead",
]

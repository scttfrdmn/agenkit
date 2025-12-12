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

from .simple_human_approval import SimpleApprovalTool, simple_approval
from .rag import SimpleRAG
from .rag_with_citations import CitedRAG, Document
from .context_optimization import ContextOptimizer
from .prioritization import TaskQueue, PriorityTaskExecutor, PrioritizedTask
from .goal_monitoring import GoalMonitor
from .exploration import ExplorationStrategy, ActionStats
from .learning_feedback import LearningFromFeedback, Interaction
from .actor_critic_variation import ActorCriticVariation, why_use_reflection_instead

__all__ = [
    # Simple Human Approval
    "SimpleApprovalTool",
    "simple_approval",
    # RAG
    "SimpleRAG",
    # RAG with Citations
    "CitedRAG",
    "Document",
    # Context Optimization
    "ContextOptimizer",
    # Prioritization
    "TaskQueue",
    "PriorityTaskExecutor",
    "PrioritizedTask",
    # Goal Monitoring
    "GoalMonitor",
    # Exploration
    "ExplorationStrategy",
    "ActionStats",
    # Learning from Feedback
    "LearningFromFeedback",
    "Interaction",
    # Actor-Critic Variation
    "ActorCriticVariation",
    "why_use_reflection_instead",
]

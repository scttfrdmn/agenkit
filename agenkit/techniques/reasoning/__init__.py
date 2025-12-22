"""
Reasoning techniques for AI agents.

This module provides advanced reasoning techniques that enhance agent
capabilities through structured prompting and multi-step reasoning strategies.

Available Techniques:
    - ChainOfThought: Step-by-step reasoning with explicit thought process
    - TreeOfThought: Multi-path exploration with tree search and backtracking
    - SelfConsistency: Multiple sampling with consensus voting
    - LeastToMost: Problem decomposition and sequential solving
    - PlanAndSolve: Strategic planning before execution
    - GraphOfThought: Graph-based reasoning with multiple interconnected paths

References:
    See docs/techniques/REASONING_TECHNIQUES.md for detailed comparisons
    and usage guidelines.
"""

from .chain_of_thought import ChainOfThought
from .graph_of_thought import GraphOfThought
from .least_to_most import LeastToMost, Subproblem
from .plan_and_solve import Plan, PlanAndSolve, PlanStep
from .reasoning_graph import EdgeType, LogicalEdge, NodeType, ReasoningGraph, ThoughtNode
from .reasoning_tree import NodeState, ReasoningNode, ReasoningTree
from .self_consistency import SelfConsistency
from .tree_of_thought import TreeOfThought

__all__ = [
    "ChainOfThought",
    "EdgeType",
    "GraphOfThought",
    "LeastToMost",
    "LogicalEdge",
    "NodeState",
    "NodeType",
    "Plan",
    "PlanAndSolve",
    "PlanStep",
    "ReasoningGraph",
    "ReasoningNode",
    "ReasoningTree",
    "SelfConsistency",
    "Subproblem",
    "ThoughtNode",
    "TreeOfThought",
]

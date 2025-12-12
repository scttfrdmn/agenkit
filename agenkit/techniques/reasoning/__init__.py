"""
Reasoning techniques for AI agents.

This module provides advanced reasoning techniques that enhance agent
capabilities through structured prompting and multi-step reasoning strategies.

Available Techniques:
    - ChainOfThought: Step-by-step reasoning with explicit thought process
    - TreeOfThought: Multi-path exploration with tree search and backtracking
    - SelfConsistency: Multiple sampling with consensus voting

References:
    See docs/techniques/REASONING_TECHNIQUES.md for detailed comparisons
    and usage guidelines.
"""

from .chain_of_thought import ChainOfThought
from .tree_of_thought import TreeOfThought
from .self_consistency import SelfConsistency
from .reasoning_tree import ReasoningTree, ReasoningNode, NodeState

__all__ = [
    "ChainOfThought",
    "TreeOfThought",
    "SelfConsistency",
    "ReasoningTree",
    "ReasoningNode",
    "NodeState"
]

"""
Reasoning techniques for AI agents.

This module provides advanced reasoning techniques that enhance agent
capabilities through structured prompting and multi-step reasoning strategies.

Available Techniques:
    - ChainOfThought: Step-by-step reasoning with explicit thought process

References:
    See docs/techniques/REASONING_TECHNIQUES.md for detailed comparisons
    and usage guidelines.
"""

from .chain_of_thought import ChainOfThought

__all__ = ["ChainOfThought"]

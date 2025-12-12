"""
Advanced techniques for AI agents.

This package provides reasoning techniques, communication protocols, and
composition patterns that extend the core Agenkit patterns.

Modules:
    reasoning: Reasoning techniques (CoT, ToT, GoT, etc.)
    protocols: Communication protocols (MCP, A2A)
    compositions: Composition patterns and recipes

Example:
    from agenkit.techniques.reasoning import ChainOfThought

    cot = ChainOfThought(llm=my_llm)
    response = await cot.process(message)
"""

# Techniques will be imported from submodules
# from .reasoning import *
# from .protocols import *
# from .compositions import *

__all__ = ["reasoning", "protocols", "compositions"]

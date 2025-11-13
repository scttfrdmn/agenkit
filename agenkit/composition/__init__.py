"""Composition patterns for agents."""

from .conditional import (
    Condition,
    ConditionalAgent,
    ConditionalRoute,
    and_conditions,
    content_contains,
    metadata_equals,
    metadata_has_key,
    not_condition,
    or_conditions,
    role_equals,
)
from .fallback import FallbackAgent
from .parallel import AgentResult, ParallelAgent
from .sequential import SequentialAgent

__all__ = [
    "AgentResult",
    "Condition",
    "ConditionalAgent",
    "ConditionalRoute",
    "FallbackAgent",
    "ParallelAgent",
    "SequentialAgent",
    "and_conditions",
    "content_contains",
    "metadata_equals",
    "metadata_has_key",
    "not_condition",
    "or_conditions",
    "role_equals",
]

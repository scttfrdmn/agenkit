"""Composition patterns for agents."""

from .sequential import SequentialAgent
from .parallel import ParallelAgent, AgentResult
from .fallback import FallbackAgent
from .conditional import (
    ConditionalAgent,
    Condition,
    ConditionalRoute,
    content_contains,
    role_equals,
    metadata_has_key,
    metadata_equals,
    and_conditions,
    or_conditions,
    not_condition,
)

__all__ = [
    "SequentialAgent",
    "ParallelAgent",
    "AgentResult",
    "FallbackAgent",
    "ConditionalAgent",
    "Condition",
    "ConditionalRoute",
    "content_contains",
    "role_equals",
    "metadata_has_key",
    "metadata_equals",
    "and_conditions",
    "or_conditions",
    "not_condition",
]

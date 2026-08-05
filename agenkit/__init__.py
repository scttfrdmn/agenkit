"""
agenkit: The foundation layer for AI agents.

Minimal, perfect primitives for agent communication.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version
from pathlib import Path

from agenkit.composition import ConditionalAgent, FallbackAgent, ParallelAgent, SequentialAgent
from agenkit.interfaces import (
    Agent,
    CallOptions,
    IntrospectionResult,
    Message,
    Tool,
    ToolResult,
)
from agenkit.patterns import Task

try:
    # Read from installed distribution metadata rather than hardcoding, so this
    # cannot drift from pyproject.toml the way it did for 77 minor versions
    # (#842: this said 0.10.0 while the same package's pyproject said 0.70.0).
    __version__ = _package_version("agenkit")
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    # Not installed (e.g. imported straight from a checkout). Fall back to the
    # VERSION file, which is the source of truth that pyproject.toml derives from.
    _version_file = Path(__file__).resolve().parent.parent / "VERSION"
    __version__ = (
        _version_file.read_text(encoding="utf-8").strip() if _version_file.is_file() else "unknown"
    )

__all__ = [
    # Core interfaces
    "Agent",
    # Per-call inference options
    "CallOptions",
    # Composition patterns
    "ConditionalAgent",
    "FallbackAgent",
    # Introspection
    "IntrospectionResult",
    "Message",
    "ParallelAgent",
    "SequentialAgent",
    # Agent patterns
    "Task",
    "Tool",
    "ToolResult",
]

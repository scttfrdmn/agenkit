"""Python feature scanner using AST parsing.

This scanner serves as the reference implementation for feature detection.
It uses Python's AST module to accurately detect classes and their inheritance.
"""

import ast
from pathlib import Path
from typing import Any

from ._paths import COMPOSITION_AGENT_NAMES, detect_protocols, scan_techniques_by_filename


def scan() -> dict[str, Any]:
    """Scan Python codebase for all features.

    Returns:
        Dictionary with detected features by category.
    """
    root = Path("agenkit")

    return {
        "patterns": scan_patterns(root),
        "middleware": scan_middleware(root),
        "llm_adapters": scan_llm_adapters(root),
        "memory": scan_memory(root),
        "techniques": scan_techniques(root),
        "protocols": scan_protocols(root),
    }


def scan_patterns(root: Path) -> list[str]:
    """Scan for agent patterns in agenkit/patterns/ and agenkit/composition/.

    Detects classes with 'Agent' in their name. composition/ additionally
    declares a non-agent `AgentResult` dataclass, so that directory is
    restricted to the known composition-pattern names (see #918).

    Args:
        root: Root directory of Python package

    Returns:
        Sorted list of pattern names (e.g., ["ReflectionAgent", "SequentialAgent"])
    """
    patterns = []
    patterns_dir = root / "patterns"
    composition_dir = root / "composition"

    for py_file in patterns_dir.rglob("*.py") if patterns_dir.exists() else []:
        if py_file.name.startswith("_"):  # Skip __init__.py, etc.
            continue

        try:
            tree = ast.parse(py_file.read_text())

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Look for classes with "Agent" in name
                    if "Agent" in node.name and not node.name.startswith("_"):
                        patterns.append(node.name)

        except SyntaxError:
            # Skip files with syntax errors
            continue

    for py_file in composition_dir.rglob("*.py") if composition_dir.exists() else []:
        if py_file.name.startswith("_"):
            continue

        try:
            tree = ast.parse(py_file.read_text())

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name in COMPOSITION_AGENT_NAMES:
                    patterns.append(node.name)

        except SyntaxError:
            continue

    return sorted(set(patterns))


def scan_middleware(root: Path) -> list[str]:
    """Scan for middleware in agenkit/middleware/.

    Detects classes with 'Decorator' suffix or middleware-related names.

    Args:
        root: Root directory of Python package

    Returns:
        Sorted list of middleware names
    """
    middleware = []
    middleware_dir = root / "middleware"

    if not middleware_dir.exists():
        return middleware

    # Known middleware patterns
    middleware_patterns = [
        "Decorator",
        "Middleware",
        "TimeoutDecorator",
        "RetryDecorator",
        "RateLimiterDecorator",
        "CircuitBreakerDecorator",
        "CachingDecorator",
        "BatchingDecorator",
        "PerUserRateLimiterDecorator",
    ]

    for py_file in middleware_dir.rglob("*.py"):
        if py_file.name.startswith("_"):
            continue

        try:
            tree = ast.parse(py_file.read_text())

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if class name matches middleware patterns
                    for pattern in middleware_patterns:
                        if pattern in node.name and not node.name.startswith("_"):
                            middleware.append(node.name)
                            break

        except SyntaxError:
            continue

    return sorted(set(middleware))


def scan_llm_adapters(root: Path) -> list[str]:
    """Scan for LLM adapters in agenkit/adapters/llm/.

    Detects adapter classes (OpenAIAdapter, AnthropicAdapter, etc.).

    Args:
        root: Root directory of Python package

    Returns:
        Sorted list of adapter names
    """
    adapters = []
    adapters_dir = root / "adapters" / "llm"

    if not adapters_dir.exists():
        return adapters

    for py_file in adapters_dir.rglob("*.py"):
        if py_file.name in ["__init__.py", "base.py"]:  # Skip base classes
            continue

        try:
            tree = ast.parse(py_file.read_text())

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Look for classes ending in "Adapter" or "LLM"
                    if (
                        ("Adapter" in node.name or "LLM" in node.name)
                        and not node.name.startswith("_")
                        and node.name != "LLM"  # Skip base class
                    ):
                        adapters.append(node.name)

        except SyntaxError:
            continue

    return sorted(set(adapters))


def scan_memory(root: Path) -> list[str]:
    """Scan for memory backends in agenkit/memory/.

    Detects memory backend classes (InMemoryMemory, RedisMemory, etc.).

    Args:
        root: Root directory of Python package

    Returns:
        Sorted list of memory backend names
    """
    memory_backends = []
    memory_dir = root / "memory"

    if not memory_dir.exists():
        return memory_backends

    for py_file in memory_dir.rglob("*.py"):
        if py_file.name in ["__init__.py", "base.py"]:  # Skip base classes
            continue

        try:
            tree = ast.parse(py_file.read_text())

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Look for classes ending in "Memory"
                    if (
                        node.name.endswith("Memory")
                        and not node.name.startswith("_")
                        and node.name != "Memory"  # Skip base class
                    ):
                        memory_backends.append(node.name)

        except SyntaxError:
            continue

    return sorted(set(memory_backends))


def scan_techniques(root: Path) -> list[str]:
    """Scan for techniques in agenkit/techniques/.

    Detects technique implementations (ChainOfThought, SelfConsistency, etc.).

    Args:
        root: Root directory of Python package

    Returns:
        Sorted list of technique names
    """
    techniques_dir = root / "techniques"
    return scan_techniques_by_filename(techniques_dir, "*.py")


def scan_protocols(root: Path) -> list[str]:
    """Scan for agent-interop protocols in agenkit/.

    Python files protocols in two trees: the modern agenkit/protocols/ (mcp,
    agui, agui_simple) and the legacy agenkit/techniques/protocols/ (a2a, mcp).

    Args:
        root: Root directory of Python package

    Returns:
        Sorted list of protocol names (e.g., ["a2a", "agui", "mcp"])
    """
    protocols_dir = root / "protocols"
    legacy_protocols_dir = root / "techniques" / "protocols"
    return detect_protocols(protocols_dir, legacy_protocols_dir)


if __name__ == "__main__":
    """Quick test when run directly."""
    import json

    result = scan()
    print(json.dumps(result, indent=2))

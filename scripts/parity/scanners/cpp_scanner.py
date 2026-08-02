"""C++ feature scanner using file structure and regex.

This scanner detects features in the C++ codebase by analyzing
file structure and using regex patterns to find class definitions.
"""

import re
from pathlib import Path
from typing import Any

from ._paths import scan_techniques_by_filename


def scan() -> dict[str, Any]:
    """Scan C++ codebase for all features.

    Returns:
        Dictionary with detected features by category.
    """
    root = Path("agenkit-cpp/include/agenkit")

    return {
        "patterns": scan_patterns(root),
        "middleware": scan_middleware(root),
        "llm_adapters": scan_llm_adapters(root),
        "memory": scan_memory(root),
        "techniques": scan_techniques(root),
    }


def scan_patterns(root: Path) -> list[str]:
    """Scan for agent patterns in agenkit-cpp/include/agenkit/patterns/.

    Detects classes with 'Agent' in their name.

    Args:
        root: Root directory of C++ package

    Returns:
        Sorted list of pattern names
    """
    patterns = []
    patterns_dir = root / "patterns"

    if not patterns_dir.exists():
        return patterns

    # Regex to find class definitions with "Agent" in name
    # Matches: class FooAgent, class FooAgent : public Agent
    agent_pattern = re.compile(r"class\s+(\w*Agent)")

    for hpp_file in patterns_dir.rglob("*.hpp"):
        if hpp_file.name.startswith("_"):
            continue

        try:
            content = hpp_file.read_text()

            # Find all Agent class definitions
            for match in agent_pattern.finditer(content):
                name = match.group(1)
                # Skip private types, mocks, base classes, and test utilities
                if (
                    not name.startswith("_")
                    and "mock" not in name.lower()
                    and name not in ["Agent", "MultiAgent"]
                    and "Dummy" not in name
                    and "NoConfidence" not in name
                ):
                    patterns.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(patterns))


def scan_middleware(root: Path) -> list[str]:
    """Scan for middleware in agenkit-cpp/include/agenkit/middleware/.

    Detects middleware classes.

    Args:
        root: Root directory of C++ package

    Returns:
        Sorted list of middleware names
    """
    middleware = []
    middleware_dir = root / "middleware"

    if not middleware_dir.exists():
        return middleware

    # Pattern for middleware classes
    # Matches: class TimeoutMiddleware, class TimeoutConfig
    middleware_pattern = re.compile(
        r"class\s+(Timeout|Retry|RateLimiter|CircuitBreaker|Caching|Batching|PerUserRateLimiter)"
        r"(Config|Middleware|Decorator)?"
    )

    for hpp_file in middleware_dir.rglob("*.hpp"):
        if hpp_file.name == "middleware.hpp":  # Skip base interface
            continue

        try:
            content = hpp_file.read_text()

            for match in middleware_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Middleware"
                name = f"{base}{suffix}"

                middleware.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(middleware))


def scan_llm_adapters(root: Path) -> list[str]:
    """Scan for LLM adapters in agenkit-cpp/include/agenkit/adapters/.

    Detects LLM adapter implementations.

    Args:
        root: Root directory of C++ package

    Returns:
        Sorted list of adapter names
    """
    adapters = []
    adapters_dir = root / "adapters"

    if not adapters_dir.exists():
        return adapters

    # Pattern for LLM adapters
    # Matches: class OpenAIAdapter, class AnthropicLLM
    adapter_pattern = re.compile(
        r"class\s+(OpenAI|Anthropic|Bedrock|Gemini|Ollama|LiteLLM)(Adapter|LLM|Client)?"
    )

    for hpp_file in adapters_dir.rglob("*.hpp"):
        try:
            content = hpp_file.read_text()

            for match in adapter_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Adapter"
                name = f"{base}{suffix}"

                adapters.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(adapters))


def scan_memory(root: Path) -> list[str]:
    """Scan for memory backends in agenkit-cpp/include/agenkit/memory/.

    Detects memory backend implementations.

    Args:
        root: Root directory of C++ package

    Returns:
        Sorted list of memory backend names
    """
    memory_backends = []
    memory_dir = root / "infrastructure" / "memory"

    if not memory_dir.exists():
        return memory_backends

    # Pattern for memory backends
    # Matches: class InMemoryBackend, class RedisMemory
    memory_pattern = re.compile(
        r"class\s+(InMemory|Redis|Vector|Hierarchy|Endless)(Memory|Backend)?"
    )

    for hpp_file in memory_dir.rglob("*.hpp"):
        try:
            content = hpp_file.read_text()

            for match in memory_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Memory"
                name = f"{base}{suffix}"

                memory_backends.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(memory_backends))


def scan_techniques(root: Path) -> list[str]:
    """Scan for techniques in agenkit-cpp/include/agenkit/techniques/.

    Detects technique implementations.

    Args:
        root: Root directory of C++ package

    Returns:
        Sorted list of technique names
    """
    techniques_dir = root / "techniques"
    return scan_techniques_by_filename(techniques_dir, "*.hpp")


if __name__ == "__main__":
    """Quick test when run directly."""
    import json

    result = scan()
    print(json.dumps(result, indent=2))

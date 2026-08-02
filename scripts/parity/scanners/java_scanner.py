"""Java feature scanner using file structure and regex.

This scanner detects features in the Java codebase by analyzing
file structure and using regex patterns to find class definitions.
"""

import re
from pathlib import Path
from typing import Any

from ._paths import scan_techniques_by_filename


def scan() -> dict[str, Any]:
    """Scan Java codebase for all features.

    Returns:
        Dictionary with detected features by category.
    """
    root = Path("agenkit-java/src/main/java/io/agenkit")

    return {
        "patterns": scan_patterns(root),
        "middleware": scan_middleware(root),
        "llm_adapters": scan_llm_adapters(root),
        "memory": scan_memory(root),
        "techniques": scan_techniques(root),
    }


def scan_patterns(root: Path) -> list[str]:
    """Scan for agent patterns in agenkit-java/.../patterns/.

    Detects classes with 'Agent' or 'Orchestrator' in their name.

    Args:
        root: Root directory of Java package

    Returns:
        Sorted list of pattern names
    """
    patterns = []
    patterns_dir = root / "patterns"

    if not patterns_dir.exists():
        return patterns

    # Regex to find class definitions with "Agent"/"Orchestrator" in name
    # Matches: public final class FooAgent implements Agent
    agent_pattern = re.compile(
        r"public\s+(?:final\s+|abstract\s+)?class\s+(\w*(?:Agent|Orchestrator))\b"
    )

    for java_file in patterns_dir.rglob("*.java"):
        if java_file.name.startswith("_"):
            continue

        try:
            content = java_file.read_text()

            for match in agent_pattern.finditer(content):
                name = match.group(1)
                # Skip private types, mocks, and base classes
                if (
                    not name.startswith("_")
                    and "mock" not in name.lower()
                    and name not in ["Agent", "MultiAgent"]
                ):
                    patterns.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(patterns))


def scan_middleware(root: Path) -> list[str]:
    """Scan for middleware in agenkit-java/.../middleware/.

    Detects middleware classes.

    Args:
        root: Root directory of Java package

    Returns:
        Sorted list of middleware names
    """
    middleware = []
    middleware_dir = root / "middleware"

    if not middleware_dir.exists():
        return middleware

    # Pattern for middleware classes
    # Matches: public final class TimeoutMiddleware
    middleware_pattern = re.compile(
        r"public\s+(?:final\s+|abstract\s+)?class\s+"
        r"(Timeout|Retry|RateLimiter|CircuitBreaker|Caching|Batching|PerUserRateLimiter|Metrics)"
        r"(Middleware|Decorator|Config)?\b"
    )

    for java_file in middleware_dir.rglob("*.java"):
        if java_file.name.startswith("_"):
            continue

        try:
            content = java_file.read_text()

            for match in middleware_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Middleware"
                name = f"{base}{suffix}"

                middleware.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(middleware))


def scan_llm_adapters(root: Path) -> list[str]:
    """Scan for LLM adapters in agenkit-java/.../adapters/.

    Detects LLM adapter implementations.

    Args:
        root: Root directory of Java package

    Returns:
        Sorted list of adapter names
    """
    adapters = []
    adapters_dir = root / "adapters"

    if not adapters_dir.exists():
        return adapters

    # Pattern for LLM adapters
    # Matches: public final class AnthropicAdapter implements LlmClient
    adapter_pattern = re.compile(
        r"public\s+(?:final\s+|abstract\s+)?class\s+"
        r"(OpenAi|Anthropic|Bedrock|Gemini|Ollama|LiteLLM|Mock)(Adapter|LLM|Client)?\b"
    )

    for java_file in adapters_dir.rglob("*.java"):
        try:
            content = java_file.read_text()

            for match in adapter_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Adapter"
                name = f"{base}{suffix}"

                adapters.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(adapters))


def scan_memory(root: Path) -> list[str]:
    """Scan for memory backends in agenkit-java/.../memory/.

    Detects memory backend implementations.

    Args:
        root: Root directory of Java package

    Returns:
        Sorted list of memory backend names
    """
    memory_backends = []
    memory_dir = root / "memory"

    if not memory_dir.exists():
        return memory_backends

    # Pattern for memory backends
    # Matches: public final class EphemeralMemory, public final class VectorMemory
    memory_pattern = re.compile(
        r"public\s+(?:final\s+|abstract\s+)?class\s+"
        r"(InMemory|Ephemeral|Redis|Vector|Memory)(Memory|Backend|Hierarchy)?\b"
    )

    for java_file in memory_dir.rglob("*.java"):
        try:
            content = java_file.read_text()

            for match in memory_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Memory"
                name = f"{base}{suffix}"

                memory_backends.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(memory_backends))


def scan_techniques(root: Path) -> list[str]:
    """Scan for techniques in agenkit-java/.../techniques/.

    Detects technique implementations.

    Args:
        root: Root directory of Java package

    Returns:
        Sorted list of technique names
    """
    techniques_dir = root / "techniques"
    # No techniques subsystem in this language yet -- declared gap, not a
    # stale path. See #754.
    return scan_techniques_by_filename(techniques_dir, "*.java", required=False)


if __name__ == "__main__":
    """Quick test when run directly."""
    import json

    result = scan()
    print(json.dumps(result, indent=2))

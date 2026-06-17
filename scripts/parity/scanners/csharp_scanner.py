"""C# feature scanner using file structure and regex.

This scanner detects features in the C# codebase by analyzing
file structure and using regex patterns to find class definitions.
"""

import re
from pathlib import Path
from typing import Any


def scan() -> dict[str, Any]:
    """Scan C# codebase for all features.

    Returns:
        Dictionary with detected features by category.
    """
    root = Path("agenkit-cs/src/Agenkit")

    return {
        "patterns": scan_patterns(root),
        "middleware": scan_middleware(root),
        "llm_adapters": scan_llm_adapters(root),
        "memory": scan_memory(root),
        "techniques": scan_techniques(root),
    }


def scan_patterns(root: Path) -> list[str]:
    """Scan for agent patterns in agenkit-cs/src/Agenkit/Patterns/.

    Detects classes with 'Agent' or 'Orchestrator' in their name.

    Args:
        root: Root directory of C# package

    Returns:
        Sorted list of pattern names
    """
    patterns = []
    patterns_dir = root / "Patterns"

    if not patterns_dir.exists():
        return patterns

    # Regex to find class definitions with "Agent"/"Orchestrator" in name
    # Matches: public class FooAgent : IAgent, public class FooOrchestrator
    agent_pattern = re.compile(
        r"public\s+(?:sealed\s+|abstract\s+)?class\s+(\w*(?:Agent|Orchestrator))\b"
    )

    for cs_file in patterns_dir.glob("*.cs"):
        if cs_file.name.startswith("_"):
            continue

        try:
            content = cs_file.read_text()

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
    """Scan for middleware in agenkit-cs/src/Agenkit/Middleware/.

    Detects middleware classes.

    Args:
        root: Root directory of C# package

    Returns:
        Sorted list of middleware names
    """
    middleware = []
    middleware_dir = root / "Middleware"

    if not middleware_dir.exists():
        return middleware

    # Pattern for middleware classes
    # Matches: public class TimeoutMiddleware, public class CachingMiddleware
    middleware_pattern = re.compile(
        r"public\s+(?:sealed\s+|abstract\s+)?class\s+"
        r"(Timeout|Retry|RateLimiter|CircuitBreaker|Caching|Batching|PerUserRateLimiter|Metrics)"
        r"(Middleware|Decorator|Config)?\b"
    )

    for cs_file in middleware_dir.glob("*.cs"):
        if cs_file.name.startswith("_"):
            continue

        try:
            content = cs_file.read_text()

            for match in middleware_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Middleware"
                name = f"{base}{suffix}"

                middleware.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(middleware))


def scan_llm_adapters(root: Path) -> list[str]:
    """Scan for LLM adapters in agenkit-cs/src/Agenkit/Adapters/.

    Detects LLM adapter implementations.

    Args:
        root: Root directory of C# package

    Returns:
        Sorted list of adapter names
    """
    adapters = []
    adapters_dir = root / "Adapters"

    if not adapters_dir.exists():
        return adapters

    # Pattern for LLM adapters
    # Matches: public class AnthropicAdapter, public class OpenAiAdapter
    adapter_pattern = re.compile(
        r"public\s+(?:sealed\s+|abstract\s+)?class\s+"
        r"(OpenAi|Anthropic|Bedrock|Gemini|Ollama|LiteLLM|Mock)(Adapter|LLM|Client)?\b"
    )

    for cs_file in adapters_dir.glob("*.cs"):
        try:
            content = cs_file.read_text()

            for match in adapter_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Adapter"
                name = f"{base}{suffix}"

                adapters.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(adapters))


def scan_memory(root: Path) -> list[str]:
    """Scan for memory backends in agenkit-cs/src/Agenkit/Memory/.

    Detects memory backend implementations.

    Args:
        root: Root directory of C# package

    Returns:
        Sorted list of memory backend names
    """
    memory_backends = []
    memory_dir = root / "Memory"

    if not memory_dir.exists():
        return memory_backends

    # Pattern for memory backends
    # Matches: public class EphemeralMemory, public class VectorMemory
    memory_pattern = re.compile(
        r"public\s+(?:sealed\s+|abstract\s+)?class\s+"
        r"(InMemory|Ephemeral|Redis|Vector|Memory)(Memory|Backend|Hierarchy)?\b"
    )

    for cs_file in memory_dir.glob("*.cs"):
        try:
            content = cs_file.read_text()

            for match in memory_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Memory"
                name = f"{base}{suffix}"

                memory_backends.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(memory_backends))


def scan_techniques(root: Path) -> list[str]:
    """Scan for techniques in agenkit-cs/src/Agenkit/Techniques/.

    Detects technique implementations.

    Args:
        root: Root directory of C# package

    Returns:
        Sorted list of technique names
    """
    techniques = []
    techniques_dir = root / "Techniques"

    if not techniques_dir.exists():
        return techniques

    # Pattern for technique classes
    technique_pattern = re.compile(
        r"public\s+(?:sealed\s+|abstract\s+)?class\s+(\w+Technique|\w+Strategy)\b"
    )

    for cs_file in techniques_dir.glob("*.cs"):
        if cs_file.name.startswith("_"):
            continue

        try:
            content = cs_file.read_text()

            for match in technique_pattern.finditer(content):
                name = match.group(1)
                if not name.startswith("_") and "mock" not in name.lower():
                    techniques.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(techniques))


if __name__ == "__main__":
    """Quick test when run directly."""
    import json

    result = scan()
    print(json.dumps(result, indent=2))

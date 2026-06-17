"""Scala feature scanner using file structure and regex.

This scanner detects features in the Scala codebase by analyzing
file structure and using regex patterns to find class/trait/object
definitions.
"""

import re
from pathlib import Path
from typing import Any


def scan() -> dict[str, Any]:
    """Scan Scala codebase for all features.

    Returns:
        Dictionary with detected features by category.
    """
    root = Path("agenkit-scala/src/main/scala/io/agenkit")

    return {
        "patterns": scan_patterns(root),
        "middleware": scan_middleware(root),
        "llm_adapters": scan_llm_adapters(root),
        "memory": scan_memory(root),
        "techniques": scan_techniques(root),
    }


def scan_patterns(root: Path) -> list[str]:
    """Scan for agent patterns in agenkit-scala/.../patterns/.

    Detects classes/objects with 'Agent' or 'Orchestrator' in their name.

    Args:
        root: Root directory of Scala package

    Returns:
        Sorted list of pattern names
    """
    patterns = []
    patterns_dir = root / "patterns"

    if not patterns_dir.exists():
        return patterns

    # Regex to find class/trait/object definitions with "Agent"/"Orchestrator"
    # Matches: class ReActAgent(, case class FooAgent, trait FooAgent, object FooAgent
    agent_pattern = re.compile(
        r"(?:final\s+|sealed\s+|abstract\s+)*"
        r"(?:case\s+)?(?:class|trait|object)\s+(\w*(?:Agent|Orchestrator))\b"
    )

    for scala_file in patterns_dir.glob("*.scala"):
        if scala_file.name.startswith("_"):
            continue

        try:
            content = scala_file.read_text()

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
    """Scan for middleware in agenkit-scala/.../middleware/.

    Detects middleware classes/objects.

    Args:
        root: Root directory of Scala package

    Returns:
        Sorted list of middleware names
    """
    middleware = []
    middleware_dir = root / "middleware"

    if not middleware_dir.exists():
        return middleware

    # Pattern for middleware classes/objects
    # Matches: class TimeoutMiddleware, object CachingMiddleware
    middleware_pattern = re.compile(
        r"(?:final\s+|sealed\s+|abstract\s+)*"
        r"(?:case\s+)?(?:class|trait|object)\s+"
        r"(Timeout|Retry|RateLimiter|CircuitBreaker|Caching|Batching|PerUserRateLimiter|Metrics)"
        r"(Middleware|Decorator|Config)?\b"
    )

    for scala_file in middleware_dir.glob("*.scala"):
        if scala_file.name.startswith("_"):
            continue

        try:
            content = scala_file.read_text()

            for match in middleware_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Middleware"
                name = f"{base}{suffix}"

                middleware.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(middleware))


def scan_llm_adapters(root: Path) -> list[str]:
    """Scan for LLM adapters in agenkit-scala/.../adapters/.

    Detects LLM adapter implementations.

    Args:
        root: Root directory of Scala package

    Returns:
        Sorted list of adapter names
    """
    adapters = []
    adapters_dir = root / "adapters"

    if not adapters_dir.exists():
        return adapters

    # Pattern for LLM adapters
    # Matches: class AnthropicAdapter(, class OpenAiAdapter(
    adapter_pattern = re.compile(
        r"(?:final\s+|sealed\s+|abstract\s+)*"
        r"(?:case\s+)?(?:class|trait|object)\s+"
        r"(OpenAi|Anthropic|Bedrock|Gemini|Ollama|LiteLLM|Mock)(Adapter|LLM|Client)?\b"
    )

    for scala_file in adapters_dir.glob("*.scala"):
        try:
            content = scala_file.read_text()

            for match in adapter_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Adapter"
                name = f"{base}{suffix}"

                adapters.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(adapters))


def scan_memory(root: Path) -> list[str]:
    """Scan for memory backends in agenkit-scala/.../memory/.

    Detects memory backend implementations.

    Args:
        root: Root directory of Scala package

    Returns:
        Sorted list of memory backend names
    """
    memory_backends = []
    memory_dir = root / "memory"

    if not memory_dir.exists():
        return memory_backends

    # Pattern for memory backends
    # Matches: class EphemeralMemory(, class VectorMemory(, class MemoryHierarchy(
    # The bare "Memory" base trait requires an explicit suffix so the abstract
    # interface itself (trait Memory) is not counted as a backend.
    memory_pattern = re.compile(
        r"(?:final\s+|sealed\s+|abstract\s+)*"
        r"(?:case\s+)?(?:class|trait|object)\s+"
        r"(?:(InMemory|Ephemeral|Redis|Vector)(Memory|Backend|Hierarchy)?"
        r"|(Memory)(Backend|Hierarchy))\b"
    )

    for scala_file in memory_dir.glob("*.scala"):
        try:
            content = scala_file.read_text()

            for match in memory_pattern.finditer(content):
                if match.group(1):
                    base = match.group(1)
                    suffix = match.group(2) or "Memory"
                else:
                    base = match.group(3)
                    suffix = match.group(4)
                name = f"{base}{suffix}"

                memory_backends.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(memory_backends))


def scan_techniques(root: Path) -> list[str]:
    """Scan for techniques in agenkit-scala/.../techniques/.

    Detects technique implementations.

    Args:
        root: Root directory of Scala package

    Returns:
        Sorted list of technique names
    """
    techniques = []
    techniques_dir = root / "techniques"

    if not techniques_dir.exists():
        return techniques

    # Pattern for technique classes/objects
    technique_pattern = re.compile(
        r"(?:final\s+|sealed\s+|abstract\s+)*"
        r"(?:case\s+)?(?:class|trait|object)\s+(\w+Technique|\w+Strategy)\b"
    )

    for scala_file in techniques_dir.glob("*.scala"):
        if scala_file.name.startswith("_"):
            continue

        try:
            content = scala_file.read_text()

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

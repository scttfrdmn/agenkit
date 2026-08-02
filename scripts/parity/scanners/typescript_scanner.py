"""TypeScript feature scanner using file structure and regex.

This scanner detects features in the TypeScript codebase by analyzing
file structure and using regex patterns to find class/interface definitions.
"""

import re
from pathlib import Path
from typing import Any

from ._paths import scan_techniques_by_filename


def scan() -> dict[str, Any]:
    """Scan TypeScript codebase for all features.

    Returns:
        Dictionary with detected features by category.
    """
    root = Path("agenkit-ts/src")

    return {
        "patterns": scan_patterns(root),
        "middleware": scan_middleware(root),
        "llm_adapters": scan_llm_adapters(root),
        "memory": scan_memory(root),
        "techniques": scan_techniques(root),
    }


def scan_patterns(root: Path) -> list[str]:
    """Scan for agent patterns in agenkit-ts/src/patterns/.

    Detects classes with 'Agent' in their name.

    Args:
        root: Root directory of TypeScript package

    Returns:
        Sorted list of pattern names
    """
    patterns = []
    patterns_dir = root / "patterns"

    if not patterns_dir.exists():
        return patterns

    # Regex to find class/interface definitions with "Agent" in name
    # Matches: class FooAgent, interface FooAgent, export class FooAgent
    agent_pattern = re.compile(r"(?:export\s+)?(?:class|interface)\s+(\w*Agent)")

    for ts_file in patterns_dir.rglob("*.ts"):
        if ts_file.name.startswith("_") or ts_file.name.endswith(".test.ts"):
            continue

        try:
            content = ts_file.read_text()

            # Find all Agent class/interface definitions
            for match in agent_pattern.finditer(content):
                name = match.group(1)
                # Skip base classes, private types, and mocks
                if (
                    not name.startswith("_")
                    and "mock" not in name.lower()
                    and name not in ["Agent", "MultiAgent"]  # Exclude base classes
                ):
                    patterns.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(patterns))


def scan_middleware(root: Path) -> list[str]:
    """Scan for middleware in agenkit-ts/src/middleware/.

    Detects middleware classes.

    Args:
        root: Root directory of TypeScript package

    Returns:
        Sorted list of middleware names
    """
    middleware = []
    middleware_dir = root / "middleware"

    if not middleware_dir.exists():
        return middleware

    # Pattern for middleware classes
    # Matches: class TimeoutMiddleware, class RetryDecorator
    middleware_pattern = re.compile(
        r"(?:export\s+)?class\s+(Timeout|Retry|RateLimiter|CircuitBreaker|Caching|Batching|PerUserRateLimiter)"
        r"(Middleware|Decorator)?"
    )

    for ts_file in middleware_dir.rglob("*.ts"):
        if ts_file.name.startswith("_") or ts_file.name.endswith(".test.ts"):
            continue

        try:
            content = ts_file.read_text()

            for match in middleware_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Middleware"
                name = f"{base}{suffix}"

                middleware.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(middleware))


def scan_llm_adapters(root: Path) -> list[str]:
    """Scan for LLM adapters in agenkit-ts/src/adapters/.

    Detects LLM adapter implementations.

    Args:
        root: Root directory of TypeScript package

    Returns:
        Sorted list of adapter names
    """
    adapters = []
    adapters_dir = root / "adapters"

    if not adapters_dir.exists():
        return adapters

    # Pattern for LLM adapters
    # Matches: class OpenAILLM, class AnthropicAdapter
    adapter_pattern = re.compile(
        r"(?:export\s+)?class\s+(OpenAI|Anthropic|Bedrock|Gemini|Ollama|LiteLLM|Local)"
        r"(LLM|Adapter|Agent)?"
    )

    for ts_file in adapters_dir.rglob("*.ts"):
        if ts_file.name in ["index.ts"] or ts_file.name.endswith(".test.ts"):
            continue

        try:
            content = ts_file.read_text()

            for match in adapter_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Adapter"
                name = f"{base}{suffix}"

                adapters.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(adapters))


def scan_memory(root: Path) -> list[str]:
    """Scan for memory backends in agenkit-ts/src/memory/.

    Detects memory backend implementations.

    Args:
        root: Root directory of TypeScript package

    Returns:
        Sorted list of memory backend names
    """
    memory_backends = []
    memory_dir = root / "memory"

    if not memory_dir.exists():
        return memory_backends

    # Pattern for memory backends
    # Matches: class InMemoryMemory, class RedisMemory
    memory_pattern = re.compile(
        r"(?:export\s+)?class\s+(InMemory|Redis|Vector|Hierarchy|Endless)(Memory|Backend)?"
    )

    for ts_file in memory_dir.rglob("*.ts"):
        if ts_file.name in ["index.ts", "base.ts"] or ts_file.name.endswith(".test.ts"):
            continue

        try:
            content = ts_file.read_text()

            for match in memory_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Memory"
                name = f"{base}{suffix}"

                memory_backends.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(memory_backends))


def scan_techniques(root: Path) -> list[str]:
    """Scan for techniques in agenkit-ts/src/techniques/.

    Detects technique implementations.

    Args:
        root: Root directory of TypeScript package

    Returns:
        Sorted list of technique names
    """
    techniques_dir = root / "techniques"
    return scan_techniques_by_filename(techniques_dir, "*.ts")


if __name__ == "__main__":
    """Quick test when run directly."""
    import json

    result = scan()
    print(json.dumps(result, indent=2))

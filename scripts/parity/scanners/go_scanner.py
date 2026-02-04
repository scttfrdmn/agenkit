"""Go feature scanner using file structure and regex.

This scanner detects features in the Go codebase by analyzing
file structure and using regex patterns to find type definitions.
"""

import re
import subprocess
from pathlib import Path
from typing import Any


def scan() -> dict[str, Any]:
    """Scan Go codebase for all features.

    Returns:
        Dictionary with detected features by category.
    """
    root = Path("agenkit-go")

    return {
        "patterns": scan_patterns(root),
        "middleware": scan_middleware(root),
        "llm_adapters": scan_llm_adapters(root),
        "memory": scan_memory(root),
        "techniques": scan_techniques(root),
    }


def scan_patterns(root: Path) -> list[str]:
    """Scan for agent patterns in agenkit-go/patterns/.

    Detects structs and types with 'Agent' in their name.

    Args:
        root: Root directory of Go package

    Returns:
        Sorted list of pattern names
    """
    patterns = []
    patterns_dir = root / "patterns"

    if not patterns_dir.exists():
        return patterns

    # Regex to find type/struct definitions with "Agent" in name
    # Matches: type FooAgent struct, type FooAgent interface
    agent_pattern = re.compile(r"type\s+(\w*Agent)\s+(struct|interface)")

    for go_file in patterns_dir.glob("*.go"):
        if go_file.name.startswith("_"):
            continue

        try:
            content = go_file.read_text()

            # Find all Agent type definitions
            for match in agent_pattern.finditer(content):
                name = match.group(1)
                # Skip private types and mocks
                if not name.startswith("_") and "mock" not in name.lower():
                    patterns.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(patterns))


def scan_middleware(root: Path) -> list[str]:
    """Scan for middleware in agenkit-go/middleware/.

    Detects middleware types and decorators.

    Args:
        root: Root directory of Go package

    Returns:
        Sorted list of middleware names
    """
    middleware = []
    middleware_dir = root / "middleware"

    if not middleware_dir.exists():
        return middleware

    # Pattern for middleware types
    # Matches: type Timeout, type TimeoutMiddleware, type TimeoutConfig
    middleware_pattern = re.compile(
        r"type\s+(Timeout|Retry|RateLimiter|CircuitBreaker|Caching|Batching|PerUserRateLimiter)"
        r"(Middleware|Decorator|Config)?\s+(struct|interface)"
    )

    for go_file in middleware_dir.glob("*.go"):
        if go_file.name.startswith("_") or go_file.name.endswith("_test.go"):
            continue

        try:
            content = go_file.read_text()

            for match in middleware_pattern.finditer(content):
                # Construct full name
                base = match.group(1)
                suffix = match.group(2) or "Middleware"
                name = f"{base}{suffix}"

                middleware.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(middleware))


def scan_llm_adapters(root: Path) -> list[str]:
    """Scan for LLM adapters in agenkit-go/adapter/llm/.

    Detects LLM adapter implementations.

    Args:
        root: Root directory of Go package

    Returns:
        Sorted list of adapter names
    """
    adapters = []
    adapters_dir = root / "adapter" / "llm"

    if not adapters_dir.exists():
        return adapters

    # Pattern for LLM adapters
    # Matches: type OpenAI, type OpenAILLM, type OpenAIAdapter
    adapter_pattern = re.compile(r"type\s+(OpenAI|Anthropic|Bedrock|Gemini|Ollama|LiteLLM|OpenAICompatible)(LLM|Adapter)?\s+struct")

    for go_file in adapters_dir.glob("*.go"):
        if go_file.name in ["llm.go"] or go_file.name.endswith("_test.go"):
            continue

        try:
            content = go_file.read_text()

            for match in adapter_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "LLM"
                name = f"{base}{suffix}"

                adapters.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(adapters))


def scan_memory(root: Path) -> list[str]:
    """Scan for memory backends in agenkit-go/memory/.

    Detects memory backend implementations.

    Args:
        root: Root directory of Go package

    Returns:
        Sorted list of memory backend names
    """
    memory_backends = []
    memory_dir = root / "memory"

    if not memory_dir.exists():
        return memory_backends

    # Pattern for memory backends
    # Matches: type InMemory, type InMemoryMemory, type RedisBackend
    memory_pattern = re.compile(r"type\s+(InMemory|Redis|Vector|Hierarchy|Endless)(Memory|Backend)?\s+struct")

    for go_file in memory_dir.glob("*.go"):
        if go_file.name in ["memory.go"] or go_file.name.endswith("_test.go"):
            continue

        try:
            content = go_file.read_text()

            for match in memory_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Memory"
                name = f"{base}{suffix}"

                memory_backends.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(memory_backends))


def scan_techniques(root: Path) -> list[str]:
    """Scan for techniques in agenkit-go/techniques/.

    Detects technique implementations.

    Args:
        root: Root directory of Go package

    Returns:
        Sorted list of technique names
    """
    techniques = []
    techniques_dir = root / "techniques"

    if not techniques_dir.exists():
        return techniques

    # Pattern for technique types
    technique_pattern = re.compile(r"type\s+(\w+Technique|\w+Strategy)\s+(struct|interface)")

    for go_file in techniques_dir.glob("*.go"):
        if go_file.name.startswith("_") or go_file.name.endswith("_test.go"):
            continue

        try:
            content = go_file.read_text()

            for match in technique_pattern.finditer(content):
                name = match.group(1)
                if not name.startswith("_"):
                    techniques.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(techniques))


if __name__ == "__main__":
    """Quick test when run directly."""
    import json

    result = scan()
    print(json.dumps(result, indent=2))

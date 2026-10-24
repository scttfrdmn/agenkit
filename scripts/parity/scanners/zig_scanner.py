"""Zig feature scanner using file structure and regex.

This scanner detects features in the Zig codebase by analyzing
file structure and using regex patterns to find struct definitions.
"""

import re
from pathlib import Path
from typing import Any

from ._paths import COMPOSITION_AGENT_NAMES, detect_protocols, scan_techniques_by_filename


def scan() -> dict[str, Any]:
    """Scan Zig codebase for all features.

    Returns:
        Dictionary with detected features by category.
    """
    root = Path("agenkit-zig/src")

    return {
        "patterns": scan_patterns(root),
        "middleware": scan_middleware(root),
        "llm_adapters": scan_llm_adapters(root),
        "memory": scan_memory(root),
        "techniques": scan_techniques(root),
        "protocols": scan_protocols(root),
    }


def scan_patterns(root: Path) -> list[str]:
    """Scan for agent patterns in agenkit-zig/src/patterns/ and composition.zig.

    Detects structs with 'Agent' in their name. Unlike the other 8 languages,
    Zig's composition code lives in a single file (composition.zig), not a
    composition/ directory, and only declares SequentialAgent/FallbackAgent
    there -- ParallelAgent/ConditionalAgent live in patterns/ (see #918).

    Args:
        root: Root directory of Zig package

    Returns:
        Sorted list of pattern names
    """
    patterns = []
    patterns_dir = root / "patterns"
    composition_file = root / "composition.zig"

    # Regex to find struct definitions with "Agent" in name
    # Matches: pub const FooAgent = struct
    agent_pattern = re.compile(r"pub\s+const\s+(\w*Agent)\s*=\s*struct")

    for zig_file in patterns_dir.rglob("*.zig") if patterns_dir.exists() else []:
        if zig_file.name.startswith("_") or zig_file.name == "mod.zig":
            continue

        try:
            content = zig_file.read_text()

            # Find all Agent struct definitions
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

    if composition_file.exists():
        content = composition_file.read_text()
        for match in agent_pattern.finditer(content):
            name = match.group(1)
            if name in COMPOSITION_AGENT_NAMES:
                patterns.append(name)

    return sorted(set(patterns))


def scan_middleware(root: Path) -> list[str]:
    """Scan for middleware in agenkit-zig/src/middleware/.

    Detects middleware structs.

    Args:
        root: Root directory of Zig package

    Returns:
        Sorted list of middleware names
    """
    middleware = []
    middleware_dir = root / "middleware"

    if not middleware_dir.exists():
        return middleware

    # Pattern for middleware structs
    # Matches: pub const TimeoutDecorator = struct, pub const TimeoutConfig = struct
    middleware_pattern = re.compile(
        r"pub\s+const\s+(Timeout|Retry|RateLimiter|CircuitBreaker|Caching|Batching|PerUserRateLimiter)"
        r"(Config|Decorator|Middleware)?\s*=\s*struct"
    )

    for zig_file in middleware_dir.rglob("*.zig"):
        if zig_file.name == "mod.zig":  # Skip module file
            continue

        try:
            content = zig_file.read_text()

            for match in middleware_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Decorator"
                name = f"{base}{suffix}"

                middleware.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(middleware))


def scan_llm_adapters(root: Path) -> list[str]:
    """Scan for LLM adapters in agenkit-zig/src/adapters/.

    Detects LLM adapter implementations.

    Args:
        root: Root directory of Zig package

    Returns:
        Sorted list of adapter names
    """
    adapters = []
    adapters_dir = root / "adapter"

    if not adapters_dir.exists():
        return adapters

    # Pattern for LLM adapters
    # Matches: pub const OpenAIAdapter = struct
    adapter_pattern = re.compile(
        r"pub\s+const\s+(OpenAI|Anthropic|Bedrock|Gemini|Ollama|LiteLLM)(Adapter|LLM|Client)?\s*=\s*struct"
    )

    for zig_file in adapters_dir.rglob("*.zig"):
        if zig_file.name == "mod.zig":
            continue

        try:
            content = zig_file.read_text()

            for match in adapter_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Adapter"
                name = f"{base}{suffix}"

                adapters.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(adapters))


def scan_memory(root: Path) -> list[str]:
    """Scan for memory backends in agenkit-zig/src/memory/.

    Detects memory backend implementations.

    Args:
        root: Root directory of Zig package

    Returns:
        Sorted list of memory backend names
    """
    memory_backends = []
    memory_dir = root / "infrastructure" / "memory"

    if not memory_dir.exists():
        return memory_backends

    # Pattern for memory backends
    # Matches: pub const InMemoryBackend = struct
    memory_pattern = re.compile(
        r"pub\s+const\s+(InMemory|Redis|Vector|Hierarchy|Endless)(Memory|Backend)?\s*=\s*struct"
    )

    for zig_file in memory_dir.rglob("*.zig"):
        if zig_file.name == "mod.zig":
            continue

        try:
            content = zig_file.read_text()

            for match in memory_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Memory"
                name = f"{base}{suffix}"

                memory_backends.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(memory_backends))


def scan_techniques(root: Path) -> list[str]:
    """Scan for techniques in agenkit-zig/src/techniques/.

    Detects technique implementations.

    Args:
        root: Root directory of Zig package

    Returns:
        Sorted list of technique names
    """
    techniques_dir = root / "techniques"
    return scan_techniques_by_filename(techniques_dir, "*.zig")


def scan_protocols(root: Path) -> list[str]:
    """Scan for agent-interop protocols in the protocols/ directory.

    Args:
        root: Root directory of the language package

    Returns:
        Sorted list of protocol names (e.g., ["agui", "mcp"])
    """
    protocols_dir = root / "protocols"
    return detect_protocols(protocols_dir)


if __name__ == "__main__":
    """Quick test when run directly."""
    import json

    result = scan()
    print(json.dumps(result, indent=2))

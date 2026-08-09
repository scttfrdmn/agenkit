"""Rust feature scanner using file structure and regex.

This scanner detects features in the Rust codebase by analyzing
file structure and using regex patterns to find struct/impl definitions.
"""

import re
from pathlib import Path
from typing import Any

from ._paths import COMPOSITION_AGENT_NAMES, scan_techniques_by_filename


def scan() -> dict[str, Any]:
    """Scan Rust codebase for all features.

    Returns:
        Dictionary with detected features by category.
    """
    root = Path("agenkit-rust/src")

    return {
        "patterns": scan_patterns(root),
        "middleware": scan_middleware(root),
        "llm_adapters": scan_llm_adapters(root),
        "memory": scan_memory(root),
        "techniques": scan_techniques(root),
    }


def scan_patterns(root: Path) -> list[str]:
    """Scan for agent patterns in agenkit-rust/src/patterns/ and .../composition/.

    Detects structs with 'Agent' in their name. composition/ additionally
    declares a non-agent `AgentResult` struct and several `#[cfg(test)]`-only
    mock structs (`CounterAgent`, `ErrorAgent`, etc.), so that directory is
    restricted to the known composition-pattern names (see #918).

    Args:
        root: Root directory of Rust package

    Returns:
        Sorted list of pattern names
    """
    patterns = []
    patterns_dir = root / "patterns"
    composition_dir = root / "composition"

    # Regex to find struct definitions with "Agent" in name
    # Matches: pub struct FooAgent, struct FooAgent
    agent_pattern = re.compile(r"(?:pub\s+)?struct\s+(\w*Agent)")

    for rs_file in patterns_dir.rglob("*.rs") if patterns_dir.exists() else []:
        if rs_file.name.startswith("_"):
            continue

        try:
            content = rs_file.read_text()

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

    for rs_file in composition_dir.rglob("*.rs") if composition_dir.exists() else []:
        if rs_file.name.startswith("_"):
            continue

        try:
            content = rs_file.read_text()

            for match in agent_pattern.finditer(content):
                name = match.group(1)
                if name in COMPOSITION_AGENT_NAMES:
                    patterns.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(patterns))


def scan_middleware(root: Path) -> list[str]:
    """Scan for middleware in agenkit-rust/src/middleware/.

    Detects middleware structs.

    Args:
        root: Root directory of Rust package

    Returns:
        Sorted list of middleware names
    """
    middleware = []
    middleware_dir = root / "middleware"

    if not middleware_dir.exists():
        return middleware

    # Pattern for middleware structs
    # Matches: pub struct Timeout, pub struct TimeoutConfig
    middleware_pattern = re.compile(
        r"(?:pub\s+)?struct\s+(Timeout|Retry|RateLimiter|CircuitBreaker|Caching|Batching|PerUserRateLimiter)"
        r"(Config|Middleware|Decorator)?"
    )

    for rs_file in middleware_dir.rglob("*.rs"):
        if rs_file.name.startswith("_"):
            continue

        try:
            content = rs_file.read_text()

            for match in middleware_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Middleware"
                name = f"{base}{suffix}"

                middleware.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(middleware))


def scan_llm_adapters(root: Path) -> list[str]:
    """Scan for LLM adapters in agenkit-rust/src/adapters/.

    Detects LLM adapter implementations.

    Args:
        root: Root directory of Rust package

    Returns:
        Sorted list of adapter names
    """
    adapters = []
    adapters_dir = root / "adapters"

    if not adapters_dir.exists():
        return adapters

    # Pattern for LLM adapters
    # Matches: pub struct OpenAI, pub struct LiteLLM
    adapter_pattern = re.compile(
        r"(?:pub\s+)?struct\s+(OpenAI|Anthropic|Bedrock|Gemini|Ollama|LiteLLM)(Adapter|LLM|Client)?"
    )

    for rs_file in adapters_dir.rglob("*.rs"):
        if rs_file.name in ["mod.rs"]:
            continue

        try:
            content = rs_file.read_text()

            for match in adapter_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Adapter"
                name = f"{base}{suffix}"

                adapters.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(adapters))


def scan_memory(root: Path) -> list[str]:
    """Scan for memory backends in agenkit-rust/src/memory/.

    Detects memory backend implementations.

    Args:
        root: Root directory of Rust package

    Returns:
        Sorted list of memory backend names
    """
    memory_backends = []
    memory_dir = root / "memory"

    if not memory_dir.exists():
        return memory_backends

    # Pattern for memory backends
    # Matches: pub struct InMemory, pub struct RedisMemory
    memory_pattern = re.compile(
        r"(?:pub\s+)?struct\s+(InMemory|Redis|Vector|Hierarchy|Endless)(Memory|Backend)?"
    )

    for rs_file in memory_dir.rglob("*.rs"):
        if rs_file.name in ["mod.rs"]:
            continue

        try:
            content = rs_file.read_text()

            for match in memory_pattern.finditer(content):
                base = match.group(1)
                suffix = match.group(2) or "Memory"
                name = f"{base}{suffix}"

                memory_backends.append(name)

        except (UnicodeDecodeError, PermissionError):
            continue

    return sorted(set(memory_backends))


def scan_techniques(root: Path) -> list[str]:
    """Scan for techniques in agenkit-rust/src/techniques/.

    Detects technique implementations.

    Args:
        root: Root directory of Rust package

    Returns:
        Sorted list of technique names
    """
    techniques_dir = root / "techniques"
    return scan_techniques_by_filename(techniques_dir, "*.rs")


if __name__ == "__main__":
    """Quick test when run directly."""
    import json

    result = scan()
    print(json.dumps(result, indent=2))

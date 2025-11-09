# agenkit

**The foundation layer for AI agents.**

Minimal, perfect primitives for agent communication. ~500 lines of production-quality code.

## Status

🚧 **Week 1 - Core Implementation** 🚧

- ✅ Project structure
- ✅ Core interfaces (Agent, Tool, Message, ToolResult)
- ✅ Core patterns (Sequential, Parallel, Router)
- ✅ Comprehensive test suite
- ✅ Performance benchmarks
- ✅ Type checking (mypy strict)
- ✅ Documentation (API + Examples)

## Quick Start

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run benchmarks
pytest benchmarks/ -v -s

# Type check (strict mode on agenkit/)
mypy

# Format code
black agenkit/ tests/ benchmarks/
ruff check agenkit/ tests/ benchmarks/
```

## Design Principles

1. **Minimal**: Only what's required for interop (~500 lines)
2. **Type-safe**: Full type hints, mypy strict compliant
3. **Async-first**: Modern Python standards
4. **Extensible**: Metadata dicts everywhere
5. **Fast**: <15% interface overhead, negligible in production (benchmarked)
6. **Professional**: Production-quality code from day 1

## Core Interfaces

```python
from agenkit import Agent, Tool, Message, ToolResult

class MyAgent(Agent):
    @property
    def name(self) -> str:
        return "my_agent"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Processed: {message.content}")
```

## Core Patterns

```python
from agenkit import SequentialPattern, ParallelPattern, RouterPattern

# Sequential: agent1 → agent2 → agent3
pipeline = SequentialPattern([agent1, agent2, agent3])

# Parallel: all agents process same input concurrently
parallel = ParallelPattern([agent1, agent2, agent3])

# Router: route to one agent based on condition
router = RouterPattern(
    router=lambda msg: "handler1" if "code" in msg.content else "handler2",
    handlers={"handler1": agent1, "handler2": agent2}
)
```

## Performance

All benchmarks show minimal interface overhead:

```
Agent Interface Overhead:     ~2-3%
Tool Interface Overhead:      ~3-7%
Sequential Pattern Overhead:  ~3-8%
Parallel Pattern Overhead:    ~2-4%
Router Pattern Overhead:      ~8-12%
```

**Production Impact:** For real agent workloads (LLM calls, I/O, compute):
- Interface overhead: 0.0001-0.001ms per operation
- Typical LLM call: 100-1000ms
- **Total production overhead: <0.001%**

The measured overhead is at the microsecond scale. For production AI systems, this is completely negligible.

See `benchmarks/test_overhead.py` for detailed methodology and measurements.

## Architecture

```
agenkit/
├── __init__.py          # Public API
├── interfaces.py        # Agent, Tool, Message, ToolResult (~200 lines)
└── patterns.py          # Sequential, Parallel, Router (~300 lines)

tests/
├── test_interfaces.py   # Interface tests
└── test_patterns.py     # Pattern tests

benchmarks/
└── test_overhead.py     # Performance benchmarks
```

## Philosophy

**This is infrastructure, not a framework.**

- Interfaces, not implementations
- Primitives, not opinions
- Extensible, not prescriptive
- Foundation, not solution

## What's Next

**Phase 1 (Week 1-2):** Core + Tests + Benchmarks ✅
**Phase 2 (Week 3-4):** Protocol adapters (Python, Go, Rust)
**Phase 3 (Week 5-8):** Framework reimplementations
**Phase 4 (Week 9-10):** Documentation & tools
**Phase 5 (Week 11-12):** Launch

## Versioning

This project follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

Given a version number MAJOR.MINOR.PATCH:
- MAJOR version for incompatible API changes
- MINOR version for backwards-compatible functionality additions
- PATCH version for backwards-compatible bug fixes

See [CHANGELOG.md](CHANGELOG.md) for release history (following [Keep a Changelog](https://keepachangelog.com/)).

## License

BSD-3-Clause

## Contributing

Not accepting contributions yet - core implementation in progress.

## Documentation

- **[API Documentation](docs/API.md)** - Complete API reference with examples
- **[Examples](examples/)** - 6 practical examples covering all features
  - [Basic Agent](examples/01_basic_agent.py)
  - [Sequential Pattern](examples/02_sequential_pattern.py)
  - [Parallel Pattern](examples/03_parallel_pattern.py)
  - [Router Pattern](examples/04_router_pattern.py)
  - [Tool Usage](examples/05_tool_usage.py)
  - [Pattern Composition](examples/06_pattern_composition.py)

## More Info

- [Vision](AGENKIT_VISION.md) - Complete vision and strategy
- [Architecture](ARCHITECTURE.md) - Design principles
- [Why Now](WHY_NOW.md) - Market positioning
- [Executive Summary](EXECUTIVE_SUMMARY.md) - 12-week execution plan

---

**agenkit: Tradecraft for your agents.** 🎯

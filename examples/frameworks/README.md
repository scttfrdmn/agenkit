# Framework Examples

This directory demonstrates how popular AI agent frameworks can be built **ON TOP** of Agenkit primitives, showing that Agenkit is a **toolkit, not a framework**.

## Philosophy

Agenkit provides minimal, composable primitives that serve as building blocks. Complex framework abstractions (like LangChain, CrewAI) can be implemented using these primitives, demonstrating flexibility without vendor lock-in.

## Available Examples

### [MiniChain](minichain.py) - LangChain/LangGraph Equivalent

Demonstrates how LangChain-style abstractions map to Agenkit patterns:

| LangChain Pattern | Agenkit Primitive | Complexity |
|-------------------|-------------------|------------|
| LLMChain | Agent + LLM adapter | Simpler |
| ConversationChain | ConversationalAgent | Built-in memory |
| SequentialChain | SequentialAgent | Direct mapping |
| RouterChain | RouterAgent | Same concept |
| Memory | ConversationalAgent.history | Automatic |

**Usage:**
```bash
uv run python examples/frameworks/minichain.py
```

**Key Features:**
- LangChain-style API compatibility
- Built entirely on Agenkit primitives
- Shows pattern mappings
- Production-ready code (232 LOC)

### [MiniCrew](minicrew.py) - CrewAI Equivalent *(Coming Soon)*

Demonstrates how CrewAI-style multi-agent collaboration maps to Agenkit:

| CrewAI Pattern | Agenkit Primitive |
|----------------|-------------------|
| Crew | Supervisor + Orchestration |
| Agent | Agent interface |
| Task | Task pattern |
| Process | Orchestration pattern |

## Why Build on Agenkit?

**Performance:**
- 18x faster in Go vs Python LangChain
- 22x faster in Rust, 25x faster in C++
- Sub-millisecond orchestration overhead

**Flexibility:**
- Cross-language support (Python, Go, TypeScript, Rust, C++, Zig)
- 100% feature parity across all languages
- No vendor lock-in

**Production-Ready:**
- OpenTelemetry observability (industry standard)
- Built-in middleware (retry, circuit breaker, timeout, rate limiting)
- Explicit control (no hidden state management)

## Pattern Comparison

### Complexity

| Framework | LOC for Basic Agent | Dependencies | Runtime Overhead |
|-----------|---------------------|--------------|------------------|
| LangChain | ~15-20 | 50+ packages | High (abstraction layers) |
| Agenkit | ~10-15 | Minimal | Low (<5% benchmarked) |

### Composability

**LangChain:**
```python
# Hidden complexity, magic abstractions
chain = LLMChain(...) | SequentialChain(...) | RouterChain(...)
```

**Agenkit:**
```python
# Explicit composition, clear data flow
pipeline = SequentialAgent([agent1, agent2])
router = RouterAgent(config)
```

## Migration Guides

For detailed migration instructions, see:

- [LangChain → Agenkit](../../docs/migrations/langchain-to-agenkit.md)
- [CrewAI → Agenkit](../../docs/migrations/crewai-to-agenkit.md)
- [AutoGen → Agenkit](../../docs/migrations/autogen-to-agenkit.md)
- [Haystack → Agenkit](../../docs/migrations/haystack-to-agenkit.md)

## Running Examples

All examples use `uv` for dependency management:

```bash
# Run a specific example
uv run python examples/frameworks/minichain.py

# Or install dependencies first
uv sync
uv run python examples/frameworks/minichain.py
```

## Contributing

Have a framework you'd like to see demonstrated? Check out the patterns in existing examples and submit a PR!

**Requirements:**
- Keep examples under 400 LOC
- Show clear pattern mappings
- Include inline documentation
- Pass all linting checks
- Demonstrate "toolkit, not framework" philosophy

## Resources

- **Agenkit Documentation**: https://agenkit.dev
- **Architecture Guide**: ../../ARCHITECTURE.md
- **Pattern Library**: ../../agenkit/patterns/
- **Issue Tracker**: https://github.com/scttfrdmn/agenkit/issues

---

**Status**: MiniChain ✅ | MiniCrew 🔜 | More frameworks TBD

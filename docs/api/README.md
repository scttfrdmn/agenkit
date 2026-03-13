# Agenkit API Reference

This section contains per-language public API references for Agenkit. All six implementations share the same conceptual model — core types, LLM adapters, patterns, middleware, memory, and checkpointing — with idiomatic APIs for each language.

## Language References

| Language | Reference | Package / Module |
|----------|-----------|-----------------|
| Python | [python.md](python.md) | `agenkit` |
| Go | [go.md](go.md) | `github.com/scttfrdmn/agenkit/agenkit-go` |
| TypeScript | [typescript.md](typescript.md) | `agenkit-ts` |
| Rust | [rust.md](rust.md) | `agenkit` (crate) |
| C++ | [cpp.md](cpp.md) | `agenkit::core`, `agenkit::adapters`, … |
| Zig | [zig.md](zig.md) | `@import("agenkit")` |

## Common Concepts

All implementations share the following conceptual structure:

### Core Types
- **Message** — the fundamental unit of agent communication, carrying a role, content, and optional metadata.
- **Agent** — an abstract interface / trait / class that accepts a `Message` and returns a `Message`.

### LLM Adapters
Adapters wrap Anthropic and OpenAI APIs (and optional providers such as Bedrock, Gemini, Ollama, LiteLLM) and conform to the `Agent` interface so they can be used directly or composed inside patterns.

Default models: `claude-sonnet-4-6` (Anthropic), `gpt-4o` (OpenAI).

### Patterns
Eighteen reusable agent patterns are provided in all languages:

`Reflection`, `ReAct`, `AgentsAsTools`, `Orchestration`, `ReasoningWithTools`, `Conversational`, `Task`, `Multiagent`, `Planning`, `Autonomous`, `Sequential`, `Parallel`, `Router`, `Fallback`, `Collaborative`, `HumanInLoop`, `Supervisor`, `WorkingMemory`

### Middleware
Decorators / wrappers that add cross-cutting behavior to any agent:
`Retry`, `Timeout`, `RateLimiter`, `CircuitBreaker`, `Batching`, `Caching`, `Metrics`

### Memory
- **Ephemeral** — in-process, lost on restart.
- **Persistent** — local file or external store (Redis, vector DB).
- **Hierarchical** — short-term + long-term with automatic promotion strategies.

### Checkpointing
Durable checkpointing saves and restores agent state. Storage backends: local file, S3, NFS. Migration helpers support moving checkpoints between environments.

### Reasoning Techniques
Higher-order reasoning wrappers: `ChainOfThought`, `TreeOfThought`, `SelfConsistency`, `GraphOfThought`, `PlanAndSolve`, `LeastToMost`.

---

For cross-language migration guides see [docs/MIGRATION_INDEX.md](../MIGRATION_INDEX.md).
For pattern descriptions see [docs/PATTERNS.md](../PATTERNS.md).
For observability APIs see [docs/observability.md](../observability.md).

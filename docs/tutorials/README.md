# Agenkit Tutorials

Step-by-step guides for building AI agents with agenkit. Each tutorial builds on the
previous one, so reading them in order is recommended.

---

| # | Tutorial | What you learn |
|---|---|---|
| 1 | [Your First Agent in 5 Minutes](./01_getting_started.md) | Build a minimal working agent in all 6 languages (Python, Go, TypeScript, Rust, C++, Zig) |
| 2 | [Memory and Conversation Context](./02_memory_and_context.md) | Multi-turn conversations, sliding-window history, and persisting sessions to disk |
| 3 | [Production Patterns: Retry, Circuit Breaker, and Observability](./03_production_patterns.md) | Wrap agents with retry logic, circuit breaker, metrics collection, and OpenTelemetry tracing |
| 4 | [Long-Running Agents and Checkpointing](./04_long_running_agents.md) | Survive process restarts with automatic checkpointing; use local disk, S3, or NFS storage |
| 5 | [Multi-Agent Composition Patterns](./05_multi_agent.md) | Chain agents sequentially, run them in parallel, and add fallback behaviour |

---

## Prerequisites

All tutorials assume basic familiarity with async programming in your chosen language.
Tutorial 1 covers installation for every language; later tutorials add dependencies as
needed.

## Running the examples

Every code snippet in these tutorials is self-contained and runnable. Copy it into a
file, install the package, and execute it directly:

```bash
# Python
uv run python my_agent.py

# Go
go run my_agent.go

# TypeScript
npx ts-node myAgent.ts
```

## Getting help

- **Reference docs:** `docs/API_REFERENCE.md`
- **Pattern catalogue:** `docs/PATTERNS.md`
- **Runnable examples:** `examples/`
- **FAQ:** `docs/FAQ.md`

---

## Language-Specific Tutorials

Deep-dive guides for each compiled language, covering idiomatic patterns, concurrency
models, testing strategies, and production best practices.

| Tutorial | Language | Key Topics |
|----------|----------|------------|
| [Building Production AI Agents in Go](./go_patterns.md) | Go | Goroutines, fan-out/fan-in channels, middleware chaining, property tests with `pgregory.net/rapid`, graceful shutdown |
| [Building Production AI Agents in TypeScript](./typescript_patterns.md) | TypeScript | Async chains, generic typed tools, React integration with abort signals, property tests with `fast-check`, error boundary patterns |
| [Building Production AI Agents in Rust](./rust_patterns.md) | Rust | `Arc<Mutex<T>>` vs `Rc<RefCell<T>>`, tokio concurrency, `Cow<str>` zero-copy, `thiserror`/`anyhow` error propagation, property tests with `proptest` |
| [Building Production AI Agents in C++](./cpp_patterns.md) | C++ | RAII smart pointers, variadic template composition, `std::async`/`std::future`, GoogleTest fixtures and parameterised tests, RapidCheck property tests |

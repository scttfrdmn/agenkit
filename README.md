# Agenkit

**Build production-ready AI agent systems.**

Agenkit is a lightweight, cross-language toolkit for building distributed AI agents that scale from prototype to production without rewriting your code.

[![Website](https://img.shields.io/badge/website-agenkit.dev-blue)](https://agenkit.dev)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript 5.0+](https://img.shields.io/badge/typescript-5.0+-3178C6.svg)](https://www.typescriptlang.org/)
[![Go 1.25+](https://img.shields.io/badge/go-1.25+-00ADD8.svg)](https://golang.org/)
[![Rust 1.75+](https://img.shields.io/badge/rust-1.75+-orange.svg)](https://www.rust-lang.org/)
[![Zig 0.15.2+](https://img.shields.io/badge/zig-0.15.2+-F7A41D.svg)](https://ziglang.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Tests: 8500+ tests](https://img.shields.io/badge/tests-8500+%20passing-brightgreen.svg)](tests/)
[![9 Languages](https://img.shields.io/badge/languages-9%20implementations-success.svg)](README.md#status)

## Why Agenkit?

### The Problem

Building production AI agent systems is hard:

- **Reliability**: LLMs fail unpredictably - you need circuit breakers, retries, and timeouts
- **Scale**: Prototypes work locally but break in production when you need distributed deployment
- **Observability**: Understanding what went wrong requires distributed tracing across services
- **Language Lock-in**: Python is great for prototyping, but you need Go/Rust for performance
- **Integration**: Every agent framework has its own incompatible abstractions

### The Solution

Agenkit provides the production infrastructure you need:

```
Prototype → Production
┌─────────────────────────────────────────────┐
│  Your Agents (Python for development)      │
└──────────────┬──────────────────────────────┘
               │
               │ Same Interface
               ↓
┌─────────────────────────────────────────────┐
│  Agenkit Toolkit                            │
│  • Automatic retries & circuit breakers    │
│  • Distributed tracing & metrics           │
│  • Cross-language support (Python ↔ Go)    │
│  • Multiple transports (HTTP/gRPC/WS)      │
└─────────────────────────────────────────────┘
```

**Key Insight:** Write your agents once in Python. Deploy them in Go for up to 18x lower framework/transport overhead in our benchmarks (see [Performance](#performance) below) — the LLM call itself still dominates wall-clock time. Same interface, zero rewrites.

## Quick Start

### 30 Second Example

Create a simple agent:

```python
from agenkit import Agent, Message

class MyAgent(Agent):
    @property
    def name(self) -> str:
        return "my-agent"

    async def process(self, message: Message) -> Message:
        return Message(
            role="agent",
            content=f"Processed: {message.content}"
        )

# Use it
agent = MyAgent()
response = await agent.process(Message(role="user", content="Hello!"))
```

### Add Production Features in 3 Lines

```python
from agenkit.middleware import RetryConfig, RetryDecorator, CircuitBreakerDecorator

# Wrap with resilience
production_agent = RetryDecorator(
    CircuitBreakerDecorator(agent),
    RetryConfig(max_retries=3),
)

# Now handles failures automatically
response = await production_agent.process(message)
```

### Deploy Anywhere

```bash
# Run locally
python my_agent.py

# Deploy with Docker
docker-compose up

# Scale with Kubernetes
kubectl apply -f deploy/kubernetes/
```

## Core Features

### 🎯 Simple, Minimal Interface

```python
class Agent:
    name: str                          # Unique identifier
    async def process(msg) -> Message  # Process messages
```

**That's it.** Everything else is optional.

### 🔄 Production Middleware (Add What You Need)

```python
from agenkit.middleware import (
    CircuitBreakerConfig,
    CircuitBreakerDecorator,
    RetryConfig,
    RetryDecorator,
    TimeoutConfig,
    TimeoutDecorator,
)

# Start simple
agent = MyAgent()

# Add retry logic
agent = RetryDecorator(agent, RetryConfig(max_retries=3))

# Add circuit breaker
agent = CircuitBreakerDecorator(agent, CircuitBreakerConfig(failure_threshold=5))

# Add timeouts (timeout_ms for clarity)
agent = TimeoutDecorator(agent, TimeoutConfig(timeout_ms=30000))

# Stack as many as you need
```

**Every middleware is <100 lines.** Easy to understand, modify, or replace.

### 🌐 Cross-Language Support

Write once. Deploy anywhere. **Nine language implementations** (Python is the
reference; all nine share the same `Agent`/`Message`/`Tool` core and most of
the 18 core patterns — C#, Java, and Scala are missing `AgentsAsTools`; see
[Status](#status) for the exact per-language pattern-class counts):

```python
# Python - Prototype quickly with ML ecosystem
class MyAgent(Agent):
    async def process(self, message):
        return process_with_python_libs(message)
```

```typescript
// TypeScript - Full-stack with browser support
class MyAgent implements Agent {
    async process(message: Message): Promise<Message> {
        return processWithTypeScriptLibs(message);
    }
}
```

```go
// Go - Production scale (up to 18x lower transport overhead vs Python in our benchmarks)
type MyAgent struct{}

func (a *MyAgent) Process(ctx context.Context, msg *Message) (*Message, error) {
    return processWithGoLibs(msg)
}
```

```cpp
// C++ - Maximum performance with zero-overhead abstractions
class MyAgent : public Agent {
public:
    Message process(const Message& msg) override {
        return process_with_cpp_libs(msg);
    }
};
```

```rust
// Rust - Memory safety + performance (up to 20x lower transport overhead vs Python in our benchmarks)
struct MyAgent;

impl Agent for MyAgent {
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        process_with_rust_libs(message).await
    }
}
```

```zig
// Zig - Systems programming with safety (up to 22x lower transport overhead vs Python in our benchmarks)
const MyAgent = struct {
    pub fn process(self: *MyAgent, message: Message) !Message {
        return processWithZigLibs(message);
    }
};
```

**Same interface across all languages.** Python, Go, and Rust are the most
complete; C#, Java, and Scala are newer and still filling in advanced
subsystems (skills, some adapters). Choose the right tool for each service.

### 📊 Full Observability

```python
from agenkit.observability import TracingMiddleware, init_tracing

# Enable tracing
init_tracing("my-service")

# Wrap agent
traced_agent = TracingMiddleware(agent)

# Every operation now traced in Jaeger
```

**View traces:** `http://localhost:16686`

### 🔍 Agent Introspection

```python
# Inspect agent state during debugging or production
result = agent.introspect()

print(f"Agent: {result.agent_name}")
print(f"Capabilities: {result.capabilities}")
print(f"Internal state: {result.internal_state}")
print(f"Memory: {result.memory_state}")

# Use for monitoring
def check_agent_health(agent):
    result = agent.introspect()
    return result.internal_state.get("error_count", 0) < 10

# Use for testing
def test_agent_state():
    result1 = agent.introspect()
    await agent.process(message)
    result2 = agent.introspect()
    assert result2.internal_state["msg_count"] > result1.internal_state["msg_count"]
```

**Introspection ≠ Reflection:**
- **Introspection** (this feature): Examines *current* state ("What do I know?")
- **Reflection** (pattern): Analyzes *past* performance ("How did I do?")

### 🚀 Multiple Transports

```python
from agenkit.adapters.python import GRPCServer, LocalAgent
from agenkit.adapters.python.http_server import HTTPAgentServer

# Same agent, different transports
await HTTPAgentServer(agent, port=8080).start()               # REST API
await GRPCServer(agent, "localhost:50051").start()            # High performance
await LocalAgent(agent, endpoint="ws://127.0.0.1:8765").start()  # Bidirectional streaming
```

**Choose the right protocol for each use case.**

## When Should You Use Agenkit?

### ✅ Perfect For:

- Building production AI agent systems that need to scale
- Teams that prototype in Python but deploy in Go
- Systems that need resilience (retries, circuit breakers, timeouts)
- Distributed agent systems that need observability
- Integrating multiple AI agent frameworks

### ❌ Not For:

- Simple one-off scripts (too much overhead)
- Embedded systems (requires async runtime)
- Real-time systems (<1ms latency requirements)

## Installation

### Core Installation

```bash
# Python
pip install agenkit

# Go
go get github.com/scttfrdmn/agenkit-go

# TypeScript/Node.js
npm install @agenkit/core

# C++
# Clone and build (CMake required)
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/agenkit-cpp && mkdir build && cd build && cmake .. && make

# Rust
cargo add agenkit

# Zig
# Clone and build (Zig 0.12+ required)
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/agenkit-zig && zig build
```

### Python: Install with Specific LLM Providers

```bash
# Install only what you need
pip install agenkit[openai]          # OpenAI (GPT-4, GPT-3.5)
pip install agenkit[anthropic]       # Anthropic (Claude 3.5)
pip install agenkit[aws]             # AWS Bedrock
pip install agenkit[google]          # Google Gemini
pip install agenkit[ollama]          # Ollama (local models)

# Multiple providers
pip install agenkit[openai,anthropic]

# All providers
pip install agenkit[all-providers]

# With Redis memory backend
pip install agenkit[redis]

# Everything (for development)
pip install agenkit[all]
```

**See [INSTALLATION.md](INSTALLATION.md) for complete installation guide.**

## What's Included?

### Core Components
- **Minimal interfaces** - Agent, Message, Tool (50 lines total)
- **Orchestration patterns** - Sequential, Parallel, Router, Fallback
- **Type safety** - Full type hints (Python), compile-time checks (Go)

### Production Middleware (Optional)
- **Circuit Breaker** - Prevent cascading failures
- **Retry** - Exponential backoff with jitter
- **Timeout** - Request deadline enforcement
- **Rate Limiter** - Token bucket algorithm
- **Caching** - LRU cache with TTL
- **Batching** - Request aggregation

### Transport Layer (Optional)
- **HTTP** - REST APIs (HTTP/1.1, HTTP/2, HTTP/3)
- **gRPC** - High-performance binary protocol
- **WebSocket** - Bidirectional streaming

### Observability (Optional)
- **Distributed Tracing** - OpenTelemetry integration
- **Metrics** - Prometheus endpoints
- **Structured Logging** - JSON logs with trace correlation

### Autonomous Agent Features (Optional)
- **Memory Management** - Context retention with compression strategies
- **Budget Tracking** - Token counting and cost optimization
- **Checkpointing** - State persistence and recovery
- **Safety** - Prompt injection detection, input/output validation
- **Evaluation** - Quality metrics and benchmarking

## Performance

**Transport Overhead:** <1% of total time in realistic LLM workloads

**Language Performance (framework/transport overhead, not general application
performance):**
- Go HTTP transport: 18.5x lower latency than Python's in the same benchmark
  (0.055ms vs 1.02ms)
- Middleware overhead: <0.01% of request time

These figures — and the "18x"/"20x"/"22x" multipliers mentioned earlier in
this README for Go/Rust/Zig — were measured in November 2025 against Python
3.14.0 and Go 1.21–1.22 on Apple Silicon (see `benchmarks/BASELINES.md`).
Both the Go toolchain and several dependency versions have since moved, so
the exact multiplier should not be read as current; the qualitative
conclusion that transport/framework overhead is a small fraction of a
100–1000ms LLM call has held across every measurement to date. See
[COMPATIBILITY.md](COMPATIBILITY.md#performance-characteristics) for the
full caveat and how to regenerate current numbers.

**Scale:**
- Kubernetes autoscaling: 3-10 replicas based on load
- Message size scaling: 10,000x size = 190x latency (linear)

See [benchmarks/BASELINES.md](benchmarks/BASELINES.md) for detailed performance data.

## Production Ready

### 8500+ Tests Passing
- Cross-language integration tests (Python ↔ Go ↔ C++)
- Chaos engineering tests (network failures, crashes)
- Property-based tests (invariant validation)
- Thousands of unit and integration tests across 9 languages (Python alone: 2200+;
  see [Test Parity](#test-parity) below for the current per-language breakdown)

### Security
- Input validation
- Prompt injection detection
- RBAC and audit logging
- Non-root containers
- Dropped capabilities

### Observability
- Jaeger distributed tracing
- Prometheus metrics
- Structured JSON logging
- Health check endpoints

### Deployment
- Docker images
- Kubernetes manifests with HPA
- Horizontal pod autoscaling (3-10 replicas)
- Zero-downtime rolling updates

## Architecture

```
┌─────────────────────────────────────────┐
│   Your Application (Agents + Logic)    │
└──────────────┬──────────────────────────┘
               │
┌──────────────┴──────────────────────────┐
│   Optional Middleware Layer             │
│   (Add only what you need)              │
│   • Retry     • Caching                 │
│   • Timeout   • Batching                │
│   • Circuit Breaker                     │
└──────────────┬──────────────────────────┘
               │
┌──────────────┴──────────────────────────┐
│   Optional Transport Layer              │
│   • HTTP   • gRPC   • WebSocket         │
└──────────────┬──────────────────────────┘
               │
┌──────────────┴──────────────────────────┐
│   Core Interface (Required)             │
│   • Agent  • Message  • Tool            │
└─────────────────────────────────────────┘
```

**Design Philosophy:** Start simple. Add complexity only when you need it.

## Learning Path

1. **[Getting Started](GETTING_STARTED.md)** (15 min) - Choose your language and create your first agent
   - [Python Guide](docs/getting-started/python.md) | [Go Guide](docs/getting-started/go.md) | [TypeScript Guide](docs/getting-started/typescript.md)
   - [Rust Guide](docs/getting-started/rust.md) | [C++ Guide](docs/getting-started/cpp.md) | [Zig Guide](docs/getting-started/zig.md)
2. **[Agent Patterns Book](../agent-patterns-book)** (2-3 hours) - Master the 18 core patterns and advanced architectures
3. **[Advanced Architectures](docs/ADVANCED_ARCHITECTURES.md)** (1 hour) - Pattern compositions and multi-agent systems
4. **[Examples](examples/)** (1 hour) - Learn by doing with 27+ examples
5. **[Architecture](ARCHITECTURE.md)** (30 min) - Understand design principles
6. **[Migration Guides](docs/MIGRATION_INDEX.md)** (30 min per language) - Migrate between languages
7. **[Production Deployment](deploy/README.md)** (1 hour) - Docker + Kubernetes

**Total time investment:** ~6 hours from zero to production deployment with pattern mastery.

## Documentation

### Getting Started (Language-Specific)
- **[Python Guide](docs/getting-started/python.md)** - 15-30 min to first agent
- **[Go Guide](docs/getting-started/go.md)** - Idiomatic Go patterns
- **[TypeScript Guide](docs/getting-started/typescript.md)** - Modern JavaScript/TypeScript
- **[Rust Guide](docs/getting-started/rust.md)** - Memory-safe agents
- **[C++ Guide](docs/getting-started/cpp.md)** - High-performance systems
- **[Zig Guide](docs/getting-started/zig.md)** - Systems programming with safety

### Patterns & Architecture
- **[Agent Patterns Book](../agent-patterns-book)** - Comprehensive guide to 18 core patterns
- **[Advanced Architectures](docs/ADVANCED_ARCHITECTURES.md)** - Pattern compositions and multi-agent systems
- **[Architecture Principles](ARCHITECTURE.md)** - Design philosophy
- **[Streaming Patterns](docs/STREAMING_PATTERNS.md)** - Language-specific streaming approaches

### Migration & Reference
- **[Migration Guide Index](docs/MIGRATION_INDEX.md)** - Complete migration documentation for all 6 languages
- **[API Reference](docs/API.md)** - Complete API documentation
- **[Deployment Guide](deploy/README.md)** - Docker and Kubernetes
- **[Examples](examples/README.md)** - 27+ comprehensive examples

### Operations & Security
- **[Security Policy](SECURITY.md)** - Vulnerability reporting and best practices
- **[Compatibility Matrix](COMPATIBILITY.md)** - Language, platform, and version support
- **[Testing Strategy](TESTING.md)** - Test philosophy and coverage

### Package-Specific Docs
- [Memory Management](agenkit/memory/README.md) - Context retention strategies
- [Budget Tracking](agenkit/budget/README.md) - Token and cost management
- [Checkpointing](agenkit/checkpointing/README.md) - State persistence
- [Safety & Security](agenkit/safety/README.md) - Input validation
- [Evaluation](agenkit/evaluation/README.md) - Quality metrics

## Examples

We provide 27+ examples covering common use cases:

**Getting Started:**
- [Basic Agent](examples/01_basic_agent.py) - Your first agent in 20 lines
- [Sequential Pipeline](examples/02_sequential_pattern.py) - Chain agents together
- [Parallel Execution](examples/03_parallel_pattern.py) - Run agents concurrently

**Production Features:**
- [Retry & Circuit Breaker](examples/middleware/circuit_breaker_example.py) - Handle failures
- [Distributed Tracing](examples/observability/observability_example.py) - Debug with Jaeger
- [Rate Limiting](examples/middleware/rate_limiter_example.py) - Protect your APIs

**Advanced:**
- [Remote Agents](examples/adapters/01_basic_remote_agent.py) - Cross-process communication
- [Streaming Responses](examples/adapters/03_streaming.py) - Server-sent events

[Browse all examples →](examples/README.md)

## Community

- **Website:** [agenkit.dev](https://agenkit.dev)
- **GitHub:** [github.com/scttfrdmn/agenkit](https://github.com/scttfrdmn/agenkit)
- **Issues:** [Report bugs or request features](https://github.com/scttfrdmn/agenkit/issues)
- **Discussions:** [Ask questions](https://github.com/scttfrdmn/agenkit/discussions)

## Contributing

We welcome contributions! See our [Contributing Guide](.github/CONTRIBUTING.md).

### Development Setup

```bash
# Clone repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run type checking
mypy agenkit/
```

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

## Status

**v0.89.0 — 9 language implementations, Python reference** (see the root `VERSION`
file for the current number — this line will drift again if hand-maintained)

### Language Support

The shared core is the `Agent`/`Message`/`Tool` interface plus 18 named
patterns (listed below). The "Pattern classes" column is a raw class count
from `feature-manifest.json` — it is **not** a conformance score against
those 18 patterns. Languages differ in how many concrete classes back a given
pattern for legitimate architectural reasons (Python ships config/streaming
variants like `StreamingConversationalAgent` and `ConversationalAgentConfig`
that other languages fold into one class; C++ has a couple of duplicate class
names for the same pattern), so a lower number does not always mean a missing
pattern. Regenerate it yourself with:
`uv run python -c "import json; d=json.load(open('feature-manifest.json')); [print(l, len(v['patterns'])) for l,v in d['languages'].items()]"`.
Two caveats on these specific numbers, found while re-deriving them for this
table: (1) C#/Java/Scala's scanners
(`scripts/parity/scanners/{csharp,java,scala}_scanner.py`) only walk each
language's `Patterns/` directory, but those three languages implement
`SequentialAgent`/`ParallelAgent` under a sibling `Composition/` directory
that the scanner never visits — so their manifest counts (15) undercount by
2; by direct source inspection all three actually have 17 of 18 patterns.
(2) The one gap in C#/Java/Scala that *is* real: none of the three implement
`AgentsAsTools` (verified by `grep -rl AgentTool` finding no hits under
`agenkit-cs`/`agenkit-java`/`agenkit-scala`). See #913 for a planned move to a
spec-conformance metric that would replace this class count with a
per-pattern ✅/❌ table generated from `specs/patterns/*.yaml`. The "Tests"
column is the test count from the parity report; "Depth" reflects how many
advanced subsystems (memory, skills, reasoning memory, full adapter set) are
implemented.

| Language | Pattern classes (of 18 named patterns) | LLM Adapters | Tests | Depth |
|----------|------------------------------------------|--------------|-------|-------|
| **Python** | 24 (all 18 patterns) | 7 | 2229 | Reference — all subsystems |
| **Go** | 17 (all 18 patterns) | 7 (+vLLM, SGLang) | 1330 | Complete — incl. reasoning memory, skills |
| **TypeScript** | 17 (all 18 patterns) | 7 | 976 | Broad — no skills / reasoning memory |
| **C++** | 18 (all 18 patterns) | 5 | 1133 | Broad — `safety/` not yet implemented |
| **Rust** | 15 (all 18 patterns) | 6 | 1352 | Complete — incl. skills |
| **Zig** | 13 (all 18 patterns) | 8 | 671 | Broad — no skills |
| **C#** (.NET) | 15 in manifest / 17 actual (missing `AgentsAsTools`) | 2 (+mock) | 272 | Newer — no skills |
| **Java** | 15 in manifest / 17 actual (missing `AgentsAsTools`) | 2 (+mock) | 358 | Newer — no skills |
| **Scala** | 15 in manifest / 17 actual (missing `AgentsAsTools`) | mock only | 363 | Newest — LLM adapters are stubs |

**18 Core Patterns** documented in the [Agent Patterns Book](../agent-patterns-book): Task, Conversational, ReAct, Planning, Reflection, ReasoningWithTools, AgentsAsTools, Memory, Sequential, Parallel, Router, Fallback, Orchestration, Supervisor, Collaborative, HumanInLoop, MultiAgent, Autonomous. Six languages (Python, Go, TypeScript, Rust, C++, Zig) implement all 18; C#, Java, and Scala implement 17 of 18 (missing `AgentsAsTools`).

### Recent Highlights (v0.85 – v0.89)

- ✅ **Defect repair** (v0.89) — 82 commits fixing release-gate and CI bugs found by a
  fleet audit (SBOM/signing, version-declaration drift, a test gate that couldn't fail)
- ✅ **Typed cross-language token `Usage`** (v0.86–v0.87) — unified `Usage` struct across
  all 9 language cores, plus Bedrock prompt-cache token counts
- ✅ **Agent Skills** (v0.85) — `AgentSkill`, `SkillRegistry`, `SkillEnabledAgent` (Python, Go, Rust)

v0.88.0 is intentionally skipped — reserved for the observability milestone (#715). See
`CHANGELOG.md` for the full release history.

### Project Status

- ✅ Core toolkit across 9 languages; 18 shared patterns in 6 of them, 17 of 18 in C#/Java/Scala (see [Status](#status))
- ✅ MCP (Model Context Protocol) client/server in every language
- ✅ Production middleware (retry, circuit breaker, timeout, rate limiting, caching, batching)
- ✅ Multiple transports (HTTP/1.1, HTTP/2, HTTP/3, gRPC, WebSocket)
- ✅ Deployment manifests (Docker + Kubernetes with HPA)
- 🚧 Advanced-subsystem parity (skills, reasoning memory, full adapter sets) still landing in the JVM/.NET tier

---

**Ready to build production AI agents?** Visit [agenkit.dev](https://agenkit.dev) or [get started in 5 minutes →](GETTING_STARTED.md)

## Test Parity

Patterns are at full parity across languages; **test-count** parity varies — the
secondary languages have fewer tests than the Python reference. Counts are
regenerated via `scripts/test-parity.sh` (and surfaced by the Parity Validation
CI workflow). Relative to Python's 2229 tests:

| Language | Tests | vs Python |
|----------|-------|-----------|
| Rust | 1352 | 61% |
| Go | 1330 | 60% |
| C++ | 1133 | 51% |
| TypeScript | 976 | 44% |
| Zig | 671 | 30% |
| Java | 358 | 16% |
| Scala | 363 | 16% |
| C# | 272 | 12% |

Counts are regenerated via `scripts/test-parity.sh`.

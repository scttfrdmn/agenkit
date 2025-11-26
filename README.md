# Agenkit

**Build production-ready AI agent systems.**

Agenkit is a lightweight, cross-language framework for building distributed AI agents that scale from prototype to production without rewriting your code.

[![Website](https://img.shields.io/badge/website-agenkit.dev-blue)](https://agenkit.dev)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript 5.0+](https://img.shields.io/badge/typescript-5.0+-3178C6.svg)](https://www.typescriptlang.org/)
[![Go 1.21+](https://img.shields.io/badge/go-1.21+-00ADD8.svg)](https://golang.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Tests: 1134+ tests](https://img.shields.io/badge/tests-1134+%20passing-brightgreen.svg)](tests/)
[![3 Languages + Rust](https://img.shields.io/badge/languages-3%20at%20100%25%20%2B%20Rust%2036%25-success.svg)](README.md#status)

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
│  Agenkit Framework                          │
│  • Automatic retries & circuit breakers    │
│  • Distributed tracing & metrics           │
│  • Cross-language support (Python ↔ Go)    │
│  • Multiple transports (HTTP/gRPC/WS)      │
└─────────────────────────────────────────────┘
```

**Key Insight:** Write your agents once in Python. Deploy them in Go for 18x better performance. Same interface, zero rewrites.

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
from agenkit.middleware import RetryMiddleware, CircuitBreakerMiddleware

# Wrap with resilience
production_agent = RetryMiddleware(
    CircuitBreakerMiddleware(agent)
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
# Start simple
agent = MyAgent()

# Add retry logic
agent = RetryMiddleware(agent, max_attempts=3)

# Add circuit breaker
agent = CircuitBreakerMiddleware(agent)

# Add timeouts
agent = TimeoutMiddleware(agent, timeout=30.0)

# Stack as many as you need
```

**Every middleware is <100 lines.** Easy to understand, modify, or replace.

### 🌐 Cross-Language Support

Write once. Deploy anywhere. **Three languages at 100% parity:**

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
// Go - Production scale (18x faster than Python)
type MyAgent struct{}

func (a *MyAgent) Process(ctx context.Context, msg *Message) (*Message, error) {
    return processWithGoLibs(msg)
}
```

**Same interface across all languages. Choose the right tool for each service.**

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

### 🚀 Multiple Transports

```python
from agenkit.adapters.python import HTTPServer, GRPCServer, WebSocketServer

# Same agent, different transports
HTTPServer(agent, port=8080).start()       # REST API
GRPCServer(agent, port=50051).start()      # High performance
WebSocketServer(agent, port=8765).start()  # Bidirectional streaming
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

```bash
# Python
pip install agenkit

# Go
go get github.com/agenkit/agenkit-go
```

## What's Included?

### Core Framework
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

**Language Performance:**
- Go HTTP: 18.5x faster than Python (0.055ms vs 1.02ms)
- Middleware overhead: <0.01% of request time

**Scale:**
- Kubernetes autoscaling: 3-10 replicas based on load
- Message size scaling: 10,000x size = 190x latency (linear)

See [benchmarks/BASELINES.md](benchmarks/BASELINES.md) for detailed performance data.

## Production Ready

### 867 Tests Passing
- 47 cross-language integration tests (Python ↔ Go)
- 53 chaos engineering tests (network failures, crashes)
- 37 property-based tests (invariant validation)
- 730+ unit and integration tests

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

1. **[Getting Started](GETTING_STARTED.md)** (15 min) - Create your first agent
2. **[Core Concepts](GETTING_STARTED.md#core-concepts)** (30 min) - Understand the fundamentals
3. **[Examples](examples/)** (1 hour) - Learn by doing with 27+ examples
4. **[Architecture](ARCHITECTURE.md)** (30 min) - Understand design principles
5. **[Production Deployment](deploy/README.md)** (1 hour) - Docker + Kubernetes

**Total time investment:** 3 hours from zero to production deployment.

## Documentation

- **[Getting Started Guide](GETTING_STARTED.md)** - Step-by-step tutorial
- **[Architecture Principles](ARCHITECTURE.md)** - Design philosophy
- **[API Reference](docs/API.md)** - Complete API documentation
- **[Deployment Guide](deploy/README.md)** - Docker and Kubernetes
- **[Examples](examples/README.md)** - 27+ comprehensive examples
- **[Security Policy](SECURITY.md)** - Vulnerability reporting and best practices
- **[Compatibility Matrix](COMPATIBILITY.md)** - Language, platform, and version support

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
- [Custom Middleware](examples/middleware/custom_middleware_example.py) - Extend the framework

[Browse all examples →](examples/README.md)

## Community

- **Website:** [agenkit.dev](https://agenkit.dev)
- **GitHub:** [github.com/agenkit/agenkit](https://github.com/agenkit/agenkit)
- **Issues:** [Report bugs or request features](https://github.com/agenkit/agenkit/issues)
- **Discussions:** [Ask questions](https://github.com/agenkit/agenkit/discussions)

## Contributing

We welcome contributions! See our [Contributing Guide](.github/CONTRIBUTING.md).

### Development Setup

```bash
# Clone repository
git clone https://github.com/agenkit/agenkit.git
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

**v0.25.0 - Rust Critical Patterns Complete! 🎉**

### Language Support

| Language | Patterns | Tests | Status | Performance |
|----------|----------|-------|--------|-------------|
| **Python** | 11/11 (100%) | ~300 | ✅ Complete | Reference |
| **TypeScript** | 11/11 (100%) | 643 | ✅ Complete | Node.js speed |
| **Go** | 11/11 (100%) | 410 | ✅ Complete | 18x Python |
| **Rust** | 4/11 (36%) | 44 | 🔄 In Progress | Expected 20x |
| C++ | 0/11 (0%) | 0 | 📋 Planned (v0.29+) | Max performance |
| Zig | 0/11 (0%) | 0 | 📋 Planned (v0.31+) | C interop |

**Milestone:** Three-language parity achieved 5 months ahead of schedule! Rust infrastructure and critical patterns complete.

### Project Status

- ✅ Core framework complete
- ✅ **Three languages at 100% pattern parity** (Python, TypeScript, Go)
- ✅ **Rust at 36% parity** - Infrastructure + 4 critical patterns (Reflection, Agents-as-Tools, Sequential, Parallel)
- ✅ 1,134+ tests passing (100% success rate)
- ✅ Production middleware ready
- ✅ Full observability (OpenTelemetry integration)
- ✅ Multiple transports (HTTP, gRPC, WebSocket)
- ✅ Deployment manifests included
- ✅ Comprehensive documentation
- 🚀 **Next:** Rust remaining patterns (v0.26.0-v0.27.0)

---

**Ready to build production AI agents?** Visit [agenkit.dev](https://agenkit.dev) or [get started in 5 minutes →](GETTING_STARTED.md)

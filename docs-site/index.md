# Agenkit

**The foundation for AI agents.**

A production-ready framework for building distributed AI agent systems with cross-language support, comprehensive middleware, and full observability.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Go 1.21+](https://img.shields.io/badge/go-1.21+-00ADD8.svg)](https://golang.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Tests: 137/137](https://img.shields.io/badge/tests-137%2F137%20passing-brightgreen.svg)](https://github.com/scttfrdmn/agenkit/tree/main/tests)

---

## 🎉 Production Ready

All 5 development phases complete:

- ✅ **Phase 1:** Foundation & Core (100%)
- ✅ **Phase 2:** Transport Layer (100%)
- ✅ **Phase 3:** Middleware & Resilience (100%)
- ✅ **Phase 4:** Testing & Quality (100% - 137/137 tests passing)
- ✅ **Phase 5:** DevOps & Release (100% - Docker + Kubernetes ready)

---

## ✨ Key Features

### Core Capabilities
- **🏗️ Minimal, Type-Safe Interfaces** - Agent, Message, Tool primitives
- **🔄 Orchestration Patterns** - Sequential, Parallel, Router, Fallback, Conditional
- **🌐 Cross-Language Support** - Python ↔ Go with full compatibility
- **🚀 Multiple Transports** - HTTP, gRPC, WebSocket
- **🛡️ Production Middleware** - Circuit breaker, retry, timeout, rate limiting, caching, batching
- **📊 Full Observability** - OpenTelemetry tracing, Prometheus metrics, structured logging
- **🐳 Container Ready** - Docker images and Kubernetes manifests
- **⚡ High Performance** - <1% overhead, benchmarked and optimized

---

## 🚀 Quick Start

=== "Python"

    ```bash
    # Install
    pip install agenkit
    ```

    ```python
    from agenkit import Agent, Message

    # Create a simple agent
    class MyAgent(Agent):
        @property
        def name(self) -> str:
            return "my-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["text-processing"]

        async def process(self, message: Message) -> Message:
            return Message(
                role="agent",
                content=f"Processed: {message.content}"
            )

    # Use it
    agent = MyAgent()
    response = await agent.process(Message(role="user", content="Hello!"))
    print(response.content)  # "Processed: Hello!"
    ```

=== "Go"

    ```bash
    # Install
    go get github.com/agenkit/agenkit-go
    ```

    ```go
    package main

    import (
        "context"
        "fmt"
        "github.com/agenkit/agenkit-go/agenkit"
    )

    type MyAgent struct{}

    func (a *MyAgent) Name() string {
        return "my-agent"
    }

    func (a *MyAgent) Capabilities() []string {
        return []string{"text-processing"}
    }

    func (a *MyAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
        return &agenkit.Message{
            Role:    "agent",
            Content: fmt.Sprintf("Processed: %s", msg.Content),
        }, nil
    }

    func main() {
        agent := &MyAgent{}
        msg := &agenkit.Message{Role: "user", Content: "Hello!"}
        response, _ := agent.Process(context.Background(), msg)
        fmt.Println(response.Content) // "Processed: Hello!"
    }
    ```

=== "Docker"

    ```bash
    # Start full stack (agents + observability)
    docker-compose up -d

    # Access services
    # - Python agent: http://localhost:8080
    # - Go agent: http://localhost:8081
    # - Jaeger UI: http://localhost:16686
    # - Prometheus: http://localhost:9090
    ```

---

## 📚 Learn More

<div class="grid cards" markdown>

-   :material-lightning-bolt-circle:{ .lg .middle } __Getting Started__

    ---

    New to Agenkit? Start here to learn the basics and build your first agent.

    [:octicons-arrow-right-24: Get started](getting-started/index.md)

-   :material-layers-triple:{ .lg .middle } __Architecture__

    ---

    Understand the layered architecture and design principles behind Agenkit.

    [:octicons-arrow-right-24: Learn architecture](core-concepts/architecture.md)

-   :material-book-open-variant:{ .lg .middle } __Guides__

    ---

    Step-by-step guides for Python, Go, cross-language communication, and deployment.

    [:octicons-arrow-right-24: Browse guides](guides/index.md)

-   :material-rocket-launch:{ .lg .middle } __Examples__

    ---

    28+ comprehensive examples covering all features and patterns.

    [:octicons-arrow-right-24: View examples](examples/index.md)

</div>

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  (Your agents, tools, and business logic)                   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                  Middleware Layer                            │
│  Circuit Breaker • Retry • Timeout • Rate Limiter           │
│  Caching • Batching • Tracing • Metrics                     │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                  Transport Layer                             │
│  HTTP • gRPC • WebSocket • Protocol Adapters                │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                   Core Interfaces                            │
│  Agent • Message • Tool • Patterns                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Performance

Agenkit is designed for production use with minimal overhead:

- **Go HTTP:** 18.5x faster than Python (0.055ms vs 1.02ms)
- **Middleware overhead:** <0.01% of total request time
- **Transport overhead:** <1% in realistic LLM workloads
- **Message scaling:** 10,000x size = 190x latency (excellent efficiency)

[View detailed benchmarks →](performance/benchmarks.md)

---

## 🧪 Testing

Comprehensive test coverage with **137/137 tests passing (100%)**:

- **47 tests** - Cross-language integration (Python ↔ Go)
- **53 tests** - Chaos engineering (network failures, crashes, slow responses)
- **37 tests** - Property-based testing (invariant validation)

---

## 🤝 Contributing

We welcome contributions! Check out our [contributing guide](contributing.md) to get started.

---

## 📄 License

Apache License 2.0 - See [LICENSE](https://github.com/scttfrdmn/agenkit/blob/main/LICENSE) for details.

---

## 🔗 Links

- **GitHub:** [github.com/scttfrdmn/agenkit](https://github.com/scttfrdmn/agenkit)
- **Issues:** [Report a bug](https://github.com/scttfrdmn/agenkit/issues)
- **Discussions:** [Join the discussion](https://github.com/scttfrdmn/agenkit/discussions)

---

Built with ❤️ by the Agenkit team

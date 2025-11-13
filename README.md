# Agenkit

**The foundation for AI agents.**

A production-ready framework for building distributed AI agent systems with cross-language support, comprehensive middleware, and full observability.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Go 1.21+](https://img.shields.io/badge/go-1.21+-00ADD8.svg)](https://golang.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Tests: 137/137](https://img.shields.io/badge/tests-137%2F137%20passing-brightgreen.svg)](tests/)

## Status

🎉 **Production Ready** - All 5 Phases Complete! 🎉

- ✅ Phase 1: Foundation & Core (100%)
- ✅ Phase 2: Transport Layer (100%)
- ✅ Phase 3: Middleware & Resilience (100%)
- ✅ Phase 4: Testing & Quality (100% - 137/137 tests passing)
- ✅ Phase 5: DevOps & Release (100% - Docker + Kubernetes ready)

## Features

### Core Capabilities
- 🏗️ **Minimal, Type-Safe Interfaces** - Agent, Message, Tool primitives
- 🔄 **Orchestration Patterns** - Sequential, Parallel, Router, Fallback, Conditional
- 🌐 **Cross-Language Support** - Python ↔ Go with full compatibility
- 🚀 **Multiple Transports** - HTTP, gRPC, WebSocket
- 🛡️ **Production Middleware** - Circuit breaker, retry, timeout, rate limiting, caching, batching
- 📊 **Full Observability** - OpenTelemetry tracing, Prometheus metrics, structured logging
- 🐳 **Container Ready** - Docker images and Kubernetes manifests
- ⚡ **High Performance** - <1% overhead, benchmarked and optimized

### Transport Layer
- **HTTP/1.1, HTTP/2, HTTP/3** - Full HTTP stack support
- **gRPC** - Efficient binary protocol for microservices
- **WebSocket** - Bidirectional streaming communication
- **Protocol Adapters** - Consistent interface across all transports

### Middleware Stack
- **Circuit Breaker** - Fail-fast pattern with automatic recovery
- **Retry** - Exponential backoff with jitter
- **Timeout** - Request deadline enforcement
- **Rate Limiter** - Token bucket algorithm
- **Caching** - LRU cache with TTL support
- **Batching** - Request aggregation for efficiency
- **Observability** - Tracing and metrics integration

### Production Ready
- **137 Tests** - Comprehensive test coverage
  - 47 cross-language integration tests
  - 53 chaos engineering tests
  - 37 property-based tests
- **Security** - Non-root containers, dropped capabilities, TLS support
- **Scalability** - Kubernetes HPA with 3-10 replica autoscaling
- **Monitoring** - Jaeger tracing + Prometheus metrics
- **Documentation** - Comprehensive guides and examples

## Quick Start

### Python

```bash
# Install
pip install agenkit

# Or install from source with development dependencies
pip install -e ".[dev]"
```

```python
from agenkit import Agent, Message
from agenkit.adapters.python.remote_agent import RemoteAgent

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

### Go

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

### Docker

```bash
# Start full stack (agents + observability)
docker-compose up -d

# Access services
# - Python agent: http://localhost:8080
# - Go agent: http://localhost:8081
# - Jaeger UI: http://localhost:16686
# - Prometheus: http://localhost:9090
```

### Kubernetes

```bash
# Deploy to Kubernetes
kubectl apply -f deploy/kubernetes/namespace.yaml
kubectl apply -f deploy/kubernetes/configmap.yaml
kubectl apply -f deploy/kubernetes/

# Check status
kubectl get pods -n agenkit
```

## Architecture

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

## Examples

We provide 27+ comprehensive examples covering all features:

### Core Patterns
- [Basic Agent](examples/01_basic_agent.py) - Simple agent creation
- [Sequential Pattern](examples/02_sequential_pattern.py) - Pipeline processing
- [Parallel Pattern](examples/03_parallel_pattern.py) - Concurrent execution
- [Router Pattern](examples/04_router_pattern.py) - Conditional dispatch
- [Tool Usage](examples/05_tool_usage.py) - Tool integration
- [Pattern Composition](examples/06_pattern_composition.py) - Complex workflows

### Transport Examples
- [HTTP Transport](examples/transport/http_example.py) - HTTP communication
- [gRPC Transport](examples/transport/grpc_example.py) - gRPC communication
- [WebSocket Transport](examples/transport/websocket_example.py) - Bidirectional streaming

### Middleware Examples
- [Circuit Breaker](examples/middleware/circuit_breaker_example.py)
- [Retry Logic](examples/middleware/retry_example.py)
- [Timeout Control](examples/middleware/timeout_example.py)
- [Rate Limiting](examples/middleware/rate_limiter_example.py)
- [Caching](examples/middleware/caching_example.py)
- [Batching](examples/middleware/batching_example.py)

### Advanced Topics
- [Observability](examples/observability/observability_example.py) - Tracing and metrics
- [Remote Agents](examples/adapters/01_basic_remote_agent.py) - Cross-process communication
- [Streaming](examples/adapters/03_streaming.py) - Stream processing

See [examples/README.md](examples/README.md) for the complete list.

## Performance

Agenkit is designed for production use with minimal overhead:

### Transport Performance
- **Go HTTP**: 18.5x faster than Python (0.055ms vs 1.02ms)
- **HTTP/2 vs HTTP/1.1**: <2% difference
- **HTTP/3**: Excellent for concurrent workloads (21% faster)
- **Message Scaling**: 10,000x size = 190x latency (excellent efficiency)

### Middleware Overhead
- **Circuit Breaker**: 14.6µs per request (Python), 10.0µs (Go)
- **Retry**: 0.9µs per request (Python), 0.8µs (Go)
- **Timeout**: 2.1µs per request (Python), 1.5µs (Go)
- **Rate Limiter**: 4.0µs per request (Python), 2.5µs (Go)

### Production Impact
- **Transport overhead**: <1% of total time in realistic LLM workloads
- **Middleware overhead**: <0.01% of total request time
- **Memory efficient**: Streaming with minimal buffering

See [benchmarks/BASELINES.md](benchmarks/BASELINES.md) for detailed performance data.

## Testing

Comprehensive test coverage with 137/137 tests passing:

```bash
# Run all tests
pytest tests/

# Run specific test suites
pytest tests/integration/ -m cross_language  # Cross-language tests
pytest tests/chaos/ -m chaos                 # Chaos engineering
pytest tests/property/ -m property           # Property-based tests

# Run with coverage
pytest tests/ --cov=agenkit --cov-report=html
```

### Test Categories
- **Integration Tests** (47 tests): Python ↔ Go cross-language compatibility
- **Chaos Tests** (53 tests): Network failures, service crashes, slow responses
- **Property Tests** (37 tests): Invariant validation with Hypothesis

## Deployment

### Docker

Build and run with Docker:

```bash
# Build images
docker build -f Dockerfile.python -t agenkit/python:0.1.0 .
docker build -f Dockerfile.go -t agenkit/go:0.1.0 .

# Run with docker-compose
docker-compose up -d
```

### Kubernetes

Deploy to Kubernetes with production-ready manifests:

```bash
# Apply manifests
kubectl apply -f deploy/kubernetes/

# Enable autoscaling
kubectl apply -f deploy/kubernetes/hpa.yaml

# Configure ingress
kubectl apply -f deploy/kubernetes/ingress.yaml
```

Features:
- **Autoscaling**: 3-10 replicas based on CPU/memory
- **Health Checks**: Liveness and readiness probes
- **Security**: Non-root containers, dropped capabilities
- **Observability**: Prometheus metrics, distributed tracing

See [deploy/README.md](deploy/README.md) for complete deployment guide.

## Observability

Built-in OpenTelemetry integration:

### Distributed Tracing
```python
from agenkit.observability import init_tracing, TracingMiddleware

# Initialize tracing
init_tracing("my-service", otlp_endpoint="http://jaeger:4317")

# Wrap agents
traced_agent = TracingMiddleware(base_agent)
```

### Metrics
```python
from agenkit.observability import init_metrics, MetricsMiddleware

# Initialize metrics (Prometheus)
init_metrics("my-service", port=8001)

# Wrap agents
metered_agent = MetricsMiddleware(base_agent)
```

### Structured Logging
```python
from agenkit.observability import configure_logging

# Configure JSON logging with trace correlation
configure_logging(structured=True, include_trace_context=True)
```

See [docs/observability.md](docs/observability.md) for details.

## Documentation

- **[Architecture](ARCHITECTURE.md)** - System design and principles
- **[API Reference](docs/API.md)** - Complete API documentation
- **[Roadmap](ROADMAP.md)** - Project roadmap and status
- **[Examples](examples/README.md)** - Comprehensive examples
- **[Deployment Guide](deploy/README.md)** - Docker and Kubernetes
- **[Observability](docs/observability.md)** - Tracing and metrics
- **[Security](docs/SECURITY.md)** - Security best practices

## Development

```bash
# Clone repository
git clone https://github.com/agenkit/agenkit.git
cd agenkit

# Install Python dependencies
pip install -e ".[dev]"

# Install Go dependencies
cd agenkit-go && go mod download && cd ..

# Run tests
pytest tests/ -v                    # Python tests
cd agenkit-go && go test ./... && cd ..  # Go tests

# Run benchmarks
pytest benchmarks/ -v --benchmark-only

# Type checking
mypy agenkit/                       # Python
cd agenkit-go && golangci-lint run && cd ..  # Go

# Format code
black agenkit/ tests/ benchmarks/   # Python
ruff check agenkit/ tests/
cd agenkit-go && gofmt -w . && cd ..  # Go
```

## Contributing

We welcome contributions! Please see our contributing guidelines (coming soon).

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite
5. Submit a pull request

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

## Links

- **GitHub**: https://github.com/agenkit/agenkit
- **Documentation**: https://docs.agenkit.dev (coming soon)
- **Issues**: https://github.com/agenkit/agenkit/issues

## Project Stats

- **Code**: ~35,000 lines (Python + Go)
- **Tests**: 137/137 passing (100%)
- **Examples**: 27+ comprehensive examples
- **Documentation**: 25+ guides and references
- **Languages**: Python 3.10+, Go 1.21+
- **Status**: Production Ready ✅

---

Built with ❤️ by the Agenkit team

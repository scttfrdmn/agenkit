# Examples

28+ comprehensive examples covering all Agenkit features.

## Overview

Our examples demonstrate real-world usage patterns with:

- **Complete code** - Ready to run
- **Explanations** - Why, not just what
- **Best practices** - Production patterns
- **Both languages** - Python and Go

---

## Quick Start Examples

New to Agenkit? Start here:

1. **[01_basic_agent.py](https://github.com/scttfrdmn/agenkit/blob/main/examples/01_basic_agent.py)** - Create your first agent
2. **[02_sequential_pattern.py](https://github.com/scttfrdmn/agenkit/blob/main/examples/02_sequential_pattern.py)** - Chain agents in a pipeline
3. **[03_parallel_pattern.py](https://github.com/scttfrdmn/agenkit/blob/main/examples/03_parallel_pattern.py)** - Run agents concurrently

---

## Examples by Category

### Core Patterns (6 examples)

Basic agent creation and composition patterns.

| Example | Description | Python | Go |
|---------|-------------|--------|-----|
| Basic Agent | Simple message processing | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/01_basic_agent.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/basic/main.go) |
| Sequential Pattern | Pipeline processing | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/02_sequential_pattern.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/composition/sequential_example.go) |
| Parallel Pattern | Concurrent execution | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/03_parallel_pattern.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/composition/parallel_example.go) |
| Router Pattern | Conditional dispatch | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/04_router_pattern.py) | - |
| Tool Usage | Tool integration | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/05_tool_usage.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/tools/calculator_example.go) |
| Pattern Composition | Complex workflows | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/06_pattern_composition.py) | - |

### Transport Layer (3 examples)

Cross-process and cross-language communication.

| Example | Description | Python | Go |
|---------|-------------|--------|-----|
| WebSocket | Bidirectional streaming | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/transport/websocket_example.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/transport/websocket_example.go) |
| gRPC | High-performance RPC | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/transport/grpc_example.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/transport/grpc_example.go) |

### Middleware (6 examples)

Production resilience and observability.

| Example | Description | Python | Go |
|---------|-------------|--------|-----|
| Circuit Breaker | Fail-fast pattern | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/middleware/circuit_breaker_example.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/middleware/circuit_breaker_example.go) |
| Retry | Exponential backoff | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/middleware/retry_example.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/middleware/retry_example.go) |
| Timeout | Request deadlines | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/middleware/timeout_example.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/middleware/timeout_example.go) |
| Rate Limiter | Token bucket | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/middleware/rate_limiter_example.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/middleware/rate_limiter_example.go) |
| Caching | LRU cache with TTL | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/middleware/caching_example.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/middleware/caching_example.go) |
| Batching | Request aggregation | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/middleware/batching_example.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/middleware/batching_example.go) |

### Composition Patterns (4 examples)

Advanced multi-agent orchestration.

| Example | Description | Python | Go |
|---------|-------------|--------|-----|
| Sequential | Advanced pipelines | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/composition/sequential_example.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/composition/sequential_example.go) |
| Parallel | Result aggregation | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/composition/parallel_example.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/composition/parallel_example.go) |
| Fallback | High availability | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/composition/fallback_example.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/composition/fallback_example.go) |
| Conditional | Dynamic routing | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/composition/conditional_example.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/composition/conditional_example.go) |

### Tools (4 examples)

Tool integration and function calling.

| Example | Description | Python | Go |
|---------|-------------|--------|-----|
| Calculator | Math operations | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/tools/calculator_example.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/tools/calculator_example.go) |
| Search | External API calls | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/tools/search_example.py) | - |
| Database | Database operations | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/tools/database_example.py) | - |
| OS Tools | File system & processes | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/tools/os_tools_example.py) | - |

### Adapters (3 examples)

Remote agents and streaming.

| Example | Description | Python | Go |
|---------|-------------|--------|-----|
| Basic Remote | Cross-process agents | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/adapters/01_basic_remote_agent.py) | - |
| Agent Registry | Service discovery | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/adapters/02_agent_registry.py) | - |
| Streaming | Stream processing | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/adapters/03_streaming.py) | - |

### Observability (2 examples)

Tracing, metrics, and logging.

| Example | Description | Python | Go |
|---------|-------------|--------|-----|
| Full Stack | Complete observability | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/observability/observability_example.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/observability/observability_example.go) |
| Metrics | Prometheus integration | [📄](https://github.com/scttfrdmn/agenkit/blob/main/examples/middleware/metrics_example.py) | [📄](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/examples/middleware/metrics_example.go) |

---

## Running Examples

### Python

```bash
# Clone repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit

# Install dependencies
pip install -e ".[dev]"

# Run any example
python examples/01_basic_agent.py
python examples/middleware/circuit_breaker_example.py
```

### Go

```bash
# Clone repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/agenkit-go/examples

# Run any example
go run basic/main.go
go run middleware/circuit_breaker_example.go
```

---

## Learning Path

Follow this order for the best learning experience:

### 1. **Fundamentals** (Day 1)
- 01_basic_agent.py
- 02_sequential_pattern.py
- 03_parallel_pattern.py
- 04_router_pattern.py
- 05_tool_usage.py
- 06_pattern_composition.py

### 2. **Transport & Remote** (Day 2)
- adapters/01_basic_remote_agent.py
- transport/grpc_example.py
- transport/websocket_example.py

### 3. **Production Middleware** (Day 3)
- middleware/retry_example.py
- middleware/timeout_example.py
- middleware/circuit_breaker_example.py
- middleware/rate_limiter_example.py
- middleware/caching_example.py
- middleware/batching_example.py

### 4. **Observability** (Day 4)
- middleware/metrics_example.py
- observability/observability_example.py

### 5. **Advanced** (Day 5)
- composition/fallback_example.py
- composition/conditional_example.py
- tools/* (all tool examples)

---

## Example Statistics

- **Total Examples:** 28+ (Python) + 16 (Go) = 44+ examples
- **Lines of Code:** ~6,700 lines with documentation
- **Coverage:** All features demonstrated
- **Maintenance:** Updated with each release

---

## Next Steps

- **Run examples** - Clone the repo and try them out
- **Read guides** - Deepen understanding with [guides](../guides/index.md)
- **Build something** - Use examples as templates
- **Contribute** - Share your examples with the community

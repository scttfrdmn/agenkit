# Agenkit Examples

Comprehensive examples demonstrating all Agenkit features across Python and Go.

## Running Examples

### Python Examples

```bash
# Make sure you're in the project directory
cd /path/to/agenkit

# Run any example
python examples/01_basic_agent.py
python examples/middleware/circuit_breaker_example.py
python examples/transport/websocket_example.py
```

### Go Examples

```bash
# Navigate to Go examples
cd agenkit-go/examples

# Run any example
go run basic/main.go
go run middleware/circuit_breaker_example.go
go run transport/grpc_example.go
```

## Examples by Category

### Core Patterns (6 examples)

### [01_basic_agent.py](01_basic_agent.py)
**Basic Agent Creation**

Learn how to create a simple agent that processes messages.

Key concepts:
- Agent interface
- Message creation
- Async processing

```bash
python examples/01_basic_agent.py
```

---

### [02_sequential_pattern.py](02_sequential_pattern.py)
**Sequential Pattern (Pipeline)**

Chain agents in a pipeline where output of one becomes input of next.

Key concepts:
- SequentialPattern
- Validation → Processing → Formatting pipeline
- Error propagation

```bash
python examples/02_sequential_pattern.py
```

---

### [03_parallel_pattern.py](03_parallel_pattern.py)
**Parallel Pattern (Fan-out)**

Run multiple agents concurrently on the same input.

Key concepts:
- ParallelPattern
- Concurrent execution
- Result aggregation
- Multiple analysis (sentiment, length, keywords)

```bash
python examples/03_parallel_pattern.py
```

---

### [04_router_pattern.py](04_router_pattern.py)
**Router Pattern (Conditional Dispatch)**

Route messages to different agents based on content.

Key concepts:
- RouterPattern
- Intent-based routing
- Specialized agents (weather, news, calculator, general)

```bash
python examples/04_router_pattern.py
```

---

### [05_tool_usage.py](05_tool_usage.py)
**Tool Usage**

Create and use tools within agents.

Key concepts:
- Tool interface
- ToolResult
- Search and calculator tools
- Error handling

```bash
python examples/05_tool_usage.py
```

---

### [06_pattern_composition.py](06_pattern_composition.py)
**Pattern Composition**

Compose patterns to create complex workflows.

Key concepts:
- Patterns of patterns
- Sequential [ Parallel [ ... ], Router { ... } ]
- Metadata propagation
- Multi-stage processing

```bash
python examples/06_pattern_composition.py
```

---

### Transport Layer (3 examples)

#### [transport/websocket_example.py](transport/websocket_example.py)
**WebSocket Transport**

Bidirectional streaming communication between agents.

Key concepts:
- WebSocket transport protocol
- Real-time bidirectional messaging
- Connection lifecycle management

```bash
python examples/transport/websocket_example.py
```

---

#### [transport/grpc_example.py](transport/grpc_example.py)
**gRPC Transport**

High-performance binary protocol for microservices.

Key concepts:
- gRPC transport protocol
- Protocol Buffers serialization
- Cross-language agent communication

```bash
python examples/transport/grpc_example.py
```

---

### Middleware (6 examples)

#### [middleware/circuit_breaker_example.py](middleware/circuit_breaker_example.py)
**Circuit Breaker Middleware**

Fail-fast pattern with automatic recovery.

Key concepts:
- Circuit breaker states (closed, open, half-open)
- Failure threshold detection
- Automatic recovery

```bash
python examples/middleware/circuit_breaker_example.py
```

---

#### [middleware/retry_example.py](middleware/retry_example.py)
**Retry Middleware**

Exponential backoff with jitter for transient failures.

Key concepts:
- Automatic retry on failure
- Exponential backoff algorithm
- Jitter for distributed systems

```bash
python examples/middleware/retry_example.py
```

---

#### [middleware/timeout_example.py](middleware/timeout_example.py)
**Timeout Middleware**

Request deadline enforcement.

Key concepts:
- Timeout configuration
- Graceful timeout handling
- Deadline propagation

```bash
python examples/middleware/timeout_example.py
```

---

#### [middleware/rate_limiter_example.py](middleware/rate_limiter_example.py)
**Rate Limiter Middleware**

Token bucket algorithm for request rate control.

Key concepts:
- Token bucket algorithm
- Rate limiting per time window
- Backpressure handling

```bash
python examples/middleware/rate_limiter_example.py
```

---

#### [middleware/caching_example.py](middleware/caching_example.py)
**Caching Middleware**

LRU cache with TTL support.

Key concepts:
- LRU eviction policy
- TTL (time-to-live) expiration
- Cache key generation

```bash
python examples/middleware/caching_example.py
```

---

#### [middleware/batching_example.py](middleware/batching_example.py)
**Batching Middleware**

Request aggregation for improved efficiency.

Key concepts:
- Request batching
- Batch size and timeout configuration
- Response distribution

```bash
python examples/middleware/batching_example.py
```

---

### Composition Patterns (4 examples)

#### [composition/sequential_example.py](composition/sequential_example.py)
**Sequential Composition**

Advanced sequential pattern with error handling.

Key concepts:
- Sequential agent chaining
- Error propagation
- Pipeline composition

```bash
python examples/composition/sequential_example.py
```

---

#### [composition/parallel_example.py](composition/parallel_example.py)
**Parallel Composition**

Advanced parallel execution with result aggregation.

Key concepts:
- Concurrent agent execution
- Result aggregation strategies
- Fan-out patterns

```bash
python examples/composition/parallel_example.py
```

---

#### [composition/fallback_example.py](composition/fallback_example.py)
**Fallback Pattern**

Automatic fallback to alternative agents on failure.

Key concepts:
- Primary and fallback agents
- Automatic failover
- Resilience patterns

```bash
python examples/composition/fallback_example.py
```

---

#### [composition/conditional_example.py](composition/conditional_example.py)
**Conditional Pattern**

Dynamic agent selection based on conditions.

Key concepts:
- Conditional routing
- Dynamic agent selection
- Context-aware execution

```bash
python examples/composition/conditional_example.py
```

---

### Tools (4 examples)

#### [tools/calculator_example.py](tools/calculator_example.py)
**Calculator Tool**

Mathematical operations tool integration.

Key concepts:
- Tool interface implementation
- Synchronous tool execution
- Error handling

```bash
python examples/tools/calculator_example.py
```

---

#### [tools/search_example.py](tools/search_example.py)
**Search Tool**

Search functionality integration.

Key concepts:
- Async tool execution
- External API integration
- Result formatting

```bash
python examples/tools/search_example.py
```

---

#### [tools/database_example.py](tools/database_example.py)
**Database Tool**

Database operations tool integration.

Key concepts:
- Database connections
- Query execution
- Transaction handling

```bash
python examples/tools/database_example.py
```

---

#### [tools/os_tools_example.py](tools/os_tools_example.py)
**OS Tools**

Operating system operations integration.

Key concepts:
- File system operations
- Process management
- System information

```bash
python examples/tools/os_tools_example.py
```

---

### Adapters (3 examples)

#### [adapters/01_basic_remote_agent.py](adapters/01_basic_remote_agent.py)
**Basic Remote Agent**

Remote agent communication basics.

Key concepts:
- RemoteAgent wrapper
- Cross-process communication
- Transport abstraction

```bash
python examples/adapters/01_basic_remote_agent.py
```

---

#### [adapters/02_agent_registry.py](adapters/02_agent_registry.py)
**Agent Registry**

Centralized agent discovery and management.

Key concepts:
- Agent registration
- Service discovery
- Registry patterns

```bash
python examples/adapters/02_agent_registry.py
```

---

#### [adapters/03_streaming.py](adapters/03_streaming.py)
**Streaming Agents**

Stream processing with agents.

Key concepts:
- Async streaming
- Backpressure handling
- Stream composition

```bash
python examples/adapters/03_streaming.py
```

---

### Observability (2 examples)

#### [observability/observability_example.py](observability/observability_example.py)
**Full Observability Stack**

OpenTelemetry tracing and Prometheus metrics.

Key concepts:
- Distributed tracing with OpenTelemetry
- W3C Trace Context propagation
- Prometheus metrics collection
- Trace correlation

```bash
python examples/observability/observability_example.py
```

---

#### [middleware/metrics_example.py](middleware/metrics_example.py)
**Metrics Middleware**

Prometheus metrics integration.

Key concepts:
- Metrics middleware
- Custom metric collection
- Metrics export

```bash
python examples/middleware/metrics_example.py
```

---

## Learning Path

We recommend following the examples in this order:

### 1. Fundamentals
Start with these core examples to understand the basics:
1. **01_basic_agent.py** - Basic agent creation and message processing
2. **02_sequential_pattern.py** - Chain agents in a pipeline
3. **03_parallel_pattern.py** - Run agents concurrently
4. **04_router_pattern.py** - Conditional agent routing
5. **05_tool_usage.py** - Tool integration
6. **06_pattern_composition.py** - Compose patterns together

### 2. Transport & Remote Agents
Learn cross-process and cross-language communication:
1. **adapters/01_basic_remote_agent.py** - Remote agent basics
2. **transport/grpc_example.py** - gRPC transport
3. **transport/websocket_example.py** - WebSocket transport
4. **adapters/03_streaming.py** - Stream processing

### 3. Production Middleware
Add resilience and production features:
1. **middleware/retry_example.py** - Retry with exponential backoff
2. **middleware/timeout_example.py** - Timeout enforcement
3. **middleware/circuit_breaker_example.py** - Circuit breaker pattern
4. **middleware/rate_limiter_example.py** - Rate limiting
5. **middleware/caching_example.py** - Response caching
6. **middleware/batching_example.py** - Request batching

### 4. Observability
Add monitoring and tracing:
1. **middleware/metrics_example.py** - Prometheus metrics
2. **observability/observability_example.py** - Full observability stack

### 5. Advanced Patterns
Explore advanced composition and tools:
1. **composition/fallback_example.py** - Fallback pattern
2. **composition/conditional_example.py** - Conditional routing
3. **tools/** - Various tool integrations

## Go Examples

All Python examples have Go equivalents in `agenkit-go/examples/`. The Go examples demonstrate:
- Full Python ↔ Go cross-language compatibility
- Same API patterns and idioms
- Performance-optimized implementations
- Production-ready error handling

Example Go usage:
```bash
cd agenkit-go/examples
go run basic/main.go
go run middleware/circuit_breaker_example.go
go run transport/grpc_example.go
```

## Example Statistics

- **Total Examples**: 26 Python + 16 Go = 42 examples
- **Core Patterns**: 6 examples
- **Transport Layer**: 3 examples
- **Middleware**: 6 examples
- **Composition**: 4 examples
- **Tools**: 4 examples
- **Adapters**: 3 examples
- **Observability**: 2 examples

## Next Steps

- Read the [API Documentation](../docs/API.md) for detailed reference
- Check out [Architecture](../ARCHITECTURE.md) for design principles
- See [Deployment Guide](../deploy/README.md) for Docker/Kubernetes
- Review [Observability](../docs/observability.md) for monitoring
- Check [Performance Benchmarks](../benchmarks/BASELINES.md) for metrics
- Explore [Cross-Language Integration](../tests/integration/) for Python ↔ Go

## Need Help?

- Review the main [README](../README.md) for project overview
- Check [ROADMAP](../ROADMAP.md) for project status
- Browse [tests/](../tests/) for more usage examples (137 tests)
- Open an issue on [GitHub](https://github.com/agenkit/agenkit/issues)

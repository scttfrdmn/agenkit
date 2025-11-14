# Features

Explore Agenkit's comprehensive feature set.

## Overview

Agenkit provides production-ready features organized into five categories:

<div class="grid cards" markdown>

-   :material-transit-connection-variant:{ .lg .middle } __Transport Layer__

    ---

    Connect agents across processes and languages with HTTP, gRPC, and WebSocket.

    [:octicons-arrow-right-24: Learn more](transport.md)

-   :material-shield-check:{ .lg .middle } __Middleware__

    ---

    Add resilience, caching, rate limiting, and observability with composable middleware.

    [:octicons-arrow-right-24: Learn more](middleware.md)

-   :material-lan:{ .lg .middle } __Composition__

    ---

    Orchestrate multiple agents into workflows with sequential, parallel, and router patterns.

    [:octicons-arrow-right-24: Learn more](composition.md)

-   :material-chart-line:{ .lg .middle } __Observability__

    ---

    Full OpenTelemetry integration with distributed tracing and Prometheus metrics.

    [:octicons-arrow-right-24: Learn more](observability.md)

-   :material-robot:{ .lg .middle } __LLM Adapters__

    ---

    Connect to any LLM provider with a consistent interface. Swap providers with one line.

    [:octicons-arrow-right-24: Learn more](llm-adapters.md)

-   :material-tools:{ .lg .middle } __Tools__

    ---

    Extend agents with executable tools for deterministic operations.

    [:octicons-arrow-right-24: Learn more](tools.md)

</div>

---

## Feature Matrix

| Feature | Python | Go | Cross-Language |
|---------|--------|-----|----------------|
| **Transport Layer** | | | |
| HTTP/1.1 | ✅ | ✅ | ✅ |
| HTTP/2 | ✅ | ✅ | ✅ |
| HTTP/3 (QUIC) | ✅ | ✅ | ✅ |
| gRPC | ✅ | ✅ | ✅ |
| WebSocket | ✅ | ✅ | ✅ |
| **Middleware** | | | |
| Retry | ✅ | ✅ | N/A |
| Circuit Breaker | ✅ | ✅ | N/A |
| Timeout | ✅ | ✅ | N/A |
| Rate Limiter | ✅ | ✅ | N/A |
| Caching (LRU) | ✅ | ✅ | N/A |
| Batching | ✅ | ✅ | N/A |
| **Composition** | | | |
| Sequential | ✅ | ✅ | ✅ |
| Parallel | ✅ | ✅ | ✅ |
| Fallback | ✅ | ✅ | ✅ |
| Conditional | ✅ | ✅ | ✅ |
| **Observability** | | | |
| OpenTelemetry Tracing | ✅ | ✅ | ✅ |
| W3C Trace Context | ✅ | ✅ | ✅ |
| Prometheus Metrics | ✅ | ✅ | ✅ |
| Structured Logging | ✅ | ✅ | ✅ |
| **LLM Adapters** | | | |
| Anthropic (Claude) | ✅ | ⏳ | N/A |
| OpenAI (GPT) | ✅ | ⏳ | N/A |
| Google Gemini | ✅ | ⏳ | N/A |
| AWS Bedrock | ✅ | ⏳ | N/A |
| Ollama (Local) | ✅ | ⏳ | N/A |
| LiteLLM (100+ providers) | ✅ | ⏳ | N/A |
| **Tools** | | | |
| Tool Interface | ✅ | ✅ | N/A |
| Tool Registry | ✅ | ✅ | N/A |

---

## Quick Examples

### Transport Layer

```python
# HTTP
agent = RemoteAgent(name="api", endpoint="http://localhost:8080")

# gRPC
agent = RemoteAgent(name="api", endpoint="grpc://localhost:50051")

# WebSocket
agent = RemoteAgent(name="api", endpoint="ws://localhost:8080")
```

### Middleware

```python
# Stack middleware
agent = MyAgent()
agent = CachingDecorator(agent, max_size=1000)
agent = RetryDecorator(agent, max_attempts=3)
agent = CircuitBreaker(agent)
agent = TimeoutDecorator(agent, timeout=30.0)
```

### Composition

```python
# Sequential pipeline
pipeline = SequentialAgent([validator, processor, formatter])

# Parallel analysis
analysis = ParallelAgent([sentiment, summary, entities])

# Router
router = ConditionalAgent(
    agents=[weather_agent, news_agent, general_agent],
    condition=route_function
)
```

### Observability

```python
# Initialize tracing and metrics
init_tracing("my-service", otlp_endpoint="http://jaeger:4317")
init_metrics("my-service", port=8001)

# Wrap agent
agent = TracingMiddleware(MetricsMiddleware(MyAgent()))
```

### LLM Adapters

```python
from agenkit.adapters.llm import AnthropicLLM, OpenAILLM, GeminiLLM

# Use Anthropic
llm = AnthropicLLM(api_key="sk-ant-...")

# Swap to OpenAI (same interface!)
llm = OpenAILLM(api_key="sk-...")

# Or try Gemini
llm = GeminiLLM(api_key="...")

# All use the same interface
response = await llm.complete(messages)
```

---

## Performance

All features are designed for production use with minimal overhead:

- **Transport overhead:** <1% in realistic workloads
- **Middleware overhead:** <0.01% per middleware
- **Composition overhead:** <5% for sequential/parallel
- **Observability overhead:** <2% with tracing enabled

[View detailed benchmarks →](../performance/benchmarks.md)

---

## Next Steps

- **[Transport Layer](transport.md)** - Connect agents across boundaries
- **[Middleware](middleware.md)** - Add production resilience
- **[Composition](composition.md)** - Build multi-agent workflows
- **[Observability](observability.md)** - Monitor and debug
- **[LLM Adapters](llm-adapters.md)** - Connect to any LLM provider
- **[Tools](tools.md)** - Extend agent capabilities

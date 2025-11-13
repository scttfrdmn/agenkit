# Observability Guide

Agenkit provides comprehensive observability features built on [OpenTelemetry](https://opentelemetry.io/), enabling distributed tracing, metrics collection, and structured logging for your AI agent applications.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
  - [Python](#python-quick-start)
  - [Go](#go-quick-start)
- [Distributed Tracing](#distributed-tracing)
- [Metrics Collection](#metrics-collection)
- [Structured Logging](#structured-logging)
- [Cross-Language Compatibility](#cross-language-compatibility)
- [Configuration](#configuration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

Agenkit's observability features help you:

- **Trace agent interactions** across your application with distributed tracing
- **Monitor performance** with Prometheus-compatible metrics
- **Debug issues** with structured, trace-correlated logs
- **Understand behavior** across polyglot (Python/Go) agent systems

All observability features use OpenTelemetry, the industry-standard observability framework, ensuring compatibility with popular backends like Jaeger, Zipkin, Prometheus, and Grafana.

## Features

### Distributed Tracing
- Automatic span creation for agent processing
- W3C Trace Context propagation across agents and languages
- Parent-child span relationships
- Error recording and status tracking
- Custom span names and attributes

### Metrics Collection
- Request counters (total requests, success/error)
- Latency histograms (processing time distribution)
- Message size tracking
- Error rates by agent and error type
- Prometheus-compatible export

### Structured Logging
- JSON structured logging format
- Automatic trace context injection (trace_id, span_id)
- Configurable log levels
- Compatible formats across Python and Go

## Quick Start

### Python Quick Start

```python
import asyncio
from agenkit.observability import (
    init_tracing,
    init_metrics,
    configure_logging,
    TracingMiddleware,
    MetricsMiddleware,
)
from agenkit.interfaces import Agent, Message
import logging

# 1. Initialize observability
init_tracing(
    service_name="my-agent-service",
    console_export=True,  # For development
    # otlp_endpoint="localhost:4317",  # For production
)

init_metrics(
    service_name="my-agent-service",
    port=8001,  # Prometheus metrics endpoint
)

configure_logging(
    level=logging.INFO,
    structured=True,
    include_trace_context=True,
)

# 2. Wrap your agent with observability middleware
class MyAgent(Agent):
    @property
    def name(self) -> str:
        return "my-agent"

    @property
    def capabilities(self) -> list[str]:
        return ["process"]

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Processed: {message.content}")

# Create agent with observability
base_agent = MyAgent()
traced_agent = TracingMiddleware(base_agent)
monitored_agent = MetricsMiddleware(traced_agent)

# 3. Process messages - observability happens automatically!
async def main():
    message = Message(role="user", content="Hello!")
    response = await monitored_agent.process(message)
    print(response.content)

asyncio.run(main())
```

View metrics at: `http://localhost:8001/metrics`

### Go Quick Start

```go
package main

import (
    "context"
    "fmt"
    "log/slog"

    "github.com/agenkit/agenkit-go/observability"
)

func main() {
    // 1. Initialize observability
    tp, err := observability.InitTracing(
        "my-agent-service",
        "",    // No OTLP endpoint for dev
        true,  // Console export for dev
    )
    if err != nil {
        panic(err)
    }
    defer observability.Shutdown(context.Background())

    mp, err := observability.InitMetrics(
        "my-agent-service",
        8002,  // Prometheus metrics endpoint
    )
    if err != nil {
        panic(err)
    }
    defer observability.ShutdownMetrics(context.Background())

    observability.ConfigureLogging(
        slog.LevelInfo,
        true,  // Structured JSON
        true,  // Include trace context
    )

    // 2. Wrap your agent with observability middleware
    baseAgent := &MyAgent{}
    tracedAgent := observability.NewTracingMiddleware(baseAgent, "")
    monitoredAgent, err := observability.NewMetricsMiddleware(tracedAgent)
    if err != nil {
        panic(err)
    }

    // 3. Process messages - observability happens automatically!
    ctx := context.Background()
    message := &observability.Message{
        Role:    "user",
        Content: "Hello!",
    }

    response, err := monitoredAgent.Process(ctx, message)
    if err != nil {
        panic(err)
    }

    fmt.Println(response.Content)
}
```

View metrics at: `http://localhost:8002/metrics`

## Distributed Tracing

### How It Works

Tracing creates a hierarchical view of your agent's execution:

```
Request
└── agent.agent1.process (span)
    ├── agent.agent2.process (child span)
    └── agent.agent3.process (child span)
```

Each span records:
- **Duration**: How long the operation took
- **Attributes**: Agent name, message role, content length, metadata
- **Status**: Success or error
- **Events**: Exceptions and other notable events

### Trace Context Propagation

Agenkit automatically propagates trace context across agents using W3C Trace Context:

```python
# Python example
response1 = await agent1.process(message)
# Trace context automatically included in response1.metadata

response2 = await agent2.process(response1)
# agent2's span is a child of agent1's span
```

This works **across languages** - Python agents can call Go agents and maintain trace continuity.

### Custom Span Names

```python
# Python
traced_agent = TracingMiddleware(agent, span_name="custom.operation")
```

```go
// Go
tracedAgent := observability.NewTracingMiddleware(agent, "custom.operation")
```

### Exporting Traces

#### Development: Console Export

```python
init_tracing(service_name="my-service", console_export=True)
```

```go
observability.InitTracing("my-service", "", true)
```

#### Production: OTLP Export

```python
init_tracing(
    service_name="my-service",
    otlp_endpoint="localhost:4317",  # Jaeger, Tempo, etc.
)
```

```go
observability.InitTracing("my-service", "localhost:4317", false)
```

## Metrics Collection

### Available Metrics

Agenkit automatically collects these metrics:

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `agenkit.agent.requests` | Counter | Total requests processed | `agent.name`, `message.role`, `status` |
| `agenkit.agent.errors` | Counter | Total errors encountered | `agent.name`, `status`, `error.type` |
| `agenkit.agent.latency` | Histogram | Processing latency in ms | `agent.name`, `message.role`, `status` |
| `agenkit.agent.message_size` | Histogram | Message content size in bytes | `agent.name`, `message.role` |

### Viewing Metrics

Metrics are exposed in Prometheus format:

```bash
# Python (port 8001 by default)
curl http://localhost:8001/metrics

# Go (port 8002 by default)
curl http://localhost:8002/metrics
```

### Example Prometheus Queries

```promql
# Request rate by agent
rate(agenkit_agent_requests_total[5m])

# Error rate
rate(agenkit_agent_errors_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(agenkit_agent_latency_bucket[5m]))

# Average message size
rate(agenkit_agent_message_size_sum[5m]) / rate(agenkit_agent_message_size_count[5m])
```

### Prometheus Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'agenkit-python'
    static_configs:
      - targets: ['localhost:8001']

  - job_name: 'agenkit-go'
    static_configs:
      - targets: ['localhost:8002']
```

## Structured Logging

### Basic Usage

```python
# Python
from agenkit.observability import configure_logging, get_logger_with_trace

configure_logging(
    level=logging.INFO,
    structured=True,
    include_trace_context=True,
)

logger = get_logger_with_trace(__name__)
logger.info("Processing message", extra={"user_id": "123"})
```

```go
// Go
observability.ConfigureLogging(slog.LevelInfo, true, true)

logger := observability.GetLoggerWithTrace()
logger.Info("Processing message", slog.String("user_id", "123"))
```

### Log Format

Structured logs are output in JSON format:

```json
{
  "timestamp": "2025-11-12T20:00:00Z",
  "level": "INFO",
  "message": "Processing message",
  "trace_id": "8a89f6ecb04b04d023cc690961850547",
  "span_id": "5782371d5170d9e5",
  "user_id": "123"
}
```

### Correlating Logs with Traces

The automatic inclusion of `trace_id` and `span_id` allows you to:

1. **Find logs for a specific trace**: Search logs by `trace_id`
2. **Jump from logs to traces**: Click trace_id to view the full trace
3. **Debug issues**: See exactly what happened during a failed span

## Cross-Language Compatibility

Agenkit's observability features are designed for polyglot systems:

### Trace Propagation

```python
# Python agent
response = await python_agent.process(message)
# Trace context in response.metadata["trace_context"]
```

```go
// Go agent receives the same message
response, err := goAgent.Process(ctx, message)
// Continues the same trace!
```

### Compatible Formats

- **Trace Context**: W3C Trace Context standard
- **Metrics**: Prometheus exposition format
- **Logs**: JSON structured logging

### Example: Python → Go Chain

```python
# agent1 (Python)
traced_agent1 = TracingMiddleware(PythonAgent())

# agent2 (Go)
traced_agent2 = observability.NewTracingMiddleware(GoAgent(), "")

# Process through chain
response1 = await traced_agent1.process(message)
response2 = traced_agent2.Process(ctx, response1)

# Both spans share the same trace_id!
```

## Configuration

### Environment Variables

You can configure observability using environment variables:

```bash
# Service name
export OTEL_SERVICE_NAME=my-agent-service

# OTLP endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Log level
export LOG_LEVEL=INFO
```

### Python Configuration

```python
# Detailed tracing configuration
init_tracing(
    service_name="my-service",
    otlp_endpoint="localhost:4317",  # Optional: OTLP collector
    console_export=False,            # Optional: Console output
)

# Detailed metrics configuration
init_metrics(
    service_name="my-service",
    port=8001,  # Prometheus port
)

# Detailed logging configuration
configure_logging(
    level=logging.INFO,      # Log level
    structured=True,         # JSON format
    include_trace_context=True,  # Add trace IDs
)
```

### Go Configuration

```go
// Detailed tracing configuration
tp, err := observability.InitTracing(
    "my-service",          // Service name
    "localhost:4317",      // OTLP endpoint (empty for none)
    false,                 // Console export
)

// Detailed metrics configuration
mp, err := observability.InitMetrics(
    "my-service",  // Service name
    8002,          // Prometheus port
)

// Detailed logging configuration
observability.ConfigureLogging(
    slog.LevelInfo,  // Log level
    true,            // Structured (JSON)
    true,            // Include trace context
)
```

## Best Practices

### 1. Initialize Early

Initialize observability at application startup, before creating agents:

```python
# ✅ Good
init_tracing(...)
init_metrics(...)
configure_logging(...)

agent = create_agent()
```

```python
# ❌ Bad
agent = create_agent()
init_tracing(...)  # Too late!
```

### 2. Layer Middleware Correctly

Apply middleware in this order:

```python
# ✅ Correct order
base_agent = MyAgent()
traced_agent = TracingMiddleware(base_agent)     # Tracing first
monitored_agent = MetricsMiddleware(traced_agent) # Metrics second
```

### 3. Use Meaningful Service Names

```python
# ✅ Good
init_tracing(service_name="recommendation-agent")
init_tracing(service_name="search-agent")

# ❌ Bad
init_tracing(service_name="service")
init_tracing(service_name="agent1")
```

### 4. Include Context in Logs

```python
# ✅ Good
logger.info("Processing request", extra={
    "user_id": user_id,
    "request_id": request_id,
    "agent": agent.name,
})

# ❌ Bad
logger.info(f"Processing request for {user_id}")
```

### 5. Handle Shutdown Gracefully

```python
# Python
import atexit
from opentelemetry.sdk.trace import TracerProvider

def shutdown():
    # Flush any pending traces/metrics
    pass

atexit.register(shutdown)
```

```go
// Go
defer observability.Shutdown(context.Background())
defer observability.ShutdownMetrics(context.Background())
```

### 6. Don't Log Sensitive Data

```python
# ✅ Good
logger.info("User authenticated", extra={"user_id": user.id})

# ❌ Bad
logger.info("User authenticated", extra={"password": password})
```

## Troubleshooting

### No Traces Appearing

**Problem**: Traces are not being exported.

**Solutions**:
1. Check that `init_tracing()` was called before processing messages
2. Verify OTLP endpoint is reachable: `telnet localhost 4317`
3. Enable console export for debugging: `init_tracing(..., console_export=True)`
4. Check for errors in application logs

### Metrics Not Updating

**Problem**: Prometheus metrics show no data.

**Solutions**:
1. Verify metrics endpoint is accessible: `curl http://localhost:8001/metrics`
2. Check that middleware is applied: `MetricsMiddleware(agent)`
3. Confirm messages are being processed
4. Check Prometheus scrape config

### Trace IDs Not in Logs

**Problem**: Logs don't contain trace_id/span_id.

**Solutions**:
1. Ensure `configure_logging(include_trace_context=True)`
2. Use context-aware logging: `logger.InfoContext(ctx, ...)` (Go) or ensure spans are active (Python)
3. Verify logger was created after configuration

### Broken Trace Chains

**Problem**: Spans are not connected in the trace.

**Solutions**:
1. Check that trace context is being passed between agents
2. Verify message metadata contains `trace_context`
3. Ensure W3C propagator is set (should be automatic)
4. Check that the same context is used throughout the chain

### Performance Impact

**Problem**: Observability causing performance issues.

**Solutions**:
1. Use sampling for high-volume traces:
   ```python
   from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
   # Sample 10% of traces
   sampler = TraceIdRatioBased(0.1)
   ```
2. Use batch span processors instead of simple (automatic)
3. Reduce log verbosity in production
4. Consider async metric recording

### Cross-Language Issues

**Problem**: Traces break when crossing Python/Go boundary.

**Solutions**:
1. Verify both sides are using W3C Trace Context (automatic in Agenkit)
2. Check that metadata is preserved when passing messages
3. Ensure both languages have tracing initialized
4. Verify trace context is in the expected format

## Additional Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [W3C Trace Context Specification](https://www.w3.org/TR/trace-context/)
- [Agenkit Examples](../examples/observability/)

## Support

For issues or questions:
- GitHub Issues: https://github.com/agenkit/agenkit/issues
- Documentation: https://docs.agenkit.dev

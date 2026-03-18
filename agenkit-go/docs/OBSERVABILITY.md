# Observability Guide for Agenkit-Go

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Distributed Tracing with OpenTelemetry](#distributed-tracing-with-opentelemetry)
- [Metrics with Prometheus](#metrics-with-prometheus)
- [Structured Logging with slog](#structured-logging-with-slog)
- [Audit Middleware](#audit-middleware)
- [Context Propagation](#context-propagation)
- [Jaeger Integration](#jaeger-integration)
- [Full Stack Example](#full-stack-example)
- [Best Practices](#best-practices)
- [Cross-Language Compatibility](#cross-language-compatibility)

---

## Overview

The Agenkit-Go observability module provides comprehensive monitoring, tracing, and auditing for AI agents. It follows OpenTelemetry standards and W3C Trace Context specifications for cross-language compatibility.

### Features

- **Distributed Tracing** - W3C Trace Context compliant with automatic span propagation
- **Metrics Collection** - Prometheus-compatible counters, histograms, and gauges
- **Structured Logging** - JSON and text formats via Go's `log/slog`
- **Audit Logging** - Compliance-ready event logging
- **Middleware Integration** - Automatic instrumentation wrapping any `agenkit.Agent`
- **Context Propagation** - Trace IDs flow through goroutines and HTTP calls
- **Cross-Language** - Compatible with Python, TypeScript, Rust, C++, Zig implementations

---

## Quick Start

Install observability dependencies:

```bash
go get go.opentelemetry.io/otel
go get go.opentelemetry.io/otel/exporters/otlp/otlptrace
go get github.com/prometheus/client_golang
```

Basic setup:

```go
package main

import (
    "context"
    "fmt"
    "log"
    "log/slog"
    "os"

    "go.opentelemetry.io/otel"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/observability"
)

func main() {
    ctx := context.Background()

    // 1. Configure structured logging
    logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    }))

    // 2. Create base agent
    base := &MyAgent{}

    // 3. Add tracing
    tracer := otel.Tracer("my-service")
    traced := observability.NewTracingMiddleware(base, tracer)

    // 4. Add metrics
    collector := observability.NewMetricsCollector("agenkit")
    if err := collector.Register(); err != nil {
        log.Fatalf("failed to register metrics: %v", err)
    }
    observed := collector.Middleware(traced)

    // 5. Add logging
    agent := observability.NewLoggingMiddleware(observed, logger, slog.LevelInfo)

    // All agent calls are now traced, measured, and logged
    msg := agenkit.NewMessage("user", "Hello!")
    response, err := agent.Process(ctx, msg)
    if err != nil {
        log.Fatalf("processing failed: %v", err)
    }
    fmt.Println(response.Content)
}
```

---

## Distributed Tracing with OpenTelemetry

### Setup

```go
package observability_example

import (
    "context"
    "fmt"
    "log"

    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.21.0"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/observability"
)

// initTracer configures the OpenTelemetry SDK with OTLP gRPC exporter.
func initTracer(ctx context.Context, endpoint string) (func(context.Context) error, error) {
    exporter, err := otlptracegrpc.New(ctx,
        otlptracegrpc.WithEndpoint(endpoint),
        otlptracegrpc.WithInsecure(),
    )
    if err != nil {
        return nil, fmt.Errorf("failed to create OTLP exporter: %w", err)
    }

    res, err := resource.New(ctx,
        resource.WithAttributes(
            semconv.ServiceNameKey.String("my-agenkit-service"),
            semconv.ServiceVersionKey.String("0.75.0"),
        ),
    )
    if err != nil {
        return nil, fmt.Errorf("failed to create resource: %w", err)
    }

    tp := sdktrace.NewTracerProvider(
        sdktrace.WithBatcher(exporter),
        sdktrace.WithResource(res),
        sdktrace.WithSampler(sdktrace.AlwaysSample()),
    )
    otel.SetTracerProvider(tp)

    return tp.Shutdown, nil
}

func main() {
    ctx := context.Background()

    // Initialize tracer
    shutdown, err := initTracer(ctx, "localhost:4317")
    if err != nil {
        log.Fatalf("failed to init tracer: %v", err)
    }
    defer func() {
        if err := shutdown(ctx); err != nil {
            log.Printf("failed to shutdown tracer: %v", err)
        }
    }()

    // Wrap agent with tracing
    tracer := otel.Tracer("agenkit")
    agent := observability.NewTracingMiddleware(&MyAgent{}, tracer)

    // All Process() calls create spans automatically
    msg := agenkit.NewMessage("user", "trace this call")
    response, err := agent.Process(ctx, msg)
    if err != nil {
        log.Fatalf("failed: %v", err)
    }
    fmt.Println(response.Content)
}
```

### What Gets Traced

The `TracingMiddleware` automatically creates spans with:

| Attribute | Value | Description |
|-----------|-------|-------------|
| `agent.name` | `"my-agent"` | Agent identifier |
| `agent.role` | `"user"` | Input message role |
| `agent.content_length` | `42` | Input content length |
| `agent.response_role` | `"assistant"` | Output message role |
| `agent.latency_ms` | `150` | Processing time |
| `error` | `true/false` | Whether an error occurred |
| `error.message` | `"..."` | Error details if any |

### Adding Custom Spans

```go
func (a *MyAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    tracer := otel.Tracer("my-agent")

    // Create a child span for a specific operation
    ctx, span := tracer.Start(ctx, "llm-call")
    defer span.End()

    span.SetAttributes(
        attribute.String("model", "claude-3-5-sonnet"),
        attribute.Int("max_tokens", 1024),
    )

    response, err := a.callLLM(ctx, msg)
    if err != nil {
        span.RecordError(err)
        return nil, fmt.Errorf("llm call failed: %w", err)
    }

    span.SetAttributes(attribute.Int("tokens_used", response.TokenCount))
    return response.Message, nil
}
```

---

## Metrics with Prometheus

### Setup

```go
package main

import (
    "log"
    "net/http"

    "github.com/prometheus/client_golang/prometheus/promhttp"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/observability"
)

func main() {
    // Create metrics collector
    collector := observability.NewMetricsCollector("agenkit")
    if err := collector.Register(); err != nil {
        log.Fatalf("failed to register metrics: %v", err)
    }

    // Wrap agent
    agent := collector.Middleware(&MyAgent{})

    // Expose /metrics endpoint
    http.Handle("/metrics", promhttp.Handler())
    go func() {
        if err := http.ListenAndServe(":9090", nil); err != nil && err != http.ErrServerClosed {
            log.Printf("metrics server error: %v", err)
        }
    }()

    // Use agent normally
    ctx := context.Background()
    msg := agenkit.NewMessage("user", "hello")
    if _, err := agent.Process(ctx, msg); err != nil {
        log.Printf("processing error: %v", err)
    }
}
```

### Available Metrics

The `MetricsCollector` registers these Prometheus metrics:

```
# HELP agenkit_requests_total Total number of agent requests
# TYPE agenkit_requests_total counter
agenkit_requests_total{agent="my-agent",status="success"} 1234
agenkit_requests_total{agent="my-agent",status="error"} 12

# HELP agenkit_request_duration_seconds Agent request latency
# TYPE agenkit_request_duration_seconds histogram
agenkit_request_duration_seconds_bucket{agent="my-agent",le="0.1"} 800
agenkit_request_duration_seconds_bucket{agent="my-agent",le="0.5"} 1100
agenkit_request_duration_seconds_bucket{agent="my-agent",le="1.0"} 1200
agenkit_request_duration_seconds_sum{agent="my-agent"} 623.4
agenkit_request_duration_seconds_count{agent="my-agent"} 1234

# HELP agenkit_active_requests Current number of active requests
# TYPE agenkit_active_requests gauge
agenkit_active_requests{agent="my-agent"} 3
```

### Metrics Snapshot

For non-Prometheus use cases, get an in-process snapshot:

```go
snapshot := collector.Snapshot()
fmt.Printf("Total requests: %d\n", snapshot.TotalRequests)
fmt.Printf("Success rate: %.2f%%\n",
    float64(snapshot.SuccessfulRequests)/float64(snapshot.TotalRequests)*100)
fmt.Printf("P95 latency: %.2fms\n", snapshot.P95LatencyMs)
```

### Custom Metrics

Add application-specific metrics alongside agent metrics:

```go
import "github.com/prometheus/client_golang/prometheus"

tokenCounter := prometheus.NewCounterVec(
    prometheus.CounterOpts{
        Namespace: "agenkit",
        Name:      "tokens_used_total",
        Help:      "Total tokens consumed by LLM calls",
    },
    []string{"model", "agent"},
)
prometheus.MustRegister(tokenCounter)

// Increment in your agent
func (a *MyAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    resp, tokensUsed, err := a.callLLM(ctx, msg)
    if err != nil {
        return nil, err
    }
    tokenCounter.WithLabelValues("claude-3-5-sonnet", a.Name()).Add(float64(tokensUsed))
    return resp, nil
}
```

---

## Structured Logging with slog

Go 1.21+ ships with `log/slog` for structured logging. Agenkit uses it throughout.

### Basic Configuration

```go
import (
    "log/slog"
    "os"
)

// JSON format (production)
logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
    Level: slog.LevelInfo,
}))

// Text format (development)
logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
    Level: slog.LevelDebug,
}))

// Set as default logger
slog.SetDefault(logger)
```

### Logging Middleware

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/observability"

logger := slog.Default()
agent := observability.NewLoggingMiddleware(base, logger, slog.LevelInfo)
```

Each `Process()` call logs:

```json
{"time":"2026-03-17T10:00:00Z","level":"INFO","msg":"agent.process.start",
  "agent":"my-agent","message_role":"user","content_length":12}

{"time":"2026-03-17T10:00:00.150Z","level":"INFO","msg":"agent.process.complete",
  "agent":"my-agent","latency_ms":150,"response_role":"assistant"}
```

### Logging with Trace Correlation

Link log entries to OpenTelemetry traces:

```go
import (
    "log/slog"
    "go.opentelemetry.io/otel/trace"
)

// Add trace context to log record
func logWithTrace(ctx context.Context, logger *slog.Logger, msg string, args ...any) {
    span := trace.SpanFromContext(ctx)
    if span.IsRecording() {
        sc := span.SpanContext()
        args = append(args,
            slog.String("trace_id", sc.TraceID().String()),
            slog.String("span_id", sc.SpanID().String()),
        )
    }
    logger.InfoContext(ctx, msg, args...)
}

// Usage in an agent
func (a *MyAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    logWithTrace(ctx, slog.Default(), "processing message",
        slog.String("agent", a.Name()),
        slog.Int("content_length", len(msg.Content)),
    )
    // ...
}
```

### Logging Levels

```go
logger.Debug("verbose debug", slog.String("key", "value"))
logger.Info("normal operation", slog.String("agent", "my-agent"))
logger.Warn("degraded state", slog.Int("retries", 2))
logger.Error("operation failed", slog.String("error", err.Error()))
```

**Note:** Error messages in log entries (as in all Go code) start lowercase: `"failed to connect"` not `"Failed to connect"`.

---

## Audit Middleware

The `AuditMiddleware` records every agent interaction for compliance and debugging.

```go
import (
    "log/slog"
    "os"

    "github.com/scttfrdmn/agenkit/agenkit-go/middleware"
)

auditLogger := slog.New(slog.NewJSONHandler(auditFile, nil))

agent := middleware.NewAuditMiddleware(base, &middleware.AuditConfig{
    Logger:   auditLogger,
    LogInput: true, // Set false to avoid logging PII
})
```

Each call emits a structured audit record:

```json
{
  "time": "2026-03-17T10:00:00Z",
  "level": "INFO",
  "msg": "audit",
  "event": "agent.process",
  "agent": "my-agent",
  "session_id": "abc-123",
  "input_role": "user",
  "input_content": "What is Go?",
  "output_role": "assistant",
  "output_length": 256,
  "latency_ms": 142,
  "success": true
}
```

---

## Context Propagation

Trace context must flow through all goroutines and HTTP calls.

### Within Goroutines

```go
func (a *MyAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    tracer := otel.Tracer("my-agent")
    ctx, span := tracer.Start(ctx, "parallel-subwork")
    defer span.End()

    type result struct {
        msg *agenkit.Message
        err error
    }

    ch := make(chan result, 2)

    // Pass ctx to each goroutine to propagate trace context
    go func() {
        resp, err := a.subAgent1.Process(ctx, msg) // ctx carries trace
        ch <- result{resp, err}
    }()

    go func() {
        resp, err := a.subAgent2.Process(ctx, msg) // ctx carries trace
        ch <- result{resp, err}
    }()

    r1, r2 := <-ch, <-ch
    if r1.err != nil {
        return nil, fmt.Errorf("subagent1 failed: %w", r1.err)
    }
    if r2.err != nil {
        return nil, fmt.Errorf("subagent2 failed: %w", r2.err)
    }

    return r1.msg, nil
}
```

### Across HTTP Calls

Use the W3C `traceparent` header to propagate traces across services:

```go
import (
    "net/http"

    "go.opentelemetry.io/otel/propagation"
    "go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
)

// Outgoing HTTP request with trace propagation
func callRemoteAgent(ctx context.Context, url string, msg *agenkit.Message) (*agenkit.Message, error) {
    httpClient := &http.Client{Transport: otelhttp.NewTransport(http.DefaultTransport)}

    req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, encodeMessage(msg))
    if err != nil {
        return nil, fmt.Errorf("failed to create request: %w", err)
    }

    // otelhttp injects traceparent header automatically
    resp, err := httpClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("http request failed: %w", err)
    }
    defer func() { _ = resp.Body.Close() }()

    return decodeMessage(resp.Body)
}

// Incoming HTTP request — extract trace context
func agentHandler(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context() // otelhttp middleware already extracted trace context
    // ctx now contains the incoming span — use it for all downstream calls
    processRequest(ctx, r)
}
```

---

## Jaeger Integration

Jaeger provides a UI for visualizing distributed traces.

### Start Jaeger

```bash
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest

# Open UI
open http://localhost:16686
```

### Configure Go to Export to Jaeger

```go
import (
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
)

exporter, err := otlptracegrpc.New(ctx,
    otlptracegrpc.WithEndpoint("localhost:4317"),
    otlptracegrpc.WithInsecure(),
)
if err != nil {
    log.Fatalf("failed to create Jaeger exporter: %v", err)
}
```

Then follow the [Distributed Tracing](#distributed-tracing-with-opentelemetry) setup above with this exporter.

### Trace Visualization

Once traces are flowing, the Jaeger UI shows:

- Full request timeline across agents
- Per-span latency breakdown
- Error rates and propagation
- Cross-language trace correlation (Go agent → Python agent → Go agent)

---

## Full Stack Example

This example shows all three observability pillars (traces, metrics, logs) working together:

```go
package main

import (
    "context"
    "fmt"
    "log"
    "log/slog"
    "net/http"
    "os"
    "time"

    "github.com/prometheus/client_golang/prometheus/promhttp"
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    "go.opentelemetry.io/otel/sdk/resource"
    semconv "go.opentelemetry.io/otel/semconv/v1.21.0"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/middleware"
    "github.com/scttfrdmn/agenkit/agenkit-go/observability"
)

func main() {
    ctx := context.Background()

    // -- Logging setup --
    logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    }))
    slog.SetDefault(logger)

    // -- Tracing setup --
    exporter, err := otlptracegrpc.New(ctx,
        otlptracegrpc.WithEndpoint("localhost:4317"),
        otlptracegrpc.WithInsecure(),
    )
    if err != nil {
        log.Fatalf("failed to create exporter: %v", err)
    }

    res, err := resource.New(ctx,
        resource.WithAttributes(semconv.ServiceNameKey.String("agenkit-demo")),
    )
    if err != nil {
        log.Fatalf("failed to create resource: %v", err)
    }

    tp := sdktrace.NewTracerProvider(
        sdktrace.WithBatcher(exporter),
        sdktrace.WithResource(res),
    )
    otel.SetTracerProvider(tp)
    defer func() {
        if err := tp.Shutdown(ctx); err != nil {
            log.Printf("failed to shutdown tracer: %v", err)
        }
    }()

    // -- Metrics setup --
    collector := observability.NewMetricsCollector("agenkit")
    if err := collector.Register(); err != nil {
        log.Fatalf("failed to register metrics: %v", err)
    }

    // Expose /metrics endpoint
    http.Handle("/metrics", promhttp.Handler())
    go func() {
        if err := http.ListenAndServe(":9090", nil); err != nil && err != http.ErrServerClosed {
            log.Printf("metrics server error: %v", err)
        }
    }()

    // -- Build instrumented agent --
    base := &MyAgent{}

    // Layer middleware: from innermost to outermost
    var agent agenkit.Agent = base

    // Resilience
    agent = middleware.NewRetryMiddleware(agent, &middleware.RetryConfig{
        MaxRetries:   3,
        InitialDelay: 100 * time.Millisecond,
    })
    agent = middleware.NewTimeoutMiddleware(agent, &middleware.TimeoutConfig{
        Timeout: 10 * time.Second,
    })

    // Observability
    agent = observability.NewTracingMiddleware(agent, otel.Tracer("my-agent"))
    agent = collector.Middleware(agent)
    agent = observability.NewLoggingMiddleware(agent, logger, slog.LevelInfo)

    // -- Process requests --
    for i := range 10 {
        msg := agenkit.NewMessage("user", fmt.Sprintf("request %d", i))
        _, err := agent.Process(ctx, msg)
        if err != nil {
            slog.Error("request failed", slog.Int("request", i), slog.String("error", err.Error()))
        }
    }

    // -- Print metrics summary --
    snap := collector.Snapshot()
    slog.Info("metrics summary",
        slog.Int64("total_requests", snap.TotalRequests),
        slog.Int64("successful", snap.SuccessfulRequests),
        slog.Float64("p95_latency_ms", snap.P95LatencyMs),
    )
}
```

---

## Best Practices

### 1. Always Propagate Context

```go
// CORRECT: propagate ctx to all downstream calls
func (a *MyAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    return a.llm.Process(ctx, msg) // ctx carries trace
}

// WRONG: create new context, losing trace
func (a *MyAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    return a.llm.Process(context.Background(), msg) // trace lost!
}
```

### 2. Record Errors in Spans

```go
ctx, span := tracer.Start(ctx, "operation")
defer span.End()

result, err := doWork(ctx)
if err != nil {
    span.RecordError(err)
    span.SetStatus(codes.Error, err.Error())
    return nil, err
}
```

### 3. Use Semantic Attributes

```go
import semconv "go.opentelemetry.io/otel/semconv/v1.21.0"

span.SetAttributes(
    semconv.ServiceNameKey.String("my-agent"),
    attribute.String("llm.model", "claude-3-5-sonnet"),
    attribute.Int("llm.max_tokens", 1024),
)
```

### 4. Shutdown Tracer Properly

```go
shutdown, err := initTracer(ctx, endpoint)
if err != nil {
    log.Fatalf("init tracer failed: %v", err)
}
// Always defer shutdown to flush pending spans
defer func() {
    if err := shutdown(ctx); err != nil {
        log.Printf("tracer shutdown error: %v", err)
    }
}()
```

### 5. Sampling for High-Traffic Services

```go
tp := sdktrace.NewTracerProvider(
    sdktrace.WithBatcher(exporter),
    // Sample 10% of traces in production
    sdktrace.WithSampler(sdktrace.TraceIDRatioBased(0.1)),
)
```

---

## Cross-Language Compatibility

Agenkit's observability layer uses W3C Trace Context for cross-language correlation. A trace initiated in a Go agent can continue in a Python or TypeScript agent.

### W3C traceparent Header

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
             ^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^  ^^
             version  trace-id (32 hex chars)      span-id (16 hex)  flags
```

When a Go agent calls a Python agent over HTTP, the `traceparent` header carries the trace ID. The Python agent creates a child span under the same trace. In Jaeger or any OTLP-compatible backend, you see the full cross-language call tree.

### Agent Identification in Spans

All Agenkit implementations use the same span attribute names:
- `agent.name` - Agent identifier
- `agent.pattern` - Pattern type (sequential, parallel, etc.)
- `agent.latency_ms` - Processing time

This enables cross-language dashboards and alerts.

---

## See Also

- [API Reference](API.md) - TracingAgent and MetricsCollector types
- [Getting Started](GETTING_STARTED.md) - Basic setup
- [Patterns Guide](PATTERNS.md) - Agent patterns
- [Testing Framework](TESTING_FRAMEWORK.md) - Testing with mock traces
- [GoDoc](https://pkg.go.dev/github.com/scttfrdmn/agenkit/agenkit-go/observability) - Auto-generated docs

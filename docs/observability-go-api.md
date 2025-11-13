# Go Observability API Reference

Complete API reference for Agenkit's Go observability package.

## Package: `github.com/agenkit/agenkit-go/observability`

### Functions

#### `InitTracing()`

Initialize OpenTelemetry distributed tracing.

```go
func InitTracing(serviceName string, otlpEndpoint string, consoleExport bool) (*sdktrace.TracerProvider, error)
```

**Parameters:**
- `serviceName` (string): Name to identify this service in traces.
- `otlpEndpoint` (string): OTLP collector endpoint (e.g., `"localhost:4317"`). Use empty string to disable OTLP export.
- `consoleExport` (bool): Whether to export traces to console for debugging.

**Returns:**
- `*sdktrace.TracerProvider`: The configured OpenTelemetry tracer provider.
- `error`: Error if initialization fails.

**Example:**
```go
import "github.com/agenkit/agenkit-go/observability"

// Development: console export
tp, err := observability.InitTracing("my-agent", "", true)
if err != nil {
    log.Fatal(err)
}
defer observability.Shutdown(context.Background())

// Production: OTLP export to Jaeger/Tempo
tp, err := observability.InitTracing("my-agent", "localhost:4317", false)
if err != nil {
    log.Fatal(err)
}
defer observability.Shutdown(context.Background())
```

---

#### `InitMetrics()`

Initialize OpenTelemetry metrics with Prometheus export.

```go
func InitMetrics(serviceName string, port int) (*sdkmetric.MeterProvider, error)
```

**Parameters:**
- `serviceName` (string): Name to identify this service in metrics.
- `port` (int): Port parameter (currently unused, kept for API compatibility).

**Returns:**
- `*sdkmetric.MeterProvider`: The configured OpenTelemetry meter provider.
- `error`: Error if initialization fails.

**Note:** The `port` parameter is currently unused as the Prometheus exporter uses a pull-based model.

**Example:**
```go
mp, err := observability.InitMetrics("my-agent", 8002)
if err != nil {
    log.Fatal(err)
}
defer observability.ShutdownMetrics(context.Background())

// Metrics available via Prometheus client library
```

---

#### `ConfigureLogging()`

Configure structured logging with optional trace correlation.

```go
func ConfigureLogging(level slog.Level, structured bool, includeTraceContext bool)
```

**Parameters:**
- `level` (slog.Level): Log level (e.g., `slog.LevelInfo`, `slog.LevelDebug`).
- `structured` (bool): Whether to use JSON structured logging format.
- `includeTraceContext` (bool): Whether to include trace_id and span_id in logs.

**Example:**
```go
import "log/slog"

// JSON logs with trace correlation
observability.ConfigureLogging(slog.LevelInfo, true, true)

// Plain text logs without trace correlation
observability.ConfigureLogging(slog.LevelDebug, false, false)
```

---

#### `GetLoggerWithTrace()`

Get a logger instance that includes trace context in log records.

```go
func GetLoggerWithTrace() *slog.Logger
```

**Returns:**
- `*slog.Logger`: Logger instance with trace context handler applied.

**Example:**
```go
logger := observability.GetLoggerWithTrace()

// Logs will automatically include trace_id and span_id when in a span
logger.InfoContext(ctx, "Processing request",
    slog.String("user_id", "123"),
)
```

---

#### `GetTracer()`

Get a tracer instance for manual instrumentation.

```go
func GetTracer(name string) trace.Tracer
```

**Parameters:**
- `name` (string): Tracer name for grouping spans.

**Returns:**
- `trace.Tracer`: OpenTelemetry tracer instance.

**Example:**
```go
tracer := observability.GetTracer("mypackage")

ctx, span := tracer.Start(ctx, "custom-operation")
defer span.End()

span.SetAttributes(attribute.String("key", "value"))
// Do work...
```

---

#### `GetMeter()`

Get a meter instance for manual metric recording.

```go
func GetMeter(name string) metric.Meter
```

**Parameters:**
- `name` (string): Meter name for grouping metrics.

**Returns:**
- `metric.Meter`: OpenTelemetry meter instance.

**Example:**
```go
meter := observability.GetMeter("mypackage")

counter, err := meter.Int64Counter(
    "my_counter",
    metric.WithDescription("Custom counter metric"),
)
if err != nil {
    log.Fatal(err)
}

counter.Add(ctx, 1, metric.WithAttributes(
    attribute.String("key", "value"),
))
```

---

#### `Shutdown()`

Gracefully shut down the tracer provider.

```go
func Shutdown(ctx context.Context) error
```

**Parameters:**
- `ctx` (context.Context): Context for shutdown, use for timeout control.

**Returns:**
- `error`: Error if shutdown fails.

**Example:**
```go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

if err := observability.Shutdown(ctx); err != nil {
    log.Printf("Error shutting down tracer: %v", err)
}
```

---

#### `ShutdownMetrics()`

Gracefully shut down the meter provider.

```go
func ShutdownMetrics(ctx context.Context) error
```

**Parameters:**
- `ctx` (context.Context): Context for shutdown, use for timeout control.

**Returns:**
- `error`: Error if shutdown fails.

**Example:**
```go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

if err := observability.ShutdownMetrics(ctx); err != nil {
    log.Printf("Error shutting down metrics: %v", err)
}
```

---

### Types

#### `TracingMiddleware`

Middleware that adds distributed tracing to agent processing.

```go
type TracingMiddleware struct {
    // contains filtered or unexported fields
}
```

**Constructor:**

```go
func NewTracingMiddleware(agent Agent, spanName string) *TracingMiddleware
```

**Parameters:**
- `agent` (Agent): The agent to wrap with tracing.
- `spanName` (string): Custom span name. If empty, uses `"agent.{agent.Name()}.process"`.

**Returns:**
- `*TracingMiddleware`: New tracing middleware instance.

**Methods:**

##### `Name()`

Returns the wrapped agent's name.

```go
func (t *TracingMiddleware) Name() string
```

##### `Capabilities()`

Returns the wrapped agent's capabilities.

```go
func (t *TracingMiddleware) Capabilities() []string
```

##### `Process()`

Process a message with distributed tracing.

```go
func (t *TracingMiddleware) Process(ctx context.Context, message *Message) (*Message, error)
```

**Parameters:**
- `ctx` (context.Context): Context for the operation.
- `message` (*Message): Input message to process.

**Returns:**
- `*Message`: Response message with trace context injected into metadata.
- `error`: Error from wrapped agent, if any.

**Behavior:**
- Extracts parent trace context from `message.Metadata["trace_context"]`
- Creates a new span as a child of parent context
- Records span attributes (agent name, message role, content length, metadata)
- Calls wrapped agent's `Process()` method
- Records success status or error
- Injects trace context into response metadata

**Example:**
```go
baseAgent := &MyAgent{}
tracedAgent := observability.NewTracingMiddleware(baseAgent, "")

// Process message - span is created automatically
response, err := tracedAgent.Process(ctx, message)
if err != nil {
    log.Fatal(err)
}

// Response includes trace context for propagation
fmt.Println(response.Metadata["trace_context"])
```

---

#### `MetricsMiddleware`

Middleware that adds metrics collection to agent processing.

```go
type MetricsMiddleware struct {
    // contains filtered or unexported fields
}
```

**Constructor:**

```go
func NewMetricsMiddleware(agent Agent) (*MetricsMiddleware, error)
```

**Parameters:**
- `agent` (Agent): The agent to wrap with metrics collection.

**Returns:**
- `*MetricsMiddleware`: New metrics middleware instance.
- `error`: Error if metrics initialization fails.

**Methods:**

##### `Name()`

Returns the wrapped agent's name.

```go
func (m *MetricsMiddleware) Name() string
```

##### `Capabilities()`

Returns the wrapped agent's capabilities.

```go
func (m *MetricsMiddleware) Capabilities() []string
```

##### `Process()`

Process a message with metrics collection.

```go
func (m *MetricsMiddleware) Process(ctx context.Context, message *Message) (*Message, error)
```

**Parameters:**
- `ctx` (context.Context): Context for the operation.
- `message` (*Message): Input message to process.

**Returns:**
- `*Message`: Response message from wrapped agent.
- `error`: Error from wrapped agent, if any.

**Metrics Recorded:**
- `agenkit.agent.requests`: Counter of total requests
- `agenkit.agent.errors`: Counter of errors (only on failure)
- `agenkit.agent.latency`: Histogram of processing latency in milliseconds
- `agenkit.agent.message_size`: Histogram of message content size in bytes

**Attributes (Labels):**
- `agent.name`: Name of the agent
- `message.role`: Role of the message
- `status`: "success" or "error"
- `error.type`: Type of error (only on error)

**Example:**
```go
baseAgent := &MyAgent{}
monitoredAgent, err := observability.NewMetricsMiddleware(baseAgent)
if err != nil {
    log.Fatal(err)
}

// Process message - metrics are recorded automatically
response, err := monitoredAgent.Process(ctx, message)
```

---

#### `TraceContextHandler`

slog.Handler that adds trace context to log records.

```go
type TraceContextHandler struct {
    // contains filtered or unexported fields
}
```

**Constructor:**

```go
func NewTraceContextHandler(handler slog.Handler) *TraceContextHandler
```

**Parameters:**
- `handler` (slog.Handler): Base handler to wrap.

**Returns:**
- `*TraceContextHandler`: Handler that adds trace context.

**Behavior:**
- Extracts current span context from OpenTelemetry
- Adds `trace_id` and `span_id` attributes to log record
- Passes through to wrapped handler

**Methods:**

##### `Enabled()`

```go
func (h *TraceContextHandler) Enabled(ctx context.Context, level slog.Level) bool
```

##### `Handle()`

```go
func (h *TraceContextHandler) Handle(ctx context.Context, record slog.Record) error
```

##### `WithAttrs()`

```go
func (h *TraceContextHandler) WithAttrs(attrs []slog.Attr) slog.Handler
```

##### `WithGroup()`

```go
func (h *TraceContextHandler) WithGroup(name string) slog.Handler
```

**Example:**
```go
handler := slog.NewJSONHandler(os.Stdout, nil)
traceHandler := observability.NewTraceContextHandler(handler)

logger := slog.New(traceHandler)

// Logs will include trace context
logger.InfoContext(ctx, "Processing request")
```

---

#### `StructuredHandler`

slog.Handler that outputs JSON structured logs.

```go
type StructuredHandler struct {
    // contains filtered or unexported fields
}
```

**Constructor:**

```go
func NewStructuredHandler() *StructuredHandler
```

**Returns:**
- `*StructuredHandler`: Handler that formats logs as JSON.

**Output Format:**
```json
{
  "timestamp": "2025-11-12T20:00:00-08:00",
  "level": "INFO",
  "message": "Log message",
  "trace_id": "...",
  "span_id": "...",
  "custom_field": "custom_value"
}
```

**Methods:**

##### `Enabled()`

```go
func (h *StructuredHandler) Enabled(ctx context.Context, level slog.Level) bool
```

##### `Handle()`

```go
func (h *StructuredHandler) Handle(ctx context.Context, record slog.Record) error
```

##### `WithAttrs()`

```go
func (h *StructuredHandler) WithAttrs(attrs []slog.Attr) slog.Handler
```

##### `WithGroup()`

```go
func (h *StructuredHandler) WithGroup(name string) slog.Handler
```

**Example:**
```go
structuredHandler := observability.NewStructuredHandler()
traceHandler := observability.NewTraceContextHandler(structuredHandler)

logger := slog.New(traceHandler)

logger.Info("Processing", slog.String("user_id", "123"))
// Output: {"timestamp": "...", "level": "INFO", "message": "Processing", "user_id": "123"}
```

---

#### `Message`

Agent message type.

```go
type Message struct {
    Role     string
    Content  string
    Metadata map[string]interface{}
}
```

**Fields:**
- `Role` (string): Message role (e.g., "user", "agent").
- `Content` (string): Message content.
- `Metadata` (map[string]interface{}): Optional metadata, used for trace context propagation.

---

#### `Agent`

Agent interface.

```go
type Agent interface {
    Name() string
    Capabilities() []string
    Process(ctx context.Context, message *Message) (*Message, error)
}
```

---

### Helper Functions

#### `ExtractTraceContext()`

Extract W3C Trace Context from message metadata.

```go
func ExtractTraceContext(ctx context.Context, metadata map[string]interface{}) context.Context
```

**Parameters:**
- `ctx` (context.Context): Base context.
- `metadata` (map[string]interface{}): Message metadata.

**Returns:**
- `context.Context`: Context with extracted trace context.

**Example:**
```go
ctx = observability.ExtractTraceContext(ctx, message.Metadata)
```

---

#### `InjectTraceContext()`

Inject current trace context into metadata dictionary.

```go
func InjectTraceContext(ctx context.Context, metadata map[string]interface{}) map[string]interface{}
```

**Parameters:**
- `ctx` (context.Context): Context with active span.
- `metadata` (map[string]interface{}): Existing metadata or nil.

**Returns:**
- `map[string]interface{}`: Metadata with trace context added under `"trace_context"` key.

**Example:**
```go
metadata := map[string]interface{}{"key": "value"}
metadata = observability.InjectTraceContext(ctx, metadata)
// metadata["trace_context"] = {"traceparent": "00-..."}
```

---

## Usage Patterns

### Complete Setup

```go
package main

import (
    "context"
    "log"
    "log/slog"

    "github.com/agenkit/agenkit-go/observability"
)

func main() {
    // Initialize observability
    tp, err := observability.InitTracing("my-service", "", true)
    if err != nil {
        log.Fatal(err)
    }
    defer observability.Shutdown(context.Background())

    mp, err := observability.InitMetrics("my-service", 8002)
    if err != nil {
        log.Fatal(err)
    }
    defer observability.ShutdownMetrics(context.Background())

    observability.ConfigureLogging(slog.LevelInfo, true, true)

    // Get logger
    logger := observability.GetLoggerWithTrace()

    // Wrap agent with middleware
    baseAgent := &MyAgent{}
    tracedAgent := observability.NewTracingMiddleware(baseAgent, "")
    monitoredAgent, err := observability.NewMetricsMiddleware(tracedAgent)
    if err != nil {
        log.Fatal(err)
    }

    // Use agent
    ctx := context.Background()
    logger.InfoContext(ctx, "Starting request")
    response, err := monitoredAgent.Process(ctx, message)
    if err != nil {
        log.Fatal(err)
    }
    logger.InfoContext(ctx, "Request complete")
}
```

### Custom Instrumentation

```go
import (
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/metric"
)

// Manual tracing
tracer := observability.GetTracer("mypackage")
ctx, span := tracer.Start(ctx, "database-query")
defer span.End()

span.SetAttributes(attribute.String("query", "SELECT * FROM users"))
result, err := db.Query(ctx, ...)
span.SetAttributes(attribute.Int("rows", len(result)))

// Manual metrics
meter := observability.GetMeter("mypackage")
cacheHits, _ := meter.Int64Counter("cache.hits")
cacheHits.Add(ctx, 1, metric.WithAttributes(
    attribute.String("cache_name", "user-cache"),
))
```

### Error Handling

```go
response, err := agent.Process(ctx, message)
if err != nil {
    // Errors are automatically recorded in spans and metrics
    logger.ErrorContext(ctx, "Processing failed",
        slog.String("error", err.Error()),
    )
    return err
}
```

---

## See Also

- [Observability Guide](./observability.md) - Comprehensive usage guide
- [Python API Reference](./observability-python-api.md) - Python observability API
- [Examples](../agenkit-go/examples/observability/) - Working examples

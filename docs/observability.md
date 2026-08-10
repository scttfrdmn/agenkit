# Observability Guide for Agenkit Rust

Comprehensive guide to distributed tracing, metrics, logging, and audit logging in Agenkit Rust.

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Modules](#modules)
5. [Production Setup](#production-setup)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)
8. [Examples](#examples)

## Overview

The Agenkit Rust observability module provides four integrated components for production agent monitoring:

- **Distributed Tracing**: W3C Trace Context propagation across agents with OpenTelemetry
- **Metrics Collection**: Counters, histograms, and gauges exported over OTLP
- **Structured Logging**: JSON logging with trace correlation
- **Audit Logging**: Compliance-friendly event logging with querying

### Key Features

✅ **Cross-Language Compatible**: Uses message metadata for trace propagation (not thread-local storage)
✅ **Multiple Exporters**: OTLP (traces + metrics), Jaeger (via OTLP), Console
✅ **Zero-Config Middleware**: Automatic span creation and metric recording
✅ **Production-Ready**: Buffered audit logging, graceful degradation, thread-safe

## Installation

Add the following to your `Cargo.toml`:

```toml
[dependencies]
agenkit = { version = "0.89.0", features = ["native"] }
```

(See [`agenkit-rust/Cargo.toml`](../agenkit-rust/Cargo.toml) for the current version —
this line previously pinned 0.48.0 and had drifted 41 releases stale; see #874.)

The `native` feature includes all OpenTelemetry dependencies.

## Quick Start

### Minimal Setup (Development)

```rust
use agenkit::observability::{init_tracing, init_metrics, configure_logging};
use agenkit::observability::{TracingMiddleware, MetricsMiddleware};
use agenkit::core::Agent;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize observability
    init_tracing("console", None)?;
    init_metrics("stdout", None)?;
    configure_logging("json", "info")?;

    // Wrap your agent with middleware
    let agent = MyAgent::new();
    let traced_agent = TracingMiddleware::new(agent, None);
    let full_agent = MetricsMiddleware::new(traced_agent);

    // Process messages (observability automatic)
    let msg = Message::new("user", serde_json::json!("Hello!"));
    let response = full_agent.process(msg).await?;

    Ok(())
}
```

### Production Setup

```rust
use agenkit::observability::{init_tracing, init_metrics, configure_logging};
use agenkit::observability::audit::{AuditLogger, AuditEvent, AuditEventType};
use std::sync::Arc;
use std::path::PathBuf;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // OTLP for distributed tracing
    init_tracing("otlp", Some("http://localhost:4317"))?;

    // OTLP metrics to the same collector
    init_metrics("otlp", Some("http://localhost:4317"))?;

    // JSON logging for production
    configure_logging("json", "info")?;

    // Audit logging for compliance
    let audit_logger = Arc::new(
        AuditLogger::with_buffer_size(
            PathBuf::from("/var/log/agenkit/audit.log"),
            50
        )?
    );

    // Log agent creation
    audit_logger.log(AuditEvent::new(
        AuditEventType::AgentCreated,
        "production_agent".to_string(),
        None
    )).await?;

    // Your application code...

    // Flush audit logs before exit
    audit_logger.flush().await?;

    Ok(())
}
```

## Modules


### 1. Tracing Module

Distributed tracing with W3C Trace Context propagation.

#### Initialization

```rust
use agenkit::observability::init_tracing;

// OTLP (best for production)
init_tracing("otlp", Some("http://localhost:4317"))?;

// Console (best for development)
init_tracing("console", None)?;

// Jaeger (deprecated, use OTLP instead)
init_tracing("jaeger", Some("http://localhost:14250"))?;

// Zipkin
init_tracing("zipkin", Some("http://localhost:9411"))?;
```

#### TracingMiddleware

Automatically creates spans for agent calls and propagates trace context:

```rust
use agenkit::observability::TracingMiddleware;

// Default span name (uses agent name)
let traced_agent = TracingMiddleware::new(agent, None);

// Custom span name
let traced_agent = TracingMiddleware::new(agent, Some("my_span".to_string()));
```

#### Trace Context Propagation

Trace context is automatically propagated via message metadata:

```rust
use agenkit::observability::{extract_trace_context, inject_trace_context};
use agenkit::core::Message;

// Extract parent context from incoming message
let parent_context = extract_trace_context(&message.metadata);

// Inject context into outgoing message
let mut response = Message::new("assistant", serde_json::json!("Hi!"));
inject_trace_context(&mut response.metadata, &context);
```

#### Key Concepts

- **Trace ID**: Unique identifier for entire request flow across all agents
- **Span ID**: Unique identifier for single agent operation
- **Parent Span ID**: Links spans into a tree structure
- **W3C Trace Context**: Standard format (`traceparent` header) for cross-language compatibility

### 2. Metrics Module

Metrics collection with automatic counters and histograms.

#### Initialization

```rust
use agenkit::observability::init_metrics;

// OTLP (push-based)
init_metrics("otlp", Some("http://localhost:4317"))?;

// OTLP using OTEL_EXPORTER_OTLP_ENDPOINT from the environment
init_metrics("otlp", None)?;

// Console, for debugging
init_metrics("stdout", None)?;
```

> **`"prometheus"` returns an error.** The `opentelemetry-prometheus` and
> `prometheus` crates were removed from `Cargo.toml` over vulnerable transitive
> dependencies (thrift, protobuf 2.x), so there is no exporter to install. It
> previously returned `Ok(())` and exported nothing — worse than failing, since a
> scrape endpoint that never appears is indistinguishable from a misconfigured
> scrape target. To get Prometheus, export OTLP to a collector and let the
> collector expose the scrape endpoint.

Metrics are exported by a periodic reader on a 60-second interval (the OTel spec
default), so **call `shutdown_observability()` before exit** or the last interval
of metrics is lost.

#### MetricsMiddleware

Automatically records request counts and duration:

```rust
use agenkit::observability::MetricsMiddleware;

let metrics_agent = MetricsMiddleware::new(agent);
```

**Recorded Metrics:**

- `agent_requests_total` (counter) - Total requests with labels:
  - `agent.name`: Name of the agent
  - `status`: "success" or "error"

- `agent_request_duration_seconds` (histogram) - Request duration with labels:
  - `agent.name`: Name of the agent

#### Custom Metrics

```rust
use agenkit::observability::get_meter;
use opentelemetry::KeyValue;

let meter = get_meter("my_app");

// Counter
let counter = meter.u64_counter("my_counter").init();
counter.add(1, &[KeyValue::new("key", "value")]);

// Histogram
let histogram = meter.f64_histogram("my_histogram").init();
histogram.record(1.5, &[KeyValue::new("key", "value")]);
```

#### Accessing Prometheus Metrics

Agenkit Rust does not serve a scrape endpoint — see the note above. Export OTLP
to a collector configured with a `prometheus` exporter, and scrape the
collector:

```bash
curl http://otel-collector:8889/metrics
```

### 3. Logging Module

Structured logging with trace correlation.

#### Initialization

```rust
use agenkit::observability::configure_logging;

// JSON format (best for production)
configure_logging("json", "info")?;

// Pretty format (best for development)
configure_logging("pretty", "debug")?;

// Compact format
configure_logging("compact", "warn")?;
```

**Log Levels:** `trace`, `debug`, `info`, `warn`, `error`

#### Logging Functions

```rust
use agenkit::observability::{log_agent_event, log_agent_error, log_agent_warning};

// Log an event
log_agent_event(
    "message_processed",
    "Successfully processed user message",
    &[("agent_name", "ChatAgent"), ("duration_ms", "150")]
);

// Log an error
log_agent_error(
    "processing_failed",
    "Failed to process message",
    "Connection timeout after 30s"
);

// Log a warning
log_agent_warning(
    "high_latency",
    "Agent response time exceeding threshold",
    &[("latency_ms", "2500"), ("threshold_ms", "1000")]
);
```

#### Trace Correlation

When tracing is initialized, logs automatically include trace context for correlation between logs and traces.

### 4. Audit Module

Compliance-friendly event logging with querying.

#### Initialization

```rust
use agenkit::observability::audit::AuditLogger;
use std::path::PathBuf;

// Default buffer size (100)
let logger = AuditLogger::new(PathBuf::from("/var/log/audit.log"))?;

// Custom buffer size
let logger = AuditLogger::with_buffer_size(
    PathBuf::from("/var/log/audit.log"),
    50
)?;
```

#### Event Types

```rust
use agenkit::observability::audit::AuditEventType;

pub enum AuditEventType {
    AgentCreated,
    MessageProcessed,
    SecurityViolation,
    ConfigurationChanged,
    ErrorOccurred,
    UserAction,
    SystemEvent,
}
```

#### Severity Levels

```rust
use agenkit::observability::audit::Severity;

pub enum Severity {
    Info,
    Warning,
    Error,
    Critical,
}
```

#### Logging Events

```rust
use agenkit::observability::audit::{AuditEvent, AuditEventType, Severity};

// Basic event
let event = AuditEvent::new(
    AuditEventType::MessageProcessed,
    "ChatAgent".to_string(),
    Some("session-123".to_string())
);
logger.log(event).await?;

// Event with details and severity
let event = AuditEvent::new(
    AuditEventType::SecurityViolation,
    "AuthAgent".to_string(),
    Some("session-456".to_string())
)
.with_detail("reason".to_string(), serde_json::json!("Invalid token"))
.with_severity(Severity::Critical);
logger.log(event).await?;

// Flush to disk (automatic when buffer is full)
logger.flush().await?;
```

#### Querying Events

```rust
// Query all events
let all_events = logger.query(None).await?;

// Query with custom filter
let filtered = logger.query(Some(Box::new(|event| {
    event.agent_name == "ChatAgent"
}))).await?;

// Query by session ID
let session_events = logger.query_by_session("session-123").await?;

// Query by agent name
let agent_events = logger.query_by_agent("AuthAgent").await?;

// Query by event type
let errors = logger.query_by_type(AuditEventType::ErrorOccurred).await?;
```


## Production Setup

### Complete Production Configuration

```rust
use agenkit::observability::{init_tracing, init_metrics, configure_logging, shutdown_observability};
use agenkit::observability::audit::{AuditLogger, AuditEvent, AuditEventType};
use std::sync::Arc;
use std::path::PathBuf;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 1. Initialize tracing with OTLP
    match init_tracing("otlp", Some("http://localhost:4317")) {
        Ok(_) => println!("Tracing initialized"),
        Err(e) => eprintln!("Failed to initialize tracing: {}", e),
    }

    // 2. Initialize metrics with OTLP
    match init_metrics("otlp", Some("http://localhost:4317")) {
        Ok(_) => println!("Metrics initialized"),
        Err(e) => eprintln!("Failed to initialize metrics: {}", e),
    }

    // 3. Configure JSON logging
    match configure_logging("json", "info") {
        Ok(_) => println!("Logging configured"),
        Err(e) => eprintln!("Failed to configure logging: {}", e),
    }

    // 4. Setup audit logging
    let audit_logger = Arc::new(AuditLogger::with_buffer_size(
        PathBuf::from("/var/log/agenkit/audit.log"),
        50
    )?);

    // Your application...

    // 5. Cleanup on shutdown — REQUIRED with the OTLP exporter. The span
    //    processor batches, so exiting without this drops every unflushed span
    //    silently: no error, and nothing arrives at the collector.
    audit_logger.flush().await?;
    shutdown_observability();

    Ok(())
}
```

### Docker Compose for Observability Stack

```yaml
version: '3.8'

services:
  # OpenTelemetry Collector
  otel-collector:
    image: otel/opentelemetry-collector:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"  # OTLP gRPC
      - "4318:4318"  # OTLP HTTP

  # Jaeger for trace visualization
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # UI
      - "14250:14250"  # gRPC

  # Prometheus for metrics
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  # Grafana for dashboards
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
```

### Kubernetes Deployment

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: observability-config
data:
  # Read by init_tracing/InitTracing/initTracing in every language (Python,
  # Go, TypeScript, Rust, C++) as the default OTLP endpoint whenever the
  # corresponding parameter is not explicitly supplied. An explicit parameter
  # always takes precedence over this variable. See
  # docs/OTEL_CONVENTION.md#collector-endpoint-and-service-name (#771).
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector:4317"
  # Read the same way for the service name, except in C++, which has no
  # service_name parameter yet.
  OTEL_SERVICE_NAME: "agenkit-app"
  RUST_LOG: "info"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agenkit-app
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: app
        image: my-agenkit-app:latest
        envFrom:
        - configMapRef:
            name: observability-config
        ports:
        - containerPort: 9464  # Prometheus metrics
```

## Best Practices

### 1. Initialization Order

Always initialize in this order:

1. Tracing
2. Metrics
3. Logging
4. Audit (if needed)

### 2. Middleware Composition

Apply middleware in this order for best results:

```rust
let agent = MyAgent::new();
let traced = TracingMiddleware::new(agent, None);       // 1. Tracing
let metered = MetricsMiddleware::new(traced);           // 2. Metrics
// 3. Logging happens automatically via log_agent_* functions
```

### 3. Error Handling

Handle initialization errors gracefully:

```rust
// Production: Degrade gracefully if observability fails
match init_tracing("otlp", Some("http://localhost:4317")) {
    Ok(_) => {},
    Err(e) => {
        eprintln!("Failed to initialize tracing: {}", e);
        // Application continues without tracing
    }
}

// Development: Fail fast to catch configuration issues
init_tracing("otlp", Some("http://localhost:4317"))?;
```

### 4. Audit Log Management

- **Buffer Size**: Balance memory usage vs flush frequency (50-100 is typical)
- **Retention**: Implement log rotation (use `logrotate` or similar)
- **Queries**: Flush before querying to ensure consistency

```rust
// Flush before querying
logger.flush().await?;
let events = logger.query_by_session("session-123").await?;
```

### 5. Resource Management

```rust
// Always flush and shutdown on application exit
audit_logger.flush().await?;
shutdown_observability();
```

`shutdown_observability()` is synchronous and idempotent. Skipping it is the
single most common way to lose production traces: the OTLP span processor
batches, so unflushed spans are dropped at exit without an error. Nothing
distinguishes "traces were lost at shutdown" from "the code never ran".

### 6. Testing

In tests, handle already-initialized state:

```rust
#[tokio::test]
async fn test_my_feature() {
    // Ignore errors if already initialized
    let _ = init_tracing("console", None);

    // Test code...
}
```

## Troubleshooting

### Issue: "Tracer provider already initialized"

**Cause:** `init_tracing()` called multiple times.

**Solution:** Initialize once at application startup, or check if already initialized:

```rust
use agenkit::observability::tracing::get_tracer_if_initialized;

if get_tracer_if_initialized().is_none() {
    init_tracing("console", None)?;
}
```

### Issue: Traces not appearing in Jaeger

**Checklist:**

1. ✅ Is OTLP collector running? `curl http://localhost:4317`
2. ✅ Is endpoint correct in `init_tracing()`?
3. ✅ Are spans being created? (Check logs for span output)
4. ✅ Is sampling enabled? (`ParentBased(TraceIdRatioBased(rate))`, where `rate`
   defaults to `1.0` — sample everything — and is settable via
   `init_tracing_with_config`)
5. ✅ **Did you call `shutdown_observability()` before exit?** Without it, batched
   spans are silently dropped and Jaeger stays empty.

**Debug:**

```bash
# Check OTLP collector logs
docker logs otel-collector

# Use console exporter for debugging
init_tracing("console", None)?;
```

### Issue: Prometheus metrics not scraping

Agenkit Rust exposes no scrape endpoint. `init_metrics("prometheus", ...)`
returns an error rather than pretending to. Route metrics through a collector:

**Checklist:**

1. ✅ Are you calling `init_metrics("otlp", ...)`, not `"prometheus"`?
2. ✅ Did you call `shutdown_observability()` before exit? The reader exports on a
   60s interval, so a short-lived process delivers nothing without it.
3. ✅ Is the collector's `prometheus` exporter configured and its port scraped?

**Prometheus configuration — scrape the collector, not the app:**

```yaml
scrape_configs:
  - job_name: 'agenkit-via-collector'
    scrape_interval: 15s
    static_configs:
      - targets: ['otel-collector:8889']
```

### Issue: Audit log file not created

**Cause:** Parent directory doesn't exist or lacks permissions.

**Solution:**

```bash
# Create directory with correct permissions
mkdir -p /var/log/agenkit
chmod 755 /var/log/agenkit
```

### Issue: Trace context not propagating across agents

**Cause:** Message metadata not being passed through.

**Solution:** Ensure you're passing the response metadata to the next agent:

```rust
// Correct
let response1 = agent1.process(msg).await?;
let response2 = agent2.process(response1).await?;  // Metadata propagates

// Incorrect
let response1 = agent1.process(msg).await?;
let new_msg = Message::new("user", response1.content);  // Metadata lost!
let response2 = agent2.process(new_msg).await?;
```

## Examples

The `examples/` directory contains complete working examples:

### Basic Example

```bash
cargo run --example observability_basic --features=native
```

Demonstrates:
- Console tracing
- Prometheus metrics
- JSON logging
- Simple agent with middleware

### Distributed Example

```bash
cargo run --example observability_distributed --features=native
```

Demonstrates:
- Trace context propagation through Router → Processor → Aggregator pipeline
- Parent-child span relationships
- Per-agent metrics
- End-to-end request tracing

### Production Example

```bash
cargo run --example observability_production --features=native
```

Demonstrates:
- OTLP tracing (no fallback to console — the tonic channel connects lazily, so
  an unreachable collector does not surface as an error at init)
- Prometheus metrics
- Structured JSON logging
- Audit logging with session tracking
- Error handling and warning detection
- Query API usage

## Additional Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [W3C Trace Context Specification](https://www.w3.org/TR/trace-context/)
- [Jaeger UI Guide](https://www.jaegertracing.io/docs/latest/frontend-ui/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)

## API Reference

For detailed API documentation, run:

```bash
cargo doc --no-deps --open
```

This will generate and open the full rustdoc documentation for all modules.

---

**Last Updated:** August 2026
**Version:** see [`agenkit-rust/Cargo.toml`](../agenkit-rust/Cargo.toml) (not restated
here — it rots; see #874, following the #842 precedent)

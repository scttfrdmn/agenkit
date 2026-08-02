# Agenkit Rust Observability Guide

Production-grade monitoring, tracing, and logging for Agenkit-Rust agents.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Distributed Tracing](#distributed-tracing)
  - [tracing Crate Integration](#tracing-crate-integration)
  - [OpenTelemetry Setup](#opentelemetry-setup)
  - [Span Attributes](#span-attributes)
  - [Distributed Context Propagation](#distributed-context-propagation)
- [Metrics](#metrics)
  - [Built-in Metrics](#built-in-metrics)
  - [Prometheus Integration](#prometheus-integration)
  - [Custom Metrics](#custom-metrics)
- [Structured Logging](#structured-logging)
  - [tracing::instrument Macro](#tracinginstrument-macro)
  - [JSON Logging](#json-logging)
  - [Log Levels and Filtering](#log-levels-and-filtering)
- [Audit Logging](#audit-logging)
- [Full Observability Stack](#full-observability-stack)
- [Production Deployment](#production-deployment)

---

## Overview

Agenkit-Rust's observability stack is built on the Rust `tracing` ecosystem and OpenTelemetry:

| Layer | Crate | Purpose |
|-------|-------|---------|
| Tracing | `tracing` + `opentelemetry` | Distributed spans across agents |
| Metrics | `opentelemetry` + `prometheus` | Request counts, durations, errors |
| Logging | `tracing-subscriber` | Structured JSON logs with trace correlation |
| Audit | `agenkit::observability` | Compliance-ready event logs |

**Why `tracing` over `log`?**

The `tracing` crate captures structured, contextual diagnostics — not just text strings. It understands spans (duration), events (point-in-time), and fields (structured key-value data). This maps directly to OpenTelemetry concepts.

---

## Quick Start

Add dependencies:

```bash
cargo add tracing tracing-subscriber opentelemetry opentelemetry-otlp opentelemetry_sdk
cargo add agenkit --features observability
```

Minimal setup:

```rust
use agenkit::core::{Agent, AgentError, Message};
use agenkit::observability::{init_tracing, TracingMiddleware, MetricsMiddleware};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing (console output for development)
    init_tracing("console", None)?;

    // Wrap your agent with observability middleware
    let base_agent = MyAgent::new();
    let traced = TracingMiddleware::new(base_agent, Some("my-service"));
    let observed = MetricsMiddleware::new(traced);

    // All calls are now traced and metered
    let message = Message::user("Hello!");
    let response = observed.process(message).await?;
    println!("{}", response.content_as_str().unwrap_or(""));

    Ok(())
}
```

---

## Distributed Tracing

### tracing Crate Integration

The `tracing` crate provides the core primitives. Agenkit's `TracingMiddleware` creates spans automatically around every `process()` call.

**How spans are created:**

```rust
use agenkit::observability::TracingMiddleware;

// TracingMiddleware automatically creates a span like:
// Span {
//   name: "agent.process",
//   attributes: {
//     "agent.name": "my-agent",
//     "message.role": "user",
//     "message.length": 42,
//   }
// }
let agent = TracingMiddleware::new(base_agent, Some("my-service"))
    .with_attribute("environment", "production")
    .with_attribute("version", "1.0.0")
    .with_include_content(false);  // Omit message content from spans (privacy)
```

**Adding custom spans in your agent:**

```rust
use tracing::{info, warn, error, instrument, Span};
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;

pub struct AnalysisAgent;

#[async_trait]
impl Agent for AnalysisAgent {
    fn name(&self) -> &str { "analysis" }

    // #[instrument] creates a span for this function automatically
    #[instrument(
        name = "analysis.process",
        skip(self, message),
        fields(
            agent.name = "analysis",
            message.role = %message.role,
        )
    )]
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let text = message.content_as_str().unwrap_or("");

        // Record fields on the current span
        tracing::Span::current().record("input.length", text.len());

        info!(input = text, "starting analysis");

        // Create a child span for a sub-operation
        let result = {
            let _span = tracing::info_span!("tokenization").entered();
            let tokens = tokenize(text);
            tracing::Span::current().record("token.count", tokens.len());
            tokens
        };

        if result.is_empty() {
            warn!("no tokens produced from input");
            return Err(AgentError::InvalidInput("empty input".to_string()));
        }

        let analysis = analyze(&result);
        info!(
            token_count = result.len(),
            analysis_length = analysis.len(),
            "analysis complete"
        );

        Ok(Message::assistant(&analysis))
    }
}

fn tokenize(text: &str) -> Vec<&str> {
    text.split_whitespace().collect()
}

fn analyze(tokens: &[&str]) -> String {
    format!("Analyzed {} tokens", tokens.len())
}
```

### OpenTelemetry Setup

For production, export traces to Jaeger, Zipkin, or an OTLP collector:

```rust
use opentelemetry::global;
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::{runtime, trace as sdktrace};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};
use tracing_opentelemetry::OpenTelemetryLayer;

fn init_opentelemetry(
    service_name: &str,
    otlp_endpoint: &str,
) -> Result<opentelemetry_sdk::trace::Tracer, Box<dyn std::error::Error>> {
    let tracer = opentelemetry_otlp::new_pipeline()
        .tracing()
        .with_exporter(
            opentelemetry_otlp::new_exporter()
                .tonic()
                .with_endpoint(otlp_endpoint),
        )
        .with_trace_config(
            sdktrace::config()
                .with_resource(opentelemetry_sdk::Resource::new(vec![
                    opentelemetry::KeyValue::new("service.name", service_name.to_string()),
                    opentelemetry::KeyValue::new("service.version", env!("CARGO_PKG_VERSION")),
                ]))
                .with_sampler(sdktrace::Sampler::AlwaysOn),
        )
        .install_batch(runtime::Tokio)?;

    Ok(tracer)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize OpenTelemetry
    let tracer = init_opentelemetry(
        "my-agent-service",
        "http://localhost:4317",  // OTLP gRPC endpoint
    )?;

    // Build subscriber with OpenTelemetry layer
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new("info"))
        .with(tracing_subscriber::fmt::layer().json())
        .with(OpenTelemetryLayer::new(tracer))
        .init();

    // Your agent code here — all tracing calls are automatically exported
    let agent = TracingMiddleware::new(MyAgent::new(), Some("my-agent-service"));
    let response = agent.process(Message::user("Hello")).await?;

    // Ensure all spans are flushed before exit
    global::shutdown_tracer_provider();

    Ok(())
}
```

**Jaeger setup (docker-compose for development):**

```yaml
# docker-compose.yml
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"   # Jaeger UI
      - "4317:4317"     # OTLP gRPC
      - "4318:4318"     # OTLP HTTP
```

```bash
docker-compose up -d
# View traces at http://localhost:16686
```

### Span Attributes

Standard attributes set by `TracingMiddleware`:

| Attribute | Type | Description |
|-----------|------|-------------|
| `agent.name` | string | Agent's `name()` return value |
| `message.role` | string | `"user"`, `"assistant"`, etc. |
| `message.content_length` | int | Length of message content |
| `duration_ms` | float | Total processing time |
| `status` | string | `"ok"` or `"error"` |
| `error.type` | string | Error variant name (on failure) |
| `error.message` | string | Error message (on failure) |

**Adding custom attributes:**

```rust
use tracing::Span;

// In your process() implementation
async fn process(&self, message: Message) -> Result<Message, AgentError> {
    // Add attributes to the current span (created by TracingMiddleware)
    let span = Span::current();
    span.record("model.name", &self.model_name.as_str());
    span.record("temperature", &self.temperature);

    // ... processing ...
    Ok(response)
}
```

### Distributed Context Propagation

For multi-agent pipelines, trace context propagates automatically through `Message` metadata using W3C Trace Context:

```rust
use opentelemetry::propagation::Injector;
use opentelemetry::global::get_text_map_propagator;
use std::collections::HashMap;

// Inject trace context into outgoing message
fn inject_trace_context(message: Message) -> Message {
    let mut carrier = HashMap::new();
    get_text_map_propagator(|propagator| {
        propagator.inject(&mut carrier);
    });

    let mut msg = message;
    for (key, value) in carrier {
        msg = msg.with_metadata(&key, serde_json::json!(value));
    }
    msg
}
```

Agenkit's `TracingMiddleware` handles this automatically when you use the standard middleware stack.

---

## Metrics

### Built-in Metrics

`MetricsMiddleware` automatically collects:

| Metric | Type | Description |
|--------|------|-------------|
| `agent_requests_total` | Counter | Total requests processed |
| `agent_errors_total` | Counter | Total errors by error type |
| `agent_request_duration_ms` | Histogram | Request duration distribution |
| `agent_tokens_total` | Counter | Total tokens processed |

### Prometheus Integration

```bash
cargo add prometheus metrics metrics-exporter-prometheus
```

**Setup:**

```rust
use prometheus::{Encoder, TextEncoder, Counter, Histogram, HistogramOpts, Registry};
use std::sync::Arc;

pub struct AgentMetrics {
    pub requests_total: Counter,
    pub errors_total: Counter,
    pub duration_seconds: Histogram,
    registry: Registry,
}

impl AgentMetrics {
    pub fn new() -> Result<Self, Box<dyn std::error::Error>> {
        let registry = Registry::new();

        let requests_total = Counter::new(
            "agent_requests_total",
            "Total number of agent requests",
        )?;

        let errors_total = Counter::new(
            "agent_errors_total",
            "Total number of agent errors",
        )?;

        let duration_seconds = Histogram::with_opts(
            HistogramOpts::new(
                "agent_request_duration_seconds",
                "Agent request duration in seconds",
            )
            .buckets(vec![0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]),
        )?;

        registry.register(Box::new(requests_total.clone()))?;
        registry.register(Box::new(errors_total.clone()))?;
        registry.register(Box::new(duration_seconds.clone()))?;

        Ok(Self {
            requests_total,
            errors_total,
            duration_seconds,
            registry,
        })
    }

    pub fn gather_text(&self) -> String {
        let encoder = TextEncoder::new();
        let metric_families = self.registry.gather();
        let mut buffer = Vec::new();
        encoder.encode(&metric_families, &mut buffer).unwrap();
        String::from_utf8(buffer).unwrap()
    }
}
```

**Exposing metrics over HTTP:**

```rust
use axum::{routing::get, Router};
use std::sync::Arc;

async fn metrics_handler(
    axum::extract::State(metrics): axum::extract::State<Arc<AgentMetrics>>,
) -> String {
    metrics.gather_text()
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let metrics = Arc::new(AgentMetrics::new()?);

    let app = Router::new()
        .route("/metrics", get(metrics_handler))
        .with_state(Arc::clone(&metrics));

    let listener = tokio::net::TcpListener::bind("0.0.0.0:9090").await?;
    axum::serve(listener, app).await?;

    Ok(())
}
```

**Prometheus scrape config:**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'agenkit'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 15s
```

### Custom Metrics

```rust
use agenkit::observability::MetricsCollector;
use std::sync::Arc;
use std::time::Instant;

pub struct InstrumentedAgent<A: Agent> {
    inner: A,
    collector: Arc<MetricsCollector>,
}

impl<A: Agent> InstrumentedAgent<A> {
    pub fn new(inner: A, collector: Arc<MetricsCollector>) -> Self {
        Self { inner, collector }
    }
}

#[async_trait]
impl<A: Agent> Agent for InstrumentedAgent<A> {
    fn name(&self) -> &str { self.inner.name() }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let start = Instant::now();
        self.collector.increment_requests();

        let result = self.inner.process(message).await;

        let duration = start.elapsed();
        self.collector.record_duration(duration);

        match &result {
            Ok(_) => {},
            Err(_) => self.collector.increment_errors(),
        }

        result
    }
}
```

---

## Structured Logging

### tracing::instrument Macro

The `#[instrument]` macro is the primary way to add structured logging to agent methods:

```rust
use tracing::{info, warn, error, debug, instrument};
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;

pub struct ProcessingAgent {
    model: String,
    temperature: f64,
}

#[async_trait]
impl Agent for ProcessingAgent {
    fn name(&self) -> &str { "processor" }

    #[instrument(
        name = "processor.process",
        skip(self, message),          // Don't log these (can be large)
        fields(
            agent.name = "processor",
            model = %self.model,
            temperature = %self.temperature,
            message.role = %message.role,
        ),
        err,                          // Automatically log errors
    )]
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let text = message.content_as_str().unwrap_or("");
        debug!(input_length = text.len(), "processing message");

        if text.is_empty() {
            warn!("empty input received");
            return Err(AgentError::InvalidInput("empty input".to_string()));
        }

        // Simulate processing
        info!(model = %self.model, "calling LLM");
        let response = format!("Processed by {}: {}", self.model, text);

        info!(
            response_length = response.len(),
            "processing complete"
        );

        Ok(Message::assistant(&response))
    }
}
```

**Log levels guide:**

| Level | Use for |
|-------|---------|
| `error!` | Unexpected failures that need immediate attention |
| `warn!` | Recoverable issues; unexpected but handled |
| `info!` | Normal operation milestones |
| `debug!` | Detailed diagnostic information |
| `trace!` | Very detailed per-step diagnostics |

### JSON Logging

For production log ingestion (Datadog, CloudWatch, Elasticsearch):

```rust
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

fn init_json_logging() {
    tracing_subscriber::registry()
        .with(EnvFilter::try_from_default_env().unwrap_or_else(|_| {
            EnvFilter::new("info,agenkit=debug")
        }))
        .with(
            tracing_subscriber::fmt::layer()
                .json()                           // JSON format
                .with_current_span(true)          // Include span info
                .with_span_list(true)             // Include span hierarchy
                .with_target(true)                // Include module path
                .with_thread_ids(true)            // Include thread IDs
                .with_file(true)                  // Include source file
                .with_line_number(true),          // Include line number
        )
        .init();
}
```

**Sample JSON log output:**
```json
{
  "timestamp": "2026-03-17T12:34:56.789Z",
  "level": "INFO",
  "target": "my_agent::processing",
  "message": "processing complete",
  "span": {
    "name": "processor.process",
    "model": "gpt-4-turbo",
    "temperature": "0.7",
    "message.role": "user"
  },
  "fields": {
    "response_length": 156
  },
  "thread_id": "ThreadId(5)",
  "file": "src/agent.rs",
  "line": 42
}
```

### Log Levels and Filtering

Control log verbosity with environment variables:

```bash
# Production: info level
RUST_LOG=info cargo run

# Development: debug for your crate, info for dependencies
RUST_LOG=my_agent=debug,agenkit=debug,info cargo run

# Verbose tracing: trace everything
RUST_LOG=trace cargo run

# Per-module control
RUST_LOG=my_agent::patterns=debug,my_agent::adapters=warn cargo run
```

**Programmatic filtering:**

```rust
use tracing_subscriber::EnvFilter;

let filter = EnvFilter::new("info")
    .add_directive("agenkit=debug".parse().unwrap())
    .add_directive("my_agent::critical_path=trace".parse().unwrap());
```

---

## Audit Logging

For compliance, security monitoring, and forensics:

```rust
use agenkit::observability::{
    AuditLogger,
    AuditLoggerConfig,
    AuditEvent,
    AuditEventType,
    AuditSeverity,
};
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Configure audit logger
    let config = AuditLoggerConfig {
        log_file: std::path::PathBuf::from("./logs/audit.jsonl"),
        console_logging: true,
        min_severity: AuditSeverity::Info,
        rotate_size_mb: 100,
        retention_days: 90,
    };

    let audit = AuditLogger::new(config)?;

    // Log agent lifecycle events
    let mut started = AuditEvent {
        event_type: AuditEventType::AgentStarted,
        severity: AuditSeverity::Info,
        message: "Agent service started".to_string(),
        agent_name: Some("my-agent".to_string()),
        timestamp: chrono::Utc::now(),
        details: Default::default(),
    };
    started.details.insert("version".to_string(), json!("0.75.0"));
    started.details.insert("environment".to_string(), json!("production"));
    audit.log(&started)?;

    // Log each request
    let mut request_event = AuditEvent {
        event_type: AuditEventType::AgentCompleted,
        severity: AuditSeverity::Info,
        message: "Request processed successfully".to_string(),
        agent_name: Some("my-agent".to_string()),
        timestamp: chrono::Utc::now(),
        details: Default::default(),
    };
    request_event.details.insert("session_id".to_string(), json!("abc-123"));
    request_event.details.insert("duration_ms".to_string(), json!(142));
    audit.log(&request_event)?;

    // Query past events
    let recent_errors = audit.query(agenkit::observability::AuditFilter {
        event_type: Some(AuditEventType::AgentError),
        severity_min: Some(AuditSeverity::Error),
        since: Some(chrono::Utc::now() - chrono::Duration::hours(24)),
        limit: 100,
    });

    println!("Errors in last 24h: {}", recent_errors.len());

    Ok(())
}
```

---

## Full Observability Stack

Complete production setup integrating all observability layers:

```rust
use agenkit::core::{Agent, AgentError, Message};
use agenkit::observability::{
    init_tracing, init_metrics, configure_logging,
    TracingMiddleware, MetricsMiddleware, AuditLogger, AuditLoggerConfig,
};
use opentelemetry::global;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};
use std::sync::Arc;

struct ObservabilityStack {
    audit_logger: Arc<AuditLogger>,
}

impl ObservabilityStack {
    fn init(service_name: &str, otlp_endpoint: Option<&str>) -> Result<Self, Box<dyn std::error::Error>> {
        // 1. Initialize OpenTelemetry tracing
        let tracer = init_tracing(
            if otlp_endpoint.is_some() { "otlp" } else { "console" },
            otlp_endpoint,
        )?;

        // 2. Initialize metrics. "prometheus" is not available in this build —
        //    export OTLP and let a collector expose the scrape endpoint.
        init_metrics("otlp", otlp_endpoint)?;

        // 3. Initialize structured logging
        configure_logging("json", "info")?;

        // 4. Initialize audit logger
        std::fs::create_dir_all("./logs")?;
        let audit = AuditLogger::new(AuditLoggerConfig {
            log_file: "./logs/audit.jsonl".into(),
            console_logging: false,
            min_severity: agenkit::observability::AuditSeverity::Info,
            rotate_size_mb: 100,
            retention_days: 90,
        })?;

        Ok(Self {
            audit_logger: Arc::new(audit),
        })
    }

    fn wrap_agent<A: Agent + 'static>(&self, agent: A) -> impl Agent {
        let traced = TracingMiddleware::new(agent, None)
            .with_attribute("service.version", env!("CARGO_PKG_VERSION"))
            .with_include_content(false);

        MetricsMiddleware::new(traced)
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let obs = ObservabilityStack::init(
        "my-agent-service",
        std::env::var("OTLP_ENDPOINT").ok().as_deref(),
    )?;

    let base_agent = MyAgent::new();
    let agent = obs.wrap_agent(base_agent);

    // All requests are now:
    // - Traced with OpenTelemetry spans
    // - Metered with Prometheus counters and histograms
    // - Logged as structured JSON
    // - Audited for compliance

    let response = agent.process(Message::user("Hello")).await?;
    println!("{}", response.content_as_str().unwrap_or(""));

    // Flush telemetry on shutdown
    global::shutdown_tracer_provider();

    Ok(())
}
```

---

## Production Deployment

### Kubernetes with Prometheus and Jaeger

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-agent
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: agent
        image: my-org/my-agent:0.75.0
        env:
        - name: RUST_LOG
          value: "info,agenkit=debug"
        - name: OTLP_ENDPOINT
          value: "http://jaeger-collector:4317"
        ports:
        - containerPort: 8080   # Agent HTTP port
        - containerPort: 9090   # Prometheus metrics port
```

```yaml
# k8s/servicemonitor.yaml — for Prometheus Operator
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: my-agent
spec:
  selector:
    matchLabels:
      app: my-agent
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

### Grafana Dashboard Queries

**Request rate:**
```promql
rate(agent_requests_total[5m])
```

**Error rate:**
```promql
rate(agent_errors_total[5m]) / rate(agent_requests_total[5m])
```

**P95 latency:**
```promql
histogram_quantile(0.95, rate(agent_request_duration_seconds_bucket[5m]))
```

**Alert: High error rate:**
```yaml
# alerting rule
- alert: AgentHighErrorRate
  expr: rate(agent_errors_total[5m]) / rate(agent_requests_total[5m]) > 0.05
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "Agent error rate above 5%"
```

---

**Version**: v0.75.0
**Last Updated**: March 17, 2026

See also:
- [rust_safety.md](rust_safety.md) — Security audit logging
- [API.md](API.md) — TracingMiddleware, MetricsMiddleware API reference
- Examples: `cargo run --example observability_basic`
- Examples: `cargo run --example observability_distributed`
- Examples: `cargo run --example observability_production`

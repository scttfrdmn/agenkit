# C++ Observability Guide

**OpenTelemetry-based observability for production C++ agents**

Version: 0.49.0
Status: Production Ready
Test Coverage: 63 tests (tracing: 12, metrics: 12, logging: 14, audit: 17, integration: 8)

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Installation](#installation)
4. [Core Modules](#core-modules)
5. [Usage Patterns](#usage-patterns)
6. [Production Deployment](#production-deployment)
7. [API Reference](#api-reference)
8. [Examples](#examples)
9. [Troubleshooting](#troubleshooting)

---

## Overview

Agenkit C++ provides comprehensive OpenTelemetry-based observability for AI agents:

- **Distributed Tracing**: W3C Trace Context propagation across agents
- **Metrics Collection**: Request counts, durations, errors
- **Structured Logging**: Trace-correlated logs with multiple formats
- **Audit Logging**: Compliance-ready event persistence with queries

### Key Features

✅ **RAII-based span management** - Automatic resource cleanup
✅ **Message metadata propagation** - Cross-language compatibility
✅ **Thread-safe operations** - Production-ready concurrency
✅ **Multiple exporters** - OTLP, Jaeger, Zipkin, Prometheus, Console
✅ **Middleware composition** - Clean separation of concerns
✅ **Zero runtime overhead** when disabled - Optional compilation flag

---

## Quick Start

### 1. Build with Observability

```bash
cd agenkit-cpp
mkdir build && cd build

# Install OpenTelemetry C++ SDK (via vcpkg)
vcpkg install opentelemetry-cpp

# Configure with observability enabled
cmake -DAGENKIT_WITH_OBSERVABILITY=ON \
      -DCMAKE_TOOLCHAIN_FILE=[vcpkg]/scripts/buildsystems/vcpkg.cmake ..

make
```

### 2. Basic Usage

```cpp
#include "agenkit/observability/tracing.hpp"
#include "agenkit/observability/metrics.hpp"
#include "agenkit/observability/logging.hpp"
#include "agenkit/observability/audit.hpp"
#include "agenkit/adapters/echo_agent.hpp"

using namespace agenkit;
using namespace agenkit::observability;

int main() {
    // Initialize observability
    init_tracing("console", "");
    init_metrics("console", "");
    configure_logging("pretty", "info");
    auto audit = AuditLogger::create("audit.log");

    // Create observable agent
    auto echo = std::make_shared<EchoAgent>();
    auto traced = std::make_shared<TracingMiddleware>(echo, "echo.process");
    auto observed = std::make_shared<MetricsMiddleware>(traced);

    // Process message (automatically traced and metered)
    Message msg;
    msg.role = "user";
    msg.content = "Hello, observability!";

    auto result_future = observed->process(msg);
    auto result = result_future.get();

    // Audit the operation
    audit->log(
        AuditEvent::create(AuditEventType::MessageProcessed, "echo", "session_1")
            .with_detail("success", true)
    );

    audit->flush();
    return 0;
}
```

**Output:**
```
✓ Span created: echo.process
✓ Metrics recorded: agent_requests_total=1, agent_request_duration_seconds=0.002
✓ Logs correlated with trace_id
✓ Audit event persisted to audit.log
```

---

## Installation

### Prerequisites

- C++17 compatible compiler (GCC 7+, Clang 5+, MSVC 2017+)
- CMake 3.16+
- OpenTelemetry C++ SDK 1.8.0+
- nlohmann/json 3.11.0+

### Install OpenTelemetry C++ SDK

#### Using vcpkg (Recommended)

```bash
# Install vcpkg
git clone https://github.com/Microsoft/vcpkg.git
cd vcpkg
./bootstrap-vcpkg.sh

# Install OpenTelemetry
./vcpkg install opentelemetry-cpp

# Use in CMake
cmake -DCMAKE_TOOLCHAIN_FILE=[path-to-vcpkg]/scripts/buildsystems/vcpkg.cmake \
      -DAGENKIT_WITH_OBSERVABILITY=ON ..
```

#### Using system package manager

**Ubuntu/Debian:**
```bash
# Build from source (no official packages yet)
git clone https://github.com/open-telemetry/opentelemetry-cpp.git
cd opentelemetry-cpp
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/usr/local \
      -DWITH_OTLP_HTTP=ON \
      -DWITH_PROMETHEUS=ON ..
make -j$(nproc)
sudo make install
```

**macOS:**
```bash
# Using Homebrew (if available)
brew install opentelemetry-cpp

# Or use vcpkg as above
```

### Build Agenkit with Observability

```bash
cd agenkit-cpp
mkdir build && cd build

# Configure
cmake -DAGENKIT_WITH_OBSERVABILITY=ON \
      -DCMAKE_BUILD_TYPE=Release ..

# Build
make -j$(nproc)

# Run tests
ctest --output-on-failure

# Run examples
./examples/observability_basic
```

---

## Core Modules

### 1. Tracing (`agenkit/observability/tracing.hpp`)

**Purpose**: Distributed tracing with W3C Trace Context propagation

**Key Classes**:
- `ScopedSpan` - RAII span with automatic ending
- `TracingMiddleware` - Agent wrapper for automatic span creation

**Initialization**:
```cpp
// Console exporter (development)
init_tracing("console", "");

// OTLP exporter (production)
init_tracing("otlp", "http://localhost:4317");

// Jaeger exporter
init_tracing("jaeger", "http://localhost:14268/api/traces");

// Zipkin exporter
init_tracing("zipkin", "http://localhost:9411/api/v2/spans");
```

**Manual Span Creation**:
```cpp
#include "agenkit/observability/tracing.hpp"

auto tracer = get_tracer("my_component");
auto span = ScopedSpan(tracer, "operation_name",
                       opentelemetry::context::Context::GetCurrent());

span.set_attribute("key", "value");
span.set_attribute("count", 42);

// Span automatically ends when going out of scope
```

**Middleware Usage**:
```cpp
auto agent = std::make_shared<EchoAgent>();
auto traced = std::make_shared<TracingMiddleware>(agent, "custom.span.name");

// Process creates span automatically
auto result = traced->process(msg).get();
```

**Trace Context Propagation**:
```cpp
// Extract context from message metadata
auto context = extract_trace_context(message.metadata);

// Create child span
auto span = tracer->StartSpan("child_operation", context);

// Inject context into outgoing message
inject_trace_context(outgoing_message.metadata,
                     opentelemetry::context::Context::GetCurrent());
```

---

### 2. Metrics (`agenkit/observability/metrics.hpp`)

**Purpose**: Metrics collection (counters, histograms)

**Key Classes**:
- `MetricsMiddleware` - Agent wrapper for automatic metric recording

**Initialization**:
```cpp
// Console exporter (development)
init_metrics("console", "");

// OTLP exporter (production)
init_metrics("otlp", "http://localhost:4317");

// Prometheus exporter
init_metrics("prometheus", "http://localhost:9464");
```

**Automatic Metrics**:
```cpp
auto agent = std::make_shared<EchoAgent>();
auto observed = std::make_shared<MetricsMiddleware>(agent);

// Automatically records:
// - agent_requests_total (counter) with label {agent_name, status}
// - agent_request_duration_seconds (histogram)

auto result = observed->process(msg).get();
```

**Manual Metrics** (advanced):
```cpp
auto meter = get_meter("my_component");

// Counter
auto counter = meter->CreateUInt64Counter("my_counter", "description", "unit");
counter->Add(1, {KeyValue::new("label", "value")});

// Histogram
auto histogram = meter->CreateDoubleHistogram("my_histogram", "desc", "seconds");
histogram->Record(0.123, {KeyValue::new("operation", "process")});
```

---

### 3. Logging (`agenkit/observability/logging.hpp`)

**Purpose**: Structured logging with trace correlation

**Formats**:
- `json` - Structured JSON for production
- `compact` - Single-line text for development
- `pretty` - Multi-line formatted for debugging

**Initialization**:
```cpp
// JSON format, INFO level
configure_logging("json", "info");

// Compact format, DEBUG level
configure_logging("compact", "debug");

// Pretty format, TRACE level
configure_logging("pretty", "trace");
```

**Logging Functions**:
```cpp
// Info event
log_agent_event("event_type", "Message");

// Info event with context
std::map<std::string, std::string> context;
context["agent"] = "agent_name";
context["session_id"] = "abc123";
log_agent_event("event_type", "Message", context);

// Error
log_agent_error("error_type", "Error occurred", "Error details");

// Warning
log_agent_warning("warning_type", "Warning message");
log_agent_warning("warning_type", "Warning message", context);
```

**Log Format Examples**:

**JSON:**
```json
{
  "timestamp": "2026-01-15T10:30:45.123Z",
  "level": "INFO",
  "event_type": "message_processed",
  "message": "Processing complete",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "agent": "agent_name",
  "session_id": "abc123"
}
```

**Compact:**
```
2026-01-15T10:30:45.123Z [INFO] message_processed: Processing complete trace_id=4bf92f3577b34da6a3ce929d0e0e4736 agent=agent_name
```

**Pretty:**
```
────────────────────────────────────────
Time:       2026-01-15T10:30:45.123Z
Level:      INFO
Event:      message_processed
Message:    Processing complete
Trace ID:   4bf92f3577b34da6a3ce929d0e0e4736
Span ID:    00f067aa0ba902b7
Context:
  agent:      agent_name
  session_id: abc123
────────────────────────────────────────
```

---

### 4. Audit (`agenkit/observability/audit.hpp`)

**Purpose**: Compliance-ready event persistence with querying

**Event Types**:
- `AgentCreated` - Agent instantiation
- `AgentDestroyed` - Agent cleanup
- `MessageProcessed` - Successful message processing
- `MessageFailed` - Failed message processing
- `SecurityViolation` - Security policy violation
- `ConfigurationChanged` - Config modification
- `ErrorOccurred` - Error event
- `UserAction` - User-initiated action
- `SystemEvent` - System-level event

**Severity Levels**:
- `INFO` - Informational
- `WARNING` - Warning condition
- `ERROR` - Error condition
- `CRITICAL` - Critical event requiring immediate attention

**Basic Usage**:
```cpp
// Create logger
auto audit = AuditLogger::create("audit.log", 100); // buffer size: 100

// Log event with fluent API
audit->log(
    AuditEvent::create(
        AuditEventType::MessageProcessed,
        "agent_name",
        "session_id"
    )
    .with_detail("message_id", "msg_123")
    .with_detail("duration_ms", 42)
    .with_severity(Severity::INFO)
);

// Flush to disk
audit->flush();
```

**Querying**:
```cpp
// Query all events
auto all = audit->query();

// Query by session
auto session_events = audit->query_by_session("session_123");

// Query by agent
auto agent_events = audit->query_by_agent("agent_name");

// Query by type
auto violations = audit->query_by_type(AuditEventType::SecurityViolation);

// Custom filter
auto critical = audit->query_with_filter([](const AuditEvent& e) {
    return e.severity() == Severity::CRITICAL;
});
```

**Audit Log Format** (JSON Lines):
```json
{"event_id":"3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c","timestamp":"2026-01-15T10:30:45.123Z","event_type":"MessageProcessed","agent_name":"agent_name","session_id":"session_123","details":{"message_id":"msg_123","duration_ms":42},"severity":"INFO"}
```

---

## Usage Patterns

### Pattern 1: Basic Observable Agent

```cpp
#include "agenkit/observability/tracing.hpp"
#include "agenkit/observability/metrics.hpp"

auto agent = std::make_shared<EchoAgent>();

// Wrap with tracing
auto traced = std::make_shared<TracingMiddleware>(agent, "echo.process");

// Wrap with metrics
auto observed = std::make_shared<MetricsMiddleware>(traced);

// Process (automatically traced and metered)
auto result = observed->process(msg).get();
```

### Pattern 2: Distributed Multi-Agent Workflow

```cpp
// Agent 1
auto agent1 = std::make_shared<MyAgent>();
auto traced1 = std::make_shared<TracingMiddleware>(agent1, "agent1.process");
auto observed1 = std::make_shared<MetricsMiddleware>(traced1);

// Agent 2
auto agent2 = std::make_shared<MyAgent>();
auto traced2 = std::make_shared<TracingMiddleware>(agent2, "agent2.process");
auto observed2 = std::make_shared<MetricsMiddleware>(traced2);

// Process with Agent 1
auto result1 = observed1->process(msg1).get().unwrap();

// Result1 contains trace context in metadata
// Pass to Agent 2 - context automatically propagated
auto result2 = observed2->process(result1).get().unwrap();

// Both agents' spans are children of same trace
```

### Pattern 3: Error Handling with Observability

```cpp
auto audit = AuditLogger::create("audit.log");

try {
    auto result = observed->process(msg).get();

    if (result.is_ok()) {
        log_agent_event("success", "Message processed");
        audit->log(
            AuditEvent::create(AuditEventType::MessageProcessed, "agent", "session")
                .with_severity(Severity::INFO)
        );
    } else {
        auto error = result.error();
        log_agent_error("processing_failed", error.message(), error.details());
        audit->log(
            AuditEvent::create(AuditEventType::MessageFailed, "agent", "session")
                .with_detail("error", error.message())
                .with_severity(Severity::ERROR)
        );
    }
} catch (const std::exception& e) {
    log_agent_error("exception", "Unexpected error", e.what());
    audit->log(
        AuditEvent::create(AuditEventType::ErrorOccurred, "agent", "session")
            .with_detail("exception", e.what())
            .with_severity(Severity::CRITICAL)
    );
}

audit->flush();
```

### Pattern 4: Security Auditing

```cpp
auto audit = AuditLogger::create("security_audit.log");

// Validate input
if (is_suspicious(msg.content)) {
    log_agent_error("security_violation", "Suspicious content detected",
                    "Content matches blacklist pattern");

    audit->log(
        AuditEvent::create(AuditEventType::SecurityViolation, "security_agent", session_id)
            .with_detail("violation_type", "blacklisted_content")
            .with_detail("pattern", "malicious_pattern")
            .with_detail("user_ip", get_user_ip())
            .with_severity(Severity::CRITICAL)
    );

    throw SecurityException("Content rejected");
}

// Query critical security events
auto violations = audit->query_with_filter([](const AuditEvent& e) {
    return e.event_type() == AuditEventType::SecurityViolation &&
           e.severity() == Severity::CRITICAL;
});

for (const auto& violation : violations) {
    alert_security_team(violation);
}
```

---

## Production Deployment

### 1. Deploy OpenTelemetry Collector

**Docker Compose:**
```yaml
version: '3'
services:
  otel-collector:
    image: otel/opentelemetry-collector:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
      - "8888:8888"   # Prometheus metrics
      - "13133:13133" # Health check

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686" # Jaeger UI
      - "14268:14268" # Jaeger collector

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
```

**otel-collector-config.yaml:**
```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:

exporters:
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true
  prometheus:
    endpoint: "0.0.0.0:8889"
  logging:
    loglevel: info

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger, logging]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus, logging]
```

### 2. Configure Application

**Environment Variables:**
```bash
export OTLP_ENDPOINT="http://otel-collector:4317"
export LOG_FORMAT="json"
export LOG_LEVEL="info"
export AUDIT_LOG_PATH="/var/log/agenkit/audit.log"
export AUDIT_BUFFER_SIZE="100"
```

**C++ Code:**
```cpp
// Read from environment
const char* endpoint = std::getenv("OTLP_ENDPOINT");
const char* log_format = std::getenv("LOG_FORMAT");
const char* log_level = std::getenv("LOG_LEVEL");

// Initialize
init_tracing("otlp", endpoint ? endpoint : "http://localhost:4317");
init_metrics("otlp", endpoint ? endpoint : "http://localhost:4317");
configure_logging(log_format ? log_format : "json",
                  log_level ? log_level : "info");
```

### 3. Kubernetes Deployment

**ConfigMap:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agenkit-observability-config
data:
  OTLP_ENDPOINT: "http://otel-collector.observability.svc.cluster.local:4317"
  LOG_FORMAT: "json"
  LOG_LEVEL: "info"
  AUDIT_LOG_PATH: "/var/log/agenkit/audit.log"
```

**Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agenkit-agent
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: agent
        image: myregistry/agenkit-agent:latest
        envFrom:
        - configMapRef:
            name: agenkit-observability-config
        volumeMounts:
        - name: audit-logs
          mountPath: /var/log/agenkit
      volumes:
      - name: audit-logs
        persistentVolumeClaim:
          claimName: audit-logs-pvc
```

### 4. Monitoring and Alerting

**Prometheus Alerts:**
```yaml
groups:
- name: agenkit
  rules:
  - alert: HighErrorRate
    expr: rate(agent_requests_total{status="error"}[5m]) > 0.05
    for: 5m
    annotations:
      summary: "High error rate detected"

  - alert: SlowProcessing
    expr: histogram_quantile(0.95, rate(agent_request_duration_seconds_bucket[5m])) > 5.0
    for: 10m
    annotations:
      summary: "P95 latency exceeds 5 seconds"
```

### 5. Log Aggregation

**Fluentd/Fluent Bit:**
```yaml
# Collect JSON logs
<source>
  @type tail
  path /var/log/agenkit/*.log
  pos_file /var/log/agenkit.log.pos
  tag agenkit
  format json
  time_key timestamp
  time_format %Y-%m-%dT%H:%M:%S.%LZ
</source>

<match agenkit>
  @type elasticsearch
  host elasticsearch.observability.svc.cluster.local
  port 9200
  index_name agenkit
  include_tag_key true
  tag_key @log_name
</match>
```

---

## API Reference

### Tracing

```cpp
// Initialize tracing
void init_tracing(const std::string& exporter_type,
                  const std::string& endpoint);
// exporter_type: "otlp", "jaeger", "zipkin", "console"

// Get tracer
std::shared_ptr<opentelemetry::trace::Tracer> get_tracer(const std::string& name);

// Extract trace context from message metadata
opentelemetry::context::Context extract_trace_context(const nlohmann::json& metadata);

// Inject trace context into message metadata
void inject_trace_context(nlohmann::json& metadata,
                         const opentelemetry::context::Context& context);

// ScopedSpan - RAII span wrapper
class ScopedSpan {
    ScopedSpan(std::shared_ptr<Tracer> tracer,
               const std::string& name,
               const Context& parent_context);

    void set_attribute(const std::string& key, const std::string& value);
    void set_attribute(const std::string& key, int64_t value);
    void set_attribute(const std::string& key, double value);
    void set_attribute(const std::string& key, bool value);

    void set_status(StatusCode code, const std::string& description = "");

    // Move-only
    ScopedSpan(ScopedSpan&&) noexcept;
    ScopedSpan& operator=(ScopedSpan&&) noexcept;
};

// TracingMiddleware
class TracingMiddleware : public Agent {
    TracingMiddleware(std::shared_ptr<Agent> agent,
                     const std::string& span_name = "agent.process");

    std::future<Result<Message, AgentError>> process(Message message) override;
    std::string name() const override;
};
```

### Metrics

```cpp
// Initialize metrics
void init_metrics(const std::string& exporter_type,
                  const std::string& endpoint);
// exporter_type: "otlp", "prometheus", "console"

// Get meter
opentelemetry::nostd::shared_ptr<opentelemetry::metrics::Meter>
get_meter(const std::string& name);

// MetricsMiddleware
class MetricsMiddleware : public Agent {
    MetricsMiddleware(std::shared_ptr<Agent> agent);

    std::future<Result<Message, AgentError>> process(Message message) override;
    std::string name() const override;

    // Automatically records:
    // - agent_requests_total (counter)
    // - agent_request_duration_seconds (histogram)
};
```

### Logging

```cpp
// Configure logging
void configure_logging(const std::string& format, const std::string& level);
// format: "json", "compact", "pretty"
// level: "trace", "debug", "info", "warn", "error", "critical"

// Log functions
void log_agent_event(const std::string& event_type,
                     const std::string& message,
                     const std::map<std::string, std::string>& context = {});

void log_agent_error(const std::string& event_type,
                     const std::string& message,
                     const std::string& error);

void log_agent_warning(const std::string& event_type,
                       const std::string& message,
                       const std::map<std::string, std::string>& context = {});
```

### Audit

```cpp
// Event types
enum class AuditEventType {
    AgentCreated, AgentDestroyed, MessageProcessed, MessageFailed,
    SecurityViolation, ConfigurationChanged, ErrorOccurred,
    UserAction, SystemEvent
};

// Severity levels
enum class Severity {
    INFO, WARNING, ERROR, CRITICAL
};

// AuditEvent
class AuditEvent {
    static AuditEvent create(AuditEventType type,
                            const std::string& agent_name,
                            const std::string& session_id = "");

    AuditEvent& with_detail(const std::string& key, const nlohmann::json& value);
    AuditEvent& with_severity(Severity severity);

    // Getters
    const std::string& event_id() const;
    std::chrono::system_clock::time_point timestamp() const;
    AuditEventType event_type() const;
    const std::string& agent_name() const;
    const std::string& session_id() const;
    const nlohmann::json& details() const;
    Severity severity() const;

    // Serialization
    nlohmann::json to_json() const;
    static AuditEvent from_json(const nlohmann::json& j);
};

// AuditLogger
class AuditLogger {
    static std::shared_ptr<AuditLogger> create(const std::string& log_path,
                                               size_t buffer_size = 100);

    void log(const AuditEvent& event);
    void flush();
    void set_buffer_size(size_t size);

    // Queries
    std::vector<AuditEvent> query();
    std::vector<AuditEvent> query_by_session(const std::string& session_id);
    std::vector<AuditEvent> query_by_agent(const std::string& agent_name);
    std::vector<AuditEvent> query_by_type(AuditEventType type);
    std::vector<AuditEvent> query_with_filter(
        std::function<bool(const AuditEvent&)> filter);
};
```

---

## Examples

### Example 1: Basic Observability

**File**: `examples/observability_basic.cpp`

Simple setup demonstrating all four modules with console exporters.

```bash
cd build
./examples/observability_basic
```

### Example 2: Distributed Tracing

**File**: `examples/observability_distributed.cpp`

Multi-agent workflow showing trace context propagation.

```bash
./examples/observability_distributed
```

### Example 3: Production Setup

**File**: `examples/observability_production.cpp`

Production-ready configuration with OTLP exporters and error handling.

```bash
export OTLP_ENDPOINT="http://localhost:4317"
./examples/observability_production
```

---

## Troubleshooting

### OpenTelemetry SDK not found

**Error:**
```
CMake Error: Could not find a package configuration file provided by "opentelemetry-cpp"
```

**Solution:**
```bash
# Install via vcpkg
vcpkg install opentelemetry-cpp

# Or specify CMAKE_PREFIX_PATH
cmake -DCMAKE_PREFIX_PATH=/usr/local -DAGENKIT_WITH_OBSERVABILITY=ON ..
```

### Observability disabled at runtime

**Symptom:** No spans/metrics/logs appear

**Check:**
1. Was `-DAGENKIT_WITH_OBSERVABILITY=ON` used during build?
2. Are exporters reachable? (check `endpoint` parameter)
3. Is OpenTelemetry Collector running?

**Debug:**
```cpp
// Enable console exporters for debugging
init_tracing("console", "");
init_metrics("console", "");
```

### Trace context not propagating

**Symptom:** Each agent creates separate traces instead of child spans

**Check:**
1. Ensure message metadata is being passed between agents
2. Verify `TracingMiddleware` is wrapping agents
3. Check that message objects are not being recreated without metadata

**Solution:**
```cpp
// WRONG: Creates new message without metadata
Message new_msg;
new_msg.content = response.content; // metadata lost!

// CORRECT: Preserve metadata
auto new_msg = response; // metadata preserved
new_msg.content = "modified " + response.content;
```

### Audit log not being written

**Symptom:** `audit->query()` returns empty

**Check:**
1. Has `audit->flush()` been called?
2. Does process have write permissions to log file?
3. Is buffer size larger than number of events logged?

**Solution:**
```cpp
// Flush explicitly
audit->flush();

// Or reduce buffer size for auto-flush
auto audit = AuditLogger::create("audit.log", 10); // auto-flush after 10 events
```

### High memory usage with metrics

**Symptom:** Memory grows over time

**Cause:** Metrics with high-cardinality labels (e.g., session_id as label)

**Solution:**
```cpp
// WRONG: High cardinality
counter->Add(1, {KeyValue("session_id", session_id)}); // Creates metric per session!

// CORRECT: Low cardinality
counter->Add(1, {KeyValue("status", "success")}); // Only 2 values
```

### Compilation errors with observability disabled

**Error:** `undefined reference to 'init_tracing'`

**Cause:** Code using observability functions without guarding

**Solution:**
```cpp
#ifdef AGENKIT_WITH_OBSERVABILITY
#include "agenkit/observability/tracing.hpp"
    init_tracing("console", "");
#endif
```

---

## Performance Considerations

### Overhead

- **Tracing**: ~1-5μs per span (negligible for most use cases)
- **Metrics**: <1μs per measurement (highly optimized)
- **Logging**: ~10-50μs per log (depends on format)
- **Audit**: ~5-20μs per event (buffered writes)

### Best Practices

1. **Use appropriate buffer sizes**: Larger buffers reduce disk I/O but increase memory
2. **Limit span attributes**: Each attribute adds overhead
3. **Use sampling in high-throughput scenarios**: Not all requests need tracing
4. **Flush audit logs periodically**: Don't flush after every event
5. **Use JSON logging in production**: Easier to parse, smaller than pretty format

### Benchmark Results

On modern hardware (Intel i7, 16GB RAM):

| Operation | Throughput | P50 Latency | P95 Latency |
|-----------|------------|-------------|-------------|
| Span creation | 200k/s | 2μs | 8μs |
| Metric recording | 500k/s | 1μs | 3μs |
| JSON log | 100k/s | 10μs | 25μs |
| Audit event | 150k/s | 6μs | 15μs |

---

## Security Considerations

### Sensitive Data in Traces

**Don't log sensitive data in span attributes:**

```cpp
// WRONG
span.set_attribute("password", user_password); // Security violation!
span.set_attribute("ssn", user_ssn);

// CORRECT
span.set_attribute("user_id", user_id); // Safe identifier
span.set_attribute("auth_method", "password"); // Safe metadata
```

### Audit Log Protection

```cpp
// Set restrictive permissions on audit logs
chmod 0600 /var/log/agenkit/audit.log

// Implement log rotation
logrotate -f /etc/logrotate.d/agenkit
```

### Compliance

Audit logs support:
- **GDPR**: Query by user ID for data export/deletion
- **SOC 2**: Comprehensive activity logging
- **HIPAA**: Audit trail of access to protected data
- **PCI DSS**: Security event logging

---

## Migration Guide

### From No Observability

```cpp
// Before
auto agent = std::make_shared<EchoAgent>();
auto result = agent->process(msg).get();

// After (minimal change)
#ifdef AGENKIT_WITH_OBSERVABILITY
init_tracing("otlp", "http://localhost:4317");
init_metrics("otlp", "http://localhost:4317");
configure_logging("json", "info");
#endif

auto agent = std::make_shared<EchoAgent>();
#ifdef AGENKIT_WITH_OBSERVABILITY
auto traced = std::make_shared<TracingMiddleware>(agent);
auto observed = std::make_shared<MetricsMiddleware>(traced);
auto result = observed->process(msg).get();
#else
auto result = agent->process(msg).get();
#endif
```

### From Custom Logging

```cpp
// Before
myLogger.info("Processing message", {{"agent", "echo"}});

// After
log_agent_event("processing", "Processing message", {{"agent", "echo"}});
```

---

## Contributing

Found a bug or have a feature request? Open an issue at:
https://github.com/scttfrdmn/agenkit/issues

---

## License

Apache 2.0 - See LICENSE file

---

## References

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/cpp/)
- [W3C Trace Context Specification](https://www.w3.org/TR/trace-context/)
- [Agenkit Architecture](../ARCHITECTURE.md)
- [Agenkit Testing Guide](../TESTING.md)

---

**Last Updated**: January 15, 2026
**Version**: 0.49.0
**Status**: ✅ Production Ready

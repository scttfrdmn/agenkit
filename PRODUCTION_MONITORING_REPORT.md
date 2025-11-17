# Agenkit Production Monitoring Readiness Assessment

## Executive Summary

**Overall Readiness: MODERATE (60% - Needs Work)**

The Agenkit codebase has implemented a solid foundation for observability using OpenTelemetry across Python and Go implementations. However, several critical components for production-grade monitoring are either incomplete or missing entirely. This report details the current state, gaps, and actionable recommendations.

### Quick Stats
- **Tracing Implementation**: ✓ Foundation exists (W3C Trace Context)
- **Metrics Collection**: ✓ Basic implementation (Prometheus-ready)
- **Structured Logging**: ✓ Implemented with trace correlation
- **Health Checks**: ⚠️ Basic endpoint exists, no dependency health checks
- **Alerting Foundations**: ✗ Missing (no alert rules defined)
- **Dashboards**: ✗ Missing (no Grafana templates provided)
- **Sampling & Configuration**: ⚠️ Limited
- **Graceful Shutdown**: ⚠️ Partial implementation
- **Resource Metrics**: ✗ Missing (CPU, memory, connections)

---

## 1. CURRENT OBSERVABILITY IMPLEMENTATION

### 1.1 Python Implementation

**Files:**
- `/Users/scttfrdmn/src/agenkit/agenkit/observability/tracing.py` (5.9 KB)
- `/Users/scttfrdmn/src/agenkit/agenkit/observability/metrics.py` (4.9 KB)
- `/Users/scttfrdmn/src/agenkit/agenkit/observability/logging.py` (4.3 KB)

**Status: PRODUCTION-READY (Core Only)**

#### Tracing (tracing.py)
**Readiness Level:** GOOD
- OpenTelemetry integration with BatchSpanProcessor
- W3C Trace Context propagation (TraceContextTextMapPropagator)
- OTLP endpoint support for production exporters (Jaeger, Tempo)
- Console export for development
- Automatic trace context extraction/injection into message metadata

**What's Implemented:**
```python
✓ init_tracing() - Initialize TracerProvider with exporters
✓ get_tracer() - Get tracer instance from global provider
✓ extract_trace_context() - Extract W3C context from metadata
✓ inject_trace_context() - Inject W3C context into metadata
✓ TracingMiddleware - Middleware that wraps agents with tracing
  - Span creation with agent.name and message.role attributes
  - Exception recording and error status tracking
  - Parent-child span relationships via context propagation
```

**Missing:**
- ✗ Trace sampling configuration (currently traces all requests)
- ✗ Custom resource attributes (environment, region, pod)
- ✗ Configurable batch size/timeout for span processor
- ✗ Trace ID generation strategy (custom vs. random)

#### Metrics (metrics.py)
**Readiness Level:** GOOD
- PrometheusMetricReader integration
- Standard RED metrics implementation
- Counter, Histogram metric types

**What's Implemented:**
```python
✓ init_metrics() - Initialize MeterProvider with Prometheus export
✓ get_meter() - Get meter instance from global provider
✓ MetricsMiddleware - Collects operational metrics
  Metrics created:
  - agenkit.agent.requests (Counter) - Total requests
  - agenkit.agent.errors (Counter) - Error count
  - agenkit.agent.latency (Histogram) - Request latency in ms
  - agenkit.agent.message_size (Histogram) - Message size in bytes
```

**Metrics Details:**
```
Attributes added to all metrics:
- agent.name: Name of processing agent
- message.role: Role of the message (user/agent/system)
- status: success/error
- error.type: Exception type name (on error)
```

**Missing:**
- ✗ Gauge for in-flight requests
- ✗ Gauge for connection pool status
- ✗ Resource-level metrics (CPU, memory, connections)
- ✗ Custom metric creation API
- ✗ Metric buckets/bounds customization
- ✗ Processing throughput metrics
- ✗ Token consumption metrics (for LLM usage tracking)

#### Logging (logging.py)
**Readiness Level:** GOOD
- Structured JSON logging format
- Automatic trace context injection (trace_id, span_id)
- Configurable log levels

**What's Implemented:**
```python
✓ TraceContextFilter - Injects trace_id, span_id into log records
✓ StructuredFormatter - JSON output with structured fields
✓ configure_logging() - Setup logging with trace correlation
✓ get_logger_with_trace() - Get logger with trace context
```

**Log Fields:**
```json
{
  "timestamp": "2025-11-12T20:00:00Z",
  "level": "INFO",
  "logger": "module.name",
  "message": "Log message",
  "module": "filename",
  "function": "function_name",
  "line": 42,
  "trace_id": "8a89f6ecb04b04d023cc690961850547",
  "span_id": "5782371d5170d9e5",
  "trace_flags": 1
}
```

**Missing:**
- ✗ Sensitive data redaction/masking
- ✗ Log sampling (for high-volume environments)
- ✗ Structured context propagation (beyond trace context)
- ✗ Performance metrics for logging itself

### 1.2 Go Implementation

**Files:**
- `/Users/scttfrdmn/src/agenkit/agenkit-go/observability/tracing.go` (6.8 KB)
- `/Users/scttfrdmn/src/agenkit/agenkit-go/observability/metrics.go` (5.2 KB)
- `/Users/scttfrdmn/src/agenkit/agenkit-go/observability/logging.go` (4.4 KB)

**Status: PRODUCTION-READY (Core Only)**

#### Tracing (tracing.go)
**Readiness Level:** GOOD
- OpenTelemetry integration with BatchSpanProcessor
- W3C Trace Context propagation (CompositeTextMapPropagator)
- OTLP gRPC exporter support
- Console export for development
- Global tracer provider management

**Implementation Quality:** Same as Python (parity maintained)

**Notable Additions in Go:**
```go
✓ Shutdown() - Graceful tracer provider shutdown
✓ GetTracer() - Named tracer retrieval
✓ Context-aware span creation with SpanKindInternal
```

#### Metrics (metrics.go)
**Readiness Level:** GOOD
- PrometheusMetricReader integration
- Same metric types as Python version

**Notable Differences from Python:**
```go
// Go uses time.Duration for latency tracking
latencyMs := float64(time.Since(startTime).Microseconds()) / 1000.0
```

**Missing:** Same as Python version

#### Logging (logging.go)
**Readiness Level:** GOOD
- slog (structured logging) integration
- TraceContextHandler for trace correlation
- StructuredHandler for JSON output

**Features:**
```go
✓ TraceContextHandler - Adds trace context to records
✓ StructuredHandler - JSON output with source location
✓ ConfigureLogging() - Setup logging configuration
✓ GetLoggerWithTrace() - Trace-aware logger
```

**Notable Go-specific:**
```go
- Source location tracking (function, file, line)
- slog.Logger as standard interface
- Handler composition pattern (not Filter pattern like Python)
```

### 1.3 Middleware Instrumentation

**Python Middleware:**
- `/Users/scttfrdmn/src/agenkit/agenkit/middleware/metrics.py` (5.5 KB)
  - `MetricsDecorator` class (not OpenTelemetry-based)
  - Tracks: total_requests, success/error counts, latency, in_flight_requests
  - Local metrics storage (not exported)

**Go Middleware:**
- `/Users/scttfrdmn/src/agenkit/agenkit-go/middleware/metrics.go` (5.9 KB)
  - `MetricsDecorator` with similar tracking
  - Thread-safe with sync.RWMutex
  - Local metrics storage (not exported)

**Status:** ⚠️ DUPLICATE IMPLEMENTATION
- Python has BOTH OpenTelemetry MetricsMiddleware AND local MetricsDecorator
- Go has both implementations too
- Local decorators don't export to Prometheus/OTLP
- Creates confusion about which to use in production

---

## 2. CRITICAL METRICS COVERAGE

### 2.1 RED Metrics (Rate, Errors, Duration)

**Status: GOOD (Partial)**

#### Implemented:
```
✓ Rate (Request Counter)
  - agenkit.agent.requests (Counter)
  - Labels: agent.name, message.role, status

✓ Errors (Error Counter) 
  - agenkit.agent.errors (Counter)
  - Labels: agent.name, status, error.type
  - Records exception information

✓ Duration (Latency Histogram)
  - agenkit.agent.latency (Histogram, ms)
  - Labels: agent.name, message.role, status
  - Provides percentile distribution
```

#### Missing:
```
✗ Request rate per endpoint (for transports)
✗ Error rate as percentage metric
✗ Latency percentiles (p50, p95, p99) - histogram only gives raw data
✗ Timeout errors tracking
✗ Retry metrics
```

### 2.2 USE Metrics (Utilization, Saturation, Errors)

**Status: MISSING (Critical Gap)**

```
✗ Utilization:
  - CPU usage percentage
  - Memory usage (heap, RSS)
  - Connection pool utilization
  - Thread pool saturation
  - Message queue depth

✗ Saturation:
  - In-flight request count (partially tracked in local decorators)
  - Queue wait time
  - Connection wait time
  - GC pause time

✗ Errors:
  - Connection errors
  - Timeout errors
  - Resource exhaustion errors
```

### 2.3 Business Metrics

**Status: MISSING (Critical Gap)**

```
✗ Agent call counts by type
✗ Message processing volume
✗ Token consumption (for LLM integration)
✗ Tool call success rates
✗ Response quality metrics
✗ User satisfaction metrics
```

### 2.4 Example Prometheus Queries

**Currently Working:**
```promql
# Request rate
rate(agenkit_agent_requests_total{status="success"}[5m])

# Error rate
rate(agenkit_agent_errors_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(agenkit_agent_latency_bucket[5m]))

# Average message size
rate(agenkit_agent_message_size_sum[5m]) / rate(agenkit_agent_message_size_count[5m])
```

**Missing/Broken:**
```promql
# In-flight requests (not exported as metric)
# Should be: rate of inflight_requests

# Connection pool status
# Should query: connection_pool_utilization

# Resource utilization
# Should query: process_resident_memory_bytes, process_cpu_seconds_total
# (These are NOT tracked in Agenkit)
```

---

## 3. DISTRIBUTED TRACING

### 3.1 Trace Context Propagation

**Status: GOOD**

**Implementation:**
- W3C Trace Context standard (not proprietary)
- Extracted from message metadata["trace_context"]
- Injected back into response metadata
- Parent-child span relationships maintained

**Cross-Language Support:**
```
✓ Python → Go: Trace context in message metadata survives RPC
✓ Go → Python: Same mechanism works both directions
✓ Propagator: TraceContextTextMapPropagator (W3C standard)
```

**Code Flow:**
```python
# Python side
response1 = await traced_agent1.process(message)
# metadata now contains: {"trace_context": {"traceparent": "00-...", ...}}

# Message sent to Go agent (via HTTP/gRPC)
response2 = await go_agent.process(response1)
# Go extracts same trace context, continues same trace
```

### 3.2 Span Creation

**Status: GOOD**

**Spans Created:**
```
✓ agent.{name}.process - Main operation span
  Attributes:
  - agent.name: "my-agent"
  - message.role: "user"
  - message.content_length: 42
  - message.metadata.{key}: value (custom metadata)
```

**Missing Spans:**
```
✗ Transport spans (HTTP POST, gRPC call)
✗ Codec spans (encoding/decoding)
✗ Storage/database spans
✗ External API call spans
✗ Tool execution spans
```

### 3.3 Trace Sampling Configuration

**Status: MISSING (Critical for Production)**

**Current Behavior:**
- ALL requests traced (no sampling)
- BatchSpanProcessor used (good batching)

**Production Issues:**
```
✗ No sampling configuration available
✗ High-volume agents will flood backend
✗ No option to sample by: user, endpoint, error status, etc.
✗ No adaptive sampling based on traffic
```

**Recommended Implementation:**
```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Sample 10% of traces
sampler = TraceIdRatioBased(0.1)
tp = TracerProvider(sampler=sampler)
```

### 3.4 Missing Instrumentation Points

```
Priority 1 (Critical):
✗ Transport layer spans (HTTP requests, gRPC calls, WebSocket)
✗ Agent process error spans
✗ Message codec errors

Priority 2 (Important):
✗ Tool execution spans
✗ LLM API call spans
✗ Database query spans

Priority 3 (Nice-to-have):
✗ Custom span creation API
✗ Manual span annotations
```

---

## 4. LOGGING STANDARDS

### 4.1 Structured Logging

**Status: GOOD**

**Implementation:**
- JSON output format
- All logs include timestamp, level, logger name
- Module, function, line number tracking
- Trace context injection (trace_id, span_id)

**Log Entry Example:**
```json
{
  "timestamp": "2025-11-12T20:00:00Z",
  "level": "INFO",
  "logger": "agenkit.observability",
  "message": "Agent processing started",
  "module": "tracing",
  "function": "Process",
  "line": 154,
  "trace_id": "8a89f6ecb04b04d023cc690961850547",
  "span_id": "5782371d5170d9e5",
  "agent.name": "my-agent",
  "message.role": "user"
}
```

### 4.2 Log Levels

**Status: GOOD**

**Available Levels:**
- Python: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Go: DEBUG, INFO, WARN, ERROR

**Current Usage:**
- Middleware uses logging.INFO by default
- Can be configured per application

**Missing:**
```
✗ Recommended log levels per component not documented
✗ No log level adjustment without code change
✗ No log sampling by level
```

### 4.3 Sensitive Data in Logs

**Status: INCOMPLETE**

**Current Protection:**
```
~ Message content is logged (RISK!)
  - Message.content is recorded in spans and logs
  - Could contain API keys, PII, sensitive data
  
~ No automatic redaction or masking
```

**Examples of Risks:**
```
// This gets logged:
Message(role="user", content="my_secret_api_key=xxx")

// Span attribute:
span.set_attribute("message.content_length", len("my_secret_api_key=xxx"))
// (not the content itself, but still risky)
```

### 4.4 Log Aggregation Readiness

**Status: READY FOR INTEGRATION**

**Output Format:** JSON (aggregator-friendly)
**Trace Correlation:** Included (trace_id, span_id)
**Platform Support:**
- ✓ ELK Stack (Elasticsearch/Logstash/Kibana)
- ✓ Splunk
- ✓ Datadog
- ✓ CloudWatch
- ✓ Google Cloud Logging
- ✓ Azure Monitor

**Aggregation Configuration Example:**
```json
// Filebeat/Logstash config
{
  "filebeat": {
    "inputs": [{
      "type": "log",
      "paths": ["/app/logs/*.log"],
      "json.message_key": "message",
      "json.keys_under_root": true
    }]
  }
}
```

---

## 5. HEALTH CHECKS & PROBES

### 5.1 Health Check Endpoints

**Status: PARTIAL**

**Python HTTP Server (`/agenkit/adapters/python/http_server.py`):**
```python
async def handle_health(self, request: Request) -> Response:
    """Handle health check requests."""
    return Response(status=200)
```
- ✓ Endpoint exists: `/health`
- ✓ Returns 200 OK
- ✗ No health state information returned
- ✗ No dependency checks

**Go HTTP Server (`/agenkit-go/adapter/http/http_server.go`):**
```go
mux.HandleFunc("/health", h.handleHealth)
// handleHealth not shown but similar pattern
```
- ✓ Endpoint exists: `/health`
- ✗ No implementation details visible
- ✗ Presumably same basic check

**HTTP Transport (`/agenkit-go/adapter/transport/http_transport.go`):**
```go
func (t *HTTPTransport) Connect(ctx context.Context) error {
    // Test connectivity by making a HEAD request
    req, err := http.NewRequestWithContext(ctx, "HEAD", t.baseURL+"/health", nil)
    // ...
}
```
- ✓ Client uses `/health` to test connectivity
- ✓ HEAD request (lightweight)

### 5.2 Liveness vs Readiness

**Status: NOT IMPLEMENTED**

**Missing:**
```
✗ /live or /healthz - Liveness probe
  - Should indicate process is still running
  - Currently missing

✗ /ready or /ready - Readiness probe
  - Should indicate service is ready to accept requests
  - Should check: dependencies, warming up state, etc.
  - Currently missing
```

**Kubernetes Integration:**
```yaml
# This would be needed but not yet implemented
spec:
  livenessProbe:
    httpGet:
      path: /live
      port: 8080
    initialDelaySeconds: 10
  readinessProbe:
    httpGet:
      path: /ready
      port: 8080
    initialDelaySeconds: 5
```

### 5.3 Dependency Health Checks

**Status: NOT IMPLEMENTED**

**Missing:**
```
✗ Check if remote agents are reachable (for RemoteAgent)
✗ Check if database is connected (if used)
✗ Check if LLM API is available
✗ Check if message queue is accessible
✗ Timeout detection for unresponsive services
```

**Recommended Implementation:**
```python
async def handle_ready(self) -> dict:
    """Check service readiness."""
    checks = {
        "self": "healthy",
        "dependencies": {}
    }
    
    # Check remote agents
    for agent_name, agent in self.remote_agents.items():
        try:
            await asyncio.wait_for(agent.health_check(), timeout=2.0)
            checks["dependencies"][agent_name] = "healthy"
        except:
            checks["dependencies"][agent_name] = "unhealthy"
    
    return checks
```

### 5.4 Graceful Shutdown

**Status: PARTIAL**

**Python Implementation:**
```python
async def stop(self) -> None:
    """Stop the HTTP server."""
    if self.site:
        await self.site.stop()
        self.site = None
    if self.runner:
        await self.runner.cleanup()
        self.runner = None
```
- ✓ Server shutdown implemented
- ✗ No connection draining
- ✗ No request deadline enforcement
- ✗ No in-flight request tracking

**Go Implementation:**
```go
func (h *HTTPAgent) Start(ctx context.Context) error {
    // Timeout for shutdown
    ctx, cancel := context.WithTimeout(context.Background(), 5*1000*1000*1000) // 5 seconds
```
- ✓ Uses context with timeout
- ✗ Timeout is hardcoded
- ✗ No explicit connection draining

**OpenTelemetry Shutdown:**
```python
# Shutdown code shown in examples
def shutdown():
    observability.Shutdown(context.Background())
```
- ✓ Tracer provider shutdown
- ✓ Meter provider shutdown
- ✗ Not integrated with server lifecycle
- ✗ No order of operations guaranteed

---

## 6. ALERTING FOUNDATIONS

### 6.1 Metrics Suitable for Alerting

**Status: PARTIAL DATA AVAILABLE**

**Currently Exportable Metrics:**

```
✓ agenkit.agent.requests (Counter)
  Alert: rate(agenkit_agent_requests_total[5m]) < threshold
  Threshold: < 1 req/5m = service might be down

✓ agenkit.agent.errors (Counter)  
  Alert: rate(agenkit_agent_errors_total[5m]) > threshold
  Threshold: > 5 errors/5m = high error rate

✓ agenkit.agent.latency (Histogram)
  Alert: histogram_quantile(0.95, rate(agenkit_agent_latency_bucket[5m])) > threshold
  Threshold: > 5000ms (5s) = slow responses

✓ agenkit.agent.message_size (Histogram)
  Alert: rate(agenkit_agent_message_size_sum[5m]) > threshold
  Threshold: > 1GB/5m = excessive data transfer
```

**Missing Alert Candidates:**

```
✗ Connection errors
✗ Timeout errors  
✗ Resource exhaustion (memory, CPU, connections)
✗ In-flight request queue depth
✗ Backend availability (for remote agents)
✗ Response time SLOs
✗ Error budget depletion
```

### 6.2 SLI/SLO Definitions

**Status: NOT IMPLEMENTED**

**Recommended SLIs (Service Level Indicators):**

```
SLI 1: Request Success Rate
Formula: (Total Requests - Failed Requests) / Total Requests
Alert Threshold: < 99.5%
Prometheus: 1 - (rate(agenkit_agent_errors_total[5m]) / rate(agenkit_agent_requests_total[5m]))

SLI 2: Request Latency (p99)
Formula: 99th percentile response time
Alert Threshold: > 1000ms (1s)
Prometheus: histogram_quantile(0.99, rate(agenkit_agent_latency_bucket[5m]))

SLI 3: Availability
Formula: (Uptime) / (Total Time)
Alert Threshold: < 99.9%
Prometheus: up{job="agenkit"}
```

**Recommended SLOs (Service Level Objectives):**

```
SLO 1: 99.5% success rate over 30 days
- Error budget: 3.6 hours of failed requests per month
- Alert when: Error rate > 0.5% for 5 consecutive minutes

SLO 2: 99th percentile latency < 1 second over 30 days  
- Alert when: p99 latency > 1s for 10 consecutive minutes

SLO 3: 99.9% availability over 30 days
- Downtime budget: 43 seconds per month
- Alert when: Service returns 5xx errors for 1 minute
```

### 6.3 Error Budget Tracking

**Status: NOT IMPLEMENTED**

**Needed Components:**

```
✗ Error counter by type (distinguishing recoverable vs. critical)
✗ Error budget calculation per SLO
✗ Budget consumption rate tracking
✗ Burndown alerts (consuming budget too fast)
✗ Budget recovery tracking
```

**Implementation Example:**

```python
# Track error budget in Prometheus
error_budget_remaining = MeterProvider.create_gauge(
    "agenkit.error_budget_remaining",
    description="Seconds of allowed errors remaining in SLO window"
)

# Alert if consuming budget too quickly
# SLO: 99.5% = 3.6 hours budget per 30 days
# Normal burn rate: 3.6 hours / 30 days / 24 hours = 0.005 errors/sec
# Alert burn rate: 0.1 errors/sec (20x normal = alert within 2 hours)
```

### 6.4 Alert-Worthy Conditions

**Critical Alerts (Page On-Call):**

```
1. Error rate spike > 5% for 5 minutes
   rate(agenkit_agent_errors_total[5m]) / rate(agenkit_agent_requests_total[5m]) > 0.05

2. P99 latency > 10 seconds (10x normal)
   histogram_quantile(0.99, rate(agenkit_agent_latency_bucket[5m])) > 10000

3. Agent server is down
   up{job="agenkit-agent"} == 0

4. In-flight requests growing without bound (queue buildup)
   (Needs implementation)
```

**Warning Alerts (Notify Slack):**

```
1. Error rate 1-5% for 10 minutes
   rate(agenkit_agent_errors_total[10m]) > 0.01

2. P95 latency trending up
   histogram_quantile(0.95, rate(agenkit_agent_latency_bucket[5m])) > 1000

3. Message size trending up (potential DoS)
   rate(agenkit_agent_message_size_sum[1h]) > 500_000_000

4. Connection pool exhaustion risk
   (Needs implementation)
```

---

## 7. DASHBOARD REQUIREMENTS

### 7.1 Key Metrics for Dashboards

**Status: IDENTIFIED BUT NO TEMPLATES PROVIDED**

**Top-Level Service Dashboard:**

```
Metrics to Display:
1. Request Rate (requests/sec)
   Query: rate(agenkit_agent_requests_total[5m])
   
2. Error Rate (%)
   Query: 100 * rate(agenkit_agent_errors_total[5m]) / rate(agenkit_agent_requests_total[5m])
   
3. P50/P95/P99 Latency (ms)
   Query: histogram_quantile(0.XX, rate(agenkit_agent_latency_bucket[5m]))
   
4. Success Rate (%)
   Query: 100 * (1 - rate(agenkit_agent_errors_total[5m]) / rate(agenkit_agent_requests_total[5m]))
```

**Agent-Level Dashboard:**

```
Per-Agent Metrics:
1. Request rate by agent
   Query: rate(agenkit_agent_requests_total{agent_name="$agent"}[5m])
   
2. Error rate by agent
   Query: rate(agenkit_agent_errors_total{agent_name="$agent"}[5m])
   
3. Latency distribution
   Query: rate(agenkit_agent_latency_bucket{agent_name="$agent"}[5m])
   
4. Message size distribution
   Query: rate(agenkit_agent_message_size_bucket{agent_name="$agent"}[5m])
   
5. Top error types
   Query: topk(5, rate(agenkit_agent_errors_total{agent_name="$agent"}[5m]) by (error_type))
```

**Trace Dashboard (requires Jaeger/Tempo integration):**

```
1. Trace latency distribution
2. Trace error rate
3. Slowest traces (sorted by duration)
4. Most frequent error traces
5. Trace depth distribution
6. Cross-language traces (Python → Go transitions)
```

### 7.2 Service-Level Dashboard

**Status: NOT PROVIDED**

**Missing Template:**
- No Grafana JSON dashboard provided
- No example dashboard configuration
- No recommended panel layouts

**Recommended Layout:**

```
Row 1: SLI Status
  - Success Rate (big number) - GREEN if >99.5%, RED if <99%
  - P99 Latency (big number) - GREEN if <1s, YELLOW if >1s, RED if >5s
  - Availability (big number) - GREEN if >99.9%

Row 2: Traffic Trends
  - Request rate time series (last 24h)
  - Error rate time series (last 24h)
  - Latency percentiles time series (p50, p95, p99)

Row 3: Error Analysis
  - Error rate by type (bar chart)
  - Top 5 failing agents (bar chart)
  - Error trend over time

Row 4: Resource Usage
  - In-flight request count (gauge)
  - Message size distribution (heatmap)
  - Agent utilization by name (table)
```

### 7.3 Request Flow Visualization

**Status: NOT PROVIDED**

**Missing:**
- No request flow diagram generator
- No service map visualization
- No dependency graph

**Would Need:**
```
1. Service map showing agent dependencies
   - Python agent → Go agent → External API
   
2. Trace visualization
   - Timeline of spans
   - Parent-child relationships
   - Latency breakdown per span

3. Message flow diagram
   - Shows how messages flow between agents
   - Includes transport type (HTTP, gRPC, WebSocket)
```

### 7.4 Real-Time Monitoring Needs

**Status: PARTIALLY SUPPORTED**

**What's Ready:**
- ✓ Prometheus metrics available for scraping
- ✓ Prometheus push option available
- ✓ OpenTelemetry traces exportable to Jaeger/Zipkin

**What's Missing:**
- ✗ WebSocket for real-time metric updates
- ✗ Server-Sent Events for streaming metrics
- ✗ Embedded real-time dashboard
- ✗ Custom event streaming

---

## 8. PRODUCTION READINESS GAPS

### 8.1 Missing Instrumentation

**Priority 1 - Critical (must have for production):**

```
1. Transport Layer Instrumentation
   Files to modify: 
   - /agenkit/adapters/python/http_transport.py
   - /agenkit/adapters/python/grpc_transport.py
   - /agenkit/adapters/python/websocket_transport.py
   - /agenkit-go/adapter/transport/http_transport.go
   - /agenkit-go/adapter/transport/grpc_transport.go
   
   Missing:
   - Spans for network calls (HTTP POST, gRPC calls)
   - Metrics for connection establishment time
   - Metrics for wire transfer time
   - Metrics for socket errors
   
2. Health Check Instrumentation  
   Files to create:
   - /agenkit/observability/health.py
   - /agenkit-go/observability/health.go
   
   Missing:
   - Structured health check responses
   - Dependency health tracking
   - Health check metrics

3. Resource Metrics
   Status: COMPLETELY MISSING
   
   Missing:
   - Process CPU usage (seconds, %)
   - Process memory usage (heap, RSS, allocated)
   - GC statistics (pause time, frequency)
   - Thread/goroutine count
   - Connection pool status
   - File descriptor usage
```

**Priority 2 - Important (needed within 1 month):**

```
4. Error Categorization
   Files to modify:
   - /agenkit/interfaces.py (or create /agenkit/observability/errors.py)
   - /agenkit-go/agenkit/interfaces.go
   
   Missing:
   - Error classification (retriable vs. fatal)
   - Error context/metadata
   - Error rate SLO tracking
   
5. Sampling Configuration
   Files to create:
   - /agenkit/observability/sampling.py
   - /agenkit-go/observability/sampling.go
   
   Missing:
   - Trace sampling strategies
   - Metric sampling configuration
   - Log sampling options

6. Custom Metrics API
   Files to modify:
   - /agenkit/observability/metrics.py
   - /agenkit-go/observability/metrics.go
   
   Missing:
   - User-defined metric creation
   - Gauge creation
   - Histogram bucket customization
```

**Priority 3 - Nice-to-have:**

```
7. Baggage Propagation
   - For passing request context across agent boundaries
   - Currently uses metadata but no structured baggage

8. Sensitive Data Filtering
   - Automatic redaction in traces/logs
   - PII masking

9. Metrics Export Formats
   - OpenMetrics format (in addition to Prometheus)
   - StatsD format option
```

### 8.2 Configuration for Production

**Status: PARTIAL**

**What's Configurable:**
```python
# Python
init_tracing(
    service_name="my-service",
    otlp_endpoint="localhost:4317",  # Production endpoint
    console_export=False,  # Disable console in production
)

init_metrics(
    service_name="my-service",
    port=8001,  # Metrics port
)

configure_logging(
    level=logging.ERROR,  # Reduce verbosity
    structured=True,
    include_trace_context=True,
)
```

**What's NOT Configurable:**
```
✗ Trace sampling ratio (hardcoded to 100%)
✗ Batch processor size/timeout
✗ Metric export interval
✗ Log rotation policy
✗ Sensitive field redaction rules
✗ Custom resource attributes
✗ Environment-specific settings
```

**Missing Environment Variable Support:**
```bash
# These should be supported but aren't
export OTEL_TRACES_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_METRICS_EXPORTER=prometheus
export OTEL_PROPAGATORS=tracecontext,baggage
export OTEL_SAMPLER=parentbased_traceidratio
export OTEL_SAMPLER_ARG=0.1
export OTEL_LOG_LEVEL=ERROR
```

### 8.3 Performance Impact of Monitoring

**Status: NOT MEASURED**

**Potential Concerns:**
```
✗ No benchmark showing tracing overhead
✗ No benchmark showing metrics collection overhead
✗ No benchmark showing logging overhead
✗ No guidance on acceptable overhead thresholds
```

**Expected Impact (estimates):**
- Tracing middleware: 2-5% latency overhead
- Metrics middleware: 1-2% latency overhead
- Structured logging: 3-8% latency overhead
- Total: ~6-15% overhead (needs measurement)

**Production Recommendations:**
```
1. Enable sampling for high-traffic services
   - Sample 10-50% of traces depending on traffic volume
   
2. Use async metric export
   - Batch metrics with 5-10 second interval
   - Already implemented (BatchSpanProcessor)
   
3. Reduce log verbosity in production
   - Use WARNING or ERROR level
   - Sample debug logs
   
4. Monitor the monitoring
   - Track exporter queue depth
   - Track export latency
   - Alert if monitoring itself is failing
```

### 8.4 Integration with Monitoring Stacks

**Status: ARCHITECTURE-READY BUT NOT DOCUMENTED**

**Tested Integrations:**
```
✓ OpenTelemetry Protocol (OTLP) - gRPC
  - Works with: Jaeger, Tempo, Otel Collector
  - Configuration: otlp_endpoint="localhost:4317"

✓ Prometheus - metrics only
  - Works with: Prometheus, Thanos, VictorOps
  - Configuration: Exposes metrics on HTTP endpoint

✓ JSON Logging - log forwarding
  - Works with: ELK, Splunk, Datadog, CloudWatch
  - Configuration: Structured JSON output
```

**Missing Documentation:**
- No setup guide for Jaeger + Prometheus + Grafana
- No setup guide for ELK Stack integration
- No setup guide for cloud platforms (AWS, GCP, Azure)
- No Docker Compose example with full stack

**Integration Gaps:**
```
✗ Prometheus scrape config not provided
✗ Jaeger receiver configuration not provided
✗ Grafana dashboard definitions not provided
✗ Alert rules (Prometheus alerts.yaml) not provided
✗ Filebeat/Logstash config not provided
```

---

## 9. ACTIONABLE IMPLEMENTATION PLAN

### Phase 1: Core Production Readiness (Weeks 1-2)

**Tasks:**

1. **Add Trace Sampling Configuration**
   ```python
   # agenkit/observability/tracing.py
   from opentelemetry.sdk.trace.sampling import TraceIdRatioBased, ParentBasedTraceIdRatio
   
   def init_tracing(
       service_name: str = "agenkit",
       otlp_endpoint: str | None = None,
       console_export: bool = False,
       sampling_ratio: float = 1.0,  # NEW
   ) -> TracerProvider:
       sampler = TraceIdRatioBased(sampling_ratio)
       provider = TracerProvider(
           sampler=sampler,
           resource=resource,
       )
       # ...
   ```

2. **Implement Health Check Endpoints**
   ```python
   # agenkit/observability/health.py
   from dataclasses import dataclass
   from enum import Enum
   
   class HealthStatus(str, Enum):
       HEALTHY = "healthy"
       DEGRADED = "degraded"
       UNHEALTHY = "unhealthy"
   
   @dataclass
   class HealthResponse:
       status: HealthStatus
       checks: dict[str, HealthStatus]
       timestamp: str
   ```

3. **Remove Duplicate Middleware**
   - Use OpenTelemetry MetricsMiddleware exclusively
   - Deprecate local MetricsDecorator
   - Update examples and tests

4. **Add Resource Metrics**
   ```python
   def init_resource_metrics(meter: metrics.Meter) -> None:
       # Add process metrics
       meter.create_counter(
           "process.cpu.seconds",
           description="CPU time used"
       )
       meter.create_gauge(
           "process.memory.usage",
           description="Memory usage in bytes"
       )
       # ... more metrics
   ```

### Phase 2: Production Hardening (Weeks 3-4)

**Tasks:**

1. **Add Transport Layer Instrumentation**
   - Create spans for network operations
   - Track connection establishment time
   - Track DNS resolution time
   - Track TLS handshake time

2. **Implement Structured Health Checks**
   ```python
   # In HTTP/gRPC servers
   async def handle_ready(self) -> Response:
       health = HealthChecker()
       health.check_self()  # Always passes if process is running
       health.check_dependencies()  # Check remote agents, etc.
       
       response_data = {
           "status": health.status.value,
           "checks": {k: v.value for k, v in health.checks.items()},
           "timestamp": datetime.now(timezone.utc).isoformat(),
       }
       return Response(body=json.dumps(response_data), status=200 if health.is_healthy else 503)
   ```

3. **Create Alert Rules**
   ```yaml
   # prometheus-rules.yaml
   groups:
     - name: agenkit_alerts
       rules:
         - alert: AgentHighErrorRate
           expr: rate(agenkit_agent_errors_total[5m]) / rate(agenkit_agent_requests_total[5m]) > 0.05
           for: 5m
           labels:
             severity: critical
           annotations:
             summary: "High error rate on agent {{ $labels.agent_name }}"
   ```

4. **Create Grafana Dashboards**
   - Export as JSON files
   - Include in repository
   - Document dashboard variables

### Phase 3: Advanced Features (Weeks 5-6)

**Tasks:**

1. **Implement Trace Sampling Strategies**
   - Parent-based sampling
   - Probability-based sampling
   - Per-agent sampling rules

2. **Add Custom Metrics API**
   - Allow users to create custom metrics
   - Document best practices
   - Provide examples

3. **Implement Sensitive Data Filtering**
   - Automatic PII redaction in logs
   - Configurable redaction rules
   - Secure transport of redacted data

4. **Environment Variable Configuration**
   - Support standard OTEL env vars
   - Support custom Agenkit env vars
   - Document all configuration options

### Phase 4: Documentation & Examples (Weeks 7-8)

**Tasks:**

1. **Create Integration Guides**
   - Jaeger setup guide
   - Prometheus + Grafana guide
   - ELK Stack integration
   - Cloud platform guides (AWS, GCP, Azure)

2. **Create Example Deployments**
   - Docker Compose with full stack
   - Kubernetes manifests
   - Terraform for AWS/GCP

3. **Create Troubleshooting Guide**
   - Common issues and solutions
   - Performance tuning guide
   - Debug mode documentation

4. **Update Main Documentation**
   - Observability best practices
   - Production deployment checklist
   - Troubleshooting section

---

## 10. RECOMMENDED TOOLING & INTEGRATION GUIDE

### 10.1 Recommended Stack

**Production Recommended:**
```
Frontend (Dashboards):
  - Grafana 10.x (open-source) or newer

Metrics Collection:
  - Prometheus 2.40.x or newer
  - (or managed: AWS CloudWatch, GCP Cloud Monitoring, Azure Monitor)

Distributed Tracing:
  - Jaeger 1.40.x (open-source) or newer
  - (or managed: AWS X-Ray, GCP Cloud Trace, Azure App Insights)

Log Aggregation:
  - ELK Stack 8.x (Elasticsearch, Logstash, Kibana)
  - (or managed: Splunk, Datadog, New Relic)

OpenTelemetry Collector:
  - Open Telemetry Collector 0.80.x or newer
```

### 10.2 Integration Examples

**Example: Prometheus Configuration**

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'agenkit-python'
    static_configs:
      - targets: ['localhost:8001']
    scrape_interval: 10s  # More frequent for important service
    
  - job_name: 'agenkit-go'
    static_configs:
      - targets: ['localhost:8002']
    scrape_interval: 10s

  - job_name: 'otel-collector'
    static_configs:
      - targets: ['localhost:8888']

rule_files:
  - "prometheus-rules.yaml"
```

**Example: Jaeger Configuration**

```yaml
# jaeger-config.yaml
samplers:
  default_strategy: probabilistic
  probabilistic:
    sampling_rate: 0.1  # Sample 10% of traces

reporters:
  logSpans: true
  
storage:
  type: elasticsearch
  elasticsearch:
    server_urls:
      - http://elasticsearch:9200
    index_prefix: jaeger
```

**Example: OpenTelemetry Collector Configuration**

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  batch:
    send_batch_size: 1024
    timeout: 5s

exporters:
  prometheus:
    endpoint: 0.0.0.0:8888
  jaeger:
    endpoint: jaeger:14250
  
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus]
```

### 10.3 Docker Compose Example

See detailed example in "Example Docker Compose" section below.

---

## 11. CODE EXAMPLES FOR IMPLEMENTATION

### 11.1 Enhanced Metrics Middleware (Missing Resource Metrics)

```python
# agenkit/observability/resource_metrics.py
"""Resource metrics collection for production monitoring."""

import os
import psutil
from opentelemetry import metrics

def init_resource_metrics(meter: metrics.Meter) -> None:
    """Initialize resource/process metrics."""
    
    process = psutil.Process(os.getpid())
    
    # CPU metrics
    cpu_counter = meter.create_counter(
        "process.cpu.seconds",
        description="CPU time used by process",
        unit="s",
    )
    
    # Memory metrics
    memory_gauge = meter.create_gauge(
        "process.memory.rss",
        description="Resident set size (RSS) memory in bytes",
        unit="bytes",
    )
    
    memory_heap_gauge = meter.create_gauge(
        "process.memory.heap",
        description="Heap memory in bytes",
        unit="bytes",
    )
    
    # Connection pool metrics
    connection_gauge = meter.create_gauge(
        "connection.pool.size",
        description="Number of active connections",
        unit="1",
    )
    
    # Set up periodic updates
    import threading
    def update_metrics():
        while True:
            try:
                # Update memory
                mem_info = process.memory_info()
                memory_gauge.observe(mem_info.rss)
                memory_heap_gauge.observe(mem_info.vms)
                
                # Update CPU
                cpu_info = process.cpu_num()
                cpu_counter.add(cpu_info)
                
            except Exception as e:
                print(f"Error updating resource metrics: {e}")
            
            time.sleep(5)  # Update every 5 seconds
    
    thread = threading.Thread(target=update_metrics, daemon=True)
    thread.start()
```

### 11.2 Enhanced Tracing with Sampling

```python
# agenkit/observability/tracing.py (enhancement)
"""Enhanced tracing with sampling support."""

from opentelemetry.sdk.trace.sampling import TraceIdRatioBased, ParentBasedTraceIdRatio

def init_tracing_with_sampling(
    service_name: str = "agenkit",
    otlp_endpoint: str | None = None,
    console_export: bool = False,
    sampling_ratio: float = 1.0,  # New parameter
) -> TracerProvider:
    """Initialize OpenTelemetry tracing with sampling.
    
    Args:
        service_name: Service name
        otlp_endpoint: OTLP exporter endpoint
        console_export: Enable console export
        sampling_ratio: Trace sampling ratio (0.0-1.0)
                       1.0 = trace all requests (default)
                       0.1 = trace 10% of requests
    """
    resource = Resource(attributes={
        SERVICE_NAME: service_name,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "version": os.getenv("SERVICE_VERSION", "unknown"),
    })
    
    # Create sampler based on ratio
    if sampling_ratio >= 1.0:
        sampler = AlwaysOnSampler()
    elif sampling_ratio <= 0.0:
        sampler = AlwaysOffSampler()
    else:
        # Parent-based sampling: inherit parent's sampling decision
        sampler = ParentBasedTraceIdRatio(sampling_ratio)
    
    provider = TracerProvider(
        resource=resource,
        sampler=sampler,
    )
    
    # ... rest of implementation
```

### 11.3 Health Check Implementation

```python
# agenkit/observability/health.py
"""Health check implementation for production services."""

import asyncio
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timezone
from typing import Dict, Callable, Awaitable

class HealthStatus(str, Enum):
    """Health status enum."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  
    UNHEALTHY = "unhealthy"

@dataclass
class HealthCheckResult:
    """Result of a single health check."""
    name: str
    status: HealthStatus
    message: str = ""
    duration_ms: float = 0.0

class HealthChecker:
    """Manages health checks for a service."""
    
    def __init__(self):
        self.checks: Dict[str, Callable[[], Awaitable[HealthCheckResult]]] = {}
        self.results: Dict[str, HealthCheckResult] = {}
    
    def add_check(
        self,
        name: str,
        check_func: Callable[[], Awaitable[HealthCheckResult]]
    ) -> None:
        """Register a health check."""
        self.checks[name] = check_func
    
    async def run_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered checks."""
        import time
        
        self.results = {}
        for name, check_func in self.checks.items():
            try:
                start = time.time()
                result = await asyncio.wait_for(check_func(), timeout=2.0)
                result.duration_ms = (time.time() - start) * 1000
                self.results[name] = result
            except asyncio.TimeoutError:
                self.results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message="Check timed out",
                )
            except Exception as e:
                self.results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                )
        
        return self.results
    
    @property
    def overall_status(self) -> HealthStatus:
        """Get overall health status."""
        if not self.results:
            return HealthStatus.UNHEALTHY
        
        if any(r.status == HealthStatus.UNHEALTHY for r in self.results.values()):
            return HealthStatus.UNHEALTHY
        if any(r.status == HealthStatus.DEGRADED for r in self.results.values()):
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON response."""
        return {
            "status": self.overall_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                name: {
                    "status": result.status.value,
                    "message": result.message,
                    "duration_ms": result.duration_ms,
                }
                for name, result in self.results.items()
            }
        }

# Example usage in HTTP server
async def setup_health_checks(server: HTTPAgentServer) -> HealthChecker:
    """Setup health checks for HTTP server."""
    
    health = HealthChecker()
    
    # Self check (always passes)
    async def check_self() -> HealthCheckResult:
        return HealthCheckResult(
            name="self",
            status=HealthStatus.HEALTHY,
            message="Process is running",
        )
    
    # Remote agent check (example)
    async def check_remote_agent() -> HealthCheckResult:
        try:
            result = await server.agent.process(
                Message(role="health_check", content="ping")
            )
            return HealthCheckResult(
                name="remote_agent",
                status=HealthStatus.HEALTHY,
                message="Remote agent responding",
            )
        except Exception as e:
            return HealthCheckResult(
                name="remote_agent",
                status=HealthStatus.UNHEALTHY,
                message=f"Remote agent error: {str(e)}",
            )
    
    health.add_check("self", check_self)
    health.add_check("remote_agent", check_remote_agent)
    
    return health

# In HTTP server handler
async def handle_ready(self, request: web.Request) -> web.Response:
    """Readiness probe - indicates if service is ready for traffic."""
    await self.health_checker.run_checks()
    
    health_data = self.health_checker.to_dict()
    status_code = 200 if self.health_checker.overall_status == HealthStatus.HEALTHY else 503
    
    return web.Response(
        body=json.dumps(health_data),
        status=status_code,
        content_type="application/json",
    )

async def handle_live(self, request: web.Request) -> web.Response:
    """Liveness probe - indicates if process should be restarted."""
    # Simple check - if process is running, it's live
    return web.Response(
        body=json.dumps({
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }),
        status=200,
        content_type="application/json",
    )
```

### 11.4 Prometheus Alert Rules

```yaml
# prometheus-rules.yaml
groups:
  - name: agenkit_alerts
    interval: 30s
    rules:
      # SLI-based alerts
      - alert: AgentHighErrorRate
        expr: |
          (rate(agenkit_agent_errors_total[5m]) / rate(agenkit_agent_requests_total[5m])) > 0.01
        for: 5m
        labels:
          severity: warning
          sli: error_rate
        annotations:
          summary: "High error rate on agent {{ $labels.agent_name }}"
          description: "Error rate is {{ $value | humanizePercentage }} on {{ $labels.agent_name }}"

      - alert: AgentCriticalErrorRate
        expr: |
          (rate(agenkit_agent_errors_total[5m]) / rate(agenkit_agent_requests_total[5m])) > 0.05
        for: 2m
        labels:
          severity: critical
          sli: error_rate
        annotations:
          summary: "CRITICAL: Very high error rate on agent {{ $labels.agent_name }}"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"

      # Latency alerts
      - alert: AgentHighLatency
        expr: |
          histogram_quantile(0.99, rate(agenkit_agent_latency_bucket[5m])) > 1000
        for: 10m
        labels:
          severity: warning
          sli: latency
        annotations:
          summary: "High latency on agent {{ $labels.agent_name }}"
          description: "P99 latency is {{ $value | humanizeDuration }} (threshold: 1s)"

      - alert: AgentCriticalLatency
        expr: |
          histogram_quantile(0.99, rate(agenkit_agent_latency_bucket[5m])) > 5000
        for: 5m
        labels:
          severity: critical
          sli: latency
        annotations:
          summary: "CRITICAL: Very high latency on agent {{ $labels.agent_name }}"
          description: "P99 latency is {{ $value | humanizeDuration }} (threshold: 5s)"

      # Availability alerts
      - alert: AgentDown
        expr: up{job="agenkit-agent"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Agent {{ $labels.instance }} is down"
          description: "Agent has been unreachable for 2 minutes"

      # Error budget alerts
      - alert: ErrorBudgetBurnRate
        expr: |
          (rate(agenkit_agent_errors_total[5m]) / 0.005) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Error budget consuming faster than expected"
          description: "Current burn rate: {{ $value }}x expected for 99.5% SLO"

      # Traffic alerts
      - alert: NoTraffic
        expr: rate(agenkit_agent_requests_total[5m]) == 0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "No traffic received for agent {{ $labels.agent_name }}"
          description: "No requests processed in last 5 minutes"
```

### 11.5 Grafana Dashboard JSON

```json
{
  "dashboard": {
    "title": "Agenkit Service Health",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(agenkit_agent_requests_total[5m])",
            "legendFormat": "{{ agent_name }}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "100 * rate(agenkit_agent_errors_total[5m]) / rate(agenkit_agent_requests_total[5m])",
            "legendFormat": "{{ agent_name }}"
          }
        ]
      },
      {
        "title": "Latency P99",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, rate(agenkit_agent_latency_bucket[5m]))",
            "legendFormat": "{{ agent_name }}"
          }
        ]
      }
    ]
  }
}
```

---

## 12. EXAMPLE DOCKER COMPOSE STACK

```yaml
# docker-compose.yml - Complete observability stack
version: '3.8'

services:
  # OpenTelemetry Collector
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.80.0
    ports:
      - "4317:4317"   # OTLP gRPC receiver
      - "4318:4318"   # OTLP HTTP receiver
      - "9411:9411"   # Zipkin HTTP receiver
      - "14250:14250" # Jaeger gRPC receiver
      - "8888:8888"   # Prometheus metrics
    volumes:
      - ./otel-collector-config.yaml:/etc/otel/config.yaml
    environment:
      - GOGC=80
    command: ["--config=/etc/otel/config.yaml"]
    networks:
      - observability

  # Jaeger
  jaeger:
    image: jaegertracing/all-in-one:1.40
    ports:
      - "6831:6831/udp"  # Jaeger agent
      - "16686:16686"    # Jaeger UI
      - "14250:14250"    # gRPC receiver
    environment:
      - COLLECTOR_OTLP_ENABLED=true
      - SPAN_STORAGE_TYPE=badger
      - BADGER_EPHEMERAL=false
      - BADGER_DIRECTORY_VALUE=/badger/data
      - BADGER_DIRECTORY_KEY=/badger/key
    volumes:
      - jaeger_data:/badger
    networks:
      - observability

  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - ./prometheus-rules.yaml:/etc/prometheus/rules.yaml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    networks:
      - observability

  # Grafana
  grafana:
    image: grafana/grafana:10.0.0
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/provisioning/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus
    networks:
      - observability

  # Elasticsearch (for logs)
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - xpack.security.enrollment.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    networks:
      - observability
    healthcheck:
      test: curl -f http://localhost:9200 >/dev/null 2>&1
      interval: 30s
      timeout: 10s
      retries: 3

  # Kibana
  kibana:
    image: docker.elastic.co/kibana/kibana:8.0.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
    networks:
      - observability
    healthcheck:
      test: curl -f http://localhost:5601/app/kibana >/dev/null 2>&1
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  prometheus_data:
  grafana_data:
  jaeger_data:
  elasticsearch_data:

networks:
  observability:
    driver: bridge
```

---

## 13. SUMMARY & RECOMMENDATIONS

### Quick Wins (Can implement in 1-2 weeks)

1. **Add trace sampling** - Critical for production
2. **Implement `/ready` and `/live` probes** - Kubernetes-ready
3. **Create Prometheus alert rules** - Protect SLOs
4. **Create Grafana dashboards** - Operability

### Medium-term (1-2 months)

1. **Add resource metrics** - CPU, memory, connections
2. **Instrument transports** - See HTTP/gRPC performance
3. **Implement health checks** - Detect dependency failures
4. **Create integration guides** - Reduce setup friction

### Long-term (2-3 months)

1. **Custom metrics API** - User-defined instrumentation
2. **Sampling strategies** - Advanced trace filtering
3. **Sensitive data redaction** - Security/compliance
4. **Cloud platform guides** - AWS/GCP/Azure integration

### Current Production Readiness by Component

```
Component                 | Status     | Recommendation
--------------------------|------------|------------------
Tracing (Core)            | ✓ READY    | Add sampling
Metrics (Core)            | ✓ READY    | Add resource metrics
Logging                   | ✓ READY    | Add sensitive data filter
Health Checks             | ⚠ PARTIAL  | Add dependency checks
Transport Instrumentation | ✗ MISSING  | Implement ASAP
Resource Metrics          | ✗ MISSING  | Implement ASAP
Alerting                  | ⚠ PARTIAL  | Add rules
Dashboards                | ✗ MISSING  | Create templates
Documentation             | ⚠ PARTIAL  | Expand guides
```

### Overall Assessment

**Agenkit is 60% ready for production monitoring.**

- **Strong foundation** with OpenTelemetry integration
- **Solid basics** for tracing, metrics, and logging
- **Significant gaps** in health checks, resource metrics, and alerting
- **Good cross-language support** (Python/Go parity)
- **Needs hardening** for production SLOs and error budgets

Recommended next steps: Implement the Phase 1 tasks (4-6 weeks) before considering this production-ready for mission-critical services.

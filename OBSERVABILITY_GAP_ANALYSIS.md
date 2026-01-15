# Observability Gap Analysis - Rust & C++

**Date**: January 15, 2026
**Status**: Not Implemented
**Priority**: Should-Have (Phase 2, Task 2.5)
**Estimated Effort**: 14-18 days for both languages

## Executive Summary

Observability infrastructure (OpenTelemetry integration) is fully implemented in Python and Go but missing in Rust and C++. This document analyzes the gap and provides an implementation roadmap.

## Current State

### Implemented Languages ✅

#### Python (`agenkit/observability/`)
- **Tracing** (`tracing.py` - 200 LOC): OpenTelemetry distributed tracing
- **Metrics** (`metrics.py` - 168 LOC): OpenTelemetry metrics collection
- **Logging** (`logging.py` - 165 LOC): Structured logging integration
- **Audit** (`audit.py` - 496 LOC): Comprehensive audit trail
- **Tests**: 41 tests (all passing)
- **Dependencies**: `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`

#### Go (`agenkit-go/observability/`)
- **Tracing** (`tracing.go` - 233 LOC): OpenTelemetry distributed tracing
- **Metrics** (`metrics.go` - 255 LOC): OpenTelemetry metrics collection
- **Logging** (`logging.go` - 131 LOC): Structured logging integration
- **Audit** (`audit.go` - 385 LOC): Comprehensive audit trail
- **Tests**: 41 tests (all passing)
- **Dependencies**: `go.opentelemetry.io/otel`, `go.opentelemetry.io/otel/exporters/*`

### Missing Languages ❌

#### Rust (`agenkit-rust/src/`)
- **Status**: ❌ No observability module
- **Dependencies**: None (would need `opentelemetry`, `opentelemetry-otlp`, `tracing`)
- **Tests**: 0/41 (0%)

#### C++ (`agenkit-cpp/src/`)
- **Status**: ❌ No observability module
- **Dependencies**: None (would need `opentelemetry-cpp`)
- **Tests**: 0/41 (0%)

## Reference Implementation Analysis

### Component Breakdown

Based on Python/Go implementations, observability consists of 4 main modules:

#### 1. Distributed Tracing (~200-250 LOC per language)

**Purpose**: Track request flow across distributed systems with OpenTelemetry

**Key Features**:
- `InitTracing()`: Initialize OpenTelemetry tracer provider
- OTLP exporter support (gRPC/HTTP)
- Console/stdout exporter for debugging
- Configurable sampling rates (0.0-1.0)
- W3C Trace Context propagation
- Agent middleware integration
- Span attributes (agent name, messages, metadata)
- Error tracking with span status

**Example (Go)**:
```go
// Initialize tracing
tp, _ := InitTracing("my-service", "localhost:4317", true, 1.0)
defer tp.Shutdown(context.Background())

// Wrap agent with tracing
traced := TracingMiddleware(baseAgent, "my-agent")

// Process - automatic span creation
result := traced.Process(ctx, message)
```

#### 2. Metrics Collection (~170-255 LOC per language)

**Purpose**: Collect and export agent metrics via OpenTelemetry

**Key Metrics**:
- **Counter**: `agent.requests.total` (total requests by agent, status)
- **Histogram**: `agent.request.duration` (latency distribution)
- **Counter**: `agent.errors.total` (errors by agent, error type)
- **Gauge**: `agent.active.requests` (active requests per agent)

**Key Features**:
- `InitMetrics()`: Initialize OpenTelemetry meter provider
- OTLP exporter support
- Console/stdout exporter
- Prometheus exporter support
- Agent middleware integration
- Automatic metric recording
- Label/attribute support

**Example (Go)**:
```go
// Initialize metrics
mp, _ := InitMetrics("my-service", "localhost:4318", 10*time.Second)
defer mp.Shutdown(context.Background())

// Wrap agent
metered := MetricsMiddleware(baseAgent, "my-agent")

// Automatic metrics collection
result := metered.Process(ctx, message)
// Records: requests_total++, request_duration histogram, errors (if any)
```

#### 3. Structured Logging (~130-165 LOC per language)

**Purpose**: Unified structured logging with levels and context

**Log Levels**:
- DEBUG, INFO, WARNING, ERROR, CRITICAL

**Key Features**:
- `NewLogger()`: Create structured logger
- JSON output format
- Console output for development
- File output with rotation support
- Context propagation (trace_id, span_id)
- Agent integration
- Metadata/extra fields support

**Example (Go)**:
```go
// Create logger
logger := NewLogger("INFO", true, "agent.log")

// Log with context
logger.Info("Agent processing", map[string]interface{}{
    "agent": "my-agent",
    "message_id": "123",
})

// Log errors
logger.Error("Processing failed", map[string]interface{}{
    "agent": "my-agent",
    "error": err.Error(),
})
```

#### 4. Audit Logging (~385-496 LOC per language)

**Purpose**: Security and compliance audit trail

**Event Types**:
- REQUEST, RESPONSE, ERROR, CONFIG_CHANGE, ACCESS_DENIED, DATA_ACCESS

**Key Features**:
- `NewAuditLogger()`: Create audit logger
- Structured event logging (JSON)
- Automatic timestamping
- User/session tracking
- IP address tracking
- File output with rotation
- Compliance reporting support
- Search and filtering

**Example (Go)**:
```go
// Create audit logger
audit := NewAuditLogger("audit.log", true) // rotate enabled

// Log request
audit.LogRequest("my-agent", userID, sessionID, clientIP, requestData)

// Log access denied
audit.LogAccessDenied("my-agent", userID, "insufficient permissions", resourceID)

// Log error
audit.LogError("my-agent", userID, err.Error(), errorDetails)
```

## Implementation Roadmap

### Rust Implementation (8-10 days)

**Dependencies to Add** (`Cargo.toml`):
```toml
[dependencies]
opentelemetry = "0.21"
opentelemetry-otlp = "0.14"
opentelemetry_sdk = "0.21"
tracing = "0.1"
tracing-opentelemetry = "0.22"
tracing-subscriber = "0.3"
serde_json = "1.0"
chrono = "0.4"
```

**Files to Create**:
1. `src/observability/mod.rs` - Module exports
2. `src/observability/tracing.rs` - OpenTelemetry tracing (~250 LOC)
3. `src/observability/metrics.rs` - OpenTelemetry metrics (~200 LOC)
4. `src/observability/logging.rs` - Structured logging (~150 LOC)
5. `src/observability/audit.rs` - Audit logging (~400 LOC)
6. `tests/observability_test.rs` - Comprehensive tests (~800 LOC)
7. `examples/observability_example.rs` - Usage example (~150 LOC)

**Key Challenges**:
- Rust async ecosystem integration (tokio)
- Lifetime management for tracers/meters
- Error handling with Result types
- Thread-safe global provider setup

**Estimated Effort**: 8-10 days
- Day 1-2: Tracing implementation
- Day 3-4: Metrics implementation
- Day 5-6: Logging + Audit implementation
- Day 7-8: Tests + Examples
- Day 9-10: Documentation + Integration

### C++ Implementation (6-8 days)

**Dependencies to Add** (`CMakeLists.txt`):
```cmake
find_package(opentelemetry-cpp REQUIRED)
target_link_libraries(agenkit
    opentelemetry-cpp::api
    opentelemetry-cpp::sdk
    opentelemetry-cpp::ext
    opentelemetry-cpp::exporters::otlp
    opentelemetry-cpp::exporters::ostream
)
```

**Files to Create**:
1. `include/agenkit/observability/observability.hpp` - Main export (~50 LOC)
2. `include/agenkit/observability/tracing.hpp` - Tracing declarations (~150 LOC)
3. `src/observability/tracing.cpp` - Tracing implementation (~300 LOC)
4. `include/agenkit/observability/metrics.hpp` - Metrics declarations (~120 LOC)
5. `src/observability/metrics.cpp` - Metrics implementation (~250 LOC)
6. `include/agenkit/observability/logging.hpp` - Logging declarations (~80 LOC)
7. `src/observability/logging.cpp` - Logging implementation (~150 LOC)
8. `include/agenkit/observability/audit.hpp` - Audit declarations (~100 LOC)
9. `src/observability/audit.cpp` - Audit implementation (~400 LOC)
10. `tests/observability/test_observability.cpp` - Tests (~800 LOC)
11. `examples/observability_example.cpp` - Usage example (~150 LOC)

**Key Challenges**:
- OpenTelemetry C++ SDK is complex
- Header/implementation separation
- RAII for resource management (providers, exporters)
- Thread safety with smart pointers
- Exception safety guarantees

**Estimated Effort**: 6-8 days
- Day 1-2: Tracing implementation
- Day 3-4: Metrics implementation
- Day 5: Logging implementation
- Day 6: Audit implementation
- Day 7: Tests
- Day 8: Examples + Documentation

## Test Coverage Requirements

### Test Categories (41 tests total per language)

#### Tracing Tests (10 tests)
1. InitTracing with OTLP endpoint
2. InitTracing with console export
3. InitTracing with custom sampling
4. TracingMiddleware creates spans
5. Span attributes set correctly
6. Error spans marked as error
7. Nested spans (parent-child)
8. Trace context propagation
9. Multiple agents in same trace
10. Shutdown cleans up resources

#### Metrics Tests (12 tests)
1. InitMetrics with OTLP endpoint
2. InitMetrics with console export
3. Counter increments correctly
4. Histogram records values
5. Gauge updates correctly
6. Metrics middleware records requests
7. Metrics middleware records duration
8. Metrics middleware records errors
9. Multiple agents have separate metrics
10. Labels/attributes work correctly
11. Metric export works
12. Shutdown cleans up resources

#### Logging Tests (9 tests)
1. Logger creation
2. Debug level logging
3. Info level logging
4. Warning level logging
5. Error level logging
6. JSON output format
7. Extra fields in logs
8. File output works
9. Log level filtering

#### Audit Tests (10 tests)
1. Audit logger creation
2. LogRequest works
3. LogResponse works
4. LogError works
5. LogAccessDenied works
6. LogConfigChange works
7. LogDataAccess works
8. JSON output format
9. File output works
10. Log rotation works

## Parity Impact

### Current Test Parity

| Language | Total Tests | Observability Tests | Observability % |
|----------|-------------|---------------------|-----------------|
| Python | 1,792 | 41 | 2.3% |
| Go | 950 | 41 | 4.3% |
| C++ | 793 | 0 | 0.0% |
| Rust | ~276 | 0 | 0.0% |
| TypeScript | ~328 | ~30 | ~0.9% |
| Zig | 245 | 0 | 0.0% |

### After Implementation

| Language | Total Tests | Observability Tests | Observability % | Total Parity |
|----------|-------------|---------------------|-----------------|--------------|
| Python | 1,792 | 41 | 2.3% | 100.0% |
| Go | 950 | 41 | 4.3% | 53.0% |
| **C++** | **834** | **41** | **4.9%** | **46.5%** (+2.2%) |
| **Rust** | **317** | **41** | **12.9%** | **17.7%** (+2.3%) |
| TypeScript | ~369 | ~71 | ~1.9% | ~20.6% |
| Zig | 245 | 0 | 0.0% | 13.7% |

**Impact**:
- C++: +41 tests (5.2% increase), parity improves from 44.3% to 46.5%
- Rust: +41 tests (14.9% increase), parity improves from 15.4% to 17.7%

## Alternatives to Full Implementation

### Option 1: Basic Logging Only (2-3 days)
Implement just structured logging without OpenTelemetry dependency:
- Simpler, no external dependencies
- File + console output
- JSON format
- ~150-200 LOC per language
- ~10 tests per language
- **Parity Impact**: +10 tests per language (~0.6% each)

### Option 2: Stub Implementation (1 day)
Create module structure with no-op implementations:
- Placeholder for future work
- Minimal dependencies
- ~50-100 LOC per language
- ~5 tests per language
- **Parity Impact**: +5 tests per language (~0.3% each)

### Option 3: Defer to v0.49.0+
Mark as future work and document requirements:
- Focus on higher-priority work
- Complete planning for future implementation
- No immediate parity impact

## Recommendation

**Recommended Approach**: Option 3 (Defer to v0.49.0+)

**Rationale**:
1. **Phase 2 Core Complete**: Tasks 2.1-2.3 (parity enforcement) are done (80%)
2. **Significant Effort**: 14-18 days for both languages is substantial
3. **Lower Priority**: Observability is "should-have" not "must-have"
4. **Existing Alternatives**: Both languages have basic logging via standard libraries
5. **Good Documentation**: This analysis provides clear roadmap for future work

**Alternative if Implementation Desired**: Start with Rust only (8-10 days)
- Rust has stronger community interest in OpenTelemetry
- Smaller codebase, cleaner integration
- Can serve as reference for C++ implementation later
- Provides meaningful parity boost (15.4% → 17.7%)

## Next Steps

### If Proceeding with Implementation:
1. Set up Rust OpenTelemetry dependencies
2. Implement tracing module (reference: Go implementation)
3. Implement metrics module
4. Implement logging module
5. Implement audit module
6. Write comprehensive tests (41 tests)
7. Create example
8. Repeat for C++

### If Deferring:
1. Document this analysis in project docs
2. Create GitHub issues for tracking (#398 Rust, #399 C++)
3. Update roadmap with future milestone
4. Focus on Phase 3 (Documentation Excellence)

## References

- **Go Implementation**: `/Users/scttfrdmn/src/agenkit/agenkit-go/observability/`
- **Python Implementation**: `/Users/scttfrdmn/src/agenkit/agenkit/observability/`
- **OpenTelemetry Rust**: https://docs.rs/opentelemetry/
- **OpenTelemetry C++**: https://github.com/open-telemetry/opentelemetry-cpp
- **Issue #398**: Rust Observability
- **Issue #399**: C++ Observability

---

**Status**: Gap Analysis Complete
**Decision Required**: Proceed with implementation or defer to v0.49.0?

Part of v0.48.0 Phase 2: Parity Enforcement (Task 2.5)

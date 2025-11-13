# Phase 4: Testing & Quality - Test Plan

**Version**: 1.0
**Date**: November 12, 2025
**Status**: Planning
**Target Completion**: December 2025

## Overview

This document outlines the comprehensive test plan for Phase 4: Testing & Quality. The goal is to ensure agenkit is production-ready with validated cross-language compatibility, proven resilience under failure conditions, and verified correctness properties.

## Objectives

1. **Cross-Language Compatibility**: Verify Python ↔ Go interoperability across all transports
2. **Production Resilience**: Validate failure handling and recovery mechanisms
3. **Correctness Properties**: Ensure invariants hold across all components
4. **Quality Gates**: Establish test coverage and quality metrics for v1.0 release

## Current State

### Existing Test Coverage
- **Python Tests**: 278 tests
  - Unit tests: ~240
  - Integration tests: ~15
  - Observability tests: 25
- **Go Tests**: 181 tests
  - Unit tests: ~150
  - Integration tests: ~12
  - Observability tests: 28
- **Total**: 459 tests

### Coverage Gaps
- ❌ No cross-language integration tests (Python client → Go server, vice versa)
- ❌ No chaos engineering tests (network failures, service crashes)
- ❌ Limited property-based testing (only basic Hypothesis setup)
- ❌ No comprehensive error propagation tests across languages
- ❌ No trace context propagation validation across languages

---

## Test Categories

### 1. Cross-Language Integration Tests

**Priority**: 🔴 Critical (Required for v1.0)
**Estimated Tests**: 35-45
**Estimated Effort**: 5-7 days

#### 1.1 HTTP Transport (15-20 tests)

**Python Client → Go Server:**
- ✅ Basic message exchange
- ✅ Request/response with metadata
- ✅ Error handling and status codes
- ✅ Large messages (1MB, 10MB)
- ✅ Unicode content
- ✅ Concurrent requests (10, 50, 100)
- ✅ Streaming responses
- ✅ Connection reuse and pooling
- ✅ Timeout handling
- ✅ HTTP/1.1, HTTP/2, HTTP/3 protocols

**Go Client → Python Server:**
- Same test scenarios as above

**Files to Create:**
- `tests/integration/test_http_cross_language.py` (Python tests)
- `agenkit-go/tests/integration/http_cross_language_test.go` (Go tests)

#### 1.2 WebSocket Transport (10-12 tests)

**Python Client → Go Server:**
- ✅ Connection establishment
- ✅ Message exchange (unary)
- ✅ Bidirectional communication
- ✅ Streaming (client → server, server → client)
- ✅ Reconnection after disconnect
- ✅ Ping/pong keepalive
- ✅ Large message handling
- ✅ Concurrent connections

**Go Client → Python Server:**
- Same test scenarios as above

**Files to Create:**
- `tests/integration/test_websocket_cross_language.py`
- `agenkit-go/tests/integration/websocket_cross_language_test.go`

#### 1.3 gRPC Transport (10-12 tests)

**Python Client → Go Server:**
- ✅ Unary RPC (Process)
- ✅ Streaming RPC (ProcessStream)
- ✅ Error codes and status propagation
- ✅ Metadata propagation
- ✅ Large messages
- ✅ Concurrent requests
- ✅ Deadlines and timeouts
- ✅ Service discovery

**Go Client → Python Server:**
- Same test scenarios as above

**Files to Create:**
- `tests/integration/test_grpc_cross_language.py`
- `agenkit-go/tests/integration/grpc_cross_language_test.go`

#### 1.4 Cross-Language Observability (5-8 tests)

**Trace Context Propagation:**
- ✅ Python agent → Go agent (trace ID continuity)
- ✅ Go agent → Python agent (trace ID continuity)
- ✅ Multi-hop chains (Python → Go → Python)
- ✅ Parent-child span relationships
- ✅ Span attributes preservation
- ✅ Error recording across languages

**Metrics Consistency:**
- ✅ Request counts match across languages
- ✅ Latency measurements comparable

**Files to Create:**
- `tests/integration/test_observability_cross_language.py`
- `agenkit-go/tests/integration/observability_cross_language_test.go`

---

### 2. Chaos Engineering Tests

**Priority**: 🟡 High (Production confidence)
**Estimated Tests**: 20-30
**Estimated Effort**: 4-6 days

#### 2.1 Network Chaos (8-10 tests)

**Connection Failures:**
- ✅ Connection timeout (server unreachable)
- ✅ Connection refused (port not listening)
- ✅ DNS resolution failure
- ✅ Connection drop mid-request
- ✅ Slow network (high latency injection)
- ✅ Network partition (complete isolation)

**Middleware Validation:**
- ✅ Timeout middleware triggers correctly
- ✅ Retry middleware handles transient failures
- ✅ Circuit breaker opens after threshold

**Files to Create:**
- `tests/chaos/test_network_failures.py`
- `agenkit-go/tests/chaos/network_failures_test.go`

#### 2.2 Service Chaos (6-8 tests)

**Service Failures:**
- ✅ Server crash during request
- ✅ Server restart (graceful vs ungraceful)
- ✅ Slow responses (latency injection: 1s, 5s, 10s)
- ✅ Memory pressure (OOM simulation)
- ✅ CPU saturation (high load)
- ✅ Disk I/O exhaustion

**Middleware Validation:**
- ✅ Circuit breaker protects from cascading failures
- ✅ Rate limiter prevents overload

**Files to Create:**
- `tests/chaos/test_service_failures.py`
- `agenkit-go/tests/chaos/service_failures_test.go`

#### 2.3 Partial Failures (6-8 tests)

**Scenario Testing:**
- ✅ Some agents succeed, some fail (parallel pattern)
- ✅ Intermittent failures (flaky service)
- ✅ Inconsistent responses (non-deterministic)
- ✅ Incomplete responses (truncated data)
- ✅ Message corruption (invalid JSON)
- ✅ Out-of-order responses

**Composition Pattern Validation:**
- ✅ Sequential pattern stops on first failure
- ✅ Parallel pattern returns partial results
- ✅ Fallback pattern switches to backup agent

**Files to Create:**
- `tests/chaos/test_partial_failures.py`
- `agenkit-go/tests/chaos/partial_failures_test.go`

---

### 3. Property-Based Testing Enhancement

**Priority**: 🟢 Medium (Quality improvement)
**Estimated Tests**: 15-25
**Estimated Effort**: 3-4 days

#### 3.1 Middleware Properties (8-10 tests)

**Circuit Breaker:**
- Property: State transitions are deterministic
- Property: Failure counting is accurate
- Property: Recovery timeout is respected
- Property: Half-open state allows limited requests

**Rate Limiter:**
- Property: Token refill rate is constant
- Property: Burst capacity is never exceeded
- Property: Wait time is proportional to tokens needed

**Caching:**
- Property: Cache hits return same data as misses
- Property: TTL expiration is accurate
- Property: LRU eviction maintains order
- Property: Invalidation is immediate

**Timeout:**
- Property: Requests never exceed timeout
- Property: Timeout error is always TimeoutError

**Batching:**
- Property: Batch size never exceeds max
- Property: Wait time never exceeds max
- Property: Individual responses match unbatched

**Files to Create:**
- `tests/property/test_middleware_properties.py`
- `agenkit-go/tests/property/middleware_properties_test.go`

#### 3.2 Composition Properties (4-6 tests)

**Sequential Pattern:**
- Property: Order of execution is preserved
- Property: Failure stops pipeline
- Property: Output of agent N is input to agent N+1

**Parallel Pattern:**
- Property: All agents receive same input
- Property: Failures don't affect other agents
- Property: Result count equals agent count

**Fallback Pattern:**
- Property: Primary tried before fallback
- Property: Fallback only used on primary failure
- Property: First success stops fallback chain

**Conditional Pattern:**
- Property: Only one agent executes per request
- Property: Condition evaluation is deterministic

**Files to Create:**
- `tests/property/test_composition_properties.py`
- `agenkit-go/tests/property/composition_properties_test.go`

#### 3.3 Transport Properties (3-5 tests)

**Message Serialization:**
- Property: Serialize → Deserialize is identity
- Property: All metadata preserved
- Property: Unicode handling is lossless
- Property: Large messages don't corrupt

**Protocol Invariants:**
- Property: HTTP status codes are valid
- Property: WebSocket frames are well-formed
- Property: gRPC status codes map correctly

**Files to Create:**
- `tests/property/test_transport_properties.py`
- `agenkit-go/tests/property/transport_properties_test.go`

---

## Test Infrastructure Requirements

### Tools and Frameworks

**Python:**
- `pytest` - Test runner
- `pytest-asyncio` - Async test support
- `hypothesis` - Property-based testing
- `aioresponses` - HTTP mocking (if needed)
- `pytest-timeout` - Test timeout enforcement
- `psutil` - Resource monitoring for chaos tests

**Go:**
- `testing` - Standard test framework
- `testify/assert` - Assertions
- `rapid` or `gopter` - Property-based testing
- `httptest` - HTTP testing utilities
- `testcontainers-go` - Container orchestration (optional)

**Chaos Engineering:**
- `toxiproxy` - Network chaos proxy (latency, timeouts, drops)
- `pumba` - Container chaos (crashes, stops)
- Manual simulation for simple cases

### Test Environments

**Local Development:**
- Docker Compose for multi-service tests
- Localhost servers for cross-language tests
- Manual chaos injection

**CI/CD:**
- GitHub Actions workflow for Phase 4 tests
- Separate job for chaos tests (may be flaky)
- Extended timeout for integration tests (10-15 minutes)

---

## Test Execution Strategy

### Test Organization

```
tests/
├── integration/           # Existing basic integration tests
│   ├── test_basic_integration.py
│   ├── test_http_cross_language.py         # New
│   ├── test_websocket_cross_language.py    # New
│   ├── test_grpc_cross_language.py         # New
│   └── test_observability_cross_language.py # New
├── chaos/                 # New chaos engineering tests
│   ├── test_network_failures.py
│   ├── test_service_failures.py
│   └── test_partial_failures.py
└── property/              # Enhanced property tests
    ├── test_middleware_properties.py
    ├── test_composition_properties.py
    └── test_transport_properties.py

agenkit-go/tests/
├── integration/           # Existing basic integration tests
│   ├── basic_integration_test.go
│   ├── http_cross_language_test.go         # New
│   ├── websocket_cross_language_test.go    # New
│   ├── grpc_cross_language_test.go         # New
│   └── observability_cross_language_test.go # New
├── chaos/                 # New chaos engineering tests
│   ├── network_failures_test.go
│   ├── service_failures_test.go
│   └── partial_failures_test.go
└── property/              # New property tests
    ├── middleware_properties_test.go
    ├── composition_properties_test.go
    └── transport_properties_test.go
```

### Test Execution Order

1. **Unit tests** (fast, run on every commit)
2. **Integration tests** (medium, run on every PR)
3. **Cross-language integration tests** (slower, run on every PR)
4. **Property tests** (slow, run on every PR)
5. **Chaos tests** (slowest, may be flaky, run nightly or pre-release)

### Test Tags/Markers

**Python:**
```python
@pytest.mark.integration        # Integration tests
@pytest.mark.cross_language     # Cross-language tests
@pytest.mark.chaos              # Chaos engineering tests
@pytest.mark.property           # Property-based tests
@pytest.mark.slow               # Slow tests (>1s)
```

**Go:**
```go
// +build integration        # Integration tests
// +build cross_language     # Cross-language tests
// +build chaos              # Chaos tests
// +build property           # Property tests
```

---

## Success Criteria

### Coverage Targets

- **Unit Test Coverage**: ≥85% (current: ~80%)
- **Integration Test Coverage**: ≥70% of public APIs
- **Cross-Language Test Coverage**: 100% of transport methods
- **Chaos Test Coverage**: All middleware + retry/circuit breaker

### Quality Gates

**Before merging to main:**
- ✅ All unit tests pass
- ✅ All integration tests pass
- ✅ All cross-language tests pass
- ✅ No regressions in benchmarks

**Before v1.0 release:**
- ✅ All property tests pass
- ✅ All chaos tests pass (or documented as known issues)
- ✅ Test coverage targets met
- ✅ No critical bugs in issue tracker

### Performance Targets

- Integration tests complete in <5 minutes
- Cross-language tests complete in <10 minutes
- Property tests complete in <5 minutes
- Chaos tests complete in <15 minutes
- Total CI time <30 minutes

---

## Implementation Plan

### Phase 4.1: Cross-Language Integration Tests (Week 1-2)

**Week 1:**
- [ ] HTTP cross-language tests (Python → Go, Go → Python)
- [ ] WebSocket cross-language tests
- [ ] Setup test infrastructure (servers, helpers)

**Week 2:**
- [ ] gRPC cross-language tests
- [ ] Observability cross-language tests (trace propagation)
- [ ] CI integration

**Deliverables:**
- 35-45 new integration tests
- Test helper utilities
- CI workflow updates

### Phase 4.2: Chaos Engineering Tests (Week 3)

**Days 1-2:**
- [ ] Network chaos tests (timeouts, drops, latency)
- [ ] Setup toxiproxy or manual injection

**Days 3-4:**
- [ ] Service chaos tests (crashes, slow responses)
- [ ] Partial failure tests

**Days 5:**
- [ ] Middleware validation under chaos
- [ ] Documentation and examples

**Deliverables:**
- 20-30 chaos engineering tests
- Chaos test infrastructure
- Failure mode documentation

### Phase 4.3: Property-Based Testing Enhancement (Week 4)

**Days 1-2:**
- [ ] Middleware property tests (circuit breaker, rate limiter, caching)

**Days 3-4:**
- [ ] Composition pattern property tests
- [ ] Transport property tests

**Day 5:**
- [ ] Review and cleanup
- [ ] Documentation

**Deliverables:**
- 15-25 property tests
- Property test examples
- Hypothesis/rapid patterns documentation

---

## Risk Assessment

### High Risk
- **Cross-language tests may be flaky**: Timing issues, port conflicts
  - *Mitigation*: Retry logic, generous timeouts, port randomization
- **Chaos tests are inherently flaky**: Hard to reproduce failures
  - *Mitigation*: Accept some flakiness, run multiple times, document known issues

### Medium Risk
- **Test execution time may be too long**: Slow CI/CD pipeline
  - *Mitigation*: Parallel execution, test sharding, selective test runs
- **Property test failures hard to debug**: Random inputs, large shrinking space
  - *Mitigation*: Good logging, seed preservation, example-based fallbacks

### Low Risk
- **Test maintenance overhead**: More tests = more maintenance
  - *Mitigation*: Good abstractions, test helpers, clear documentation

---

## Appendix

### Related Issues
- Issue #45: Property-based testing with Hypothesis (completed)
- Issue #46: Observability (completed)

### References
- [Chaos Engineering Principles](https://principlesofchaos.org/)
- [Property-Based Testing Best Practices](https://hypothesis.readthedocs.io/)
- [OpenTelemetry Testing Guide](https://opentelemetry.io/docs/specs/otel/trace/api/)

### Stakeholders
- Engineering Team: Implementation
- QA Team: Test review and validation
- DevOps Team: CI/CD integration
- Product Team: Release approval

---

**Document Owner**: Agenkit Team
**Last Updated**: November 12, 2025
**Next Review**: December 1, 2025

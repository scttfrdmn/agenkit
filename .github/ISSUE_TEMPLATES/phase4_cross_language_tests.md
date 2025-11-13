---
name: Cross-Language Integration Tests
about: Implement comprehensive Python ↔ Go integration tests
title: 'Phase 4.1: Cross-Language Integration Tests'
labels: ['testing', 'integration', 'cross-language', 'phase-4', 'priority: critical']
assignees: ''
---

## Overview

Implement comprehensive integration tests to validate Python ↔ Go interoperability across all transport protocols. This is **critical for v1.0** to ensure cross-language compatibility works in production.

## Context

Currently we have:
- ✅ Basic integration tests (Python-only, Go-only)
- ✅ WebSocket integration tests (Python-only)
- ❌ **No cross-language tests** (Python client → Go server, Go client → Python server)

This issue tracks the implementation of ~35-45 new cross-language integration tests.

## Test Plan

See [PHASE4_TEST_PLAN.md](../../docs/PHASE4_TEST_PLAN.md) for complete details.

## Scope

### 1. HTTP Transport Tests (15-20 tests)

**Python Client → Go Server:**
- [ ] Basic message exchange
- [ ] Request/response with metadata
- [ ] Error handling and status codes
- [ ] Large messages (1MB, 10MB)
- [ ] Unicode content
- [ ] Concurrent requests (10, 50, 100)
- [ ] Streaming responses
- [ ] Connection reuse and pooling
- [ ] Timeout handling
- [ ] HTTP/1.1, HTTP/2, HTTP/3 protocols

**Go Client → Python Server:**
- [ ] Same test scenarios as above

**Files to Create:**
- `tests/integration/test_http_cross_language.py`
- `agenkit-go/tests/integration/http_cross_language_test.go`

### 2. WebSocket Transport Tests (10-12 tests)

**Python Client → Go Server:**
- [ ] Connection establishment
- [ ] Message exchange (unary)
- [ ] Bidirectional communication
- [ ] Streaming (client → server, server → client)
- [ ] Reconnection after disconnect
- [ ] Ping/pong keepalive
- [ ] Large message handling
- [ ] Concurrent connections

**Go Client → Python Server:**
- [ ] Same test scenarios as above

**Files to Create:**
- `tests/integration/test_websocket_cross_language.py`
- `agenkit-go/tests/integration/websocket_cross_language_test.go`

### 3. gRPC Transport Tests (10-12 tests)

**Python Client → Go Server:**
- [ ] Unary RPC (Process)
- [ ] Streaming RPC (ProcessStream)
- [ ] Error codes and status propagation
- [ ] Metadata propagation
- [ ] Large messages
- [ ] Concurrent requests
- [ ] Deadlines and timeouts
- [ ] Service discovery

**Go Client → Python Server:**
- [ ] Same test scenarios as above

**Files to Create:**
- `tests/integration/test_grpc_cross_language.py`
- `agenkit-go/tests/integration/grpc_cross_language_test.go`

### 4. Cross-Language Observability Tests (5-8 tests)

**Trace Context Propagation:**
- [ ] Python agent → Go agent (trace ID continuity)
- [ ] Go agent → Python agent (trace ID continuity)
- [ ] Multi-hop chains (Python → Go → Python)
- [ ] Parent-child span relationships
- [ ] Span attributes preservation
- [ ] Error recording across languages

**Metrics Consistency:**
- [ ] Request counts match across languages
- [ ] Latency measurements comparable

**Files to Create:**
- `tests/integration/test_observability_cross_language.py`
- `agenkit-go/tests/integration/observability_cross_language_test.go`

## Test Infrastructure

### Test Helpers Needed:
- [ ] Start Python HTTP server on random port
- [ ] Start Go HTTP server on random port
- [ ] Wait for server readiness (health check)
- [ ] Graceful shutdown helpers
- [ ] Port conflict handling
- [ ] Timeout utilities
- [ ] Assertion helpers for cross-language comparison

### CI/CD Integration:
- [ ] Add GitHub Actions workflow for cross-language tests
- [ ] Ensure both Python and Go environments available
- [ ] Run servers in background
- [ ] Collect logs on failure
- [ ] Extended timeout (10-15 minutes)

## Success Criteria

- [ ] All 35-45 tests pass reliably
- [ ] Tests complete in <10 minutes
- [ ] No port conflicts (randomized ports)
- [ ] Clear error messages on failure
- [ ] Works in CI/CD environment
- [ ] Documentation updated

## Implementation Plan

### Week 1:
- [ ] HTTP cross-language tests (Python → Go, Go → Python)
- [ ] WebSocket cross-language tests
- [ ] Setup test infrastructure (servers, helpers)

### Week 2:
- [ ] gRPC cross-language tests
- [ ] Observability cross-language tests (trace propagation)
- [ ] CI integration

## Related Issues

- Issue #46: Observability (trace context propagation)
- Phase 4 Test Plan: [PHASE4_TEST_PLAN.md](../../docs/PHASE4_TEST_PLAN.md)

## Priority

🔴 **Critical** - Required for v1.0 release

## Estimated Effort

5-7 days

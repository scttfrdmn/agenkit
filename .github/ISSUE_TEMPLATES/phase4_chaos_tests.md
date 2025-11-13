---
name: Chaos Engineering Tests
about: Implement chaos tests to validate production resilience
title: 'Phase 4.2: Chaos Engineering Tests'
labels: ['testing', 'chaos-engineering', 'resilience', 'phase-4', 'priority: high']
assignees: ''
---

## Overview

Implement chaos engineering tests to validate agenkit's resilience under failure conditions. These tests prove that our middleware (circuit breaker, retry, timeout) actually works when things go wrong in production.

## Context

Currently we have:
- ✅ Unit tests for middleware (circuit breaker, retry, timeout, rate limiter)
- ✅ Basic integration tests
- ❌ **No chaos tests** (network failures, service crashes, partial failures)

This issue tracks the implementation of ~20-30 chaos engineering tests.

## Test Plan

See [PHASE4_TEST_PLAN.md](../../docs/PHASE4_TEST_PLAN.md) for complete details.

## Scope

### 1. Network Chaos Tests (8-10 tests)

**Connection Failures:**
- [ ] Connection timeout (server unreachable)
- [ ] Connection refused (port not listening)
- [ ] DNS resolution failure
- [ ] Connection drop mid-request
- [ ] Slow network (high latency injection: 100ms, 1s, 5s)
- [ ] Network partition (complete isolation)

**Middleware Validation:**
- [ ] Timeout middleware triggers correctly on slow responses
- [ ] Retry middleware handles transient connection failures
- [ ] Circuit breaker opens after connection timeout threshold

**Files to Create:**
- `tests/chaos/test_network_failures.py`
- `agenkit-go/tests/chaos/network_failures_test.go`

### 2. Service Chaos Tests (6-8 tests)

**Service Failures:**
- [ ] Server crash during request (ungraceful shutdown)
- [ ] Server restart (graceful vs ungraceful)
- [ ] Slow responses (latency injection: 1s, 5s, 10s)
- [ ] Memory pressure (OOM simulation)
- [ ] CPU saturation (high load simulation)
- [ ] Disk I/O exhaustion (optional)

**Middleware Validation:**
- [ ] Circuit breaker protects from cascading failures
- [ ] Circuit breaker transitions through states correctly (CLOSED → OPEN → HALF_OPEN)
- [ ] Rate limiter prevents service overload

**Files to Create:**
- `tests/chaos/test_service_failures.py`
- `agenkit-go/tests/chaos/service_failures_test.go`

### 3. Partial Failure Tests (6-8 tests)

**Scenario Testing:**
- [ ] Some agents succeed, some fail (parallel pattern with mixed results)
- [ ] Intermittent failures (flaky service simulation)
- [ ] Inconsistent responses (non-deterministic agent)
- [ ] Incomplete responses (truncated data)
- [ ] Message corruption (invalid JSON)
- [ ] Out-of-order responses

**Composition Pattern Validation:**
- [ ] Sequential pattern stops on first failure (fail-fast)
- [ ] Parallel pattern returns partial results (resilient)
- [ ] Fallback pattern switches to backup agent on failure

**Files to Create:**
- `tests/chaos/test_partial_failures.py`
- `agenkit-go/tests/chaos/partial_failures_test.go`

## Chaos Testing Infrastructure

### Tools:

**Option 1: Toxiproxy (Recommended)**
- Network chaos proxy (latency, timeouts, connection drops)
- Easy to use, well-documented
- Requires Docker or standalone binary
```bash
docker run -d -p 8474:8474 -p 20000-20100:20000-20100 shopify/toxiproxy
```

**Option 2: Manual Injection**
- Simpler for basic cases (no dependencies)
- Less realistic but easier to maintain
- Use `time.sleep()` for latency, raise exceptions for failures

### Test Helpers Needed:
- [ ] Toxiproxy client wrapper (if using toxiproxy)
- [ ] Latency injection helper
- [ ] Connection drop helper
- [ ] Server crash simulation
- [ ] Memory/CPU pressure simulation
- [ ] Assertion helpers for chaos scenarios

### CI/CD Integration:
- [ ] Add GitHub Actions workflow for chaos tests (separate from main tests)
- [ ] Install toxiproxy (if using)
- [ ] Longer timeout (15-20 minutes)
- [ ] Mark as allowed to fail initially (may be flaky)
- [ ] Run nightly or pre-release only

## Success Criteria

- [ ] All 20-30 tests pass reliably (or documented flakiness)
- [ ] Tests validate middleware actually works under chaos
- [ ] Circuit breaker proven to prevent cascading failures
- [ ] Retry proven to handle transient failures
- [ ] Timeout proven to prevent hung requests
- [ ] Tests complete in <15 minutes
- [ ] Documentation of failure modes

## Implementation Plan

### Days 1-2:
- [ ] Network chaos tests (timeouts, drops, latency)
- [ ] Setup toxiproxy or manual injection

### Days 3-4:
- [ ] Service chaos tests (crashes, slow responses)
- [ ] Partial failure tests

### Day 5:
- [ ] Middleware validation under chaos
- [ ] Documentation and examples
- [ ] CI integration

## Related Issues

- Issue #42: Timeout and batching middleware
- Phase 4 Test Plan: [PHASE4_TEST_PLAN.md](../../docs/PHASE4_TEST_PLAN.md)

## Priority

🟡 **High** - Production confidence (nice to have for v1.0, required for production readiness)

## Estimated Effort

4-6 days

## Notes

- Chaos tests may be inherently flaky due to timing dependencies
- Accept some flakiness initially, improve over time
- Focus on proving middleware works, not 100% stability
- Document known flaky tests and conditions

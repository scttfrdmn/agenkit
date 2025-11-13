# Phase 4.2: Chaos Engineering Test Plan

**Status**: In Progress
**Goal**: Validate system resilience and middleware effectiveness under failure conditions
**Target**: 20-30 chaos tests

## Overview

Chaos engineering tests validate that Agenkit behaves correctly under adverse conditions:
- Network failures (timeouts, drops, latency)
- Service failures (crashes, slow responses, errors)
- Resource constraints (memory, CPU)
- Middleware resilience (circuit breakers, retries, timeouts)

## Test Categories

### 1. Network Chaos Tests (~8-10 tests)

**Goal**: Validate transport resilience under network failures

#### 1.1 Connection Timeouts
- **Test**: Client connects but server doesn't respond
- **Expected**: Timeout error after configured duration
- **Validates**: Timeout middleware, error handling

#### 1.2 Connection Drops
- **Test**: Connection drops mid-request
- **Expected**: ConnectionError raised, retry if configured
- **Validates**: Connection monitoring, retry logic

#### 1.3 Network Latency
- **Test**: High latency (500ms-2s) injected
- **Expected**: Request completes but slowly, timeout if exceeded
- **Validates**: Timeout configuration, slow response handling

#### 1.4 Intermittent Failures
- **Test**: Random connection failures (20% failure rate)
- **Expected**: Retries succeed, circuit breaker eventually opens
- **Validates**: Retry logic, circuit breaker thresholds

#### 1.5 Packet Loss
- **Test**: 10-30% packet loss injected
- **Expected**: Degraded performance, eventual success or timeout
- **Validates**: TCP retry behavior, timeout handling

### 2. Service Chaos Tests (~8-10 tests)

**Goal**: Validate agent behavior under service failures

#### 2.1 Server Crashes
- **Test**: Server process killed mid-request
- **Expected**: ConnectionError, reconnection on next request
- **Validates**: Connection cleanup, error propagation

#### 2.2 Slow Responses
- **Test**: Server delays response by 5-10 seconds
- **Expected**: Timeout if configured, or long wait
- **Validates**: Timeout middleware, user experience

#### 2.3 Partial Failures
- **Test**: Server returns errors for 50% of requests
- **Expected**: Retry succeeds for transient errors, circuit breaker opens
- **Validates**: Error classification, circuit breaker

#### 2.4 Memory Exhaustion
- **Test**: Server under memory pressure (large responses)
- **Expected**: OOM errors or slow responses, graceful degradation
- **Validates**: Resource limits, error handling

#### 2.5 Malformed Responses
- **Test**: Server returns invalid JSON/protobuf
- **Expected**: MalformedPayloadError, no retries
- **Validates**: Protocol validation, error classification

### 3. Middleware Validation Under Chaos (~8-10 tests)

**Goal**: Prove middleware effectiveness under real failures

#### 3.1 Circuit Breaker Under Failures
- **Test**: Inject 100% failures, verify circuit opens
- **Expected**:
  - Circuit opens after threshold (default: 5 failures)
  - Requests fail-fast while open
  - Circuit attempts recovery after timeout
- **Validates**: Circuit breaker state machine, timing

#### 3.2 Retry Under Transient Failures
- **Test**: 80% failure rate for first 2 attempts, then success
- **Expected**: Retry succeeds after 1-2 attempts
- **Validates**: Retry strategy, exponential backoff

#### 3.3 Timeout Under Slow Responses
- **Test**: Server delays 10s, timeout set to 2s
- **Expected**: Request times out after 2s, no hang
- **Validates**: Timeout enforcement, resource cleanup

#### 3.4 Rate Limiter Under Load
- **Test**: Send 100 requests rapidly (burst > capacity)
- **Expected**: Requests queued, rate-limited, no drops
- **Validates**: Rate limiting accuracy, backpressure

#### 3.5 Cache Under Service Failures
- **Test**: Service fails, cache serves stale data
- **Expected**: Cached responses served, no errors
- **Validates**: Cache fallback, TTL handling

#### 3.6 Middleware Composition Under Failures
- **Test**: Combined circuit breaker + retry + timeout
- **Expected**: Retries until circuit opens, then fail-fast
- **Validates**: Middleware interaction, order independence

## Implementation Strategy

### Option 1: Manual Chaos Injection (Recommended for MVP)

**Pros**:
- No external dependencies
- Fast to implement
- Full control over failure modes
- Works in CI/CD

**Approach**:
```python
class ChaoticAgent(Agent):
    """Agent that injects controlled failures."""

    def __init__(self, agent, failure_rate=0.2, delay_ms=0, fail_after_n=None):
        self.agent = agent
        self.failure_rate = failure_rate
        self.delay_ms = delay_ms
        self.fail_after_n = fail_after_n
        self.call_count = 0

    async def process(self, message):
        self.call_count += 1

        # Inject delay
        if self.delay_ms > 0:
            await asyncio.sleep(self.delay_ms / 1000)

        # Inject failures
        if self.fail_after_n and self.call_count > self.fail_after_n:
            raise RuntimeError("Chaotic failure injected")

        if random.random() < self.failure_rate:
            raise RuntimeError("Random failure injected")

        return await self.agent.process(message)
```

### Option 2: Toxiproxy (Future Enhancement)

**Pros**:
- Realistic network failures
- Industry standard
- Great for integration tests

**Cons**:
- External dependency
- Setup complexity
- Requires Docker/binary

**Use for**: Network-level chaos (latency, drops, partitions)

## Test Infrastructure

### Chaos Helpers

```python
# tests/chaos/helpers.py

class ChaoticTransport:
    """Transport wrapper that injects network failures."""

    def __init__(self, transport, failure_modes):
        self.transport = transport
        self.failure_modes = failure_modes

    async def send_framed(self, data):
        if "connection_drop" in self.failure_modes:
            raise ConnectionError("Connection dropped")

        if "timeout" in self.failure_modes:
            await asyncio.sleep(999)  # Simulate hang

        await self.transport.send_framed(data)

class ChaoticServer:
    """Server that crashes or misbehaves on demand."""

    def __init__(self, crash_after_n=None, slow_response_ms=0):
        self.crash_after_n = crash_after_n
        self.slow_response_ms = slow_response_ms
        self.request_count = 0

    async def handle_request(self, request):
        self.request_count += 1

        if self.crash_after_n and self.request_count >= self.crash_after_n:
            os._exit(1)  # Hard crash

        if self.slow_response_ms > 0:
            await asyncio.sleep(self.slow_response_ms / 1000)

        return normal_response
```

## Success Criteria

- [ ] **Network Chaos**: 8-10 tests implemented, all passing
- [ ] **Service Chaos**: 8-10 tests implemented, all passing
- [ ] **Middleware Validation**: 8-10 tests implemented, all passing
- [ ] **Total**: 20-30 chaos tests passing
- [ ] **Documentation**: Chaos test results documented
- [ ] **CI Integration**: Chaos tests run in CI pipeline

## Test Markers

```python
@pytest.mark.chaos           # Mark as chaos test
@pytest.mark.chaos_network   # Network-level chaos
@pytest.mark.chaos_service   # Service-level chaos
@pytest.mark.chaos_middleware # Middleware validation
@pytest.mark.slow            # Chaos tests may be slow
```

## Expected Timeline

- **Day 1**: Infrastructure + Network chaos (8 tests)
- **Day 2**: Service chaos (8 tests)
- **Day 3**: Middleware validation (8 tests)
- **Day 4**: Documentation + CI integration

## References

- [Principles of Chaos Engineering](https://principlesofchaos.org/)
- [Netflix Chaos Monkey](https://netflix.github.io/chaosmonkey/)
- [Toxiproxy](https://github.com/Shopify/toxiproxy)

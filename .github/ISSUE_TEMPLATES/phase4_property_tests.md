---
name: Property-Based Testing Enhancement
about: Expand property-based testing coverage for all components
title: 'Phase 4.3: Property-Based Testing Enhancement'
labels: ['testing', 'property-based', 'hypothesis', 'phase-4', 'priority: medium']
assignees: ''
---

## Overview

Expand property-based testing coverage to all middleware, composition patterns, and transports. Property-based tests find edge cases that unit tests miss by testing invariants across many random inputs.

## Context

Currently we have:
- ✅ Hypothesis installed and basic setup (Issue #45)
- ✅ Some basic property tests
- ❌ **Limited coverage** across middleware and patterns

This issue tracks the implementation of ~15-25 new property tests.

## Test Plan

See [PHASE4_TEST_PLAN.md](../../docs/PHASE4_TEST_PLAN.md) for complete details.

## Scope

### 1. Middleware Property Tests (8-10 tests)

**Circuit Breaker:**
- [ ] Property: State transitions are deterministic (CLOSED → OPEN → HALF_OPEN → CLOSED)
- [ ] Property: Failure counting is accurate (increments on error, resets on success)
- [ ] Property: Recovery timeout is respected (OPEN state lasts exactly timeout duration)
- [ ] Property: Half-open state allows limited requests (exactly success_threshold requests)

**Rate Limiter:**
- [ ] Property: Token refill rate is constant over time
- [ ] Property: Burst capacity is never exceeded
- [ ] Property: Wait time is proportional to tokens needed

**Caching:**
- [ ] Property: Cache hits return same data as cache misses (consistency)
- [ ] Property: TTL expiration is accurate (±100ms tolerance)
- [ ] Property: LRU eviction maintains access order
- [ ] Property: Cache invalidation is immediate (no stale data after invalidate)

**Timeout:**
- [ ] Property: Requests never exceed timeout duration
- [ ] Property: Timeout error is always TimeoutError (not generic Exception)

**Batching:**
- [ ] Property: Batch size never exceeds max_batch_size
- [ ] Property: Wait time never exceeds max_wait_time
- [ ] Property: Individual responses match unbatched responses (correctness)

**Files to Create:**
- `tests/property/test_middleware_properties.py`
- `agenkit-go/tests/property/middleware_properties_test.go`

### 2. Composition Pattern Property Tests (4-6 tests)

**Sequential Pattern:**
- [ ] Property: Order of execution is preserved (agent1 before agent2 before agent3)
- [ ] Property: Failure stops pipeline (no subsequent agents executed)
- [ ] Property: Output of agent N is input to agent N+1 (chaining)

**Parallel Pattern:**
- [ ] Property: All agents receive same input (no cross-contamination)
- [ ] Property: Failures don't affect other agents (isolation)
- [ ] Property: Result count equals agent count (all agents execute)

**Fallback Pattern:**
- [ ] Property: Primary tried before fallback (order guarantee)
- [ ] Property: Fallback only used on primary failure (not on success)
- [ ] Property: First success stops fallback chain (short-circuit)

**Conditional Pattern:**
- [ ] Property: Only one agent executes per request (exclusivity)
- [ ] Property: Condition evaluation is deterministic (same input → same route)

**Files to Create:**
- `tests/property/test_composition_properties.py`
- `agenkit-go/tests/property/composition_properties_test.go`

### 3. Transport Property Tests (3-5 tests)

**Message Serialization:**
- [ ] Property: Serialize → Deserialize is identity (round-trip)
- [ ] Property: All metadata preserved through serialization
- [ ] Property: Unicode handling is lossless (no encoding errors)
- [ ] Property: Large messages don't corrupt (size limits)

**Protocol Invariants:**
- [ ] Property: HTTP status codes are valid (200-599 range)
- [ ] Property: WebSocket frames are well-formed
- [ ] Property: gRPC status codes map correctly

**Files to Create:**
- `tests/property/test_transport_properties.py`
- `agenkit-go/tests/property/transport_properties_test.go`

## Property Testing Tools

### Python: Hypothesis
Already installed (Issue #45), expand usage:
```python
from hypothesis import given, strategies as st

@given(
    content=st.text(min_size=1, max_size=1000),
    metadata=st.dictionaries(st.text(), st.text())
)
def test_message_serialization_roundtrip(content, metadata):
    original = Message(role="user", content=content, metadata=metadata)
    serialized = original.to_dict()
    deserialized = Message.from_dict(serialized)
    assert original == deserialized
```

### Go: rapid or gopter
Choose one and install:

**Option 1: rapid (Recommended)**
```bash
go get pgregory.net/rapid
```
```go
func TestMessageSerializationRoundtrip(t *testing.T) {
    rapid.Check(t, func(t *rapid.T) {
        content := rapid.String().Draw(t, "content")
        original := &Message{Role: "user", Content: content}
        serialized, _ := json.Marshal(original)
        var deserialized Message
        json.Unmarshal(serialized, &deserialized)
        if original.Content != deserialized.Content {
            t.Fatalf("roundtrip failed")
        }
    })
}
```

**Option 2: gopter**
```bash
go get github.com/leanovate/gopter
```

## Test Helpers Needed:

- [ ] Custom Hypothesis strategies for Message, Agent, Metadata
- [ ] Rapid generators for Go types
- [ ] Assertion helpers for property violations
- [ ] Shrinking helpers (simplify failing examples)
- [ ] Seed preservation for reproducibility

## Success Criteria

- [ ] All 15-25 property tests pass
- [ ] Tests find at least 1-2 real bugs (validation of approach)
- [ ] Tests complete in <5 minutes (with reasonable example counts)
- [ ] Failing tests shrink to minimal examples
- [ ] Documentation with property testing examples
- [ ] CI integration

## Implementation Plan

### Days 1-2:
- [ ] Middleware property tests (circuit breaker, rate limiter, caching)
- [ ] Setup rapid or gopter for Go

### Days 3-4:
- [ ] Composition pattern property tests
- [ ] Transport property tests

### Day 5:
- [ ] Review and cleanup
- [ ] Documentation and examples
- [ ] CI integration

## Related Issues

- Issue #45: Property-based testing with Hypothesis (foundation)
- Phase 4 Test Plan: [PHASE4_TEST_PLAN.md](../../docs/PHASE4_TEST_PLAN.md)

## Priority

🟢 **Medium** - Quality improvement (nice to have for v1.0, very useful for long-term maintenance)

## Estimated Effort

3-4 days

## Resources

- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [rapid Documentation](https://pkg.go.dev/pgregory.net/rapid)
- [Property-Based Testing Patterns](https://fsharpforfunandprofit.com/posts/property-based-testing/)

## Notes

- Start with simple properties, add complexity
- Property tests may find bugs - that's the point!
- Focus on invariants that should *always* hold
- Document any properties that are "too strict" (false positives)
- Keep example counts reasonable (100-1000 per test)

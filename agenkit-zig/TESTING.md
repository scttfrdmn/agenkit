# Zig Testing Guide

## Overview

Agenkit-Zig uses two categories of tests:

1. **Unit/integration tests** — inline `test` blocks in `src/` and `tests/cross_language/`
2. **Property-based tests** — randomized invariant tests in `tests/property/`

All tests are run with a single command:

```bash
zig build test
```

---

## Property-Based Testing

### Why a Custom Framework?

The Zig package ecosystem does not yet have a mature, widely-adopted property-based testing library. Rather than adding an external dependency for 35 tests, we built a minimal framework on top of `std.Random.DefaultPrng`:

- **Zero dependencies** — uses only `std` library
- **Deterministic** — given a fixed seed, tests always run the same sequence
- **Reproducible failures** — if a test fails, re-run with the same seed to reproduce
- **Fast** — no shrinking overhead (Zig tests are already fast)

### How It Works

The framework lives in `tests/property/framework.zig`:

```zig
pub fn runProperty(
    name: []const u8,
    iterations: u32,
    seed: u64,
    allocator: std.mem.Allocator,
    prop_fn: *const fn (std.Random, std.mem.Allocator) anyerror!void,
) !void {
    var prng = std.Random.DefaultPrng.init(seed);
    const rng = prng.random();
    var i: u32 = 0;
    while (i < iterations) : (i += 1) {
        try prop_fn(rng, allocator);
    }
}
```

- A single `DefaultPrng` is initialized with a fixed seed
- The same `std.Random` handle is passed to each iteration
- Since the PRNG state advances with every call to `rng.int()`, `rng.float()`, etc., each iteration sees different values
- Each test file uses a unique seed constant so test files don't interfere

### Running Property Tests

```bash
# Run all tests (includes property tests)
zig build test

# Verify property tests pass individually
zig test tests/property/message_properties.zig --dep agenkit -Magenkit=src/root.zig
zig test tests/property/middleware_properties.zig --dep agenkit -Magenkit=src/root.zig
zig test tests/property/agent_properties.zig --dep agenkit -Magenkit=src/root.zig
```

---

## Property Test Files

### `tests/property/message_properties.zig` (12 tests)

Tests invariants of `Message`, `Role`, `Content`, and `Result` types:

| Test | Invariant |
|------|-----------|
| `role_survives_roundtrip` | Any Role set on a Message is read back unchanged |
| `text_content_survives_creation` | Any text passed to `withText` is returned by `contentAsText` |
| `empty_text_is_valid` | `withText` with `""` succeeds, `contentAsText` returns `""` |
| `unicode_text_preserved` | Unicode (emoji, CJK, Cyrillic) survives Message creation |
| `long_text_preserved` | Text up to 64KB survives without truncation |
| `role_enum_all_values` | All 5 Role variants are valid and round-trip correctly |
| `message_deinit_is_safe` | Calling `deinit` on any valid Message does not panic |
| `multiple_messages_independent` | Two Messages with different content don't share memory |
| `assistant_role_roundtrip` | `.assistant` role specifically survives (critical for responses) |
| `content_type_discriminant_preserved` | `.text` content union tag stays `.text`, not `.structured` |
| `agent_result_ok_wraps_message` | `Result{ .ok = msg }` preserves role and content |
| `agent_result_err_wraps_error` | `Result{ .err = err }` preserves the specific error value |

### `tests/property/middleware_properties.zig` (13 tests)

Tests behavioral invariants of retry, circuit breaker, and rate limiter middleware:

| Test | Invariant |
|------|-----------|
| `retry_never_exceeds_max_retries` | Failing agent is called at most `max_retries` times total |
| `retry_succeeds_on_first_success` | Succeeding agent is called exactly once regardless of `max_retries` |
| `retry_propagates_last_error` | After exhausting retries, error is not swallowed |
| `retry_one_max_retry_calls_once` | `max_retries=1` calls inner agent exactly once |
| `circuit_breaker_opens_after_threshold` | After N failures, state transitions to `.OPEN` |
| `circuit_breaker_closed_passes_requests` | In `.CLOSED` state, requests reach the inner agent |
| `circuit_breaker_open_rejects_immediately` | In `.OPEN` state, inner agent is never called |
| `rate_limiter_allows_under_limit` | Requests below bucket capacity are all allowed |
| `rate_limiter_preserves_content` | Allowed requests return the inner agent's exact response |
| `middleware_name_stable` | `agent.name()` returns the same string on repeated calls |
| `middleware_wrapping_preserves_success` | Success response passes through retry middleware unchanged |
| `retry_backoff_is_bounded` | `max_delay_ms >= initial_delay_ms` always holds for valid config |
| `circuit_breaker_threshold_respected` | Exactly `failure_threshold` failures trigger the `.OPEN` transition |

> **Note on retry timing**: `RetryDecorator` uses real `Thread.sleep` between attempts. All retry property tests use `initial_delay_ms=1, max_delay_ms=2` to keep total wall time under 1 second.

### `tests/property/agent_properties.zig` (10 tests)

Tests invariants of the Agent interface and SequentialAgent composition:

| Test | Invariant |
|------|-----------|
| `echo_agent_returns_assistant_role` | EchoAgent always produces `Role.assistant` regardless of input |
| `echo_agent_content_preserved` | EchoAgent output content equals input content |
| `agent_name_is_stable` | `agent.name()` returns identical bytes on repeated calls |
| `sequential_preserves_final_content` | `SequentialAgent(echo, echo)` output equals input content |
| `sequential_empty_input_passthrough` | Empty-string message passes through SequentialAgent unchanged |
| `failing_agent_always_errors` | FailingAgent always returns `.err` regardless of input |
| `result_ok_not_err` | `.ok` result is never also `.err` (discriminant integrity) |
| `agent_deinit_is_safe` | Calling `deinit` after process completes does not panic |
| `message_role_not_mutated_by_agent` | Input Message role is not modified as a side effect of `process()` |
| `multiple_process_calls_consistent` | Calling process twice with same input produces same output |

---

## Test Helpers (`tests/property/framework.zig`)

| Helper | Purpose |
|--------|---------|
| `runProperty(name, N, seed, allocator, fn)` | Run `fn` N times with advancing PRNG |
| `randomRole(rng)` | Return a random `Role` enum value |
| `randomText(rng, allocator, max_len)` | Generate random printable ASCII string |
| `FailingAgent` | Agent that always returns `ProcessingFailed` |
| `CountingFailingAgent` | Counts `process()` calls, always returns `ProcessingFailed` |
| `CountingEchoAgent` | Counts `process()` calls, echoes input as assistant |

---

## Adding New Properties

1. Create or edit a property test file in `tests/property/`
2. Import framework helpers: `const framework = @import("framework.zig");`
3. Write a property function: `fn myProp(rng: std.Random, allocator: std.mem.Allocator) !void { ... }`
4. Write a test block:
   ```zig
   test "my_property_name" {
       try framework.runProperty("my_property_name", 50, MY_SEED, testing.allocator, myProp);
   }
   ```
5. If creating a new file, add it to `build.zig` following the existing pattern

---

## Comparison with Other Implementations

| Language | PBT Library | Approach |
|----------|------------|---------|
| Go | `testing/quick` | stdlib built-in, runs 100 iterations by default |
| TypeScript | `fast-check` | npm package, supports model-based testing and shrinking |
| Rust | `proptest` | crate with shrinking, strategies, and regression corpus |
| Zig | Custom (this) | `std.Random.DefaultPrng`, N=50 iterations, no shrinking |

The lack of shrinking is the main limitation of the custom Zig framework — when a property fails, you see the first failing input but not a minimal reproduction. To debug a failure, inspect the PRNG seed and iteration index.

---

## Test Counts (v0.78.0)

| Category | Count |
|----------|-------|
| Inline source tests | 351 |
| Cross-language integration | 42 |
| Property-based (new) | 35 |
| **Total** | **428** |

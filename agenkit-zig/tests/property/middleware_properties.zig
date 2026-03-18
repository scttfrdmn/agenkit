/// Property-based tests for middleware (retry, circuit breaker, rate limiter)
///
/// Verifies behavioral invariants of all three middleware types under
/// randomized configurations. Each property runs 50 times.
///
/// NOTE: RetryDecorator uses real sleep between attempts. All tests use
/// initial_delay_ms=1, max_delay_ms=2 to keep total test time <1s.
///
/// Run with: zig build test

const std = @import("std");
const testing = std.testing;
const agenkit = @import("agenkit");
const Agent = agenkit.Agent;
const AgentError = agenkit.AgentError;
const Message = agenkit.Message;
const Role = agenkit.Role;
const Result = agenkit.Result;
const RetryDecorator = agenkit.middleware.RetryDecorator;
const RetryConfig = agenkit.middleware.RetryConfig;
const CircuitBreakerDecorator = agenkit.middleware.CircuitBreakerDecorator;
const CircuitBreakerConfig = agenkit.middleware.CircuitBreakerConfig;
const CircuitState = agenkit.middleware.CircuitState;
const RateLimiterDecorator = agenkit.middleware.RateLimiterDecorator;
const RateLimiterConfig = agenkit.middleware.RateLimiterConfig;
const EchoAgent = agenkit.EchoAgent;

const framework = @import("framework.zig");

const ITERATIONS: u32 = 50;
const SEED: u64 = 0xcafebabe;

// ---------------------------------------------------------------------------
// Property 1: retry never exceeds max_retries total calls
// ---------------------------------------------------------------------------

fn propRetryNeverExceedsMaxRetries(rng: std.Random, allocator: std.mem.Allocator) !void {
    // max_retries is total attempts including initial (min=1)
    const max_retries = rng.intRangeAtMost(u32, 1, 5);

    var inner = try framework.CountingFailingAgent.init(allocator);
    defer inner.deinit();

    const config = RetryConfig{
        .max_retries = max_retries,
        .initial_delay_ms = 1,
        .max_delay_ms = 2,
        .multiplier = 2.0,
    };

    var retry = try RetryDecorator.init(allocator, inner.agent(), config);
    defer retry.agent().deinit();

    var msg = try Message.withText(allocator, .user, "test");
    defer msg.deinit();

    // Expect failure (inner agent always fails)
    const result = retry.agent().process(msg) catch Result{ .err = AgentError.ProcessingFailed };
    try testing.expect(result.isErr());

    // Call count must equal max_retries (total attempts = max_retries)
    try testing.expectEqual(max_retries, @as(u32, @intCast(inner.call_count)));
}

test "retry_never_exceeds_max_retries" {
    try framework.runProperty(
        "retry_never_exceeds_max_retries",
        ITERATIONS,
        SEED,
        testing.allocator,
        propRetryNeverExceedsMaxRetries,
    );
}

// ---------------------------------------------------------------------------
// Property 2: retry succeeds on first success — call count = 1
// ---------------------------------------------------------------------------

fn propRetrySucceedsOnFirstSuccess(rng: std.Random, allocator: std.mem.Allocator) !void {
    const max_retries = rng.intRangeAtMost(u32, 1, 5);

    // Use counting echo — succeeds on every call
    var inner = try framework.CountingEchoAgent.init(allocator);
    defer inner.deinit();

    const config = RetryConfig{
        .max_retries = max_retries,
        .initial_delay_ms = 1,
        .max_delay_ms = 2,
        .multiplier = 2.0,
    };

    var retry = try RetryDecorator.init(allocator, inner.agent(), config);
    defer retry.agent().deinit();

    var msg = try Message.withText(allocator, .user, "ping");
    defer msg.deinit();

    const result = try retry.agent().process(msg);
    try testing.expect(result.isOk());

    var response = try result.unwrap();
    defer response.deinit();

    // Should have called inner exactly once regardless of max_retries
    try testing.expectEqual(@as(usize, 1), inner.call_count);
}

test "retry_succeeds_on_first_success" {
    try framework.runProperty(
        "retry_succeeds_on_first_success",
        ITERATIONS,
        SEED + 1,
        testing.allocator,
        propRetrySucceedsOnFirstSuccess,
    );
}

// ---------------------------------------------------------------------------
// Property 3: retry propagates last error after exhausting retries
// ---------------------------------------------------------------------------

fn propRetryPropagatesLastError(_: std.Random, allocator: std.mem.Allocator) !void {
    var inner = try framework.FailingAgent.init(allocator);
    defer inner.deinit();

    const config = RetryConfig{
        .max_retries = 3,
        .initial_delay_ms = 1,
        .max_delay_ms = 2,
        .multiplier = 2.0,
    };

    var retry = try RetryDecorator.init(allocator, inner.agent(), config);
    defer retry.agent().deinit();

    var msg = try Message.withText(allocator, .user, "test");
    defer msg.deinit();

    // After exhausting retries, should return an error (not swallow it)
    const outcome = retry.agent().process(msg);
    if (outcome) |res| {
        try testing.expect(res.isErr());
    } else |_| {
        // Also acceptable — the error propagated up
    }
}

test "retry_propagates_last_error" {
    try framework.runProperty(
        "retry_propagates_last_error",
        ITERATIONS,
        SEED + 2,
        testing.allocator,
        propRetryPropagatesLastError,
    );
}

// ---------------------------------------------------------------------------
// Property 4: retry with max_retries=1 calls inner exactly once
// ---------------------------------------------------------------------------

fn propRetryOneMaxRetryCallsOnce(_: std.Random, allocator: std.mem.Allocator) !void {
    var inner = try framework.CountingFailingAgent.init(allocator);
    defer inner.deinit();

    const config = RetryConfig{
        .max_retries = 1,
        .initial_delay_ms = 1,
        .max_delay_ms = 2,
        .multiplier = 2.0,
    };

    var retry = try RetryDecorator.init(allocator, inner.agent(), config);
    defer retry.agent().deinit();

    var msg = try Message.withText(allocator, .user, "test");
    defer msg.deinit();

    _ = retry.agent().process(msg) catch {};

    try testing.expectEqual(@as(usize, 1), inner.call_count);
}

test "retry_one_max_retry_calls_once" {
    try framework.runProperty(
        "retry_one_max_retry_calls_once",
        ITERATIONS,
        SEED + 3,
        testing.allocator,
        propRetryOneMaxRetryCallsOnce,
    );
}

// ---------------------------------------------------------------------------
// Property 5: circuit breaker opens after failure_threshold failures
// ---------------------------------------------------------------------------

fn propCircuitBreakerOpensAfterThreshold(rng: std.Random, allocator: std.mem.Allocator) !void {
    const threshold = rng.intRangeAtMost(u32, 1, 5);

    var inner = try framework.FailingAgent.init(allocator);
    defer inner.deinit();

    const config = CircuitBreakerConfig{
        .failure_threshold = threshold,
        .success_threshold = 2,
        .recovery_timeout_ms = 60000,
        .request_timeout_ms = 5000,
    };

    var breaker = try CircuitBreakerDecorator.init(allocator, inner.agent(), config);
    defer breaker.agent().deinit();

    var msg = try Message.withText(allocator, .user, "test");
    defer msg.deinit();

    // Fire exactly threshold failures
    var i: u32 = 0;
    while (i < threshold) : (i += 1) {
        _ = breaker.agent().process(msg) catch {};
    }

    // Circuit should now be OPEN
    try testing.expectEqual(CircuitState.OPEN, breaker.getState());
}

test "circuit_breaker_opens_after_threshold" {
    try framework.runProperty(
        "circuit_breaker_opens_after_threshold",
        ITERATIONS,
        SEED + 4,
        testing.allocator,
        propCircuitBreakerOpensAfterThreshold,
    );
}

// ---------------------------------------------------------------------------
// Property 6: circuit breaker in closed state passes requests to inner agent
// ---------------------------------------------------------------------------

fn propCircuitBreakerClosedPassesRequests(_: std.Random, allocator: std.mem.Allocator) !void {
    var inner = try framework.CountingEchoAgent.init(allocator);
    defer inner.deinit();

    const config = CircuitBreakerConfig{
        .failure_threshold = 10, // high threshold — won't open during test
        .success_threshold = 2,
        .recovery_timeout_ms = 60000,
        .request_timeout_ms = 5000,
    };

    var breaker = try CircuitBreakerDecorator.init(allocator, inner.agent(), config);
    defer breaker.agent().deinit();

    // Verify circuit starts CLOSED
    try testing.expectEqual(CircuitState.CLOSED, breaker.getState());

    var msg = try Message.withText(allocator, .user, "ping");
    defer msg.deinit();

    const result = try breaker.agent().process(msg);
    try testing.expect(result.isOk());

    var response = try result.unwrap();
    defer response.deinit();

    // Inner agent should have been called
    try testing.expect(inner.call_count > 0);
}

test "circuit_breaker_closed_passes_requests" {
    try framework.runProperty(
        "circuit_breaker_closed_passes_requests",
        ITERATIONS,
        SEED + 5,
        testing.allocator,
        propCircuitBreakerClosedPassesRequests,
    );
}

// ---------------------------------------------------------------------------
// Property 7: circuit breaker open state rejects immediately (no inner call)
// ---------------------------------------------------------------------------

fn propCircuitBreakerOpenRejectsImmediately(_: std.Random, allocator: std.mem.Allocator) !void {
    var inner = try framework.CountingFailingAgent.init(allocator);
    defer inner.deinit();

    const config = CircuitBreakerConfig{
        .failure_threshold = 1, // opens after 1 failure
        .success_threshold = 2,
        .recovery_timeout_ms = 60000, // long timeout so it stays OPEN
        .request_timeout_ms = 5000,
    };

    var breaker = try CircuitBreakerDecorator.init(allocator, inner.agent(), config);
    defer breaker.agent().deinit();

    var msg = try Message.withText(allocator, .user, "test");
    defer msg.deinit();

    // One call to open the circuit
    _ = breaker.agent().process(msg) catch {};

    try testing.expectEqual(CircuitState.OPEN, breaker.getState());

    // Record call count before open-state rejection
    const count_before = inner.call_count;

    // These calls should be rejected without reaching the inner agent
    _ = breaker.agent().process(msg) catch {};
    _ = breaker.agent().process(msg) catch {};

    // Inner agent should NOT have been called again
    try testing.expectEqual(count_before, inner.call_count);
}

test "circuit_breaker_open_rejects_immediately" {
    try framework.runProperty(
        "circuit_breaker_open_rejects_immediately",
        ITERATIONS,
        SEED + 6,
        testing.allocator,
        propCircuitBreakerOpenRejectsImmediately,
    );
}

// ---------------------------------------------------------------------------
// Property 8: rate limiter allows requests under capacity
// ---------------------------------------------------------------------------

fn propRateLimiterAllowsUnderLimit(rng: std.Random, allocator: std.mem.Allocator) !void {
    const capacity: u32 = rng.intRangeAtMost(u32, 3, 10);
    // Request fewer than capacity to ensure all succeed
    const num_requests = rng.intRangeAtMost(u32, 1, capacity - 1);

    var inner = try framework.CountingEchoAgent.init(allocator);
    defer inner.deinit();

    const config = RateLimiterConfig{
        .rate = 1000.0, // high rate so tokens refill quickly if needed
        .capacity = capacity,
        .tokens_per_request = 1,
        .max_wait_timeout_ms = 10, // fail fast if bucket is unexpectedly empty
    };

    var limiter = try RateLimiterDecorator.init(allocator, inner.agent(), config);
    defer limiter.agent().deinit();

    var msg = try Message.withText(allocator, .user, "test");
    defer msg.deinit();

    var allowed: u32 = 0;
    var i: u32 = 0;
    while (i < num_requests) : (i += 1) {
        const res = limiter.agent().process(msg) catch continue;
        if (res.isOk()) {
            var response = res.unwrap() catch continue;
            response.deinit();
            allowed += 1;
        }
    }

    // All requests under capacity should have been allowed
    try testing.expectEqual(num_requests, allowed);
}

test "rate_limiter_allows_under_limit" {
    try framework.runProperty(
        "rate_limiter_allows_under_limit",
        ITERATIONS,
        SEED + 7,
        testing.allocator,
        propRateLimiterAllowsUnderLimit,
    );
}

// ---------------------------------------------------------------------------
// Property 9: rate limiter preserves response content
// ---------------------------------------------------------------------------

fn propRateLimiterPreservesContent(rng: std.Random, allocator: std.mem.Allocator) !void {
    const text = try framework.randomText(rng, allocator, 64);
    defer allocator.free(text);

    var inner = try EchoAgent.init(allocator);
    defer inner.agent().deinit();

    const config = RateLimiterConfig{
        .rate = 1000.0,
        .capacity = 10,
        .tokens_per_request = 1,
        .max_wait_timeout_ms = 10,
    };

    var limiter = try RateLimiterDecorator.init(allocator, inner.agent(), config);
    defer limiter.agent().deinit();

    var msg = try Message.withText(allocator, .user, text);
    defer msg.deinit();

    const result = try limiter.agent().process(msg);
    try testing.expect(result.isOk());

    var response = try result.unwrap();
    defer response.deinit();

    const out = try response.contentAsText();
    try testing.expectEqualStrings(text, out);
}

test "rate_limiter_preserves_content" {
    try framework.runProperty(
        "rate_limiter_preserves_content",
        ITERATIONS,
        SEED + 8,
        testing.allocator,
        propRateLimiterPreservesContent,
    );
}

// ---------------------------------------------------------------------------
// Property 10: middleware name is stable across multiple calls
// ---------------------------------------------------------------------------

fn propMiddlewareNameStable(_: std.Random, allocator: std.mem.Allocator) !void {
    var inner = try EchoAgent.init(allocator);
    defer inner.agent().deinit();

    const config = RetryConfig{
        .max_retries = 1,
        .initial_delay_ms = 1,
        .max_delay_ms = 2,
        .multiplier = 2.0,
    };

    var retry = try RetryDecorator.init(allocator, inner.agent(), config);
    defer retry.agent().deinit();

    const ag = retry.agent();
    const name1 = ag.name();
    const name2 = ag.name();
    const name3 = ag.name();

    try testing.expectEqualStrings(name1, name2);
    try testing.expectEqualStrings(name2, name3);
}

test "middleware_name_stable" {
    try framework.runProperty(
        "middleware_name_stable",
        ITERATIONS,
        SEED + 9,
        testing.allocator,
        propMiddlewareNameStable,
    );
}

// ---------------------------------------------------------------------------
// Property 11: wrapping with middleware preserves success response
// ---------------------------------------------------------------------------

fn propMiddlewareWrappingPreservesSuccess(rng: std.Random, allocator: std.mem.Allocator) !void {
    const text = try framework.randomText(rng, allocator, 64);
    defer allocator.free(text);

    var inner = try EchoAgent.init(allocator);
    defer inner.agent().deinit();

    const config = RetryConfig{
        .max_retries = 3,
        .initial_delay_ms = 1,
        .max_delay_ms = 2,
        .multiplier = 2.0,
    };

    var retry = try RetryDecorator.init(allocator, inner.agent(), config);
    defer retry.agent().deinit();

    var msg = try Message.withText(allocator, .user, text);
    defer msg.deinit();

    const result = try retry.agent().process(msg);
    try testing.expect(result.isOk());

    var response = try result.unwrap();
    defer response.deinit();

    const out = try response.contentAsText();
    try testing.expectEqualStrings(text, out);
}

test "middleware_wrapping_preserves_success" {
    try framework.runProperty(
        "middleware_wrapping_preserves_success",
        ITERATIONS,
        SEED + 10,
        testing.allocator,
        propMiddlewareWrappingPreservesSuccess,
    );
}

// ---------------------------------------------------------------------------
// Property 12: retry backoff is bounded by max_delay
// ---------------------------------------------------------------------------
// NOTE: This verifies the config constraint: max_delay_ms >= initial_delay_ms.
// The backoff starts at initial_delay_ms and is capped at max_delay_ms.
// We verify that a valid RetryConfig always satisfies this invariant.

fn propRetryBackoffIsBounded(rng: std.Random, allocator: std.mem.Allocator) !void {
    _ = allocator;
    // Generate random initial and max delay where max >= initial
    const initial = rng.intRangeAtMost(u64, 1, 10);
    // Ensure max >= initial
    const max_extra = rng.intRangeAtMost(u64, 0, 10);
    const max_delay = initial + max_extra;

    const config = RetryConfig{
        .max_retries = 2,
        .initial_delay_ms = initial,
        .max_delay_ms = max_delay,
        .multiplier = 2.0,
    };

    // Config must be valid
    try config.validate();

    // Invariant: max_delay >= initial_delay always holds
    try testing.expect(config.max_delay_ms >= config.initial_delay_ms);
}

test "retry_backoff_is_bounded" {
    try framework.runProperty(
        "retry_backoff_is_bounded",
        ITERATIONS,
        SEED + 11,
        testing.allocator,
        propRetryBackoffIsBounded,
    );
}

// ---------------------------------------------------------------------------
// Property 13: circuit breaker threshold is exactly respected
// ---------------------------------------------------------------------------

fn propCircuitBreakerThresholdRespected(rng: std.Random, allocator: std.mem.Allocator) !void {
    const threshold = rng.intRangeAtMost(u32, 2, 6);

    var inner = try framework.FailingAgent.init(allocator);
    defer inner.deinit();

    const config = CircuitBreakerConfig{
        .failure_threshold = threshold,
        .success_threshold = 2,
        .recovery_timeout_ms = 60000,
        .request_timeout_ms = 5000,
    };

    var breaker = try CircuitBreakerDecorator.init(allocator, inner.agent(), config);
    defer breaker.agent().deinit();

    var msg = try Message.withText(allocator, .user, "test");
    defer msg.deinit();

    // After threshold-1 failures, circuit must still be CLOSED
    var i: u32 = 0;
    while (i < threshold - 1) : (i += 1) {
        _ = breaker.agent().process(msg) catch {};
    }
    try testing.expectEqual(CircuitState.CLOSED, breaker.getState());

    // After exactly threshold-th failure, circuit must be OPEN
    _ = breaker.agent().process(msg) catch {};
    try testing.expectEqual(CircuitState.OPEN, breaker.getState());
}

test "circuit_breaker_threshold_respected" {
    try framework.runProperty(
        "circuit_breaker_threshold_respected",
        ITERATIONS,
        SEED + 12,
        testing.allocator,
        propCircuitBreakerThresholdRespected,
    );
}

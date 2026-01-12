/// Middleware module for Agenkit
///
/// Middleware provides cross-cutting concerns like retry, timeout, circuit breaking,
/// rate limiting, caching, and batching. All middleware implement the Agent interface
/// and can be composed together.
///
/// Example:
/// ```zig
/// // Wrap an agent with retry, then timeout
/// var retry = try RetryDecorator.init(allocator, base_agent, retry_config);
/// defer retry.deinit();
/// // var timeout = try TimeoutDecorator.init(allocator, retry.agent(), timeout_config);
/// // defer timeout.deinit();
/// ```

// Retry middleware
pub const RetryDecorator = @import("retry.zig").RetryDecorator;
pub const RetryConfig = @import("retry.zig").RetryConfig;
pub const RetryMetrics = @import("retry.zig").RetryMetrics;

// Timeout middleware
pub const TimeoutDecorator = @import("timeout.zig").TimeoutDecorator;
pub const TimeoutConfig = @import("timeout.zig").TimeoutConfig;
pub const TimeoutMetrics = @import("timeout.zig").TimeoutMetrics;
pub const MethodTimeout = @import("timeout.zig").MethodTimeout;

// TODO: Add more middleware as they are implemented
// pub const CircuitBreakerDecorator = @import("circuit_breaker.zig").CircuitBreakerDecorator;
// pub const RateLimiter = @import("rate_limiter.zig").RateLimiter;
// pub const CachingDecorator = @import("caching.zig").CachingDecorator;
// pub const BatchingDecorator = @import("batching.zig").BatchingDecorator;

test {
    const std = @import("std");
    std.testing.refAllDecls(@This());
    _ = @import("retry.zig");
    _ = @import("timeout.zig");
}

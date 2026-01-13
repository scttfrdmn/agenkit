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

// Circuit Breaker middleware
pub const CircuitBreakerDecorator = @import("circuit_breaker.zig").CircuitBreakerDecorator;
pub const CircuitBreakerConfig = @import("circuit_breaker.zig").CircuitBreakerConfig;
pub const CircuitBreakerMetrics = @import("circuit_breaker.zig").CircuitBreakerMetrics;
pub const CircuitState = @import("circuit_breaker.zig").CircuitState;
pub const CircuitBreakerError = @import("circuit_breaker.zig").CircuitBreakerError;

// Rate Limiter middleware
pub const RateLimiterDecorator = @import("rate_limiter.zig").RateLimiterDecorator;
pub const RateLimiterConfig = @import("rate_limiter.zig").RateLimiterConfig;
pub const RateLimiterMetrics = @import("rate_limiter.zig").RateLimiterMetrics;
pub const RateLimitError = @import("rate_limiter.zig").RateLimitError;

// Per-User Rate Limiter middleware
pub const PerUserRateLimiterDecorator = @import("per_user_rate_limiter.zig").PerUserRateLimiterDecorator;
pub const PerUserRateLimiterConfig = @import("per_user_rate_limiter.zig").PerUserRateLimiterConfig;
pub const PerUserRateLimiterMetrics = @import("per_user_rate_limiter.zig").PerUserRateLimiterMetrics;
pub const PerUserRateLimitError = @import("per_user_rate_limiter.zig").PerUserRateLimitError;
pub const UserIdExtractor = @import("per_user_rate_limiter.zig").UserIdExtractor;

// Caching middleware
pub const CachingDecorator = @import("caching.zig").CachingDecorator;
pub const CachingConfig = @import("caching.zig").CachingConfig;
pub const CachingMetrics = @import("caching.zig").CachingMetrics;

// Batching middleware
pub const BatchingDecorator = @import("batching.zig").BatchingDecorator;
pub const BatchingConfig = @import("batching.zig").BatchingConfig;
pub const BatchingMetrics = @import("batching.zig").BatchingMetrics;

test {
    const std = @import("std");
    std.testing.refAllDecls(@This());
    _ = @import("retry.zig");
    _ = @import("timeout.zig");
    _ = @import("circuit_breaker.zig");
    _ = @import("rate_limiter.zig");
    _ = @import("per_user_rate_limiter.zig");
    _ = @import("caching.zig");
    _ = @import("batching.zig");
}

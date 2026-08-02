/// Rate limiting middleware using token bucket algorithm
///
/// The token bucket algorithm allows for smooth rate limiting with burst capacity:
/// - Tokens are added to the bucket at a constant rate
/// - Each request consumes tokens from the bucket
/// - If insufficient tokens are available, the request waits or is rejected
/// - Burst capacity allows temporary spikes in traffic
///
/// This is useful for:
/// - Protecting downstream services from overload
/// - Complying with API rate limits (e.g., OpenAI: 3500 RPM)
/// - Fair resource allocation across tenants
/// - Cost control
///
/// Example:
/// ```zig
/// const config = RateLimiterConfig{
///     .rate = 100.0,              // 100 tokens per second
///     .capacity = 200,            // Allow bursts up to 200 requests
///     .tokens_per_request = 1,    // 1 token per request
/// };
///
/// var limiter = try RateLimiterDecorator.init(allocator, base_agent, config);
/// defer limiter.deinit();
///
/// const result = try limiter.agent().process(message);
/// const metrics = limiter.metrics();
/// ```
const std = @import("std");
const agksync = @import("../sync_compat.zig");
const agktime = @import("../time_compat.zig");
const json = std.json;
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const StreamCallbacks = @import("../agent.zig").StreamCallbacks;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;

/// Rate limiter error
pub const RateLimitError = error{
    RateLimitExceeded,
};

/// Configuration for rate limiter behavior
pub const RateLimiterConfig = struct {
    /// Number of tokens added per second
    /// Default: 10.0
    rate: f64 = 10.0,

    /// Maximum burst capacity (maximum tokens in bucket)
    /// Default: 10
    capacity: u32 = 10,

    /// Number of tokens consumed per request
    /// Default: 1
    tokens_per_request: u32 = 1,

    /// Maximum time to wait for tokens in milliseconds (null = wait indefinitely)
    /// Prevents requests from waiting too long when rate limiter is heavily loaded
    /// Default: null (wait indefinitely)
    max_wait_timeout_ms: ?u64 = null,

    /// Validate configuration
    pub fn validate(self: RateLimiterConfig) !void {
        if (self.rate <= 0.0) {
            return error.InvalidConfig;
        }
        if (self.capacity < 1) {
            return error.InvalidConfig;
        }
        if (self.tokens_per_request < 1) {
            return error.InvalidConfig;
        }
        if (self.tokens_per_request > self.capacity) {
            return error.InvalidConfig;
        }
        if (self.max_wait_timeout_ms) |timeout| {
            if (timeout == 0) {
                return error.InvalidConfig;
            }
        }
    }
};

/// Metrics tracked by rate limiter middleware
pub const RateLimiterMetrics = struct {
    /// Total number of requests
    total_requests: u64 = 0,

    /// Number of allowed requests
    allowed_requests: u64 = 0,

    /// Number of rejected requests
    rejected_requests: u64 = 0,

    /// Total time spent waiting for tokens (milliseconds)
    total_wait_time_ms: u64 = 0,

    /// Current number of tokens in bucket
    current_tokens: f64 = 0.0,

    /// Average wait time per request (milliseconds)
    pub fn avgWaitTime(self: *const RateLimiterMetrics) ?f64 {
        if (self.total_requests == 0) return null;
        return @as(f64, @floatFromInt(self.total_wait_time_ms)) / @as(f64, @floatFromInt(self.total_requests));
    }

    /// Rejection rate (percentage)
    pub fn rejectionRate(self: *const RateLimiterMetrics) ?f64 {
        if (self.total_requests == 0) return null;
        return (@as(f64, @floatFromInt(self.rejected_requests)) / @as(f64, @floatFromInt(self.total_requests))) * 100.0;
    }

    /// Create a snapshot of metrics
    pub fn snapshot(self: *const RateLimiterMetrics) RateLimiterMetrics {
        return RateLimiterMetrics{
            .total_requests = self.total_requests,
            .allowed_requests = self.allowed_requests,
            .rejected_requests = self.rejected_requests,
            .total_wait_time_ms = self.total_wait_time_ms,
            .current_tokens = self.current_tokens,
        };
    }
};

/// Rate limiter decorator - wraps an agent with rate limiting protection
pub const RateLimiterDecorator = struct {
    allocator: Allocator,
    inner_agent: Agent,
    config: RateLimiterConfig,
    metrics_data: RateLimiterMetrics,
    tokens: f64,
    last_update_ms: i64,
    mutex: agksync.Mutex,

    pub fn init(allocator: Allocator, inner_agent: Agent, config: RateLimiterConfig) !*RateLimiterDecorator {
        // Validate configuration
        try config.validate();

        const now_ms = agktime.milliTimestamp();
        const initial_tokens = @as(f64, @floatFromInt(config.capacity));

        const self = try allocator.create(RateLimiterDecorator);
        self.* = RateLimiterDecorator{
            .allocator = allocator,
            .inner_agent = inner_agent,
            .config = config,
            .metrics_data = RateLimiterMetrics{ .current_tokens = initial_tokens },
            .tokens = initial_tokens,
            .last_update_ms = now_ms,
            .mutex = agksync.Mutex{},
        };
        return self;
    }

    pub fn agent(self: *RateLimiterDecorator) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .process_stream = processStreamImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
            },
        };
    }

    /// Get current metrics (thread-safe)
    pub fn metrics(self: *RateLimiterDecorator) RateLimiterMetrics {
        self.mutex.lock();
        defer self.mutex.unlock();
        return self.metrics_data.snapshot();
    }

    /// Refill tokens based on elapsed time
    fn refillTokens(self: *RateLimiterDecorator) void {
        const now_ms = agktime.milliTimestamp();
        const elapsed_ms = now_ms - self.last_update_ms;
        const elapsed_sec = @as(f64, @floatFromInt(elapsed_ms)) / 1000.0;

        // Add tokens based on elapsed time
        const tokens_to_add = elapsed_sec * self.config.rate;
        const capacity_f64 = @as(f64, @floatFromInt(self.config.capacity));
        self.tokens = @min(self.tokens + tokens_to_add, capacity_f64);
        self.last_update_ms = now_ms;

        // Update metrics
        self.metrics_data.current_tokens = self.tokens;
    }

    /// Acquire tokens from the bucket.
    ///
    /// Wait-and-retry loop. A single wait is not enough, for two independent
    /// reasons, and the old code returned an error from a branch it labelled
    /// "should not happen" when either bit:
    ///
    ///   1. refillTokens credits elapsed*rate from the wall clock, and
    ///      wait_time_ms truncates toward zero, so the sleep can return having
    ///      credited marginally less than tokens_needed.
    ///   2. The mutex is released across the sleep, so another thread can take
    ///      it first and drain the tokens this caller was waiting for -- a lost
    ///      wakeup. The equivalent Python path raised on every run with
    ///      capacity=1 and 8 concurrent callers (#750), despite a wait budget.
    ///
    /// This previously papered over (1) with an epsilon on the comparison, which
    /// narrowed the jitter window, did nothing for (2), and let a caller take
    /// tokens it had not earned. max_wait_timeout_ms still bounds the total,
    /// measured against cumulative wait, so this cannot spin forever when the
    /// configured rate genuinely cannot satisfy the request.
    fn acquireTokens(self: *RateLimiterDecorator, tokens_needed: u32, wait: bool) !void {
        const tokens_needed_f64 = @as(f64, @floatFromInt(tokens_needed));
        var total_waited_ms: u64 = 0;

        while (true) {
            self.mutex.lock();
            self.refillTokens();

            if (self.tokens >= tokens_needed_f64) {
                // Sufficient tokens available
                self.tokens -= tokens_needed_f64;
                self.metrics_data.current_tokens = self.tokens;
                if (total_waited_ms > 0) {
                    self.metrics_data.total_wait_time_ms += total_waited_ms;
                }
                self.mutex.unlock();
                return;
            }

            if (!wait) {
                // Insufficient tokens and not waiting
                self.mutex.unlock();
                return RateLimitError.RateLimitExceeded;
            }

            // Calculate wait time for the outstanding deficit. Floored at 1ms:
            // a sub-millisecond residual would otherwise truncate to a
            // zero-length sleep and spin hot until the wall clock caught up.
            const tokens_deficit = tokens_needed_f64 - self.tokens;
            const wait_time_sec = tokens_deficit / self.config.rate;
            var wait_time_ms = @as(u64, @intFromFloat(wait_time_sec * 1000.0));
            if (wait_time_ms < 1) {
                wait_time_ms = 1;
            }

            // Check the cumulative wait against max_wait_timeout so repeated
            // short retries cannot outlast the budget.
            if (self.config.max_wait_timeout_ms) |max_timeout| {
                if (total_waited_ms + wait_time_ms > max_timeout) {
                    self.mutex.unlock();
                    return RateLimitError.RateLimitExceeded;
                }
            }

            self.mutex.unlock();

            // Wait outside the lock to allow other operations
            agktime.sleep(wait_time_ms * std.time.ns_per_ms);
            total_waited_ms += wait_time_ms;
        }
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *RateLimiterDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.name();
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *RateLimiterDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.capabilities(allocator);
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *RateLimiterDecorator = @ptrCast(@alignCast(ptr));

        // Track request
        self.mutex.lock();
        self.metrics_data.total_requests += 1;
        self.mutex.unlock();

        // Acquire tokens (wait=true)
        self.acquireTokens(self.config.tokens_per_request, true) catch {
            self.mutex.lock();
            self.metrics_data.rejected_requests += 1;
            self.mutex.unlock();
            return AgentError.Cancelled; // Map RateLimitExceeded to Cancelled
        };

        // Token acquired successfully
        self.mutex.lock();
        self.metrics_data.allowed_requests += 1;
        self.mutex.unlock();

        // Process request
        return self.inner_agent.process(message);
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *RateLimiterDecorator = @ptrCast(@alignCast(ptr));

        // Get introspection from inner agent
        const inner_result = try self.inner_agent.introspect(allocator);

        // Add rate limiter metrics to metadata
        const metrics_snapshot = self.metrics();

        var metadata_map = json.ObjectMap.empty;
        errdefer metadata_map.deinit(allocator);

        // Add metrics as metadata
        try metadata_map.put(allocator, "total_requests", json.Value{ .integer = @intCast(metrics_snapshot.total_requests) });
        try metadata_map.put(allocator, "allowed_requests", json.Value{ .integer = @intCast(metrics_snapshot.allowed_requests) });
        try metadata_map.put(allocator, "rejected_requests", json.Value{ .integer = @intCast(metrics_snapshot.rejected_requests) });
        try metadata_map.put(allocator, "total_wait_time_ms", json.Value{ .integer = @intCast(metrics_snapshot.total_wait_time_ms) });
        try metadata_map.put(allocator, "current_tokens", json.Value{ .float = metrics_snapshot.current_tokens });

        if (metrics_snapshot.avgWaitTime()) |avg| {
            try metadata_map.put(allocator, "avg_wait_time_ms", json.Value{ .float = avg });
        }
        if (metrics_snapshot.rejectionRate()) |rate| {
            try metadata_map.put(allocator, "rejection_rate", json.Value{ .float = rate });
        }

        // Add configuration
        try metadata_map.put(allocator, "rate", json.Value{ .float = self.config.rate });
        try metadata_map.put(allocator, "capacity", json.Value{ .integer = @intCast(self.config.capacity) });
        try metadata_map.put(allocator, "tokens_per_request", json.Value{ .integer = @intCast(self.config.tokens_per_request) });

        // Merge with inner metadata (if it's an object)
        if (inner_result.metadata == .object) {
            var inner_iter = inner_result.metadata.object.iterator();
            while (inner_iter.next()) |entry| {
                const key = entry.key_ptr.*;
                if (!std.mem.startsWith(u8, key, "rate_")) {
                    try metadata_map.put(allocator, key, entry.value_ptr.*);
                }
            }
        }

        return IntrospectionResult{
            .allocator = allocator,
            .timestamp = agktime.timestamp(),
            .agent_name = inner_result.agent_name,
            .capabilities = inner_result.capabilities,
            .memory_state = inner_result.memory_state,
            .internal_state = inner_result.internal_state,
            .metadata = json.Value{ .object = metadata_map },
        };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *RateLimiterDecorator = @ptrCast(@alignCast(ptr));
        // Don't deinit inner agent - caller manages it
        self.allocator.destroy(self);
    }
};

// Tests
const testing = std.testing;

fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
    _ = ptr;
    _ = message;
    callbacks.onError(AgentError.NotImplemented);
}

test "RateLimiterConfig validation" {
    var config = RateLimiterConfig{};
    try config.validate();

    // Invalid: rate <= 0
    config.rate = 0.0;
    try testing.expectError(error.InvalidConfig, config.validate());
    config.rate = -1.0;
    try testing.expectError(error.InvalidConfig, config.validate());
    config.rate = 10.0;

    // Invalid: capacity < 1
    config.capacity = 0;
    try testing.expectError(error.InvalidConfig, config.validate());
    config.capacity = 10;

    // Invalid: tokens_per_request < 1
    config.tokens_per_request = 0;
    try testing.expectError(error.InvalidConfig, config.validate());
    config.tokens_per_request = 1;

    // Invalid: tokens_per_request > capacity
    config.tokens_per_request = 20;
    config.capacity = 10;
    try testing.expectError(error.InvalidConfig, config.validate());
}

test "RateLimiterMetrics calculations" {
    var metrics = RateLimiterMetrics{
        .total_requests = 10,
        .allowed_requests = 8,
        .rejected_requests = 2,
        .total_wait_time_ms = 5000,
    };

    // Average wait time
    const avg = metrics.avgWaitTime().?;
    try testing.expectApproxEqRel(@as(f64, 500.0), avg, 0.01);

    // Rejection rate
    const rejection_rate = metrics.rejectionRate().?;
    try testing.expectApproxEqRel(@as(f64, 20.0), rejection_rate, 0.01);
}

test "RateLimiterMetrics snapshot" {
    var metrics = RateLimiterMetrics{
        .total_requests = 5,
        .allowed_requests = 4,
        .rejected_requests = 1,
        .total_wait_time_ms = 1000,
        .current_tokens = 5.5,
    };

    const snapshot = metrics.snapshot();
    try testing.expectEqual(@as(u64, 5), snapshot.total_requests);
    try testing.expectEqual(@as(u64, 4), snapshot.allowed_requests);
    try testing.expectEqual(@as(u64, 1), snapshot.rejected_requests);
    try testing.expectEqual(@as(u64, 1000), snapshot.total_wait_time_ms);
    try testing.expectApproxEqRel(@as(f64, 5.5), snapshot.current_tokens, 0.01);
}

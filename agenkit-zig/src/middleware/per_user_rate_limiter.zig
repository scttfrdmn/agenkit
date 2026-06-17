/// Per-user rate limiting middleware using token bucket algorithm
///
/// The token bucket algorithm allows for smooth rate limiting with burst capacity,
/// with separate buckets per user/tenant for fair resource allocation:
/// - Each user has their own token bucket
/// - Tokens are added to each bucket at a constant rate
/// - Each request consumes tokens from the user's bucket
/// - If insufficient tokens are available, the request waits or is rejected
/// - Burst capacity allows temporary spikes per user
///
/// This is useful for:
/// - Multi-tenant fairness (prevent one user from starving others)
/// - Per-user quotas and billing
/// - Isolating abuse from legitimate users
/// - SaaS rate limiting
///
/// Example:
/// ```zig
/// const config = PerUserRateLimiterConfig{
///     .rate = 100.0,              // 100 tokens per second per user
///     .capacity = 200,            // Allow bursts up to 200 requests per user
///     .tokens_per_request = 1,    // 1 token per request
/// };
///
/// var limiter = try PerUserRateLimiterDecorator.init(allocator, base_agent, config);
/// defer limiter.deinit();
///
/// const result = try limiter.agent().process(message);
/// const metrics = limiter.metrics();
/// ```
const std = @import("std");
const agksync = @import("../sync_compat.zig");
const agktime = @import("../time_compat.zig");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const StreamCallbacks = @import("../agent.zig").StreamCallbacks;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;

/// Per-user rate limiter error
pub const PerUserRateLimitError = error{
    RateLimitExceeded,
};

/// User ID extractor function type
pub const UserIdExtractor = *const fn (*const Message) []const u8;

/// Default user ID extractor (extracts from metadata["user_id"])
fn defaultUserIdExtractor(message: *const Message) []const u8 {
    if (message.getMetadata("user_id")) |value| {
        if (value == .string) {
            return value.string;
        }
    }
    return "";
}

/// Configuration for per-user rate limiter behavior
pub const PerUserRateLimiterConfig = struct {
    /// Number of tokens added per second per user
    /// Default: 10.0
    rate: f64 = 10.0,

    /// Maximum burst capacity per user (maximum tokens in bucket)
    /// Default: 10
    capacity: u32 = 10,

    /// Number of tokens consumed per request
    /// Default: 1
    tokens_per_request: u32 = 1,

    /// Maximum time to wait for tokens in milliseconds (null = wait indefinitely)
    /// Prevents requests from waiting too long when rate limiter is heavily loaded
    /// Default: null (wait indefinitely)
    max_wait_timeout_ms: ?u64 = null,

    /// Function to extract user ID from message
    /// Default: extracts from metadata["user_id"]
    user_id_extractor: UserIdExtractor = &defaultUserIdExtractor,

    /// Validate configuration
    pub fn validate(self: PerUserRateLimiterConfig) !void {
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

/// User bucket - token bucket for a single user
const UserBucket = struct {
    tokens: f64,
    last_update_ms: i64,

    fn init(capacity: u32) UserBucket {
        return UserBucket{
            .tokens = @as(f64, @floatFromInt(capacity)),
            .last_update_ms = agktime.milliTimestamp(),
        };
    }
};

/// Metrics tracked by per-user rate limiter middleware
pub const PerUserRateLimiterMetrics = struct {
    /// Total number of requests
    total_requests: u64 = 0,

    /// Number of allowed requests
    allowed_requests: u64 = 0,

    /// Number of rejected requests
    rejected_requests: u64 = 0,

    /// Total time spent waiting for tokens (milliseconds)
    total_wait_time_ms: u64 = 0,

    /// Number of active users
    active_users: usize = 0,

    /// Average wait time per request (milliseconds)
    pub fn avgWaitTime(self: *const PerUserRateLimiterMetrics) ?f64 {
        if (self.total_requests == 0) return null;
        return @as(f64, @floatFromInt(self.total_wait_time_ms)) / @as(f64, @floatFromInt(self.total_requests));
    }

    /// Rejection rate (percentage)
    pub fn rejectionRate(self: *const PerUserRateLimiterMetrics) ?f64 {
        if (self.total_requests == 0) return null;
        return (@as(f64, @floatFromInt(self.rejected_requests)) / @as(f64, @floatFromInt(self.total_requests))) * 100.0;
    }

    /// Create a snapshot of metrics
    pub fn snapshot(self: *const PerUserRateLimiterMetrics) PerUserRateLimiterMetrics {
        return PerUserRateLimiterMetrics{
            .total_requests = self.total_requests,
            .allowed_requests = self.allowed_requests,
            .rejected_requests = self.rejected_requests,
            .total_wait_time_ms = self.total_wait_time_ms,
            .active_users = self.active_users,
        };
    }
};

/// Per-user rate limiter decorator - wraps an agent with per-user rate limiting protection
pub const PerUserRateLimiterDecorator = struct {
    allocator: Allocator,
    inner_agent: Agent,
    config: PerUserRateLimiterConfig,
    metrics_data: PerUserRateLimiterMetrics,
    buckets: std.StringHashMap(UserBucket),
    mutex: agksync.Mutex,

    pub fn init(allocator: Allocator, inner_agent: Agent, config: PerUserRateLimiterConfig) !*PerUserRateLimiterDecorator {
        // Validate configuration
        try config.validate();

        const self = try allocator.create(PerUserRateLimiterDecorator);
        self.* = PerUserRateLimiterDecorator{
            .allocator = allocator,
            .inner_agent = inner_agent,
            .config = config,
            .metrics_data = PerUserRateLimiterMetrics{},
            .buckets = std.StringHashMap(UserBucket).init(allocator),
            .mutex = agksync.Mutex{},
        };
        return self;
    }

    pub fn agent(self: *PerUserRateLimiterDecorator) Agent {
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
    pub fn metrics(self: *PerUserRateLimiterDecorator) PerUserRateLimiterMetrics {
        self.mutex.lock();
        defer self.mutex.unlock();
        return self.metrics_data.snapshot();
    }

    /// Get or create user bucket
    fn getUserBucket(self: *PerUserRateLimiterDecorator, user_id: []const u8) !*UserBucket {
        // Note: Assumes mutex is already held by caller

        if (self.buckets.getPtr(user_id)) |bucket| {
            return bucket;
        }

        // Create new bucket for user
        try self.buckets.put(user_id, UserBucket.init(self.config.capacity));
        self.metrics_data.active_users = self.buckets.count();
        return self.buckets.getPtr(user_id).?;
    }

    /// Refill tokens for a user based on elapsed time
    fn refillUserTokens(self: *PerUserRateLimiterDecorator, bucket: *UserBucket) void {
        const now_ms = agktime.milliTimestamp();
        const elapsed_ms = now_ms - bucket.last_update_ms;
        const elapsed_sec = @as(f64, @floatFromInt(elapsed_ms)) / 1000.0;

        // Add tokens based on elapsed time
        const tokens_to_add = elapsed_sec * self.config.rate;
        const capacity_f64 = @as(f64, @floatFromInt(self.config.capacity));
        bucket.tokens = @min(bucket.tokens + tokens_to_add, capacity_f64);
        bucket.last_update_ms = now_ms;
    }

    /// Acquire tokens for a user from their bucket
    fn acquireUserTokens(self: *PerUserRateLimiterDecorator, user_id: []const u8, tokens_needed: u32, wait: bool) !void {
        const tokens_needed_f64 = @as(f64, @floatFromInt(tokens_needed));

        self.mutex.lock();
        defer self.mutex.unlock();

        const bucket = try self.getUserBucket(user_id);
        self.refillUserTokens(bucket);

        if (bucket.tokens >= tokens_needed_f64) {
            // Sufficient tokens available
            bucket.tokens -= tokens_needed_f64;
            return;
        }

        if (!wait) {
            // Insufficient tokens and not waiting
            return PerUserRateLimitError.RateLimitExceeded;
        }

        // Calculate wait time for tokens
        const tokens_deficit = tokens_needed_f64 - bucket.tokens;
        const wait_time_sec = tokens_deficit / self.config.rate;
        const wait_time_ms = @as(u64, @intFromFloat(wait_time_sec * 1000.0));

        // Check if wait time exceeds max_wait_timeout
        if (self.config.max_wait_timeout_ms) |max_timeout| {
            if (wait_time_ms > max_timeout) {
                return PerUserRateLimitError.RateLimitExceeded;
            }
        }

        // Release lock before sleeping to allow other operations
        self.mutex.unlock();

        // Wait for tokens to refill
        agktime.sleep(wait_time_ms * std.time.ns_per_ms);

        // Re-acquire lock and try again
        self.mutex.lock();

        // Refill tokens based on actual elapsed time
        self.refillUserTokens(bucket);

        // Try to consume tokens
        // Use epsilon for floating point comparison
        const epsilon = 0.01;
        if (bucket.tokens >= tokens_needed_f64 - epsilon) {
            bucket.tokens -= tokens_needed_f64;
            self.metrics_data.total_wait_time_ms += wait_time_ms;
            return;
        }

        // Should not happen, but handle defensively
        return PerUserRateLimitError.RateLimitExceeded;
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *PerUserRateLimiterDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.name();
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *PerUserRateLimiterDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.capabilities(allocator);
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *PerUserRateLimiterDecorator = @ptrCast(@alignCast(ptr));

        // Track request
        self.mutex.lock();
        self.metrics_data.total_requests += 1;
        self.mutex.unlock();

        // Extract user ID from message
        const user_id = self.config.user_id_extractor(&message);

        // Acquire tokens (wait=true)
        self.acquireUserTokens(user_id, self.config.tokens_per_request, true) catch {
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
        const self: *PerUserRateLimiterDecorator = @ptrCast(@alignCast(ptr));

        // Get introspection from inner agent
        const inner_result = try self.inner_agent.introspect(allocator);

        // Add per-user rate limiter metrics to metadata
        const metrics_snapshot = self.metrics();

        var metadata = std.StringHashMap([]const u8).init(allocator);
        errdefer metadata.deinit();

        // Add metrics as metadata
        try metadata.put("total_requests", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.total_requests}));
        try metadata.put("allowed_requests", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.allowed_requests}));
        try metadata.put("rejected_requests", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.rejected_requests}));
        try metadata.put("total_wait_time_ms", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.total_wait_time_ms}));
        try metadata.put("active_users", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.active_users}));

        if (metrics_snapshot.avgWaitTime()) |avg| {
            try metadata.put("avg_wait_time_ms", try std.fmt.allocPrint(allocator, "{d:.2}", .{avg}));
        }
        if (metrics_snapshot.rejectionRate()) |rate| {
            try metadata.put("rejection_rate", try std.fmt.allocPrint(allocator, "{d:.2}%", .{rate}));
        }

        // Add configuration
        try metadata.put("rate", try std.fmt.allocPrint(allocator, "{d:.1}", .{self.config.rate}));
        try metadata.put("capacity", try std.fmt.allocPrint(allocator, "{d}", .{self.config.capacity}));
        try metadata.put("tokens_per_request", try std.fmt.allocPrint(allocator, "{d}", .{self.config.tokens_per_request}));

        // Merge with inner metadata
        var inner_iter = inner_result.metadata.iterator();
        while (inner_iter.next()) |entry| {
            if (!std.mem.startsWith(u8, entry.key_ptr.*, "per_user_rate_")) {
                try metadata.put(entry.key_ptr.*, entry.value_ptr.*);
            }
        }

        return IntrospectionResult{
            .agent_name = inner_result.agent_name,
            .capabilities = inner_result.capabilities,
            .metadata = metadata,
            .memory = inner_result.memory,
        };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *PerUserRateLimiterDecorator = @ptrCast(@alignCast(ptr));
        self.buckets.deinit();
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

test "PerUserRateLimiterConfig validation" {
    var config = PerUserRateLimiterConfig{};
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

test "PerUserRateLimiterMetrics calculations" {
    var metrics = PerUserRateLimiterMetrics{
        .total_requests = 10,
        .allowed_requests = 8,
        .rejected_requests = 2,
        .total_wait_time_ms = 5000,
        .active_users = 3,
    };

    // Average wait time
    const avg = metrics.avgWaitTime().?;
    try testing.expectApproxEqRel(@as(f64, 500.0), avg, 0.01);

    // Rejection rate
    const rejection_rate = metrics.rejectionRate().?;
    try testing.expectApproxEqRel(@as(f64, 20.0), rejection_rate, 0.01);
}

test "PerUserRateLimiterMetrics snapshot" {
    var metrics = PerUserRateLimiterMetrics{
        .total_requests = 5,
        .allowed_requests = 4,
        .rejected_requests = 1,
        .total_wait_time_ms = 1000,
        .active_users = 2,
    };

    const snapshot = metrics.snapshot();
    try testing.expectEqual(@as(u64, 5), snapshot.total_requests);
    try testing.expectEqual(@as(u64, 4), snapshot.allowed_requests);
    try testing.expectEqual(@as(u64, 1), snapshot.rejected_requests);
    try testing.expectEqual(@as(u64, 1000), snapshot.total_wait_time_ms);
    try testing.expectEqual(@as(usize, 2), snapshot.active_users);
}

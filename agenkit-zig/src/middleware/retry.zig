/// Retry middleware with exponential backoff
///
/// Wraps an agent and retries failed operations with exponential backoff.
/// Tracks comprehensive metrics for observability.
///
/// Example:
/// ```zig
/// const config = RetryConfig{
///     .max_retries = 3,
///     .initial_delay_ms = 100,
///     .max_delay_ms = 10000,
///     .multiplier = 2.0,
///     .should_retry = null,  // retry all errors
/// };
///
/// var retry = try RetryDecorator.init(allocator, base_agent, config);
/// defer retry.deinit();
///
/// const result = try retry.agent().process(message);
/// const metrics = retry.metrics();
/// ```
const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const StreamCallbacks = @import("../agent.zig").StreamCallbacks;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;

/// Configuration for retry behavior
pub const RetryConfig = struct {
    /// Maximum number of retry attempts (including initial attempt)
    /// Default: 3
    max_retries: u32 = 3,

    /// Initial delay duration in milliseconds
    /// Default: 100ms
    initial_delay_ms: u64 = 100,

    /// Maximum delay duration in milliseconds
    /// Default: 10000ms (10 seconds)
    max_delay_ms: u64 = 10000,

    /// Multiplier for exponential backoff
    /// Default: 2.0
    multiplier: f64 = 2.0,

    /// Optional predicate to determine if an error should trigger a retry
    /// If null, all errors trigger retries
    should_retry: ?*const fn (err: AgentError) bool = null,

    /// Validate configuration
    pub fn validate(self: RetryConfig) !void {
        if (self.max_retries < 1) {
            return error.InvalidConfig;
        }
        if (self.initial_delay_ms == 0) {
            return error.InvalidConfig;
        }
        if (self.max_delay_ms < self.initial_delay_ms) {
            return error.InvalidConfig;
        }
        if (self.multiplier <= 1.0) {
            return error.InvalidConfig;
        }
    }
};

/// Metrics tracked by retry middleware
pub const RetryMetrics = struct {
    /// Total number of requests (including retries)
    total_attempts: u64 = 0,

    /// Number of requests that succeeded on first try
    successful_first_attempt: u64 = 0,

    /// Number of requests that succeeded after retry
    successful_on_retry: u64 = 0,

    /// Number of requests that failed after all retries
    failed_after_retries: u64 = 0,

    /// Total number of retry attempts across all requests
    total_retries: u64 = 0,

    /// Create a snapshot of metrics
    pub fn snapshot(self: *const RetryMetrics) RetryMetrics {
        return RetryMetrics{
            .total_attempts = self.total_attempts,
            .successful_first_attempt = self.successful_first_attempt,
            .successful_on_retry = self.successful_on_retry,
            .failed_after_retries = self.failed_after_retries,
            .total_retries = self.total_retries,
        };
    }
};

/// Retry decorator - wraps an agent with retry logic
pub const RetryDecorator = struct {
    allocator: Allocator,
    inner_agent: Agent,
    config: RetryConfig,
    metrics_data: RetryMetrics,
    mutex: std.Thread.Mutex,

    pub fn init(allocator: Allocator, inner_agent: Agent, config: RetryConfig) !*RetryDecorator {
        // Validate configuration
        try config.validate();

        const self = try allocator.create(RetryDecorator);
        self.* = RetryDecorator{
            .allocator = allocator,
            .inner_agent = inner_agent,
            .config = config,
            .metrics_data = RetryMetrics{},
            .mutex = std.Thread.Mutex{},
        };
        return self;
    }

    pub fn agent(self: *RetryDecorator) Agent {
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
    pub fn metrics(self: *RetryDecorator) RetryMetrics {
        self.mutex.lock();
        defer self.mutex.unlock();
        return self.metrics_data.snapshot();
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *RetryDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.name();
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *RetryDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.capabilities(allocator);
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *RetryDecorator = @ptrCast(@alignCast(ptr));

        var last_error: ?AgentError = null;
        var backoff_ms = self.config.initial_delay_ms;

        var attempt: u32 = 1;
        while (attempt <= self.config.max_retries) : (attempt += 1) {
            // Track attempt
            self.mutex.lock();
            self.metrics_data.total_attempts += 1;
            self.mutex.unlock();

            // Try the operation
            const result = self.inner_agent.process(message);

            // Success case
            if (result) |res| {
                if (res.isOk()) {
                    // Track success
                    self.mutex.lock();
                    if (attempt == 1) {
                        self.metrics_data.successful_first_attempt += 1;
                    } else {
                        self.metrics_data.successful_on_retry += 1;
                    }
                    self.mutex.unlock();

                    return res;
                } else {
                    // Got an error wrapped in Result
                    last_error = res.unwrapErr();
                }
            } else |err| {
                // Got a direct error
                last_error = err;
            }

            // Check if we should retry this error
            if (self.config.should_retry) |should_retry_fn| {
                if (!should_retry_fn(last_error.?)) {
                    self.mutex.lock();
                    self.metrics_data.failed_after_retries += 1;
                    self.mutex.unlock();
                    return last_error.?;
                }
            }

            // Don't sleep after the last attempt
            if (attempt == self.config.max_retries) {
                break;
            }

            // Track retry
            self.mutex.lock();
            self.metrics_data.total_retries += 1;
            self.mutex.unlock();

            // Wait before retrying (exponential backoff)
            std.time.sleep(backoff_ms * std.time.ns_per_ms);

            // Calculate next backoff
            const next_backoff = @as(f64, @floatFromInt(backoff_ms)) * self.config.multiplier;
            backoff_ms = @min(@as(u64, @intFromFloat(next_backoff)), self.config.max_delay_ms);
        }

        // All attempts failed
        self.mutex.lock();
        self.metrics_data.failed_after_retries += 1;
        self.mutex.unlock();

        return if (last_error) |err| err else error.ProcessingFailed;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *RetryDecorator = @ptrCast(@alignCast(ptr));

        // Get introspection from inner agent
        const inner_result = try self.inner_agent.introspect(allocator);

        // Add retry metrics to metadata
        const metrics_snapshot = self.metrics();

        var metadata = std.StringHashMap([]const u8).init(allocator);
        errdefer metadata.deinit();

        // Add metrics as metadata
        try metadata.put("total_attempts", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.total_attempts}));
        try metadata.put("successful_first_attempt", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.successful_first_attempt}));
        try metadata.put("successful_on_retry", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.successful_on_retry}));
        try metadata.put("failed_after_retries", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.failed_after_retries}));
        try metadata.put("total_retries", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.total_retries}));
        try metadata.put("max_retries", try std.fmt.allocPrint(allocator, "{d}", .{self.config.max_retries}));
        try metadata.put("initial_delay_ms", try std.fmt.allocPrint(allocator, "{d}", .{self.config.initial_delay_ms}));
        try metadata.put("max_delay_ms", try std.fmt.allocPrint(allocator, "{d}", .{self.config.max_delay_ms}));

        // Merge with inner metadata
        var inner_iter = inner_result.metadata.iterator();
        while (inner_iter.next()) |entry| {
            // Inner metadata wins for non-metric keys
            if (!std.mem.startsWith(u8, entry.key_ptr.*, "retry_")) {
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
        const self: *RetryDecorator = @ptrCast(@alignCast(ptr));
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

test "RetryConfig validation" {
    var config = RetryConfig{};
    try config.validate();

    // Invalid: max_retries = 0
    config.max_retries = 0;
    try testing.expectError(error.InvalidConfig, config.validate());
    config.max_retries = 3;

    // Invalid: initial_backoff = 0
    config.initial_delay_ms = 0;
    try testing.expectError(error.InvalidConfig, config.validate());
    config.initial_delay_ms = 100;

    // Invalid: max_backoff < initial_backoff
    config.max_delay_ms = 50;
    try testing.expectError(error.InvalidConfig, config.validate());
    config.max_delay_ms = 10000;

    // Invalid: multiplier <= 1.0
    config.multiplier = 1.0;
    try testing.expectError(error.InvalidConfig, config.validate());
}

test "RetryMetrics snapshot" {
    var metrics = RetryMetrics{
        .total_attempts = 10,
        .successful_first_attempt = 5,
        .successful_on_retry = 3,
        .failed_after_retries = 2,
        .total_retries = 5,
    };

    const snapshot = metrics.snapshot();
    try testing.expectEqual(@as(u64, 10), snapshot.total_attempts);
    try testing.expectEqual(@as(u64, 5), snapshot.successful_first_attempt);
    try testing.expectEqual(@as(u64, 3), snapshot.successful_on_retry);
    try testing.expectEqual(@as(u64, 2), snapshot.failed_after_retries);
    try testing.expectEqual(@as(u64, 5), snapshot.total_retries);
}

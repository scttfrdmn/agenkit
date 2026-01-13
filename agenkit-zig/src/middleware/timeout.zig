/// Timeout middleware with method-specific timeout support
///
/// Wraps an agent and enforces timeouts on operations. Tracks comprehensive
/// metrics including duration statistics for observability.
///
/// Example:
/// ```zig
/// const config = TimeoutConfig{
///     .timeout_ms = 5000,  // 5 second default
///     .method_timeouts = &.{
///         .{ .name = "search", .timeout_ms = 10000 },  // 10s for search
///         .{ .name = "analyze", .timeout_ms = 30000 }, // 30s for analyze
///     },
/// };
///
/// var timeout_agent = try TimeoutDecorator.init(allocator, base_agent, config);
/// defer timeout_agent.deinit();
///
/// const result = try timeout_agent.agent().process(message);
/// const metrics = timeout_agent.metrics();
/// ```
const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const Result = @import("../agent.zig").Result;
const StreamCallbacks = @import("../agent.zig").StreamCallbacks;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;

/// Method-specific timeout configuration
pub const MethodTimeout = struct {
    name: []const u8,
    timeout_ms: u64,
};

/// Configuration for timeout behavior
pub const TimeoutConfig = struct {
    /// Default timeout duration in milliseconds
    /// Default: 30000ms (30 seconds)
    timeout_ms: u64 = 30000,

    /// Optional method-specific timeouts
    /// Lookup by message metadata["method"] or metadata["operation"]
    method_timeouts: ?[]const MethodTimeout = null,

    /// Validate configuration
    pub fn validate(self: TimeoutConfig) !void {
        if (self.timeout_ms == 0) {
            return error.InvalidConfig;
        }

        if (self.method_timeouts) |timeouts| {
            for (timeouts) |mt| {
                if (mt.timeout_ms == 0) {
                    return error.InvalidConfig;
                }
            }
        }
    }
};

/// Metrics tracked by timeout middleware
pub const TimeoutMetrics = struct {
    /// Total number of requests
    total_requests: u64 = 0,

    /// Number of successful requests
    successful_requests: u64 = 0,

    /// Number of timed out requests
    timed_out_requests: u64 = 0,

    /// Number of failed requests (non-timeout)
    failed_requests: u64 = 0,

    /// Minimum duration in milliseconds (null if no requests)
    min_duration_ms: ?u64 = null,

    /// Maximum duration in milliseconds (null if no requests)
    max_duration_ms: ?u64 = null,

    /// Total duration in milliseconds (for computing average)
    total_duration_ms: u64 = 0,

    /// Computed average duration in milliseconds
    pub fn avgDuration(self: *const TimeoutMetrics) ?f64 {
        if (self.total_requests == 0) return null;
        return @as(f64, @floatFromInt(self.total_duration_ms)) / @as(f64, @floatFromInt(self.total_requests));
    }

    /// Computed timeout rate (percentage)
    pub fn timeoutRate(self: *const TimeoutMetrics) ?f64 {
        if (self.total_requests == 0) return null;
        return (@as(f64, @floatFromInt(self.timed_out_requests)) / @as(f64, @floatFromInt(self.total_requests))) * 100.0;
    }

    /// Computed error rate (percentage)
    pub fn errorRate(self: *const TimeoutMetrics) ?f64 {
        if (self.total_requests == 0) return null;
        return (@as(f64, @floatFromInt(self.failed_requests + self.timed_out_requests)) / @as(f64, @floatFromInt(self.total_requests))) * 100.0;
    }

    /// Create a snapshot of metrics
    pub fn snapshot(self: *const TimeoutMetrics) TimeoutMetrics {
        return TimeoutMetrics{
            .total_requests = self.total_requests,
            .successful_requests = self.successful_requests,
            .timed_out_requests = self.timed_out_requests,
            .failed_requests = self.failed_requests,
            .min_duration_ms = self.min_duration_ms,
            .max_duration_ms = self.max_duration_ms,
            .total_duration_ms = self.total_duration_ms,
        };
    }
};

/// Timeout decorator - wraps an agent with timeout enforcement
pub const TimeoutDecorator = struct {
    allocator: Allocator,
    inner_agent: Agent,
    config: TimeoutConfig,
    metrics_data: TimeoutMetrics,
    mutex: std.Thread.Mutex,

    pub fn init(allocator: Allocator, inner_agent: Agent, config: TimeoutConfig) !*TimeoutDecorator {
        // Validate configuration
        try config.validate();

        const self = try allocator.create(TimeoutDecorator);
        self.* = TimeoutDecorator{
            .allocator = allocator,
            .inner_agent = inner_agent,
            .config = config,
            .metrics_data = TimeoutMetrics{},
            .mutex = std.Thread.Mutex{},
        };
        return self;
    }

    pub fn agent(self: *TimeoutDecorator) Agent {
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
    pub fn metrics(self: *TimeoutDecorator) TimeoutMetrics {
        self.mutex.lock();
        defer self.mutex.unlock();
        return self.metrics_data.snapshot();
    }

    /// Get timeout for a specific message (checks method/operation metadata)
    fn getTimeoutForMessage(self: *TimeoutDecorator, message: Message) u64 {
        // Check for method-specific timeout
        if (self.config.method_timeouts) |timeouts| {
            // Try to get method/operation from metadata
            const method_name = message.metadata.get("method") orelse message.metadata.get("operation");

            if (method_name) |name| {
                for (timeouts) |mt| {
                    if (std.mem.eql(u8, mt.name, name)) {
                        return mt.timeout_ms;
                    }
                }
            }
        }

        // Use default timeout
        return self.config.timeout_ms;
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *TimeoutDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.name();
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *TimeoutDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.capabilities(allocator);
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *TimeoutDecorator = @ptrCast(@alignCast(ptr));

        // Get timeout for this message
        const timeout_ms = self.getTimeoutForMessage(message);

        // Track request
        self.mutex.lock();
        self.metrics_data.total_requests += 1;
        self.mutex.unlock();

        // Record start time
        const start_time = std.time.milliTimestamp();
        const deadline = start_time + @as(i64, @intCast(timeout_ms));

        // Create a thread to execute the operation
        const ExecutionContext = struct {
            agent: Agent,
            msg: Message,
            result: ?Result = null,
            error_value: ?AgentError = null,
            completed: std.atomic.Value(bool),

            fn execute(ctx: *@This()) void {
                const res = ctx.agent.process(ctx.msg);
                if (res) |r| {
                    ctx.result = r;
                } else |err| {
                    ctx.error_value = err;
                }
                ctx.completed.store(true, .release);
            }
        };

        var context = ExecutionContext{
            .agent = self.inner_agent,
            .msg = message,
            .completed = std.atomic.Value(bool).init(false),
        };

        // Spawn thread for execution
        const thread = try std.Thread.spawn(.{}, ExecutionContext.execute, .{&context});
        defer thread.join();

        // Poll for completion or timeout
        while (!context.completed.load(.acquire)) {
            const now = std.time.milliTimestamp();
            if (now >= deadline) {
                // Timeout occurred
                const duration_ms = @as(u64, @intCast(now - start_time));

                self.mutex.lock();
                self.metrics_data.timed_out_requests += 1;
                self.updateDurationMetrics(duration_ms);
                self.mutex.unlock();

                return AgentError.Timeout;
            }

            // Sleep briefly to avoid busy waiting
            std.time.sleep(10 * std.time.ns_per_ms); // 10ms poll interval
        }

        // Calculate duration
        const end_time = std.time.milliTimestamp();
        const duration_ms = @as(u64, @intCast(end_time - start_time));

        // Check result
        if (context.error_value) |err| {
            // Operation failed with error
            self.mutex.lock();
            self.metrics_data.failed_requests += 1;
            self.updateDurationMetrics(duration_ms);
            self.mutex.unlock();

            return err;
        }

        if (context.result) |result| {
            // Success
            self.mutex.lock();
            self.metrics_data.successful_requests += 1;
            self.updateDurationMetrics(duration_ms);
            self.mutex.unlock();

            return result;
        }

        // Should not reach here
        return AgentError.ProcessingFailed;
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        const self: *TimeoutDecorator = @ptrCast(@alignCast(ptr));

        // Get timeout for this message
        const timeout_ms = self.getTimeoutForMessage(message);

        // Track request
        self.mutex.lock();
        self.metrics_data.total_requests += 1;
        self.mutex.unlock();

        // Record start time and deadline
        const start_time = std.time.milliTimestamp();
        const deadline = start_time + @as(i64, @intCast(timeout_ms));

        // Create context for wrapped callbacks
        const CallbackContext = struct {
            decorator: *TimeoutDecorator,
            original_callbacks: StreamCallbacks,
            deadline: i64,
            start_time: i64,
            timeout_ms: u64,
        };

        // Allocate context on heap for async callbacks
        const context = try self.allocator.create(CallbackContext);
        context.* = CallbackContext{
            .decorator = self,
            .original_callbacks = callbacks,
            .deadline = deadline,
            .start_time = start_time,
            .timeout_ms = timeout_ms,
        };

        // Create wrapped callbacks with timeout checking
        const wrapped_callbacks = StreamCallbacks{
            .ptr = context,
            .on_message_fn = struct {
                fn callback(ctx_ptr: *anyopaque, msg: Message) void {
                    const ctx: *CallbackContext = @ptrCast(@alignCast(ctx_ptr));
                    const now = std.time.milliTimestamp();

                    if (now >= ctx.deadline) {
                        // Timeout exceeded - call error callback
                        const duration_ms = @as(u64, @intCast(now - ctx.start_time));

                        ctx.decorator.mutex.lock();
                        ctx.decorator.metrics_data.timed_out_requests += 1;
                        ctx.decorator.updateDurationMetrics(duration_ms);
                        ctx.decorator.mutex.unlock();

                        ctx.original_callbacks.onError(AgentError.Timeout);
                        return;
                    }

                    // Forward message to original callback
                    ctx.original_callbacks.onMessage(msg);
                }
            }.callback,
            .on_error_fn = struct {
                fn callback(ctx_ptr: *anyopaque, err: AgentError) void {
                    const ctx: *CallbackContext = @ptrCast(@alignCast(ctx_ptr));
                    const now = std.time.milliTimestamp();
                    const duration_ms = @as(u64, @intCast(now - ctx.start_time));

                    ctx.decorator.mutex.lock();
                    ctx.decorator.metrics_data.failed_requests += 1;
                    ctx.decorator.updateDurationMetrics(duration_ms);
                    ctx.decorator.mutex.unlock();

                    // Forward error to original callback
                    ctx.original_callbacks.onError(err);

                    // Clean up context
                    ctx.decorator.allocator.destroy(ctx);
                }
            }.callback,
            .on_complete_fn = struct {
                fn callback(ctx_ptr: *anyopaque) void {
                    const ctx: *CallbackContext = @ptrCast(@alignCast(ctx_ptr));
                    const now = std.time.milliTimestamp();
                    const duration_ms = @as(u64, @intCast(now - ctx.start_time));

                    ctx.decorator.mutex.lock();
                    ctx.decorator.metrics_data.successful_requests += 1;
                    ctx.decorator.updateDurationMetrics(duration_ms);
                    ctx.decorator.mutex.unlock();

                    // Forward completion to original callback
                    ctx.original_callbacks.onComplete();

                    // Clean up context
                    ctx.decorator.allocator.destroy(ctx);
                }
            }.callback,
        };

        // Call inner agent's process_stream with wrapped callbacks
        return self.inner_agent.processStream(message, wrapped_callbacks);
    }

    fn updateDurationMetrics(self: *TimeoutDecorator, duration_ms: u64) void {
        // Update min/max
        if (self.metrics_data.min_duration_ms == null or duration_ms < self.metrics_data.min_duration_ms.?) {
            self.metrics_data.min_duration_ms = duration_ms;
        }
        if (self.metrics_data.max_duration_ms == null or duration_ms > self.metrics_data.max_duration_ms.?) {
            self.metrics_data.max_duration_ms = duration_ms;
        }

        // Update total
        self.metrics_data.total_duration_ms += duration_ms;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *TimeoutDecorator = @ptrCast(@alignCast(ptr));

        // Get introspection from inner agent
        const inner_result = try self.inner_agent.introspect(allocator);

        // Add timeout metrics to metadata
        const metrics_snapshot = self.metrics();

        var metadata = std.StringHashMap([]const u8).init(allocator);
        errdefer metadata.deinit();

        // Add metrics as metadata
        try metadata.put("total_requests", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.total_requests}));
        try metadata.put("successful_requests", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.successful_requests}));
        try metadata.put("timed_out_requests", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.timed_out_requests}));
        try metadata.put("failed_requests", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.failed_requests}));

        if (metrics_snapshot.min_duration_ms) |min| {
            try metadata.put("min_duration_ms", try std.fmt.allocPrint(allocator, "{d}", .{min}));
        }
        if (metrics_snapshot.max_duration_ms) |max| {
            try metadata.put("max_duration_ms", try std.fmt.allocPrint(allocator, "{d}", .{max}));
        }
        if (metrics_snapshot.avgDuration()) |avg| {
            try metadata.put("avg_duration_ms", try std.fmt.allocPrint(allocator, "{d:.2}", .{avg}));
        }
        if (metrics_snapshot.timeoutRate()) |rate| {
            try metadata.put("timeout_rate", try std.fmt.allocPrint(allocator, "{d:.2}%", .{rate}));
        }
        if (metrics_snapshot.errorRate()) |rate| {
            try metadata.put("error_rate", try std.fmt.allocPrint(allocator, "{d:.2}%", .{rate}));
        }

        try metadata.put("timeout_ms", try std.fmt.allocPrint(allocator, "{d}", .{self.config.timeout_ms}));

        // Merge with inner metadata
        var inner_iter = inner_result.metadata.iterator();
        while (inner_iter.next()) |entry| {
            if (!std.mem.startsWith(u8, entry.key_ptr.*, "timeout_")) {
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
        const self: *TimeoutDecorator = @ptrCast(@alignCast(ptr));
        // Don't deinit inner agent - caller manages it
        self.allocator.destroy(self);
    }
};

// Tests
const testing = std.testing;

test "TimeoutConfig validation" {
    var config = TimeoutConfig{};
    try config.validate();

    // Invalid: timeout = 0
    config.timeout_ms = 0;
    try testing.expectError(error.InvalidConfig, config.validate());
    config.timeout_ms = 5000;

    // Invalid: method timeout = 0
    const timeouts = [_]MethodTimeout{
        .{ .name = "test", .timeout_ms = 0 },
    };
    config.method_timeouts = &timeouts;
    try testing.expectError(error.InvalidConfig, config.validate());
}

test "TimeoutMetrics calculations" {
    var metrics = TimeoutMetrics{
        .total_requests = 10,
        .successful_requests = 7,
        .timed_out_requests = 2,
        .failed_requests = 1,
        .total_duration_ms = 5000,
    };

    // Average duration
    const avg = metrics.avgDuration().?;
    try testing.expectApproxEqRel(@as(f64, 500.0), avg, 0.01);

    // Timeout rate
    const timeout_rate = metrics.timeoutRate().?;
    try testing.expectApproxEqRel(@as(f64, 20.0), timeout_rate, 0.01);

    // Error rate (timeouts + failures)
    const error_rate = metrics.errorRate().?;
    try testing.expectApproxEqRel(@as(f64, 30.0), error_rate, 0.01);
}

test "TimeoutMetrics snapshot" {
    var metrics = TimeoutMetrics{
        .total_requests = 5,
        .successful_requests = 3,
        .timed_out_requests = 1,
        .failed_requests = 1,
        .min_duration_ms = 100,
        .max_duration_ms = 500,
        .total_duration_ms = 1500,
    };

    const snapshot = metrics.snapshot();
    try testing.expectEqual(@as(u64, 5), snapshot.total_requests);
    try testing.expectEqual(@as(u64, 3), snapshot.successful_requests);
    try testing.expectEqual(@as(u64, 1), snapshot.timed_out_requests);
    try testing.expectEqual(@as(u64, 100), snapshot.min_duration_ms.?);
    try testing.expectEqual(@as(u64, 500), snapshot.max_duration_ms.?);
}

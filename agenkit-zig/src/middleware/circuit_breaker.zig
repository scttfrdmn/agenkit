/// Circuit Breaker middleware with three-state FSM
///
/// Implements the circuit breaker pattern to prevent cascading failures.
/// Tracks failures and automatically opens the circuit when threshold is exceeded.
/// After a recovery timeout, transitions to half-open to test if the service recovered.
///
/// States:
/// - CLOSED: Normal operation, requests pass through
/// - OPEN: Circuit is open, requests are rejected immediately
/// - HALF_OPEN: Testing recovery, limited requests allowed
///
/// State transitions:
/// - CLOSED → OPEN: When failure count >= failure_threshold
/// - OPEN → HALF_OPEN: After recovery_timeout elapsed
/// - HALF_OPEN → CLOSED: When success count >= success_threshold
/// - HALF_OPEN → OPEN: When any failure occurs
///
/// Example:
/// ```zig
/// const config = CircuitBreakerConfig{
///     .failure_threshold = 5,
///     .success_threshold = 2,
///     .recovery_timeout_ms = 60000,  // 1 minute
/// };
///
/// var breaker = try CircuitBreakerDecorator.init(allocator, base_agent, config);
/// defer breaker.deinit();
///
/// const state = breaker.getState();
/// const result = try breaker.agent().process(message);
/// const metrics = breaker.metrics();
/// ```
const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;

/// Circuit breaker states
pub const CircuitState = enum {
    CLOSED,
    OPEN,
    HALF_OPEN,

    pub fn toString(self: CircuitState) []const u8 {
        return switch (self) {
            .CLOSED => "CLOSED",
            .OPEN => "OPEN",
            .HALF_OPEN => "HALF_OPEN",
        };
    }
};

/// Configuration for circuit breaker behavior
pub const CircuitBreakerConfig = struct {
    /// Number of failures before opening the circuit
    /// Default: 5
    failure_threshold: u32 = 5,

    /// Number of successes in half-open state before closing
    /// Default: 2
    success_threshold: u32 = 2,

    /// Time in milliseconds to wait before attempting recovery (OPEN → HALF_OPEN)
    /// Default: 60000ms (1 minute)
    recovery_timeout_ms: u64 = 60000,

    /// Optional per-request timeout in milliseconds
    /// If null, no timeout is enforced
    request_timeout_ms: ?u64 = null,

    /// Validate configuration
    pub fn validate(self: CircuitBreakerConfig) !void {
        if (self.failure_threshold == 0) {
            return error.InvalidConfig;
        }
        if (self.success_threshold == 0) {
            return error.InvalidConfig;
        }
        if (self.recovery_timeout_ms == 0) {
            return error.InvalidConfig;
        }
    }
};

/// Metrics tracked by circuit breaker middleware
pub const CircuitBreakerMetrics = struct {
    /// Total number of requests
    total_requests: u64 = 0,

    /// Number of successful requests
    successful_requests: u64 = 0,

    /// Number of failed requests
    failed_requests: u64 = 0,

    /// Number of rejected requests (circuit open)
    rejected_requests: u64 = 0,

    /// Map of state transition counts
    state_transitions: std.StringHashMap(u64),

    /// Timestamp of last state change (milliseconds since epoch)
    last_state_change_ms: ?i64 = null,

    /// Current circuit state
    current_state: CircuitState = .CLOSED,

    pub fn init(allocator: Allocator) CircuitBreakerMetrics {
        return CircuitBreakerMetrics{
            .state_transitions = std.StringHashMap(u64).init(allocator),
        };
    }

    pub fn deinit(self: *CircuitBreakerMetrics) void {
        // Free all keys before deinitializing the hashmap
        var iter = self.state_transitions.keyIterator();
        while (iter.next()) |key| {
            self.state_transitions.allocator.free(key.*);
        }
        self.state_transitions.deinit();
    }

    /// Increment state transition count
    pub fn recordTransition(self: *CircuitBreakerMetrics, from: CircuitState, to: CircuitState, allocator: Allocator) !void {
        const key = try std.fmt.allocPrint(allocator, "{s}_to_{s}", .{ from.toString(), to.toString() });

        // Check if key already exists
        if (self.state_transitions.getKey(key)) |existing_key| {
            // Key exists, use existing key and free our temporary one
            const count = self.state_transitions.get(existing_key).?;
            try self.state_transitions.put(existing_key, count + 1);
            allocator.free(key);
        } else {
            // Key doesn't exist, store it (don't free - hashmap will own it)
            try self.state_transitions.put(key, 1);
        }
    }

    /// Create a snapshot of metrics (allocates new hash map)
    pub fn snapshot(self: *const CircuitBreakerMetrics, allocator: Allocator) !CircuitBreakerMetrics {
        var new_transitions = std.StringHashMap(u64).init(allocator);
        var iter = self.state_transitions.iterator();
        while (iter.next()) |entry| {
            const key_copy = try allocator.dupe(u8, entry.key_ptr.*);
            try new_transitions.put(key_copy, entry.value_ptr.*);
        }

        return CircuitBreakerMetrics{
            .total_requests = self.total_requests,
            .successful_requests = self.successful_requests,
            .failed_requests = self.failed_requests,
            .rejected_requests = self.rejected_requests,
            .state_transitions = new_transitions,
            .last_state_change_ms = self.last_state_change_ms,
            .current_state = self.current_state,
        };
    }
};

/// Circuit breaker error
pub const CircuitBreakerError = error{
    CircuitOpen,
};

/// Circuit breaker decorator - wraps an agent with circuit breaker logic
pub const CircuitBreakerDecorator = struct {
    allocator: Allocator,
    inner_agent: Agent,
    config: CircuitBreakerConfig,
    metrics_data: CircuitBreakerMetrics,
    state: CircuitState,
    failure_count: u32,
    success_count: u32,
    last_failure_time_ms: ?i64,
    mutex: std.Thread.Mutex,

    pub fn init(allocator: Allocator, inner_agent: Agent, config: CircuitBreakerConfig) !*CircuitBreakerDecorator {
        // Validate configuration
        try config.validate();

        const self = try allocator.create(CircuitBreakerDecorator);
        self.* = CircuitBreakerDecorator{
            .allocator = allocator,
            .inner_agent = inner_agent,
            .config = config,
            .metrics_data = CircuitBreakerMetrics.init(allocator),
            .state = .CLOSED,
            .failure_count = 0,
            .success_count = 0,
            .last_failure_time_ms = null,
            .mutex = std.Thread.Mutex{},
        };
        return self;
    }

    pub fn agent(self: *CircuitBreakerDecorator) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
            },
        };
    }

    /// Get current circuit state (thread-safe)
    pub fn getState(self: *CircuitBreakerDecorator) CircuitState {
        self.mutex.lock();
        defer self.mutex.unlock();
        return self.state;
    }

    /// Get current metrics (thread-safe, allocates new hash map)
    pub fn metrics(self: *CircuitBreakerDecorator) !CircuitBreakerMetrics {
        self.mutex.lock();
        defer self.mutex.unlock();
        return try self.metrics_data.snapshot(self.allocator);
    }

    /// Check if circuit should transition to HALF_OPEN
    fn shouldAttemptRecovery(self: *CircuitBreakerDecorator) bool {
        if (self.state != .OPEN) return false;
        if (self.last_failure_time_ms == null) return false;

        const now = std.time.milliTimestamp();
        const elapsed = now - self.last_failure_time_ms.?;
        return elapsed >= @as(i64, @intCast(self.config.recovery_timeout_ms));
    }

    /// Transition circuit state
    fn transitionState(self: *CircuitBreakerDecorator, new_state: CircuitState) !void {
        const old_state = self.state;
        if (old_state == new_state) return;

        self.state = new_state;
        self.metrics_data.current_state = new_state;
        self.metrics_data.last_state_change_ms = std.time.milliTimestamp();

        // Record transition
        try self.metrics_data.recordTransition(old_state, new_state, self.allocator);

        // Reset counters on transition
        if (new_state == .HALF_OPEN) {
            self.success_count = 0;
            self.failure_count = 0;
        } else if (new_state == .CLOSED) {
            self.failure_count = 0;
        }
    }

    /// Record successful request
    fn recordSuccess(self: *CircuitBreakerDecorator) !void {
        self.metrics_data.successful_requests += 1;

        if (self.state == .HALF_OPEN) {
            self.success_count += 1;
            if (self.success_count >= self.config.success_threshold) {
                try self.transitionState(.CLOSED);
            }
        } else if (self.state == .CLOSED) {
            // Reset failure count on success
            self.failure_count = 0;
        }
    }

    /// Record failed request
    fn recordFailure(self: *CircuitBreakerDecorator) !void {
        self.metrics_data.failed_requests += 1;
        self.last_failure_time_ms = std.time.milliTimestamp();

        if (self.state == .HALF_OPEN) {
            // Any failure in HALF_OPEN immediately opens circuit
            try self.transitionState(.OPEN);
        } else if (self.state == .CLOSED) {
            self.failure_count += 1;
            if (self.failure_count >= self.config.failure_threshold) {
                try self.transitionState(.OPEN);
            }
        }
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *CircuitBreakerDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.name();
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *CircuitBreakerDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.capabilities(allocator);
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *CircuitBreakerDecorator = @ptrCast(@alignCast(ptr));

        self.mutex.lock();
        defer self.mutex.unlock();

        // Track request
        self.metrics_data.total_requests += 1;

        // Check if we should attempt recovery
        if (self.shouldAttemptRecovery()) {
            try self.transitionState(.HALF_OPEN);
        }

        // Check circuit state
        if (self.state == .OPEN) {
            self.metrics_data.rejected_requests += 1;
            return AgentError.Cancelled; // Circuit open, reject request
        }

        // Release lock before calling inner agent
        self.mutex.unlock();

        // Execute request (with optional timeout)
        const result = if (self.config.request_timeout_ms) |timeout_ms| blk: {
            // TODO: Implement request timeout (similar to TimeoutDecorator)
            // For now, just call inner agent
            _ = timeout_ms;
            break :blk self.inner_agent.process(message);
        } else blk: {
            break :blk self.inner_agent.process(message);
        };

        // Re-acquire lock to update state
        self.mutex.lock();

        // Handle result
        if (result) |res| {
            if (res.isOk()) {
                try self.recordSuccess();
                return res;
            } else {
                try self.recordFailure();
                return res;
            }
        } else |err| {
            try self.recordFailure();
            return err;
        }
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *CircuitBreakerDecorator = @ptrCast(@alignCast(ptr));

        // Get introspection from inner agent
        const inner_result = try self.inner_agent.introspect(allocator);

        // Add circuit breaker metrics to metadata
        const metrics_snapshot = try self.metrics();
        defer metrics_snapshot.state_transitions.deinit();

        var metadata = std.StringHashMap([]const u8).init(allocator);
        errdefer metadata.deinit();

        // Add metrics as metadata
        try metadata.put("total_requests", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.total_requests}));
        try metadata.put("successful_requests", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.successful_requests}));
        try metadata.put("failed_requests", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.failed_requests}));
        try metadata.put("rejected_requests", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.rejected_requests}));
        try metadata.put("current_state", try std.fmt.allocPrint(allocator, "{s}", .{metrics_snapshot.current_state.toString()}));

        if (metrics_snapshot.last_state_change_ms) |timestamp| {
            try metadata.put("last_state_change_ms", try std.fmt.allocPrint(allocator, "{d}", .{timestamp}));
        }

        // Add state transitions
        var iter = metrics_snapshot.state_transitions.iterator();
        while (iter.next()) |entry| {
            const key = try std.fmt.allocPrint(allocator, "transition_{s}", .{entry.key_ptr.*});
            try metadata.put(key, try std.fmt.allocPrint(allocator, "{d}", .{entry.value_ptr.*}));
        }

        // Add configuration
        try metadata.put("failure_threshold", try std.fmt.allocPrint(allocator, "{d}", .{self.config.failure_threshold}));
        try metadata.put("success_threshold", try std.fmt.allocPrint(allocator, "{d}", .{self.config.success_threshold}));
        try metadata.put("recovery_timeout_ms", try std.fmt.allocPrint(allocator, "{d}", .{self.config.recovery_timeout_ms}));

        // Merge with inner metadata
        var inner_iter = inner_result.metadata.iterator();
        while (inner_iter.next()) |entry| {
            if (!std.mem.startsWith(u8, entry.key_ptr.*, "circuit_")) {
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
        const self: *CircuitBreakerDecorator = @ptrCast(@alignCast(ptr));
        self.metrics_data.deinit();
        // Don't deinit inner agent - caller manages it
        self.allocator.destroy(self);
    }
};

// Tests
const testing = std.testing;

test "CircuitBreakerConfig validation" {
    var config = CircuitBreakerConfig{};
    try config.validate();

    // Invalid: failure_threshold = 0
    config.failure_threshold = 0;
    try testing.expectError(error.InvalidConfig, config.validate());
    config.failure_threshold = 5;

    // Invalid: success_threshold = 0
    config.success_threshold = 0;
    try testing.expectError(error.InvalidConfig, config.validate());
    config.success_threshold = 2;

    // Invalid: recovery_timeout = 0
    config.recovery_timeout_ms = 0;
    try testing.expectError(error.InvalidConfig, config.validate());
}

test "CircuitState toString" {
    try testing.expectEqualStrings("CLOSED", CircuitState.CLOSED.toString());
    try testing.expectEqualStrings("OPEN", CircuitState.OPEN.toString());
    try testing.expectEqualStrings("HALF_OPEN", CircuitState.HALF_OPEN.toString());
}

test "CircuitBreakerMetrics transitions" {
    const allocator = testing.allocator;
    var metrics = CircuitBreakerMetrics.init(allocator);
    defer metrics.deinit();

    // Record transitions
    try metrics.recordTransition(.CLOSED, .OPEN, allocator);
    try metrics.recordTransition(.CLOSED, .OPEN, allocator);
    try metrics.recordTransition(.OPEN, .HALF_OPEN, allocator);

    // Verify counts
    const closed_to_open = metrics.state_transitions.get("CLOSED_to_OPEN").?;
    try testing.expectEqual(@as(u64, 2), closed_to_open);

    const open_to_half = metrics.state_transitions.get("OPEN_to_HALF_OPEN").?;
    try testing.expectEqual(@as(u64, 1), open_to_half);
}

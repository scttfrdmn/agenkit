/// Budget limiting middleware for cost control
///
/// Enforces budget limits at both session and global levels:
/// - Per-session budgets: Limit spending for individual users/sessions
/// - Global budgets: Limit total spending across all sessions
/// - Pre-request validation: Check budget before making LLM calls
/// - Soft/hard limits: Warn on soft limits, reject on hard limits
///
/// This is useful for:
/// - Cost control and spend management
/// - Preventing runaway costs from bugs or abuse
/// - Fair resource allocation across users
/// - Compliance with budget constraints
///
/// Example:
/// ```zig
/// const config = BudgetLimiterConfig{
///     .per_session_limit = 10.0,  // $10 per session
///     .global_limit = 1000.0,      // $1000 total
///     .soft_limit_ratio = 0.8,     // Warn at 80%
/// };
///
/// var tracker = try CostTracker.init(allocator, null);
/// defer tracker.deinit();
///
/// var limiter = try BudgetLimiterDecorator.init(allocator, base_agent, &tracker, config);
/// defer limiter.deinit();
///
/// const result = try limiter.agent().process(message);
/// ```
const std = @import("std");
const agksync = @import("../../sync_compat.zig");
const Agent = @import("../../agent.zig").Agent;
const AgentError = @import("../../agent.zig").AgentError;
const StreamCallbacks = @import("../../agent.zig").StreamCallbacks;
const Result = @import("../../agent.zig").Result;
const Message = @import("../../message.zig").Message;
const IntrospectionResult = @import("../../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../../introspection.zig").createDefaultIntrospectionResult;
const CostTracker = @import("tracker.zig").CostTracker;
const Allocator = std.mem.Allocator;

/// Budget limiter error
pub const BudgetError = error{
    SessionBudgetExceeded,
    GlobalBudgetExceeded,
};

/// Configuration for budget limiter behavior
pub const BudgetLimiterConfig = struct {
    /// Maximum cost per session in dollars (null = no limit)
    /// Default: null (no limit)
    per_session_limit: ?f64 = null,

    /// Maximum global cost across all sessions in dollars (null = no limit)
    /// Default: null (no limit)
    global_limit: ?f64 = null,

    /// Soft limit ratio (0.0-1.0) - warn when budget reaches this percentage
    /// Default: 0.8 (warn at 80%)
    soft_limit_ratio: f64 = 0.8,

    /// Whether to allow requests that would exceed the budget
    /// If false, rejects requests that would push over limit
    /// If true, allows requests but logs warnings
    /// Default: false (reject over-budget requests)
    allow_overage: bool = false,

    /// Validate configuration
    pub fn validate(self: BudgetLimiterConfig) !void {
        if (self.per_session_limit) |limit| {
            if (limit <= 0.0) {
                return error.InvalidConfig;
            }
        }
        if (self.global_limit) |limit| {
            if (limit <= 0.0) {
                return error.InvalidConfig;
            }
        }
        if (self.soft_limit_ratio < 0.0 or self.soft_limit_ratio > 1.0) {
            return error.InvalidConfig;
        }
    }
};

/// Metrics tracked by budget limiter middleware
pub const BudgetLimiterMetrics = struct {
    /// Total number of requests
    total_requests: u64 = 0,

    /// Number of allowed requests
    allowed_requests: u64 = 0,

    /// Number of rejected requests
    rejected_requests: u64 = 0,

    /// Number of soft limit warnings
    soft_limit_warnings: u64 = 0,

    /// Current global spend
    global_spend: f64 = 0.0,

    /// Rejection rate (percentage)
    pub fn rejectionRate(self: *const BudgetLimiterMetrics) ?f64 {
        if (self.total_requests == 0) return null;
        return (@as(f64, @floatFromInt(self.rejected_requests)) / @as(f64, @floatFromInt(self.total_requests))) * 100.0;
    }

    /// Create a snapshot of metrics
    pub fn snapshot(self: *const BudgetLimiterMetrics) BudgetLimiterMetrics {
        return BudgetLimiterMetrics{
            .total_requests = self.total_requests,
            .allowed_requests = self.allowed_requests,
            .rejected_requests = self.rejected_requests,
            .soft_limit_warnings = self.soft_limit_warnings,
            .global_spend = self.global_spend,
        };
    }
};

/// Budget limiter decorator - wraps an agent with budget enforcement
pub const BudgetLimiterDecorator = struct {
    allocator: Allocator,
    inner_agent: Agent,
    cost_tracker: *CostTracker,
    config: BudgetLimiterConfig,
    metrics_data: BudgetLimiterMetrics,
    mutex: agksync.Mutex,

    pub fn init(
        allocator: Allocator,
        inner_agent: Agent,
        cost_tracker: *CostTracker,
        config: BudgetLimiterConfig,
    ) !*BudgetLimiterDecorator {
        // Validate configuration
        try config.validate();

        const self = try allocator.create(BudgetLimiterDecorator);
        self.* = BudgetLimiterDecorator{
            .allocator = allocator,
            .inner_agent = inner_agent,
            .cost_tracker = cost_tracker,
            .config = config,
            .metrics_data = BudgetLimiterMetrics{},
            .mutex = agksync.Mutex{},
        };
        return self;
    }

    pub fn agent(self: *BudgetLimiterDecorator) Agent {
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
    pub fn metrics(self: *BudgetLimiterDecorator) BudgetLimiterMetrics {
        self.mutex.lock();
        defer self.mutex.unlock();
        return self.metrics_data.snapshot();
    }

    /// Check if request would exceed budget
    fn checkBudget(self: *BudgetLimiterDecorator, session_id: []const u8) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        self.metrics_data.total_requests += 1;

        // Check global budget
        if (self.config.global_limit) |limit| {
            const global_cost = try self.cost_tracker.getTotalCost(null, null);
            self.metrics_data.global_spend = global_cost;

            // Check hard limit
            if (global_cost >= limit) {
                self.metrics_data.rejected_requests += 1;
                std.log.err("Global budget exceeded: ${d:.2} >= ${d:.2}", .{ global_cost, limit });
                if (!self.config.allow_overage) {
                    return BudgetError.GlobalBudgetExceeded;
                }
            }

            // Check soft limit
            const soft_limit = limit * self.config.soft_limit_ratio;
            if (global_cost >= soft_limit and global_cost < limit) {
                self.metrics_data.soft_limit_warnings += 1;
                std.log.warn("Global budget approaching limit: ${d:.2} / ${d:.2} ({d:.1}%)", .{
                    global_cost,
                    limit,
                    (global_cost / limit) * 100.0,
                });
            }
        }

        // Check per-session budget
        if (self.config.per_session_limit) |limit| {
            const session_cost = try self.cost_tracker.getSessionCost(session_id, null, null);

            // Check hard limit
            if (session_cost >= limit) {
                self.metrics_data.rejected_requests += 1;
                std.log.err("Session budget exceeded: ${d:.2} >= ${d:.2} (session: {s})", .{
                    session_cost,
                    limit,
                    session_id,
                });
                if (!self.config.allow_overage) {
                    return BudgetError.SessionBudgetExceeded;
                }
            }

            // Check soft limit
            const soft_limit = limit * self.config.soft_limit_ratio;
            if (session_cost >= soft_limit and session_cost < limit) {
                self.metrics_data.soft_limit_warnings += 1;
                std.log.warn("Session budget approaching limit: ${d:.2} / ${d:.2} ({d:.1}%) (session: {s})", .{
                    session_cost,
                    limit,
                    (session_cost / limit) * 100.0,
                    session_id,
                });
            }
        }

        // Budget check passed
        self.metrics_data.allowed_requests += 1;
    }

    // VTable implementations
    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *BudgetLimiterDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.name();
    }

    fn capabilitiesImpl(ptr: *anyopaque) []const []const u8 {
        const self: *BudgetLimiterDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.capabilities();
    }

    fn processImpl(ptr: *anyopaque, message: Message) anyerror!Result {
        const self: *BudgetLimiterDecorator = @ptrCast(@alignCast(ptr));

        // Extract session_id from message metadata
        const session_id = if (message.metadata) |meta|
            switch (meta) {
                .object => |obj| blk: {
                    if (obj.get("session_id")) |val| {
                        switch (val) {
                            .string => |s| break :blk s,
                            else => break :blk "default",
                        }
                    } else {
                        break :blk "default";
                    }
                },
                else => "default",
            }
        else
            "default";

        // Check budget before processing
        try self.checkBudget(session_id);

        // Process the message
        return self.inner_agent.process(message);
    }

    fn processStreamImpl(
        ptr: *anyopaque,
        message: Message,
        callbacks: StreamCallbacks,
    ) anyerror!Result {
        const self: *BudgetLimiterDecorator = @ptrCast(@alignCast(ptr));

        // Extract session_id from message metadata
        const session_id = if (message.metadata) |meta|
            switch (meta) {
                .object => |obj| blk: {
                    if (obj.get("session_id")) |val| {
                        switch (val) {
                            .string => |s| break :blk s,
                            else => break :blk "default",
                        }
                    } else {
                        break :blk "default";
                    }
                },
                else => "default",
            }
        else
            "default";

        // Check budget before processing
        try self.checkBudget(session_id);

        // Process the message with streaming
        return self.inner_agent.processStream(message, callbacks);
    }

    fn introspectImpl(ptr: *anyopaque) anyerror!IntrospectionResult {
        const self: *BudgetLimiterDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.introspect();
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *BudgetLimiterDecorator = @ptrCast(@alignCast(ptr));
        self.inner_agent.deinit();
    }

    pub fn deinit(self: *BudgetLimiterDecorator) void {
        self.allocator.destroy(self);
    }
};

// Tests
const testing = std.testing;
const ModelPricing = @import("models.zig").ModelPricing;
const Cost = @import("models.zig").Cost;

test "BudgetLimiterConfig validation" {
    const valid_config = BudgetLimiterConfig{
        .per_session_limit = 10.0,
        .global_limit = 100.0,
        .soft_limit_ratio = 0.8,
    };
    try valid_config.validate();

    // Invalid per_session_limit
    const invalid_session = BudgetLimiterConfig{
        .per_session_limit = -1.0,
    };
    try testing.expectError(error.InvalidConfig, invalid_session.validate());

    // Invalid global_limit
    const invalid_global = BudgetLimiterConfig{
        .global_limit = 0.0,
    };
    try testing.expectError(error.InvalidConfig, invalid_global.validate());

    // Invalid soft_limit_ratio
    const invalid_ratio = BudgetLimiterConfig{
        .soft_limit_ratio = 1.5,
    };
    try testing.expectError(error.InvalidConfig, invalid_ratio.validate());
}

test "BudgetLimiterMetrics snapshot" {
    var metrics = BudgetLimiterMetrics{
        .total_requests = 100,
        .allowed_requests = 80,
        .rejected_requests = 20,
        .soft_limit_warnings = 10,
        .global_spend = 150.50,
    };

    const snap = metrics.snapshot();
    try testing.expectEqual(@as(u64, 100), snap.total_requests);
    try testing.expectEqual(@as(u64, 80), snap.allowed_requests);
    try testing.expectEqual(@as(u64, 20), snap.rejected_requests);
    try testing.expectEqual(@as(u64, 10), snap.soft_limit_warnings);
    try testing.expectEqual(@as(f64, 150.50), snap.global_spend);
}

test "BudgetLimiterMetrics rejectionRate" {
    var metrics = BudgetLimiterMetrics{
        .total_requests = 100,
        .rejected_requests = 20,
    };

    const rate = metrics.rejectionRate().?;
    try testing.expectApproxEqAbs(@as(f64, 20.0), rate, 0.01);

    // No requests
    var empty_metrics = BudgetLimiterMetrics{};
    try testing.expectEqual(@as(?f64, null), empty_metrics.rejectionRate());
}

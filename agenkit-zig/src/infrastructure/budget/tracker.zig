/// Cost tracking and storage for LLM usage.
///
/// Provides thread-safe cost recording and querying capabilities.
///
/// Components:
///   - Storage: Interface for cost storage backends
///   - InMemoryStorage: In-memory cost storage implementation
///   - CostTracker: High-level cost tracking API
///
/// Example:
///   var tracker = CostTracker.init(allocator, null);
///   defer tracker.deinit();
///
///   const cost = try tracker.recordCost(
///       "session-1", "assistant", "claude-sonnet-4",
///       1000, 500, 0, null
///   );
///   defer allocator.destroy(cost);
///
///   const total = try tracker.getSessionCost("session-1", null, null);
const std = @import("std");
const Allocator = std.mem.Allocator;
const models = @import("models.zig");
const Cost = models.Cost;
const ModelPricing = models.ModelPricing;

/// Storage interface for cost records.
///
/// Implementations:
///   - InMemoryStorage: Fast, volatile storage
///   - FileStorage: Persistent JSON storage (future)
///   - RedisStorage: Distributed storage (future)
pub const Storage = struct {
    ptr: *anyopaque,
    vtable: *const VTable,

    pub const VTable = struct {
        store: *const fn (ptr: *anyopaque, cost: *const Cost) anyerror!void,
        query: *const fn (
            ptr: *anyopaque,
            session_id: ?[]const u8,
            agent_name: ?[]const u8,
            start_time: ?i64,
            end_time: ?i64,
        ) anyerror![]const *Cost,
        deinit: *const fn (ptr: *anyopaque) void,
    };

    pub fn store(self: Storage, cost: *const Cost) !void {
        return self.vtable.store(self.ptr, cost);
    }

    pub fn query(
        self: Storage,
        session_id: ?[]const u8,
        agent_name: ?[]const u8,
        start_time: ?i64,
        end_time: ?i64,
    ) ![]const *Cost {
        return self.vtable.query(self.ptr, session_id, agent_name, start_time, end_time);
    }

    pub fn deinit(self: Storage) void {
        return self.vtable.deinit(self.ptr);
    }
};

/// InMemoryStorage provides in-memory storage for cost records.
///
/// Good for:
///   - Testing
///   - Development
///   - Short-lived sessions
///
/// Not suitable for:
///   - Production (no persistence)
///   - Long-running agents (lost on restart)
///   - Distributed systems
///
/// Example:
///   var storage = InMemoryStorage.init(allocator);
///   defer storage.deinit();
///   try storage.store(&cost);
pub const InMemoryStorage = struct {
    allocator: Allocator,
    mutex: std.Thread.Mutex,
    costs: std.ArrayList(*Cost),

    pub fn init(allocator: Allocator) InMemoryStorage {
        return .{
            .allocator = allocator,
            .mutex = .{},
            .costs = .{},
        };
    }

    pub fn deinit(self: *InMemoryStorage) void {
        // Free all stored costs
        for (self.costs.items) |cost| {
            cost.deinit();
            self.allocator.destroy(cost);
        }
        self.costs.deinit(self.allocator);
    }

    pub fn storage(self: *InMemoryStorage) Storage {
        return .{
            .ptr = self,
            .vtable = &.{
                .store = storeImpl,
                .query = queryImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn storeImpl(ptr: *anyopaque, cost: *const Cost) !void {
        const self: *InMemoryStorage = @ptrCast(@alignCast(ptr));
        return self.store(cost);
    }

    fn queryImpl(
        ptr: *anyopaque,
        session_id: ?[]const u8,
        agent_name: ?[]const u8,
        start_time: ?i64,
        end_time: ?i64,
    ) ![]const *Cost {
        const self: *InMemoryStorage = @ptrCast(@alignCast(ptr));
        return self.query(session_id, agent_name, start_time, end_time);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *InMemoryStorage = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    pub fn store(self: *InMemoryStorage, cost: *const Cost) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        // Create a deep copy of the cost to store
        const cost_copy = try self.allocator.create(Cost);
        cost_copy.* = Cost{
            .allocator = self.allocator,
            .session_id = try self.allocator.dupe(u8, cost.session_id),
            .agent_name = try self.allocator.dupe(u8, cost.agent_name),
            .model = try self.allocator.dupe(u8, cost.model),
            .input_tokens = cost.input_tokens,
            .output_tokens = cost.output_tokens,
            .thinking_tokens = cost.thinking_tokens,
            .input_cost = cost.input_cost,
            .output_cost = cost.output_cost,
            .thinking_cost = cost.thinking_cost,
            .total_cost = cost.total_cost,
            .timestamp = cost.timestamp,
            .metadata = std.json.Value{ .null = {} }, // TODO: Implement deep copy of metadata
        };

        try self.costs.append(self.allocator, cost_copy);
    }

    pub fn query(
        self: *InMemoryStorage,
        session_id: ?[]const u8,
        agent_name: ?[]const u8,
        start_time: ?i64,
        end_time: ?i64,
    ) ![]const *Cost {
        self.mutex.lock();
        defer self.mutex.unlock();

        var results: std.ArrayList(*Cost) = .{};

        for (self.costs.items) |cost| {
            // Filter by session_id
            if (session_id) |sid| {
                if (!std.mem.eql(u8, cost.session_id, sid)) {
                    continue;
                }
            }

            // Filter by agent_name
            if (agent_name) |aname| {
                if (!std.mem.eql(u8, cost.agent_name, aname)) {
                    continue;
                }
            }

            // Filter by time range
            if (start_time) |st| {
                if (cost.timestamp < st) {
                    continue;
                }
            }
            if (end_time) |et| {
                if (cost.timestamp > et) {
                    continue;
                }
            }

            try results.append(self.allocator, cost);
        }

        return try results.toOwnedSlice(self.allocator);
    }
};

/// CostTracker tracks LLM costs per session, agent, and globally.
///
/// Features:
///   - Per-session cost tracking
///   - Per-agent cost tracking
///   - Global cost tracking
///   - Cost breakdown by model
///   - Time-series cost data
///   - Thread-safe operations
///
/// Example:
///   var tracker = CostTracker.init(allocator, null);
///   defer tracker.deinit();
///
///   const cost = try tracker.recordCost(
///       "user-123", "assistant", "claude-sonnet-4",
///       1000, 500, 0, null
///   );
///   defer allocator.destroy(cost);
///
///   const total = try tracker.getSessionCost("user-123", null, null);
///   std.debug.print("Session cost: ${d:.2}\n", .{total});
pub const CostTracker = struct {
    allocator: Allocator,
    storage: Storage,
    model_pricing: ModelPricing,
    owns_storage: bool,
    owned_storage_ptr: ?*InMemoryStorage,

    /// Create a new cost tracker.
    ///
    /// Args:
    ///   allocator: Memory allocator
    ///   storage: Storage backend (uses in-memory if null)
    ///
    /// Example:
    ///   var tracker = CostTracker.init(allocator, null); // Uses in-memory storage
    ///   defer tracker.deinit();
    pub fn init(allocator: Allocator, storage: ?Storage) !CostTracker {
        const owns_storage = storage == null;
        var owned_ptr: ?*InMemoryStorage = null;
        const actual_storage = storage orelse blk: {
            const mem_storage = try allocator.create(InMemoryStorage);
            mem_storage.* = InMemoryStorage.init(allocator);
            owned_ptr = mem_storage;
            break :blk mem_storage.storage();
        };

        return .{
            .allocator = allocator,
            .storage = actual_storage,
            .model_pricing = try ModelPricing.init(allocator),
            .owns_storage = owns_storage,
            .owned_storage_ptr = owned_ptr,
        };
    }

    pub fn deinit(self: *CostTracker) void {
        if (self.owned_storage_ptr) |ptr| {
            ptr.deinit();
            self.allocator.destroy(ptr);
        }
        self.model_pricing.deinit();
    }

    /// Record a cost event.
    ///
    /// Args:
    ///   session_id: Session identifier
    ///   agent_name: Agent name
    ///   model: Model identifier
    ///   input_tokens: Number of input tokens
    ///   output_tokens: Number of output tokens
    ///   thinking_tokens: Number of thinking tokens (default: 0)
    ///   metadata: Optional metadata (JSON object)
    ///
    /// Returns:
    ///   Cost record (caller owns memory)
    ///
    /// Example:
    ///   const cost = try tracker.recordCost(
    ///       "session-1", "assistant", "claude-sonnet-4",
    ///       1000, 500, 0, null
    ///   );
    ///   defer allocator.destroy(cost);
    ///   std.debug.print("Total: ${d:.4}\n", .{cost.total_cost});
    pub fn recordCost(
        self: *CostTracker,
        session_id: []const u8,
        agent_name: []const u8,
        model: []const u8,
        input_tokens: usize,
        output_tokens: usize,
        thinking_tokens: usize,
        metadata: ?std.json.Value,
    ) !*Cost {
        // Create cost record
        var cost = try Cost.init(
            self.allocator,
            session_id,
            agent_name,
            model,
            input_tokens,
            output_tokens,
            thinking_tokens,
            &self.model_pricing,
        );

        // Set metadata if provided
        if (metadata) |m| {
            cost.metadata.object.deinit();
            cost.metadata = m;
        }

        // Store cost record
        try self.storage.store(&cost);

        // Return owned copy
        const cost_ptr = try self.allocator.create(Cost);
        cost_ptr.* = cost;
        return cost_ptr;
    }

    /// Get total cost for a session.
    ///
    /// Args:
    ///   session_id: Session identifier
    ///   start_time: Optional start time (Unix millis)
    ///   end_time: Optional end time (Unix millis)
    ///
    /// Returns:
    ///   Total cost in dollars
    ///
    /// Example:
    ///   const total = try tracker.getSessionCost("session-1", null, null);
    ///   std.debug.print("Session cost: ${d:.2}\n", .{total});
    pub fn getSessionCost(
        self: *CostTracker,
        session_id: []const u8,
        start_time: ?i64,
        end_time: ?i64,
    ) !f64 {
        const costs = try self.storage.query(session_id, null, start_time, end_time);
        defer self.allocator.free(costs);

        var total: f64 = 0.0;
        for (costs) |cost| {
            total += cost.total_cost;
        }
        return total;
    }

    /// Get total cost for an agent.
    ///
    /// Args:
    ///   agent_name: Agent name
    ///   start_time: Optional start time (Unix millis)
    ///   end_time: Optional end time (Unix millis)
    ///
    /// Returns:
    ///   Total cost in dollars
    ///
    /// Example:
    ///   const total = try tracker.getAgentCost("assistant", null, null);
    ///   std.debug.print("Agent cost: ${d:.2}\n", .{total});
    pub fn getAgentCost(
        self: *CostTracker,
        agent_name: []const u8,
        start_time: ?i64,
        end_time: ?i64,
    ) !f64 {
        const costs = try self.storage.query(null, agent_name, start_time, end_time);
        defer self.allocator.free(costs);

        var total: f64 = 0.0;
        for (costs) |cost| {
            total += cost.total_cost;
        }
        return total;
    }

    /// Get total cost across all sessions and agents.
    ///
    /// Args:
    ///   start_time: Optional start time (Unix millis)
    ///   end_time: Optional end time (Unix millis)
    ///
    /// Returns:
    ///   Total cost in dollars
    ///
    /// Example:
    ///   const total = try tracker.getTotalCost(null, null);
    ///   std.debug.print("Total cost: ${d:.2}\n", .{total});
    pub fn getTotalCost(
        self: *CostTracker,
        start_time: ?i64,
        end_time: ?i64,
    ) !f64 {
        const costs = try self.storage.query(null, null, start_time, end_time);
        defer self.allocator.free(costs);

        var total: f64 = 0.0;
        for (costs) |cost| {
            total += cost.total_cost;
        }
        return total;
    }

    /// Get cost breakdown by model.
    ///
    /// Args:
    ///   session_id: Optional session identifier
    ///   start_time: Optional start time (Unix millis)
    ///   end_time: Optional end time (Unix millis)
    ///
    /// Returns:
    ///   HashMap from model to total cost (caller owns memory)
    ///
    /// Example:
    ///   const breakdown = try tracker.getCostByModel("session-1", null, null);
    ///   defer {
    ///       var iter = breakdown.iterator();
    ///       while (iter.next()) |entry| {
    ///           allocator.free(entry.key_ptr.*);
    ///       }
    ///       breakdown.deinit();
    ///   }
    pub fn getCostByModel(
        self: *CostTracker,
        session_id: ?[]const u8,
        start_time: ?i64,
        end_time: ?i64,
    ) !std.StringHashMap(f64) {
        const costs = try self.storage.query(session_id, null, start_time, end_time);
        defer self.allocator.free(costs);

        var breakdown = std.StringHashMap(f64).init(self.allocator);

        for (costs) |cost| {
            const gop = try breakdown.getOrPut(cost.model);
            if (!gop.found_existing) {
                gop.key_ptr.* = try self.allocator.dupe(u8, cost.model);
                gop.value_ptr.* = 0.0;
            }
            gop.value_ptr.* += cost.total_cost;
        }

        return breakdown;
    }

    /// Get cost statistics for a session.
    ///
    /// Args:
    ///   session_id: Session identifier
    ///
    /// Returns:
    ///   JSON object with statistics (caller owns memory)
    ///
    /// Example:
    ///   var stats = try tracker.getSessionStats("session-1");
    ///   defer stats.object.deinit();
    ///   if (stats.object.get("total_cost")) |cost| {
    ///       std.debug.print("Total: ${d:.2}\n", .{cost.float});
    ///   }
    pub fn getSessionStats(
        self: *CostTracker,
        session_id: []const u8,
    ) !std.json.Value {
        const costs = try self.storage.query(session_id, null, null, null);
        defer self.allocator.free(costs);

        if (costs.len == 0) {
            var obj = std.json.ObjectMap.init(self.allocator);
            try obj.put("total_cost", .{ .float = 0.0 });
            try obj.put("total_requests", .{ .integer = 0 });
            try obj.put("total_input_tokens", .{ .integer = 0 });
            try obj.put("total_output_tokens", .{ .integer = 0 });
            try obj.put("total_thinking_tokens", .{ .integer = 0 });
            return std.json.Value{ .object = obj };
        }

        var total_cost: f64 = 0.0;
        var total_input_tokens: usize = 0;
        var total_output_tokens: usize = 0;
        var total_thinking_tokens: usize = 0;

        for (costs) |cost| {
            total_cost += cost.total_cost;
            total_input_tokens += cost.input_tokens;
            total_output_tokens += cost.output_tokens;
            total_thinking_tokens += cost.thinking_tokens;
        }

        var obj = std.json.ObjectMap.init(self.allocator);
        try obj.put("total_cost", .{ .float = total_cost });
        try obj.put("total_requests", .{ .integer = @intCast(costs.len) });
        try obj.put("total_input_tokens", .{ .integer = @intCast(total_input_tokens) });
        try obj.put("total_output_tokens", .{ .integer = @intCast(total_output_tokens) });
        try obj.put("total_thinking_tokens", .{ .integer = @intCast(total_thinking_tokens) });
        try obj.put("avg_cost_per_request", .{ .float = total_cost / @as(f64, @floatFromInt(costs.len)) });

        return std.json.Value{ .object = obj };
    }
};

// Tests
test "InMemoryStorage store and query" {
    const allocator = std.testing.allocator;

    var storage = InMemoryStorage.init(allocator);
    defer storage.deinit();

    var pricing = try ModelPricing.init(allocator);
    defer pricing.deinit();

    // Create cost record
    var cost1 = try Cost.init(
        allocator,
        "session-1",
        "assistant",
        "claude-sonnet-4",
        1000,
        500,
        0,
        &pricing,
    );
    defer cost1.deinit();

    // Store it
    try storage.store(&cost1);

    // Query by session
    const results = try storage.query("session-1", null, null, null);
    defer allocator.free(results);

    try std.testing.expectEqual(@as(usize, 1), results.len);
    try std.testing.expectEqualStrings("session-1", results[0].session_id);
}

test "InMemoryStorage query filtering" {
    const allocator = std.testing.allocator;

    var storage = InMemoryStorage.init(allocator);
    defer storage.deinit();

    var pricing = try ModelPricing.init(allocator);
    defer pricing.deinit();

    // Create multiple costs
    var cost1 = try Cost.init(allocator, "session-1", "agent-1", "gpt-4o", 1000, 500, 0, &pricing);
    defer cost1.deinit();
    try storage.store(&cost1);

    var cost2 = try Cost.init(allocator, "session-2", "agent-1", "gpt-4o", 2000, 1000, 0, &pricing);
    defer cost2.deinit();
    try storage.store(&cost2);

    var cost3 = try Cost.init(allocator, "session-1", "agent-2", "gpt-4o", 1500, 750, 0, &pricing);
    defer cost3.deinit();
    try storage.store(&cost3);

    // Query by session
    const session_results = try storage.query("session-1", null, null, null);
    defer allocator.free(session_results);
    try std.testing.expectEqual(@as(usize, 2), session_results.len);

    // Query by agent
    const agent_results = try storage.query(null, "agent-1", null, null);
    defer allocator.free(agent_results);
    try std.testing.expectEqual(@as(usize, 2), agent_results.len);

    // Query by both
    const combined_results = try storage.query("session-1", "agent-1", null, null);
    defer allocator.free(combined_results);
    try std.testing.expectEqual(@as(usize, 1), combined_results.len);
}

test "CostTracker recordCost" {
    const allocator = std.testing.allocator;

    var tracker = try CostTracker.init(allocator, null);
    defer tracker.deinit();

    const cost = try tracker.recordCost(
        "session-1",
        "assistant",
        "claude-sonnet-4",
        1000,
        500,
        0,
        null,
    );
    defer {
        cost.deinit();
        allocator.destroy(cost);
    }

    // Verify cost was recorded
    try std.testing.expectApproxEqAbs(@as(f64, 0.0105), cost.total_cost, 0.001);
}

test "CostTracker getSessionCost" {
    const allocator = std.testing.allocator;

    var tracker = try CostTracker.init(allocator, null);
    defer tracker.deinit();

    // Record multiple costs
    const cost1 = try tracker.recordCost("session-1", "agent-1", "gpt-4o", 1000, 500, 0, null);
    defer {
        cost1.deinit();
        allocator.destroy(cost1);
    }

    const cost2 = try tracker.recordCost("session-1", "agent-2", "gpt-4o", 2000, 1000, 0, null);
    defer {
        cost2.deinit();
        allocator.destroy(cost2);
    }

    const cost3 = try tracker.recordCost("session-2", "agent-1", "gpt-4o", 1500, 750, 0, null);
    defer {
        cost3.deinit();
        allocator.destroy(cost3);
    }

    // Get session cost
    const session1_cost = try tracker.getSessionCost("session-1", null, null);
    const session2_cost = try tracker.getSessionCost("session-2", null, null);

    // Session 1 should have cost1 + cost2
    try std.testing.expect(session1_cost > 0.0);
    try std.testing.expect(session2_cost > 0.0);
    try std.testing.expect(session1_cost > session2_cost);
}

test "CostTracker getSessionStats" {
    const allocator = std.testing.allocator;

    var tracker = try CostTracker.init(allocator, null);
    defer tracker.deinit();

    // Record some costs
    const cost1 = try tracker.recordCost("session-1", "assistant", "claude-sonnet-4", 1000, 500, 0, null);
    defer {
        cost1.deinit();
        allocator.destroy(cost1);
    }

    const cost2 = try tracker.recordCost("session-1", "assistant", "claude-sonnet-4", 2000, 1000, 0, null);
    defer {
        cost2.deinit();
        allocator.destroy(cost2);
    }

    // Get stats
    var stats = try tracker.getSessionStats("session-1");
    defer stats.object.deinit();

    // Verify stats
    try std.testing.expect(stats.object.get("total_cost") != null);
    try std.testing.expect(stats.object.get("total_requests") != null);
    try std.testing.expectEqual(@as(i64, 2), stats.object.get("total_requests").?.integer);
}

test "CostTracker getCostByModel" {
    const allocator = std.testing.allocator;

    var tracker = try CostTracker.init(allocator, null);
    defer tracker.deinit();

    // Record costs with different models
    const cost1 = try tracker.recordCost("session-1", "assistant", "gpt-4o", 1000, 500, 0, null);
    defer {
        cost1.deinit();
        allocator.destroy(cost1);
    }

    const cost2 = try tracker.recordCost("session-1", "assistant", "claude-sonnet-4", 1000, 500, 0, null);
    defer {
        cost2.deinit();
        allocator.destroy(cost2);
    }

    const cost3 = try tracker.recordCost("session-1", "assistant", "gpt-4o", 2000, 1000, 0, null);
    defer {
        cost3.deinit();
        allocator.destroy(cost3);
    }

    // Get breakdown
    var breakdown = try tracker.getCostByModel("session-1", null, null);
    defer {
        var iter = breakdown.iterator();
        while (iter.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        breakdown.deinit();
    }

    // Should have 2 models
    try std.testing.expectEqual(@as(usize, 2), breakdown.count());

    // Verify costs exist for both models
    try std.testing.expect(breakdown.get("gpt-4o") != null);
    try std.testing.expect(breakdown.get("claude-sonnet-4") != null);
}

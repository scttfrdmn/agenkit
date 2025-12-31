/// Introspection capability for examining agent internal state.
///
/// This module provides introspection support - the ability for agents to examine
/// their own internal state, memory, and capabilities. This is distinct from the
/// Reflection pattern, which is about analyzing past performance.
///
/// Key distinctions:
/// - Introspection (this module): "What do I know?" - State examination
/// - Reflection (pattern): "How did I do?" - Performance analysis
///
/// References:
/// - Issue #301: Add Introspection Capability to Agent Interface
/// - ArXiv: Introspection of Thought Helps AI Agents (https://arxiv.org/abs/2507.08664)
/// - Biswas & Talukdar: Building Agentic AI Systems
const std = @import("std");
const Allocator = std.mem.Allocator;

/// Result of agent introspection - a snapshot of internal state.
///
/// This provides a structured view into an agent's current state, including
/// its capabilities, memory contents, and any agent-specific internal state.
///
/// Design decisions:
/// - timestamp: Unix timestamp (i64) for when this snapshot was taken
/// - agent_name: Which agent was introspected (owned slice)
/// - capabilities: What the agent can do (owned slice)
/// - memory_state: Contents of agent's memory (null if no memory)
/// - internal_state: Agent-specific state information
/// - metadata: Extension point for additional information
///
/// Memory management:
/// All string fields are owned and must be deallocated with deinit()
///
/// Introspection is useful for:
/// - Debugging: Examine agent state during development
/// - Monitoring: Track agent state in production
/// - Coordination: Agents can inspect each other's capabilities
/// - Testing: Verify agent state in tests
/// - Explainability: Understand what an agent "knows"
pub const IntrospectionResult = struct {
    allocator: Allocator,

    /// Unix timestamp when introspection was performed
    timestamp: i64,

    /// Name of the agent that was introspected (owned)
    agent_name: []const u8,

    /// List of capability strings this agent supports (owned)
    capabilities: []const []const u8,

    /// Agent's memory contents as JSON value (null if no memory)
    memory_state: ?std.json.Value,

    /// Agent-specific internal state as JSON value
    internal_state: std.json.Value,

    /// Additional introspection metadata as JSON value
    metadata: std.json.Value,

    /// Create a new introspection result.
    ///
    /// Arguments:
    /// - allocator: Memory allocator to use
    /// - agent_name: Name of the agent
    /// - capabilities: List of capabilities
    /// - memory_state: Optional memory state as JSON
    /// - internal_state: Agent-specific internal state as JSON
    /// - metadata: Additional metadata as JSON
    ///
    /// Returns:
    /// A new IntrospectionResult with current timestamp
    ///
    /// Note: Takes ownership of agent_name and capabilities slices
    pub fn init(
        allocator: Allocator,
        agent_name: []const u8,
        capabilities: []const []const u8,
        memory_state: ?std.json.Value,
        internal_state: std.json.Value,
        metadata: std.json.Value,
    ) Allocator.Error!IntrospectionResult {
        if (agent_name.len == 0) {
            return error.OutOfMemory; // Zig doesn't have custom validation errors in allocator context
        }

        const timestamp = std.time.timestamp();

        return IntrospectionResult{
            .allocator = allocator,
            .timestamp = timestamp,
            .agent_name = agent_name,
            .capabilities = capabilities,
            .memory_state = memory_state,
            .internal_state = internal_state,
            .metadata = metadata,
        };
    }

    /// Free all resources associated with this introspection result.
    pub fn deinit(self: *IntrospectionResult) void {
        // Free agent name
        self.allocator.free(self.agent_name);

        // Free capabilities
        for (self.capabilities) |cap| {
            self.allocator.free(cap);
        }
        self.allocator.free(self.capabilities);

        // Free JSON object maps
        if (self.memory_state) |mem| {
            if (mem == .object) {
                var obj = mem.object;
                obj.deinit();
            }
        }
        if (self.internal_state == .object) {
            var obj = self.internal_state.object;
            obj.deinit();
        }
        if (self.metadata == .object) {
            var obj = self.metadata.object;
            obj.deinit();
        }
    }

    /// Validate an introspection result.
    ///
    /// Returns: true if valid, false otherwise
    pub fn validate(self: *const IntrospectionResult) bool {
        return self.agent_name.len > 0;
    }
};

/// Create a default introspection result for an agent.
///
/// This is a helper function that creates an introspection result with default
/// values for agents that don't have custom memory or internal state.
///
/// Arguments:
/// - allocator: Memory allocator to use
/// - name: Agent name (will be duplicated)
/// - capabilities: Agent capabilities (will be duplicated)
///
/// Returns:
/// IntrospectionResult with basic information
///
/// Caller must call deinit() when done
pub fn createDefaultIntrospectionResult(
    allocator: Allocator,
    name: []const u8,
    capabilities: []const []const u8,
) Allocator.Error!IntrospectionResult {
    // Duplicate name
    const name_copy = try allocator.dupe(u8, name);
    errdefer allocator.free(name_copy);

    // Duplicate capabilities
    const caps_copy = try allocator.alloc([]const u8, capabilities.len);
    errdefer allocator.free(caps_copy);

    for (capabilities, 0..) |cap, i| {
        caps_copy[i] = try allocator.dupe(u8, cap);
    }

    // Create empty JSON objects
    const internal_state = std.json.Value{ .object = std.json.ObjectMap.init(allocator) };
    const metadata = std.json.Value{ .object = std.json.ObjectMap.init(allocator) };

    return IntrospectionResult.init(
        allocator,
        name_copy,
        caps_copy,
        null,
        internal_state,
        metadata,
    );
}

// Tests
const testing = std.testing;

test "IntrospectionResult - basic creation" {
    const allocator = testing.allocator;

    const name = try allocator.dupe(u8, "test-agent");
    const caps = try allocator.alloc([]const u8, 2);
    caps[0] = try allocator.dupe(u8, "test");
    caps[1] = try allocator.dupe(u8, "demo");

    const internal_state = std.json.Value{ .object = std.json.ObjectMap.init(allocator) };
    const metadata = std.json.Value{ .object = std.json.ObjectMap.init(allocator) };

    var result = try IntrospectionResult.init(
        allocator,
        name,
        caps,
        null,
        internal_state,
        metadata,
    );
    defer result.deinit();

    try testing.expectEqualStrings("test-agent", result.agent_name);
    try testing.expectEqual(@as(usize, 2), result.capabilities.len);
    try testing.expect(result.memory_state == null);
}

test "IntrospectionResult - with memory state" {
    const allocator = testing.allocator;

    const name = try allocator.dupe(u8, "memory-agent");
    const caps = try allocator.alloc([]const u8, 1);
    caps[0] = try allocator.dupe(u8, "memory");

    var memory = std.json.ObjectMap.init(allocator);
    try memory.put("short_term_count", std.json.Value{ .integer = 5 });
    try memory.put("long_term_count", std.json.Value{ .integer = 10 });
    const memory_state = std.json.Value{ .object = memory };

    const internal_state = std.json.Value{ .object = std.json.ObjectMap.init(allocator) };
    const metadata = std.json.Value{ .object = std.json.ObjectMap.init(allocator) };

    var result = try IntrospectionResult.init(
        allocator,
        name,
        caps,
        memory_state,
        internal_state,
        metadata,
    );
    defer result.deinit();

    try testing.expect(result.memory_state != null);
    const mem = result.memory_state.?.object;
    try testing.expectEqual(@as(i64, 5), mem.get("short_term_count").?.integer);
}

test "IntrospectionResult - validation" {
    const allocator = testing.allocator;

    const name = try allocator.dupe(u8, "test");
    const caps = try allocator.alloc([]const u8, 0);

    const internal_state = std.json.Value{ .object = std.json.ObjectMap.init(allocator) };
    const metadata = std.json.Value{ .object = std.json.ObjectMap.init(allocator) };

    var result = try IntrospectionResult.init(
        allocator,
        name,
        caps,
        null,
        internal_state,
        metadata,
    );
    defer result.deinit();

    try testing.expect(result.validate());
}

test "IntrospectionResult - timestamp is recent" {
    const allocator = testing.allocator;

    const before = std.time.timestamp();

    const name = try allocator.dupe(u8, "test");
    const caps = try allocator.alloc([]const u8, 0);
    const internal_state = std.json.Value{ .object = std.json.ObjectMap.init(allocator) };
    const metadata = std.json.Value{ .object = std.json.ObjectMap.init(allocator) };

    var result = try IntrospectionResult.init(
        allocator,
        name,
        caps,
        null,
        internal_state,
        metadata,
    );
    defer result.deinit();

    const after = std.time.timestamp();

    try testing.expect(result.timestamp >= before);
    try testing.expect(result.timestamp <= after);
}

test "createDefaultIntrospectionResult - basic" {
    const allocator = testing.allocator;

    const name = "simple-agent";
    const caps = &[_][]const u8{ "test", "demo" };

    var result = try createDefaultIntrospectionResult(allocator, name, caps);
    defer result.deinit();

    try testing.expectEqualStrings("simple-agent", result.agent_name);
    try testing.expectEqual(@as(usize, 2), result.capabilities.len);
    try testing.expectEqualStrings("test", result.capabilities[0]);
    try testing.expectEqualStrings("demo", result.capabilities[1]);
    try testing.expect(result.memory_state == null);
    try testing.expect(result.internal_state.object.count() == 0);
}

test "createDefaultIntrospectionResult - no capabilities" {
    const allocator = testing.allocator;

    const name = "simple-agent";
    const caps = &[_][]const u8{};

    var result = try createDefaultIntrospectionResult(allocator, name, caps);
    defer result.deinit();

    try testing.expectEqualStrings("simple-agent", result.agent_name);
    try testing.expectEqual(@as(usize, 0), result.capabilities.len);
}

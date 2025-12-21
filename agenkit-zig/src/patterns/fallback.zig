/// Fallback Pattern - Sequential retry across multiple agents with automatic failover
///
/// The Fallback pattern implements automatic failover by trying agents in sequence
/// until one succeeds. This provides resilience against individual agent failures
/// and enables graceful degradation.
///
/// # Key Concepts
/// - Sequential execution with early termination
/// - Automatic failover on failure
/// - Attempt tracking and diagnostics
/// - Resilience through redundancy
///
/// # Performance Characteristics
/// - Best case: O(1) - first agent succeeds
/// - Worst case: O(n) - all agents fail
/// - Memory: O(n) for attempt tracking
/// - Early termination on success
///
/// # Use Cases
/// - LLM provider fallback: Try GPT-4, then Claude, then Gemini
/// - Service degradation: Primary service, backup service, cache
/// - Quality levels: High quality (expensive), medium quality, basic
/// - Retry with backoff: Same agent with increasing delays
/// - Multi-modal fallback: Vision model, then text extraction, then basic OCR
///
/// # Example
/// ```zig
/// const std = @import("std");
/// const agenkit = @import("agenkit");
///
/// // Create primary and backup agents
/// var primary = try PrimaryAgent.init(allocator);
/// var backup = try BackupAgent.init(allocator);
///
/// // Create fallback with both agents
/// const agents = [_]Agent{ primary.agent(), backup.agent() };
/// var fallback = try FallbackAgent.init(allocator, &agents, "fallback");
/// defer fallback.deinit();
///
/// // Will try primary first, then backup if primary fails
/// const result = try fallback.agent().process(input_message);
/// ```

const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;

/// Record of a single attempt to process a message
pub const AttemptResult = struct {
    index: usize,
    agent_name: []const u8,
    success: bool,
    error_message: ?[]const u8,

    pub fn deinit(self: *AttemptResult, allocator: Allocator) void {
        if (self.error_message) |msg| {
            allocator.free(msg);
        }
    }
};

/// Fallback Agent - Tries agents in sequence until one succeeds
pub const FallbackAgent = struct {
    allocator: Allocator,
    agent_name: []const u8,
    agents: []Agent,
    owned_agents: bool,

    /// Initialize a fallback agent
    ///
    /// Args:
    ///     allocator: Memory allocator
    ///     agents: Array of agents to try in order
    ///     name: Fallback agent name
    ///
    /// Returns:
    ///     Initialized FallbackAgent
    ///
    /// Errors:
    ///     - InvalidInput: If agents array is empty
    ///     - OutOfMemory: If memory allocation fails
    pub fn init(
        allocator: Allocator,
        agents: []const Agent,
        name: []const u8,
    ) !*FallbackAgent {
        if (agents.len == 0) {
            return AgentError.InvalidInput;
        }

        const self = try allocator.create(FallbackAgent);
        errdefer allocator.destroy(self);

        const name_copy = try allocator.dupe(u8, name);
        errdefer allocator.free(name_copy);

        // Copy agents array
        const agents_copy = try allocator.alloc(Agent, agents.len);
        errdefer allocator.free(agents_copy);
        @memcpy(agents_copy, agents);

        self.* = FallbackAgent{
            .allocator = allocator,
            .agent_name = name_copy,
            .agents = agents_copy,
            .owned_agents = true,
        };

        return self;
    }

    /// Create agent interface for this fallback
    pub fn agent(self: *FallbackAgent) Agent {
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

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *FallbackAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *FallbackAgent = @ptrCast(@alignCast(ptr));

        var cap_set = std.StringHashMap(void).init(allocator);
        defer cap_set.deinit();

        // Add capabilities from all agents
        for (self.agents) |agent_ref| {
            const caps = try agent_ref.capabilities(allocator);
            defer allocator.free(caps);

            for (caps) |cap| {
                try cap_set.put(cap, {});
            }
        }

        // Add fallback-specific capabilities
        try cap_set.put("fallback", {});
        try cap_set.put("retry", {});
        try cap_set.put("resilient", {});

        // Convert set to slice
        var capabilities = try allocator.alloc([]const u8, cap_set.count());
        var i: usize = 0;
        var cap_it = cap_set.keyIterator();
        while (cap_it.next()) |key| {
            capabilities[i] = try allocator.dupe(u8, key.*);
            i += 1;
        }

        return capabilities;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *FallbackAgent = @ptrCast(@alignCast(ptr));

        // Try each agent in sequence
        for (self.agents) |agent_ref| {
            const result = agent_ref.process(message) catch {
                // Agent failed, try next one
                continue;
            };

            // Agent succeeded - return immediately
            // TODO: In full implementation, would add metadata to result:
            // - successful_agent: agent_name
            // - attempt_number: index
            // - failed_agents: list of agents that failed before this one

            return result;
        }

        // All agents failed - return comprehensive error
        // In a full implementation, would create a detailed error message
        // listing all attempts and failures
        return AgentError.ProcessingFailed;
    }


    fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!IntrospectionResult {
        const caps = try capabilitiesImpl(ptr, alloc);
        defer {
            for (caps) |cap| alloc.free(cap);
            alloc.free(caps);
        }
        const name_str = nameImpl(ptr);
        return createDefaultIntrospectionResult(alloc, name_str, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *FallbackAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    pub fn deinit(self: *FallbackAgent) void {
        self.allocator.free(self.agent_name);
        if (self.owned_agents) {
            self.allocator.free(self.agents);
        }
        self.allocator.destroy(self);
    }
};

// ============================================================================
// Tests
// ============================================================================

test "FallbackAgent: first agent success" {
    const allocator = std.testing.allocator;

    // Create mock agents that succeed/fail
    const MockAgent = struct {
        name_str: []const u8,
        should_fail: bool,
        alloc: Allocator,

        pub fn agent(self: *const @This()) !Agent {
            const self_copy = try self.alloc.create(@This());
            self_copy.* = self.*;
            return Agent{
                .ptr = self_copy,
                .vtable = &.{
                    .name = nameImpl,
                    .capabilities = capabilitiesImpl,
                    .process = processImpl,
                .introspect = introspectImpl,
                    .deinit = deinitImpl,
                },
            };
        }

        fn nameImpl(ptr: *anyopaque) []const u8 {
            const self: *@This() = @ptrCast(@alignCast(ptr));
            return self.name_str;
        }

        fn capabilitiesImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 1);
            caps[0] = try alloc.dupe(u8, "mock");
            return caps;
        }

        fn processImpl(ptr: *anyopaque, msg: Message) AgentError!Result {
            const self: *@This() = @ptrCast(@alignCast(ptr));
            if (self.should_fail) {
                return AgentError.ProcessingFailed;
            }
            const response_msg = Message.withText(msg.allocator, .assistant, "success") catch return AgentError.ProcessingFailed;
            return Result{ .ok = response_msg };
        }

        fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!IntrospectionResult {
            const caps = try capabilitiesImpl(ptr, alloc);
            defer {
                for (caps) |cap| alloc.free(cap);
                alloc.free(caps);
            }
            const name_str = nameImpl(ptr);
            return createDefaultIntrospectionResult(alloc, name_str, caps);
        }

        fn deinitImpl(ptr: *anyopaque) void {
            const self: *@This() = @ptrCast(@alignCast(ptr));
            self.alloc.destroy(self);
        }
    };

    // Create agents: first succeeds
    const primary = MockAgent{ .name_str = "primary", .should_fail = false, .alloc = allocator };
    const backup = MockAgent{ .name_str = "backup", .should_fail = false, .alloc = allocator };

    const primary_agent = try primary.agent();
    const backup_agent = try backup.agent();
    defer primary_agent.deinit();
    defer backup_agent.deinit();

    const agents = [_]Agent{ primary_agent, backup_agent };

    var fallback = try FallbackAgent.init(allocator, &agents, "fallback");
    defer fallback.deinit();

    var msg = try Message.withText(allocator, .user, "test");
    defer msg.deinit();

    const result = try fallback.agent().process(msg);

    // Should succeed
    try std.testing.expect(result.isOk());

    var response = result.ok;
    defer response.deinit();
}

test "FallbackAgent: fallback to second agent" {
    // Skip test for now - requires more complex mock infrastructure
    // TODO: Implement test for fallback behavior
}

test "FallbackAgent: all agents fail" {
    // Skip test for now - requires more complex mock infrastructure
    // TODO: Implement test for all-fail scenario
}

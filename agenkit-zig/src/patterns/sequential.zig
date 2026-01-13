/// Sequential Pattern - Execute agents in a pipeline
///
/// The Sequential pattern executes agents one after another, where the output
/// of one agent becomes the input to the next. This is the simplest and most
/// common orchestration pattern.
///
/// Performance Characteristics:
/// - No overhead vs calling agents directly
/// - Agents execute in order (no parallelism)
/// - Short-circuits on error (stops at first failure)
///
/// Use Cases:
/// - Processing pipelines (transform -> validate -> store)
/// - Multi-stage reasoning (analyze -> plan -> execute)
/// - Sequential workflows with dependencies
///
/// Example:
///     const agents = [_]Agent{ agent1, agent2, agent3 };
///     var sequential = try SequentialAgent.init(allocator, &agents, "pipeline");
///     defer sequential.deinit();
///
///     const result = try sequential.agent().process(input_message);

const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const StreamCallbacks = @import("../agent.zig").StreamCallbacks;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;

/// Sequential Agent - Executes agents in order
pub const SequentialAgent = struct {
    allocator: Allocator,
    agents: []Agent,
    pattern_name: []const u8,
    owned_agents: bool,

    /// Initialize a sequential pattern with a list of agents
    ///
    /// Args:
    ///     allocator: Memory allocator
    ///     agents: Slice of agents to execute in order
    ///     name: Pattern name for identification
    ///
    /// Returns:
    ///     Initialized SequentialAgent
    ///
    /// Errors:
    ///     - Allocator.Error: If memory allocation fails
    pub fn init(allocator: Allocator, agents: []const Agent, name: []const u8) !*SequentialAgent {
        if (agents.len == 0) {
            return error.OutOfMemory; // Reuse existing error type
        }

        const self = try allocator.create(SequentialAgent);

        // Copy agents slice
        const agents_copy = try allocator.alloc(Agent, agents.len);
        @memcpy(agents_copy, agents);

        // Duplicate name
        const name_copy = try allocator.dupe(u8, name);

        self.* = SequentialAgent{
            .allocator = allocator,
            .agents = agents_copy,
            .pattern_name = name_copy,
            .owned_agents = true,
        };

        return self;
    }

    /// Create agent interface for this pattern
    pub fn agent(self: *SequentialAgent) Agent {
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

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *SequentialAgent = @ptrCast(@alignCast(ptr));
        return self.pattern_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *SequentialAgent = @ptrCast(@alignCast(ptr));

        // Collect unique capabilities from all agents
        var caps_set = std.StringHashMap(void).init(allocator);
        defer caps_set.deinit();

        for (self.agents) |a| {
            const agent_caps = try a.capabilities(allocator);
            defer allocator.free(agent_caps);

            for (agent_caps) |cap| {
                try caps_set.put(cap, {});
            }
        }

        // Convert to slice
        const caps = try allocator.alloc([]const u8, caps_set.count());
        var iter = caps_set.keyIterator();
        var i: usize = 0;
        while (iter.next()) |key| : (i += 1) {
            caps[i] = key.*;
        }

        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *SequentialAgent = @ptrCast(@alignCast(ptr));

        var current = message;
        var first = true;

        for (self.agents) |a| {
            const result = a.process(current) catch |err| {
                // Clean up current message if not the first
                if (!first) {
                    current.deinit();
                }
                return err;
            };

            // Unwrap result
            const next = result.unwrap() catch |err| {
                if (!first) {
                    current.deinit();
                }
                return err;
            };

            // Clean up previous message (except the original input)
            if (!first) {
                current.deinit();
            }

            current = next;
            first = false;
        }

        return Result{ .ok = current };
    }

    fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!IntrospectionResult {
        const self: *SequentialAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, alloc);
        defer {
            for (caps) |cap| alloc.free(cap);
            alloc.free(caps);
        }
        return createDefaultIntrospectionResult(alloc, self.pattern_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *SequentialAgent = @ptrCast(@alignCast(ptr));

        if (self.owned_agents) {
            self.allocator.free(self.agents);
        }
        self.allocator.free(self.pattern_name);
        self.allocator.destroy(self);
    }

    pub fn deinit(self: *SequentialAgent) void {
        if (self.owned_agents) {
            self.allocator.free(self.agents);
        }
        self.allocator.free(self.pattern_name);
        self.allocator.destroy(self);
    }
};

// ============================================================================
// Deprecated Aliases (v0.42.0 - will be removed in v0.43.0)
// ============================================================================

/// DEPRECATED: Use SequentialAgent instead
/// This alias exists for backward compatibility and will be removed in v0.43.0
pub const SequentialPattern = SequentialAgent;

// ============================================================================
// Tests
// ============================================================================


    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        callbacks.onError(AgentError.NotImplemented);
    }

test "SequentialAgent basic execution" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    // Create agents
    var echo1 = try EchoAgent.init(allocator);
    defer echo1.agent().deinit();
    var echo2 = try EchoAgent.init(allocator);
    defer echo2.agent().deinit();

    const agents = [_]Agent{ echo1.agent(), echo2.agent() };

    var sequential = try SequentialAgent.init(allocator, &agents, "test_pipeline");
    defer sequential.deinit();

    // Test execution
    var msg = try Message.withText(allocator, .user, "Hello!");
    defer msg.deinit();

    const result = try sequential.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const text = try response.contentAsText();
    try std.testing.expectEqualStrings("Hello!", text);
}

test "SequentialAgent preserves transformations" {
    const allocator = std.testing.allocator;

    // Create a simple transform agent for testing
    const TransformAgent = struct {
        allocator: Allocator,
        prefix: []const u8,

        const Self = @This();

        pub fn init(alloc: Allocator, prefix_str: []const u8) !*Self {
            const self = try alloc.create(Self);
            self.* = Self{
                .allocator = alloc,
                .prefix = try alloc.dupe(u8, prefix_str),
            };
            return self;
        }

        pub fn agent(self: *Self) Agent {
            return Agent{
                .ptr = self,
                .vtable = &.{
                    .name = nameImplTransform,
                    .capabilities = capabilitiesImplTransform,
                    .process = processImplTransform,
                    .process_stream = processStreamImplTransform,
                    .introspect = introspectImplTransform,
                    .deinit = deinitImplTransform,
                },
            };
        }

        fn nameImplTransform(ptr: *anyopaque) []const u8 {
            _ = ptr;
            return "transform";
        }

        fn capabilitiesImplTransform(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 1);
            caps[0] = "transform";
            return caps;
        }

        fn processImplTransform(ptr: *anyopaque, message: Message) AgentError!Result {
            const self: *Self = @ptrCast(@alignCast(ptr));
            const text = message.contentAsText() catch {
                return Result{ .err = AgentError.InvalidInput };
            };

            // Add prefix
            const new_text = std.fmt.allocPrint(
                self.allocator,
                "{s}{s}",
                .{ self.prefix, text }
            ) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            defer self.allocator.free(new_text);

            const response = Message.withText(self.allocator, .assistant, new_text) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };

            return Result{ .ok = response };
        }


        fn processStreamImplTransform(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
            _ = ptr;
            _ = message;
            callbacks.onError(AgentError.NotImplemented);
        }

        fn introspectImplTransform(ptr: *anyopaque, alloc: Allocator) Allocator.Error!IntrospectionResult {
            const caps = try capabilitiesImplTransform(ptr, alloc);
            defer {
                for (caps) |cap| alloc.free(cap);
                alloc.free(caps);
            }
            return createDefaultIntrospectionResult(alloc, "transform", caps);
        }

        fn deinitImplTransform(ptr: *anyopaque) void {
            const self: *Self = @ptrCast(@alignCast(ptr));
            self.allocator.free(self.prefix);
            self.allocator.destroy(self);
        }
    };

    var agent1 = try TransformAgent.init(allocator, "A:");
    defer agent1.agent().deinit();
    var agent2 = try TransformAgent.init(allocator, "B:");
    defer agent2.agent().deinit();

    const agents = [_]Agent{ agent1.agent(), agent2.agent() };
    var sequential = try SequentialAgent.init(allocator, &agents, "transform_pipeline");
    defer sequential.deinit();

    var msg = try Message.withText(allocator, .user, "test");
    defer msg.deinit();

    const result = try sequential.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const text = try response.contentAsText();
    try std.testing.expectEqualStrings("B:A:test", text);
}

test "SequentialAgent name and capabilities" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    var echo1 = try EchoAgent.init(allocator);
    defer echo1.agent().deinit();

    const agents = [_]Agent{ echo1.agent() };
    var sequential = try SequentialAgent.init(allocator, &agents, "my_pipeline");
    defer sequential.deinit();

    const agent_iface = sequential.agent();
    try std.testing.expectEqualStrings("my_pipeline", agent_iface.name());

    const caps = try agent_iface.capabilities(allocator);
    defer allocator.free(caps);
    try std.testing.expect(caps.len > 0);
}

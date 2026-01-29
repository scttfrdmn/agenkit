/// Agent composition patterns
///
/// Simple, lightweight building blocks for composing agents:
/// - Sequential: Execute agents in order (pipeline)
/// - Parallel: Execute agents concurrently (ensemble)
/// - Conditional: Route to different agents based on conditions
/// - Fallback: Try agents in order until one succeeds (fault tolerance)
///
/// These are minimal composition primitives. For richer agent patterns
/// with advanced features, see the patterns module.

const std = @import("std");
const Agent = @import("agent.zig").Agent;
const AgentError = @import("agent.zig").AgentError;
const Result = @import("agent.zig").Result;
const Message = @import("message.zig").Message;
const Allocator = std.mem.Allocator;

//================================================
// Sequential Agent
//================================================

pub const SequentialAgent = struct {
    allocator: Allocator,
    agent_name: []const u8,
    agents: []Agent,

    pub fn init(allocator: Allocator, agent_name: []const u8, agents: []Agent) !*SequentialAgent {
        if (agents.len == 0) {
            return AgentError.InvalidInput;
        }

        const self = try allocator.create(SequentialAgent);
        self.* = .{
            .allocator = allocator,
            .agent_name = try allocator.dupe(u8, agent_name),
            .agents = try allocator.dupe(Agent, agents),
        };
        return self;
    }

    pub fn agent(self: *SequentialAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = name,
                .capabilities = capabilities,
                .process = process,
                .process_stream = processStream,
                .introspect = introspect,
                .deinit = deinit,
            },
        };
    }

    fn name(ptr: *anyopaque) []const u8 {
        const self: *SequentialAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilities(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *SequentialAgent = @ptrCast(@alignCast(ptr));

        var cap_set = std.StringHashMap(void).init(allocator);
        defer cap_set.deinit();

        for (self.agents) |ag| {
            const caps = try ag.capabilities(allocator);
            defer allocator.free(caps);
            for (caps) |cap| {
                try cap_set.put(cap, {});
            }
        }

        var caps = std.ArrayList([]const u8).init(allocator);
        var it = cap_set.keyIterator();
        while (it.next()) |key| {
            try caps.append(try allocator.dupe(u8, key.*));
        }
        try caps.append(try allocator.dupe(u8, "sequential"));

        return caps.toOwnedSlice();
    }

    fn process(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *SequentialAgent = @ptrCast(@alignCast(ptr));

        var current = message;
        for (self.agents) |ag| {
            const result = try ag.process(current);
            if (result.isErr()) {
                return AgentError.ProcessingFailed;
            }
            current = try result.unwrap();
        }

        return Result{ .ok = current };
    }

    fn processStream(ptr: *anyopaque, message: Message, callbacks: @import("agent.zig").StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        callbacks.onError(AgentError.NotImplemented);
    }

    fn introspect(ptr: *anyopaque, allocator: Allocator) Allocator.Error!@import("introspection.zig").IntrospectionResult {
        const self: *SequentialAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilities(ptr, allocator);
        return @import("introspection.zig").createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinit(ptr: *anyopaque) void {
        const self: *SequentialAgent = @ptrCast(@alignCast(ptr));
        self.allocator.free(self.agent_name);
        self.allocator.free(self.agents);
        self.allocator.destroy(self);
    }
};

//================================================
// Fallback Agent
//================================================

pub const FallbackAgent = struct {
    allocator: Allocator,
    agent_name: []const u8,
    agents: []Agent,

    pub fn init(allocator: Allocator, agent_name: []const u8, agents: []Agent) !*FallbackAgent {
        if (agents.len == 0) {
            return AgentError.InvalidInput;
        }

        const self = try allocator.create(FallbackAgent);
        self.* = .{
            .allocator = allocator,
            .agent_name = try allocator.dupe(u8, agent_name),
            .agents = try allocator.dupe(Agent, agents),
        };
        return self;
    }

    pub fn agent(self: *FallbackAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = name,
                .capabilities = capabilities,
                .process = process,
                .process_stream = processStream,
                .introspect = introspect,
                .deinit = deinit,
            },
        };
    }

    fn name(ptr: *anyopaque) []const u8 {
        const self: *FallbackAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilities(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *FallbackAgent = @ptrCast(@alignCast(ptr));

        var cap_set = std.StringHashMap(void).init(allocator);
        defer cap_set.deinit();

        for (self.agents) |ag| {
            const caps = try ag.capabilities(allocator);
            defer allocator.free(caps);
            for (caps) |cap| {
                try cap_set.put(cap, {});
            }
        }

        var caps = std.ArrayList([]const u8).init(allocator);
        var it = cap_set.keyIterator();
        while (it.next()) |key| {
            try caps.append(try allocator.dupe(u8, key.*));
        }
        try caps.append(try allocator.dupe(u8, "fallback"));

        return caps.toOwnedSlice();
    }

    fn process(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *FallbackAgent = @ptrCast(@alignCast(ptr));

        for (self.agents) |ag| {
            const result = ag.process(message) catch |err| {
                // Try next agent on error
                _ = err;
                continue;
            };

            if (result.isOk()) {
                return result;
            }
        }

        return AgentError.ProcessingFailed;
    }

    fn processStream(ptr: *anyopaque, message: Message, callbacks: @import("agent.zig").StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        callbacks.onError(AgentError.NotImplemented);
    }

    fn introspect(ptr: *anyopaque, allocator: Allocator) Allocator.Error!@import("introspection.zig").IntrospectionResult {
        const self: *FallbackAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilities(ptr, allocator);
        return @import("introspection.zig").createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinit(ptr: *anyopaque) void {
        const self: *FallbackAgent = @ptrCast(@alignCast(ptr));
        self.allocator.free(self.agent_name);
        self.allocator.free(self.agents);
        self.allocator.destroy(self);
    }
};

// Note: Parallel and Conditional agents require more complex state management
// and are best implemented in the patterns module where richer features exist.
// These minimal composition primitives (Sequential, Fallback) provide the
// essential building blocks for most use cases.

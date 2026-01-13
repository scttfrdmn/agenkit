/// Multi-Agent Collaboration Pattern
///
/// Enables multiple agents to work together on complex tasks through:
/// - **Coordination**: Agents working on different parts sequentially
/// - **Delegation**: Agents delegating subtasks to specialists
/// - **Consensus**: Agents reaching agreement through discussion
///
/// # Key Concepts
///
/// - **Orchestration**: Coordinate multiple agents with different strategies
/// - **Sequential**: Execute agents one after another
/// - **Delegation**: Main agent delegates to specialists
/// - **Task Tracking**: Monitor execution status and results
///
/// # Use Cases
///
/// - Complex tasks requiring diverse expertise
/// - Problems benefiting from multiple perspectives
/// - Ensemble approaches for reliability
/// - Composable agent workflows
///
/// # Example
///
/// ```zig
/// const std = @import("std");
/// const agenkit = @import("agenkit");
///
/// pub fn main() !void {
///     var gpa = std.heap.GeneralPurposeAllocator(.{}){};
///     defer _ = gpa.deinit();
///     const allocator = gpa.allocator();
///
///     var orchestrator = try agenkit.patterns.MultiAgentOrchestrator.init(
///         allocator,
///         .sequential,
///     );
///     defer orchestrator.deinit();
///
///     var agent1 = try agenkit.EchoAgent.init(allocator);
///     defer agent1.agent().deinit();
///
///     try orchestrator.registerAgent("researcher", agent1.agent());
///
///     var msg = try agenkit.Message.withText(allocator, .user, "Create a report");
///     defer msg.deinit();
///
///     const result = try orchestrator.agent().process(msg);
///     var response = try result.unwrap();
///     defer response.deinit();
/// }
/// ```

const std = @import("std");
const Allocator = std.mem.Allocator;
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const StreamCallbacks = @import("../agent.zig").StreamCallbacks;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Result = @import("../agent.zig").Result;

/// Task execution status
pub const TaskStatus = enum {
    pending,
    in_progress,
    completed,
    failed,

    pub fn toString(self: TaskStatus) []const u8 {
        return switch (self) {
            .pending => "pending",
            .in_progress => "in_progress",
            .completed => "completed",
            .failed => "failed",
        };
    }
};

/// A task assigned to an agent
pub const AgentTask = struct {
    agent_name: []const u8,
    description: []const u8,
    result: ?[]const u8,
    status: TaskStatus,
    error_msg: ?[]const u8,
    allocator: Allocator,

    pub fn init(allocator: Allocator, agent_name: []const u8, description: []const u8) !AgentTask {
        return AgentTask{
            .agent_name = try allocator.dupe(u8, agent_name),
            .description = try allocator.dupe(u8, description),
            .result = null,
            .status = .pending,
            .error_msg = null,
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *AgentTask) void {
        self.allocator.free(self.agent_name);
        self.allocator.free(self.description);
        if (self.result) |r| {
            self.allocator.free(r);
        }
        if (self.error_msg) |e| {
            self.allocator.free(e);
        }
    }

    pub fn setResult(self: *AgentTask, result: []const u8) !void {
        if (self.result) |old| {
            self.allocator.free(old);
        }
        self.result = try self.allocator.dupe(u8, result);
        self.status = .completed;
    }

    pub fn setError(self: *AgentTask, error_msg: []const u8) !void {
        if (self.error_msg) |old| {
            self.allocator.free(old);
        }
        self.error_msg = try self.allocator.dupe(u8, error_msg);
        self.status = .failed;
    }
};

/// Orchestration strategy for coordinating multiple agents
pub const OrchestrationStrategy = enum {
    /// Execute agents one after another
    sequential,
    /// Main agent delegates to specialists (future work)
    delegate,
};

/// Registered agent entry
const RegisteredAgent = struct {
    name: []const u8,
    agent: Agent,
    allocator: Allocator,

    pub fn deinit(self: *RegisteredAgent) void {
        self.allocator.free(self.name);
    }
};

/// Orchestrates multiple agents working together
pub const MultiAgentOrchestrator = struct {
    allocator: Allocator,
    agents: std.ArrayList(RegisteredAgent),
    strategy: OrchestrationStrategy,
    tasks: std.ArrayList(AgentTask),
    agent_name: []const u8,

    pub fn init(allocator: Allocator, strategy: OrchestrationStrategy) !MultiAgentOrchestrator {
        return MultiAgentOrchestrator{
            .allocator = allocator,
            .agents = std.ArrayList(RegisteredAgent){},
            .strategy = strategy,
            .tasks = std.ArrayList(AgentTask){},
            .agent_name = try allocator.dupe(u8, "MultiAgentOrchestrator"),
        };
    }

    pub fn deinit(self: *MultiAgentOrchestrator) void {
        for (self.agents.items) |*entry| {
            entry.deinit();
        }
        self.agents.deinit(self.allocator);

        for (self.tasks.items) |*task| {
            task.deinit();
        }
        self.tasks.deinit(self.allocator);

        self.allocator.free(self.agent_name);
    }

    /// Register an agent that can be used
    pub fn registerAgent(self: *MultiAgentOrchestrator, name: []const u8, agent_instance: Agent) !void {
        const entry = RegisteredAgent{
            .name = try self.allocator.dupe(u8, name),
            .agent = agent_instance,
            .allocator = self.allocator,
        };
        try self.agents.append(self.allocator, entry);
    }

    /// Get list of registered agent names
    pub fn listAgents(self: *const MultiAgentOrchestrator, allocator: Allocator) !std.ArrayList([]const u8) {
        var names = std.ArrayList([]const u8){};
        for (self.agents.items) |entry| {
            try names.append(allocator, try allocator.dupe(u8, entry.name));
        }
        return names;
    }

    /// Get number of registered agents
    pub fn agentCount(self: *const MultiAgentOrchestrator) usize {
        return self.agents.items.len;
    }

    /// Get task history
    pub fn getTasks(self: *const MultiAgentOrchestrator) []const AgentTask {
        return self.tasks.items;
    }

    /// Process message by coordinating multiple agents
    fn processSequential(self: *MultiAgentOrchestrator, message: Message) !Message {
        if (self.agents.items.len == 0) {
            return AgentError.InvalidInput;
        }

        var results = std.ArrayList([]const u8){};
        defer {
            for (results.items) |r| {
                self.allocator.free(r);
            }
            results.deinit(self.allocator);
        }

        // Execute each agent sequentially
        for (self.agents.items) |entry| {
            var task = try AgentTask.init(self.allocator, entry.name, "Process message");

            task.status = .in_progress;

            const result = entry.agent.process(message) catch |err| {
                const error_msg = std.fmt.allocPrint(self.allocator, "Agent {s} failed: {s}", .{ entry.name, @errorName(err) }) catch {
                    return AgentError.ProcessingFailed;
                };
                defer self.allocator.free(error_msg);

                task.setError(error_msg) catch {};
                try self.tasks.append(self.allocator, task);
                continue;
            };

            var response = try result.unwrap();
            defer response.deinit();

            const text = response.contentAsText() catch {
                return AgentError.ProcessingFailed;
            };

            task.setResult(text) catch {
                return AgentError.ProcessingFailed;
            };

            const result_text = std.fmt.allocPrint(self.allocator, "Agent '{s}': {s}", .{ entry.name, text }) catch {
                return AgentError.ProcessingFailed;
            };
            try results.append(self.allocator, result_text);

            try self.tasks.append(self.allocator, task);
        }

        // Combine all results
        var combined = std.ArrayList(u8){};
        defer combined.deinit(self.allocator);

        for (results.items, 0..) |r, i| {
            if (i > 0) {
                try combined.appendSlice(self.allocator, "\n\n");
            }
            try combined.appendSlice(self.allocator, r);
        }

        const final_text = try combined.toOwnedSlice(self.allocator);
        defer self.allocator.free(final_text);
        return try Message.withText(self.allocator, .assistant, final_text);
    }

    /// Get the Agent interface for this orchestrator
    pub fn agent(self: *MultiAgentOrchestrator) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .process = processImpl,
                .process_stream = processStreamImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
            },
        };
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *MultiAgentOrchestrator = @ptrCast(@alignCast(ptr));

        const response = switch (self.strategy) {
            .sequential => self.processSequential(message) catch |err| {
                // Map known AgentErrors, convert others to ProcessingFailed
                if (err == AgentError.InvalidInput) return AgentError.InvalidInput;
                if (err == AgentError.Timeout) return AgentError.Timeout;
                if (err == AgentError.Cancelled) return AgentError.Cancelled;
                if (err == AgentError.NotImplemented) return AgentError.NotImplemented;
                return AgentError.ProcessingFailed;
            },
            .delegate => {
                // Not implemented yet
                return AgentError.NotImplemented;
            },
        };

        return Result{ .ok = response };
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
        const self: *MultiAgentOrchestrator = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *MultiAgentOrchestrator = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = [_][]const u8{ "multiagent", "orchestration", "collaboration" };
        const result = try allocator.alloc([]const u8, caps.len);
        for (caps, 0..) |cap, i| {
            result[i] = try allocator.dupe(u8, cap);
        }
        return result;
    }
};

// Tests
const testing = std.testing;
const EchoAgent = @import("../agent.zig").EchoAgent;


    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        callbacks.onError(AgentError.NotImplemented);
    }

test "TaskStatus toString" {
    try testing.expectEqualStrings("pending", TaskStatus.pending.toString());
    try testing.expectEqualStrings("completed", TaskStatus.completed.toString());
}

test "AgentTask creation" {
    const allocator = testing.allocator;

    var task = try AgentTask.init(allocator, "test_agent", "Test task");
    defer task.deinit();

    try testing.expectEqualStrings("test_agent", task.agent_name);
    try testing.expectEqualStrings("Test task", task.description);
    try testing.expectEqual(TaskStatus.pending, task.status);
}

test "AgentTask setResult" {
    const allocator = testing.allocator;

    var task = try AgentTask.init(allocator, "test_agent", "Test task");
    defer task.deinit();

    try task.setResult("Success!");
    try testing.expectEqualStrings("Success!", task.result.?);
    try testing.expectEqual(TaskStatus.completed, task.status);
}

test "AgentTask setError" {
    const allocator = testing.allocator;

    var task = try AgentTask.init(allocator, "test_agent", "Test task");
    defer task.deinit();

    try task.setError("Failed!");
    try testing.expectEqualStrings("Failed!", task.error_msg.?);
    try testing.expectEqual(TaskStatus.failed, task.status);
}

test "MultiAgentOrchestrator creation" {
    const allocator = testing.allocator;

    var orchestrator = try MultiAgentOrchestrator.init(allocator, .sequential);
    defer orchestrator.deinit();

    try testing.expectEqual(OrchestrationStrategy.sequential, orchestrator.strategy);
    try testing.expectEqual(@as(usize, 0), orchestrator.agentCount());
}

test "MultiAgentOrchestrator registerAgent" {
    const allocator = testing.allocator;

    var orchestrator = try MultiAgentOrchestrator.init(allocator, .sequential);
    defer orchestrator.deinit();

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    try orchestrator.registerAgent("echo", echo.agent());

    try testing.expectEqual(@as(usize, 1), orchestrator.agentCount());
}

test "MultiAgentOrchestrator listAgents" {
    const allocator = testing.allocator;

    var orchestrator = try MultiAgentOrchestrator.init(allocator, .sequential);
    defer orchestrator.deinit();

    var echo1 = try EchoAgent.init(allocator);
    defer echo1.agent().deinit();

    var echo2 = try EchoAgent.init(allocator);
    defer echo2.agent().deinit();

    try orchestrator.registerAgent("agent1", echo1.agent());
    try orchestrator.registerAgent("agent2", echo2.agent());

    var names = try orchestrator.listAgents(allocator);
    defer {
        for (names.items) |name| {
            allocator.free(name);
        }
        names.deinit(allocator);
    }

    try testing.expectEqual(@as(usize, 2), names.items.len);
}

test "MultiAgentOrchestrator sequential execution" {
    const allocator = testing.allocator;

    var orchestrator = try MultiAgentOrchestrator.init(allocator, .sequential);
    defer orchestrator.deinit();

    var echo1 = try EchoAgent.init(allocator);
    defer echo1.agent().deinit();

    var echo2 = try EchoAgent.init(allocator);
    defer echo2.agent().deinit();

    try orchestrator.registerAgent("agent1", echo1.agent());
    try orchestrator.registerAgent("agent2", echo2.agent());

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    const result = try orchestrator.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const content = try response.contentAsText();
    try testing.expect(std.mem.indexOf(u8, content, "agent1") != null);
    try testing.expect(std.mem.indexOf(u8, content, "agent2") != null);
}

test "MultiAgentOrchestrator task tracking" {
    const allocator = testing.allocator;

    var orchestrator = try MultiAgentOrchestrator.init(allocator, .sequential);
    defer orchestrator.deinit();

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    try orchestrator.registerAgent("echo", echo.agent());

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    const result = try orchestrator.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const tasks = orchestrator.getTasks();
    try testing.expectEqual(@as(usize, 1), tasks.len);
    try testing.expectEqual(TaskStatus.completed, tasks[0].status);
}

test "MultiAgentOrchestrator empty agents" {
    const allocator = testing.allocator;

    var orchestrator = try MultiAgentOrchestrator.init(allocator, .sequential);
    defer orchestrator.deinit();

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    const result = orchestrator.agent().process(msg);
    try testing.expectError(AgentError.InvalidInput, result);
}

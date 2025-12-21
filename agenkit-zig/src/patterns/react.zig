/// ReAct (Reasoning + Acting) Pattern
///
/// Implements the ReAct pattern where agents reason about actions and execute tools
/// in an iterative loop until completing a task.
///
/// The ReAct loop:
/// 1. Observation: Current state/input
/// 2. Thought: Reason about what to do next
/// 3. Action: Execute a tool or provide final answer
/// 4. Repeat until task is complete
///
/// References:
/// - ReAct Paper: https://arxiv.org/abs/2210.03629

const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const AgentError = @import("../agent.zig").AgentError;
const Result = @import("../agent.zig").Result;

const Allocator = std.mem.Allocator;

/// Tool function signature
pub const ToolFn = *const fn (allocator: Allocator, input: []const u8) AgentError![]const u8;

/// A tool that can be executed by ReActAgent
pub const Tool = struct {
    name: []const u8,
    description: []const u8,
    execute_fn: ToolFn,
    allocator: Allocator,

    pub fn init(allocator: Allocator, name: []const u8, description: []const u8, execute_fn: ToolFn) !*Tool {
        const self = try allocator.create(Tool);
        self.* = Tool{
            .name = try allocator.dupe(u8, name),
            .description = try allocator.dupe(u8, description),
            .execute_fn = execute_fn,
            .allocator = allocator,
        };
        return self;
    }

    pub fn deinit(self: *Tool) void {
        self.allocator.free(self.name);
        self.allocator.free(self.description);
        self.allocator.destroy(self);
    }

    pub fn execute(self: *Tool, allocator: Allocator, input: []const u8) AgentError![]const u8 {
        return self.execute_fn(allocator, input);
    }
};

/// Result from tool execution
pub const ToolResult = struct {
    tool_name: []const u8,
    result: ?[]const u8,
    error_msg: ?[]const u8,
    success: bool,
    allocator: Allocator,

    pub fn initSuccess(allocator: Allocator, tool_name: []const u8, result: []const u8) !ToolResult {
        return ToolResult{
            .tool_name = try allocator.dupe(u8, tool_name),
            .result = try allocator.dupe(u8, result),
            .error_msg = null,
            .success = true,
            .allocator = allocator,
        };
    }

    pub fn initError(allocator: Allocator, tool_name: []const u8, error_msg: []const u8) !ToolResult {
        return ToolResult{
            .tool_name = try allocator.dupe(u8, tool_name),
            .result = null,
            .error_msg = try allocator.dupe(u8, error_msg),
            .success = false,
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *ToolResult) void {
        self.allocator.free(self.tool_name);
        if (self.result) |r| {
            self.allocator.free(r);
        }
        if (self.error_msg) |e| {
            self.allocator.free(e);
        }
    }
};

/// A single step in the ReAct reasoning loop
pub const ReActStep = struct {
    thought: []const u8,
    action: []const u8,
    action_input: []const u8,
    observation: []const u8,
    step_number: u32,
    allocator: Allocator,

    pub fn init(
        allocator: Allocator,
        thought: []const u8,
        action: []const u8,
        action_input: []const u8,
        step_number: u32,
    ) !ReActStep {
        return ReActStep{
            .thought = try allocator.dupe(u8, thought),
            .action = try allocator.dupe(u8, action),
            .action_input = try allocator.dupe(u8, action_input),
            .observation = try allocator.dupe(u8, ""),
            .step_number = step_number,
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *ReActStep) void {
        self.allocator.free(self.thought);
        self.allocator.free(self.action);
        self.allocator.free(self.action_input);
        self.allocator.free(self.observation);
    }

    pub fn setObservation(self: *ReActStep, observation: []const u8) !void {
        self.allocator.free(self.observation);
        self.observation = try self.allocator.dupe(u8, observation);
    }
};

/// Registry for managing available tools
pub const ToolRegistry = struct {
    tools: std.StringHashMap(*Tool),
    allocator: Allocator,

    pub fn init(allocator: Allocator) ToolRegistry {
        return ToolRegistry{
            .tools = std.StringHashMap(*Tool).init(allocator),
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *ToolRegistry) void {
        var iter = self.tools.valueIterator();
        while (iter.next()) |tool| {
            tool.*.deinit();
        }
        self.tools.deinit();
    }

    pub fn register(self: *ToolRegistry, tool: *Tool) !void {
        // Check if tool already exists
        if (self.tools.contains(tool.name)) {
            return AgentError.InvalidInput;
        }
        try self.tools.put(tool.name, tool);
    }

    pub fn unregister(self: *ToolRegistry, name: []const u8) void {
        if (self.tools.fetchRemove(name)) |kv| {
            kv.value.deinit();
        }
    }

    pub fn getTool(self: *ToolRegistry, name: []const u8) ?*Tool {
        return self.tools.get(name);
    }

    pub fn listTools(self: *ToolRegistry, allocator: Allocator) ![][]const u8 {
        var list = std.ArrayList([]const u8){};
        errdefer list.deinit(allocator);

        var iter = self.tools.keyIterator();
        while (iter.next()) |key| {
            try list.append(allocator, try allocator.dupe(u8, key.*));
        }

        const result = try list.toOwnedSlice(allocator);
        return result;
    }

    pub fn getToolsDescription(self: *ToolRegistry, allocator: Allocator) ![]const u8 {
        if (self.tools.count() == 0) {
            return try allocator.dupe(u8, "No tools available.");
        }

        var buffer = std.ArrayList(u8){};
        defer buffer.deinit(allocator);

        try buffer.appendSlice(allocator, "Available tools:\n");

        var iter = self.tools.iterator();
        while (iter.next()) |entry| {
            const tool = entry.value_ptr.*;
            try buffer.appendSlice(allocator, "- ");
            try buffer.appendSlice(allocator, tool.name);
            try buffer.appendSlice(allocator, ": ");
            try buffer.appendSlice(allocator, tool.description);
            try buffer.appendSlice(allocator, "\n");
        }

        return try buffer.toOwnedSlice(allocator);
    }

    pub fn execute(self: *ToolRegistry, allocator: Allocator, tool_name: []const u8, input: []const u8) !ToolResult {
        const tool = self.getTool(tool_name);
        if (tool == null) {
            const error_msg = try std.fmt.allocPrint(allocator, "Tool '{s}' not found", .{tool_name});
            defer allocator.free(error_msg);
            return try ToolResult.initError(allocator, tool_name, error_msg);
        }

        const result = tool.?.execute(allocator, input) catch |err| {
            const error_msg = try std.fmt.allocPrint(allocator, "Tool execution failed: {s}", .{@errorName(err)});
            defer allocator.free(error_msg);
            return try ToolResult.initError(allocator, tool_name, error_msg);
        };
        defer allocator.free(result);

        return try ToolResult.initSuccess(allocator, tool_name, result);
    }
};

/// ReAct agent that reasons and acts using tools
pub const ReActAgent = struct {
    allocator: Allocator,
    tool_registry: *ToolRegistry,
    max_iterations: u32,
    system_prompt: []const u8,
    verbose: bool,
    steps: std.ArrayList(ReActStep),
    agent_name: []const u8,

    pub fn init(
        allocator: Allocator,
        tool_registry: *ToolRegistry,
        max_iterations: u32,
        verbose: bool,
    ) !*ReActAgent {
        const self = try allocator.create(ReActAgent);

        // Generate system prompt
        const tools_desc = try tool_registry.getToolsDescription(allocator);
        defer allocator.free(tools_desc);

        const system_prompt = try std.fmt.allocPrint(allocator,
            \\You are a helpful assistant that uses tools to answer questions.
            \\
            \\{s}
            \\
            \\You should use the following format:
            \\
            \\Thought: Think about what you need to do
            \\Action: The tool to use (or "Final Answer" if you can answer)
            \\Action Input: The input for the tool
            \\Observation: The result from the tool
            \\
            \\Repeat Thought/Action/Observation until you have enough information, then:
            \\
            \\Thought: I now know the final answer
            \\Action: Final Answer
            \\Action Input: [your final answer here]
            \\
            \\Begin!
        , .{tools_desc});

        self.* = ReActAgent{
            .allocator = allocator,
            .tool_registry = tool_registry,
            .max_iterations = max_iterations,
            .system_prompt = system_prompt,
            .verbose = verbose,
            .steps = .{},
            .agent_name = try allocator.dupe(u8, "ReActAgent"),
        };

        return self;
    }

    pub fn deinit(self: *ReActAgent) void {
        for (self.steps.items) |*step| {
            step.deinit();
        }
        self.steps.deinit(self.allocator);
        self.allocator.free(self.system_prompt);
        self.allocator.free(self.agent_name);
        self.allocator.destroy(self);
    }

    pub fn agent(self: *ReActAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .process = processImpl,
                .introspect = introspectImpl,
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = [_][]const u8{ "reasoning", "tool_use", "react_loop" };
        const result = try allocator.alloc([]const u8, caps.len);
        for (caps, 0..) |cap, i| {
            result[i] = try allocator.dupe(u8, cap);
        }
        return result;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *ReActAgent = @ptrCast(@alignCast(ptr));

        // Clear previous steps
        for (self.steps.items) |*step| {
            step.deinit();
        }
        self.steps.clearRetainingCapacity();

        // For this mock implementation, we'll simulate the ReAct loop
        // In production, this would call an LLM for each iteration
        const user_input = message.contentAsText() catch {
            return AgentError.InvalidInput;
        };

        // Simulate ReAct loop (simplified for demo)
        var iteration: u32 = 0;
        while (iteration < self.max_iterations) : (iteration += 1) {
            // In production: Call LLM with conversation history
            // For now, simulate parsing a response

            // Mock: Parse "thought, action, action_input" from a simulated LLM response
            const response = self.simulateLLMResponse(user_input, iteration) catch {
                return AgentError.ProcessingFailed;
            };
            defer self.allocator.free(response);

            const step_opt = self.parseResponse(response, iteration) catch null;
            if (step_opt) |step| {
                var step_mut = step;
                defer step_mut.deinit();

                // Check if final answer
                if (std.mem.eql(u8, step_mut.action, "Final Answer")) {
                    const final_msg = self.formatFinalResponse(step_mut.action_input) catch {
                        return AgentError.ProcessingFailed;
                    };
                    return Result{ .ok = final_msg };
                }

                // Execute tool
                var tool_result = self.tool_registry.execute(self.allocator, step_mut.action, step_mut.action_input) catch {
                    return AgentError.ProcessingFailed;
                };
                defer tool_result.deinit();

                const observation = if (tool_result.success)
                    tool_result.result.?
                else
                    tool_result.error_msg.?;

                // Store step with observation
                var stored_step = ReActStep.init(self.allocator, step_mut.thought, step_mut.action, step_mut.action_input, iteration) catch {
                    return AgentError.ProcessingFailed;
                };
                stored_step.setObservation(observation) catch {
                    return AgentError.ProcessingFailed;
                };
                self.steps.append(self.allocator, stored_step) catch {
                    return AgentError.ProcessingFailed;
                };
            }
        }

        // Max iterations reached
        const error_msg = self.allocator.dupe(u8, "Max iterations reached without finding answer") catch {
            return AgentError.ProcessingFailed;
        };
        const msg = Message.withText(self.allocator, .assistant, error_msg) catch {
            return AgentError.ProcessingFailed;
        };
        return Result{ .ok = msg };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *ReActAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
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
        const self: *ReActAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    fn simulateLLMResponse(self: *ReActAgent, input: []const u8, iteration: u32) ![]const u8 {
        // Mock LLM response for testing
        // In production, this would call actual LLM
        _ = input;

        if (iteration == 0) {
            return try std.fmt.allocPrint(self.allocator,
                \\Thought: I need to calculate something
                \\Action: calculator
                \\Action Input: 2+2
            , .{});
        } else {
            return try std.fmt.allocPrint(self.allocator,
                \\Thought: I have the answer
                \\Action: Final Answer
                \\Action Input: The answer is 4
            , .{});
        }
    }

    fn parseResponse(self: *ReActAgent, response: []const u8, step_number: u32) !?ReActStep {
        var thought: []const u8 = "";
        var action: []const u8 = "";
        var action_input: []const u8 = "";

        // Parse line by line
        var lines = std.mem.splitScalar(u8, response, '\n');
        while (lines.next()) |line| {
            const trimmed = std.mem.trim(u8, line, " \t\r");
            if (trimmed.len == 0) continue;

            if (std.mem.startsWith(u8, trimmed, "Thought:")) {
                thought = std.mem.trim(u8, trimmed[8..], " ");
            } else if (std.mem.startsWith(u8, trimmed, "Action:")) {
                action = std.mem.trim(u8, trimmed[7..], " ");
            } else if (std.mem.startsWith(u8, trimmed, "Action Input:")) {
                action_input = std.mem.trim(u8, trimmed[13..], " ");
            }
        }

        if (action.len == 0) {
            return null;
        }

        return try ReActStep.init(self.allocator, thought, action, action_input, step_number);
    }

    fn formatFinalResponse(self: *ReActAgent, answer: []const u8) !Message {
        if (self.verbose) {
            // Include thought process
            var buffer = std.ArrayList(u8){};
            defer buffer.deinit(self.allocator);

            for (self.steps.items, 0..) |step, i| {
                const step_header = try std.fmt.allocPrint(self.allocator, "Step {d}:\n", .{i + 1});
                defer self.allocator.free(step_header);
                try buffer.appendSlice(self.allocator, step_header);
                try buffer.appendSlice(self.allocator, "Thought: ");
                try buffer.appendSlice(self.allocator, step.thought);
                try buffer.appendSlice(self.allocator, "\nAction: ");
                try buffer.appendSlice(self.allocator, step.action);
                try buffer.appendSlice(self.allocator, "\nObservation: ");
                try buffer.appendSlice(self.allocator, step.observation);
                try buffer.appendSlice(self.allocator, "\n\n");
            }

            try buffer.appendSlice(self.allocator, "Final Answer: ");
            try buffer.appendSlice(self.allocator, answer);

            return try Message.withText(self.allocator, .assistant, buffer.items);
        } else {
            return try Message.withText(self.allocator, .assistant, answer);
        }
    }

    pub fn getSteps(self: *ReActAgent, allocator: Allocator) ![]ReActStep {
        var steps = try allocator.alloc(ReActStep, self.steps.items.len);
        for (self.steps.items, 0..) |step, i| {
            steps[i] = try ReActStep.init(allocator, step.thought, step.action, step.action_input, step.step_number);
            try steps[i].setObservation(step.observation);
        }
        return steps;
    }

    pub fn clearSteps(self: *ReActAgent) void {
        for (self.steps.items) |*step| {
            step.deinit();
        }
        self.steps.clearRetainingCapacity();
    }
};

// Tests
test "Tool creation and execution" {
    const allocator = std.testing.allocator;

    // Create a simple calculator tool
    const calculator_fn = struct {
        fn execute(alloc: Allocator, input: []const u8) AgentError![]const u8 {
            _ = input;
            return alloc.dupe(u8, "4") catch {
                return AgentError.ProcessingFailed;
            };
        }
    }.execute;

    var tool = try Tool.init(allocator, "calculator", "Performs calculations", calculator_fn);
    defer tool.deinit();

    const result = try tool.execute(allocator, "2+2");
    defer allocator.free(result);

    try std.testing.expectEqualStrings("4", result);
}

test "ToolRegistry register and execute" {
    const allocator = std.testing.allocator;

    var registry = ToolRegistry.init(allocator);
    defer registry.deinit();

    const calculator_fn = struct {
        fn execute(alloc: Allocator, input: []const u8) AgentError![]const u8 {
            _ = input;
            return alloc.dupe(u8, "42") catch {
                return AgentError.ProcessingFailed;
            };
        }
    }.execute;

    const tool = try Tool.init(allocator, "test_tool", "Test tool", calculator_fn);
    try registry.register(tool);

    var result = try registry.execute(allocator, "test_tool", "input");
    defer result.deinit();

    try std.testing.expect(result.success);
    try std.testing.expectEqualStrings("42", result.result.?);
}

test "ToolRegistry tool not found" {
    const allocator = std.testing.allocator;

    var registry = ToolRegistry.init(allocator);
    defer registry.deinit();

    var result = try registry.execute(allocator, "nonexistent", "input");
    defer result.deinit();

    try std.testing.expect(!result.success);
}

test "ReActStep creation" {
    const allocator = std.testing.allocator;

    var step = try ReActStep.init(allocator, "I need to calculate", "calculator", "2+2", 0);
    defer step.deinit();

    try std.testing.expectEqualStrings("I need to calculate", step.thought);
    try std.testing.expectEqualStrings("calculator", step.action);
    try std.testing.expectEqualStrings("2+2", step.action_input);
    try std.testing.expectEqual(@as(u32, 0), step.step_number);
}

test "ReActAgent creation and basic flow" {
    const allocator = std.testing.allocator;

    var registry = ToolRegistry.init(allocator);
    defer registry.deinit();

    // Add calculator tool
    const calculator_fn = struct {
        fn execute(alloc: Allocator, input: []const u8) AgentError![]const u8 {
            _ = input;
            return alloc.dupe(u8, "4") catch {
                return AgentError.ProcessingFailed;
            };
        }
    }.execute;

    const tool = try Tool.init(allocator, "calculator", "Performs calculations", calculator_fn);
    try registry.register(tool);

    var react_agent = try ReActAgent.init(allocator, &registry, 5, false);
    defer react_agent.deinit();

    var msg = try Message.withText(allocator, .user, "What is 2+2?");
    defer msg.deinit();

    const result = try react_agent.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const content = try response.contentAsText();
    try std.testing.expect(content.len > 0);
}

test "ReActAgent verbose mode" {
    const allocator = std.testing.allocator;

    var registry = ToolRegistry.init(allocator);
    defer registry.deinit();

    const calculator_fn = struct {
        fn execute(alloc: Allocator, input: []const u8) AgentError![]const u8 {
            _ = input;
            return alloc.dupe(u8, "4") catch {
                return AgentError.ProcessingFailed;
            };
        }
    }.execute;

    const tool = try Tool.init(allocator, "calculator", "Performs calculations", calculator_fn);
    try registry.register(tool);

    const react_agent = try ReActAgent.init(allocator, &registry, 5, true); // verbose = true
    defer react_agent.deinit();

    var msg = try Message.withText(allocator, .user, "Calculate 2+2");
    defer msg.deinit();

    const result = try react_agent.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const content = try response.contentAsText();
    // Verbose mode should include "Step" in output
    try std.testing.expect(std.mem.indexOf(u8, content, "Step") != null);
}

//! Reasoning with Tools Pattern Example
//!
//! This example demonstrates the Reasoning with Tools pattern where agents can
//! use tools DURING reasoning (not just after), enabling extended thinking with
//! tool integration.
//!
//! Build: zig build
//! Run: zig build run-reasoning-with-tools

const std = @import("std");
const agenkit = @import("agenkit");

const Agent = agenkit.Agent;
const StreamCallbacks = agenkit.StreamCallbacks;
const AgentError = agenkit.AgentError;
const Message = agenkit.Message;
const Tool = agenkit.patterns.Tool;
const ReasoningWithToolsAgent = agenkit.patterns.ReasoningWithToolsAgent;
const ReasoningConfig = agenkit.patterns.ReasoningConfig;

/// Mock LLM agent that simulates reasoning responses
const MockLLMAgent = struct {
    allocator: std.mem.Allocator,
    name: []const u8,

    pub fn init(allocator: std.mem.Allocator, name: []const u8) !*MockLLMAgent {
        const self = try allocator.create(MockLLMAgent);
        self.* = .{
            .allocator = allocator,
            .name = try allocator.dupe(u8, name),
        };
        return self;
    }

    pub fn agent(self: *MockLLMAgent) Agent {
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
        const self: *MockLLMAgent = @ptrCast(@alignCast(ptr));
        return self.name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = try allocator.dupe(u8, "reasoning");
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) agenkit.AgentError!agenkit.Result {
        const self: *MockLLMAgent = @ptrCast(@alignCast(ptr));

        const content = message.contentAsText() catch return agenkit.AgentError.ProcessingFailed;

        // Simulate reasoning response
        const response = std.fmt.allocPrint(
            self.allocator,
            "I've analyzed: {s}\n\nBased on the available tools, I would:\n" ++
                "1. Break down the problem\n" ++
                "2. Use tools as needed for calculations/data\n" ++
                "3. Synthesize the final answer\n\n" ++
                "Conclusion: Problem analyzed with tool support available",
            .{content},
        ) catch return agenkit.AgentError.ProcessingFailed;
        defer self.allocator.free(response);

        const response_msg = Message.withText(
            self.allocator,
            .assistant,
            response,
        ) catch return agenkit.AgentError.ProcessingFailed;

        return agenkit.Result{ .ok = response_msg };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        const self: *MockLLMAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return agenkit.createDefaultIntrospectionResult(allocator, self.name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *MockLLMAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    pub fn deinit(self: *MockLLMAgent) void {
        self.allocator.free(self.name);
        self.allocator.destroy(self);
    }
};

/// Mock tool execute function
fn mockToolExecute(_: std.mem.Allocator, _: []const u8) agenkit.AgentError![]const u8 {
    return "42"; // Mock result
}


fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
    _ = ptr;
    _ = message;
    callbacks.onError(AgentError.NotImplemented);
}
pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Reasoning with Tools Pattern Example ===\n\n", .{});

    // ========================================================================
    // Example 1: Basic Reasoning with Tool Support
    // ========================================================================
    std.debug.print("Example 1: Basic Reasoning with Tool Support\n", .{});
    std.debug.print("----------------------------------------------\n", .{});

    // Create mock LLM
    var llm = try MockLLMAgent.init(allocator, "MockLLM");
    defer llm.deinit();

    // Create tools (using inline struct initialization)
    var tools = std.StringHashMap(Tool).init(allocator);
    defer {
        var it = tools.valueIterator();
        while (it.next()) |tool_ptr| {
            allocator.free(tool_ptr.name);
            allocator.free(tool_ptr.description);
        }
        tools.deinit();
    }

    const calc_tool = Tool{
        .name = try allocator.dupe(u8, "calculator"),
        .description = try allocator.dupe(u8, "Performs mathematical calculations"),
        .execute_fn = mockToolExecute,
        .allocator = allocator,
    };
    try tools.put("calculator", calc_tool);

    const search_tool = Tool{
        .name = try allocator.dupe(u8, "search"),
        .description = try allocator.dupe(u8, "Searches for information"),
        .execute_fn = mockToolExecute,
        .allocator = allocator,
    };
    try tools.put("search", search_tool);

    // Create reasoning agent
    const config = ReasoningConfig{
        .max_steps = 10,
        .enable_trace = true,
        .confidence_threshold = 0.8,
    };

    var reasoning_agent = try ReasoningWithToolsAgent.init(
        allocator,
        llm.agent(),
        tools,
        config,
        "ReasoningAgent",
    );
    defer reasoning_agent.deinit();

    std.debug.print("\nAgent: {s}\n", .{reasoning_agent.agent().name()});
    std.debug.print("Tools available: calculator, search\n", .{});
    std.debug.print("Max steps: {d}\n", .{config.max_steps});

    std.debug.print("\nInput: What is 15 * 23 + 47?\n", .{});
    std.debug.print("Expected: Agent reasons about math problem with calculator support\n\n", .{});

    var msg1 = try Message.withText(allocator, .user, "What is 15 * 23 + 47?");
    defer msg1.deinit();

    const result1 = reasoning_agent.agent().process(msg1) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return;
    };

    switch (result1) {
        .ok => |response| {
            var mutable_response = response;
            defer mutable_response.deinit();
            const response_text = mutable_response.contentAsText() catch "No content";
            std.debug.print("Response:\n{s}\n", .{response_text});
        },
        .err => |e| {
            std.debug.print("Error: {}\n", .{e});
        },
    }

    // ========================================================================
    // Example 2: Complex Multi-Step Reasoning
    // ========================================================================
    std.debug.print("\n\nExample 2: Complex Multi-Step Reasoning\n", .{});
    std.debug.print("----------------------------------------\n", .{});

    const database_tool = Tool{
        .name = try allocator.dupe(u8, "database"),
        .description = try allocator.dupe(u8, "Queries database for information"),
        .execute_fn = mockToolExecute,
        .allocator = allocator,
    };

    var tools2 = std.StringHashMap(Tool).init(allocator);
    defer {
        // Only free database_tool since calc_tool and search_tool will be freed by tools defer
        allocator.free(database_tool.name);
        allocator.free(database_tool.description);
        tools2.deinit();
    }
    try tools2.put("calculator", calc_tool);
    try tools2.put("search", search_tool);
    try tools2.put("database", database_tool);

    var reasoning_agent2 = try ReasoningWithToolsAgent.init(
        allocator,
        llm.agent(),
        tools2,
        config,
        "AdvancedReasoning",
    );
    defer reasoning_agent2.deinit();

    std.debug.print("\nTools available: calculator, search, database\n", .{});
    std.debug.print("\nInput: Research quantum computing and calculate market growth\n", .{});
    std.debug.print("Expected: Agent interleaves research (search/database) with\n", .{});
    std.debug.print("          calculation (calculator) during reasoning\n\n", .{});

    var msg2 = try Message.withText(
        allocator,
        .user,
        "Research quantum computing trends and calculate projected market growth",
    );
    defer msg2.deinit();

    const result2 = reasoning_agent2.agent().process(msg2) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        std.debug.print("\n=== Reasoning with Tools Pattern Complete ===\n\n", .{});
        return;
    };

    switch (result2) {
        .ok => |response| {
            var mutable_response = response;
            defer mutable_response.deinit();
            const response_text = mutable_response.contentAsText() catch "No content";
            std.debug.print("Response:\n{s}\n", .{response_text});
        },
        .err => |e| {
            std.debug.print("Error: {}\n", .{e});
        },
    }

    // ========================================================================
    // Summary
    // ========================================================================
    std.debug.print("\n\n=== Reasoning with Tools Pattern Summary ===\n", .{});
    std.debug.print("✓ Tools available during reasoning (not just after)\n", .{});
    std.debug.print("✓ Agent can refine thinking with real-time information\n", .{});
    std.debug.print("✓ Supports extended thinking with tool integration\n", .{});
    std.debug.print("✓ Different from ReAct (interleaved vs sequential)\n", .{});
    std.debug.print("✓ Useful for: complex problems, research, calculations\n", .{});
    std.debug.print("\n✓ Reasoning with Tools pattern example completed!\n\n", .{});
}

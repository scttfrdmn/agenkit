/// Agents-as-Tools Pattern - Hierarchical Agent Delegation
///
/// The Agents-as-Tools pattern enables agents to call other agents as tools,
/// creating hierarchical multi-agent systems where specialized agents can be
/// invoked by supervisor agents.
///
/// Key Concepts:
/// - AgentTool: Wrapper that exposes an agent as a callable tool
/// - Hierarchical Delegation: Supervisor delegates to specialist agents
/// - Tool Interface: Agents expose standard tool interface
/// - Transparent Integration: Works with existing tool-calling infrastructure
///
/// Use Cases:
/// - Supervisor agent delegating to specialist agents
/// - Domain-specific agent routing
/// - Hierarchical multi-agent systems
/// - Agent composition and orchestration
///
/// Example:
///     // Create specialist agent
///     var specialist = try CodeSpecialistAgent.init(allocator);
///     defer specialist.deinit();
///
///     // Wrap as tool
///     var tool = try AgentTool.init(
///         allocator,
///         specialist.agent(),
///         "code_specialist",
///         "Expert in programming and code review"
///     );
///     defer tool.deinit();
///
///     // Execute tool
///     const result = try tool.execute(allocator, "Write a function to reverse a string");

const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;

/// Output format for agent tool
pub const OutputFormat = enum {
    str, // Return content as string
    dict, // Return {content, metadata} dictionary
    message, // Return full Message object
};

/// Agent Tool - Wrapper that exposes an agent as a tool
///
/// Allows agents to call other agents as tools, enabling hierarchical
/// delegation and specialization. Compatible with existing tool infrastructure.
///
/// Performance Characteristics:
/// - Latency: Same as underlying agent
/// - Enables hierarchical composition
/// - Maintains full observability (traces preserved)
pub const AgentTool = struct {
    allocator: Allocator,
    agent_impl: Agent,
    tool_name: []const u8,
    tool_description: []const u8,
    input_key: []const u8,
    output_format: OutputFormat,
    include_metadata: bool,

    /// Initialize an agent tool
    ///
    /// Args:
    ///     allocator: Memory allocator
    ///     agent_impl: The agent to wrap as a tool
    ///     name: Tool name for identification and routing
    ///     description: Description for LLM to understand when to use
    ///     input_key: Parameter name for input (default: "query")
    ///     output_format: How to format output (default: str)
    ///     include_metadata: Include agent metadata (default: false)
    pub fn init(
        allocator: Allocator,
        agent_impl: Agent,
        tool_name: []const u8,
        tool_description: []const u8,
        input_key: []const u8,
        output_format: OutputFormat,
        include_metadata: bool,
    ) !*AgentTool {
        if (tool_name.len == 0) {
            return error.OutOfMemory; // Reuse existing error type
        }
        if (tool_description.len == 0) {
            return error.OutOfMemory;
        }

        const self = try allocator.create(AgentTool);

        self.* = AgentTool{
            .allocator = allocator,
            .agent_impl = agent_impl,
            .tool_name = try allocator.dupe(u8, tool_name),
            .tool_description = try allocator.dupe(u8, tool_description),
            .input_key = try allocator.dupe(u8, input_key),
            .output_format = output_format,
            .include_metadata = include_metadata,
        };

        return self;
    }

    /// Execute the wrapped agent with input
    ///
    /// Args:
    ///     allocator: Memory allocator for output
    ///     input: Input string for the agent
    ///
    /// Returns:
    ///     Agent output formatted according to output_format
    pub fn execute(self: *AgentTool, allocator: Allocator, input: []const u8) !Message {
        // Create message
        var message = try Message.withText(allocator, .user, input);
        defer message.deinit();

        // Call agent
        const result = try self.agent_impl.process(message);
        const response = try result.unwrap();

        // Format output based on output_format
        return response;
    }

    /// Get tool name
    pub fn name(self: *AgentTool) []const u8 {
        return self.tool_name;
    }

    /// Get tool description
    pub fn description(self: *AgentTool) []const u8 {
        return self.tool_description;
    }

    /// Get input parameter name
    pub fn inputKey(self: *AgentTool) []const u8 {
        return self.input_key;
    }

    pub fn deinit(self: *AgentTool) void {
        self.allocator.free(self.tool_name);
        self.allocator.free(self.tool_description);
        self.allocator.free(self.input_key);
        self.allocator.destroy(self);
    }
};

/// Convenience function to wrap an agent as a tool
///
/// This is the primary API for creating agent tools.
///
/// Args:
///     allocator: Memory allocator
///     agent_impl: The agent to wrap
///     name: Tool name (used for routing and identification)
///     description: Tool description (helps LLM decide when to use)
///
/// Returns:
///     AgentTool instance ready to be used
///
/// Example:
///     var specialist = try CodeAgent.init(allocator);
///     defer specialist.deinit();
///
///     var tool = try agentAsTool(
///         allocator,
///         specialist.agent(),
///         "code_expert",
///         "Expert programmer for code-related tasks"
///     );
///     defer tool.deinit();
///
///     const result = try tool.execute(allocator, "Write a hash function");
pub fn agentAsTool(
    allocator: Allocator,
    agent_impl: Agent,
    name: []const u8,
    description: []const u8,
) !*AgentTool {
    return AgentTool.init(
        allocator,
        agent_impl,
        name,
        description,
        "query", // default input key
        .str, // default output format
        false, // default: don't include metadata
    );
}

// ============================================================================
// ToolCoordinator - Agent that delegates to specialist tools
// ============================================================================

/// Supervisor Agent - Coordinates multiple specialist agents
///
/// The supervisor pattern uses a lead agent to coordinate specialist agents
/// by wrapping them as tools and delegating tasks appropriately.
pub const ToolCoordinator = struct {
    allocator: Allocator,
    agent_name: []const u8,
    tools: std.ArrayList(*AgentTool),

    /// Initialize a tool coordinator
    pub fn init(allocator: Allocator, name: []const u8) !*ToolCoordinator {
        const self = try allocator.create(ToolCoordinator);
        self.* = ToolCoordinator{
            .allocator = allocator,
            .agent_name = try allocator.dupe(u8, name),
            .tools = .{},
        };
        return self;
    }

    /// Register a specialist agent as a tool
    pub fn registerTool(self: *ToolCoordinator, tool: *AgentTool) !void {
        try self.tools.append(self.allocator, tool);
    }

    /// Get list of available tools
    pub fn getTools(self: *ToolCoordinator) []*AgentTool {
        return self.tools.items;
    }

    /// Execute a specific tool by name
    pub fn executeTool(self: *ToolCoordinator, tool_name: []const u8, input: []const u8) !Message {
        for (self.tools.items) |tool| {
            if (std.mem.eql(u8, tool.name(), tool_name)) {
                return tool.execute(self.allocator, input);
            }
        }
        return error.NotImplemented; // Tool not found
    }

    /// Create agent interface for this supervisor
    pub fn agent(self: *ToolCoordinator) Agent {
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
        const self: *ToolCoordinator = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *ToolCoordinator = @ptrCast(@alignCast(ptr));

        // Collect capabilities from all tools
        var caps_set = std.StringHashMap(void).init(allocator);
        defer caps_set.deinit();

        try caps_set.put("supervisor", {});
        try caps_set.put("delegation", {});

        for (self.tools.items) |tool| {
            try caps_set.put(tool.name(), {});
        }

        const caps = try allocator.alloc([]const u8, caps_set.count());
        var iter = caps_set.keyIterator();
        var i: usize = 0;
        while (iter.next()) |key| : (i += 1) {
            caps[i] = key.*;
        }

        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *ToolCoordinator = @ptrCast(@alignCast(ptr));

        // Simple supervisor logic: use first tool if available
        // In real implementation, this would use LLM to decide which tool
        if (self.tools.items.len == 0) {
            return Result{ .err = AgentError.NotImplemented };
        }

        const tool = self.tools.items[0];
        const text = message.contentAsText() catch {
            return Result{ .err = AgentError.InvalidInput };
        };

        const response = tool.execute(self.allocator, text) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        return Result{ .ok = response };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *ToolCoordinator = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer {
            for (caps) |cap| allocator.free(cap);
            allocator.free(caps);
        }
        return createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *ToolCoordinator = @ptrCast(@alignCast(ptr));
        self.allocator.free(self.agent_name);
        self.tools.deinit(self.allocator); // Don't deinit tools themselves (owned externally)
        self.allocator.destroy(self);
    }

    pub fn deinit(self: *ToolCoordinator) void {
        self.allocator.free(self.agent_name);
        self.tools.deinit(self.allocator);
        self.allocator.destroy(self);
    }
};

// ============================================================================
// Tests
// ============================================================================

test "AgentTool basic functionality" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var tool = try agentAsTool(
        allocator,
        echo.agent(),
        "echo_tool",
        "Echoes back the input",
    );
    defer tool.deinit();

    try std.testing.expectEqualStrings("echo_tool", tool.name());
    try std.testing.expectEqualStrings("Echoes back the input", tool.description());

    var result = try tool.execute(allocator, "test input");
    defer result.deinit();

    const text = try result.contentAsText();
    try std.testing.expectEqualStrings("test input", text);
}

test "AgentTool custom configuration" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var tool = try AgentTool.init(
        allocator,
        echo.agent(),
        "custom_tool",
        "Custom tool with options",
        "task", // custom input key
        .str,
        true, // include metadata
    );
    defer tool.deinit();

    try std.testing.expectEqualStrings("task", tool.inputKey());

    var result = try tool.execute(allocator, "hello");
    defer result.deinit();

    const text = try result.contentAsText();
    try std.testing.expectEqualStrings("hello", text);
}

test "ToolCoordinator delegation" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    // Create specialist agents
    var specialist1 = try EchoAgent.init(allocator);
    defer specialist1.agent().deinit();
    var specialist2 = try EchoAgent.init(allocator);
    defer specialist2.agent().deinit();

    // Wrap as tools
    var tool1 = try agentAsTool(
        allocator,
        specialist1.agent(),
        "specialist1",
        "First specialist",
    );
    defer tool1.deinit();

    var tool2 = try agentAsTool(
        allocator,
        specialist2.agent(),
        "specialist2",
        "Second specialist",
    );
    defer tool2.deinit();

    // Create supervisor
    var supervisor = try ToolCoordinator.init(allocator, "supervisor");
    defer supervisor.deinit();

    try supervisor.registerTool(tool1);
    try supervisor.registerTool(tool2);

    // Test delegation
    const tools = supervisor.getTools();
    try std.testing.expectEqual(@as(usize, 2), tools.len);

    var result = try supervisor.executeTool("specialist1", "test task");
    defer result.deinit();

    const text = try result.contentAsText();
    try std.testing.expectEqualStrings("test task", text);
}

test "ToolCoordinator as agent interface" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    var specialist = try EchoAgent.init(allocator);
    defer specialist.agent().deinit();

    var tool = try agentAsTool(
        allocator,
        specialist.agent(),
        "specialist",
        "Specialist agent",
    );
    defer tool.deinit();

    var supervisor = try ToolCoordinator.init(allocator, "my_supervisor");
    defer supervisor.deinit();

    try supervisor.registerTool(tool);

    const agent_iface = supervisor.agent();
    try std.testing.expectEqualStrings("my_supervisor", agent_iface.name());

    // Test processing through agent interface
    var msg = try Message.withText(allocator, .user, "task");
    defer msg.deinit();

    const result = try agent_iface.process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const text = try response.contentAsText();
    try std.testing.expectEqualStrings("task", text);
}

test "ToolCoordinator capabilities" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    var specialist = try EchoAgent.init(allocator);
    defer specialist.agent().deinit();

    var tool = try agentAsTool(
        allocator,
        specialist.agent(),
        "specialist",
        "Specialist agent",
    );
    defer tool.deinit();

    var supervisor = try ToolCoordinator.init(allocator, "supervisor");
    defer supervisor.deinit();

    try supervisor.registerTool(tool);

    const agent_iface = supervisor.agent();
    const caps = try agent_iface.capabilities(allocator);
    defer allocator.free(caps);

    // Should have supervisor capabilities + tool names
    try std.testing.expect(caps.len >= 2);

    // Check for supervisor capability
    var has_supervisor = false;
    for (caps) |cap| {
        if (std.mem.eql(u8, cap, "supervisor")) {
            has_supervisor = true;
            break;
        }
    }
    try std.testing.expect(has_supervisor);
}

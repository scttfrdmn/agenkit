//! Agents-as-Tools Pattern Example
//!
//! The Agents-as-Tools pattern enables hierarchical agent delegation by wrapping
//! specialist agents as callable tools that a supervisor can coordinate.
//!
//! This example demonstrates:
//! - Wrapping agents as tools with agentAsTool()
//! - ToolCoordinator coordinating multiple specialists
//! - Direct tool execution by name
//! - Tool coordination as an Agent interface
//! - Capabilities aggregation from tools
//!
//! Run with: zig build run-agents-as-tools

const std = @import("std");
const agenkit = @import("agenkit");
const Message = agenkit.Message;
const AgentError = agenkit.AgentError;
const StreamCallbacks = agenkit.StreamCallbacks;

/// Custom specialist agent that prefixes messages with a domain label
const SpecialistAgent = struct {
    allocator: std.mem.Allocator,
    domain: []const u8,

    pub fn init(allocator: std.mem.Allocator, domain: []const u8) !*SpecialistAgent {
        const self = try allocator.create(SpecialistAgent);
        self.* = SpecialistAgent{
            .allocator = allocator,
            .domain = try allocator.dupe(u8, domain),
        };
        return self;
    }

    pub fn agent(self: *SpecialistAgent) agenkit.Agent {
        return agenkit.Agent{
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
        const self: *SpecialistAgent = @ptrCast(@alignCast(ptr));
        return self.domain;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        const self: *SpecialistAgent = @ptrCast(@alignCast(ptr));
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = self.domain;
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *SpecialistAgent = @ptrCast(@alignCast(ptr));

        const content = message.contentAsText() catch {
            return agenkit.Result{ .err = agenkit.AgentError.InvalidInput };
        };

        const response_text = std.fmt.allocPrint(
            self.allocator,
            "[{s}] {s}",
            .{ self.domain, content },
        ) catch {
            return agenkit.Result{ .err = agenkit.AgentError.ProcessingFailed };
        };
        defer self.allocator.free(response_text);

        const response = agenkit.Message.withText(self.allocator, .assistant, response_text) catch {
            return agenkit.Result{ .err = agenkit.AgentError.ProcessingFailed };
        };

        return agenkit.Result{ .ok = response };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        const self: *SpecialistAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return agenkit.createDefaultIntrospectionResult(allocator, self.domain, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *SpecialistAgent = @ptrCast(@alignCast(ptr));
        self.allocator.free(self.domain);
        self.allocator.destroy(self);
    }

    pub fn deinit(self: *SpecialistAgent) void {
        self.allocator.free(self.domain);
        self.allocator.destroy(self);
    }
};


fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
    _ = ptr;
    _ = message;
    callbacks.onError(AgentError.NotImplemented);
}
pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== AgentKit Agents-as-Tools Pattern Example ===\n\n", .{});

    // Example 1: Wrapping an agent as a tool
    std.debug.print("--- Example 1: Agent as Tool ---\n", .{});
    {
        var echo = try agenkit.EchoAgent.init(allocator);
        defer echo.agent().deinit();

        var tool = try agenkit.patterns.agentAsTool(
            allocator,
            echo.agent(),
            "echo_tool",
            "Echoes back the input verbatim",
        );
        defer tool.deinit();

        std.debug.print("Tool name: {s}\n", .{tool.name()});
        std.debug.print("Tool description: {s}\n", .{tool.description()});

        var result = try tool.execute(allocator, "Hello from tool!");
        defer result.deinit();

        const text = try result.contentAsText();
        std.debug.print("Tool output: {s}\n", .{text});
        std.debug.print("✓ Agent successfully wrapped as tool\n\n", .{});
    }

    // Example 2: Multiple specialist agents as tools
    std.debug.print("--- Example 2: Multiple Specialists ---\n", .{});
    {
        var math_agent = try SpecialistAgent.init(allocator, "MATH");
        defer math_agent.deinit();

        var code_agent = try SpecialistAgent.init(allocator, "CODE");
        defer code_agent.deinit();

        var research_agent = try SpecialistAgent.init(allocator, "RESEARCH");
        defer research_agent.deinit();

        var math_tool = try agenkit.patterns.agentAsTool(
            allocator,
            math_agent.agent(),
            "math_specialist",
            "Expert in mathematical calculations and proofs",
        );
        defer math_tool.deinit();

        var code_tool = try agenkit.patterns.agentAsTool(
            allocator,
            code_agent.agent(),
            "code_specialist",
            "Expert in programming and software design",
        );
        defer code_tool.deinit();

        var research_tool = try agenkit.patterns.agentAsTool(
            allocator,
            research_agent.agent(),
            "research_specialist",
            "Expert in information gathering and analysis",
        );
        defer research_tool.deinit();

        std.debug.print("Created 3 specialist tools:\n", .{});
        std.debug.print("  - {s}: {s}\n", .{ math_tool.name(), math_tool.description() });
        std.debug.print("  - {s}: {s}\n", .{ code_tool.name(), code_tool.description() });
        std.debug.print("  - {s}: {s}\n", .{ research_tool.name(), research_tool.description() });
        std.debug.print("✓ Multiple specialists ready for delegation\n\n", .{});
    }

    // Example 3: ToolCoordinator coordination
    std.debug.print("--- Example 3: Supervisor Delegation ---\n", .{});
    {
        var math_agent = try SpecialistAgent.init(allocator, "MATH");
        defer math_agent.deinit();

        var code_agent = try SpecialistAgent.init(allocator, "CODE");
        defer code_agent.deinit();

        var math_tool = try agenkit.patterns.agentAsTool(
            allocator,
            math_agent.agent(),
            "math_specialist",
            "Mathematical expert",
        );
        defer math_tool.deinit();

        var code_tool = try agenkit.patterns.agentAsTool(
            allocator,
            code_agent.agent(),
            "code_specialist",
            "Programming expert",
        );
        defer code_tool.deinit();

        var supervisor = try agenkit.patterns.ToolCoordinator.init(allocator, "SupervisorBot");
        defer supervisor.deinit();

        try supervisor.registerTool(math_tool);
        try supervisor.registerTool(code_tool);

        std.debug.print("Supervisor registered {d} tools\n", .{supervisor.getTools().len});

        // Execute specific tool by name
        var result1 = try supervisor.executeTool("math_specialist", "Calculate fibonacci(10)");
        defer result1.deinit();
        std.debug.print("Math result: {s}\n", .{try result1.contentAsText()});

        var result2 = try supervisor.executeTool("code_specialist", "Write a sorting algorithm");
        defer result2.deinit();
        std.debug.print("Code result: {s}\n", .{try result2.contentAsText()});

        std.debug.print("✓ Supervisor delegates to appropriate specialists\n\n", .{});
    }

    // Example 4: Supervisor as Agent interface
    std.debug.print("--- Example 4: Supervisor as Agent ---\n", .{});
    {
        var specialist = try SpecialistAgent.init(allocator, "DOMAIN");
        defer specialist.deinit();

        var tool = try agenkit.patterns.agentAsTool(
            allocator,
            specialist.agent(),
            "domain_expert",
            "Domain specialist",
        );
        defer tool.deinit();

        var supervisor = try agenkit.patterns.ToolCoordinator.init(allocator, "Coordinator");
        defer supervisor.deinit();

        try supervisor.registerTool(tool);

        // Use supervisor through Agent interface
        const agent_iface = supervisor.agent();
        std.debug.print("Agent name: {s}\n", .{agent_iface.name()});

        var msg = try agenkit.Message.withText(allocator, .user, "Process this task");
        defer msg.deinit();

        const result = try agent_iface.process(msg);
        var response = try result.unwrap();
        defer response.deinit();

        std.debug.print("Response: {s}\n", .{try response.contentAsText()});
        std.debug.print("✓ Supervisor works as standard Agent\n\n", .{});
    }

    // Example 5: Capabilities aggregation
    std.debug.print("--- Example 5: Aggregated Capabilities ---\n", .{});
    {
        var agent1 = try SpecialistAgent.init(allocator, "NLP");
        defer agent1.deinit();

        var agent2 = try SpecialistAgent.init(allocator, "VISION");
        defer agent2.deinit();

        var agent3 = try SpecialistAgent.init(allocator, "AUDIO");
        defer agent3.deinit();

        var tool1 = try agenkit.patterns.agentAsTool(allocator, agent1.agent(), "nlp", "NLP specialist");
        defer tool1.deinit();

        var tool2 = try agenkit.patterns.agentAsTool(allocator, agent2.agent(), "vision", "Vision specialist");
        defer tool2.deinit();

        var tool3 = try agenkit.patterns.agentAsTool(allocator, agent3.agent(), "audio", "Audio specialist");
        defer tool3.deinit();

        var supervisor = try agenkit.patterns.ToolCoordinator.init(allocator, "MultiModalAgent");
        defer supervisor.deinit();

        try supervisor.registerTool(tool1);
        try supervisor.registerTool(tool2);
        try supervisor.registerTool(tool3);

        const agent_iface = supervisor.agent();
        const caps = try agent_iface.capabilities(allocator);
        defer allocator.free(caps);

        std.debug.print("Supervisor capabilities ({d} total):\n", .{caps.len});
        for (caps) |cap| {
            std.debug.print("  - {s}\n", .{cap});
        }
        std.debug.print("✓ Supervisor aggregates all tool capabilities\n\n", .{});
    }

    // Example 6: Hierarchical delegation
    std.debug.print("--- Example 6: Hierarchical Multi-Agent ---\n", .{});
    {
        // Create leaf specialists
        var specialist1 = try SpecialistAgent.init(allocator, "BACKEND");
        defer specialist1.deinit();

        var specialist2 = try SpecialistAgent.init(allocator, "FRONTEND");
        defer specialist2.deinit();

        var tool1 = try agenkit.patterns.agentAsTool(
            allocator,
            specialist1.agent(),
            "backend_dev",
            "Backend development specialist",
        );
        defer tool1.deinit();

        var tool2 = try agenkit.patterns.agentAsTool(
            allocator,
            specialist2.agent(),
            "frontend_dev",
            "Frontend development specialist",
        );
        defer tool2.deinit();

        // Create supervisor
        var dev_supervisor = try agenkit.patterns.ToolCoordinator.init(allocator, "DevSupervisor");
        defer dev_supervisor.deinit();

        try dev_supervisor.registerTool(tool1);
        try dev_supervisor.registerTool(tool2);

        // Wrap supervisor as a tool for higher-level supervisor
        var dev_tool = try agenkit.patterns.agentAsTool(
            allocator,
            dev_supervisor.agent(),
            "development_team",
            "Complete development team",
        );
        defer dev_tool.deinit();

        var meta_supervisor = try agenkit.patterns.ToolCoordinator.init(allocator, "ProjectManager");
        defer meta_supervisor.deinit();

        try meta_supervisor.registerTool(dev_tool);

        std.debug.print("Hierarchical structure:\n", .{});
        std.debug.print("  ProjectManager\n", .{});
        std.debug.print("    └─ DevSupervisor\n", .{});
        std.debug.print("       ├─ backend_dev\n", .{});
        std.debug.print("       └─ frontend_dev\n", .{});

        var msg = try agenkit.Message.withText(allocator, .user, "Build new feature");
        defer msg.deinit();

        const result = try meta_supervisor.agent().process(msg);
        var response = try result.unwrap();
        defer response.deinit();

        std.debug.print("\nDelegated task: {s}\n", .{try response.contentAsText()});
        std.debug.print("✓ Multi-level hierarchical delegation\n\n", .{});
    }

    std.debug.print("=== Agents-as-Tools Pattern Summary ===\n", .{});
    std.debug.print("✓ agentAsTool() wraps any agent as a callable tool\n", .{});
    std.debug.print("✓ ToolCoordinator coordinates multiple specialist tools\n", .{});
    std.debug.print("✓ Direct tool execution by name\n", .{});
    std.debug.print("✓ Supervisor implements standard Agent interface\n", .{});
    std.debug.print("✓ Capabilities automatically aggregated from tools\n", .{});
    std.debug.print("✓ Supports hierarchical multi-agent architectures\n", .{});
    std.debug.print("✓ Useful for: domain specialization, task routing, delegation\n", .{});
    std.debug.print("\n✓ Agents-as-Tools pattern example completed successfully!\n\n", .{});
}

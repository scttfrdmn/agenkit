//! ReAct (Reasoning + Acting) Pattern Example
//!
//! The ReAct pattern implements iterative reasoning and tool execution where agents
//! alternate between thinking about what to do and acting with tools.
//!
//! This example demonstrates:
//! - Tool creation with execute functions
//! - ToolRegistry for managing available tools
//! - ReActAgent reasoning loop (Thought → Action → Observation)
//! - Tool execution and result handling
//! - Multi-step problem solving with tools
//!
//! Run with: zig build run-react

const std = @import("std");
const agenkit = @import("agenkit");

// Example tool functions

fn calculatorTool(allocator: std.mem.Allocator, input: []const u8) agenkit.AgentError![]const u8 {
    // Simple calculator that evaluates basic expressions
    // For demo purposes, just return a mocked result
    _ = input;
    return std.fmt.allocPrint(allocator, "42", .{}) catch {
        return agenkit.AgentError.ProcessingFailed;
    };
}

fn searchTool(allocator: std.mem.Allocator, input: []const u8) agenkit.AgentError![]const u8 {
    // Mock search tool
    return std.fmt.allocPrint(allocator, "Search results for '{s}': Found 3 relevant documents", .{input}) catch {
        return agenkit.AgentError.ProcessingFailed;
    };
}

fn weatherTool(allocator: std.mem.Allocator, input: []const u8) agenkit.AgentError![]const u8 {
    // Mock weather API
    return std.fmt.allocPrint(allocator, "Weather in {s}: Sunny, 72°F", .{input}) catch {
        return agenkit.AgentError.ProcessingFailed;
    };
}

fn databaseTool(allocator: std.mem.Allocator, input: []const u8) agenkit.AgentError![]const u8 {
    // Mock database query
    return std.fmt.allocPrint(allocator, "Database query for '{s}': 5 records found", .{input}) catch {
        return agenkit.AgentError.ProcessingFailed;
    };
}

pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== AgentKit ReAct Pattern Example ===\n\n", .{});

    // Example 1: Single tool registration and execution
    std.debug.print("--- Example 1: Tool Registry Basics ---\n", .{});
    {
        var registry = agenkit.patterns.ToolRegistry.init(allocator);
        defer registry.deinit();

        const calc_tool = try agenkit.patterns.Tool.init(
            allocator,
            "calculator",
            "Performs mathematical calculations",
            calculatorTool,
        );
        // Tool is owned by registry, will be freed in registry.deinit()

        try registry.register(calc_tool);

        std.debug.print("Registered tool: calculator\n", .{});

        // Execute tool directly through registry
        var result = try registry.execute(allocator, "calculator", "2 + 2");
        defer result.deinit();

        if (result.success) {
            std.debug.print("Result: {s}\n", .{result.result.?});
        } else {
            std.debug.print("Error: {s}\n", .{result.error_msg.?});
        }

        std.debug.print("✓ Tool execution successful\n\n", .{});
    }

    // Example 2: Multiple tools
    std.debug.print("--- Example 2: Multiple Tool Registration ---\n", .{});
    {
        var registry = agenkit.patterns.ToolRegistry.init(allocator);
        defer registry.deinit();

        const calc_tool = try agenkit.patterns.Tool.init(allocator, "calculator", "Math calculations", calculatorTool);
        const search_tool = try agenkit.patterns.Tool.init(allocator, "search", "Search the web", searchTool);
        const weather_tool = try agenkit.patterns.Tool.init(allocator, "weather", "Get weather info", weatherTool);

        try registry.register(calc_tool);
        try registry.register(search_tool);
        try registry.register(weather_tool);

        const tool_list = try registry.listTools(allocator);
        defer {
            for (tool_list) |name| {
                allocator.free(name);
            }
            allocator.free(tool_list);
        }

        std.debug.print("Registered {d} tools:\n", .{tool_list.len});
        for (tool_list) |name| {
            std.debug.print("  - {s}\n", .{name});
        }

        const tools_desc = try registry.getToolsDescription(allocator);
        defer allocator.free(tools_desc);
        std.debug.print("\n{s}", .{tools_desc});

        std.debug.print("✓ Multiple tools registered\n\n", .{});
    }

    // Example 3: Tool execution with error handling
    std.debug.print("--- Example 3: Tool Execution & Errors ---\n", .{});
    {
        var registry = agenkit.patterns.ToolRegistry.init(allocator);
        defer registry.deinit();

        const calc_tool = try agenkit.patterns.Tool.init(allocator, "calculator", "Math operations", calculatorTool);
        try registry.register(calc_tool);

        // Successful execution
        var result1 = try registry.execute(allocator, "calculator", "10 * 5");
        defer result1.deinit();
        std.debug.print("Calculator: {s}\n", .{result1.result.?});

        // Error: tool not found
        var result2 = try registry.execute(allocator, "nonexistent", "input");
        defer result2.deinit();
        if (!result2.success) {
            std.debug.print("Expected error: {s}\n", .{result2.error_msg.?});
        }

        std.debug.print("✓ Error handling works correctly\n\n", .{});
    }

    // Example 4: ReActAgent with tools
    std.debug.print("--- Example 4: ReAct Agent (Simulated) ---\n", .{});
    {
        var registry = agenkit.patterns.ToolRegistry.init(allocator);
        defer registry.deinit();

        const search_tool = try agenkit.patterns.Tool.init(allocator, "search", "Search the web", searchTool);
        const db_tool = try agenkit.patterns.Tool.init(allocator, "database", "Query database", databaseTool);

        try registry.register(search_tool);
        try registry.register(db_tool);

        var react_agent = try agenkit.patterns.ReActAgent.init(
            allocator,
            &registry,
            5, // max_iterations
            true, // verbose
        );
        defer react_agent.deinit();

        std.debug.print("ReActAgent initialized with {d} tools\n", .{registry.tools.count()});
        std.debug.print("Max iterations: {d}\n", .{react_agent.max_iterations});
        std.debug.print("Verbose: {}\n", .{react_agent.verbose});

        // The agent would normally process a message and use tools automatically
        // For this example, we'll demonstrate the step structure
        var step = try agenkit.patterns.ReActStep.init(
            allocator,
            "I need to search for information about agents",
            "search",
            "AI agents",
            1,
        );
        defer step.deinit();

        try step.setObservation("Found 3 relevant documents about AI agents");

        std.debug.print("\nSimulated ReAct Step:\n", .{});
        std.debug.print("  Step: {d}\n", .{step.step_number});
        std.debug.print("  Thought: {s}\n", .{step.thought});
        std.debug.print("  Action: {s}\n", .{step.action});
        std.debug.print("  Action Input: {s}\n", .{step.action_input});
        std.debug.print("  Observation: {s}\n", .{step.observation});

        std.debug.print("✓ ReAct reasoning loop structure\n\n", .{});
    }

    // Example 5: ReActAgent through Agent interface
    std.debug.print("--- Example 5: ReAct as Standard Agent ---\n", .{});
    {
        var registry = agenkit.patterns.ToolRegistry.init(allocator);
        defer registry.deinit();

        const weather_tool = try agenkit.patterns.Tool.init(allocator, "weather", "Get weather", weatherTool);
        try registry.register(weather_tool);

        var react_agent = try agenkit.patterns.ReActAgent.init(allocator, &registry, 3, false);
        defer react_agent.deinit();

        const agent_iface = react_agent.agent();
        std.debug.print("Agent name: {s}\n", .{agent_iface.name()});

        const caps = try agent_iface.capabilities(allocator);
        defer {
            for (caps) |cap| {
                allocator.free(cap);
            }
            allocator.free(caps);
        }
        std.debug.print("Capabilities: {d}\n", .{caps.len});
        for (caps) |cap| {
            std.debug.print("  - {s}\n", .{cap});
        }

        // Note: Processing would require LLM integration to parse actions
        // For now, we demonstrate the interface is working
        std.debug.print("✓ ReActAgent implements Agent interface\n\n", .{});
    }

    // Example 6: Tool registry management
    std.debug.print("--- Example 6: Registry Management ---\n", .{});
    {
        var registry = agenkit.patterns.ToolRegistry.init(allocator);
        defer registry.deinit();

        const tool1 = try agenkit.patterns.Tool.init(allocator, "tool1", "First tool", calculatorTool);
        const tool2 = try agenkit.patterns.Tool.init(allocator, "tool2", "Second tool", searchTool);
        const tool3 = try agenkit.patterns.Tool.init(allocator, "tool3", "Third tool", weatherTool);

        try registry.register(tool1);
        try registry.register(tool2);
        try registry.register(tool3);

        std.debug.print("Registered 3 tools\n", .{});

        // Get specific tool
        const retrieved_tool = registry.getTool("tool2");
        if (retrieved_tool) |tool| {
            std.debug.print("Retrieved tool: {s} - {s}\n", .{ tool.name, tool.description });
        }

        // Unregister a tool
        registry.unregister("tool1");
        std.debug.print("Unregistered tool1\n", .{});

        const remaining = try registry.listTools(allocator);
        defer {
            for (remaining) |name| {
                allocator.free(name);
            }
            allocator.free(remaining);
        }

        std.debug.print("Remaining tools: {d}\n", .{remaining.len});
        std.debug.print("✓ Registry management complete\n\n", .{});
    }

    std.debug.print("=== ReAct Pattern Summary ===\n", .{});
    std.debug.print("✓ Tool: Wraps functions with name and description\n", .{});
    std.debug.print("✓ ToolRegistry: Manages tool registration and execution\n", .{});
    std.debug.print("✓ ToolResult: Captures success or error from execution\n", .{});
    std.debug.print("✓ ReActStep: Tracks Thought → Action → Observation cycle\n", .{});
    std.debug.print("✓ ReActAgent: Implements reasoning + acting loop\n", .{});
    std.debug.print("✓ Agent interface: Standard process() integration\n", .{});
    std.debug.print("✓ Useful for: tool-using agents, multi-step reasoning, LLM agents\n", .{});
    std.debug.print("\n✓ ReAct pattern example completed successfully!\n\n", .{});
}

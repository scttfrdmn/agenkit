/// Agenkit Zig Patterns Example
///
/// This example demonstrates the 4 critical patterns implemented in Zig:
/// 1. Sequential Pattern - Chain agents in a pipeline
/// 2. Parallel Pattern - Execute agents concurrently
/// 3. Reflection Pattern - Iterative self-improvement
/// 4. Agents-as-Tools Pattern - Hierarchical delegation
///
/// Build and run:
///     zig build example-patterns
///
const std = @import("std");
const agenkit = @import("agenkit");

// Import patterns
const SequentialPattern = agenkit.patterns.SequentialPattern;
const ParallelPattern = agenkit.patterns.ParallelPattern;
const defaultAggregator = agenkit.patterns.defaultAggregator;
const ReflectionAgent = agenkit.patterns.ReflectionAgent;
const AgentTool = agenkit.patterns.AgentTool;
const SupervisorAgent = agenkit.patterns.SupervisorAgent;
const agentAsTool = agenkit.patterns.agentAsTool;

const Agent = agenkit.Agent;
const Message = agenkit.Message;
const EchoAgent = agenkit.EchoAgent;

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Agenkit Zig Patterns Demo ===\n\n", .{});

    // Example 1: Sequential Pattern
    try sequentialExample(allocator);

    // Example 2: Parallel Pattern
    try parallelExample(allocator);

    // Example 3: Reflection Pattern
    try reflectionExample(allocator);

    // Example 4: Agents-as-Tools Pattern
    try agentsAsToolsExample(allocator);

    std.debug.print("\n=== All Examples Complete ===\n", .{});
}

fn sequentialExample(allocator: std.mem.Allocator) !void {
    std.debug.print("--- Sequential Pattern Example ---\n", .{});
    std.debug.print("Chaining agents in a pipeline: agent1 → agent2 → agent3\n\n", .{});

    // Create agents
    var echo1 = try EchoAgent.init(allocator);
    defer echo1.agent().deinit();
    var echo2 = try EchoAgent.init(allocator);
    defer echo2.agent().deinit();
    var echo3 = try EchoAgent.init(allocator);
    defer echo3.agent().deinit();

    // Create sequential pipeline
    const agents = [_]Agent{ echo1.agent(), echo2.agent(), echo3.agent() };
    var pipeline = try SequentialPattern.init(allocator, &agents, "demo_pipeline");
    defer pipeline.deinit();

    // Process message through pipeline
    var msg = try Message.withText(allocator, .user, "Hello from Sequential!");
    defer msg.deinit();

    std.debug.print("Input: {s}\n", .{try msg.contentAsText()});

    const result = try pipeline.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    std.debug.print("Output: {s}\n", .{try response.contentAsText()});
    std.debug.print("Pattern: {s}\n\n", .{pipeline.agent().name()});
}

fn parallelExample(allocator: std.mem.Allocator) !void {
    std.debug.print("--- Parallel Pattern Example ---\n", .{});
    std.debug.print("Executing agents concurrently and aggregating results\n\n", .{});

    // Create agents
    var echo1 = try EchoAgent.init(allocator);
    defer echo1.agent().deinit();
    var echo2 = try EchoAgent.init(allocator);
    defer echo2.agent().deinit();
    var echo3 = try EchoAgent.init(allocator);
    defer echo3.agent().deinit();

    // Create parallel pattern
    const agents = [_]Agent{ echo1.agent(), echo2.agent(), echo3.agent() };
    var parallel = try ParallelPattern.init(
        allocator,
        &agents,
        "demo_parallel",
        defaultAggregator,
    );
    defer parallel.deinit();

    // Process message in parallel
    var msg = try Message.withText(allocator, .user, "Hello from Parallel!");
    defer msg.deinit();

    std.debug.print("Input: {s}\n", .{try msg.contentAsText()});

    const result = try parallel.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    std.debug.print("Output: {s}\n", .{try response.contentAsText()});

    // Check parallel results metadata
    if (response.getMetadata("parallel_results_count")) |count| {
        std.debug.print("Parallel agents executed: {d}\n", .{count.integer});
    }
    std.debug.print("Pattern: {s}\n\n", .{parallel.agent().name()});
}

fn reflectionExample(allocator: std.mem.Allocator) !void {
    std.debug.print("--- Reflection Pattern Example ---\n", .{});
    std.debug.print("Iterative self-improvement with generator and critic\n\n", .{});

    // Create generator and critic (using echo agents for demo)
    var generator = try EchoAgent.init(allocator);
    defer generator.agent().deinit();
    var critic = try EchoAgent.init(allocator);
    defer critic.agent().deinit();

    // Create reflection agent
    var reflection = try ReflectionAgent.init(
        allocator,
        generator.agent(),
        critic.agent(),
        3, // max_iterations
        0.9, // quality_threshold
        0.05, // improvement_threshold
        .free_form,
        false,
    );
    defer reflection.deinit();

    // Process message with reflection
    var msg = try Message.withText(allocator, .user, "Generate and improve a solution");
    defer msg.deinit();

    std.debug.print("Input: {s}\n", .{try msg.contentAsText()});

    const result = try reflection.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    std.debug.print("Output: {s}\n", .{try response.contentAsText()});

    // Show reflection metadata
    if (response.getMetadata("reflection_iterations")) |iterations| {
        std.debug.print("Iterations completed: {d}\n", .{iterations.integer});
    }
    if (response.getMetadata("stop_reason")) |reason| {
        std.debug.print("Stop reason: {s}\n", .{reason.string});
    }
    std.debug.print("Pattern: {s}\n\n", .{reflection.agent().name()});
}

fn agentsAsToolsExample(allocator: std.mem.Allocator) !void {
    std.debug.print("--- Agents-as-Tools Pattern Example ---\n", .{});
    std.debug.print("Hierarchical delegation with supervisor and specialists\n\n", .{});

    // Create specialist agents
    var specialist1 = try EchoAgent.init(allocator);
    defer specialist1.agent().deinit();
    var specialist2 = try EchoAgent.init(allocator);
    defer specialist2.agent().deinit();

    // Wrap specialists as tools
    var tool1 = try agentAsTool(
        allocator,
        specialist1.agent(),
        "code_specialist",
        "Expert in code generation and review",
    );
    defer tool1.deinit();

    var tool2 = try agentAsTool(
        allocator,
        specialist2.agent(),
        "data_specialist",
        "Expert in data analysis",
    );
    defer tool2.deinit();

    // Create supervisor
    var supervisor = try SupervisorAgent.init(allocator, "supervisor");
    defer supervisor.deinit();

    try supervisor.registerTool(tool1);
    try supervisor.registerTool(tool2);

    // Execute task via supervisor
    var msg = try Message.withText(allocator, .user, "Analyze this data");
    defer msg.deinit();

    std.debug.print("Input: {s}\n", .{try msg.contentAsText()});

    const result = try supervisor.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    std.debug.print("Output: {s}\n", .{try response.contentAsText()});
    std.debug.print("Pattern: {s}\n", .{supervisor.agent().name()});
    std.debug.print("Tools available: {d}\n\n", .{supervisor.getTools().len});
}

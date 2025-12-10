//! Simple Workflow Example
//!
//! This example demonstrates:
//! - Sequential agent composition
//! - Multiple agents working together
//! - Result passing between agents
//! - Using the Sequential pattern
//! - Building agent pipelines
//!
//! Run with: zig build run-workflow

const std = @import("std");
const agenkit = @import("agenkit");

pub fn main() !void {
    // Initialize allocator
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== AgentKit Simple Workflow Example ===\n\n", .{});

    // Create three agents that will work in sequence
    std.debug.print("Creating agents...\n", .{});
    
    var agent1 = try agenkit.EchoAgent.init(allocator);
    defer agent1.agent().deinit();
    
    var agent2 = try agenkit.EchoAgent.init(allocator);
    defer agent2.agent().deinit();
    
    var agent3 = try agenkit.EchoAgent.init(allocator);
    defer agent3.agent().deinit();

    std.debug.print("Created 3 agents\n\n", .{});

    // Create a sequential pattern to run them in order
    std.debug.print("Building sequential workflow...\n", .{});

    // Create an array of agents
    const agents = [_]agenkit.Agent{
        agent1.agent(),
        agent2.agent(),
        agent3.agent(),
    };

    var workflow = try agenkit.patterns.SequentialPattern.init(allocator, &agents, "workflow");
    defer workflow.deinit();

    std.debug.print("Created workflow with {d} agents\n\n", .{agents.len});

    // Create input message
    var input = try agenkit.Message.withText(
        allocator,
        .user,
        "Process this through the pipeline",
    );
    defer input.deinit();

    std.debug.print("Input message: {s}\n\n", .{try input.contentAsText()});

    // Execute the workflow
    std.debug.print("Executing workflow...\n", .{});
    const result = try workflow.agent().process(input);
    var output = try result.unwrap();
    defer output.deinit();

    std.debug.print("Workflow complete!\n", .{});
    std.debug.print("Output role: {s}\n", .{@tagName(output.role)});
    std.debug.print("Output content: {s}\n\n", .{try output.contentAsText()});

    // Demonstrate individual agent execution for comparison
    std.debug.print("=== Comparison: Individual Agent ===\n\n", .{});
    
    var single_input = try agenkit.Message.withText(
        allocator,
        .user,
        "Single agent processing",
    );
    defer single_input.deinit();

    const single_result = try agent1.agent().process(single_input);
    var single_output = try single_result.unwrap();
    defer single_output.deinit();

    std.debug.print("Single agent output: {s}\n\n", .{try single_output.contentAsText()});

    std.debug.print("✓ Example completed successfully!\n\n", .{});
}

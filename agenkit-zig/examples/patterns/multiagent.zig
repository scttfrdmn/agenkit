//! Multiagent Pattern Example
//!
//! The Multiagent pattern coordinates multiple agents working on related tasks.
//!
//! This example demonstrates:
//! - Agent task assignment and coordination
//! - Sequential orchestration strategy
//! - Task status tracking
//! - Collective results
//!
//! Run with: zig build run-multiagent

const std = @import("std");
const agenkit = @import("agenkit");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== AgentKit Multiagent Pattern Example ===\n\n", .{});

    // Example 1: Coordinated multiagent execution
    std.debug.print("--- Example 1: Multiple Agents, Multiple Tasks ---\n", .{});
    {
        var agent1 = try agenkit.EchoAgent.init(allocator);
        defer agent1.agent().deinit();

        var agent2 = try agenkit.EchoAgent.init(allocator);
        defer agent2.agent().deinit();

        var orchestrator = try agenkit.patterns.MultiAgentOrchestrator.init(
            allocator,
            .sequential, // Strategy
        );
        defer orchestrator.deinit();

        var task1_msg = try agenkit.Message.withText(allocator, .user, "Task A");
        defer task1_msg.deinit();

        var task2_msg = try agenkit.Message.withText(allocator, .user, "Task B");
        defer task2_msg.deinit();

        const task1 = agenkit.patterns.AgentTask{
            .agent = agent1.agent(),
            .message = task1_msg,
            .status = .pending,
        };

        const task2 = agenkit.patterns.AgentTask{
            .agent = agent2.agent(),
            .message = task2_msg,
            .status = .pending,
        };

        const tasks = [_]agenkit.patterns.AgentTask{ task1, task2 };

        const results = try orchestrator.execute(allocator, &tasks);
        defer {
            for (results) |*result| {
                result.deinit();
            }
            allocator.free(results);
        }

        std.debug.print("Executed {d} tasks\n", .{results.len});
        std.debug.print("✓ Multiagent coordination complete\n\n", .{});
    }

    std.debug.print("=== Multiagent Pattern Summary ===\n", .{});
    std.debug.print("✓ Coordinates multiple agents\n", .{});
    std.debug.print("✓ Task assignment and tracking\n", .{});
    std.debug.print("✓ Sequential orchestration strategy\n", .{});
    std.debug.print("✓ Collective result aggregation\n", .{});
    std.debug.print("✓ Useful for: team workflows, distributed tasks\n", .{});
    std.debug.print("\n✓ Multiagent pattern example completed successfully!\n\n", .{});
}

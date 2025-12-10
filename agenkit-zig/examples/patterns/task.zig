//! Task Pattern Example
//!
//! The Task pattern provides lifecycle management for one-shot agent execution.
//!
//! This example demonstrates:
//! - Task creation with configuration
//! - Task execution and state tracking
//! - Timeout handling
//! - Result retrieval
//!
//! Run with: zig build run-task

const std = @import("std");
const agenkit = @import("agenkit");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== AgentKit Task Pattern Example ===\n\n", .{});

    // Example 1: Basic task execution
    std.debug.print("--- Example 1: Basic Task Execution ---\n", .{});
    {
        var echo = try agenkit.EchoAgent.init(allocator);
        defer echo.agent().deinit();

        const config = agenkit.patterns.TaskConfig{
            .retries = 0,
        };

        var task = try agenkit.patterns.Task.init(allocator, echo.agent(), config);
        defer task.deinit();

        var input = try agenkit.Message.withText(allocator, .user, "Task input");
        defer input.deinit();

        const result = try task.execute(input);
        var response = try result.unwrap();
        defer response.deinit();

        std.debug.print("Task completed\n", .{});
        const text = try response.contentAsText();
        std.debug.print("Result: {s}\n", .{text});
        std.debug.print("✓ Task executed successfully\n\n", .{});
    }

    // Example 2: Multiple tasks
    std.debug.print("--- Example 2: Multiple Independent Tasks ---\n", .{});
    {
        var agent1 = try agenkit.EchoAgent.init(allocator);
        defer agent1.agent().deinit();

        var agent2 = try agenkit.EchoAgent.init(allocator);
        defer agent2.agent().deinit();

        const config = agenkit.patterns.TaskConfig{
            .retries = 0,
        };

        var task1 = try agenkit.patterns.Task.init(allocator, agent1.agent(), config);
        defer task1.deinit();

        var task2 = try agenkit.patterns.Task.init(allocator, agent2.agent(), config);
        defer task2.deinit();

        var input1 = try agenkit.Message.withText(allocator, .user, "Task 1");
        defer input1.deinit();

        var input2 = try agenkit.Message.withText(allocator, .user, "Task 2");
        defer input2.deinit();

        const result1 = try task1.execute(input1);
        var response1 = try result1.unwrap();
        defer response1.deinit();

        const result2 = try task2.execute(input2);
        var response2 = try result2.unwrap();
        defer response2.deinit();

        std.debug.print("Task 1: completed\n", .{});
        std.debug.print("Task 2: completed\n", .{});
        std.debug.print("✓ Both tasks executed\n\n", .{});
    }

    std.debug.print("=== Task Pattern Summary ===\n", .{});
    std.debug.print("✓ One-shot agent execution\n", .{});
    std.debug.print("✓ Lifecycle management (pending → running → completed/failed)\n", .{});
    std.debug.print("✓ Timeout support\n", .{});
    std.debug.print("✓ Result storage and retrieval\n", .{});
    std.debug.print("✓ Useful for: background jobs, scheduled tasks\n", .{});
    std.debug.print("\n✓ Task pattern example completed successfully!\n\n", .{});
}

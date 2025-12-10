//! Multiagent Pattern Example
//!
//! The Multiagent pattern coordinates multiple agents working on related tasks.
//!
//! This example demonstrates:
//! - Agent registration with MultiAgentOrchestrator
//! - Sequential orchestration strategy
//! - Automatic task tracking and status updates
//! - Task history and result retrieval
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
    std.debug.print("--- Example 1: Multiple Agents, Sequential Processing ---\n", .{});
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

        // Register agents
        try orchestrator.registerAgent("Agent-A", agent1.agent());
        try orchestrator.registerAgent("Agent-B", agent2.agent());

        std.debug.print("Registered {d} agents\n", .{orchestrator.agentCount()});

        // Process a message through the orchestrator
        var msg = try agenkit.Message.withText(allocator, .user, "Coordinate this task");
        defer msg.deinit();

        // Use orchestrator through Agent interface
        const agent_iface = orchestrator.agent();
        const result = try agent_iface.process(msg);
        var response = try result.unwrap();
        defer response.deinit();

        std.debug.print("Result: {s}\n", .{try response.contentAsText()});

        // Check task history
        const tasks = orchestrator.getTasks();
        std.debug.print("Tasks executed: {d}\n", .{tasks.len});
        for (tasks, 0..) |task, i| {
            std.debug.print("  Task {d}: {s} - {s}\n", .{ i + 1, task.agent_name, task.status.toString() });
        }

        std.debug.print("✓ Multiagent coordination complete\n\n", .{});
    }

    // Example 2: Listing registered agents
    std.debug.print("--- Example 2: Agent Registry ---\n", .{});
    {
        var agent1 = try agenkit.EchoAgent.init(allocator);
        defer agent1.agent().deinit();

        var agent2 = try agenkit.EchoAgent.init(allocator);
        defer agent2.agent().deinit();

        var agent3 = try agenkit.EchoAgent.init(allocator);
        defer agent3.agent().deinit();

        var orchestrator = try agenkit.patterns.MultiAgentOrchestrator.init(
            allocator,
            .sequential,
        );
        defer orchestrator.deinit();

        try orchestrator.registerAgent("Writer", agent1.agent());
        try orchestrator.registerAgent("Reviewer", agent2.agent());
        try orchestrator.registerAgent("Editor", agent3.agent());

        var agent_names = try orchestrator.listAgents(allocator);
        defer {
            for (agent_names.items) |name| {
                allocator.free(name);
            }
            agent_names.deinit(allocator);
        }

        std.debug.print("Registered agents:\n", .{});
        for (agent_names.items) |name| {
            std.debug.print("  - {s}\n", .{name});
        }
        std.debug.print("✓ Agent registry maintains agent list\n\n", .{});
    }

    // Example 3: Task status tracking
    std.debug.print("--- Example 3: Task Status Tracking ---\n", .{});
    {
        var agent1 = try agenkit.EchoAgent.init(allocator);
        defer agent1.agent().deinit();

        var agent2 = try agenkit.EchoAgent.init(allocator);
        defer agent2.agent().deinit();

        var orchestrator = try agenkit.patterns.MultiAgentOrchestrator.init(
            allocator,
            .sequential,
        );
        defer orchestrator.deinit();

        try orchestrator.registerAgent("FirstAgent", agent1.agent());
        try orchestrator.registerAgent("SecondAgent", agent2.agent());

        // Process multiple messages
        const messages = [_][]const u8{
            "Task 1: Analyze data",
            "Task 2: Generate report",
            "Task 3: Send summary",
        };

        for (messages, 0..) |msg_text, i| {
            var msg = try agenkit.Message.withText(allocator, .user, msg_text);
            defer msg.deinit();

            const result = try orchestrator.agent().process(msg);
            var response = try result.unwrap();
            defer response.deinit();

            std.debug.print("Message {d} processed\n", .{i + 1});
        }

        const tasks = orchestrator.getTasks();
        std.debug.print("\nTotal tasks executed: {d}\n", .{tasks.len});

        // Count by status
        var completed: usize = 0;
        var failed: usize = 0;
        for (tasks) |task| {
            switch (task.status) {
                .completed => completed += 1,
                .failed => failed += 1,
                else => {},
            }
        }
        std.debug.print("  Completed: {d}\n", .{completed});
        std.debug.print("  Failed: {d}\n", .{failed});
        std.debug.print("✓ Task status properly tracked\n\n", .{});
    }

    // Example 4: Agent capabilities through orchestrator
    std.debug.print("--- Example 4: Orchestrator as Agent ---\n", .{});
    {
        var agent1 = try agenkit.EchoAgent.init(allocator);
        defer agent1.agent().deinit();

        var orchestrator = try agenkit.patterns.MultiAgentOrchestrator.init(
            allocator,
            .sequential,
        );
        defer orchestrator.deinit();

        try orchestrator.registerAgent("Specialist", agent1.agent());

        const agent_iface = orchestrator.agent();
        std.debug.print("Orchestrator name: {s}\n", .{agent_iface.name()});

        const caps = try agent_iface.capabilities(allocator);
        defer allocator.free(caps);

        std.debug.print("Capabilities: {d}\n", .{caps.len});
        for (caps) |cap| {
            std.debug.print("  - {s}\n", .{cap});
        }
        std.debug.print("✓ Orchestrator implements Agent interface\n\n", .{});
    }

    std.debug.print("=== Multiagent Pattern Summary ===\n", .{});
    std.debug.print("✓ Coordinates multiple agents with registerAgent()\n", .{});
    std.debug.print("✓ Sequential orchestration strategy\n", .{});
    std.debug.print("✓ Automatic task creation and tracking\n", .{});
    std.debug.print("✓ Task status updates (pending → in_progress → completed/failed)\n", .{});
    std.debug.print("✓ Task history with getTasks()\n", .{});
    std.debug.print("✓ Agent registry with listAgents()\n", .{});
    std.debug.print("✓ Implements standard Agent interface\n", .{});
    std.debug.print("✓ Useful for: team workflows, distributed tasks, coordination\n", .{});
    std.debug.print("\n✓ Multiagent pattern example completed successfully!\n\n", .{});
}

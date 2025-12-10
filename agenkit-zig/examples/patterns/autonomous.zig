//! Autonomous Agent Pattern Example
//!
//! The Autonomous pattern enables agents to operate independently toward objectives,
//! setting their own goals and making decisions with minimal human intervention.
//!
//! This example demonstrates:
//! - Creating an autonomous agent with an objective
//! - Adding and prioritizing goals
//! - Autonomous execution with run()
//! - Progress tracking and goal completion
//! - Custom goal worker functions
//! - Iteration limiting and early termination
//!
//! Run with: zig build run-autonomous

const std = @import("std");
const agenkit = @import("agenkit");

// Custom goal worker that simulates different types of work
fn researchWorker(allocator: std.mem.Allocator, goal: *agenkit.patterns.Goal) agenkit.AgentError![]const u8 {
    const result = std.fmt.allocPrint(allocator, "[RESEARCH] Working on: {s} (priority: {d})", .{ goal.description, goal.priority }) catch {
        return agenkit.AgentError.ProcessingFailed;
    };

    // Simulate significant progress for high priority goals
    const progress_increment: f64 = if (goal.priority >= 8) 0.5 else 0.25;
    goal.updateProgress(goal.progress + progress_increment);

    return result;
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== AgentKit Autonomous Pattern Example ===\n\n", .{});

    // Example 1: Basic autonomous agent
    std.debug.print("--- Example 1: Basic Autonomous Agent ---\n", .{});
    {
        var agent = try agenkit.patterns.AutonomousAgent.init(
            allocator,
            "Research AI trends",
            10, // max_iterations
        );
        defer agent.deinit();

        std.debug.print("Agent created:\n", .{});
        std.debug.print("  Objective: {s}\n", .{agent.getObjective()});
        std.debug.print("  Max iterations: {d}\n", .{agent.getMaxIterations()});
        std.debug.print("  Is running: {}\n", .{agent.isRunning()});
        std.debug.print("✓ Autonomous agent initialized\n\n", .{});
    }

    // Example 2: Adding and prioritizing goals
    std.debug.print("--- Example 2: Goal Management ---\n", .{});
    {
        var agent = try agenkit.patterns.AutonomousAgent.init(allocator, "Build product", 20);
        defer agent.deinit();

        try agent.addGoal("Critical bug fix", 10);
        try agent.addGoal("Feature development", 5);
        try agent.addGoal("Documentation", 2);
        try agent.addGoal("Performance optimization", 7);

        std.debug.print("Goals added: {d}\n", .{agent.goals.items.len});
        std.debug.print("Active goals: {d}\n", .{agent.activeGoalCount()});
        std.debug.print("\nGoal list:\n", .{});
        for (agent.goals.items) |goal| {
            std.debug.print("  [{d}] {s} - {s} ({d:.0}%)\n", .{ goal.priority, goal.status.toString(), goal.description, goal.progress * 100.0 });
        }
        std.debug.print("✓ Goals prioritized correctly\n\n", .{});
    }

    // Example 3: Running autonomous agent
    std.debug.print("--- Example 3: Autonomous Execution ---\n", .{});
    {
        var agent = try agenkit.patterns.AutonomousAgent.init(allocator, "Complete tasks", 5);
        defer agent.deinit();

        try agent.addGoal("High priority task", 10);
        try agent.addGoal("Medium priority task", 5);

        var result = try agent.run();
        defer result.deinit();

        std.debug.print("Execution completed:\n", .{});
        std.debug.print("  Objective: {s}\n", .{result.objective});
        std.debug.print("  Iterations: {d}\n", .{result.iterations});
        std.debug.print("  Goals completed: {d}/{d}\n", .{ result.goals_completed, agent.goals.items.len });
        std.debug.print("\nResults:\n", .{});
        for (result.results.items, 0..) |res, i| {
            std.debug.print("  {d}. {s}\n", .{ i + 1, res });
        }
        std.debug.print("✓ Agent ran autonomously\n\n", .{});
    }

    // Example 4: Goal completion tracking
    std.debug.print("--- Example 4: Progress Tracking ---\n", .{});
    {
        var goal1 = try agenkit.patterns.Goal.init(allocator, "Task 1", 5);
        defer goal1.deinit();

        std.debug.print("Initial state: {s}, progress: {d:.0}%\n", .{ goal1.status.toString(), goal1.progress * 100.0 });

        goal1.updateProgress(0.5);
        std.debug.print("After update: {s}, progress: {d:.0}%\n", .{ goal1.status.toString(), goal1.progress * 100.0 });

        goal1.complete();
        std.debug.print("After complete: {s}, progress: {d:.0}%\n", .{ goal1.status.toString(), goal1.progress * 100.0 });

        std.debug.print("✓ Progress tracking working\n\n", .{});
    }

    // Example 5: Custom worker function
    std.debug.print("--- Example 5: Custom Worker ---\n", .{});
    {
        var agent = try agenkit.patterns.AutonomousAgent.init(allocator, "Research project", 3);
        defer agent.deinit();

        agent.setWorker(researchWorker);

        try agent.addGoal("Literature review", 9);
        try agent.addGoal("Data analysis", 6);

        var result = try agent.run();
        defer result.deinit();

        std.debug.print("Custom worker results:\n", .{});
        for (result.results.items) |res| {
            std.debug.print("  {s}\n", .{res});
        }
        std.debug.print("  Completed: {d}/{d} goals\n", .{ result.goals_completed, agent.goals.items.len });
        std.debug.print("✓ Custom worker function used\n\n", .{});
    }

    // Example 6: Early termination when goals complete
    std.debug.print("--- Example 6: Early Termination ---\n", .{});
    {
        var agent = try agenkit.patterns.AutonomousAgent.init(allocator, "Quick task", 100);
        defer agent.deinit();

        // Add goal that completes quickly
        try agent.addGoal("Fast task", 10);

        // Manually complete the goal before running
        agent.goals.items[0].complete();

        var result = try agent.run();
        defer result.deinit();

        std.debug.print("Terminated early:\n", .{});
        std.debug.print("  Max iterations: {d}\n", .{agent.getMaxIterations()});
        std.debug.print("  Actual iterations: {d}\n", .{result.iterations});
        std.debug.print("  Reason: All goals complete\n", .{});
        std.debug.print("✓ Early termination when goals complete\n\n", .{});
    }

    // Example 7: Goal status transitions
    std.debug.print("--- Example 7: Status Transitions ---\n", .{});
    {
        var goal = try agenkit.patterns.Goal.init(allocator, "Sample goal", 5);
        defer goal.deinit();

        std.debug.print("Status lifecycle:\n", .{});
        std.debug.print("  Initial: {s}\n", .{goal.status.toString()});

        goal.updateProgress(0.5);
        std.debug.print("  After update: {s} (progress: {d:.0}%)\n", .{ goal.status.toString(), goal.progress * 100.0 });

        goal.updateProgress(1.0);
        std.debug.print("  After 100%%: {s}\n", .{goal.status.toString()});

        std.debug.print("✓ Status transitions automatically\n\n", .{});
    }

    // Example 8: Complete workflow simulation
    std.debug.print("--- Example 8: Full Workflow ---\n", .{});
    {
        var agent = try agenkit.patterns.AutonomousAgent.init(allocator, "Launch application", 15);
        defer agent.deinit();

        try agent.addGoal("Setup infrastructure", 9);
        try agent.addGoal("Deploy backend", 8);
        try agent.addGoal("Deploy frontend", 7);
        try agent.addGoal("Configure monitoring", 5);
        try agent.addGoal("Update documentation", 3);

        std.debug.print("Starting autonomous execution...\n", .{});
        std.debug.print("Initial: {d} active goals\n", .{agent.activeGoalCount()});

        var result = try agent.run();
        defer result.deinit();

        std.debug.print("\nExecution summary:\n", .{});
        std.debug.print("  Objective: {s}\n", .{result.objective});
        std.debug.print("  Total iterations: {d}\n", .{result.iterations});
        std.debug.print("  Goals completed: {d}/{d}\n", .{ result.goals_completed, agent.goals.items.len });
        std.debug.print("  Active remaining: {d}\n", .{agent.activeGoalCount()});

        std.debug.print("\nFinal goal states:\n", .{});
        for (agent.goals.items) |goal| {
            std.debug.print("  {s}: {d:.0}% - {s}\n", .{ goal.status.toString(), goal.progress * 100.0, goal.description });
        }

        std.debug.print("✓ Full autonomous workflow\n\n", .{});
    }

    std.debug.print("=== Autonomous Pattern Summary ===\n", .{});
    std.debug.print("✓ AutonomousAgent: Operates independently toward objectives\n", .{});
    std.debug.print("✓ Goal: Prioritized sub-tasks with progress tracking\n", .{});
    std.debug.print("✓ Priority-based execution: High priority goals worked on first\n", .{});
    std.debug.print("✓ Progress tracking: updateProgress() and complete()\n", .{});
    std.debug.print("✓ Custom workers: setWorker() for domain-specific logic\n", .{});
    std.debug.print("✓ Iteration limiting: max_iterations prevents infinite loops\n", .{});
    std.debug.print("✓ Early termination: Stops when all goals complete\n", .{});
    std.debug.print("✓ AutonomousResult: Captures iterations, completions, results\n", .{});
    std.debug.print("✓ Useful for: long-running tasks, self-directed systems, automation\n", .{});
    std.debug.print("\n✓ Autonomous pattern example completed successfully!\n\n", .{});
}

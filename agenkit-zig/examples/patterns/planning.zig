//! Planning Pattern Example
//!
//! The Planning pattern breaks complex tasks into manageable steps with dependencies,
//! executing them in order while tracking progress and handling failures.
//!
//! This example demonstrates:
//! - Plan creation with goal and steps
//! - PlanStep with dependencies and status tracking
//! - Dependency resolution and execution ordering
//! - Progress tracking and completion status
//! - Custom step executors
//! - PlanningAgent for automated planning
//!
//! Run with: zig build run-planning

const std = @import("std");
const agenkit = @import("agenkit");

// Custom step executor function
fn customStepExecutor(allocator: std.mem.Allocator, step: *const agenkit.patterns.PlanStep) agenkit.AgentError![]const u8 {
    return std.fmt.allocPrint(allocator, "[CUSTOM] Executed: {s}", .{step.description}) catch {
        return agenkit.AgentError.ProcessingFailed;
    };
}

pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== AgentKit Planning Pattern Example ===\n\n", .{});

    // Example 1: Basic plan creation
    std.debug.print("--- Example 1: Basic Plan ---\n", .{});
    {
        var plan = try agenkit.patterns.Plan.init(allocator, "Build a website");
        defer plan.deinit();

        const step1 = try agenkit.patterns.PlanStep.init(allocator, "Design mockups", 0, &[_]usize{});
        const step2 = try agenkit.patterns.PlanStep.init(allocator, "Setup development environment", 1, &[_]usize{});
        const step3 = try agenkit.patterns.PlanStep.init(allocator, "Implement frontend", 2, &[_]usize{ 0, 1 });

        try plan.addStep(step1);
        try plan.addStep(step2);
        try plan.addStep(step3);

        std.debug.print("Goal: {s}\n", .{plan.goal});
        std.debug.print("Steps: {d}\n", .{plan.steps.items.len});
        for (plan.steps.items) |step| {
            std.debug.print("  {d}. {s} (deps: {d})\n", .{ step.step_number, step.description, step.dependencies.items.len });
        }
        std.debug.print("✓ Plan created with dependencies\n\n", .{});
    }

    // Example 2: Step status tracking
    std.debug.print("--- Example 2: Step Status Tracking ---\n", .{});
    {
        var plan = try agenkit.patterns.Plan.init(allocator, "Deploy application");
        defer plan.deinit();

        const step1 = try agenkit.patterns.PlanStep.init(allocator, "Run tests", 0, &[_]usize{});
        try plan.addStep(step1);

        const step2 = try agenkit.patterns.PlanStep.init(allocator, "Build artifacts", 1, &[_]usize{0});
        try plan.addStep(step2);

        const step3 = try agenkit.patterns.PlanStep.init(allocator, "Deploy to production", 2, &[_]usize{1});
        try plan.addStep(step3);

        std.debug.print("Initial status:\n", .{});
        for (plan.steps.items) |step| {
            std.debug.print("  Step {d}: {s}\n", .{ step.step_number, step.status.toString() });
        }

        // Mark first step complete
        try plan.steps.items[0].setResult("All tests passed");
        plan.steps.items[0].status = .completed;

        std.debug.print("\nAfter completing step 0:\n", .{});
        std.debug.print("  Step 0: {s} - Result: {s}\n", .{ plan.steps.items[0].status.toString(), plan.steps.items[0].result.? });
        std.debug.print("  Progress: {d:.1}%\n", .{plan.getProgress()});
        std.debug.print("  Complete: {}\n", .{plan.isComplete()});

        std.debug.print("✓ Step status tracking works\n\n", .{});
    }

    // Example 3: Dependency resolution
    std.debug.print("--- Example 3: Dependency Resolution ---\n", .{});
    {
        var plan = try agenkit.patterns.Plan.init(allocator, "Multi-step task");
        defer plan.deinit();

        const step1 = try agenkit.patterns.PlanStep.init(allocator, "Step A (no deps)", 0, &[_]usize{});
        const step2 = try agenkit.patterns.PlanStep.init(allocator, "Step B (no deps)", 1, &[_]usize{});
        const step3 = try agenkit.patterns.PlanStep.init(allocator, "Step C (depends on A)", 2, &[_]usize{0});
        const step4 = try agenkit.patterns.PlanStep.init(allocator, "Step D (depends on A, B)", 3, &[_]usize{ 0, 1 });

        try plan.addStep(step1);
        try plan.addStep(step2);
        try plan.addStep(step3);
        try plan.addStep(step4);

        // Get next executable steps (initially: A and B since they have no dependencies)
        var next = try plan.getNextSteps(allocator);
        defer next.deinit(allocator);

        std.debug.print("Next executable steps (no completions yet): ", .{});
        for (next.items) |idx| {
            std.debug.print("{d} ", .{idx});
        }
        std.debug.print("\n", .{});

        // Complete step A
        plan.steps.items[0].status = .completed;

        var next2 = try plan.getNextSteps(allocator);
        defer next2.deinit(allocator);

        std.debug.print("Next steps after completing A: ", .{});
        for (next2.items) |idx| {
            std.debug.print("{d} ", .{idx});
        }
        std.debug.print("\n", .{});

        std.debug.print("✓ Dependency resolution working\n\n", .{});
    }

    // Example 4: Progress tracking
    std.debug.print("--- Example 4: Progress Tracking ---\n", .{});
    {
        var plan = try agenkit.patterns.Plan.init(allocator, "Complete project");
        defer plan.deinit();

        for (0..5) |i| {
            const step = try agenkit.patterns.PlanStep.init(allocator, "Step", i, &[_]usize{});
            try plan.addStep(step);
        }

        std.debug.print("Progress tracking:\n", .{});
        std.debug.print("  Initial: {d:.1}%\n", .{plan.getProgress()});

        plan.steps.items[0].status = .completed;
        plan.steps.items[1].status = .completed;
        std.debug.print("  After 2 steps: {d:.1}%\n", .{plan.getProgress()});

        for (plan.steps.items) |*step| {
            step.status = .completed;
        }
        std.debug.print("  After all steps: {d:.1}%\n", .{plan.getProgress()});
        std.debug.print("  Is complete: {}\n", .{plan.isComplete()});

        std.debug.print("✓ Progress tracking accurate\n\n", .{});
    }

    // Example 5: Failure handling
    std.debug.print("--- Example 5: Failure Handling ---\n", .{});
    {
        var plan = try agenkit.patterns.Plan.init(allocator, "Task with failures");
        defer plan.deinit();

        const step1 = try agenkit.patterns.PlanStep.init(allocator, "First step", 0, &[_]usize{});
        const step2 = try agenkit.patterns.PlanStep.init(allocator, "Second step", 1, &[_]usize{0});
        try plan.addStep(step1);
        try plan.addStep(step2);

        // First step completes
        try plan.steps.items[0].setResult("Success");

        // Second step fails
        try plan.steps.items[1].setError("Network timeout");

        std.debug.print("Step 0: {s}\n", .{plan.steps.items[0].status.toString()});
        std.debug.print("Step 1: {s} - Error: {s}\n", .{ plan.steps.items[1].status.toString(), plan.steps.items[1].error_msg.? });
        std.debug.print("Has failures: {}\n", .{plan.hasFailures()});
        std.debug.print("✓ Failure detection working\n\n", .{});
    }

    // Example 6: PlanningAgent
    std.debug.print("--- Example 6: Planning Agent ---\n", .{});
    {
        var planning_agent = try agenkit.patterns.PlanningAgent.init(
            allocator,
            10, // max_steps
            false, // allow_replanning
        );
        defer planning_agent.deinit();

        std.debug.print("PlanningAgent initialized\n", .{});
        std.debug.print("  Max steps: {d}\n", .{planning_agent.max_steps});
        std.debug.print("  Allow replanning: {}\n", .{planning_agent.allow_replanning});

        // Note: Full plan creation would require LLM integration
        // The agent has methods for plan generation and execution
        std.debug.print("✓ PlanningAgent ready for use\n\n", .{});
    }

    // Example 7: Custom executor
    std.debug.print("--- Example 7: Custom Step Executor ---\n", .{});
    {
        var planning_agent = try agenkit.patterns.PlanningAgent.init(allocator, 5, false);
        defer planning_agent.deinit();

        // Set custom executor
        planning_agent.setExecutor(customStepExecutor);

        // Create a mock step
        var step = try agenkit.patterns.PlanStep.init(allocator, "Deploy to staging", 0, &[_]usize{});
        defer step.deinit();

        // Execute with custom executor
        const result = try planning_agent.executor(allocator, &step);
        defer allocator.free(result);

        std.debug.print("Custom executor result: {s}\n", .{result});
        std.debug.print("✓ Custom executors supported\n\n", .{});
    }

    // Example 8: Complete workflow simulation
    std.debug.print("--- Example 8: Complete Workflow ---\n", .{});
    {
        var plan = try agenkit.patterns.Plan.init(allocator, "Launch product");
        defer plan.deinit();

        // Create plan with dependencies
        const step1 = try agenkit.patterns.PlanStep.init(allocator, "Market research", 0, &[_]usize{});
        const step2 = try agenkit.patterns.PlanStep.init(allocator, "Product design", 1, &[_]usize{0});
        const step3 = try agenkit.patterns.PlanStep.init(allocator, "Development", 2, &[_]usize{1});
        const step4 = try agenkit.patterns.PlanStep.init(allocator, "Testing", 3, &[_]usize{2});
        const step5 = try agenkit.patterns.PlanStep.init(allocator, "Launch", 4, &[_]usize{ 3 });

        try plan.addStep(step1);
        try plan.addStep(step2);
        try plan.addStep(step3);
        try plan.addStep(step4);
        try plan.addStep(step5);

        std.debug.print("Executing plan: {s}\n", .{plan.goal});

        // Simulate execution
        for (plan.steps.items) |*step| {
            step.status = .in_progress;
            std.debug.print("  [{d:.0}%] Executing: {s}\n", .{ plan.getProgress(), step.description });
            try step.setResult("Done");
            step.status = .completed;
        }

        std.debug.print("  [100%] Complete!\n", .{});
        std.debug.print("✓ Full workflow simulation\n\n", .{});
    }

    std.debug.print("=== Planning Pattern Summary ===\n", .{});
    std.debug.print("✓ Plan: Goal + ordered steps\n", .{});
    std.debug.print("✓ PlanStep: Dependencies, status, results\n", .{});
    std.debug.print("✓ Dependency resolution with canExecute() and getNextSteps()\n", .{});
    std.debug.print("✓ Progress tracking with getProgress() and isComplete()\n", .{});
    std.debug.print("✓ Failure detection with hasFailures()\n", .{});
    std.debug.print("✓ PlanningAgent for automated plan creation\n", .{});
    std.debug.print("✓ Custom executors via setExecutor()\n", .{});
    std.debug.print("✓ Useful for: multi-step tasks, workflows, coordinated execution\n", .{});
    std.debug.print("\n✓ Planning pattern example completed successfully!\n\n", .{});
}

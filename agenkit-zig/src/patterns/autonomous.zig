/// Autonomous Agent Pattern
///
/// An agent that operates independently with minimal human intervention:
/// - Sets its own goals based on high-level objectives
/// - Makes decisions about actions to take
/// - Monitors progress and adapts strategy
/// - Continues until objective is met or stopped
///
/// # Key Concepts
///
/// - **Objective**: High-level goal the agent is working towards
/// - **Goals**: Specific sub-tasks the agent pursues
/// - **Iterations**: Number of work cycles completed
/// - **Priority**: Goals are worked on in priority order
/// - **Progress**: Track completion of each goal
///
/// # Use Cases
///
/// - Long-running tasks
/// - Self-directed research
/// - Continuous improvement systems
/// - Automated workflows
///
/// # Example
///
/// ```zig
/// const std = @import("std");
/// const agenkit = @import("agenkit");
///
/// pub fn main() !void {
///     var gpa = std.heap.DebugAllocator(.{}){};
///     defer _ = gpa.deinit();
///     const allocator = gpa.allocator();
///
///     var agent = try agenkit.patterns.AutonomousAgent.init(
///         allocator,
///         "Research and summarize AI trends",
///         10,
///     );
///     defer agent.deinit();
///
///     try agent.addGoal("Search for recent AI papers", 10);
///     try agent.addGoal("Identify key trends", 5);
///     try agent.addGoal("Write summary report", 1);
///
///     var result = try agent.run();
///     defer result.deinit();
/// }
/// ```

const std = @import("std");
const Allocator = std.mem.Allocator;
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const Message = @import("../message.zig").Message;
const Result = @import("../agent.zig").Result;

/// Goal status values
pub const GoalStatus = enum {
    active,
    completed,
    abandoned,

    pub fn toString(self: GoalStatus) []const u8 {
        return switch (self) {
            .active => "active",
            .completed => "completed",
            .abandoned => "abandoned",
        };
    }
};

/// A goal the autonomous agent is pursuing
pub const Goal = struct {
    description: []const u8,
    priority: i32,
    status: GoalStatus,
    progress: f64,
    allocator: Allocator,

    pub fn init(allocator: Allocator, description: []const u8, priority: i32) !Goal {
        return Goal{
            .description = try allocator.dupe(u8, description),
            .priority = priority,
            .status = .active,
            .progress = 0.0,
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *Goal) void {
        self.allocator.free(self.description);
    }

    /// Mark goal as completed
    pub fn complete(self: *Goal) void {
        self.status = .completed;
        self.progress = 1.0;
    }

    /// Update progress (0.0 to 1.0)
    pub fn updateProgress(self: *Goal, progress: f64) void {
        self.progress = std.math.clamp(progress, 0.0, 1.0);
        if (self.progress >= 1.0) {
            self.status = .completed;
        }
    }
};

/// Result of running an autonomous agent
pub const AutonomousResult = struct {
    objective: []const u8,
    iterations: usize,
    goals_completed: usize,
    results: std.ArrayList([]const u8),
    allocator: Allocator,

    pub fn init(allocator: Allocator, objective: []const u8, iterations: usize, goals_completed: usize) !AutonomousResult {
        return AutonomousResult{
            .objective = try allocator.dupe(u8, objective),
            .iterations = iterations,
            .goals_completed = goals_completed,
            .results = std.ArrayList([]const u8){},
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *AutonomousResult) void {
        self.allocator.free(self.objective);
        for (self.results.items) |r| {
            self.allocator.free(r);
        }
        self.results.deinit(self.allocator);
    }

    pub fn addResult(self: *AutonomousResult, result: []const u8) !void {
        const owned = try self.allocator.dupe(u8, result);
        try self.results.append(self.allocator, owned);
    }
};

/// Goal worker function signature
pub const GoalWorkerFn = *const fn (allocator: Allocator, goal: *Goal) AgentError![]const u8;

/// Default worker function
pub fn defaultWorker(allocator: Allocator, goal: *Goal) AgentError![]const u8 {
    const result = std.fmt.allocPrint(allocator, "Progress on: {s} (priority: {d}, progress: {d:.1}%)", .{ goal.description, goal.priority, goal.progress * 100.0 }) catch {
        return AgentError.ProcessingFailed;
    };

    // Simulate progress
    goal.updateProgress(goal.progress + 0.2);

    return result;
}

/// Agent that operates autonomously toward objectives
pub const AutonomousAgent = struct {
    allocator: Allocator,
    objective: []const u8,
    max_iterations: usize,
    goals: std.ArrayList(Goal),
    iteration_count: usize,
    is_running: bool,
    worker: GoalWorkerFn,

    pub fn init(allocator: Allocator, objective: []const u8, max_iterations: usize) !AutonomousAgent {
        const max_iter = if (max_iterations == 0) 10 else max_iterations;

        return AutonomousAgent{
            .allocator = allocator,
            .objective = try allocator.dupe(u8, objective),
            .max_iterations = max_iter,
            .goals = std.ArrayList(Goal){},
            .iteration_count = 0,
            .is_running = false,
            .worker = defaultWorker,
        };
    }

    pub fn deinit(self: *AutonomousAgent) void {
        self.allocator.free(self.objective);
        for (self.goals.items) |*goal| {
            goal.deinit();
        }
        self.goals.deinit(self.allocator);
    }

    /// Get the agent's objective
    pub fn getObjective(self: *const AutonomousAgent) []const u8 {
        return self.objective;
    }

    /// Get maximum iterations
    pub fn getMaxIterations(self: *const AutonomousAgent) usize {
        return self.max_iterations;
    }

    /// Get current iteration count
    pub fn getIterationCount(self: *const AutonomousAgent) usize {
        return self.iteration_count;
    }

    /// Check if agent is running
    pub fn isRunning(self: *const AutonomousAgent) bool {
        return self.is_running;
    }

    /// Add a goal for the agent to pursue
    pub fn addGoal(self: *AutonomousAgent, description: []const u8, priority: i32) !void {
        const goal = try Goal.init(self.allocator, description, priority);
        try self.goals.append(self.allocator, goal);
    }

    /// Set custom worker function
    pub fn setWorker(self: *AutonomousAgent, worker: GoalWorkerFn) void {
        self.worker = worker;
    }

    /// Get the highest priority active goal
    fn getNextGoal(self: *AutonomousAgent) ?*Goal {
        var highest_priority: ?*Goal = null;
        var highest_priority_value: i32 = std.math.minInt(i32);

        for (self.goals.items) |*goal| {
            if (goal.status == .active and goal.priority > highest_priority_value) {
                highest_priority = goal;
                highest_priority_value = goal.priority;
            }
        }

        return highest_priority;
    }

    /// Check if all goals are complete
    fn allGoalsComplete(self: *const AutonomousAgent) bool {
        for (self.goals.items) |goal| {
            if (goal.status == .active) {
                return false;
            }
        }
        return true;
    }

    /// Run the autonomous agent
    pub fn run(self: *AutonomousAgent) !AutonomousResult {
        if (self.is_running) {
            return AgentError.InvalidInput;
        }

        self.is_running = true;
        defer self.is_running = false;

        var result = try AutonomousResult.init(self.allocator, self.objective, 0, 0);
        errdefer result.deinit();

        while (self.iteration_count < self.max_iterations) {
            // Check if all goals are complete
            if (self.allGoalsComplete()) {
                break;
            }

            // Get next goal to work on
            const goal = self.getNextGoal() orelse break;

            // Work on the goal
            const work_result = try self.worker(self.allocator, goal);
            defer self.allocator.free(work_result);

            try result.addResult(work_result);

            self.iteration_count += 1;
        }

        // Count completed goals
        var completed: usize = 0;
        for (self.goals.items) |goal| {
            if (goal.status == .completed) {
                completed += 1;
            }
        }

        result.iterations = self.iteration_count;
        result.goals_completed = completed;

        return result;
    }

    /// Get number of active goals
    pub fn activeGoalCount(self: *const AutonomousAgent) usize {
        var count: usize = 0;
        for (self.goals.items) |goal| {
            if (goal.status == .active) {
                count += 1;
            }
        }
        return count;
    }

    /// Get number of completed goals
    pub fn completedGoalCount(self: *const AutonomousAgent) usize {
        var count: usize = 0;
        for (self.goals.items) |goal| {
            if (goal.status == .completed) {
                count += 1;
            }
        }
        return count;
    }
};

// Tests
const testing = std.testing;

test "GoalStatus toString" {
    try testing.expectEqualStrings("active", GoalStatus.active.toString());
    try testing.expectEqualStrings("completed", GoalStatus.completed.toString());
    try testing.expectEqualStrings("abandoned", GoalStatus.abandoned.toString());
}

test "Goal creation" {
    const allocator = testing.allocator;

    var goal = try Goal.init(allocator, "Test goal", 10);
    defer goal.deinit();

    try testing.expectEqualStrings("Test goal", goal.description);
    try testing.expectEqual(@as(i32, 10), goal.priority);
    try testing.expectEqual(GoalStatus.active, goal.status);
    try testing.expectEqual(@as(f64, 0.0), goal.progress);
}

test "Goal complete" {
    const allocator = testing.allocator;

    var goal = try Goal.init(allocator, "Test goal", 10);
    defer goal.deinit();

    goal.complete();
    try testing.expectEqual(GoalStatus.completed, goal.status);
    try testing.expectEqual(@as(f64, 1.0), goal.progress);
}

test "Goal updateProgress" {
    const allocator = testing.allocator;

    var goal = try Goal.init(allocator, "Test goal", 10);
    defer goal.deinit();

    goal.updateProgress(0.5);
    try testing.expectEqual(@as(f64, 0.5), goal.progress);
    try testing.expectEqual(GoalStatus.active, goal.status);

    goal.updateProgress(1.0);
    try testing.expectEqual(@as(f64, 1.0), goal.progress);
    try testing.expectEqual(GoalStatus.completed, goal.status);
}

test "AutonomousAgent creation" {
    const allocator = testing.allocator;

    var agent = try AutonomousAgent.init(allocator, "Test objective", 10);
    defer agent.deinit();

    try testing.expectEqualStrings("Test objective", agent.getObjective());
    try testing.expectEqual(@as(usize, 10), agent.getMaxIterations());
    try testing.expectEqual(@as(usize, 0), agent.getIterationCount());
    try testing.expect(!agent.isRunning());
}

test "AutonomousAgent addGoal" {
    const allocator = testing.allocator;

    var agent = try AutonomousAgent.init(allocator, "Test objective", 10);
    defer agent.deinit();

    try agent.addGoal("Goal 1", 10);
    try agent.addGoal("Goal 2", 5);

    try testing.expectEqual(@as(usize, 2), agent.goals.items.len);
    try testing.expectEqual(@as(usize, 2), agent.activeGoalCount());
}

test "AutonomousAgent getNextGoal" {
    const allocator = testing.allocator;

    var agent = try AutonomousAgent.init(allocator, "Test objective", 10);
    defer agent.deinit();

    try agent.addGoal("Low priority", 1);
    try agent.addGoal("High priority", 10);
    try agent.addGoal("Medium priority", 5);

    const next = agent.getNextGoal();
    try testing.expect(next != null);
    try testing.expectEqualStrings("High priority", next.?.description);
    try testing.expectEqual(@as(i32, 10), next.?.priority);
}

test "AutonomousAgent run basic" {
    const allocator = testing.allocator;

    var agent = try AutonomousAgent.init(allocator, "Test objective", 5);
    defer agent.deinit();

    try agent.addGoal("Goal 1", 10);

    var result = try agent.run();
    defer result.deinit();

    try testing.expect(result.iterations > 0);
    try testing.expect(result.iterations <= 5);
}

test "AutonomousAgent run multiple goals" {
    const allocator = testing.allocator;

    var agent = try AutonomousAgent.init(allocator, "Complete tasks", 20);
    defer agent.deinit();

    try agent.addGoal("Task 1", 10);
    try agent.addGoal("Task 2", 5);

    var result = try agent.run();
    defer result.deinit();

    try testing.expect(result.iterations > 0);
    try testing.expect(result.results.items.len > 0);
}

test "AutonomousAgent stops when goals complete" {
    const allocator = testing.allocator;

    var agent = try AutonomousAgent.init(allocator, "Test", 100);
    defer agent.deinit();

    try agent.addGoal("Quick task", 1);

    var result = try agent.run();
    defer result.deinit();

    // Should stop before 100 iterations when goal completes
    try testing.expect(result.iterations < 100);
}

test "AutonomousAgent cannot run twice simultaneously" {
    const allocator = testing.allocator;

    var agent = try AutonomousAgent.init(allocator, "Test", 10);
    defer agent.deinit();

    agent.is_running = true;

    const result = agent.run();
    try testing.expectError(AgentError.InvalidInput, result);

    agent.is_running = false;
}

test "defaultWorker updates progress" {
    const allocator = testing.allocator;

    var goal = try Goal.init(allocator, "Test", 1);
    defer goal.deinit();

    const initial_progress = goal.progress;

    const result = try defaultWorker(allocator, &goal);
    defer allocator.free(result);

    try testing.expect(goal.progress > initial_progress);
    try testing.expect(std.mem.indexOf(u8, result, "Test") != null);
}

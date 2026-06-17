/// Planning Pattern - Task Decomposition and Execution
///
/// The Planning pattern breaks complex tasks into manageable steps and executes
/// them in order, handling dependencies and potential failures.
///
/// # Key Concepts
///
/// - **Plan**: Collection of steps to accomplish a goal
/// - **PlanStep**: Individual actionable step with dependencies
/// - **StepExecutor**: Function for executing steps
/// - **Dynamic Replanning**: Adapt plan when steps fail (future work)
///
/// # Use Cases
///
/// - Multi-step task coordination
/// - Tasks requiring specific ordering
/// - Complex workflows with dependencies
/// - Adaptive task execution
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
///     var agent = try agenkit.patterns.PlanningAgent.init(
///         allocator,
///         10, // max_steps
///         false, // allow_replanning
///     );
///     defer agent.deinit();
///
///     var msg = try agenkit.Message.withText(allocator, .user, "Organize a team event");
///     defer msg.deinit();
///
///     const result = try agent.agent().process(msg);
///     var response = try result.unwrap();
///     defer response.deinit();
/// }
/// ```
const std = @import("std");
const Allocator = std.mem.Allocator;
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const StreamCallbacks = @import("../agent.zig").StreamCallbacks;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Result = @import("../agent.zig").Result;

/// Status of a plan step
pub const StepStatus = enum {
    /// Step not yet started
    pending,
    /// Step currently executing
    in_progress,
    /// Step completed successfully
    completed,
    /// Step failed with error
    failed,
    /// Step was skipped
    skipped,

    pub fn toString(self: StepStatus) []const u8 {
        return switch (self) {
            .pending => "pending",
            .in_progress => "in_progress",
            .completed => "completed",
            .failed => "failed",
            .skipped => "skipped",
        };
    }
};

/// A single step in a plan
pub const PlanStep = struct {
    /// Description of what this step should accomplish
    description: []const u8,
    /// Step indices that must complete before this step (0-indexed)
    dependencies: std.ArrayList(usize),
    /// Current status of the step
    status: StepStatus,
    /// Result from executing the step (if completed)
    result: ?[]const u8,
    /// Error message if step failed
    error_msg: ?[]const u8,
    /// Position in the plan (0-indexed)
    step_number: usize,
    allocator: Allocator,

    pub fn init(allocator: Allocator, description: []const u8, step_number: usize, dependencies: []const usize) !PlanStep {
        var deps = std.ArrayList(usize).empty;
        try deps.appendSlice(allocator, dependencies);

        return PlanStep{
            .description = try allocator.dupe(u8, description),
            .dependencies = deps,
            .status = .pending,
            .result = null,
            .error_msg = null,
            .step_number = step_number,
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *PlanStep) void {
        self.allocator.free(self.description);
        self.dependencies.deinit(self.allocator);
        if (self.result) |r| {
            self.allocator.free(r);
        }
        if (self.error_msg) |e| {
            self.allocator.free(e);
        }
    }

    /// Check if this step's dependencies are met
    pub fn canExecute(self: *const PlanStep, completed_steps: []const usize) bool {
        for (self.dependencies.items) |dep| {
            var found = false;
            for (completed_steps) |completed| {
                if (dep == completed) {
                    found = true;
                    break;
                }
            }
            if (!found) {
                return false;
            }
        }
        return true;
    }

    /// Set the result after successful execution
    pub fn setResult(self: *PlanStep, result: []const u8) !void {
        if (self.result) |old_result| {
            self.allocator.free(old_result);
        }
        self.result = try self.allocator.dupe(u8, result);
        self.status = .completed;
    }

    /// Set error message after failed execution
    pub fn setError(self: *PlanStep, error_msg: []const u8) !void {
        if (self.error_msg) |old_error| {
            self.allocator.free(old_error);
        }
        self.error_msg = try self.allocator.dupe(u8, error_msg);
        self.status = .failed;
    }
};

/// A plan consisting of multiple steps
pub const Plan = struct {
    /// The overall goal the plan aims to achieve
    goal: []const u8,
    /// List of steps in the plan
    steps: std.ArrayList(PlanStep),
    allocator: Allocator,

    pub fn init(allocator: Allocator, goal: []const u8) !Plan {
        return Plan{
            .goal = try allocator.dupe(u8, goal),
            .steps = std.ArrayList(PlanStep).empty,
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *Plan) void {
        self.allocator.free(self.goal);
        for (self.steps.items) |*step| {
            step.deinit();
        }
        self.steps.deinit(self.allocator);
    }

    /// Add a step to the plan
    pub fn addStep(self: *Plan, step: PlanStep) !void {
        try self.steps.append(self.allocator, step);
    }

    /// Get all steps that can be executed now
    pub fn getNextSteps(self: *const Plan, allocator: Allocator) !std.ArrayList(usize) {
        // Get completed step indices
        var completed = std.ArrayList(usize).empty;
        defer completed.deinit(allocator);

        for (self.steps.items, 0..) |step, i| {
            if (step.status == .completed) {
                try completed.append(allocator, i);
            }
        }

        // Find pending steps with met dependencies
        var next = std.ArrayList(usize).empty;
        for (self.steps.items) |step| {
            if (step.status == .pending and step.canExecute(completed.items)) {
                try next.append(allocator, step.step_number);
            }
        }

        return next;
    }

    /// Check if all steps are completed or skipped
    pub fn isComplete(self: *const Plan) bool {
        for (self.steps.items) |step| {
            if (step.status != .completed and step.status != .skipped) {
                return false;
            }
        }
        return true;
    }

    /// Check if any steps failed
    pub fn hasFailures(self: *const Plan) bool {
        for (self.steps.items) |step| {
            if (step.status == .failed) {
                return true;
            }
        }
        return false;
    }

    /// Get completion progress as a percentage
    pub fn getProgress(self: *const Plan) f64 {
        if (self.steps.items.len == 0) {
            return 0.0;
        }

        var completed: usize = 0;
        for (self.steps.items) |step| {
            if (step.status == .completed or step.status == .skipped) {
                completed += 1;
            }
        }

        return (@as(f64, @floatFromInt(completed)) / @as(f64, @floatFromInt(self.steps.items.len))) * 100.0;
    }
};

/// Function signature for step execution
pub const StepExecutorFn = *const fn (allocator: Allocator, step: *const PlanStep) AgentError![]const u8;

/// Default step executor that returns mock results
pub fn defaultStepExecutor(allocator: Allocator, step: *const PlanStep) AgentError![]const u8 {
    const result = std.fmt.allocPrint(allocator, "Completed: {s}", .{step.description}) catch {
        return AgentError.ProcessingFailed;
    };
    return result;
}

/// Agent that creates and executes plans for complex tasks
pub const PlanningAgent = struct {
    allocator: Allocator,
    max_steps: usize,
    allow_replanning: bool,
    system_prompt: []const u8,
    agent_name: []const u8,
    executor: StepExecutorFn,

    pub fn init(
        allocator: Allocator,
        max_steps: usize,
        allow_replanning: bool,
    ) !PlanningAgent {
        if (max_steps == 0) {
            return AgentError.InvalidInput;
        }

        const system_prompt = try std.fmt.allocPrint(allocator,
            \\You are a planning agent that breaks down complex tasks into steps.
            \\
            \\For each task, create a plan with specific, actionable steps.
            \\
            \\Format your plan as:
            \\Goal: [overall goal]
            \\Steps:
            \\1. [first step]
            \\2. [second step]
            \\...
            \\
            \\Maximum {d} steps.
            \\
            \\Guidelines:
            \\- Make steps concrete and actionable
            \\- Consider dependencies between steps
            \\- Keep steps focused and achievable
            \\- Include verification steps when appropriate
        , .{max_steps});

        return PlanningAgent{
            .allocator = allocator,
            .max_steps = max_steps,
            .allow_replanning = allow_replanning,
            .system_prompt = system_prompt,
            .agent_name = try allocator.dupe(u8, "PlanningAgent"),
            .executor = defaultStepExecutor,
        };
    }

    pub fn deinit(self: *PlanningAgent) void {
        self.allocator.free(self.system_prompt);
        self.allocator.free(self.agent_name);
    }

    /// Set a custom step executor
    pub fn setExecutor(self: *PlanningAgent, executor: StepExecutorFn) void {
        self.executor = executor;
    }

    /// Create a plan for the given task (simulated for demo)
    fn createPlan(self: *PlanningAgent, task: []const u8) !Plan {
        // Simulate LLM plan creation
        // In production, this would call an actual LLM
        const plan_text = self.simulateLLMPlan(task) catch {
            return AgentError.ProcessingFailed;
        };
        defer self.allocator.free(plan_text);

        const plan = self.parsePlan(plan_text, task) catch {
            return AgentError.ProcessingFailed;
        };

        return plan;
    }

    /// Simulate LLM plan generation (mock implementation)
    fn simulateLLMPlan(self: *PlanningAgent, task: []const u8) ![]const u8 {
        // Simple mock: create a basic plan based on task keywords
        if (std.mem.indexOf(u8, task, "event") != null) {
            return self.allocator.dupe(u8,
                \\Goal: Organize a team event
                \\Steps:
                \\1. Choose event date and time
                \\2. Select venue
                \\3. Send invitations to team
                \\4. Plan activities and agenda
                \\5. Arrange catering
            );
        } else if (std.mem.indexOf(u8, task, "project") != null) {
            return self.allocator.dupe(u8,
                \\Goal: Complete the project
                \\Steps:
                \\1. Define project requirements
                \\2. Create project timeline
                \\3. Assign tasks to team members
                \\4. Monitor progress
                \\5. Review and finalize deliverables
            );
        } else {
            return std.fmt.allocPrint(self.allocator,
                \\Goal: {s}
                \\Steps:
                \\1. Analyze the task
                \\2. Break down into subtasks
                \\3. Execute each subtask
                \\4. Verify results
            , .{task});
        }
    }

    /// Parse LLM response into a Plan object
    fn parsePlan(self: *PlanningAgent, plan_text: []const u8, default_goal: []const u8) !Plan {
        var plan = try Plan.init(self.allocator, default_goal);
        errdefer plan.deinit();

        var lines = std.mem.splitScalar(u8, plan_text, '\n');
        var in_steps_section = false;
        var step_number: usize = 0;

        while (lines.next()) |line| {
            const trimmed = std.mem.trim(u8, line, " \t\r");

            if (trimmed.len == 0) continue;

            // Check for goal line
            if (std.mem.startsWith(u8, trimmed, "Goal:")) {
                const goal_text = std.mem.trim(u8, trimmed[5..], " \t\r");
                if (goal_text.len > 0) {
                    self.allocator.free(plan.goal);
                    plan.goal = try self.allocator.dupe(u8, goal_text);
                }
                continue;
            }

            // Check for steps section
            if (std.mem.startsWith(u8, trimmed, "Steps:")) {
                in_steps_section = true;
                continue;
            }

            // Parse step lines
            if (in_steps_section and trimmed.len > 0) {
                // Try to extract step text after number
                var step_text = trimmed;

                // Handle "1. " format
                if (trimmed.len > 2 and std.ascii.isDigit(trimmed[0])) {
                    var i: usize = 1;
                    while (i < trimmed.len and std.ascii.isDigit(trimmed[i])) : (i += 1) {}
                    if (i < trimmed.len and (trimmed[i] == '.' or trimmed[i] == ')')) {
                        i += 1;
                        while (i < trimmed.len and (trimmed[i] == ' ' or trimmed[i] == '\t')) : (i += 1) {}
                        if (i < trimmed.len) {
                            step_text = trimmed[i..];
                        }
                    }
                }

                if (step_text.len > 0 and step_number < self.max_steps) {
                    const step = try PlanStep.init(self.allocator, step_text, step_number, &[_]usize{});
                    try plan.addStep(step);
                    step_number += 1;
                }
            }
        }

        return plan;
    }

    /// Execute all steps in the plan
    fn executePlan(self: *PlanningAgent, plan: *Plan) ![]const u8 {
        var results = std.ArrayList([]const u8).empty;
        defer {
            for (results.items) |r| {
                self.allocator.free(r);
            }
            results.deinit(self.allocator);
        }

        while (!plan.isComplete()) {
            // Get next executable steps
            var next_step_numbers = plan.getNextSteps(self.allocator) catch {
                return AgentError.ProcessingFailed;
            };
            defer next_step_numbers.deinit(self.allocator);

            if (next_step_numbers.items.len == 0) {
                // No steps can execute
                if (plan.hasFailures() and self.allow_replanning) {
                    // Could implement replanning here
                    break;
                }
                break;
            }

            // Execute next steps
            for (next_step_numbers.items) |step_num| {
                var step = &plan.steps.items[step_num];
                step.status = .in_progress;

                // Execute the step
                const result = self.executor(self.allocator, step) catch |err| {
                    const error_msg = std.fmt.allocPrint(self.allocator, "Execution failed: {s}", .{@errorName(err)}) catch {
                        return AgentError.ProcessingFailed;
                    };
                    step.setError(error_msg) catch {};
                    self.allocator.free(error_msg);

                    const fail_msg = std.fmt.allocPrint(self.allocator, "Step {d}: {s} ✗", .{ step_num + 1, step.description }) catch {
                        return AgentError.ProcessingFailed;
                    };
                    try results.append(self.allocator, fail_msg);
                    continue;
                };

                step.setResult(result) catch {
                    return AgentError.ProcessingFailed;
                };
                self.allocator.free(result);

                const success_msg = std.fmt.allocPrint(self.allocator, "Step {d}: {s} ✓", .{ step_num + 1, step.description }) catch {
                    return AgentError.ProcessingFailed;
                };
                try results.append(self.allocator, success_msg);
            }
        }

        // Generate summary
        var summary = std.ArrayList(u8).empty;
        defer summary.deinit(self.allocator);

        for (results.items) |r| {
            summary.appendSlice(self.allocator, r) catch {
                return AgentError.ProcessingFailed;
            };
            summary.append(self.allocator, '\n') catch {
                return AgentError.ProcessingFailed;
            };
        }

        const progress = plan.getProgress();

        if (plan.isComplete()) {
            const final_msg = std.fmt.allocPrint(self.allocator, "\n\nPlan completed successfully ({d:.0}%)", .{progress}) catch {
                return AgentError.ProcessingFailed;
            };
            defer self.allocator.free(final_msg);
            summary.appendSlice(self.allocator, final_msg) catch {
                return AgentError.ProcessingFailed;
            };
        } else if (plan.hasFailures()) {
            const final_msg = std.fmt.allocPrint(self.allocator, "\n\nPlan failed ({d:.0}% complete)", .{progress}) catch {
                return AgentError.ProcessingFailed;
            };
            defer self.allocator.free(final_msg);
            summary.appendSlice(self.allocator, final_msg) catch {
                return AgentError.ProcessingFailed;
            };
        } else {
            const final_msg = std.fmt.allocPrint(self.allocator, "\n\nPlan partially completed ({d:.0}%)", .{progress}) catch {
                return AgentError.ProcessingFailed;
            };
            defer self.allocator.free(final_msg);
            summary.appendSlice(self.allocator, final_msg) catch {
                return AgentError.ProcessingFailed;
            };
        }

        return summary.toOwnedSlice(self.allocator) catch {
            return AgentError.ProcessingFailed;
        };
    }

    /// Get the Agent interface for this PlanningAgent
    pub fn agent(self: *PlanningAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .process = processImpl,
                .process_stream = processStreamImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
            },
        };
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *PlanningAgent = @ptrCast(@alignCast(ptr));

        const task = message.contentAsText() catch {
            return AgentError.InvalidInput;
        };

        // Create plan
        var plan = self.createPlan(task) catch {
            return AgentError.ProcessingFailed;
        };
        defer plan.deinit();

        // Execute plan
        const result = self.executePlan(&plan) catch {
            return AgentError.ProcessingFailed;
        };
        defer self.allocator.free(result);

        // Count completed steps
        var completed: usize = 0;
        for (plan.steps.items) |step| {
            if (step.status == .completed) {
                completed += 1;
            }
        }

        const content = std.fmt.allocPrint(self.allocator, "Task completed.\n\nGoal: {s}\n\nSteps completed: {d}/{d}\n\nResult:\n{s}", .{
            plan.goal,
            completed,
            plan.steps.items.len,
            result,
        }) catch {
            return AgentError.ProcessingFailed;
        };
        defer self.allocator.free(content);

        const response = Message.withText(self.allocator, .assistant, content) catch {
            return AgentError.ProcessingFailed;
        };

        return Result{ .ok = response };
    }

    fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!IntrospectionResult {
        const caps = try capabilitiesImpl(ptr, alloc);
        defer {
            for (caps) |cap| alloc.free(cap);
            alloc.free(caps);
        }
        const name_str = nameImpl(ptr);
        return createDefaultIntrospectionResult(alloc, name_str, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *PlanningAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *PlanningAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = [_][]const u8{ "planning", "task_decomposition", "step_execution" };
        const result = try allocator.alloc([]const u8, caps.len);
        for (caps, 0..) |cap, i| {
            result[i] = try allocator.dupe(u8, cap);
        }
        return result;
    }
};

// Tests
const testing = std.testing;

fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
    _ = ptr;
    _ = message;
    callbacks.onError(AgentError.NotImplemented);
}

test "StepStatus toString" {
    try testing.expectEqualStrings("pending", StepStatus.pending.toString());
    try testing.expectEqualStrings("completed", StepStatus.completed.toString());
    try testing.expectEqualStrings("failed", StepStatus.failed.toString());
}

test "PlanStep creation and dependencies" {
    const allocator = testing.allocator;

    var step = try PlanStep.init(allocator, "Test step", 0, &[_]usize{});
    defer step.deinit();

    try testing.expectEqualStrings("Test step", step.description);
    try testing.expectEqual(@as(usize, 0), step.step_number);
    try testing.expectEqual(StepStatus.pending, step.status);
    try testing.expectEqual(@as(usize, 0), step.dependencies.items.len);
}

test "PlanStep canExecute" {
    const allocator = testing.allocator;

    var step = try PlanStep.init(allocator, "Test step", 2, &[_]usize{ 0, 1 });
    defer step.deinit();

    const completed_all = [_]usize{ 0, 1 };
    const completed_partial = [_]usize{0};
    const completed_none = [_]usize{};

    try testing.expect(step.canExecute(&completed_all));
    try testing.expect(!step.canExecute(&completed_partial));
    try testing.expect(!step.canExecute(&completed_none));
}

test "Plan creation and progress" {
    const allocator = testing.allocator;

    var plan = try Plan.init(allocator, "Test goal");
    defer plan.deinit();

    try testing.expectEqualStrings("Test goal", plan.goal);
    try testing.expectEqual(@as(usize, 0), plan.steps.items.len);
    try testing.expectEqual(@as(f64, 0.0), plan.getProgress());
}

test "Plan addStep and getProgress" {
    const allocator = testing.allocator;

    var plan = try Plan.init(allocator, "Test goal");
    defer plan.deinit();

    const step1 = try PlanStep.init(allocator, "Step 1", 0, &[_]usize{});
    try plan.addStep(step1);

    const step2 = try PlanStep.init(allocator, "Step 2", 1, &[_]usize{});
    try plan.addStep(step2);

    try testing.expectEqual(@as(usize, 2), plan.steps.items.len);
    try testing.expectEqual(@as(f64, 0.0), plan.getProgress());

    plan.steps.items[0].status = .completed;
    const progress = plan.getProgress();
    try testing.expect(progress > 49.0 and progress < 51.0); // ~50%

    plan.steps.items[1].status = .completed;
    try testing.expectEqual(@as(f64, 100.0), plan.getProgress());
}

test "Plan isComplete and hasFailures" {
    const allocator = testing.allocator;

    var plan = try Plan.init(allocator, "Test goal");
    defer plan.deinit();

    const step1 = try PlanStep.init(allocator, "Step 1", 0, &[_]usize{});
    try plan.addStep(step1);

    try testing.expect(!plan.isComplete());
    try testing.expect(!plan.hasFailures());

    plan.steps.items[0].status = .completed;
    try testing.expect(plan.isComplete());
    try testing.expect(!plan.hasFailures());

    plan.steps.items[0].status = .failed;
    try testing.expect(!plan.isComplete());
    try testing.expect(plan.hasFailures());
}

test "PlanningAgent creation" {
    const allocator = testing.allocator;

    var agent = try PlanningAgent.init(allocator, 10, false);
    defer agent.deinit();

    try testing.expectEqualStrings("PlanningAgent", agent.agent_name);
    try testing.expectEqual(@as(usize, 10), agent.max_steps);
    try testing.expect(!agent.allow_replanning);
}

test "PlanningAgent validation" {
    const allocator = testing.allocator;

    // Test max_steps = 0
    const result = PlanningAgent.init(allocator, 0, false);
    try testing.expectError(AgentError.InvalidInput, result);
}

test "PlanningAgent parsePlan" {
    const allocator = testing.allocator;

    var agent = try PlanningAgent.init(allocator, 10, false);
    defer agent.deinit();

    const plan_text =
        \\Goal: Test goal
        \\Steps:
        \\1. Step one
        \\2. Step two
        \\3. Step three
    ;

    var plan = try agent.parsePlan(plan_text, "Default goal");
    defer plan.deinit();

    try testing.expectEqualStrings("Test goal", plan.goal);
    try testing.expectEqual(@as(usize, 3), plan.steps.items.len);
    try testing.expectEqualStrings("Step one", plan.steps.items[0].description);
    try testing.expectEqualStrings("Step two", plan.steps.items[1].description);
    try testing.expectEqualStrings("Step three", plan.steps.items[2].description);
}

test "defaultStepExecutor" {
    const allocator = testing.allocator;

    var step = try PlanStep.init(allocator, "Test step", 0, &[_]usize{});
    defer step.deinit();

    const result = try defaultStepExecutor(allocator, &step);
    defer allocator.free(result);

    try testing.expectEqualStrings("Completed: Test step", result);
}

test "PlanningAgent basic flow" {
    const allocator = testing.allocator;

    var planning_agent = try PlanningAgent.init(allocator, 10, false);
    defer planning_agent.deinit();

    var msg = try Message.withText(allocator, .user, "Organize a team event");
    defer msg.deinit();

    const result = try planning_agent.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const content = try response.contentAsText();
    try testing.expect(std.mem.indexOf(u8, content, "Task completed") != null);
    try testing.expect(std.mem.indexOf(u8, content, "Steps completed") != null);
}

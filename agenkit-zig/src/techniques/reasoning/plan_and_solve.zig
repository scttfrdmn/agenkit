/// Plan-and-Solve Prompting Technique
///
/// Explicitly separates planning (devising a solution strategy) from solving
/// (executing the strategy). Creates more structured reasoning than pure CoT
/// by forcing an upfront planning phase.
///
/// Reference: "Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning"
/// Lei Wang et al., 2023 - https://arxiv.org/abs/2305.04091

const std = @import("std");
const Agent = @import("../../agent.zig").Agent;
const AgentError = @import("../../agent.zig").AgentError;
const Result = @import("../../agent.zig").Result;
const Message = @import("../../message.zig").Message;
const Allocator = std.mem.Allocator;

/// A single step in a solution plan
pub const PlanStep = struct {
    description: []const u8,
    order: usize,
    dependencies: []usize,
    estimated_complexity: usize,
    result: ?[]const u8,
    executed: bool,

    pub fn init(allocator: Allocator, desc: []const u8, order: usize) !PlanStep {
        const description = try allocator.dupe(u8, desc);
        const dependencies = try allocator.alloc(usize, 0);
        return PlanStep{
            .description = description,
            .order = order,
            .dependencies = dependencies,
            .estimated_complexity = 1,
            .result = null,
            .executed = false,
        };
    }

    pub fn deinit(self: *PlanStep, allocator: Allocator) void {
        allocator.free(self.description);
        allocator.free(self.dependencies);
        if (self.result) |r| {
            allocator.free(r);
        }
    }
};

/// A complete solution plan with steps
pub const Plan = struct {
    steps: std.ArrayList(PlanStep),
    problem: []const u8,
    strategy: ?[]const u8,
    validated: bool,
    validation_notes: ?[]const u8,
    allocator: Allocator,

    pub fn init(allocator: Allocator, problem: []const u8) !Plan {
        const problem_copy = try allocator.dupe(u8, problem);
        return Plan{
            .steps = std.ArrayList(PlanStep).init(allocator),
            .problem = problem_copy,
            .strategy = null,
            .validated = false,
            .validation_notes = null,
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *Plan) void {
        for (self.steps.items) |*step| {
            step.deinit(self.allocator);
        }
        self.steps.deinit();
        self.allocator.free(self.problem);
        if (self.strategy) |s| {
            self.allocator.free(s);
        }
        if (self.validation_notes) |vn| {
            self.allocator.free(vn);
        }
    }
};

/// Configuration for PlanAndSolve agent
pub const PlanAndSolveConfig = struct {
    validate_plan: bool = true,
    allow_replanning: bool = false,
};

/// Plan-and-Solve agent
pub const PlanAndSolveAgent = struct {
    allocator: Allocator,
    base_agent: Agent,
    config: PlanAndSolveConfig,
    agent_name: []const u8,

    pub fn init(
        allocator: Allocator,
        base_agent: Agent,
        config: PlanAndSolveConfig,
    ) !*PlanAndSolveAgent {
        const self = try allocator.create(PlanAndSolveAgent);
        self.* = PlanAndSolveAgent{
            .allocator = allocator,
            .base_agent = base_agent,
            .config = config,
            .agent_name = "plan_and_solve",
        };
        return self;
    }

    pub fn agent(self: *PlanAndSolveAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .process_stream = processStreamImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *PlanAndSolveAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 5);
        caps[0] = "reasoning";
        caps[1] = "planning";
        caps[2] = "plan_and_solve";
        caps[3] = "strategic_thinking";
        caps[4] = "step_by_step_execution";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *PlanAndSolveAgent = @ptrCast(@alignCast(ptr));

        const problem = message.contentAsText() catch {
            return Result{ .err = AgentError.InvalidInput };
        };

        // Create plan
        var plan = self.createPlan(problem) catch {
            return Result{ .err = AgentError.ProcessingError };
        };
        defer plan.deinit();

        // Validate plan if configured
        if (self.config.validate_plan) {
            self.validate(&plan) catch {
                return Result{ .err = AgentError.ProcessingError };
            };

            // Replan if validation failed and replanning is allowed
            if (!plan.validated and self.config.allow_replanning) {
                const improved_prompt = std.fmt.allocPrint(
                    self.allocator,
                    "The previous plan had issues. Create an improved plan.\n\n" ++
                        "Problem: {s}\n\n" ++
                        "Previous Plan Issues:\n{s}\n\n" ++
                        "Improved Plan:",
                    .{ problem, plan.validation_notes orelse "" },
                ) catch {
                    return Result{ .err = AgentError.ProcessingError };
                };
                defer self.allocator.free(improved_prompt);

                _ = self.llmCall(improved_prompt) catch {
                    return Result{ .err = AgentError.ProcessingError };
                };

                // Create and validate new plan
                plan.deinit();
                plan = self.createPlan(problem) catch {
                    return Result{ .err = AgentError.ProcessingError };
                };
                self.validate(&plan) catch {
                    return Result{ .err = AgentError.ProcessingError };
                };
            }
        }

        // Execute plan
        const execution_results = self.executePlan(&plan) catch {
            return Result{ .err = AgentError.ProcessingError };
        };
        defer {
            for (execution_results) |result| {
                self.allocator.free(result);
            }
            self.allocator.free(execution_results);
        }

        const final_solution = if (execution_results.len > 0)
            try self.allocator.dupe(u8, execution_results[execution_results.len - 1])
        else
            try self.allocator.dupe(u8, "");

        // Build response message
        var response = Message.init(self.allocator, "assistant", final_solution);
        response.metadata.put("technique", "plan_and_solve") catch {};
        response.metadata.put("num_steps", plan.steps.items.len) catch {};
        response.metadata.put("validated", plan.validated) catch {};
        if (plan.validation_notes) |vn| {
            response.metadata.put("validation_notes", vn) catch {};
        }
        response.metadata.put("allow_replanning", self.config.allow_replanning) catch {};

        return Result{ .ok = response };
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        _ = ptr;
        _ = message;
        return Result{ .err = AgentError.NotImplemented };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) AgentError![]const u8 {
        const self: *PlanAndSolveAgent = @ptrCast(@alignCast(ptr));
        return std.fmt.allocPrint(
            allocator,
            "{{\"name\":\"{s}\",\"type\":\"plan_and_solve\",\"validate_plan\":{},\"allow_replanning\":{}}}",
            .{
                self.agent_name,
                self.config.validate_plan,
                self.config.allow_replanning,
            },
        );
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *PlanAndSolveAgent = @ptrCast(@alignCast(ptr));
        const allocator = self.allocator;
        allocator.destroy(self);
    }

    // Helper methods
    fn llmCall(self: *PlanAndSolveAgent, prompt: []const u8) ![]const u8 {
        const message = Message.init(self.allocator, "user", prompt);
        defer message.deinit();

        const result = try self.base_agent.vtable.process(self.base_agent.ptr, message);
        switch (result) {
            .ok => |msg| {
                defer msg.deinit();
                return msg.contentAsText();
            },
            .err => return AgentError.ProcessingError,
        }
    }

    fn createPlan(self: *PlanAndSolveAgent, problem: []const u8) !Plan {
        const prompt = try std.fmt.allocPrint(
            self.allocator,
            "Create a detailed step-by-step plan to solve this problem.\n" ++
                "List each step on a separate line, numbered 1, 2, 3, etc.\n" ++
                "Focus on WHAT needs to be done, not HOW to do it yet.\n\n" ++
                "Problem: {s}\n\n" ++
                "Solution Plan:",
            .{problem},
        );
        defer self.allocator.free(prompt);

        const response = try self.llmCall(prompt);
        defer self.allocator.free(response);

        var plan = try Plan.init(self.allocator, problem);
        errdefer plan.deinit();

        // Parse numbered lines
        var lines = std.mem.splitScalar(u8, response, '\n');
        var order: usize = 0;

        while (lines.next()) |line| {
            const trimmed = std.mem.trim(u8, line, &std.ascii.whitespace);
            if (trimmed.len == 0) continue;

            // Remove numbering (digits, dots, closing parentheses)
            var start: usize = 0;
            while (start < trimmed.len and
                (std.ascii.isDigit(trimmed[start]) or
                trimmed[start] == '.' or
                trimmed[start] == ')' or
                std.ascii.isWhitespace(trimmed[start])))
            {
                start += 1;
            }

            if (start < trimmed.len) {
                const cleaned = trimmed[start..];
                const step = try PlanStep.init(self.allocator, cleaned, order);
                try plan.steps.append(step);
                order += 1;
            }
        }

        return plan;
    }

    fn validate(self: *PlanAndSolveAgent, plan: *Plan) !void {
        const plan_formatted = try self.formatPlan(plan);
        defer self.allocator.free(plan_formatted);

        const prompt = try std.fmt.allocPrint(
            self.allocator,
            "Review this solution plan for completeness and feasibility.\n" ++
                "Is this plan sufficient to solve the problem? Are there any missing steps or issues?\n\n" ++
                "Problem: {s}\n\n" ++
                "Plan:\n{s}\n\n" ++
                "Validation (answer \"VALID\" or describe issues):",
            .{ plan.problem, plan_formatted },
        );
        defer self.allocator.free(prompt);

        const response = try self.llmCall(prompt);
        defer self.allocator.free(response);

        // Check if response contains "VALID" or "YES" (case insensitive)
        const response_upper = try std.ascii.allocUpperString(self.allocator, response);
        defer self.allocator.free(response_upper);

        plan.validated = std.mem.indexOf(u8, response_upper, "VALID") != null or
            std.mem.indexOf(u8, response_upper, "YES") != null;

        const trimmed = std.mem.trim(u8, response, &std.ascii.whitespace);
        plan.validation_notes = try self.allocator.dupe(u8, trimmed);
    }

    fn formatPlan(self: *PlanAndSolveAgent, plan: *Plan) ![]const u8 {
        var buffer = std.ArrayList(u8).init(self.allocator);
        defer buffer.deinit();

        const writer = buffer.writer();

        for (plan.steps.items, 0..) |step, i| {
            const status: []const u8 = if (step.executed) "✓" else "○";
            try writer.print("{}. [{}] {s}", .{ i + 1, status, step.description });
            if (i < plan.steps.items.len - 1) {
                try writer.writeByte('\n');
            }
        }

        return buffer.toOwnedSlice();
    }

    fn executeStep(
        self: *PlanAndSolveAgent,
        step: *const PlanStep,
        previous_results: []const []const u8,
    ) ![]const u8 {
        const prompt = if (previous_results.len > 0) blk: {
            var buffer = std.ArrayList(u8).init(self.allocator);
            defer buffer.deinit();

            const writer = buffer.writer();
            try writer.writeAll("Execute this step of the plan, using previous results as context.\n\n");
            try writer.writeAll("Previous Results:\n");

            for (previous_results, 0..) |result, i| {
                try writer.print("Previous step {} result: {s}\n", .{ i + 1, result });
            }

            try writer.print("\nCurrent Step: {s}\n\n", .{step.description});
            try writer.writeAll("Execution Result:");

            break :blk try buffer.toOwnedSlice();
        } else blk: {
            break :blk try std.fmt.allocPrint(
                self.allocator,
                "Execute this step of the plan:\n\n" ++
                    "Step: {s}\n\n" ++
                    "Execution Result:",
                .{step.description},
            );
        };
        defer self.allocator.free(prompt);

        const result = try self.llmCall(prompt);
        const trimmed = std.mem.trim(u8, result, &std.ascii.whitespace);
        const result_copy = try self.allocator.dupe(u8, trimmed);
        self.allocator.free(result);

        return result_copy;
    }

    fn executePlan(self: *PlanAndSolveAgent, plan: *Plan) ![][]const u8 {
        var results = std.ArrayList([]const u8).init(self.allocator);
        errdefer {
            for (results.items) |result| {
                self.allocator.free(result);
            }
            results.deinit();
        }

        for (plan.steps.items) |*step| {
            const result = try self.executeStep(step, results.items);
            try results.append(result);
            step.result = result;
            step.executed = true;
        }

        return results.toOwnedSlice();
    }
};

// Tests
test "PlanStep initialization" {
    const allocator = std.testing.allocator;

    var step = try PlanStep.init(allocator, "Test step", 0);
    defer step.deinit(allocator);

    try std.testing.expectEqualStrings("Test step", step.description);
    try std.testing.expectEqual(@as(usize, 0), step.order);
    try std.testing.expectEqual(false, step.executed);
}

test "Plan initialization" {
    const allocator = std.testing.allocator;

    var plan = try Plan.init(allocator, "Test problem");
    defer plan.deinit();

    try std.testing.expectEqualStrings("Test problem", plan.problem);
    try std.testing.expectEqual(false, plan.validated);
    try std.testing.expectEqual(@as(usize, 0), plan.steps.items.len);
}

test "Plan with steps" {
    const allocator = std.testing.allocator;

    var plan = try Plan.init(allocator, "Solve equation");
    defer plan.deinit();

    const step1 = try PlanStep.init(allocator, "Simplify left side", 0);
    try plan.steps.append(step1);

    const step2 = try PlanStep.init(allocator, "Simplify right side", 1);
    try plan.steps.append(step2);

    try std.testing.expectEqual(@as(usize, 2), plan.steps.items.len);
    try std.testing.expectEqualStrings("Simplify left side", plan.steps.items[0].description);
    try std.testing.expectEqualStrings("Simplify right side", plan.steps.items[1].description);
}

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
const StreamCallbacks = @import("../../agent.zig").StreamCallbacks;
const Message = @import("../../message.zig").Message;
const CallOptions = @import("../../call_options.zig").CallOptions;
const IntrospectionResult = @import("../../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../../introspection.zig").createDefaultIntrospectionResult;
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
        errdefer allocator.free(description);
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
    steps: std.ArrayListUnmanaged(PlanStep),
    problem: []const u8,
    strategy: ?[]const u8,
    validated: bool,
    validation_notes: ?[]const u8,
    allocator: Allocator,

    pub fn init(allocator: Allocator, problem: []const u8) !Plan {
        const problem_copy = try allocator.dupe(u8, problem);
        return Plan{
            .steps = std.ArrayListUnmanaged(PlanStep).empty,
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
        self.steps.deinit(self.allocator);
        self.allocator.free(self.problem);
        if (self.strategy) |s| {
            self.allocator.free(s);
        }
        if (self.validation_notes) |vn| {
            self.allocator.free(vn);
        }
    }

    /// Append a step, taking ownership of it.
    ///
    /// Provided so callers do not have to thread the allocator through a second
    /// time — the plan already owns one.
    pub fn addStep(self: *Plan, step: PlanStep) !void {
        try self.steps.append(self.allocator, step);
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
                .process_with = processWithImpl,
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

        var empty = CallOptions.init(self.allocator);
        defer empty.deinit();
        return self.run(message, &empty);
    }

    /// Implements the optional `processWith` capability (#801).
    ///
    /// The options reach every phase: planning, validation, each step's
    /// execution, and the replanning branch — which issues a feedback call and
    /// then a second plan-and-validate round. That branch is the easy one to
    /// miss, and missing it would mean a retried problem silently ran at
    /// different settings from the first attempt.
    fn processWithImpl(ptr: *anyopaque, message: Message, options: *const CallOptions) AgentError!Result {
        const self: *PlanAndSolveAgent = @ptrCast(@alignCast(ptr));
        return self.run(message, options);
    }

    /// Shared body for both entry points.
    ///
    /// Allocation failures are mapped to ProcessingFailed rather than
    /// propagated: the vtable signature is AgentError!Result, which does not
    /// include Allocator.Error.
    fn run(self: *PlanAndSolveAgent, message: Message, options: *const CallOptions) AgentError!Result {
        return self.processInner(message, options) catch |err| switch (err) {
            error.OutOfMemory => Result{ .err = AgentError.ProcessingFailed },
            else => |e| Result{ .err = e },
        };
    }

    /// The real body, allowed to fail with Allocator.Error.
    ///
    /// Split out so `try` can be used on allocating calls; `run` narrows the
    /// error set back down to what the Agent vtable declares.
    fn processInner(self: *PlanAndSolveAgent, message: Message, options: *const CallOptions) (AgentError || Allocator.Error)!Result {
        const problem = message.contentAsText() catch {
            return Result{ .err = AgentError.InvalidInput };
        };

        // Phase 1: create the plan
        var plan = self.createPlan(problem, options) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };
        defer plan.deinit();

        // Phase 2: validate the plan, if configured
        if (self.config.validate_plan) {
            self.validate(&plan, options) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };

            // Replan if validation rejected the plan and replanning is allowed
            if (!plan.validated and self.config.allow_replanning) {
                const improved_prompt = std.fmt.allocPrint(
                    self.allocator,
                    "The previous plan had issues. Create an improved plan.\n\n" ++
                        "Problem: {s}\n\n" ++
                        "Previous Plan Issues:\n{s}\n\n" ++
                        "Improved Plan:",
                    .{ problem, plan.validation_notes orelse "" },
                ) catch {
                    return Result{ .err = AgentError.ProcessingFailed };
                };
                defer self.allocator.free(improved_prompt);

                const feedback = self.llmCall(improved_prompt, options) catch {
                    return Result{ .err = AgentError.ProcessingFailed };
                };
                self.allocator.free(feedback);

                // Replace the plan wholesale, then validate the replacement.
                plan.deinit();
                plan = self.createPlan(problem, options) catch {
                    return Result{ .err = AgentError.ProcessingFailed };
                };
                self.validate(&plan, options) catch {
                    return Result{ .err = AgentError.ProcessingFailed };
                };
            }
        }

        // Phase 3: execute the plan
        const execution_results = self.executePlan(&plan, options) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };
        defer {
            for (execution_results) |result| {
                self.allocator.free(result);
            }
            self.allocator.free(execution_results);
        }

        // Final solution is the last step's result
        const final_solution = if (execution_results.len > 0)
            execution_results[execution_results.len - 1]
        else
            "";

        // Message.withText dupes, so final_solution stays owned by
        // execution_results and is freed by the defer above.
        var response = try Message.withText(self.allocator, .assistant, final_solution);
        errdefer response.deinit();

        try response.setMetadata("technique", .{ .string = "plan_and_solve" });
        try response.setMetadata("num_steps", .{ .integer = @as(i64, @intCast(plan.steps.items.len)) });
        try response.setMetadata("validated", .{ .bool = plan.validated });
        try response.setMetadata("allow_replanning", .{ .bool = self.config.allow_replanning });

        // plan_steps and execution_steps carry per-step strings. They are
        // emitted as JSON arrays rather than as top-level strings because
        // Message.deinit only frees strings nested inside an array — a
        // dynamically allocated top-level metadata string would leak. For the
        // same reason validation_notes and strategy are not emitted here even
        // though the Python and Go cores include them; both are owned by the
        // plan, which is freed before this function returns.
        try response.setMetadata("plan_steps", .{ .array = try self.stepDescriptions(&plan) });
        try response.setMetadata("execution_steps", .{ .array = try self.dupeStrings(execution_results) });

        return Result{ .ok = response };
    }

    /// Build a JSON array of every step's description (owned copies).
    fn stepDescriptions(self: *PlanAndSolveAgent, plan: *const Plan) !std.json.Array {
        var array = std.ArrayListUnmanaged(std.json.Value).empty;
        errdefer {
            for (array.items) |item| {
                self.allocator.free(item.string);
            }
            array.deinit(self.allocator);
        }

        for (plan.steps.items) |step| {
            const owned = try self.allocator.dupe(u8, step.description);
            errdefer self.allocator.free(owned);
            try array.append(self.allocator, .{ .string = owned });
        }

        return array.toManaged(self.allocator);
    }

    /// Build a JSON array from a slice of strings (owned copies).
    fn dupeStrings(self: *PlanAndSolveAgent, strings: []const []const u8) !std.json.Array {
        var array = std.ArrayListUnmanaged(std.json.Value).empty;
        errdefer {
            for (array.items) |item| {
                self.allocator.free(item.string);
            }
            array.deinit(self.allocator);
        }

        for (strings) |s| {
            const owned = try self.allocator.dupe(u8, s);
            errdefer self.allocator.free(owned);
            try array.append(self.allocator, .{ .string = owned });
        }

        return array.toManaged(self.allocator);
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        _ = callbacks;
        return AgentError.NotImplemented;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *PlanAndSolveAgent = @ptrCast(@alignCast(ptr));
        const caps = try self.agent().capabilities(allocator);
        defer allocator.free(caps);
        return createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *PlanAndSolveAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }

    // Helper methods

    /// Send one prompt to the wrapped agent and return an owned response body.
    ///
    /// The returned slice is duped: the response Message is freed here, and
    /// contentAsText only borrows from it.
    fn llmCall(self: *PlanAndSolveAgent, prompt: []const u8, options: *const CallOptions) ![]const u8 {
        var message = try Message.withText(self.allocator, .user, prompt);
        defer message.deinit();

        const result = try self.base_agent.processWithOptions(message, options);
        var response_msg = try result.unwrap();
        defer response_msg.deinit();

        const text = try response_msg.contentAsText();
        return try self.allocator.dupe(u8, text);
    }

    fn createPlan(self: *PlanAndSolveAgent, problem: []const u8, options: *const CallOptions) !Plan {
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

        const response = try self.llmCall(prompt, options);
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
                var step = try PlanStep.init(self.allocator, cleaned, order);
                errdefer step.deinit(self.allocator);
                try plan.addStep(step);
                order += 1;
            }
        }

        return plan;
    }

    fn validate(self: *PlanAndSolveAgent, plan: *Plan, options: *const CallOptions) !void {
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

        const response = try self.llmCall(prompt, options);
        defer self.allocator.free(response);

        // Check if response contains "VALID" or "YES" (case insensitive)
        // But check for INVALID first to avoid matching "VALID" inside "INVALID"
        const response_upper = try std.ascii.allocUpperString(self.allocator, response);
        defer self.allocator.free(response_upper);

        const has_invalid = std.mem.indexOf(u8, response_upper, "INVALID") != null;
        const has_valid = std.mem.indexOf(u8, response_upper, "VALID") != null or
            std.mem.indexOf(u8, response_upper, "YES") != null;

        plan.validated = !has_invalid and has_valid;

        const trimmed = std.mem.trim(u8, response, &std.ascii.whitespace);
        const notes = try self.allocator.dupe(u8, trimmed);
        // Replacing, not accumulating: validate() may run twice when
        // replanning is enabled.
        if (plan.validation_notes) |old| {
            self.allocator.free(old);
        }
        plan.validation_notes = notes;
    }

    fn formatPlan(self: *PlanAndSolveAgent, plan: *const Plan) ![]const u8 {
        var buffer = std.ArrayListUnmanaged(u8).empty;
        defer buffer.deinit(self.allocator);

        for (plan.steps.items, 0..) |step, i| {
            const status: []const u8 = if (step.executed) "✓" else "○";
            try buffer.print(self.allocator, "{d}. [{s}] {s}", .{ i + 1, status, step.description });
            if (i + 1 < plan.steps.items.len) {
                try buffer.append(self.allocator, '\n');
            }
        }

        return buffer.toOwnedSlice(self.allocator);
    }

    fn executeStep(
        self: *PlanAndSolveAgent,
        step: *const PlanStep,
        previous_results: []const []const u8,
        options: *const CallOptions,
    ) ![]const u8 {
        const prompt = if (previous_results.len > 0) blk: {
            var buffer = std.ArrayListUnmanaged(u8).empty;
            defer buffer.deinit(self.allocator);

            try buffer.appendSlice(
                self.allocator,
                "Execute this step of the plan, using previous results as context.\n\n",
            );
            try buffer.appendSlice(self.allocator, "Previous Results:\n");

            for (previous_results, 0..) |result, i| {
                try buffer.print(self.allocator, "Previous step {d} result: {s}\n", .{ i + 1, result });
            }

            try buffer.print(self.allocator, "\nCurrent Step: {s}\n\n", .{step.description});
            try buffer.appendSlice(self.allocator, "Execution Result:");

            break :blk try buffer.toOwnedSlice(self.allocator);
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

        const result = try self.llmCall(prompt, options);
        defer self.allocator.free(result);

        const trimmed = std.mem.trim(u8, result, &std.ascii.whitespace);
        return try self.allocator.dupe(u8, trimmed);
    }

    fn executePlan(self: *PlanAndSolveAgent, plan: *Plan, options: *const CallOptions) ![][]const u8 {
        var results = std.ArrayListUnmanaged([]const u8).empty;
        errdefer {
            for (results.items) |result| {
                self.allocator.free(result);
            }
            results.deinit(self.allocator);
        }

        for (plan.steps.items) |*step| {
            const result = try self.executeStep(step, results.items, options);
            errdefer self.allocator.free(result);
            try results.append(self.allocator, result);

            // step.result gets its own copy: the returned slice is owned by the
            // caller of executePlan, and the step is freed independently by
            // Plan.deinit. Aliasing them would double-free.
            if (step.result) |old| {
                self.allocator.free(old);
            }
            step.result = try self.allocator.dupe(u8, result);
            step.executed = true;
        }

        return results.toOwnedSlice(self.allocator);
    }
};

// Tests
const testing = std.testing;

/// Mock agent replaying a fixed list of responses, cycling if exhausted.
const MockAgent = struct {
    allocator: Allocator,
    responses: []const []const u8,
    index: usize,

    fn init(allocator: Allocator, responses: []const []const u8) !*MockAgent {
        const self = try allocator.create(MockAgent);
        self.* = .{
            .allocator = allocator,
            .responses = responses,
            .index = 0,
        };
        return self;
    }

    fn agent(self: *MockAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = mockName,
                .capabilities = mockCapabilities,
                .process = mockProcess,
                .process_stream = mockProcessStream,
                .introspect = mockIntrospect,
                .deinit = mockDeinit,
            },
        };
    }

    fn mockName(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "mock_agent";
    }

    fn mockCapabilities(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 2);
        caps[0] = "mock";
        caps[1] = "testing";
        return caps;
    }

    fn mockProcess(ptr: *anyopaque, message: Message) AgentError!Result {
        _ = message;
        const self: *MockAgent = @ptrCast(@alignCast(ptr));
        const response_text = self.responses[self.index % self.responses.len];
        self.index += 1;

        const response = Message.withText(self.allocator, .assistant, response_text) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };
        return Result{ .ok = response };
    }

    fn mockProcessStream(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        _ = callbacks;
        return AgentError.NotImplemented;
    }

    fn mockIntrospect(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *MockAgent = @ptrCast(@alignCast(ptr));
        const caps = try self.agent().capabilities(allocator);
        defer allocator.free(caps);
        return createDefaultIntrospectionResult(allocator, "mock_agent", caps);
    }

    fn mockDeinit(ptr: *anyopaque) void {
        const self: *MockAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};

test "PlanStep initialization" {
    const allocator = testing.allocator;

    var step = try PlanStep.init(allocator, "Test step", 0);
    defer step.deinit(allocator);

    try testing.expectEqualStrings("Test step", step.description);
    try testing.expectEqual(@as(usize, 0), step.order);
    try testing.expectEqual(false, step.executed);
}

test "Plan initialization" {
    const allocator = testing.allocator;

    var plan = try Plan.init(allocator, "Test problem");
    defer plan.deinit();

    try testing.expectEqualStrings("Test problem", plan.problem);
    try testing.expectEqual(false, plan.validated);
    try testing.expectEqual(@as(usize, 0), plan.steps.items.len);
}

test "Plan with steps" {
    const allocator = testing.allocator;

    var plan = try Plan.init(allocator, "Solve equation");
    defer plan.deinit();

    const step1 = try PlanStep.init(allocator, "Simplify left side", 0);
    try plan.addStep(step1);

    const step2 = try PlanStep.init(allocator, "Simplify right side", 1);
    try plan.addStep(step2);

    try testing.expectEqual(@as(usize, 2), plan.steps.items.len);
    try testing.expectEqualStrings("Simplify left side", plan.steps.items[0].description);
    try testing.expectEqualStrings("Simplify right side", plan.steps.items[1].description);
}

test "PlanAndSolve name and capabilities" {
    const allocator = testing.allocator;

    const mock = try MockAgent.init(allocator, &[_][]const u8{"response"});
    defer mock.allocator.destroy(mock);

    const agent = try PlanAndSolveAgent.init(allocator, mock.agent(), .{});
    defer agent.agent().deinit();

    try testing.expectEqualStrings("plan_and_solve", agent.agent().name());

    const caps = try agent.agent().capabilities(allocator);
    defer allocator.free(caps);

    try testing.expectEqual(@as(usize, 5), caps.len);
    try testing.expectEqualStrings("reasoning", caps[0]);
    try testing.expectEqualStrings("planning", caps[1]);
    try testing.expectEqualStrings("plan_and_solve", caps[2]);
    try testing.expectEqualStrings("strategic_thinking", caps[3]);
    try testing.expectEqualStrings("step_by_step_execution", caps[4]);
}

test "PlanAndSolve basic functionality" {
    const allocator = testing.allocator;

    const mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. Gather ingredients\n2. Preheat oven\n3. Mix ingredients\n4. Bake",
        "VALID: Plan is complete",
        "Gathered: flour, sugar, eggs",
        "Preheated oven to 350°F",
        "Mixed all ingredients thoroughly",
        "Baked for 30 minutes",
    });
    defer mock.allocator.destroy(mock);

    const agent = try PlanAndSolveAgent.init(allocator, mock.agent(), .{ .validate_plan = true });
    defer agent.agent().deinit();

    var message = try Message.withText(allocator, .user, "How do I bake a cake?");
    defer message.deinit();

    const result = try agent.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    const content = try response.contentAsText();
    try testing.expect(content.len > 0);

    const technique = response.getMetadata("technique").?;
    try testing.expectEqualStrings("plan_and_solve", technique.string);
    try testing.expectEqual(@as(i64, 4), response.getMetadata("num_steps").?.integer);
    try testing.expectEqual(true, response.getMetadata("validated").?.bool);
}

test "PlanAndSolve skip validation when disabled" {
    const allocator = testing.allocator;

    const mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. Step",
        "Result",
    });
    defer mock.allocator.destroy(mock);

    const agent = try PlanAndSolveAgent.init(allocator, mock.agent(), .{ .validate_plan = false });
    defer agent.agent().deinit();

    var message = try Message.withText(allocator, .user, "Simple problem");
    defer message.deinit();

    const result = try agent.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    // With validation disabled, only two LLM calls happen: plan + execute.
    try testing.expectEqual(@as(usize, 2), mock.index);
    try testing.expectEqual(false, response.getMetadata("validated").?.bool);
}

test "PlanAndSolve handle invalid validation" {
    const allocator = testing.allocator;

    const mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. Step 1",
        "INVALID: Missing important step",
        "Result 1",
    });
    defer mock.allocator.destroy(mock);

    const agent = try PlanAndSolveAgent.init(allocator, mock.agent(), .{
        .validate_plan = true,
        .allow_replanning = false,
    });
    defer agent.agent().deinit();

    var message = try Message.withText(allocator, .user, "Problem");
    defer message.deinit();

    const result = try agent.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    // "INVALID" must not be read as "VALID": validated stays false, and with
    // replanning disabled the plan is executed as-is.
    try testing.expectEqual(false, response.getMetadata("validated").?.bool);
    try testing.expectEqual(false, response.getMetadata("allow_replanning").?.bool);
    try testing.expectEqual(@as(usize, 3), mock.index);
}

test "PlanAndSolve replans when validation rejects the plan" {
    const allocator = testing.allocator;

    // plan, INVALID, replan-feedback, plan again, VALID, execute
    const mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. Bad step",
        "INVALID: Missing important step",
        "Here is better guidance",
        "1. Good step",
        "VALID",
        "Executed the good step",
    });
    defer mock.allocator.destroy(mock);

    const agent = try PlanAndSolveAgent.init(allocator, mock.agent(), .{
        .validate_plan = true,
        .allow_replanning = true,
    });
    defer agent.agent().deinit();

    var message = try Message.withText(allocator, .user, "Problem");
    defer message.deinit();

    const result = try agent.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    // Six calls: the replanning branch adds feedback + a second plan + a
    // second validation on top of the three the non-replanning path makes.
    try testing.expectEqual(@as(usize, 6), mock.index);
    try testing.expectEqual(true, response.getMetadata("validated").?.bool);
    try testing.expectEqual(true, response.getMetadata("allow_replanning").?.bool);

    const plan_steps = response.getMetadata("plan_steps").?.array;
    try testing.expectEqual(@as(usize, 1), plan_steps.items.len);
    try testing.expectEqualStrings("Good step", plan_steps.items[0].string);
}

test "PlanAndSolve execute steps sequentially" {
    const allocator = testing.allocator;

    const mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. Step A\n2. Step B",
        "Answer A",
        "Answer B",
    });
    defer mock.allocator.destroy(mock);

    const agent = try PlanAndSolveAgent.init(allocator, mock.agent(), .{ .validate_plan = false });
    defer agent.agent().deinit();

    var message = try Message.withText(allocator, .user, "Problem");
    defer message.deinit();

    const result = try agent.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    // Final solution is the last execution result
    const content = try response.contentAsText();
    try testing.expectEqualStrings("Answer B", content);

    const execution_steps = response.getMetadata("execution_steps").?.array;
    try testing.expectEqual(@as(usize, 2), execution_steps.items.len);
    try testing.expectEqualStrings("Answer A", execution_steps.items[0].string);
    try testing.expectEqualStrings("Answer B", execution_steps.items[1].string);
}

test "PlanAndSolve handle empty plan" {
    const allocator = testing.allocator;

    const mock = try MockAgent.init(allocator, &[_][]const u8{""});
    defer mock.allocator.destroy(mock);

    const agent = try PlanAndSolveAgent.init(allocator, mock.agent(), .{ .validate_plan = false });
    defer agent.agent().deinit();

    var message = try Message.withText(allocator, .user, "Problem");
    defer message.deinit();

    const result = try agent.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    const content = try response.contentAsText();
    try testing.expectEqualStrings("", content);
    try testing.expectEqual(@as(i64, 0), response.getMetadata("num_steps").?.integer);
}

test "PlanAndSolve handle single step plan" {
    const allocator = testing.allocator;

    const mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. Only step",
        "Step result",
    });
    defer mock.allocator.destroy(mock);

    const agent = try PlanAndSolveAgent.init(allocator, mock.agent(), .{ .validate_plan = false });
    defer agent.agent().deinit();

    var message = try Message.withText(allocator, .user, "Simple task");
    defer message.deinit();

    const result = try agent.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    const content = try response.contentAsText();
    try testing.expectEqualStrings("Step result", content);
}

test "PlanAndSolve parse period numbering" {
    const allocator = testing.allocator;

    const mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. Step one\n2. Step two\n3. Step three",
    });
    defer mock.allocator.destroy(mock);

    const agent_struct = try PlanAndSolveAgent.init(allocator, mock.agent(), .{ .validate_plan = false });
    defer agent_struct.allocator.destroy(agent_struct);

    var options = CallOptions.init(allocator);
    defer options.deinit();

    var plan = try agent_struct.createPlan("Problem", &options);
    defer plan.deinit();

    try testing.expectEqual(@as(usize, 3), plan.steps.items.len);
    try testing.expectEqualStrings("Step one", plan.steps.items[0].description);
    try testing.expectEqualStrings("Step two", plan.steps.items[1].description);
    try testing.expectEqualStrings("Step three", plan.steps.items[2].description);
}

test "PlanAndSolve parse parenthesis numbering" {
    const allocator = testing.allocator;

    const mock = try MockAgent.init(allocator, &[_][]const u8{
        "1) Step one\n2) Step two",
    });
    defer mock.allocator.destroy(mock);

    const agent_struct = try PlanAndSolveAgent.init(allocator, mock.agent(), .{ .validate_plan = false });
    defer agent_struct.allocator.destroy(agent_struct);

    var options = CallOptions.init(allocator);
    defer options.deinit();

    var plan = try agent_struct.createPlan("Problem", &options);
    defer plan.deinit();

    try testing.expectEqual(@as(usize, 2), plan.steps.items.len);
    try testing.expectEqualStrings("Step one", plan.steps.items[0].description);
    try testing.expectEqualStrings("Step two", plan.steps.items[1].description);
}

test "PlanAndSolve skip empty lines" {
    const allocator = testing.allocator;

    const mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. Step one\n\n2. Step two\n\n",
    });
    defer mock.allocator.destroy(mock);

    const agent_struct = try PlanAndSolveAgent.init(allocator, mock.agent(), .{ .validate_plan = false });
    defer agent_struct.allocator.destroy(agent_struct);

    var options = CallOptions.init(allocator);
    defer options.deinit();

    var plan = try agent_struct.createPlan("Problem", &options);
    defer plan.deinit();

    try testing.expectEqual(@as(usize, 2), plan.steps.items.len);
}

test "PlanAndSolve formatPlan marks executed steps" {
    const allocator = testing.allocator;

    const mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.allocator.destroy(mock);

    const agent_struct = try PlanAndSolveAgent.init(allocator, mock.agent(), .{});
    defer agent_struct.allocator.destroy(agent_struct);

    var plan = try Plan.init(allocator, "Problem");
    defer plan.deinit();

    try plan.addStep(try PlanStep.init(allocator, "First", 0));
    try plan.addStep(try PlanStep.init(allocator, "Second", 1));
    plan.steps.items[0].executed = true;

    const formatted = try agent_struct.formatPlan(&plan);
    defer allocator.free(formatted);

    try testing.expectEqualStrings("1. [✓] First\n2. [○] Second", formatted);
}

test "PlanStep track execution state" {
    const allocator = testing.allocator;

    var step = try PlanStep.init(allocator, "Test step", 0);
    defer step.deinit(allocator);

    try testing.expectEqual(false, step.executed);

    step.executed = true;
    step.result = try allocator.dupe(u8, "Test result");

    try testing.expectEqual(true, step.executed);
    try testing.expectEqualStrings("Test result", step.result.?);
}

test "Plan track step dependencies" {
    const allocator = testing.allocator;

    var plan = try Plan.init(allocator, "Test");
    defer plan.deinit();

    const step1 = try PlanStep.init(allocator, "Step 1", 0);
    try plan.addStep(step1);

    var step2 = try PlanStep.init(allocator, "Step 2", 1);
    allocator.free(step2.dependencies);
    step2.dependencies = try allocator.alloc(usize, 1);
    step2.dependencies[0] = 0;
    try plan.addStep(step2);

    var step3 = try PlanStep.init(allocator, "Step 3", 2);
    allocator.free(step3.dependencies);
    step3.dependencies = try allocator.alloc(usize, 2);
    step3.dependencies[0] = 0;
    step3.dependencies[1] = 1;
    step3.estimated_complexity = 2;
    try plan.addStep(step3);

    // Verify step 2 depends on step 1
    try testing.expectEqual(@as(usize, 1), plan.steps.items[1].dependencies.len);
    try testing.expectEqual(@as(usize, 0), plan.steps.items[1].dependencies[0]);

    // Verify step 3 depends on steps 1 and 2
    try testing.expectEqual(@as(usize, 2), plan.steps.items[2].dependencies.len);
    try testing.expectEqual(@as(usize, 0), plan.steps.items[2].dependencies[0]);
    try testing.expectEqual(@as(usize, 1), plan.steps.items[2].dependencies[1]);

    // Verify complexity tracking
    try testing.expectEqual(@as(usize, 2), plan.steps.items[2].estimated_complexity);
}

test "Plan create valid structure" {
    const allocator = testing.allocator;

    var plan = try Plan.init(allocator, "Test problem");
    defer plan.deinit();

    try testing.expectEqualStrings("Test problem", plan.problem);
    try testing.expectEqual(@as(usize, 0), plan.steps.items.len);
    try testing.expectEqual(false, plan.validated);
}

test "Plan support optional fields" {
    const allocator = testing.allocator;

    var plan = try Plan.init(allocator, "Test");
    defer plan.deinit();

    plan.validated = true;
    plan.strategy = try allocator.dupe(u8, "Test strategy");
    plan.validation_notes = try allocator.dupe(u8, "All good");

    try testing.expectEqualStrings("Test strategy", plan.strategy.?);
    try testing.expectEqualStrings("All good", plan.validation_notes.?);
}

test "PlanStep create valid structure" {
    const allocator = testing.allocator;

    var step = try PlanStep.init(allocator, "Test step", 0);
    defer step.deinit(allocator);

    try testing.expectEqualStrings("Test step", step.description);
    try testing.expectEqual(@as(usize, 0), step.order);
    try testing.expectEqual(@as(usize, 0), step.dependencies.len);
    try testing.expectEqual(@as(usize, 1), step.estimated_complexity);
    try testing.expectEqual(false, step.executed);
}

test "PlanStep support optional result field" {
    const allocator = testing.allocator;

    var step = try PlanStep.init(allocator, "Test step", 0);
    defer step.deinit(allocator);

    step.executed = true;
    step.result = try allocator.dupe(u8, "Test result");

    try testing.expectEqualStrings("Test result", step.result.?);
}

// ============================================================================
// Per-call options forwarding (#801)
// ============================================================================

const OptionsAwareMockAgent = @import("../../test_utils.zig").OptionsAwareMockAgent;

test "PlanAndSolve forwards call options to planning, validation and execution" {
    const allocator = testing.allocator;

    var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{
        "1. First step\n2. Second step",
        "VALID",
        "First step done",
        "Second step done",
    });
    defer mock.deinit();

    const pas = try PlanAndSolveAgent.init(allocator, mock.agent(), .{ .validate_plan = true });
    const pas_agent = pas.agent();
    defer pas_agent.deinit();

    var msg = try Message.withText(allocator, .user, "A problem");
    defer msg.deinit();

    var options = CallOptions.init(allocator);
    defer options.deinit();
    try options.withTemperature(0.45);

    var response = try (try pas_agent.processWith(msg, &options)).unwrap();
    defer response.deinit();

    // Plan, validate, then one call per step — at least four. Every one of them
    // must have seen the options, not just the first.
    try testing.expect(mock.getCallCount() >= 4);
    try testing.expect(mock.allTemperaturesEqual(0.45));
}

test "PlanAndSolve forwards call options through the replanning branch" {
    const allocator = testing.allocator;

    // INVALID drives replanning: feedback call, second plan, second validate,
    // then execution. This is the branch most easily left un-threaded, because
    // it only runs when validation rejects the first plan.
    var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{
        "1. Weak step",
        "INVALID - missing steps",
        "Feedback on how to improve",
        "1. Better step\n2. Another step",
        "VALID",
        "Better step done",
        "Another step done",
    });
    defer mock.deinit();

    const pas = try PlanAndSolveAgent.init(allocator, mock.agent(), .{
        .validate_plan = true,
        .allow_replanning = true,
    });
    const pas_agent = pas.agent();
    defer pas_agent.deinit();

    var msg = try Message.withText(allocator, .user, "A problem");
    defer msg.deinit();

    var options = CallOptions.init(allocator);
    defer options.deinit();
    try options.withTemperature(1.1);

    var response = try (try pas_agent.processWith(msg, &options)).unwrap();
    defer response.deinit();

    // More calls than the non-replanning path, so the branch demonstrably ran.
    try testing.expect(mock.getCallCount() >= 6);
    try testing.expect(mock.allTemperaturesEqual(1.1));
}

test "PlanAndSolve sends no options when called through process" {
    const allocator = testing.allocator;

    var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{
        "1. Step one",
        "Step one done",
    });
    defer mock.deinit();

    const pas = try PlanAndSolveAgent.init(allocator, mock.agent(), .{ .validate_plan = false });
    const pas_agent = pas.agent();
    defer pas_agent.deinit();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var response = try (try pas_agent.process(msg)).unwrap();
    defer response.deinit();

    try testing.expect(mock.allTemperaturesEqual(null));
}

test "PlanAndSolve advertises the options capability" {
    const allocator = testing.allocator;

    var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{"x"});
    defer mock.deinit();

    const pas = try PlanAndSolveAgent.init(allocator, mock.agent(), .{});
    const pas_agent = pas.agent();
    defer pas_agent.deinit();

    try testing.expect(pas_agent.supportsOptions());
}

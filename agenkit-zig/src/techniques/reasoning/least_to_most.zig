/// Least-to-Most Prompting Technique
///
/// Breaks complex problems into simpler subproblems, solves them sequentially
/// from simplest to most complex, using solutions to build up to the final answer.
///
/// This technique is particularly effective for compositional reasoning where
/// complex problems can be decomposed into manageable pieces.
///
/// Reference: "Least-to-Most Prompting Enables Complex Reasoning in Large Language Models"
/// Zhou et al., 2022 - https://arxiv.org/abs/2205.10625
const std = @import("std");
const Agent = @import("../../agent.zig").Agent;
const AgentError = @import("../../agent.zig").AgentError;
const Result = @import("../../agent.zig").Result;
const Message = @import("../../message.zig").Message;
const CallOptions = @import("../../call_options.zig").CallOptions;
const Allocator = std.mem.Allocator;

/// Represents a subproblem in the decomposition
pub const Subproblem = struct {
    content: []const u8,
    difficulty: usize,
    dependencies: []const usize,

    pub fn deinit(self: *Subproblem, allocator: Allocator) void {
        allocator.free(self.content);
        allocator.free(self.dependencies);
    }
};

/// Custom function type for decomposing problems into subproblems
pub const DecomposerFunc = *const fn (allocator: Allocator, problem: []const u8) anyerror![][]const u8;

/// Configuration for Least-to-Most
pub const LeastToMostConfig = struct {
    decomposer: ?DecomposerFunc = null,
    max_subproblems: usize = 5,
    compose_solutions: bool = true,
};

/// Least-to-Most agent
pub const LeastToMostAgent = struct {
    allocator: Allocator,
    base_agent: Agent,
    config: LeastToMostConfig,
    agent_name: []const u8,

    pub fn init(
        allocator: Allocator,
        base_agent: Agent,
        config: LeastToMostConfig,
    ) !*LeastToMostAgent {
        const self = try allocator.create(LeastToMostAgent);
        self.* = LeastToMostAgent{
            .allocator = allocator,
            .base_agent = base_agent,
            .config = config,
            .agent_name = "least_to_most",
        };
        return self;
    }

    pub fn agent(self: *LeastToMostAgent) Agent {
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
        const self: *LeastToMostAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 5);
        caps[0] = "reasoning";
        caps[1] = "decomposition";
        caps[2] = "compositional_reasoning";
        caps[3] = "least_to_most";
        caps[4] = "sequential_solving";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *LeastToMostAgent = @ptrCast(@alignCast(ptr));

        var empty = CallOptions.init(self.allocator);
        defer empty.deinit();
        return self.run(message, &empty);
    }

    /// Implements the optional `processWith` capability (#801).
    ///
    /// Both LLM phases receive the options: decomposition and every subproblem
    /// solve. Threading them into only the first would leave most of the calls
    /// running at settings the caller never chose.
    fn processWithImpl(ptr: *anyopaque, message: Message, options: *const CallOptions) AgentError!Result {
        const self: *LeastToMostAgent = @ptrCast(@alignCast(ptr));
        return self.run(message, options);
    }

    /// Shared body for both entry points.
    fn run(self: *LeastToMostAgent, message: Message, options: *const CallOptions) AgentError!Result {
        // Get problem from message
        const problem = message.contentAsText() catch {
            return Result{ .err = AgentError.InvalidInput };
        };

        // Step 1: Decompose problem
        const subproblems = self.decompose(problem, options) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };
        defer {
            for (subproblems) |*sub| {
                var mutable_sub = sub.*;
                mutable_sub.deinit(self.allocator);
            }
            self.allocator.free(subproblems);
        }

        // Step 2: Solve subproblems sequentially
        var solutions = std.ArrayListUnmanaged([]const u8).empty;
        defer {
            for (solutions.items) |sol| {
                self.allocator.free(sol);
            }
            solutions.deinit(self.allocator);
        }

        for (subproblems) |subproblem| {
            const solution = self.solveSubproblem(subproblem, solutions.items, options) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            solutions.append(self.allocator, solution) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
        }

        // Step 3: Final solution is the last one (hardest problem)
        const final_solution = if (solutions.items.len > 0)
            self.allocator.dupe(u8, solutions.items[solutions.items.len - 1]) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            }
        else
            self.allocator.dupe(u8, "") catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };

        // Build result message
        var response = Message.withText(self.allocator, .assistant, final_solution) catch {
            self.allocator.free(final_solution);
            return Result{ .err = AgentError.ProcessingFailed };
        };
        self.allocator.free(final_solution);

        // Add metadata
        response.setMetadata("technique", .{ .string = "least_to_most" }) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };
        response.setMetadata("num_subproblems", .{ .integer = @as(i64, @intCast(subproblems.len)) }) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };
        response.setMetadata("compose_solutions", .{ .bool = self.config.compose_solutions }) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        // Add subproblems array
        var subproblems_array = std.ArrayListUnmanaged(std.json.Value).empty;
        for (subproblems) |sub| {
            const dupe_content = self.allocator.dupe(u8, sub.content) catch {
                // Clean up any already added items
                for (subproblems_array.items) |item| {
                    self.allocator.free(item.string);
                }
                subproblems_array.deinit(self.allocator);
                return Result{ .err = AgentError.ProcessingFailed };
            };
            subproblems_array.append(self.allocator, .{ .string = dupe_content }) catch {
                self.allocator.free(dupe_content);
                // Clean up any already added items
                for (subproblems_array.items) |item| {
                    self.allocator.free(item.string);
                }
                subproblems_array.deinit(self.allocator);
                return Result{ .err = AgentError.ProcessingFailed };
            };
        }
        response.setMetadata("subproblems", .{ .array = subproblems_array.toManaged(self.allocator) }) catch {
            // Clean up strings
            for (subproblems_array.items) |item| {
                self.allocator.free(item.string);
            }
            subproblems_array.deinit(self.allocator);
            return Result{ .err = AgentError.ProcessingFailed };
        };

        // Add solutions array
        var solutions_array = std.ArrayListUnmanaged(std.json.Value).empty;
        for (solutions.items) |sol| {
            const dupe_sol = self.allocator.dupe(u8, sol) catch {
                // Clean up any already added items
                for (solutions_array.items) |item| {
                    self.allocator.free(item.string);
                }
                solutions_array.deinit(self.allocator);
                return Result{ .err = AgentError.ProcessingFailed };
            };
            solutions_array.append(self.allocator, .{ .string = dupe_sol }) catch {
                self.allocator.free(dupe_sol);
                // Clean up any already added items
                for (solutions_array.items) |item| {
                    self.allocator.free(item.string);
                }
                solutions_array.deinit(self.allocator);
                return Result{ .err = AgentError.ProcessingFailed };
            };
        }
        response.setMetadata("subproblem_solutions", .{ .array = solutions_array.toManaged(self.allocator) }) catch {
            // Clean up strings
            for (solutions_array.items) |item| {
                self.allocator.free(item.string);
            }
            solutions_array.deinit(self.allocator);
            return Result{ .err = AgentError.ProcessingFailed };
        };

        return Result{ .ok = response };
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        _ = callbacks;
        return AgentError.NotImplemented;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
        const self: *LeastToMostAgent = @ptrCast(@alignCast(ptr));
        const caps = try self.agent().capabilities(allocator);
        defer allocator.free(caps);
        return @import("../../introspection.zig").createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *LeastToMostAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }

    /// Decompose problem into subproblems
    fn decompose(self: *LeastToMostAgent, problem: []const u8, options: *const CallOptions) ![]Subproblem {
        if (self.config.decomposer) |decomposer_func| {
            // Use custom decomposer
            const subproblem_texts = try decomposer_func(self.allocator, problem);
            defer {
                for (subproblem_texts) |text| {
                    self.allocator.free(text);
                }
                self.allocator.free(subproblem_texts);
            }

            var subproblems = std.ArrayListUnmanaged(Subproblem).empty;
            errdefer {
                for (subproblems.items) |*sub| {
                    var mutable_sub = sub.*;
                    mutable_sub.deinit(self.allocator);
                }
                subproblems.deinit(self.allocator);
            }

            const limit = @min(subproblem_texts.len, self.config.max_subproblems);
            for (subproblem_texts[0..limit], 0..) |text, i| {
                const content = try self.allocator.dupe(u8, text);
                const dependencies = try self.allocator.alloc(usize, 0);
                try subproblems.append(self.allocator, Subproblem{
                    .content = content,
                    .difficulty = i,
                    .dependencies = dependencies,
                });
            }

            return try subproblems.toOwnedSlice(self.allocator);
        }

        // Use LLM to decompose
        const decomposition_prompt = try std.fmt.allocPrint(
            self.allocator,
            "Break down this problem into simpler subproblems, ordered from easiest to hardest.\n" ++
                "List each subproblem on a separate line, numbered 1, 2, 3, etc.\n\n" ++
                "Problem: {s}\n\n" ++
                "Subproblems (from simplest to most complex):",
            .{problem},
        );
        defer self.allocator.free(decomposition_prompt);

        var prompt_msg = try Message.withText(self.allocator, .user, decomposition_prompt);
        defer prompt_msg.deinit();

        const result = self.base_agent.processWithOptions(prompt_msg, options) catch {
            return AgentError.ProcessingFailed;
        };

        var response_msg = result.unwrap() catch {
            return AgentError.ProcessingFailed;
        };
        defer response_msg.deinit();

        const response_text = response_msg.contentAsText() catch {
            return AgentError.InvalidInput;
        };

        return try self.parseSubproblems(response_text, problem);
    }

    /// Parse subproblems from LLM response
    fn parseSubproblems(self: *LeastToMostAgent, response_text: []const u8, original_problem: []const u8) ![]Subproblem {
        var subproblems = std.ArrayListUnmanaged(Subproblem).empty;
        errdefer {
            for (subproblems.items) |*sub| {
                var mutable_sub = sub.*;
                mutable_sub.deinit(self.allocator);
            }
            subproblems.deinit(self.allocator);
        }

        var lines = std.mem.splitSequence(u8, response_text, "\n");
        var difficulty: usize = 0;

        while (lines.next()) |line| {
            const trimmed = std.mem.trim(u8, line, &std.ascii.whitespace);
            if (trimmed.len == 0) continue;
            if (subproblems.items.len >= self.config.max_subproblems) break;

            // Check for numbered format: digit followed by . or )
            if (trimmed.len >= 3 and std.ascii.isDigit(trimmed[0])) {
                if (trimmed[1] == '.' or trimmed[1] == ')') {
                    // Skip whitespace after number
                    var start: usize = 2;
                    while (start < trimmed.len and std.ascii.isWhitespace(trimmed[start])) {
                        start += 1;
                    }
                    if (start < trimmed.len) {
                        const content = try self.allocator.dupe(u8, trimmed[start..]);
                        const dependencies = try self.allocator.alloc(usize, 0);
                        try subproblems.append(self.allocator, Subproblem{
                            .content = content,
                            .difficulty = difficulty,
                            .dependencies = dependencies,
                        });
                        difficulty += 1;
                    }
                }
            }
        }

        // If decomposition failed or no valid numbered steps found, treat as atomic problem
        if (subproblems.items.len == 0) {
            const content = try self.allocator.dupe(u8, original_problem);
            const dependencies = try self.allocator.alloc(usize, 0);
            try subproblems.append(self.allocator, Subproblem{
                .content = content,
                .difficulty = 0,
                .dependencies = dependencies,
            });
        }

        return try subproblems.toOwnedSlice(self.allocator);
    }

    /// Solve one subproblem, optionally using previous solutions as context
    fn solveSubproblem(
        self: *LeastToMostAgent,
        subproblem: Subproblem,
        previous_solutions: []const []const u8,
        options: *const CallOptions,
    ) ![]const u8 {
        var prompt_buf = std.ArrayListUnmanaged(u8).empty;
        defer prompt_buf.deinit(self.allocator);

        if (self.config.compose_solutions and previous_solutions.len > 0) {
            // Include previous solutions as context
            try prompt_buf.appendSlice(self.allocator, "Given these previous solutions to simpler subproblems:\n\n");
            for (previous_solutions, 0..) |sol, i| {
                try prompt_buf.print(self.allocator, "Previous solution {d}: {s}\n", .{ i + 1, sol });
            }
            try prompt_buf.print(self.allocator, "\nNow solve this subproblem:\n{s}\n\nSolution:", .{subproblem.content});
        } else {
            // Solve without context
            try prompt_buf.print(self.allocator, "Solve this subproblem:\n\n{s}\n\nSolution:", .{subproblem.content});
        }

        const prompt = try prompt_buf.toOwnedSlice(self.allocator);
        defer self.allocator.free(prompt);

        var prompt_msg = try Message.withText(self.allocator, .user, prompt);
        defer prompt_msg.deinit();

        const result = self.base_agent.processWithOptions(prompt_msg, options) catch {
            return AgentError.ProcessingFailed;
        };

        var response_msg = result.unwrap() catch {
            return AgentError.ProcessingFailed;
        };
        defer response_msg.deinit();

        const response_text = response_msg.contentAsText() catch {
            return AgentError.InvalidInput;
        };

        const trimmed = std.mem.trim(u8, response_text, &std.ascii.whitespace);
        return try self.allocator.dupe(u8, trimmed);
    }
};

// Tests
test "LeastToMostAgent - basic functionality" {
    const testing = std.testing;
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Create mock agent with responses
    const MockAgent = struct {
        allocator: Allocator,
        responses: []const []const u8,
        call_count: usize,

        pub fn init(alloc: Allocator, responses: []const []const u8) @This() {
            return .{ .allocator = alloc, .responses = responses, .call_count = 0 };
        }

        pub fn agent(self: *@This()) Agent {
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
            _ = ptr;
            return "mock_agent";
        }

        fn capabilitiesImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 2);
            caps[0] = "mock";
            caps[1] = "testing";
            return caps;
        }

        fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
            _ = message;
            const self: *@This() = @ptrCast(@alignCast(ptr));
            const idx = self.call_count % self.responses.len;
            self.call_count += 1;

            const response = Message.withText(self.allocator, .assistant, self.responses[idx]) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            return Result{ .ok = response };
        }

        fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
            _ = ptr;
            _ = message;
            _ = callbacks;
            return AgentError.NotImplemented;
        }

        fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
            _ = ptr;
            _ = alloc;
            return error.OutOfMemory;
        }

        fn deinitImpl(ptr: *anyopaque) void {
            _ = ptr;
        }
    };

    const responses = [_][]const u8{
        "1. Calculate 3*4\n2. Calculate 2*5\n3. Add the results",
        "12",
        "10",
        "22",
    };

    var mock = MockAgent.init(allocator, &responses);
    const mock_agent = mock.agent();

    const ltm = try LeastToMostAgent.init(allocator, mock_agent, .{});
    defer ltm.agent().deinit();

    var message = try Message.withText(allocator, .user, "Calculate 3*4 + 2*5");
    defer message.deinit();
    const result = try ltm.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    const content = try response.contentAsText();
    try testing.expectEqualStrings("22", content);

    // Check metadata
    const technique = response.metadata.object.get("technique").?;
    try testing.expectEqualStrings("least_to_most", technique.string);

    const num_subproblems = response.metadata.object.get("num_subproblems").?;
    try testing.expectEqual(@as(i64, 3), num_subproblems.integer);
}

test "LeastToMostAgent - name and capabilities" {
    const testing = std.testing;
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const MockAgent = struct {
        pub fn agent(self: *@This()) Agent {
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
            _ = ptr;
            return "mock";
        }

        fn capabilitiesImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 1);
            caps[0] = "mock";
            return caps;
        }

        fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
            _ = ptr;
            _ = message;
            return Result{ .err = AgentError.ProcessingFailed };
        }

        fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
            _ = ptr;
            _ = message;
            _ = callbacks;
            return AgentError.NotImplemented;
        }

        fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
            _ = ptr;
            _ = alloc;
            return error.OutOfMemory;
        }

        fn deinitImpl(ptr: *anyopaque) void {
            _ = ptr;
        }
    };

    var mock = MockAgent{};
    const mock_agent = mock.agent();

    const ltm = try LeastToMostAgent.init(allocator, mock_agent, .{});
    defer ltm.agent().deinit();

    try testing.expectEqualStrings("least_to_most", ltm.agent().name());

    const caps = try ltm.agent().capabilities(allocator);
    defer allocator.free(caps);

    try testing.expectEqual(@as(usize, 5), caps.len);
    try testing.expectEqualStrings("reasoning", caps[0]);
    try testing.expectEqualStrings("decomposition", caps[1]);
    try testing.expectEqualStrings("compositional_reasoning", caps[2]);
    try testing.expectEqualStrings("least_to_most", caps[3]);
    try testing.expectEqualStrings("sequential_solving", caps[4]);
}

test "LeastToMostAgent - decomposition verification" {
    const testing = std.testing;
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const MockAgent = struct {
        allocator: Allocator,
        responses: []const []const u8,
        call_count: usize,

        pub fn init(alloc: Allocator, responses: []const []const u8) @This() {
            return .{ .allocator = alloc, .responses = responses, .call_count = 0 };
        }

        pub fn agent(self: *@This()) Agent {
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
            _ = ptr;
            return "mock_agent";
        }

        fn capabilitiesImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 1);
            caps[0] = "mock";
            return caps;
        }

        fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
            _ = message;
            const self: *@This() = @ptrCast(@alignCast(ptr));
            const idx = self.call_count % self.responses.len;
            self.call_count += 1;

            const response = Message.withText(self.allocator, .assistant, self.responses[idx]) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            return Result{ .ok = response };
        }

        fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
            _ = ptr;
            _ = message;
            _ = callbacks;
            return AgentError.NotImplemented;
        }

        fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
            _ = ptr;
            _ = alloc;
            return error.OutOfMemory;
        }

        fn deinitImpl(ptr: *anyopaque) void {
            _ = ptr;
        }
    };

    const responses = [_][]const u8{
        "1. First subproblem\n2. Second subproblem\n3. Third subproblem",
        "Solution 1",
        "Solution 2",
        "Solution 3",
    };

    var mock = MockAgent.init(allocator, &responses);
    const mock_agent = mock.agent();

    const ltm = try LeastToMostAgent.init(allocator, mock_agent, .{});
    defer ltm.agent().deinit();

    var message = try Message.withText(allocator, .user, "Complex problem");
    defer message.deinit();
    const result = try ltm.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    // Verify subproblems in metadata
    const subproblems_value = response.metadata.object.get("subproblems").?;
    const subproblems = subproblems_value.array.items;

    try testing.expectEqual(@as(usize, 3), subproblems.len);
    try testing.expectEqualStrings("First subproblem", subproblems[0].string);
    try testing.expectEqualStrings("Second subproblem", subproblems[1].string);
    try testing.expectEqualStrings("Third subproblem", subproblems[2].string);
}

test "LeastToMostAgent - sequential solving" {
    const testing = std.testing;
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const MockAgent = struct {
        allocator: Allocator,
        responses: []const []const u8,
        call_count: usize,

        pub fn init(alloc: Allocator, responses: []const []const u8) @This() {
            return .{ .allocator = alloc, .responses = responses, .call_count = 0 };
        }

        pub fn agent(self: *@This()) Agent {
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
            _ = ptr;
            return "mock_agent";
        }

        fn capabilitiesImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 1);
            caps[0] = "mock";
            return caps;
        }

        fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
            _ = message;
            const self: *@This() = @ptrCast(@alignCast(ptr));
            const idx = self.call_count % self.responses.len;
            self.call_count += 1;

            const response = Message.withText(self.allocator, .assistant, self.responses[idx]) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            return Result{ .ok = response };
        }

        fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
            _ = ptr;
            _ = message;
            _ = callbacks;
            return AgentError.NotImplemented;
        }

        fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
            _ = ptr;
            _ = alloc;
            return error.OutOfMemory;
        }

        fn deinitImpl(ptr: *anyopaque) void {
            _ = ptr;
        }
    };

    const responses = [_][]const u8{
        "1. Step A\n2. Step B",
        "Answer A",
        "Answer B",
    };

    var mock = MockAgent.init(allocator, &responses);
    const mock_agent = mock.agent();

    const ltm = try LeastToMostAgent.init(allocator, mock_agent, .{});
    defer ltm.agent().deinit();

    var message = try Message.withText(allocator, .user, "Problem");
    defer message.deinit();
    const result = try ltm.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    // Verify solutions in metadata
    const solutions_value = response.metadata.object.get("subproblem_solutions").?;
    const solutions = solutions_value.array.items;

    try testing.expectEqual(@as(usize, 2), solutions.len);
    try testing.expectEqualStrings("Answer A", solutions[0].string);
    try testing.expectEqualStrings("Answer B", solutions[1].string);
}

test "LeastToMostAgent - final solution is last" {
    const testing = std.testing;
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const MockAgent = struct {
        allocator: Allocator,
        responses: []const []const u8,
        call_count: usize,

        pub fn init(alloc: Allocator, responses: []const []const u8) @This() {
            return .{ .allocator = alloc, .responses = responses, .call_count = 0 };
        }

        pub fn agent(self: *@This()) Agent {
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
            _ = ptr;
            return "mock_agent";
        }

        fn capabilitiesImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 1);
            caps[0] = "mock";
            return caps;
        }

        fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
            _ = message;
            const self: *@This() = @ptrCast(@alignCast(ptr));
            const idx = self.call_count % self.responses.len;
            self.call_count += 1;

            const response = Message.withText(self.allocator, .assistant, self.responses[idx]) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            return Result{ .ok = response };
        }

        fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
            _ = ptr;
            _ = message;
            _ = callbacks;
            return AgentError.NotImplemented;
        }

        fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
            _ = ptr;
            _ = alloc;
            return error.OutOfMemory;
        }

        fn deinitImpl(ptr: *anyopaque) void {
            _ = ptr;
        }
    };

    const responses = [_][]const u8{
        "1. Easy\n2. Medium\n3. Hard",
        "Easy solution",
        "Medium solution",
        "Hard solution - final",
    };

    var mock = MockAgent.init(allocator, &responses);
    const mock_agent = mock.agent();

    const ltm = try LeastToMostAgent.init(allocator, mock_agent, .{});
    defer ltm.agent().deinit();

    var message = try Message.withText(allocator, .user, "Problem");
    defer message.deinit();
    const result = try ltm.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    // Final solution should be the last one
    const content = try response.contentAsText();
    try testing.expectEqualStrings("Hard solution - final", content);
}

test "LeastToMostAgent - max subproblems limit" {
    const testing = std.testing;
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const MockAgent = struct {
        allocator: Allocator,
        responses: []const []const u8,
        call_count: usize,

        pub fn init(alloc: Allocator, responses: []const []const u8) @This() {
            return .{ .allocator = alloc, .responses = responses, .call_count = 0 };
        }

        pub fn agent(self: *@This()) Agent {
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
            _ = ptr;
            return "mock_agent";
        }

        fn capabilitiesImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 1);
            caps[0] = "mock";
            return caps;
        }

        fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
            _ = message;
            const self: *@This() = @ptrCast(@alignCast(ptr));
            const idx = self.call_count % self.responses.len;
            self.call_count += 1;

            const response = Message.withText(self.allocator, .assistant, self.responses[idx]) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            return Result{ .ok = response };
        }

        fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
            _ = ptr;
            _ = message;
            _ = callbacks;
            return AgentError.NotImplemented;
        }

        fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
            _ = ptr;
            _ = alloc;
            return error.OutOfMemory;
        }

        fn deinitImpl(ptr: *anyopaque) void {
            _ = ptr;
        }
    };

    const responses = [_][]const u8{
        "1. Sub 1\n2. Sub 2\n3. Sub 3\n4. Sub 4\n5. Sub 5\n6. Sub 6",
        "S1",
        "S2",
        "S3",
    };

    var mock = MockAgent.init(allocator, &responses);
    const mock_agent = mock.agent();

    const ltm = try LeastToMostAgent.init(allocator, mock_agent, .{ .max_subproblems = 3 });
    defer ltm.agent().deinit();

    var message = try Message.withText(allocator, .user, "Problem");
    defer message.deinit();
    const result = try ltm.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    // Should only have 3 subproblems due to limit
    const num_subproblems = response.metadata.object.get("num_subproblems").?;
    try testing.expectEqual(@as(i64, 3), num_subproblems.integer);

    const subproblems_value = response.metadata.object.get("subproblems").?;
    try testing.expectEqual(@as(usize, 3), subproblems_value.array.items.len);
}

test "LeastToMostAgent - custom decomposer" {
    const testing = std.testing;
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const MockAgent = struct {
        allocator: Allocator,
        responses: []const []const u8,
        call_count: usize,

        pub fn init(alloc: Allocator, responses: []const []const u8) @This() {
            return .{ .allocator = alloc, .responses = responses, .call_count = 0 };
        }

        pub fn agent(self: *@This()) Agent {
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
            _ = ptr;
            return "mock_agent";
        }

        fn capabilitiesImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 1);
            caps[0] = "mock";
            return caps;
        }

        fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
            _ = message;
            const self: *@This() = @ptrCast(@alignCast(ptr));
            const idx = self.call_count % self.responses.len;
            self.call_count += 1;

            const response = Message.withText(self.allocator, .assistant, self.responses[idx]) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            return Result{ .ok = response };
        }

        fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
            _ = ptr;
            _ = message;
            _ = callbacks;
            return AgentError.NotImplemented;
        }

        fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
            _ = ptr;
            _ = alloc;
            return error.OutOfMemory;
        }

        fn deinitImpl(ptr: *anyopaque) void {
            _ = ptr;
        }
    };

    const customDecomposer: DecomposerFunc = struct {
        fn decompose(alloc: Allocator, problem: []const u8) anyerror![][]const u8 {
            _ = problem;
            const parts = try alloc.alloc([]const u8, 2);
            parts[0] = try alloc.dupe(u8, "Custom A");
            parts[1] = try alloc.dupe(u8, "Custom B");
            return parts;
        }
    }.decompose;

    const responses = [_][]const u8{
        "Solution A",
        "Solution B",
    };

    var mock = MockAgent.init(allocator, &responses);
    const mock_agent = mock.agent();

    const ltm = try LeastToMostAgent.init(allocator, mock_agent, .{ .decomposer = customDecomposer });
    defer ltm.agent().deinit();

    var message = try Message.withText(allocator, .user, "Problem");
    defer message.deinit();
    const result = try ltm.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    // Should use custom decomposer
    const subproblems_value = response.metadata.object.get("subproblems").?;
    const subproblems = subproblems_value.array.items;

    try testing.expectEqual(@as(usize, 2), subproblems.len);
    try testing.expectEqualStrings("Custom A", subproblems[0].string);
    try testing.expectEqualStrings("Custom B", subproblems[1].string);
}

test "LeastToMostAgent - compose solutions enabled" {
    const testing = std.testing;
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const MockAgent = struct {
        allocator: Allocator,
        responses: []const []const u8,
        call_count: usize,

        pub fn init(alloc: Allocator, responses: []const []const u8) @This() {
            return .{ .allocator = alloc, .responses = responses, .call_count = 0 };
        }

        pub fn agent(self: *@This()) Agent {
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
            _ = ptr;
            return "mock_agent";
        }

        fn capabilitiesImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 1);
            caps[0] = "mock";
            return caps;
        }

        fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
            _ = message;
            const self: *@This() = @ptrCast(@alignCast(ptr));
            const idx = self.call_count % self.responses.len;
            self.call_count += 1;

            const response = Message.withText(self.allocator, .assistant, self.responses[idx]) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            return Result{ .ok = response };
        }

        fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
            _ = ptr;
            _ = message;
            _ = callbacks;
            return AgentError.NotImplemented;
        }

        fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
            _ = ptr;
            _ = alloc;
            return error.OutOfMemory;
        }

        fn deinitImpl(ptr: *anyopaque) void {
            _ = ptr;
        }
    };

    const responses = [_][]const u8{
        "1. Step 1\n2. Step 2",
        "Result 1",
        "Result 2",
    };

    var mock = MockAgent.init(allocator, &responses);
    const mock_agent = mock.agent();

    const ltm = try LeastToMostAgent.init(allocator, mock_agent, .{ .compose_solutions = true });
    defer ltm.agent().deinit();

    var message = try Message.withText(allocator, .user, "Problem");
    defer message.deinit();
    const result = try ltm.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    // Verify compose_solutions in metadata
    const compose = response.metadata.object.get("compose_solutions").?;
    try testing.expect(compose.bool);
}

test "LeastToMostAgent - compose solutions disabled" {
    const testing = std.testing;
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const MockAgent = struct {
        allocator: Allocator,
        responses: []const []const u8,
        call_count: usize,

        pub fn init(alloc: Allocator, responses: []const []const u8) @This() {
            return .{ .allocator = alloc, .responses = responses, .call_count = 0 };
        }

        pub fn agent(self: *@This()) Agent {
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
            _ = ptr;
            return "mock_agent";
        }

        fn capabilitiesImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 1);
            caps[0] = "mock";
            return caps;
        }

        fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
            _ = message;
            const self: *@This() = @ptrCast(@alignCast(ptr));
            const idx = self.call_count % self.responses.len;
            self.call_count += 1;

            const response = Message.withText(self.allocator, .assistant, self.responses[idx]) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            return Result{ .ok = response };
        }

        fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
            _ = ptr;
            _ = message;
            _ = callbacks;
            return AgentError.NotImplemented;
        }

        fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
            _ = ptr;
            _ = alloc;
            return error.OutOfMemory;
        }

        fn deinitImpl(ptr: *anyopaque) void {
            _ = ptr;
        }
    };

    const responses = [_][]const u8{
        "1. Step 1\n2. Step 2",
        "Result 1",
        "Result 2",
    };

    var mock = MockAgent.init(allocator, &responses);
    const mock_agent = mock.agent();

    const ltm = try LeastToMostAgent.init(allocator, mock_agent, .{ .compose_solutions = false });
    defer ltm.agent().deinit();

    var message = try Message.withText(allocator, .user, "Problem");
    defer message.deinit();
    const result = try ltm.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    // Verify compose_solutions in metadata
    const compose = response.metadata.object.get("compose_solutions").?;
    try testing.expect(!compose.bool);
}

test "LeastToMostAgent - parse numbered steps with periods" {
    const testing = std.testing;
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const MockAgent = struct {
        allocator: Allocator,
        responses: []const []const u8,
        call_count: usize,

        pub fn init(alloc: Allocator, responses: []const []const u8) @This() {
            return .{ .allocator = alloc, .responses = responses, .call_count = 0 };
        }

        pub fn agent(self: *@This()) Agent {
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
            _ = ptr;
            return "mock_agent";
        }

        fn capabilitiesImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 1);
            caps[0] = "mock";
            return caps;
        }

        fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
            _ = message;
            const self: *@This() = @ptrCast(@alignCast(ptr));
            const idx = self.call_count % self.responses.len;
            self.call_count += 1;

            const response = Message.withText(self.allocator, .assistant, self.responses[idx]) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            return Result{ .ok = response };
        }

        fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
            _ = ptr;
            _ = message;
            _ = callbacks;
            return AgentError.NotImplemented;
        }

        fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
            _ = ptr;
            _ = alloc;
            return error.OutOfMemory;
        }

        fn deinitImpl(ptr: *anyopaque) void {
            _ = ptr;
        }
    };

    const responses = [_][]const u8{
        "1. First task\n2. Second task\n3. Third task",
        "S1",
        "S2",
        "S3",
    };

    var mock = MockAgent.init(allocator, &responses);
    const mock_agent = mock.agent();

    const ltm = try LeastToMostAgent.init(allocator, mock_agent, .{});
    defer ltm.agent().deinit();

    var message = try Message.withText(allocator, .user, "Problem");
    defer message.deinit();
    const result = try ltm.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    const subproblems_value = response.metadata.object.get("subproblems").?;
    const subproblems = subproblems_value.array.items;

    try testing.expectEqual(@as(usize, 3), subproblems.len);
    try testing.expectEqualStrings("First task", subproblems[0].string);
    try testing.expectEqualStrings("Second task", subproblems[1].string);
    try testing.expectEqualStrings("Third task", subproblems[2].string);
}

test "LeastToMostAgent - parse numbered steps with parentheses" {
    const testing = std.testing;
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const MockAgent = struct {
        allocator: Allocator,
        responses: []const []const u8,
        call_count: usize,

        pub fn init(alloc: Allocator, responses: []const []const u8) @This() {
            return .{ .allocator = alloc, .responses = responses, .call_count = 0 };
        }

        pub fn agent(self: *@This()) Agent {
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
            _ = ptr;
            return "mock_agent";
        }

        fn capabilitiesImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 1);
            caps[0] = "mock";
            return caps;
        }

        fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
            _ = message;
            const self: *@This() = @ptrCast(@alignCast(ptr));
            const idx = self.call_count % self.responses.len;
            self.call_count += 1;

            const response = Message.withText(self.allocator, .assistant, self.responses[idx]) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            return Result{ .ok = response };
        }

        fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
            _ = ptr;
            _ = message;
            _ = callbacks;
            return AgentError.NotImplemented;
        }

        fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
            _ = ptr;
            _ = alloc;
            return error.OutOfMemory;
        }

        fn deinitImpl(ptr: *anyopaque) void {
            _ = ptr;
        }
    };

    const responses = [_][]const u8{
        "1) Alpha\n2) Beta\n3) Gamma",
        "S1",
        "S2",
        "S3",
    };

    var mock = MockAgent.init(allocator, &responses);
    const mock_agent = mock.agent();

    const ltm = try LeastToMostAgent.init(allocator, mock_agent, .{});
    defer ltm.agent().deinit();

    var message = try Message.withText(allocator, .user, "Problem");
    defer message.deinit();
    const result = try ltm.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    const subproblems_value = response.metadata.object.get("subproblems").?;
    const subproblems = subproblems_value.array.items;

    try testing.expectEqual(@as(usize, 3), subproblems.len);
    try testing.expectEqualStrings("Alpha", subproblems[0].string);
    try testing.expectEqualStrings("Beta", subproblems[1].string);
    try testing.expectEqualStrings("Gamma", subproblems[2].string);
}

test "LeastToMostAgent - skip empty lines" {
    const testing = std.testing;
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const MockAgent = struct {
        allocator: Allocator,
        responses: []const []const u8,
        call_count: usize,

        pub fn init(alloc: Allocator, responses: []const []const u8) @This() {
            return .{ .allocator = alloc, .responses = responses, .call_count = 0 };
        }

        pub fn agent(self: *@This()) Agent {
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
            _ = ptr;
            return "mock_agent";
        }

        fn capabilitiesImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 1);
            caps[0] = "mock";
            return caps;
        }

        fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
            _ = message;
            const self: *@This() = @ptrCast(@alignCast(ptr));
            const idx = self.call_count % self.responses.len;
            self.call_count += 1;

            const response = Message.withText(self.allocator, .assistant, self.responses[idx]) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            return Result{ .ok = response };
        }

        fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
            _ = ptr;
            _ = message;
            _ = callbacks;
            return AgentError.NotImplemented;
        }

        fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
            _ = ptr;
            _ = alloc;
            return error.OutOfMemory;
        }

        fn deinitImpl(ptr: *anyopaque) void {
            _ = ptr;
        }
    };

    const responses = [_][]const u8{
        "1. Valid\n\n2. Also valid\n\n\n3. Still valid",
        "S1",
        "S2",
        "S3",
    };

    var mock = MockAgent.init(allocator, &responses);
    const mock_agent = mock.agent();

    const ltm = try LeastToMostAgent.init(allocator, mock_agent, .{});
    defer ltm.agent().deinit();

    var message = try Message.withText(allocator, .user, "Problem");
    defer message.deinit();
    const result = try ltm.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    const subproblems_value = response.metadata.object.get("subproblems").?;
    const subproblems = subproblems_value.array.items;

    try testing.expectEqual(@as(usize, 3), subproblems.len);
}

test "LeastToMostAgent - atomic problem fallback" {
    const testing = std.testing;
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const MockAgent = struct {
        allocator: Allocator,
        responses: []const []const u8,
        call_count: usize,

        pub fn init(alloc: Allocator, responses: []const []const u8) @This() {
            return .{ .allocator = alloc, .responses = responses, .call_count = 0 };
        }

        pub fn agent(self: *@This()) Agent {
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
            _ = ptr;
            return "mock_agent";
        }

        fn capabilitiesImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 1);
            caps[0] = "mock";
            return caps;
        }

        fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
            _ = message;
            const self: *@This() = @ptrCast(@alignCast(ptr));
            const idx = self.call_count % self.responses.len;
            self.call_count += 1;

            const response = Message.withText(self.allocator, .assistant, self.responses[idx]) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            return Result{ .ok = response };
        }

        fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
            _ = ptr;
            _ = message;
            _ = callbacks;
            return AgentError.NotImplemented;
        }

        fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
            _ = ptr;
            _ = alloc;
            return error.OutOfMemory;
        }

        fn deinitImpl(ptr: *anyopaque) void {
            _ = ptr;
        }
    };

    const responses = [_][]const u8{
        "This is not a numbered list",
        "Direct solution",
    };

    var mock = MockAgent.init(allocator, &responses);
    const mock_agent = mock.agent();

    const ltm = try LeastToMostAgent.init(allocator, mock_agent, .{});
    defer ltm.agent().deinit();

    var message = try Message.withText(allocator, .user, "Simple problem");
    defer message.deinit();
    const result = try ltm.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    // Should treat as atomic problem (1 subproblem)
    const num_subproblems = response.metadata.object.get("num_subproblems").?;
    try testing.expectEqual(@as(i64, 1), num_subproblems.integer);
}

test "LeastToMostAgent - whitespace trimming" {
    const testing = std.testing;
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const MockAgent = struct {
        allocator: Allocator,
        responses: []const []const u8,
        call_count: usize,

        pub fn init(alloc: Allocator, responses: []const []const u8) @This() {
            return .{ .allocator = alloc, .responses = responses, .call_count = 0 };
        }

        pub fn agent(self: *@This()) Agent {
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
            _ = ptr;
            return "mock_agent";
        }

        fn capabilitiesImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 1);
            caps[0] = "mock";
            return caps;
        }

        fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
            _ = message;
            const self: *@This() = @ptrCast(@alignCast(ptr));
            const idx = self.call_count % self.responses.len;
            self.call_count += 1;

            const response = Message.withText(self.allocator, .assistant, self.responses[idx]) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            return Result{ .ok = response };
        }

        fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
            _ = ptr;
            _ = message;
            _ = callbacks;
            return AgentError.NotImplemented;
        }

        fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
            _ = ptr;
            _ = alloc;
            return error.OutOfMemory;
        }

        fn deinitImpl(ptr: *anyopaque) void {
            _ = ptr;
        }
    };

    const responses = [_][]const u8{
        "  1. Task with spaces  \n  2. Another task  ",
        "  Solution  ",
        "  Another solution  ",
    };

    var mock = MockAgent.init(allocator, &responses);
    const mock_agent = mock.agent();

    const ltm = try LeastToMostAgent.init(allocator, mock_agent, .{});
    defer ltm.agent().deinit();

    var message = try Message.withText(allocator, .user, "Problem");
    defer message.deinit();
    const result = try ltm.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    const subproblems_value = response.metadata.object.get("subproblems").?;
    const subproblems = subproblems_value.array.items;

    // Whitespace should be trimmed
    try testing.expectEqualStrings("Task with spaces", subproblems[0].string);
    try testing.expectEqualStrings("Another task", subproblems[1].string);
}

test "LeastToMostAgent - metadata includes all fields" {
    const testing = std.testing;
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const MockAgent = struct {
        allocator: Allocator,
        responses: []const []const u8,
        call_count: usize,

        pub fn init(alloc: Allocator, responses: []const []const u8) @This() {
            return .{ .allocator = alloc, .responses = responses, .call_count = 0 };
        }

        pub fn agent(self: *@This()) Agent {
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
            _ = ptr;
            return "mock_agent";
        }

        fn capabilitiesImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error![]const []const u8 {
            _ = ptr;
            const caps = try alloc.alloc([]const u8, 1);
            caps[0] = "mock";
            return caps;
        }

        fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
            _ = message;
            const self: *@This() = @ptrCast(@alignCast(ptr));
            const idx = self.call_count % self.responses.len;
            self.call_count += 1;

            const response = Message.withText(self.allocator, .assistant, self.responses[idx]) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            return Result{ .ok = response };
        }

        fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
            _ = ptr;
            _ = message;
            _ = callbacks;
            return AgentError.NotImplemented;
        }

        fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
            _ = ptr;
            _ = alloc;
            return error.OutOfMemory;
        }

        fn deinitImpl(ptr: *anyopaque) void {
            _ = ptr;
        }
    };

    const responses = [_][]const u8{
        "1. Step A",
        "Solution A",
    };

    var mock = MockAgent.init(allocator, &responses);
    const mock_agent = mock.agent();

    const ltm = try LeastToMostAgent.init(allocator, mock_agent, .{});
    defer ltm.agent().deinit();

    var message = try Message.withText(allocator, .user, "Problem");
    defer message.deinit();
    const result = try ltm.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    // Check all expected metadata fields
    try testing.expect(response.metadata.object.contains("technique"));
    try testing.expect(response.metadata.object.contains("num_subproblems"));
    try testing.expect(response.metadata.object.contains("subproblems"));
    try testing.expect(response.metadata.object.contains("subproblem_solutions"));
    try testing.expect(response.metadata.object.contains("compose_solutions"));
}

// ============================================================================
// Per-call options forwarding (#801)
// ============================================================================

const OptionsAwareMockAgent = @import("../../test_utils.zig").OptionsAwareMockAgent;

test "LeastToMost forwards call options to both LLM phases" {
    const testing = std.testing;
    const allocator = testing.allocator;

    var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{
        "1. First subproblem\n2. Second subproblem",
        "Solution to the first",
        "Solution to the second",
    });
    defer mock.deinit();

    const ltm = try LeastToMostAgent.init(allocator, mock.agent(), .{});
    const ltm_agent = ltm.agent();
    defer ltm_agent.deinit();

    var msg = try Message.withText(allocator, .user, "A hard problem");
    defer msg.deinit();

    var options = CallOptions.init(allocator);
    defer options.deinit();
    try options.withTemperature(0.55);

    var response = try (try ltm_agent.processWith(msg, &options)).unwrap();
    defer response.deinit();

    // Decomposition plus one call per subproblem. Threading the options into
    // decompose() alone would leave every solve running at settings the caller
    // never chose, and the call count is what proves more than one path ran.
    try testing.expect(mock.getCallCount() >= 3);
    try testing.expect(mock.allTemperaturesEqual(0.55));
}

test "LeastToMost sends no options when called through process" {
    const testing = std.testing;
    const allocator = testing.allocator;

    var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{
        "1. Only subproblem",
        "Solution",
    });
    defer mock.deinit();

    const ltm = try LeastToMostAgent.init(allocator, mock.agent(), .{});
    const ltm_agent = ltm.agent();
    defer ltm_agent.deinit();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var response = try (try ltm_agent.process(msg)).unwrap();
    defer response.deinit();

    try testing.expect(mock.allTemperaturesEqual(null));
}

test "LeastToMost advertises the options capability" {
    const testing = std.testing;
    const allocator = testing.allocator;

    var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{"x"});
    defer mock.deinit();

    const ltm = try LeastToMostAgent.init(allocator, mock.agent(), .{});
    const ltm_agent = ltm.agent();
    defer ltm_agent.deinit();

    try testing.expect(ltm_agent.supportsOptions());
}

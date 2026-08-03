/// Chain-of-Thought Reasoning Technique
///
/// Chain-of-Thought applies structured prompting to encourage step-by-step reasoning,
/// optionally parsing and tracking individual reasoning steps.
///
/// Reference: "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"
/// Wei et al., 2022 - https://arxiv.org/abs/2201.11903
const std = @import("std");
const Agent = @import("../../agent.zig").Agent;
const AgentError = @import("../../agent.zig").AgentError;
const Result = @import("../../agent.zig").Result;
const Message = @import("../../message.zig").Message;
const Allocator = std.mem.Allocator;

/// Bullet markers recognised at the start of a reasoning step.
///
/// Stored as strings, not bytes: "•" is U+2022, three bytes in UTF-8, so
/// `line[0] == '•'` compares a u8 against 8226 and is always false. That
/// silently dropped every bullet list written with "•".
const bullet_markers = [_][]const u8{ "-", "*", "•" };

/// Byte length of the bullet marker starting `text`, or null if there is none.
fn bulletWidth(text: []const u8) ?usize {
    for (bullet_markers) |marker| {
        if (std.mem.startsWith(u8, text, marker)) return marker.len;
    }
    return null;
}

/// Configuration for Chain-of-Thought
pub const ChainOfThoughtConfig = struct {
    prompt_template: []const u8 = "Let's think step by step:\n{query}",
    parse_steps: bool = true,
    step_delimiter: []const u8 = "\n",
    max_steps: ?usize = null,
};

/// Chain-of-Thought agent
pub const ChainOfThoughtAgent = struct {
    allocator: Allocator,
    base_agent: Agent,
    config: ChainOfThoughtConfig,
    agent_name: []const u8,

    pub fn init(
        allocator: Allocator,
        base_agent: Agent,
        config: ChainOfThoughtConfig,
    ) !*ChainOfThoughtAgent {
        const self = try allocator.create(ChainOfThoughtAgent);
        self.* = ChainOfThoughtAgent{
            .allocator = allocator,
            .base_agent = base_agent,
            .config = config,
            .agent_name = "chain_of_thought",
        };
        return self;
    }

    pub fn agent(self: *ChainOfThoughtAgent) Agent {
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
        const self: *ChainOfThoughtAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 4);
        caps[0] = "reasoning";
        caps[1] = "step_by_step";
        caps[2] = "chain_of_thought";
        caps[3] = "explainable_ai";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *ChainOfThoughtAgent = @ptrCast(@alignCast(ptr));

        // Allocation failures are mapped to ProcessingFailed rather than
        // propagated: the vtable signature is AgentError!Result, which does not
        // include Allocator.Error.
        return self.processInner(message) catch |err| switch (err) {
            error.OutOfMemory => Result{ .err = AgentError.ProcessingFailed },
            else => |e| Result{ .err = e },
        };
    }

    /// The real body, allowed to fail with Allocator.Error.
    ///
    /// Split out so `try` can be used on allocating calls; processImpl narrows
    /// the error set back down to what the Agent vtable declares.
    fn processInner(self: *ChainOfThoughtAgent, message: Message) (AgentError || Allocator.Error)!Result {
        // Validate template contains {query}
        if (std.mem.indexOf(u8, self.config.prompt_template, "{query}") == null) {
            return Result{ .err = AgentError.InvalidInput };
        }

        // Get query from message
        const query = message.contentAsText() catch {
            return Result{ .err = AgentError.InvalidInput };
        };

        // Apply CoT prompting - replace {query} in template
        const cot_prompt = try self.applyTemplate(query);
        defer self.allocator.free(cot_prompt);

        // Create message with CoT prompt
        var prompt_msg = try Message.withText(self.allocator, .user, cot_prompt);
        defer prompt_msg.deinit();

        // Get response from agent
        const result = self.base_agent.process(prompt_msg) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        var response_msg = result.unwrap() catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };
        defer response_msg.deinit();

        const response_text = response_msg.contentAsText() catch {
            return Result{ .err = AgentError.InvalidInput };
        };

        // Build result message
        var response = try Message.withText(self.allocator, .assistant, response_text);

        // Parse steps if requested
        if (self.config.parse_steps) {
            const steps = try self.extractSteps(response_text);
            defer {
                for (steps) |step| {
                    self.allocator.free(step);
                }
                self.allocator.free(steps);
            }

            // Add metadata
            try response.setMetadata("num_steps", .{ .integer = @as(i64, @intCast(steps.len)) });

            // For reasoning_steps, we'll just store the count since Zig metadata is simpler
            // In a real implementation, you'd store the array in a custom way
        }

        try response.setMetadata("technique", .{ .string = "chain_of_thought" });

        return Result{ .ok = response };
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        _ = callbacks;
        return AgentError.NotImplemented;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
        const self: *ChainOfThoughtAgent = @ptrCast(@alignCast(ptr));
        const caps = try self.agent().capabilities(allocator);
        defer allocator.free(caps);
        return @import("../../introspection.zig").createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *ChainOfThoughtAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }

    /// Apply template by replacing {query} placeholder
    fn applyTemplate(self: *ChainOfThoughtAgent, query: []const u8) ![]u8 {
        const template = self.config.prompt_template;
        const placeholder = "{query}";

        if (std.mem.indexOf(u8, template, placeholder)) |start_idx| {
            // Calculate result size
            const result_size = template.len - placeholder.len + query.len;
            var result = try self.allocator.alloc(u8, result_size);

            // Copy before placeholder
            @memcpy(result[0..start_idx], template[0..start_idx]);

            // Copy query
            @memcpy(result[start_idx .. start_idx + query.len], query);

            // Copy after placeholder
            const after_placeholder = start_idx + placeholder.len;
            @memcpy(result[start_idx + query.len ..], template[after_placeholder..]);

            return result;
        }

        // No placeholder found, just duplicate template
        return try self.allocator.dupe(u8, template);
    }

    /// Extract reasoning steps from response text
    fn extractSteps(self: *ChainOfThoughtAgent, text: []const u8) ![][]const u8 {
        // Try numbered steps first (1. 2. 3. or 1) 2) 3))
        if (try self.extractNumberedSteps(text)) |steps| {
            return steps;
        }

        // Try bullet points (-, *, •)
        if (try self.extractBulletSteps(text)) |steps| {
            return steps;
        }

        // Fallback: delimiter-based splitting
        return try self.extractDelimiterSteps(text);
    }

    /// Extract numbered steps (1. Step or 1) Step)
    fn extractNumberedSteps(self: *ChainOfThoughtAgent, text: []const u8) !?[][]const u8 {
        var steps = std.ArrayListUnmanaged([]const u8).empty;
        errdefer {
            for (steps.items) |step| {
                self.allocator.free(step);
            }
            steps.deinit(self.allocator);
        }

        var lines = std.mem.splitScalar(u8, text, '\n');
        while (lines.next()) |line| {
            const trimmed = std.mem.trim(u8, line, &std.ascii.whitespace);
            if (trimmed.len == 0) continue;

            // Check for numbered format: digit followed by . or )
            if (trimmed.len >= 3 and std.ascii.isDigit(trimmed[0])) {
                if (trimmed[1] == '.' or trimmed[1] == ')') {
                    // Skip whitespace after number
                    var start: usize = 2;
                    while (start < trimmed.len and std.ascii.isWhitespace(trimmed[start])) {
                        start += 1;
                    }
                    if (start < trimmed.len) {
                        const step = try self.allocator.dupe(u8, trimmed[start..]);
                        try steps.append(self.allocator, step);
                    }
                }
            }
        }

        if (steps.items.len >= 2) {
            return try steps.toOwnedSlice(self.allocator);
        }

        // Not enough numbered steps found
        for (steps.items) |step| {
            self.allocator.free(step);
        }
        steps.deinit(self.allocator);
        return null;
    }

    /// Extract bullet point steps (-, *, •)
    fn extractBulletSteps(self: *ChainOfThoughtAgent, text: []const u8) !?[][]const u8 {
        var steps = std.ArrayListUnmanaged([]const u8).empty;
        errdefer {
            for (steps.items) |step| {
                self.allocator.free(step);
            }
            steps.deinit(self.allocator);
        }

        var lines = std.mem.splitScalar(u8, text, '\n');
        while (lines.next()) |line| {
            const trimmed = std.mem.trim(u8, line, &std.ascii.whitespace);
            if (trimmed.len == 0) continue;

            // Check for bullet format
            if (bulletWidth(trimmed)) |width| {
                // Skip whitespace after bullet
                var start: usize = width;
                while (start < trimmed.len and std.ascii.isWhitespace(trimmed[start])) {
                    start += 1;
                }
                if (start < trimmed.len) {
                    const step = try self.allocator.dupe(u8, trimmed[start..]);
                    try steps.append(self.allocator, step);
                }
            }
        }

        if (steps.items.len >= 2) {
            return try steps.toOwnedSlice(self.allocator);
        }

        // Not enough bullet steps found
        for (steps.items) |step| {
            self.allocator.free(step);
        }
        steps.deinit(self.allocator);
        return null;
    }

    /// Extract steps using delimiter
    fn extractDelimiterSteps(self: *ChainOfThoughtAgent, text: []const u8) ![][]const u8 {
        var steps = std.ArrayListUnmanaged([]const u8).empty;
        errdefer {
            for (steps.items) |step| {
                self.allocator.free(step);
            }
            steps.deinit(self.allocator);
        }

        var iter = std.mem.splitSequence(u8, text, self.config.step_delimiter);
        while (iter.next()) |line| {
            const trimmed = std.mem.trim(u8, line, &std.ascii.whitespace);
            if (trimmed.len > 0) {
                const step = try self.allocator.dupe(u8, trimmed);
                try steps.append(self.allocator, step);
            }
        }

        // Apply max_steps if configured
        if (self.config.max_steps) |max| {
            if (steps.items.len > max) {
                // Free excess steps
                for (steps.items[max..]) |step| {
                    self.allocator.free(step);
                }
                try steps.resize(self.allocator, max);
            }
        }

        return try steps.toOwnedSlice(self.allocator);
    }
};

// ============================================================================
// Tests
// ============================================================================
//
// This file previously had no test blocks at all, which in Zig means it was
// never type-checked: `_ = @import(...)` only forces analysis of a file's test
// declarations, and a file with none is analysed not at all — which is how
// agent() shipped without compiling (#811). The end-to-end tests below must go
// through the Agent vtable, not merely reference `agent()`, or the rot recurs.

const MockAgent = @import("../../test_utils.zig").MockAgent;
const Role = @import("../../message.zig").Role;
const StreamCallbacks = @import("../../agent.zig").StreamCallbacks;

test "ChainOfThought name and capabilities" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"response"});
    defer mock.deinit();

    var cot = try ChainOfThoughtAgent.init(allocator, mock.agent(), .{});
    const cot_agent = cot.agent();
    defer cot_agent.deinit();

    try testing.expectEqualStrings("chain_of_thought", cot_agent.name());

    const caps = try cot_agent.capabilities(allocator);
    defer allocator.free(caps);
    try testing.expectEqual(@as(usize, 4), caps.len);
    try testing.expectEqualStrings("reasoning", caps[0]);
    try testing.expectEqualStrings("step_by_step", caps[1]);
    try testing.expectEqualStrings("chain_of_thought", caps[2]);
    try testing.expectEqualStrings("explainable_ai", caps[3]);
}

test "ChainOfThought default config" {
    const testing = std.testing;

    const config = ChainOfThoughtConfig{};
    try testing.expectEqualStrings("Let's think step by step:\n{query}", config.prompt_template);
    try testing.expectEqual(true, config.parse_steps);
    try testing.expectEqualStrings("\n", config.step_delimiter);
    try testing.expectEqual(@as(?usize, null), config.max_steps);
}

test "ChainOfThought end-to-end through the vtable" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. Read the problem\n2. Solve it\n3. Check the answer",
    });
    defer mock.deinit();

    var cot = try ChainOfThoughtAgent.init(allocator, mock.agent(), .{});
    const cot_agent = cot.agent();
    defer cot_agent.deinit();

    var msg = try Message.withText(allocator, .user, "What is 2+2?");
    defer msg.deinit();

    var response = try (try cot_agent.process(msg)).unwrap();
    defer response.deinit();

    try testing.expectEqual(Role.assistant, response.role);
    try testing.expectEqualStrings("chain_of_thought", response.getMetadata("technique").?.string);
    try testing.expectEqual(@as(i64, 3), response.getMetadata("num_steps").?.integer);
    try testing.expectEqual(@as(usize, 1), mock.call_count);
}

test "ChainOfThought applies the prompt template to the wrapped agent" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"answer"});
    defer mock.deinit();

    var cot = try ChainOfThoughtAgent.init(allocator, mock.agent(), .{
        .prompt_template = "PREFIX {query} SUFFIX",
    });
    defer cot.agent().deinit();

    const prompt = try cot.applyTemplate("QUERY");
    defer allocator.free(prompt);
    try testing.expectEqualStrings("PREFIX QUERY SUFFIX", prompt);
}

test "ChainOfThought rejects a template without the query placeholder" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"answer"});
    defer mock.deinit();

    var cot = try ChainOfThoughtAgent.init(allocator, mock.agent(), .{
        .prompt_template = "no placeholder here",
    });
    const cot_agent = cot.agent();
    defer cot_agent.deinit();

    var msg = try Message.withText(allocator, .user, "hello");
    defer msg.deinit();

    const result = try cot_agent.process(msg);
    try testing.expectEqual(AgentError.InvalidInput, result.unwrapErr());
    // The wrapped agent must not be called at all when the config is invalid.
    try testing.expectEqual(@as(usize, 0), mock.call_count);
}

test "ChainOfThought parse_steps disabled omits num_steps" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"1. one\n2. two"});
    defer mock.deinit();

    var cot = try ChainOfThoughtAgent.init(allocator, mock.agent(), .{ .parse_steps = false });
    const cot_agent = cot.agent();
    defer cot_agent.deinit();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var response = try (try cot_agent.process(msg)).unwrap();
    defer response.deinit();

    // Absent, not reported as zero.
    try testing.expect(response.getMetadata("num_steps") == null);
    try testing.expectEqualStrings("chain_of_thought", response.getMetadata("technique").?.string);
}

test "ChainOfThought extractSteps prefers numbered over bullets" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var cot = try ChainOfThoughtAgent.init(allocator, mock.agent(), .{});
    defer cot.agent().deinit();

    // Both formats present: the numbered extractor runs first and wins.
    const steps = try cot.extractSteps("1. alpha\n- bullet\n2) beta\n* star");
    defer {
        for (steps) |step| allocator.free(step);
        allocator.free(steps);
    }

    try testing.expectEqual(@as(usize, 2), steps.len);
    try testing.expectEqualStrings("alpha", steps[0]);
    try testing.expectEqualStrings("beta", steps[1]);
}

test "ChainOfThought extractSteps falls back to bullets" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var cot = try ChainOfThoughtAgent.init(allocator, mock.agent(), .{});
    defer cot.agent().deinit();

    const steps = try cot.extractSteps("- first\n* second\n• third");
    defer {
        for (steps) |step| allocator.free(step);
        allocator.free(steps);
    }

    try testing.expectEqual(@as(usize, 3), steps.len);
    try testing.expectEqualStrings("first", steps[0]);
    try testing.expectEqualStrings("second", steps[1]);
    try testing.expectEqualStrings("third", steps[2]);
}

test "ChainOfThought extractSteps falls back to the delimiter" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var cot = try ChainOfThoughtAgent.init(allocator, mock.agent(), .{ .step_delimiter = ";" });
    defer cot.agent().deinit();

    // Neither numbered nor bulleted, and a single numbered line is not enough
    // to trip the numbered extractor's two-step minimum.
    const steps = try cot.extractSteps("alpha; beta; gamma");
    defer {
        for (steps) |step| allocator.free(step);
        allocator.free(steps);
    }

    try testing.expectEqual(@as(usize, 3), steps.len);
    try testing.expectEqualStrings("alpha", steps[0]);
    try testing.expectEqualStrings("gamma", steps[2]);
}

test "ChainOfThought max_steps truncates delimiter steps" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var cot = try ChainOfThoughtAgent.init(allocator, mock.agent(), .{ .max_steps = 2 });
    defer cot.agent().deinit();

    const steps = try cot.extractSteps("a\nb\nc\nd");
    defer {
        for (steps) |step| allocator.free(step);
        allocator.free(steps);
    }

    try testing.expectEqual(@as(usize, 2), steps.len);
    try testing.expectEqualStrings("a", steps[0]);
    try testing.expectEqualStrings("b", steps[1]);
}

test "ChainOfThought process_stream is not implemented" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var cot = try ChainOfThoughtAgent.init(allocator, mock.agent(), .{});
    const cot_agent = cot.agent();
    defer cot_agent.deinit();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var sink = TestSink{};
    try testing.expectError(
        AgentError.NotImplemented,
        cot_agent.processStream(msg, sink.callbacks()),
    );
    try testing.expectEqual(@as(usize, 0), sink.calls);
}

test "ChainOfThought introspection reports name and capabilities" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var cot = try ChainOfThoughtAgent.init(allocator, mock.agent(), .{});
    const cot_agent = cot.agent();
    defer cot_agent.deinit();

    var info = try cot_agent.introspect(allocator);
    defer info.deinit();

    try testing.expectEqualStrings("chain_of_thought", info.agent_name);
    try testing.expectEqual(@as(usize, 4), info.capabilities.len);
}

/// Callback sink that records that it was never invoked.
const TestSink = struct {
    calls: usize = 0,

    fn onMessage(ptr: *anyopaque, message: Message) void {
        _ = message;
        const self: *TestSink = @ptrCast(@alignCast(ptr));
        self.calls += 1;
    }

    fn onError(ptr: *anyopaque, err: AgentError) void {
        const self: *TestSink = @ptrCast(@alignCast(ptr));
        self.calls += 1;
        std.debug.assert(err != AgentError.Cancelled);
    }

    fn onComplete(ptr: *anyopaque) void {
        const self: *TestSink = @ptrCast(@alignCast(ptr));
        self.calls += 1;
    }

    fn callbacks(self: *TestSink) StreamCallbacks {
        return StreamCallbacks{
            .ptr = self,
            .on_message_fn = onMessage,
            .on_error_fn = onError,
            .on_complete_fn = onComplete,
        };
    }
};

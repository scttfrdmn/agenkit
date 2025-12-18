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
        const prompt_msg = try Message.withText(self.allocator, .user, cot_prompt);

        // Get response from agent
        const result = self.base_agent.process(prompt_msg) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        const response_msg = result.unwrap() catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

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
        var steps = std.ArrayList([]const u8).init(self.allocator);
        errdefer {
            for (steps.items) |step| {
                self.allocator.free(step);
            }
            steps.deinit();
        }

        var lines = std.mem.split(u8, text, "\n");
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
                        try steps.append(step);
                    }
                }
            }
        }

        if (steps.items.len >= 2) {
            return try steps.toOwnedSlice();
        }

        // Not enough numbered steps found
        for (steps.items) |step| {
            self.allocator.free(step);
        }
        steps.deinit();
        return null;
    }

    /// Extract bullet point steps (-, *, •)
    fn extractBulletSteps(self: *ChainOfThoughtAgent, text: []const u8) !?[][]const u8 {
        var steps = std.ArrayList([]const u8).init(self.allocator);
        errdefer {
            for (steps.items) |step| {
                self.allocator.free(step);
            }
            steps.deinit();
        }

        var lines = std.mem.split(u8, text, "\n");
        while (lines.next()) |line| {
            const trimmed = std.mem.trim(u8, line, &std.ascii.whitespace);
            if (trimmed.len == 0) continue;

            // Check for bullet format
            if (trimmed[0] == '-' or trimmed[0] == '*' or trimmed[0] == '•') {
                // Skip whitespace after bullet
                var start: usize = 1;
                while (start < trimmed.len and std.ascii.isWhitespace(trimmed[start])) {
                    start += 1;
                }
                if (start < trimmed.len) {
                    const step = try self.allocator.dupe(u8, trimmed[start..]);
                    try steps.append(step);
                }
            }
        }

        if (steps.items.len >= 2) {
            return try steps.toOwnedSlice();
        }

        // Not enough bullet steps found
        for (steps.items) |step| {
            self.allocator.free(step);
        }
        steps.deinit();
        return null;
    }

    /// Extract steps using delimiter
    fn extractDelimiterSteps(self: *ChainOfThoughtAgent, text: []const u8) ![][]const u8 {
        var steps = std.ArrayList([]const u8).init(self.allocator);
        errdefer {
            for (steps.items) |step| {
                self.allocator.free(step);
            }
            steps.deinit();
        }

        var iter = std.mem.split(u8, text, self.config.step_delimiter);
        while (iter.next()) |line| {
            const trimmed = std.mem.trim(u8, line, &std.ascii.whitespace);
            if (trimmed.len > 0) {
                const step = try self.allocator.dupe(u8, trimmed);
                try steps.append(step);
            }
        }

        // Apply max_steps if configured
        if (self.config.max_steps) |max| {
            if (steps.items.len > max) {
                // Free excess steps
                for (steps.items[max..]) |step| {
                    self.allocator.free(step);
                }
                try steps.resize(max);
            }
        }

        return try steps.toOwnedSlice();
    }
};

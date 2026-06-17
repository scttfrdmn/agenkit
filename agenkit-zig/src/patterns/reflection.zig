/// Reflection Pattern - Self-Critique and Iterative Refinement
///
/// The Reflection pattern enables agents to review and improve their own outputs
/// through an iterative cycle of generation, critique, and refinement.
///
/// Key Concepts:
/// - Generator: Agent that produces initial output
/// - Critic: Agent that evaluates output quality and provides feedback
/// - Iteration: Repeated refinement based on critique
/// - Quality Threshold: Stop when output quality is sufficient
/// - Improvement Threshold: Stop when incremental improvements become minimal
///
/// Use Cases:
/// - Code generation with self-review
/// - Content creation with quality improvement
/// - Multi-draft writing and editing
/// - Error detection and correction
/// - Iterative problem solving
///
/// References:
/// - Reflexion: Language Agents with Verbal Reinforcement Learning
/// - Self-Refine: Iterative Refinement with Self-Feedback
const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const StreamCallbacks = @import("../agent.zig").StreamCallbacks;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;

/// Reason why reflection loop stopped
pub const StopReason = enum {
    quality_threshold_met,
    minimal_improvement,
    max_iterations,
    perfect_score,

    pub fn toString(self: StopReason) []const u8 {
        return switch (self) {
            .quality_threshold_met => "quality_threshold_met",
            .minimal_improvement => "minimal_improvement",
            .max_iterations => "max_iterations",
            .perfect_score => "perfect_score",
        };
    }
};

/// Format expected from critic agent
pub const CritiqueFormat = enum {
    structured, // JSON: {"score": 0.8, "feedback": "..."}
    free_form, // Free text with score extracted
};

/// Single iteration in the reflection loop
pub const ReflectionStep = struct {
    iteration: u32,
    output: []const u8,
    critique: []const u8,
    quality_score: f32,
    improvement: f32,
    allocator: Allocator,

    pub fn init(
        allocator: Allocator,
        iteration: u32,
        output: []const u8,
        critique: []const u8,
        quality_score: f32,
        improvement: f32,
    ) !ReflectionStep {
        return ReflectionStep{
            .iteration = iteration,
            .output = try allocator.dupe(u8, output),
            .critique = try allocator.dupe(u8, critique),
            .quality_score = quality_score,
            .improvement = improvement,
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *ReflectionStep) void {
        self.allocator.free(self.output);
        self.allocator.free(self.critique);
    }
};

/// Reflection Agent - Iteratively refines output through self-critique
pub const ReflectionAgent = struct {
    allocator: Allocator,
    generator: Agent,
    critic: Agent,
    max_iterations: u32,
    quality_threshold: f32,
    improvement_threshold: f32,
    critique_format: CritiqueFormat,
    verbose: bool,
    history: std.ArrayList(ReflectionStep),

    /// Initialize a reflection agent
    ///
    /// Args:
    ///     allocator: Memory allocator
    ///     generator: Agent that produces/refines output
    ///     critic: Agent that evaluates output (returns score + feedback)
    ///     max_iterations: Maximum refinement iterations (default: 5)
    ///     quality_threshold: Stop when score exceeds this (default: 0.9)
    ///     improvement_threshold: Min improvement to continue (default: 0.05)
    ///     critique_format: Expected format from critic (default: structured)
    ///     verbose: Include full reflection history in output (default: false)
    pub fn init(
        allocator: Allocator,
        generator: Agent,
        critic: Agent,
        max_iterations: u32,
        quality_threshold: f32,
        improvement_threshold: f32,
        critique_format: CritiqueFormat,
        verbose: bool,
    ) !*ReflectionAgent {
        const self = try allocator.create(ReflectionAgent);
        self.* = ReflectionAgent{
            .allocator = allocator,
            .generator = generator,
            .critic = critic,
            .max_iterations = max_iterations,
            .quality_threshold = quality_threshold,
            .improvement_threshold = improvement_threshold,
            .critique_format = critique_format,
            .verbose = verbose,
            .history = .empty,
        };
        return self;
    }

    pub fn agent(self: *ReflectionAgent) Agent {
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
        return "ReflectionAgent";
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *ReflectionAgent = @ptrCast(@alignCast(ptr));

        // Combine generator and critic capabilities
        var caps_set = std.StringHashMap(void).init(allocator);
        defer caps_set.deinit();

        const gen_caps = try self.generator.capabilities(allocator);
        defer allocator.free(gen_caps);
        for (gen_caps) |cap| {
            try caps_set.put(cap, {});
        }

        const critic_caps = try self.critic.capabilities(allocator);
        defer allocator.free(critic_caps);
        for (critic_caps) |cap| {
            try caps_set.put(cap, {});
        }

        // Add reflection capabilities
        try caps_set.put("reflection", {});
        try caps_set.put("self-critique", {});

        const caps = try allocator.alloc([]const u8, caps_set.count());
        var iter = caps_set.keyIterator();
        var i: usize = 0;
        while (iter.next()) |key| : (i += 1) {
            caps[i] = key.*;
        }

        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *ReflectionAgent = @ptrCast(@alignCast(ptr));

        // Clear history from previous runs
        for (self.history.items) |*step| {
            step.deinit();
        }
        self.history.clearRetainingCapacity();

        // Initial generation
        const gen_result = self.generator.process(message) catch |err| {
            return err;
        };
        var output = gen_result.unwrap() catch |err| {
            return err;
        };

        var previous_score: f32 = 0.0;
        var iteration: u32 = 1;

        while (iteration <= self.max_iterations) : (iteration += 1) {
            // Build critique prompt
            const original_text = message.contentAsText() catch {
                output.deinit();
                return AgentError.InvalidInput;
            };
            const output_text = output.contentAsText() catch {
                output.deinit();
                return AgentError.InvalidInput;
            };

            var critique_msg = self.buildCritiquePrompt(original_text, output_text) catch {
                output.deinit();
                return AgentError.ProcessingFailed;
            };
            defer critique_msg.deinit();

            // Get critique
            const critique_result = self.critic.process(critique_msg) catch |err| {
                output.deinit();
                return err;
            };
            var critique_response = critique_result.unwrap() catch |err| {
                output.deinit();
                return err;
            };
            defer critique_response.deinit();

            const critique_text = critique_response.contentAsText() catch {
                output.deinit();
                return AgentError.InvalidInput;
            };

            // Parse critique
            const parsed = self.parseCritique(critique_text) catch {
                output.deinit();
                return AgentError.ProcessingFailed;
            };
            const score = parsed.score;
            const feedback = parsed.feedback;
            defer self.allocator.free(feedback);

            const improvement = score - previous_score;

            // Record step
            const step = ReflectionStep.init(
                self.allocator,
                iteration,
                output_text,
                feedback,
                score,
                improvement,
            ) catch {
                output.deinit();
                return AgentError.ProcessingFailed;
            };
            self.history.append(self.allocator, step) catch {
                output.deinit();
                return AgentError.ProcessingFailed;
            };

            // Check stopping conditions
            const stop_check = self.checkStopConditions(score, improvement, iteration);
            const should_stop = stop_check.should_stop;
            const stop_reason = stop_check.reason;

            if (should_stop) {
                return self.formatResult(output, stop_reason);
            }

            // Refine based on critique
            var refine_msg = self.buildRefinementPrompt(
                original_text,
                output_text,
                feedback,
                iteration,
            ) catch {
                output.deinit();
                return AgentError.ProcessingFailed;
            };
            defer refine_msg.deinit();

            const refine_result = self.generator.process(refine_msg) catch |err| {
                output.deinit();
                return err;
            };

            // Clean up old output, get new one
            output.deinit();
            output = refine_result.unwrap() catch |err| {
                return err;
            };

            previous_score = score;
        }

        // Max iterations reached
        return self.formatResult(output, StopReason.max_iterations);
    }

    fn buildCritiquePrompt(self: *ReflectionAgent, original_query: []const u8, current_output: []const u8) !Message {
        const prompt = if (self.critique_format == .structured)
            try std.fmt.allocPrint(
                self.allocator,
                \\Please evaluate the following output and provide structured feedback.
                \\
                \\Original Request:
                \\{s}
                \\
                \\Current Output:
                \\{s}
                \\
                \\Provide your evaluation in this JSON format:
                \\{{
                \\  "score": <float between 0.0 and 1.0>,
                \\  "feedback": "<specific feedback on what could be improved>"
                \\}}
            ,
                .{ original_query, current_output },
            )
        else
            try std.fmt.allocPrint(
                self.allocator,
                \\Please evaluate the following output on a scale of 0.0 to 1.0.
                \\
                \\Original Request:
                \\{s}
                \\
                \\Current Output:
                \\{s}
                \\
                \\Provide:
                \\1. A score (0.0-1.0) indicating quality
                \\2. Specific feedback on what could be improved
            ,
                .{ original_query, current_output },
            );
        defer self.allocator.free(prompt);

        return Message.withText(self.allocator, .user, prompt);
    }

    fn buildRefinementPrompt(
        self: *ReflectionAgent,
        original_query: []const u8,
        current_output: []const u8,
        critique: []const u8,
        iteration: u32,
    ) !Message {
        const prompt = try std.fmt.allocPrint(
            self.allocator,
            \\Please refine your previous output based on the following critique.
            \\
            \\Original Request:
            \\{s}
            \\
            \\Your Previous Output (Iteration {d}):
            \\{s}
            \\
            \\Critique:
            \\{s}
            \\
            \\Please provide an improved version that addresses the critique.
        ,
            .{ original_query, iteration, current_output, critique },
        );
        defer self.allocator.free(prompt);

        return Message.withText(self.allocator, .user, prompt);
    }

    const ParsedCritique = struct {
        score: f32,
        feedback: []const u8,
    };

    fn parseCritique(self: *ReflectionAgent, content: []const u8) !ParsedCritique {
        if (self.critique_format == .structured) {
            return self.parseStructuredCritique(content) catch {
                // Fallback to free-form
                return self.parseFreeFormCritique(content);
            };
        } else {
            return self.parseFreeFormCritique(content);
        }
    }

    fn parseStructuredCritique(self: *ReflectionAgent, content: []const u8) !ParsedCritique {
        // Simple JSON parsing (look for "score" and "feedback" fields)
        // This is a simplified parser - production would use std.json.parseFromSlice

        var score: f32 = 0.5;
        var feedback: []const u8 = content;

        // Look for "score": <number>
        if (std.mem.indexOf(u8, content, "\"score\"")) |score_idx| {
            const after_score = content[score_idx..];
            if (std.mem.indexOf(u8, after_score, ":")) |colon_idx| {
                const after_colon = after_score[colon_idx + 1 ..];
                // Skip whitespace
                var num_start: usize = 0;
                while (num_start < after_colon.len and (after_colon[num_start] == ' ' or after_colon[num_start] == '\t')) {
                    num_start += 1;
                }
                // Extract number
                var num_end = num_start;
                while (num_end < after_colon.len and (std.ascii.isDigit(after_colon[num_end]) or after_colon[num_end] == '.')) {
                    num_end += 1;
                }
                if (num_end > num_start) {
                    const num_str = after_colon[num_start..num_end];
                    score = std.fmt.parseFloat(f32, num_str) catch 0.5;
                    // Clamp to valid range
                    score = @max(0.0, @min(1.0, score));
                }
            }
        }

        // Look for "feedback": "text"
        if (std.mem.indexOf(u8, content, "\"feedback\"")) |feedback_idx| {
            const after_feedback = content[feedback_idx..];
            if (std.mem.indexOf(u8, after_feedback, ":")) |colon_idx| {
                const after_colon = after_feedback[colon_idx + 1 ..];
                // Find opening quote
                if (std.mem.indexOf(u8, after_colon, "\"")) |quote1_idx| {
                    const after_quote1 = after_colon[quote1_idx + 1 ..];
                    // Find closing quote
                    if (std.mem.indexOf(u8, after_quote1, "\"")) |quote2_idx| {
                        feedback = after_quote1[0..quote2_idx];
                    }
                }
            }
        }

        return ParsedCritique{
            .score = score,
            .feedback = try self.allocator.dupe(u8, feedback),
        };
    }

    fn parseFreeFormCritique(self: *ReflectionAgent, content: []const u8) !ParsedCritique {
        var score: f32 = 0.5;

        // Look for patterns like "Score: 0.8", "Rating: 8", "8/10"
        const lower = try std.ascii.allocLowerString(self.allocator, content);
        defer self.allocator.free(lower);

        // Try "score: X"
        if (std.mem.indexOf(u8, lower, "score:") orelse std.mem.indexOf(u8, lower, "score ")) |idx| {
            const after = content[idx + 6 ..];
            score = self.extractScore(after) catch 0.5;
        }
        // Try "rating: X"
        else if (std.mem.indexOf(u8, lower, "rating:") orelse std.mem.indexOf(u8, lower, "rating ")) |idx| {
            const after = content[idx + 7 ..];
            score = self.extractScore(after) catch 0.5;
        }

        return ParsedCritique{
            .score = score,
            .feedback = try self.allocator.dupe(u8, content),
        };
    }

    fn extractScore(self: *ReflectionAgent, text: []const u8) !f32 {
        _ = self;
        // Skip whitespace
        var start: usize = 0;
        while (start < text.len and (text[start] == ' ' or text[start] == '\t')) {
            start += 1;
        }

        // Extract number
        var end = start;
        while (end < text.len and (std.ascii.isDigit(text[end]) or text[end] == '.')) {
            end += 1;
        }

        if (end <= start) return 0.5;

        const num_str = text[start..end];
        var value = try std.fmt.parseFloat(f32, num_str);

        // Normalize to 0.0-1.0
        if (value > 1.0) {
            value = value / 10.0; // Assume 0-10 scale
        }

        return @max(0.0, @min(1.0, value));
    }

    const StopCheck = struct {
        reason: StopReason,
        should_stop: bool,
    };

    fn checkStopConditions(self: *ReflectionAgent, score: f32, improvement: f32, iteration: u32) StopCheck {
        // Perfect score
        if (score >= 1.0) {
            return StopCheck{ .reason = .perfect_score, .should_stop = true };
        }

        // Quality threshold met
        if (score >= self.quality_threshold) {
            return StopCheck{ .reason = .quality_threshold_met, .should_stop = true };
        }

        // Minimal improvement (skip on first iteration)
        if (iteration > 1 and improvement < self.improvement_threshold) {
            return StopCheck{ .reason = .minimal_improvement, .should_stop = true };
        }

        // Continue iterating
        return StopCheck{ .reason = .max_iterations, .should_stop = false };
    }

    fn formatResult(self: *ReflectionAgent, output: Message, stop_reason: StopReason) AgentError!Result {
        const output_text = output.contentAsText() catch {
            return AgentError.InvalidInput;
        };
        var result = Message.withText(self.allocator, output.role, output_text) catch {
            return AgentError.ProcessingFailed;
        };

        // Add metadata
        const iterations_value = std.json.Value{ .integer = @intCast(self.history.items.len) };
        result.setMetadata("reflection_iterations", iterations_value) catch {
            return AgentError.ProcessingFailed;
        };

        if (self.history.items.len > 0) {
            const last = self.history.items[self.history.items.len - 1];
            const final_score = std.json.Value{ .float = last.quality_score };
            result.setMetadata("final_quality_score", final_score) catch {
                return AgentError.ProcessingFailed;
            };

            const initial_score = std.json.Value{ .float = self.history.items[0].quality_score };
            result.setMetadata("initial_quality_score", initial_score) catch {
                return AgentError.ProcessingFailed;
            };

            const total_improvement = std.json.Value{ .float = last.quality_score - self.history.items[0].quality_score };
            result.setMetadata("total_improvement", total_improvement) catch {
                return AgentError.ProcessingFailed;
            };
        }

        const reason_value = std.json.Value{ .string = stop_reason.toString() };
        result.setMetadata("stop_reason", reason_value) catch {
            return AgentError.ProcessingFailed;
        };

        // Note: history not included in metadata for now (would require JSON serialization)

        var output_mut = output;
        output_mut.deinit();
        return Result{ .ok = result };
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
        const self: *ReflectionAgent = @ptrCast(@alignCast(ptr));
        for (self.history.items) |*step| {
            step.deinit();
        }
        self.history.deinit(self.allocator);
        self.allocator.destroy(self);
    }

    pub fn deinit(self: *ReflectionAgent) void {
        for (self.history.items) |*step| {
            step.deinit();
        }
        self.history.deinit(self.allocator);
        self.allocator.destroy(self);
    }
};

// ============================================================================
// Tests
// ============================================================================

fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
    _ = ptr;
    _ = message;
    callbacks.onError(AgentError.NotImplemented);
}

test "ReflectionAgent basic functionality" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    // Use echo agents for testing
    var generator = try EchoAgent.init(allocator);
    defer generator.agent().deinit();
    var critic = try EchoAgent.init(allocator);
    defer critic.agent().deinit();

    var reflection = try ReflectionAgent.init(
        allocator,
        generator.agent(),
        critic.agent(),
        2, // max_iterations
        0.9, // quality_threshold
        0.05, // improvement_threshold
        .structured,
        false,
    );
    defer reflection.deinit();

    var msg = try Message.withText(allocator, .user, "test");
    defer msg.deinit();

    const result = try reflection.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    // Should complete (echo agents always pass through)
    const text = try response.contentAsText();
    try std.testing.expect(text.len > 0);
}

test "ReflectionAgent metadata" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    var generator = try EchoAgent.init(allocator);
    defer generator.agent().deinit();
    var critic = try EchoAgent.init(allocator);
    defer critic.agent().deinit();

    var reflection = try ReflectionAgent.init(
        allocator,
        generator.agent(),
        critic.agent(),
        3,
        0.9,
        0.05,
        .free_form,
        false,
    );
    defer reflection.deinit();

    var msg = try Message.withText(allocator, .user, "test");
    defer msg.deinit();

    const result = try reflection.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    // Check metadata
    const iterations = response.getMetadata("reflection_iterations");
    try std.testing.expect(iterations != null);

    const stop_reason = response.getMetadata("stop_reason");
    try std.testing.expect(stop_reason != null);
}

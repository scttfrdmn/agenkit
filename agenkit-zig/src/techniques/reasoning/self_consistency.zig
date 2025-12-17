/// Self-Consistency Reasoning Technique
///
/// Self-Consistency improves reliability by generating multiple independent reasoning
/// paths and using voting to select the most consistent answer.
///
/// Reference: "Self-Consistency Improves Chain of Thought Reasoning in Language Models"
/// Wang et al., 2022 - https://arxiv.org/abs/2203.11171

const std = @import("std");
const Agent = @import("../../agent.zig").Agent;
const AgentError = @import("../../agent.zig").AgentError;
const Result = @import("../../agent.zig").Result;
const Message = @import("../../message.zig").Message;
const Allocator = std.mem.Allocator;

/// Voting strategy for answer aggregation
pub const VotingStrategy = enum {
    majority,
    weighted,
    first,
};

/// Answer extractor function type
pub const AnswerExtractor = *const fn (allocator: Allocator, text: []const u8) Allocator.Error![]const u8;

/// Default answer extractor that looks for common answer patterns
pub fn defaultAnswerExtractor(allocator: Allocator, text: []const u8) ![]const u8 {
    // Try explicit answer markers
    const patterns = [_][]const u8{
        "therefore",
        "thus",
        "so",
        "the answer is",
        "answer:",
        "conclusion:",
        "result:",
    };

    // Simple pattern matching (case-insensitive)
    var lower_text = try allocator.alloc(u8, text.len);
    defer allocator.free(lower_text);
    for (text, 0..) |c, i| {
        lower_text[i] = std.ascii.toLower(c);
    }

    for (patterns) |pattern| {
        if (std.mem.indexOf(u8, lower_text, pattern)) |start_idx| {
            const after_pattern = start_idx + pattern.len;
            if (after_pattern < text.len) {
                // Find end of line or sentence
                var end_idx = after_pattern;
                while (end_idx < text.len and text[end_idx] != '.' and text[end_idx] != '\n') {
                    end_idx += 1;
                }

                // Extract and trim
                const answer = std.mem.trim(u8, text[after_pattern..end_idx], &std.ascii.whitespace);
                return try allocator.dupe(u8, answer);
            }
        }
    }

    // Fallback: use last non-empty line
    var it = std.mem.splitBackwardsScalar(u8, text, '\n');
    while (it.next()) |line| {
        const trimmed = std.mem.trim(u8, line, &std.ascii.whitespace);
        if (trimmed.len > 0) {
            return try allocator.dupe(u8, trimmed);
        }
    }

    // Final fallback
    const trimmed = std.mem.trim(u8, text, &std.ascii.whitespace);
    return try allocator.dupe(u8, trimmed);
}

/// Self-Consistency agent
pub const SelfConsistencyAgent = struct {
    allocator: Allocator,
    base_agent: Agent,
    num_samples: usize,
    voting_strategy: VotingStrategy,
    temperature: ?f64,
    answer_extractor: AnswerExtractor,
    agent_name: []const u8,

    pub fn init(
        allocator: Allocator,
        base_agent: Agent,
        num_samples: usize,
        voting_strategy: VotingStrategy,
    ) !*SelfConsistencyAgent {
        const self = try allocator.create(SelfConsistencyAgent);
        self.* = SelfConsistencyAgent{
            .allocator = allocator,
            .base_agent = base_agent,
            .num_samples = num_samples,
            .voting_strategy = voting_strategy,
            .temperature = null,
            .answer_extractor = defaultAnswerExtractor,
            .agent_name = "self_consistency",
        };
        return self;
    }

    pub fn agent(self: *SelfConsistencyAgent) Agent {
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
        const self: *SelfConsistencyAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 5);
        caps[0] = "reasoning";
        caps[1] = "self_consistency";
        caps[2] = "majority_voting";
        caps[3] = "reliability";
        caps[4] = "consensus";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *SelfConsistencyAgent = @ptrCast(@alignCast(ptr));

        // Generate multiple samples
        var samples = std.ArrayList([]const u8).init(self.allocator);
        defer {
            for (samples.items) |sample| {
                self.allocator.free(sample);
            }
            samples.deinit();
        }

        var extracted_answers = std.ArrayList([]const u8).init(self.allocator);
        defer {
            for (extracted_answers.items) |answer| {
                self.allocator.free(answer);
            }
            extracted_answers.deinit();
        }

        // Generate samples
        var i: usize = 0;
        while (i < self.num_samples) : (i += 1) {
            const result = self.base_agent.process(message) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };

            const response_msg = result.unwrap() catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };

            const full_response = response_msg.contentAsText() catch {
                return Result{ .err = AgentError.InvalidInput };
            };

            const extracted = self.answer_extractor(self.allocator, full_response) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };

            try samples.append(try self.allocator.dupe(u8, full_response));
            try extracted_answers.append(extracted);
        }

        // Vote for consensus
        const consensus = switch (self.voting_strategy) {
            .majority => try self.voteMajority(extracted_answers.items),
            .weighted => try self.voteWeighted(extracted_answers.items, samples.items),
            .first => try self.voteFirst(extracted_answers.items),
        };
        defer self.allocator.free(consensus.answer);

        // Build response
        var response = try Message.withText(self.allocator, .assistant, consensus.answer);

        // Add metadata
        try response.setMetadata("technique", .{ .string = "self_consistency" });
        try response.setMetadata("num_samples", .{ .integer = @as(i64, @intCast(self.num_samples)) });

        const strategy_str = switch (self.voting_strategy) {
            .majority => "majority",
            .weighted => "weighted",
            .first => "first",
        };
        try response.setMetadata("voting_strategy", .{ .string = strategy_str });
        try response.setMetadata("consistency_score", .{ .float = consensus.score });

        return Result{ .ok = response };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *SelfConsistencyAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }

    const VoteResult = struct {
        answer: []const u8,
        score: f64,
    };

    fn voteMajority(self: *SelfConsistencyAgent, answers: []const []const u8) !VoteResult {
        if (answers.len == 0) {
            return VoteResult{ .answer = try self.allocator.dupe(u8, ""), .score = 0.0 };
        }

        // Count occurrences
        var counts = std.StringHashMap(usize).init(self.allocator);
        defer counts.deinit();

        var original_case = std.StringHashMap([]const u8).init(self.allocator);
        defer original_case.deinit();

        for (answers) |answer| {
            // Normalize (lowercase, trim)
            var normalized = std.ArrayList(u8).init(self.allocator);
            defer normalized.deinit();

            for (answer) |c| {
                if (!std.ascii.isWhitespace(c)) {
                    try normalized.append(std.ascii.toLower(c));
                }
            }

            const normalized_str = try normalized.toOwnedSlice();
            defer self.allocator.free(normalized_str);

            const entry = try counts.getOrPut(normalized_str);
            if (!entry.found_existing) {
                entry.value_ptr.* = 0;
                try original_case.put(try self.allocator.dupe(u8, normalized_str), answer);
            }
            entry.value_ptr.* += 1;
        }

        // Find most common
        var max_count: usize = 0;
        var winning_answer: []const u8 = "";

        var it = counts.iterator();
        while (it.next()) |entry| {
            if (entry.value_ptr.* > max_count) {
                max_count = entry.value_ptr.*;
                winning_answer = original_case.get(entry.key_ptr.*) orelse "";
            }
        }

        const score = @as(f64, @floatFromInt(max_count)) / @as(f64, @floatFromInt(answers.len));
        return VoteResult{
            .answer = try self.allocator.dupe(u8, winning_answer),
            .score = score,
        };
    }

    fn voteWeighted(self: *SelfConsistencyAgent, answers: []const []const u8, responses: []const []const u8) !VoteResult {
        if (answers.len == 0) {
            return VoteResult{ .answer = try self.allocator.dupe(u8, ""), .score = 0.0 };
        }

        // Group by answer, weight by response length
        var weights = std.StringHashMap(usize).init(self.allocator);
        defer weights.deinit();

        var original_case = std.StringHashMap([]const u8).init(self.allocator);
        defer original_case.deinit();

        var total_weight: usize = 0;

        for (answers, 0..) |answer, i| {
            const normalized = try self.allocator.dupe(u8, answer);
            defer self.allocator.free(normalized);

            const entry = try weights.getOrPut(normalized);
            if (!entry.found_existing) {
                entry.value_ptr.* = 0;
                try original_case.put(try self.allocator.dupe(u8, normalized), answer);
            }
            const weight = responses[i].len;
            entry.value_ptr.* += weight;
            total_weight += weight;
        }

        // Find highest weight
        var max_weight: usize = 0;
        var winning_answer: []const u8 = "";

        var it = weights.iterator();
        while (it.next()) |entry| {
            if (entry.value_ptr.* > max_weight) {
                max_weight = entry.value_ptr.*;
                winning_answer = original_case.get(entry.key_ptr.*) orelse "";
            }
        }

        const score = if (total_weight > 0)
            @as(f64, @floatFromInt(max_weight)) / @as(f64, @floatFromInt(total_weight))
        else
            0.0;

        return VoteResult{
            .answer = try self.allocator.dupe(u8, winning_answer),
            .score = score,
        };
    }

    fn voteFirst(self: *SelfConsistencyAgent, answers: []const []const u8) !VoteResult {
        if (answers.len == 0) {
            return VoteResult{ .answer = try self.allocator.dupe(u8, ""), .score = 0.0 };
        }
        return VoteResult{
            .answer = try self.allocator.dupe(u8, answers[0]),
            .score = 1.0,
        };
    }
};

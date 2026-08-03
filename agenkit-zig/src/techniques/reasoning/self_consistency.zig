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

/// An answer marker and how it must be terminated to count as a match.
const AnswerMarker = struct {
    text: []const u8,
    /// Whether the marker must be followed by an optional comma and at least
    /// one space. True for prose markers, false for the ones ending in ':'.
    needs_separator: bool,
};

/// Whether `lower[idx..]` begins a marker match rather than continuing a word.
///
/// Without this check "so" matched inside "Some reasoning" and returned
/// "me reasoning" as the answer — a plausible-looking string that was never an
/// answer at all. The reference core's regex requires `,?\s+` after the marker
/// (agenkit/techniques/reasoning/self_consistency.py:164), which is what this
/// reproduces.
fn markerMatchesAt(lower: []const u8, idx: usize, marker: AnswerMarker) ?usize {
    if (!std.mem.startsWith(u8, lower[idx..], marker.text)) return null;

    // Must start a word, not land mid-word ("also" must not match "so").
    if (idx > 0 and (std.ascii.isAlphanumeric(lower[idx - 1]) or lower[idx - 1] == '_')) {
        return null;
    }

    var after = idx + marker.text.len;
    if (!marker.needs_separator) {
        while (after < lower.len and std.ascii.isWhitespace(lower[after])) after += 1;
        return after;
    }

    if (after < lower.len and lower[after] == ',') after += 1;

    // At least one space must separate the marker from the answer.
    if (after >= lower.len or !std.ascii.isWhitespace(lower[after])) return null;
    while (after < lower.len and std.ascii.isWhitespace(lower[after])) after += 1;

    // "therefore, the answer is 42" — the nested marker is skipped so the
    // answer is "42", not "the answer is 42", matching the reference core.
    const nested = "the answer is";
    if (std.mem.startsWith(u8, lower[after..], nested)) {
        var nested_end = after + nested.len;
        if (nested_end < lower.len and std.ascii.isWhitespace(lower[nested_end])) {
            while (nested_end < lower.len and std.ascii.isWhitespace(lower[nested_end])) nested_end += 1;
            return nested_end;
        }
    }

    return after;
}

/// Default answer extractor that looks for common answer patterns
pub fn defaultAnswerExtractor(allocator: Allocator, text: []const u8) ![]const u8 {
    // Try explicit answer markers, in the reference core's precedence order.
    const markers = [_]AnswerMarker{
        .{ .text = "therefore", .needs_separator = true },
        .{ .text = "thus", .needs_separator = true },
        .{ .text = "so", .needs_separator = true },
        .{ .text = "the answer is", .needs_separator = true },
        .{ .text = "answer:", .needs_separator = false },
        .{ .text = "conclusion:", .needs_separator = false },
        .{ .text = "result:", .needs_separator = false },
    };

    // Simple pattern matching (case-insensitive)
    var lower_text = try allocator.alloc(u8, text.len);
    defer allocator.free(lower_text);
    for (text, 0..) |c, i| {
        lower_text[i] = std.ascii.toLower(c);
    }

    for (markers) |marker| {
        var idx: usize = 0;
        while (idx < lower_text.len) : (idx += 1) {
            const after_pattern = markerMatchesAt(lower_text, idx, marker) orelse continue;
            if (after_pattern >= text.len) break;

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
                .process_stream = processStreamImpl,
                .introspect = introspectImpl,
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
    fn processInner(self: *SelfConsistencyAgent, message: Message) (AgentError || Allocator.Error)!Result {
        var samples = std.ArrayListUnmanaged([]const u8).empty;
        defer {
            for (samples.items) |sample| {
                self.allocator.free(sample);
            }
            samples.deinit(self.allocator);
        }

        var extracted_answers = std.ArrayListUnmanaged([]const u8).empty;
        defer {
            for (extracted_answers.items) |answer| {
                self.allocator.free(answer);
            }
            extracted_answers.deinit(self.allocator);
        }

        // Generate samples
        var i: usize = 0;
        while (i < self.num_samples) : (i += 1) {
            const result = self.base_agent.process(message) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };

            var response_msg = result.unwrap() catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
            defer response_msg.deinit();

            const full_response = response_msg.contentAsText() catch {
                return Result{ .err = AgentError.InvalidInput };
            };

            const extracted = self.answer_extractor(self.allocator, full_response) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };

            // Duped before append: full_response borrows from response_msg,
            // which is freed at the end of this iteration.
            const owned_response = try self.allocator.dupe(u8, full_response);
            errdefer self.allocator.free(owned_response);
            try samples.append(self.allocator, owned_response);
            try extracted_answers.append(self.allocator, extracted);
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

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        _ = callbacks;
        return AgentError.NotImplemented;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
        const self: *SelfConsistencyAgent = @ptrCast(@alignCast(ptr));
        const caps = try self.agent().capabilities(allocator);
        defer allocator.free(caps);
        return @import("../../introspection.zig").createDefaultIntrospectionResult(allocator, self.agent_name, caps);
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
        // The maps own their keys, so both are freed here. Previously the
        // normalized key was freed at the end of each loop iteration while the
        // map kept pointing at it, and original_case's duped keys leaked.
        var counts = std.StringHashMap(usize).init(self.allocator);
        defer {
            var key_it = counts.keyIterator();
            while (key_it.next()) |key| {
                self.allocator.free(key.*);
            }
            counts.deinit();
        }

        var original_case = std.StringHashMap([]const u8).init(self.allocator);
        defer original_case.deinit();

        for (answers) |answer| {
            // Normalize (lowercase, drop whitespace)
            var normalized = std.ArrayListUnmanaged(u8).empty;
            defer normalized.deinit(self.allocator);

            for (answer) |c| {
                if (!std.ascii.isWhitespace(c)) {
                    try normalized.append(self.allocator, std.ascii.toLower(c));
                }
            }

            const normalized_str = try normalized.toOwnedSlice(self.allocator);

            const entry = try counts.getOrPut(normalized_str);
            if (entry.found_existing) {
                // counts already owns an equal key; this one would leak.
                self.allocator.free(normalized_str);
            } else {
                entry.value_ptr.* = 0;
                // Borrows counts' key, which outlives this function's use of
                // the map, so no second dupe is needed.
                try original_case.put(entry.key_ptr.*, answer);
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

        // Group by answer, weight by response length. As in voteMajority, the
        // map owns its keys: freeing them per-iteration left the map holding
        // dangling pointers, and original_case's dupes leaked.
        var weights = std.StringHashMap(usize).init(self.allocator);
        defer {
            var key_it = weights.keyIterator();
            while (key_it.next()) |key| {
                self.allocator.free(key.*);
            }
            weights.deinit();
        }

        var original_case = std.StringHashMap([]const u8).init(self.allocator);
        defer original_case.deinit();

        var total_weight: usize = 0;

        for (answers, 0..) |answer, i| {
            const normalized = try self.allocator.dupe(u8, answer);

            const entry = try weights.getOrPut(normalized);
            if (entry.found_existing) {
                self.allocator.free(normalized);
            } else {
                entry.value_ptr.* = 0;
                try original_case.put(entry.key_ptr.*, answer);
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

test "SelfConsistency name and capabilities" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"answer"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), 3, .majority);
    const sc_agent = sc.agent();
    defer sc_agent.deinit();

    try testing.expectEqualStrings("self_consistency", sc_agent.name());

    const caps = try sc_agent.capabilities(allocator);
    defer allocator.free(caps);
    try testing.expectEqual(@as(usize, 5), caps.len);
    try testing.expectEqualStrings("reasoning", caps[0]);
    try testing.expectEqualStrings("self_consistency", caps[1]);
    try testing.expectEqualStrings("majority_voting", caps[2]);
    try testing.expectEqualStrings("reliability", caps[3]);
    try testing.expectEqualStrings("consensus", caps[4]);
}

test "SelfConsistency samples the wrapped agent num_samples times" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"The answer is 42"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), 5, .majority);
    const sc_agent = sc.agent();
    defer sc_agent.deinit();

    var msg = try Message.withText(allocator, .user, "What is the answer?");
    defer msg.deinit();

    var response = try (try sc_agent.process(msg)).unwrap();
    defer response.deinit();

    try testing.expectEqual(@as(usize, 5), mock.call_count);
    try testing.expectEqual(Role.assistant, response.role);
    try testing.expectEqualStrings("self_consistency", response.getMetadata("technique").?.string);
    try testing.expectEqual(@as(i64, 5), response.getMetadata("num_samples").?.integer);
    try testing.expectEqualStrings("majority", response.getMetadata("voting_strategy").?.string);
    // All five samples agreed, so consistency is perfect.
    try testing.expectApproxEqAbs(@as(f64, 1.0), response.getMetadata("consistency_score").?.float, 1e-9);
}

test "SelfConsistency majority vote picks the most common answer" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), 3, .majority);
    defer sc.agent().deinit();

    // "blue" wins 3-2 despite appearing after "red".
    const answers = [_][]const u8{ "red", "blue", "red", "blue", "blue" };
    const vote = try sc.voteMajority(&answers);
    defer allocator.free(vote.answer);

    try testing.expectEqualStrings("blue", vote.answer);
    try testing.expectApproxEqAbs(@as(f64, 3.0 / 5.0), vote.score, 1e-9);
}

test "SelfConsistency majority vote normalizes case and whitespace" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), 3, .majority);
    defer sc.agent().deinit();

    // These are three spellings of one answer, so it must beat the singleton.
    const answers = [_][]const u8{ "Forty Two", "forty two", "FORTYTWO", "seven" };
    const vote = try sc.voteMajority(&answers);
    defer allocator.free(vote.answer);

    // The original casing of the first occurrence is returned, not the
    // normalized key.
    try testing.expectEqualStrings("Forty Two", vote.answer);
    try testing.expectApproxEqAbs(@as(f64, 3.0 / 4.0), vote.score, 1e-9);
}

test "SelfConsistency weighted vote favors longer reasoning" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), 3, .weighted);
    defer sc.agent().deinit();

    // "b" appears once but with far more reasoning behind it, so it outweighs
    // "a"'s two terse samples — a plain count would pick "a".
    const answers = [_][]const u8{ "a", "a", "b" };
    const responses = [_][]const u8{ "x", "y", "a very long chain of reasoning indeed" };
    const vote = try sc.voteWeighted(&answers, &responses);
    defer allocator.free(vote.answer);

    try testing.expectEqualStrings("b", vote.answer);
    try testing.expect(vote.score > 0.5);
}

test "SelfConsistency first vote takes sample one" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), 3, .first);
    defer sc.agent().deinit();

    const answers = [_][]const u8{ "first", "second", "second" };
    const vote = try sc.voteFirst(&answers);
    defer allocator.free(vote.answer);

    try testing.expectEqualStrings("first", vote.answer);
    try testing.expectEqual(@as(f64, 1.0), vote.score);
}

test "SelfConsistency voting on zero samples yields an empty answer" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), 3, .majority);
    defer sc.agent().deinit();

    for ([_]VotingStrategy{ .majority, .weighted, .first }) |strategy| {
        const vote = switch (strategy) {
            .majority => try sc.voteMajority(&[_][]const u8{}),
            .weighted => try sc.voteWeighted(&[_][]const u8{}, &[_][]const u8{}),
            .first => try sc.voteFirst(&[_][]const u8{}),
        };
        defer allocator.free(vote.answer);
        try testing.expectEqualStrings("", vote.answer);
        try testing.expectEqual(@as(f64, 0.0), vote.score);
    }
}

test "SelfConsistency reports the configured voting strategy" {
    const testing = std.testing;

    for ([_]struct { strategy: VotingStrategy, name: []const u8 }{
        .{ .strategy = .majority, .name = "majority" },
        .{ .strategy = .weighted, .name = "weighted" },
        .{ .strategy = .first, .name = "first" },
    }) |case| {
        var gpa = std.heap.DebugAllocator(.{}){};
        defer _ = gpa.deinit();
        const allocator = gpa.allocator();

        var mock = try MockAgent.init(allocator, &[_][]const u8{"answer"});
        defer mock.deinit();

        var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), 2, case.strategy);
        const sc_agent = sc.agent();
        defer sc_agent.deinit();

        var msg = try Message.withText(allocator, .user, "q");
        defer msg.deinit();

        var response = try (try sc_agent.process(msg)).unwrap();
        defer response.deinit();

        try testing.expectEqualStrings(case.name, response.getMetadata("voting_strategy").?.string);
    }
}

test "defaultAnswerExtractor picks up an explicit answer marker" {
    const testing = std.testing;

    const answer = try defaultAnswerExtractor(testing.allocator, "Some reasoning. The answer is 42. Done.");
    defer testing.allocator.free(answer);
    try testing.expectEqualStrings("42", answer);
}

test "defaultAnswerExtractor does not match a marker inside a word" {
    const testing = std.testing;

    // "so" occurs inside "Some" and "also"; neither is an answer marker. The
    // byte-substring version returned "me reasoning" here.
    const answer = try defaultAnswerExtractor(testing.allocator, "Some reasoning, also nested\nlast line");
    defer testing.allocator.free(answer);
    try testing.expectEqualStrings("last line", answer);
}

test "defaultAnswerExtractor requires a separator after a prose marker" {
    const testing = std.testing;

    // "thus" must be followed by optional comma plus whitespace, so "thusly"
    // is not a marker.
    const answer = try defaultAnswerExtractor(testing.allocator, "thusly concluded\nfinal");
    defer testing.allocator.free(answer);
    try testing.expectEqualStrings("final", answer);
}

test "defaultAnswerExtractor handles each prose marker" {
    const testing = std.testing;

    for ([_][]const u8{
        "Therefore, the sky is blue.",
        "Thus the sky is blue.",
        "So, the sky is blue.",
    }) |text| {
        const answer = try defaultAnswerExtractor(testing.allocator, text);
        defer testing.allocator.free(answer);
        try testing.expectEqualStrings("the sky is blue", answer);
    }
}

test "defaultAnswerExtractor strips a nested answer-is marker" {
    const testing = std.testing;

    // Matches the reference core, whose regex consumes an optional
    // "the answer is" after therefore/thus/so.
    const answer = try defaultAnswerExtractor(testing.allocator, "Therefore, the answer is 7.");
    defer testing.allocator.free(answer);
    try testing.expectEqualStrings("7", answer);
}

test "defaultAnswerExtractor handles the colon markers" {
    const testing = std.testing;

    for ([_][]const u8{
        "Answer: blue",
        "Conclusion: blue",
        "Result: blue",
    }) |text| {
        const answer = try defaultAnswerExtractor(testing.allocator, text);
        defer testing.allocator.free(answer);
        try testing.expectEqualStrings("blue", answer);
    }
}

test "defaultAnswerExtractor falls back to the last non-empty line" {
    const testing = std.testing;

    const answer = try defaultAnswerExtractor(testing.allocator, "first line\nsecond line\n\n");
    defer testing.allocator.free(answer);
    try testing.expectEqualStrings("second line", answer);
}

test "SelfConsistency process_stream is not implemented" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), 3, .majority);
    const sc_agent = sc.agent();
    defer sc_agent.deinit();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var sink = TestSink{};
    try testing.expectError(
        AgentError.NotImplemented,
        sc_agent.processStream(msg, sink.callbacks()),
    );
    try testing.expectEqual(@as(usize, 0), sink.calls);
}

test "SelfConsistency introspection reports name and capabilities" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), 3, .majority);
    const sc_agent = sc.agent();
    defer sc_agent.deinit();

    var info = try sc_agent.introspect(allocator);
    defer info.deinit();

    try testing.expectEqualStrings("self_consistency", info.agent_name);
    try testing.expectEqual(@as(usize, 5), info.capabilities.len);
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

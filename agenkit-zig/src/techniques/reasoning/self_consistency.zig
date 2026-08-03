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
const CallOptions = @import("../../call_options.zig").CallOptions;
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

/// Configuration for Self-Consistency.
///
/// Introduced so the sampling temperature has somewhere to live that is not a
/// positional parameter, matching the other cores' `SelfConsistencyConfig`.
pub const SelfConsistencyConfig = struct {
    /// Number of independent samples to generate.
    num_samples: usize = 5,

    /// Voting strategy for answer aggregation.
    voting_strategy: VotingStrategy = .majority,

    /// Sampling temperature, forwarded to the wrapped agent on every sample.
    ///
    /// `null` means unset — no temperature is sent, rather than one being
    /// invented. Sample diversity is the mechanism this technique depends on:
    /// N samples at temperature 0 are the same answer N times, and voting over
    /// identical answers decides nothing. That is why the field exists at all,
    /// and why accepting it without forwarding it was a bug (#801) rather than
    /// an unused field.
    ///
    /// Reaching the provider also requires the wrapped agent to honour per-call
    /// options; `SelfConsistencyAgent.temperatureApplied()` reports whether it
    /// does, so a dropped temperature is visible instead of silent.
    temperature: ?f64 = null,

    /// Custom answer extraction function.
    answer_extractor: AnswerExtractor = defaultAnswerExtractor,
};

/// Self-Consistency agent
pub const SelfConsistencyAgent = struct {
    allocator: Allocator,
    base_agent: Agent,
    num_samples: usize,
    voting_strategy: VotingStrategy,
    temperature: ?f64,
    answer_extractor: AnswerExtractor,
    agent_name: []const u8,

    /// Construct a Self-Consistency agent.
    ///
    /// Fails with `error.InvalidTemperature` when `config.temperature` is set
    /// and out of range. Validated here rather than at the first sample so a
    /// misconfiguration surfaces at construction, and validated through
    /// `CallOptions.validate` so these bounds cannot drift from the ones the
    /// options themselves enforce.
    pub fn init(
        allocator: Allocator,
        base_agent: Agent,
        config: SelfConsistencyConfig,
    ) !*SelfConsistencyAgent {
        var probe = CallOptions.init(allocator);
        defer probe.deinit();
        probe.temperature = config.temperature;
        try probe.validate();

        const self = try allocator.create(SelfConsistencyAgent);
        self.* = SelfConsistencyAgent{
            .allocator = allocator,
            .base_agent = base_agent,
            .num_samples = config.num_samples,
            .voting_strategy = config.voting_strategy,
            .temperature = config.temperature,
            .answer_extractor = config.answer_extractor,
            .agent_name = "self_consistency",
        };
        return self;
    }

    /// Whether a configured temperature actually reaches the wrapped agent.
    ///
    /// True when no temperature is configured — there is nothing to drop — and
    /// when one is configured and the wrapped agent honours per-call options.
    /// False in the one case that matters: a temperature was asked for and the
    /// wrapped agent only implements `process()`, so the samples are all
    /// generated at whatever settings that agent already had. The samples then
    /// tend to agree because they are near-identical, not because the answer is
    /// reliable, and a consistency score computed from them overstates its own
    /// confidence.
    ///
    /// Public rather than internal because that failure is otherwise invisible:
    /// the technique still returns a plausible answer with a plausible score.
    pub fn temperatureApplied(self: *const SelfConsistencyAgent) bool {
        if (self.temperature == null) return true;
        return self.base_agent.supportsOptions();
    }

    /// Overlay the configured temperature on the caller's options.
    ///
    /// The configured temperature wins over the caller's. Sampling diversity is
    /// what makes this technique correct, so it is not something a caller can
    /// flatten by accident by forwarding options with a temperature of its own.
    /// Every other option the caller set survives — `CallOptions.merge` is
    /// field-by-field.
    ///
    /// The result borrows an `extra` map from one of the inputs and must not be
    /// deinited; both inputs must outlive it.
    fn sampleOptions(self: *const SelfConsistencyAgent, caller: CallOptions) CallOptions {
        if (self.temperature == null) return caller;

        var own = CallOptions.init(self.allocator);
        own.temperature = self.temperature;
        return caller.merge(own);
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
                .process_with = processWithImpl,
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

        var empty = CallOptions.init(self.allocator);
        defer empty.deinit();
        return self.run(message, &empty);
    }

    /// Implements the optional `processWith` capability (#801).
    ///
    /// This technique both consumes options — it imposes its own temperature on
    /// each sample — and forwards them, so a caller can stack it under another
    /// options-aware wrapper.
    fn processWithImpl(ptr: *anyopaque, message: Message, options: *const CallOptions) AgentError!Result {
        const self: *SelfConsistencyAgent = @ptrCast(@alignCast(ptr));
        return self.run(message, options);
    }

    /// Shared body for both entry points.
    ///
    /// Allocation failures are mapped to ProcessingFailed rather than
    /// propagated: the vtable signature is AgentError!Result, which does not
    /// include Allocator.Error.
    fn run(self: *SelfConsistencyAgent, message: Message, options: *const CallOptions) AgentError!Result {
        return self.processInner(message, options) catch |err| switch (err) {
            error.OutOfMemory => Result{ .err = AgentError.ProcessingFailed },
            else => |e| Result{ .err = e },
        };
    }

    /// The real body, allowed to fail with Allocator.Error.
    ///
    /// Split out so `try` can be used on allocating calls; `run` narrows the
    /// error set back down to what the Agent vtable declares.
    fn processInner(self: *SelfConsistencyAgent, message: Message, caller_options: *const CallOptions) (AgentError || Allocator.Error)!Result {
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

        // Merged once, outside the loop: the result is the same for every
        // sample, and it borrows an `extra` map from `caller_options`, which
        // outlives this call.
        const sample_options = self.sampleOptions(caller_options.*);

        // Generate samples
        var i: usize = 0;
        while (i < self.num_samples) : (i += 1) {
            const result = self.base_agent.processWithOptions(message, &sample_options) catch {
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

        // Both are reported so a reader can tell "no temperature requested"
        // from "requested and dropped" — a distinction temperature_applied
        // alone cannot express, and the one that says whether the consistency
        // score above was computed over genuinely independent samples.
        if (self.temperature) |t| {
            try response.setMetadata("temperature", .{ .float = t });
        } else {
            try response.setMetadata("temperature", .null);
        }
        try response.setMetadata("temperature_applied", .{ .bool = self.temperatureApplied() });

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

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{ .num_samples = 3, .voting_strategy = .majority });
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

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{ .num_samples = 5, .voting_strategy = .majority });
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

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{ .num_samples = 3, .voting_strategy = .majority });
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

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{ .num_samples = 3, .voting_strategy = .majority });
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

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{ .num_samples = 3, .voting_strategy = .weighted });
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

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{ .num_samples = 3, .voting_strategy = .first });
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

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{ .num_samples = 3, .voting_strategy = .majority });
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

        var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{ .num_samples = 2, .voting_strategy = case.strategy });
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

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{ .num_samples = 3, .voting_strategy = .majority });
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

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{ .num_samples = 3, .voting_strategy = .majority });
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

// ============================================================================
// Temperature wiring (#801)
// ============================================================================
//
// The bug this technique had: it accepted a temperature and applied it to
// nothing. Every test below asserts on what the *wrapped agent* received, not
// on what the config holds — a field that is stored and never read passes any
// test written against the field itself.

const OptionsAwareMockAgent = @import("../../test_utils.zig").OptionsAwareMockAgent;

test "SelfConsistency forwards the configured temperature on every sample" {
    const allocator = std.testing.allocator;

    var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{"The answer is 42"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{
        .num_samples = 4,
        .voting_strategy = .majority,
        .temperature = 0.9,
    });
    const sc_agent = sc.agent();
    defer sc_agent.deinit();

    var msg = try Message.withText(allocator, .user, "What is 6 * 7?");
    defer msg.deinit();

    var response = try (try sc_agent.process(msg)).unwrap();
    defer response.deinit();

    // Every sample, not just the first: sampling diversity is the technique, so
    // a temperature that reaches sample 1 and not samples 2-4 is still broken.
    try std.testing.expectEqual(@as(usize, 4), mock.getCallCount());
    try std.testing.expect(mock.allTemperaturesEqual(0.9));
}

test "SelfConsistency sends no temperature when none is configured" {
    const allocator = std.testing.allocator;

    var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{"The answer is 42"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{ .num_samples = 3 });
    const sc_agent = sc.agent();
    defer sc_agent.deinit();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var response = try (try sc_agent.process(msg)).unwrap();
    defer response.deinit();

    // Unset must stay unset. Substituting a "sensible" default would override
    // whatever the wrapped agent was configured with, on the caller's behalf and
    // without being asked.
    try std.testing.expect(mock.allTemperaturesEqual(null));
}

test "SelfConsistency forwards a temperature of 0 rather than treating it as unset" {
    const allocator = std.testing.allocator;

    var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{"The answer is 42"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{
        .num_samples = 2,
        .temperature = 0.0,
    });
    const sc_agent = sc.agent();
    defer sc_agent.deinit();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var response = try (try sc_agent.process(msg)).unwrap();
    defer response.deinit();

    // A deliberate request for greedy decoding. It makes the technique useless,
    // but that is the caller's call to make and it must be honoured verbatim —
    // a truthiness check on the value would silently discard it.
    try std.testing.expect(mock.allTemperaturesEqual(0.0));
}

test "SelfConsistency rejects an out-of-range temperature at construction" {
    const allocator = std.testing.allocator;

    var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{"x"});
    defer mock.deinit();

    // Caught at init, not at the first sample: a misconfigured temperature that
    // only surfaces mid-run has already produced partial work.
    try std.testing.expectError(
        error.InvalidTemperature,
        SelfConsistencyAgent.init(allocator, mock.agent(), .{ .temperature = 2.5 }),
    );
    try std.testing.expectError(
        error.InvalidTemperature,
        SelfConsistencyAgent.init(allocator, mock.agent(), .{ .temperature = -0.1 }),
    );

    // The boundaries are valid.
    for ([_]f64{ 0.0, 2.0 }) |t| {
        const sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{ .temperature = t });
        sc.agent().deinit();
    }
}

test "SelfConsistency temperatureApplied is true when no temperature is configured" {
    const allocator = std.testing.allocator;

    // MockAgent has no processWith, but there is nothing to drop, so the honest
    // answer is still true.
    var mock = try MockAgent.init(allocator, &[_][]const u8{"answer"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{ .num_samples = 2 });
    const sc_agent = sc.agent();
    defer sc_agent.deinit();

    try std.testing.expect(sc.temperatureApplied());
}

test "SelfConsistency temperatureApplied is false when the wrapped agent cannot honour options" {
    const allocator = std.testing.allocator;

    var mock = try MockAgent.init(allocator, &[_][]const u8{"answer"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{
        .num_samples = 3,
        .temperature = 0.9,
    });
    const sc_agent = sc.agent();
    defer sc_agent.deinit();

    // This is the case the whole change exists for. The technique still runs and
    // still returns an answer with a consistency score, but the samples were not
    // generated with the diversity that score assumes — so it says so.
    try std.testing.expect(!sc.temperatureApplied());
}

test "SelfConsistency temperatureApplied is true when the temperature reaches the agent" {
    const allocator = std.testing.allocator;

    var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{"answer"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{
        .num_samples = 3,
        .temperature = 0.9,
    });
    const sc_agent = sc.agent();
    defer sc_agent.deinit();

    try std.testing.expect(sc.temperatureApplied());
}

test "SelfConsistency reports the temperature and whether it applied in its metadata" {
    const allocator = std.testing.allocator;

    // Applied.
    {
        var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{"The answer is 42"});
        defer mock.deinit();

        var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{
            .num_samples = 2,
            .temperature = 0.7,
        });
        const sc_agent = sc.agent();
        defer sc_agent.deinit();

        var msg = try Message.withText(allocator, .user, "q");
        defer msg.deinit();

        var response = try (try sc_agent.process(msg)).unwrap();
        defer response.deinit();

        try std.testing.expectEqual(@as(f64, 0.7), response.getMetadata("temperature").?.float);
        try std.testing.expectEqual(true, response.getMetadata("temperature_applied").?.bool);
    }

    // Requested and dropped — reported as such, not omitted.
    {
        var mock = try MockAgent.init(allocator, &[_][]const u8{"The answer is 42"});
        defer mock.deinit();

        var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{
            .num_samples = 2,
            .temperature = 0.7,
        });
        const sc_agent = sc.agent();
        defer sc_agent.deinit();

        var msg = try Message.withText(allocator, .user, "q");
        defer msg.deinit();

        var response = try (try sc_agent.process(msg)).unwrap();
        defer response.deinit();

        try std.testing.expectEqual(@as(f64, 0.7), response.getMetadata("temperature").?.float);
        try std.testing.expectEqual(false, response.getMetadata("temperature_applied").?.bool);
    }

    // Never requested. `temperature` is present and null, which is a different
    // statement from the key being absent.
    {
        var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{"The answer is 42"});
        defer mock.deinit();

        var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{ .num_samples = 2 });
        const sc_agent = sc.agent();
        defer sc_agent.deinit();

        var msg = try Message.withText(allocator, .user, "q");
        defer msg.deinit();

        var response = try (try sc_agent.process(msg)).unwrap();
        defer response.deinit();

        try std.testing.expect(response.getMetadata("temperature").? == .null);
        try std.testing.expectEqual(true, response.getMetadata("temperature_applied").?.bool);
    }
}

test "SelfConsistency's own temperature wins over the caller's" {
    const allocator = std.testing.allocator;

    var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{"The answer is 42"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{
        .num_samples = 3,
        .temperature = 1.2,
    });
    const sc_agent = sc.agent();
    defer sc_agent.deinit();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var caller = CallOptions.init(allocator);
    defer caller.deinit();
    try caller.withTemperature(0.0);
    try caller.withMaxTokens(256);

    var response = try (try sc_agent.processWith(msg, &caller)).unwrap();
    defer response.deinit();

    // The caller's 0.0 would collapse the samples to one repeated answer, making
    // the vote meaningless. Diversity is what makes this technique correct, so it
    // is not something a caller can flatten in passing.
    try std.testing.expect(mock.allTemperaturesEqual(1.2));
}

test "SelfConsistency passes the caller's temperature through when it configures none" {
    const allocator = std.testing.allocator;

    var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{"The answer is 42"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{ .num_samples = 2 });
    const sc_agent = sc.agent();
    defer sc_agent.deinit();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var caller = CallOptions.init(allocator);
    defer caller.deinit();
    try caller.withTemperature(1.5);

    var response = try (try sc_agent.processWith(msg, &caller)).unwrap();
    defer response.deinit();

    // Nothing to override, so the caller's request stands. Overriding it with
    // "unset" would be the same silent discard in the other direction.
    try std.testing.expect(mock.allTemperaturesEqual(1.5));
}

test "SelfConsistency advertises the options capability" {
    const allocator = std.testing.allocator;

    var mock = try MockAgent.init(allocator, &[_][]const u8{"answer"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{});
    const sc_agent = sc.agent();
    defer sc_agent.deinit();

    // So this technique can itself be wrapped by another options-aware agent.
    try std.testing.expect(sc_agent.supportsOptions());
}

test "SelfConsistency still works when the wrapped agent ignores options" {
    const allocator = std.testing.allocator;

    var mock = try MockAgent.init(allocator, &[_][]const u8{"The answer is 42"});
    defer mock.deinit();

    var sc = try SelfConsistencyAgent.init(allocator, mock.agent(), .{
        .num_samples = 3,
        .temperature = 0.9,
    });
    const sc_agent = sc.agent();
    defer sc_agent.deinit();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    // Degraded, not broken: the fallback runs the samples plainly rather than
    // erroring, and temperatureApplied() is how a caller learns which happened.
    var response = try (try sc_agent.process(msg)).unwrap();
    defer response.deinit();

    try std.testing.expectEqual(@as(usize, 3), mock.getCallCount());
    try std.testing.expectEqualStrings("42", try response.contentAsText());
}

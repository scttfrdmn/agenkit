/// Quality metrics for agent evaluation
///
/// This module provides specialized metrics for measuring agent quality,
/// including accuracy, precision, recall, F1 score, and LLM-based quality judging.
///
/// Key design principles:
/// - Statistical accuracy measurement
/// - LLM-as-judge pattern support
/// - Classification metrics (precision/recall/F1)
/// - Configurable thresholds
const std = @import("std");
const json = std.json;
const core = @import("core.zig");
const Allocator = std.mem.Allocator;
const Agent = @import("../agent.zig").Agent;
const Message = @import("../message.zig").Message;

/// Accuracy metric - measures how often the expected fragment appears in the output.
///
/// `expected` is matched as a **substring**, case-insensitively unless
/// `case_sensitive` is set. This used to be a whole-string comparison, which made this
/// the only one of the nine cores' `AccuracyMetric` implementations not to do a
/// substring check (#820).
pub const AccuracyMetric = struct {
    name_str: []const u8,
    allocator: Allocator,
    case_sensitive: bool,

    pub fn init(allocator: Allocator, case_sensitive: bool) !*AccuracyMetric {
        const self = try allocator.create(AccuracyMetric);
        self.* = AccuracyMetric{
            .name_str = "accuracy",
            .allocator = allocator,
            .case_sensitive = case_sensitive,
        };
        return self;
    }

    /// Convert to Metric interface
    pub fn asMetric(self: *AccuracyMetric) core.Metric {
        return core.Metric{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .measure = measureImpl,
                .aggregate = aggregateImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *AccuracyMetric = @ptrCast(@alignCast(ptr));
        return self.name_str;
    }

    fn measureImpl(
        ptr: *anyopaque,
        agent: Agent,
        input: Message,
        output: Message,
        allocator: Allocator,
    ) anyerror!f64 {
        _ = agent;
        _ = input;
        const self: *AccuracyMetric = @ptrCast(@alignCast(ptr));

        // Get actual text from content
        const actual = switch (output.content) {
            .text => |t| t,
            .structured => return 0.0, // Can't compare structured content
        };

        // Get expected text from metadata
        var expected: []const u8 = "";
        if (output.metadata == .object) {
            if (output.metadata.object.get("expected")) |value| {
                if (value == .string) {
                    expected = value.string;
                } else {
                    return 0.0;
                }
            } else {
                return 0.0;
            }
        } else {
            return 0.0;
        }

        // Substring, not whole-string: `expected` is the fragment to find in the
        // output, so an agent replying "The answer is 42." matches "42". Python, Go,
        // TypeScript, Rust and C++ all do `in` / `Contains` / `includes` / `contains` /
        // `find` here; this core did `mem.eql` and scored such a reply zero (#820).
        const matches = if (self.case_sensitive)
            std.mem.indexOf(u8, actual, expected) != null
        else blk: {
            const actual_lower = try allocator.alloc(u8, actual.len);
            defer allocator.free(actual_lower);
            _ = std.ascii.lowerString(actual_lower, actual);

            const expected_lower = try allocator.alloc(u8, expected.len);
            defer allocator.free(expected_lower);
            _ = std.ascii.lowerString(expected_lower, expected);

            break :blk std.mem.indexOf(u8, actual_lower, expected_lower) != null;
        };

        return if (matches) 1.0 else 0.0;
    }

    fn aggregateImpl(
        ptr: *anyopaque,
        measurements: []const f64,
        allocator: Allocator,
    ) anyerror!std.StringHashMap(f64) {
        _ = ptr;
        var result = std.StringHashMap(f64).init(allocator);

        if (measurements.len == 0) {
            return result;
        }

        // Calculate mean accuracy
        var sum: f64 = 0.0;
        for (measurements) |m| {
            sum += m;
        }
        const mean = sum / @as(f64, @floatFromInt(measurements.len));

        const mean_key = try allocator.dupe(u8, "mean");
        try result.put(mean_key, mean);

        const count_key = try allocator.dupe(u8, "count");
        try result.put(count_key, @as(f64, @floatFromInt(measurements.len)));

        return result;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *AccuracyMetric = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};

/// Quality judging criteria
pub const QualityCriteria = struct {
    relevance: f64, // How relevant is the response
    correctness: f64, // Is the information correct
    completeness: f64, // Is the response complete
    clarity: f64, // Is the response clear

    pub fn overall(self: QualityCriteria) f64 {
        return (self.relevance + self.correctness + self.completeness + self.clarity) / 4.0;
    }
};

/// Quality metric using LLM-as-judge pattern
pub const QualityMetric = struct {
    name_str: []const u8,
    allocator: Allocator,
    judge_agent: ?Agent, // Optional LLM judge
    criteria: []const u8, // Judging criteria prompt

    pub fn init(
        allocator: Allocator,
        judge_agent: ?Agent,
        criteria: []const u8,
    ) !*QualityMetric {
        const self = try allocator.create(QualityMetric);
        self.* = QualityMetric{
            .name_str = "quality",
            .allocator = allocator,
            .judge_agent = judge_agent,
            .criteria = try allocator.dupe(u8, criteria),
        };
        return self;
    }

    pub fn asMetric(self: *QualityMetric) core.Metric {
        return core.Metric{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .measure = measureImpl,
                .aggregate = aggregateImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *QualityMetric = @ptrCast(@alignCast(ptr));
        return self.name_str;
    }

    fn measureImpl(
        ptr: *anyopaque,
        agent: Agent,
        input: Message,
        output: Message,
        allocator: Allocator,
    ) anyerror!f64 {
        _ = agent;
        const self: *QualityMetric = @ptrCast(@alignCast(ptr));

        if (self.judge_agent) |judge| {
            // Use LLM judge to evaluate quality
            const input_text = switch (input.content) {
                .text => |t| t,
                .structured => "",
            };
            const output_text = switch (output.content) {
                .text => |t| t,
                .structured => "",
            };
            const prompt = try std.fmt.allocPrint(
                allocator,
                "Evaluate the following response:\n\nInput: {s}\n\nOutput: {s}\n\nCriteria: {s}\n\nProvide a score from 0.0 to 1.0:",
                .{ input_text, output_text, self.criteria },
            );
            defer allocator.free(prompt);

            var judge_msg = try Message.withText(allocator, .user, prompt);
            defer judge_msg.deinit();

            const result = try judge.process(judge_msg);
            var response = try result.unwrap();
            defer response.deinit();

            // Parse score from response
            const score_str = switch (response.content) {
                .text => |t| t,
                .structured => return 0.5,
            };
            const score = std.fmt.parseFloat(f64, score_str) catch 0.5;

            return std.math.clamp(score, 0.0, 1.0);
        }

        // Fallback: simple heuristic scoring
        return scoreFallback(output);
    }

    fn scoreFallback(output: Message) f64 {
        const content = switch (output.content) {
            .text => |t| t,
            .structured => return 0.0,
        };

        // Simple heuristics:
        // - Length penalty: too short or too long is bad
        // - Completeness: has proper structure
        const len = content.len;
        var score: f64 = 0.5;

        // Length scoring (optimal: 50-500 chars)
        if (len < 20) {
            score -= 0.2;
        } else if (len > 50 and len < 500) {
            score += 0.2;
        } else if (len > 1000) {
            score -= 0.1;
        }

        // Check for common quality indicators
        if (std.mem.indexOf(u8, content, "because") != null or
            std.mem.indexOf(u8, content, "therefore") != null)
        {
            score += 0.1; // Has reasoning
        }

        return std.math.clamp(score, 0.0, 1.0);
    }

    fn aggregateImpl(
        ptr: *anyopaque,
        measurements: []const f64,
        allocator: Allocator,
    ) anyerror!std.StringHashMap(f64) {
        _ = ptr;
        var result = std.StringHashMap(f64).init(allocator);

        if (measurements.len == 0) {
            return result;
        }

        // Calculate statistics
        var sum: f64 = 0.0;
        var min: f64 = measurements[0];
        var max: f64 = measurements[0];

        for (measurements) |m| {
            sum += m;
            if (m < min) min = m;
            if (m > max) max = m;
        }

        const mean = sum / @as(f64, @floatFromInt(measurements.len));

        // Calculate standard deviation
        var variance_sum: f64 = 0.0;
        for (measurements) |m| {
            const diff = m - mean;
            variance_sum += diff * diff;
        }
        const std_dev = @sqrt(variance_sum / @as(f64, @floatFromInt(measurements.len)));

        const mean_key = try allocator.dupe(u8, "mean");
        try result.put(mean_key, mean);

        const min_key = try allocator.dupe(u8, "min");
        try result.put(min_key, min);

        const max_key = try allocator.dupe(u8, "max");
        try result.put(max_key, max);

        const std_dev_key = try allocator.dupe(u8, "std_dev");
        try result.put(std_dev_key, std_dev);

        return result;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *QualityMetric = @ptrCast(@alignCast(ptr));
        self.allocator.free(self.criteria);
        self.allocator.destroy(self);
    }
};

/// Classification result for precision/recall
pub const ClassificationResult = struct {
    true_positives: usize,
    false_positives: usize,
    true_negatives: usize,
    false_negatives: usize,

    pub fn precision(self: ClassificationResult) f64 {
        const tp = @as(f64, @floatFromInt(self.true_positives));
        const fp = @as(f64, @floatFromInt(self.false_positives));
        if (tp + fp == 0.0) return 0.0;
        return tp / (tp + fp);
    }

    pub fn recall(self: ClassificationResult) f64 {
        const tp = @as(f64, @floatFromInt(self.true_positives));
        const fn_val = @as(f64, @floatFromInt(self.false_negatives));
        if (tp + fn_val == 0.0) return 0.0;
        return tp / (tp + fn_val);
    }

    pub fn f1Score(self: ClassificationResult) f64 {
        const p = self.precision();
        const r = self.recall();
        if (p + r == 0.0) return 0.0;
        return 2.0 * (p * r) / (p + r);
    }

    pub fn accuracy(self: ClassificationResult) f64 {
        const total = @as(f64, @floatFromInt(
            self.true_positives + self.false_positives +
                self.true_negatives + self.false_negatives,
        ));
        if (total == 0.0) return 0.0;
        const correct = @as(f64, @floatFromInt(
            self.true_positives + self.true_negatives,
        ));
        return correct / total;
    }
};

/// Precision/Recall metric for classification tasks
pub const PrecisionRecallMetric = struct {
    name_str: []const u8,
    allocator: Allocator,
    positive_threshold: f64,
    classifications: std.ArrayList(bool), // true = correct, false = incorrect

    pub fn init(allocator: Allocator, positive_threshold: f64) !*PrecisionRecallMetric {
        const self = try allocator.create(PrecisionRecallMetric);
        self.* = PrecisionRecallMetric{
            .name_str = "precision_recall",
            .allocator = allocator,
            .positive_threshold = positive_threshold,
            .classifications = std.ArrayList(bool).empty,
        };
        return self;
    }

    pub fn asMetric(self: *PrecisionRecallMetric) core.Metric {
        return core.Metric{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .measure = measureImpl,
                .aggregate = aggregateImpl,
                .deinit = deinitImpl,
            },
        };
    }

    /// Record a classification result
    pub fn recordClassification(self: *PrecisionRecallMetric, is_correct: bool) !void {
        try self.classifications.append(self.allocator, is_correct);
    }

    /// Calculate confusion matrix
    pub fn confusionMatrix(self: *const PrecisionRecallMetric) ClassificationResult {
        var result = ClassificationResult{
            .true_positives = 0,
            .false_positives = 0,
            .true_negatives = 0,
            .false_negatives = 0,
        };

        for (self.classifications.items) |is_correct| {
            if (is_correct) {
                result.true_positives += 1;
            } else {
                result.false_positives += 1;
            }
        }

        return result;
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *PrecisionRecallMetric = @ptrCast(@alignCast(ptr));
        return self.name_str;
    }

    fn measureImpl(
        ptr: *anyopaque,
        agent: Agent,
        input: Message,
        output: Message,
        allocator: Allocator,
    ) anyerror!f64 {
        _ = agent;
        _ = input;
        _ = allocator;
        const self: *PrecisionRecallMetric = @ptrCast(@alignCast(ptr));

        // Check if output matches expected (stored in metadata)
        const expected = output.metadata.get("expected") orelse return 0.0;
        const actual = output.content orelse return 0.0;

        const is_correct = std.mem.eql(u8, actual, expected);
        try self.recordClassification(is_correct);

        return if (is_correct) 1.0 else 0.0;
    }

    fn aggregateImpl(
        ptr: *anyopaque,
        measurements: []const f64,
        allocator: Allocator,
    ) anyerror!std.StringHashMap(f64) {
        const self: *PrecisionRecallMetric = @ptrCast(@alignCast(ptr));
        var result = std.StringHashMap(f64).init(allocator);

        const confusion = self.confusionMatrix();

        const precision_key = try allocator.dupe(u8, "precision");
        try result.put(precision_key, confusion.precision());

        const recall_key = try allocator.dupe(u8, "recall");
        try result.put(recall_key, confusion.recall());

        const f1_key = try allocator.dupe(u8, "f1_score");
        try result.put(f1_key, confusion.f1Score());

        const accuracy_key = try allocator.dupe(u8, "accuracy");
        try result.put(accuracy_key, confusion.accuracy());

        // Also include raw counts
        const tp_key = try allocator.dupe(u8, "true_positives");
        try result.put(tp_key, @as(f64, @floatFromInt(confusion.true_positives)));

        const fp_key = try allocator.dupe(u8, "false_positives");
        try result.put(fp_key, @as(f64, @floatFromInt(confusion.false_positives)));

        _ = measurements; // Measurements already recorded internally

        return result;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *PrecisionRecallMetric = @ptrCast(@alignCast(ptr));
        self.classifications.deinit(self.allocator);
        self.allocator.destroy(self);
    }
};

// Tests
test "AccuracyMetric case sensitive" {
    const allocator = std.testing.allocator;

    const metric = try AccuracyMetric.init(allocator, true);
    defer metric.allocator.destroy(metric);

    // Test exact match
    var output1 = try Message.withText(allocator, .assistant, "Hello");
    defer output1.deinit();
    try output1.metadata.object.put(allocator, "expected", json.Value{ .string = "Hello" });

    // Mock agent and input (not used in accuracy measurement)
    const agent = Agent{ .ptr = undefined, .vtable = undefined };
    var input = try Message.withText(allocator, .user, "test");
    defer input.deinit();

    const score1 = try metric.asMetric().measure(agent, input, output1, allocator);
    try std.testing.expectEqual(@as(f64, 1.0), score1);

    // Test mismatch
    var output2 = try Message.withText(allocator, .assistant, "hello");
    defer output2.deinit();
    try output2.metadata.object.put(allocator, "expected", json.Value{ .string = "Hello" });

    const score2 = try metric.asMetric().measure(agent, input, output2, allocator);
    try std.testing.expectEqual(@as(f64, 0.0), score2);
}

test "AccuracyMetric case insensitive" {
    const allocator = std.testing.allocator;

    const metric = try AccuracyMetric.init(allocator, false);
    defer metric.allocator.destroy(metric);

    var output = try Message.withText(allocator, .assistant, "hello");
    defer output.deinit();
    try output.metadata.object.put(allocator, "expected", json.Value{ .string = "HELLO" });

    const agent = Agent{ .ptr = undefined, .vtable = undefined };
    var input = try Message.withText(allocator, .user, "test");
    defer input.deinit();

    const score = try metric.asMetric().measure(agent, input, output, allocator);
    try std.testing.expectEqual(@as(f64, 1.0), score);
}

test "AccuracyMetric matches an expected fragment inside a longer reply" {
    const allocator = std.testing.allocator;

    // The two tests above compare whole strings, so they pass under either semantics.
    // This one distinguishes them: `expected` is a fragment to find in the output, which
    // is what Python (`in`), Go (`Contains`), TypeScript (`includes`), Rust
    // (`contains`) and C++ (`find`) all do. This core used `mem.eql` and scored a reply
    // like "The answer is 42." zero (#820).
    const metric = try AccuracyMetric.init(allocator, false);
    defer metric.allocator.destroy(metric);

    const agent = Agent{ .ptr = undefined, .vtable = undefined };
    var input = try Message.withText(allocator, .user, "What is 15 + 27?");
    defer input.deinit();

    var hit = try Message.withText(allocator, .assistant, "The answer is 42.");
    defer hit.deinit();
    try hit.metadata.object.put(allocator, "expected", json.Value{ .string = "42" });
    try std.testing.expectEqual(
        @as(f64, 1.0),
        try metric.asMetric().measure(agent, input, hit, allocator),
    );

    // Substring, but still case-insensitive, and still a miss when absent.
    var mixed_case = try Message.withText(allocator, .assistant, "The capital is PaRiS, in France.");
    defer mixed_case.deinit();
    try mixed_case.metadata.object.put(allocator, "expected", json.Value{ .string = "paris" });
    try std.testing.expectEqual(
        @as(f64, 1.0),
        try metric.asMetric().measure(agent, input, mixed_case, allocator),
    );

    var miss = try Message.withText(allocator, .assistant, "The answer is 41.");
    defer miss.deinit();
    try miss.metadata.object.put(allocator, "expected", json.Value{ .string = "42" });
    try std.testing.expectEqual(
        @as(f64, 0.0),
        try metric.asMetric().measure(agent, input, miss, allocator),
    );
}

test "AccuracyMetric case_sensitive still matches a fragment" {
    const allocator = std.testing.allocator;

    // `case_sensitive` controls case only — it does not restore whole-string matching.
    const metric = try AccuracyMetric.init(allocator, true);
    defer metric.allocator.destroy(metric);

    const agent = Agent{ .ptr = undefined, .vtable = undefined };
    var input = try Message.withText(allocator, .user, "Capital of France?");
    defer input.deinit();

    var hit = try Message.withText(allocator, .assistant, "It is Paris, in the north.");
    defer hit.deinit();
    try hit.metadata.object.put(allocator, "expected", json.Value{ .string = "Paris" });
    try std.testing.expectEqual(
        @as(f64, 1.0),
        try metric.asMetric().measure(agent, input, hit, allocator),
    );

    var wrong_case = try Message.withText(allocator, .assistant, "It is paris, in the north.");
    defer wrong_case.deinit();
    try wrong_case.metadata.object.put(allocator, "expected", json.Value{ .string = "Paris" });
    try std.testing.expectEqual(
        @as(f64, 0.0),
        try metric.asMetric().measure(agent, input, wrong_case, allocator),
    );
}

test "AccuracyMetric aggregate" {
    const allocator = std.testing.allocator;

    const metric = try AccuracyMetric.init(allocator, true);
    defer metric.allocator.destroy(metric);

    const measurements = [_]f64{ 1.0, 1.0, 0.0, 1.0, 0.0 };
    var aggregated = try metric.asMetric().aggregate(&measurements, allocator);
    defer {
        var it = aggregated.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        aggregated.deinit();
    }

    const mean = aggregated.get("mean").?;
    try std.testing.expectEqual(@as(f64, 0.6), mean);

    const count = aggregated.get("count").?;
    try std.testing.expectEqual(@as(f64, 5.0), count);
}

test "QualityMetric fallback scoring" {
    const allocator = std.testing.allocator;

    const criteria = "Evaluate relevance and correctness";
    const metric = try QualityMetric.init(allocator, null, criteria);
    defer {
        allocator.free(metric.criteria);
        allocator.destroy(metric);
    }

    // Test short response (low quality)
    var output1 = try Message.withText(allocator, .assistant, "Yes");
    defer output1.deinit();

    const agent = Agent{ .ptr = undefined, .vtable = undefined };
    var input = try Message.withText(allocator, .user, "test");
    defer input.deinit();

    const score1 = try metric.asMetric().measure(agent, input, output1, allocator);
    try std.testing.expect(score1 < 0.5);

    // Test longer response with reasoning (higher quality)
    var output2 = try Message.withText(
        allocator,
        .assistant,
        "Yes, this is correct because it follows the fundamental principles of the domain.",
    );
    defer output2.deinit();

    const score2 = try metric.asMetric().measure(agent, input, output2, allocator);
    try std.testing.expect(score2 > 0.5);
}

test "ClassificationResult metrics" {
    const result = ClassificationResult{
        .true_positives = 80,
        .false_positives = 20,
        .true_negatives = 70,
        .false_negatives = 10,
    };

    const precision = result.precision();
    try std.testing.expectApproxEqAbs(@as(f64, 0.8), precision, 0.001);

    const recall = result.recall();
    try std.testing.expectApproxEqAbs(@as(f64, 0.888), recall, 0.01);

    const f1 = result.f1Score();
    try std.testing.expect(f1 > 0.8 and f1 < 0.9);

    const accuracy = result.accuracy();
    try std.testing.expectApproxEqAbs(@as(f64, 0.833), accuracy, 0.01);
}

test "PrecisionRecallMetric" {
    const allocator = std.testing.allocator;

    const metric = try PrecisionRecallMetric.init(allocator, 0.5);
    defer {
        metric.classifications.deinit(allocator);
        allocator.destroy(metric);
    }

    // Record some classifications
    try metric.recordClassification(true);
    try metric.recordClassification(true);
    try metric.recordClassification(false);
    try metric.recordClassification(true);

    const confusion = metric.confusionMatrix();
    try std.testing.expectEqual(@as(usize, 3), confusion.true_positives);
    try std.testing.expectEqual(@as(usize, 1), confusion.false_positives);
}

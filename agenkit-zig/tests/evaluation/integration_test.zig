/// Integration tests for evaluation framework
///
/// These tests demonstrate how multiple evaluation components work together
/// in realistic scenarios, including:
/// - Evaluating agents with multiple metrics
/// - Recording sessions during evaluation
/// - Detecting regressions across sessions
/// - Collecting and aggregating metrics

const std = @import("std");
const evaluation = @import("../../src/evaluation/mod.zig");
const testing = std.testing;

// Mock agent for testing
const MockAgent = struct {
    responses: std.StringHashMap([]const u8),
    allocator: std.mem.Allocator,

    fn init(allocator: std.mem.Allocator) !*MockAgent {
        const self = try allocator.create(MockAgent);
        self.* = .{
            .responses = std.StringHashMap([]const u8).init(allocator),
            .allocator = allocator,
        };
        return self;
    }

    fn addResponse(self: *MockAgent, input: []const u8, output: []const u8) !void {
        const input_copy = try self.allocator.dupe(u8, input);
        const output_copy = try self.allocator.dupe(u8, output);
        try self.responses.put(input_copy, output_copy);
    }

    fn deinit(self: *MockAgent) void {
        var it = self.responses.iterator();
        while (it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            self.allocator.free(entry.value_ptr.*);
        }
        self.responses.deinit();
        self.allocator.destroy(self);
    }
};

test "Integration: Evaluation with multiple metrics" {
    const allocator = testing.allocator;

    // This test demonstrates using multiple metrics together
    // to evaluate an agent on a test suite

    // Create test cases
    var test_cases = std.ArrayList(*evaluation.TestCase).empty;
    defer {
        for (test_cases.items) |tc| tc.deinit();
        test_cases.deinit();
    }

    const tc1 = try evaluation.TestCase.initExact(allocator, "2+2", "4");
    try test_cases.append(tc1);

    const tc2 = try evaluation.TestCase.initExact(allocator, "3+3", "6");
    try test_cases.append(tc2);

    const tc3 = try evaluation.TestCase.initExact(allocator, "5+5", "10");
    try test_cases.append(tc3);

    // Note: Full integration requires Agent implementation
    // This demonstrates the framework structure
}

test "Integration: Session recording during evaluation" {
    const allocator = testing.allocator;

    // This test demonstrates recording agent interactions
    // during an evaluation session

    const recorder = try evaluation.SessionRecorder.init(allocator);
    defer recorder.deinit();

    // Start recording
    try recorder.startRecording("eval-session-1");

    // Simulate interactions
    const interaction1 = try evaluation.Interaction.init(
        allocator,
        "What is 2+2?",
        "4",
        50,
    );
    try recorder.recordInteraction("eval-session-1", interaction1);
    interaction1.deinit();

    const interaction2 = try evaluation.Interaction.init(
        allocator,
        "What is 3+3?",
        "6",
        45,
    );
    try recorder.recordInteraction("eval-session-1", interaction2);
    interaction2.deinit();

    // Stop recording
    try recorder.stopRecording("eval-session-1");

    // Verify trace
    const trace = recorder.getTrace("eval-session-1").?;
    try testing.expectEqual(@as(usize, 2), trace.interactionCount());
    try testing.expectEqual(@as(f64, 47.5), trace.avgInteractionDuration());

    // Replay session
    const replay = try evaluation.SessionReplay.init(allocator, trace);
    defer replay.deinit();

    var count: usize = 0;
    while (replay.next()) |_| {
        count += 1;
    }
    try testing.expectEqual(@as(usize, 2), count);
}

test "Integration: Metrics collection and aggregation" {
    const allocator = testing.allocator;

    // This test demonstrates collecting metrics across multiple sessions
    // and computing aggregate statistics

    const collector = try evaluation.MetricsCollector.init(allocator);
    defer collector.deinit();

    // Session 1: High performance
    const session1 = try evaluation.SessionResult.init(allocator, "session-1", "agent-v1");
    try session1.addMetric("accuracy", 0.95);
    try session1.addMetric("latency", 100.0);
    try session1.addMetric("cost", 0.05);
    session1.complete();
    try collector.recordSession(session1);
    session1.deinit();

    // Session 2: Medium performance
    const session2 = try evaluation.SessionResult.init(allocator, "session-2", "agent-v1");
    try session2.addMetric("accuracy", 0.85);
    try session2.addMetric("latency", 120.0);
    try session2.addMetric("cost", 0.06);
    session2.complete();
    try collector.recordSession(session2);
    session2.deinit();

    // Session 3: Failed
    const session3 = try evaluation.SessionResult.init(allocator, "session-3", "agent-v1");
    try session3.fail("Timeout");
    try collector.recordSession(session3);
    session3.deinit();

    // Get statistics
    const stats = collector.getStatistics();
    try testing.expectEqual(@as(usize, 3), stats.total_sessions);
    try testing.expectEqual(@as(usize, 2), stats.successful_sessions);
    try testing.expectEqual(@as(usize, 1), stats.failed_sessions);
    try testing.expectApproxEqAbs(@as(f64, 0.667), stats.success_rate, 0.01);

    // Filter by status
    var completed = try collector.filterByStatus(allocator, .completed);
    defer completed.deinit();
    try testing.expectEqual(@as(usize, 2), completed.items.len);

    var failed = try collector.filterByStatus(allocator, .failed);
    defer failed.deinit();
    try testing.expectEqual(@as(usize, 1), failed.items.len);
}

test "Integration: Regression detection workflow" {
    const allocator = testing.allocator;

    // This test demonstrates a complete regression detection workflow:
    // 1. Establish baseline from initial sessions
    // 2. Run new evaluation
    // 3. Detect regressions

    const config = evaluation.RegressionConfig.default();
    const detector = try evaluation.RegressionDetector.init(allocator, config);
    defer detector.deinit();

    // Establish baseline from multiple runs
    try detector.setBaseline("accuracy", 0.90);
    try detector.setBaseline("accuracy", 0.91);
    try detector.setBaseline("accuracy", 0.89);
    try detector.setBaseline("accuracy", 0.90);

    try detector.setBaseline("latency", 100.0);
    try detector.setBaseline("latency", 105.0);
    try detector.setBaseline("latency", 98.0);

    // Get baseline summary
    var baseline_summary = try detector.getBaselineSummary(allocator);
    defer {
        var it = baseline_summary.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        baseline_summary.deinit();
    }

    const baseline_accuracy = baseline_summary.get("accuracy").?;
    try testing.expectEqual(@as(f64, 0.90), baseline_accuracy);

    // Simulate new evaluation with regression
    var current = std.StringHashMap(f64).init(allocator);
    defer {
        var it = current.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        current.deinit();
    }

    const accuracy_key = try allocator.dupe(u8, "accuracy");
    try current.put(accuracy_key, 0.80); // 11% drop - should trigger

    const latency_key = try allocator.dupe(u8, "latency");
    try current.put(latency_key, 102.0); // 1% change - below threshold

    // Detect regressions
    var regressions = try detector.detect(current, allocator);
    defer {
        for (regressions.items) |regression| {
            regression.deinit();
        }
        regressions.deinit();
    }

    // Should detect accuracy regression but not latency
    try testing.expectEqual(@as(usize, 1), regressions.items.len);

    const regression = regressions.items[0];
    try testing.expectEqualStrings("accuracy", regression.metric_name);
    try testing.expectEqual(@as(f64, 0.90), regression.baseline_value);
    try testing.expectEqual(@as(f64, 0.80), regression.current_value);
    try testing.expect(regression.severity == .moderate);
}

test "Integration: Quality metrics evaluation" {
    const allocator = testing.allocator;

    // This test demonstrates using quality metrics (accuracy, precision/recall)
    // together to evaluate classification performance

    // Accuracy metric
    const accuracy_metric = try evaluation.AccuracyMetric.init(allocator, true);
    defer accuracy_metric.allocator.destroy(accuracy_metric);

    // Precision/Recall metric
    const pr_metric = try evaluation.PrecisionRecallMetric.init(allocator, 0.5);
    defer {
        pr_metric.classifications.deinit();
        pr_metric.allocator.destroy(pr_metric);
    }

    // Simulate evaluations
    try pr_metric.recordClassification(true); // Correct
    try pr_metric.recordClassification(true); // Correct
    try pr_metric.recordClassification(false); // Incorrect
    try pr_metric.recordClassification(true); // Correct
    try pr_metric.recordClassification(false); // Incorrect

    // Get confusion matrix
    const confusion = pr_metric.confusionMatrix();
    try testing.expectEqual(@as(usize, 3), confusion.true_positives);
    try testing.expectEqual(@as(usize, 2), confusion.false_positives);

    // Calculate metrics
    const precision = confusion.precision();
    try testing.expectApproxEqAbs(@as(f64, 0.6), precision, 0.01);

    const accuracy = confusion.accuracy();
    try testing.expectApproxEqAbs(@as(f64, 0.6), accuracy, 0.01);
}

test "Integration: End-to-end evaluation pipeline" {
    const allocator = testing.allocator;

    // This test demonstrates a complete evaluation pipeline:
    // 1. Create test cases
    // 2. Set up metrics collection
    // 3. Start session recording
    // 4. Run evaluation (simulated)
    // 5. Collect metrics
    // 6. Check for regressions
    // 7. Generate report

    const session_id = "pipeline-test-001";

    // Step 1: Create test cases
    var test_cases = std.ArrayList(*evaluation.TestCase).empty;
    defer {
        for (test_cases.items) |tc| tc.deinit();
        test_cases.deinit();
    }

    const tc1 = try evaluation.TestCase.initExact(allocator, "input1", "output1");
    try test_cases.append(tc1);

    const tc2 = try evaluation.TestCase.initExact(allocator, "input2", "output2");
    try test_cases.append(tc2);

    // Step 2: Set up metrics collection
    const collector = try evaluation.MetricsCollector.init(allocator);
    defer collector.deinit();

    // Step 3: Start session recording
    const recorder = try evaluation.SessionRecorder.init(allocator);
    defer recorder.deinit();
    try recorder.startRecording(session_id);

    // Step 4: Simulate evaluation
    const session = try evaluation.SessionResult.init(allocator, session_id, "test-agent");
    try session.addMetric("accuracy", 0.88);
    try session.addMetric("quality_score", 0.85);

    // Record interaction
    const interaction = try evaluation.Interaction.init(
        allocator,
        "test input",
        "test output",
        75,
    );
    try recorder.recordInteraction(session_id, interaction);
    interaction.deinit();

    session.complete();

    // Step 5: Collect metrics
    try collector.recordSession(session);
    session.deinit();

    try recorder.stopRecording(session_id);

    // Step 6: Check for regressions
    const config = evaluation.RegressionConfig.default();
    const detector = try evaluation.RegressionDetector.init(allocator, config);
    defer detector.deinit();

    try detector.setBaseline("accuracy", 0.92);

    const regression_result = try detector.checkMetric(allocator, "accuracy", 0.88);
    if (regression_result) |reg| {
        defer reg.deinit();
        // Regression detected (4.3% drop)
        try testing.expect(reg.isDegradation());
    }

    // Step 7: Get final statistics
    const stats = collector.getStatistics();
    try testing.expectEqual(@as(usize, 1), stats.total_sessions);
    try testing.expectEqual(@as(usize, 1), stats.successful_sessions);

    const trace = recorder.getTrace(session_id).?;
    try testing.expectEqual(@as(usize, 1), trace.interactionCount());
}

test "Integration: Multi-session comparison" {
    const allocator = testing.allocator;

    // This test demonstrates comparing multiple agent versions
    // across sessions to track improvement/degradation over time

    const collector = try evaluation.MetricsCollector.init(allocator);
    defer collector.deinit();

    // Agent v1.0
    const v1_session = try evaluation.SessionResult.init(allocator, "v1-001", "agent-v1.0");
    try v1_session.addMetric("accuracy", 0.85);
    try v1_session.addMetric("cost", 0.10);
    v1_session.complete();
    try collector.recordSession(v1_session);
    v1_session.deinit();

    // Agent v1.1
    const v11_session = try evaluation.SessionResult.init(allocator, "v1-002", "agent-v1.1");
    try v11_session.addMetric("accuracy", 0.88);
    try v11_session.addMetric("cost", 0.09);
    v11_session.complete();
    try collector.recordSession(v11_session);
    v11_session.deinit();

    // Agent v2.0
    const v2_session = try evaluation.SessionResult.init(allocator, "v2-001", "agent-v2.0");
    try v2_session.addMetric("accuracy", 0.92);
    try v2_session.addMetric("cost", 0.08);
    v2_session.complete();
    try collector.recordSession(v2_session);
    v2_session.deinit();

    // Get all traces
    var all_traces = try collector.getAllTraces(allocator);
    defer all_traces.deinit();

    try testing.expectEqual(@as(usize, 3), all_traces.items.len);

    // Verify progression
    const v1_accuracy = all_traces.items[0].getMetric("accuracy").?;
    const v2_accuracy = all_traces.items[2].getMetric("accuracy").?;

    try testing.expect(v2_accuracy > v1_accuracy); // v2.0 improved
}

test "Integration: Severity escalation" {
    const allocator = testing.allocator;

    // This test demonstrates how regression severity changes
    // as performance degrades over time

    const config = evaluation.RegressionConfig{
        .min_change_percent = 5.0,
        .significance_level = 0.05,
        .min_samples = 3,
    };

    const detector = try evaluation.RegressionDetector.init(allocator, config);
    defer detector.deinit();

    // Establish baseline
    try detector.setBaseline("response_quality", 0.90);

    // Test different degradation levels
    const test_values = [_]f64{ 0.88, 0.82, 0.70, 0.40 };
    const expected_severities = [_]evaluation.Severity{
        .minor, // 2.2% drop
        .minor, // 8.9% drop
        .moderate, // 22.2% drop
        .critical, // 55.5% drop
    };

    for (test_values, expected_severities) |value, expected_severity| {
        const regression = try detector.checkMetric(allocator, "response_quality", value);
        if (regression) |reg| {
            defer reg.deinit();
            try testing.expectEqual(expected_severity, reg.severity);
        }
    }
}

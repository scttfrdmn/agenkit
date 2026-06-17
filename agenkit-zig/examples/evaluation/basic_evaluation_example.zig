/// Basic Evaluation Example
///
/// This example demonstrates:
/// - Creating test cases
/// - Setting up accuracy metrics
/// - Running evaluations
/// - Collecting results
///
/// Run with: zig build run-evaluation-basic

const std = @import("std");
const agenkit = @import("agenkit");
const evaluation = agenkit.evaluation;

pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n{s}\n", .{"=" ** 70});
    std.debug.print("Basic Evaluation Example\n", .{});
    std.debug.print("{s}\n\n", .{"=" ** 70});

    // ========================================================================
    // Step 1: Create Test Cases
    // ========================================================================
    std.debug.print("Step 1: Creating test cases...\n", .{});

    var test_cases = std.ArrayList(*evaluation.TestCase).empty;
    defer {
        for (test_cases.items) |tc| tc.deinit();
        test_cases.deinit(allocator);
    }

    // Math test cases
    const tc1 = try evaluation.TestCase.initExact(allocator, "What is 2 + 2?", "4");
    try tc1.addMetadata("category", "math");
    try tc1.addMetadata("difficulty", "easy");
    try test_cases.append(allocator, tc1);

    const tc2 = try evaluation.TestCase.initExact(allocator, "What is 10 - 3?", "7");
    try tc2.addMetadata("category", "math");
    try tc2.addMetadata("difficulty", "easy");
    try test_cases.append(allocator, tc2);

    const tc3 = try evaluation.TestCase.initExact(allocator, "What is 5 × 6?", "30");
    try tc3.addMetadata("category", "math");
    try tc3.addMetadata("difficulty", "medium");
    try test_cases.append(allocator, tc3);

    // Functional test case with custom validator
    const lengthValidator = struct {
        fn validate(output: []const u8) bool {
            return output.len > 10 and output.len < 100;
        }
    }.validate;

    const tc4 = try evaluation.TestCase.initFunctional(
        allocator,
        "Explain photosynthesis",
        lengthValidator,
    );
    try tc4.addMetadata("category", "science");
    try tc4.addMetadata("difficulty", "hard");
    try test_cases.append(allocator, tc4);

    std.debug.print("  ✓ Created {} test cases\n\n", .{test_cases.items.len});

    // ========================================================================
    // Step 2: Display Test Cases
    // ========================================================================
    std.debug.print("Step 2: Test Cases:\n", .{});
    for (test_cases.items, 0..) |tc, i| {
        std.debug.print("  [{d}] Input: {s}\n", .{ i + 1, tc.input });
        switch (tc.expected) {
            .exact => |expected| std.debug.print("      Expected: {s}\n", .{expected}),
            .functional => std.debug.print("      Expected: <functional validator>\n", .{}),
        }
        if (tc.metadata.get("category")) |cat| {
            std.debug.print("      Category: {s}\n", .{cat});
        }
    }
    std.debug.print("\n", .{});

    // ========================================================================
    // Step 3: Create Evaluation Result
    // ========================================================================
    std.debug.print("Step 3: Simulating evaluation...\n", .{});

    const result = try evaluation.EvaluationResult.init(allocator, "example-session-001");
    defer result.deinit();

    result.n_cases = test_cases.items.len;

    // Simulate evaluation results (in real usage, agent would process these)
    result.n_passed = 3; // Assume 3 out of 4 passed

    // Add simulated metrics
    try result.addMetric("accuracy", result.successRate());
    try result.addMetric("avg_latency_ms", 125.5);
    try result.addMetric("total_cost", 0.08);

    // Add an error for the failed case
    const error_record = try evaluation.ErrorRecord.init(
        allocator,
        3, // Test case index
        "validation_failed",
        "Response too short for functional validator",
    );
    try result.addError(error_record);

    std.debug.print("  ✓ Evaluation complete\n\n", .{});

    // ========================================================================
    // Step 4: Display Results
    // ========================================================================
    std.debug.print("Step 4: Results:\n", .{});
    std.debug.print("{s}\n", .{"-" ** 70});
    std.debug.print("Session ID: {s}\n", .{result.session_id});
    std.debug.print("Total Cases: {d}\n", .{result.n_cases});
    std.debug.print("Passed: {d}\n", .{result.n_passed});
    std.debug.print("Failed: {d}\n", .{result.n_cases - result.n_passed});
    std.debug.print("Success Rate: {d:.1}%\n", .{result.successRate() * 100.0});
    std.debug.print("\nMetrics:\n", .{});

    var metrics_it = result.metrics.iterator();
    while (metrics_it.next()) |entry| {
        std.debug.print("  {s}: {d:.3}\n", .{ entry.key_ptr.*, entry.value_ptr.* });
    }

    if (result.errors.items.len > 0) {
        std.debug.print("\nErrors:\n", .{});
        for (result.errors.items) |err| {
            std.debug.print("  [Test {d}] {s}: {s}\n", .{
                err.test_case_index,
                err.error_type,
                err.message,
            });
        }
    }

    std.debug.print("{s}\n\n", .{"-" ** 70});

    // ========================================================================
    // Summary
    // ========================================================================
    std.debug.print("Summary:\n", .{});
    std.debug.print("  ✓ Test suite creation\n", .{});
    std.debug.print("  ✓ Exact match validation\n", .{});
    std.debug.print("  ✓ Functional validation\n", .{});
    std.debug.print("  ✓ Metadata tracking\n", .{});
    std.debug.print("  ✓ Error recording\n", .{});
    std.debug.print("  ✓ Metric collection\n", .{});

    std.debug.print("\nNext Steps:\n", .{});
    std.debug.print("  • Run session_recording_example.zig to see recording in action\n", .{});
    std.debug.print("  • Run regression_detection_example.zig to track performance over time\n", .{});
    std.debug.print("  • Integrate with real agents for production evaluation\n", .{});

    std.debug.print("\n{s}\n", .{"=" ** 70});
}

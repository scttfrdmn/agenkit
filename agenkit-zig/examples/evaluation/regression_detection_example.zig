/// Regression Detection Example
///
/// This example demonstrates:
/// - Establishing performance baselines
/// - Detecting regressions
/// - Severity classification
/// - Statistical significance testing
///
/// Run with: zig build run-evaluation-regression

const std = @import("std");
const agenkit = @import("agenkit");
const evaluation = agenkit.evaluation;

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n{s}\n", .{"=" ** 70});
    std.debug.print("Regression Detection Example\n", .{});
    std.debug.print("{s}\n\n", .{"=" ** 70});

    // ========================================================================
    // Step 1: Configure Detector
    // ========================================================================
    std.debug.print("Step 1: Configuring regression detector...\n", .{});

    const config = evaluation.RegressionConfig{
        .min_change_percent = 5.0, // Alert on 5% or greater change
        .significance_level = 0.05, // 95% confidence
        .min_samples = 5, // Need 5 samples for statistical test
    };

    const detector = try evaluation.RegressionDetector.init(allocator, config);
    defer detector.deinit();

    std.debug.print("  Configuration:\n", .{});
    std.debug.print("    Min Change: {d}%\n", .{config.min_change_percent});
    std.debug.print("    Significance Level: {d}\n", .{config.significance_level});
    std.debug.print("    Min Samples: {d}\n\n", .{config.min_samples});

    // ========================================================================
    // Step 2: Establish Baseline (Week 1)
    // ========================================================================
    std.debug.print("Step 2: Establishing baseline from Week 1 runs...\n", .{});

    // Accuracy baseline (5 runs)
    const accuracy_samples = [_]f64{ 0.92, 0.91, 0.93, 0.90, 0.92 };
    for (accuracy_samples) |sample| {
        try detector.setBaseline("accuracy", sample);
    }
    std.debug.print("  ✓ Accuracy baseline: 5 samples\n", .{});

    // Latency baseline (5 runs)
    const latency_samples = [_]f64{ 125.0, 130.0, 120.0, 128.0, 127.0 };
    for (latency_samples) |sample| {
        try detector.setBaseline("latency_ms", sample);
    }
    std.debug.print("  ✓ Latency baseline: 5 samples\n", .{});

    // Cost baseline (5 runs)
    const cost_samples = [_]f64{ 0.08, 0.09, 0.08, 0.08, 0.09 };
    for (cost_samples) |sample| {
        try detector.setBaseline("cost_usd", sample);
    }
    std.debug.print("  ✓ Cost baseline: 5 samples\n\n", .{});

    // Display baseline summary
    std.debug.print("  Baseline Summary:\n", .{});
    var baseline_summary = try detector.getBaselineSummary(allocator);
    defer {
        var it = baseline_summary.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        baseline_summary.deinit();
    }

    var baseline_it = baseline_summary.iterator();
    while (baseline_it.next()) |entry| {
        std.debug.print("    {s}: {d:.4}\n", .{ entry.key_ptr.*, entry.value_ptr.* });
    }
    std.debug.print("\n", .{});

    // ========================================================================
    // Step 3: Week 2 - No Regression
    // ========================================================================
    std.debug.print("Step 3: Week 2 evaluation (no regression expected)...\n", .{});
    std.debug.print("{s}\n", .{"-" ** 70});

    var week2_metrics = std.StringHashMap(f64).init(allocator);
    defer {
        var it = week2_metrics.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        week2_metrics.deinit();
    }

    try week2_metrics.put(try allocator.dupe(u8, "accuracy"), 0.91); // -1.1% (below threshold)
    try week2_metrics.put(try allocator.dupe(u8, "latency_ms"), 128.0); // +1.6% (below threshold)
    try week2_metrics.put(try allocator.dupe(u8, "cost_usd"), 0.085); // +4.7% (below threshold)

    var week2_regressions = try detector.detect(week2_metrics, allocator);
    defer {
        for (week2_regressions.items) |reg| {
            reg.deinit();
        }
        week2_regressions.deinit(allocator);
    }

    std.debug.print("Regressions Detected: {d}\n", .{week2_regressions.items.len});
    if (week2_regressions.items.len == 0) {
        std.debug.print("✓ All metrics within acceptable range\n", .{});
    }
    std.debug.print("{s}\n\n", .{"-" ** 70});

    // ========================================================================
    // Step 4: Week 3 - Minor Regression
    // ========================================================================
    std.debug.print("Step 4: Week 3 evaluation (minor regression)...\n", .{});
    std.debug.print("{s}\n", .{"-" ** 70});

    var week3_metrics = std.StringHashMap(f64).init(allocator);
    defer {
        var it = week3_metrics.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        week3_metrics.deinit();
    }

    try week3_metrics.put(try allocator.dupe(u8, "accuracy"), 0.85); // -7.6% (minor)
    try week3_metrics.put(try allocator.dupe(u8, "latency_ms"), 126.0); // OK
    try week3_metrics.put(try allocator.dupe(u8, "cost_usd"), 0.08); // OK

    var week3_regressions = try detector.detect(week3_metrics, allocator);
    defer {
        for (week3_regressions.items) |reg| {
            reg.deinit();
        }
        week3_regressions.deinit(allocator);
    }

    std.debug.print("Regressions Detected: {d}\n\n", .{week3_regressions.items.len});
    for (week3_regressions.items) |reg| {
        std.debug.print("⚠️  {s}\n", .{reg.message});
        std.debug.print("    Severity: {s}\n", .{reg.severity.toString()});
        std.debug.print("    Significant: {}\n", .{reg.is_significant});
        std.debug.print("    Degradation: {}\n\n", .{reg.isDegradation()});
    }
    std.debug.print("{s}\n\n", .{"-" ** 70});

    // ========================================================================
    // Step 5: Week 4 - Severe Regression
    // ========================================================================
    std.debug.print("Step 5: Week 4 evaluation (severe regression)...\n", .{});
    std.debug.print("{s}\n", .{"-" ** 70});

    var week4_metrics = std.StringHashMap(f64).init(allocator);
    defer {
        var it = week4_metrics.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        week4_metrics.deinit();
    }

    try week4_metrics.put(try allocator.dupe(u8, "accuracy"), 0.70); // -23.9% (moderate)
    try week4_metrics.put(try allocator.dupe(u8, "latency_ms"), 180.0); // +41.7% (severe)
    try week4_metrics.put(try allocator.dupe(u8, "cost_usd"), 0.15); // +79.8% (critical)

    var week4_regressions = try detector.detect(week4_metrics, allocator);
    defer {
        for (week4_regressions.items) |reg| {
            reg.deinit();
        }
        week4_regressions.deinit(allocator);
    }

    std.debug.print("Regressions Detected: {d}\n\n", .{week4_regressions.items.len});

    // Sort by severity for display
    for (week4_regressions.items) |reg| {
        const icon = switch (reg.severity) {
            .none => "✓",
            .minor => "⚠️ ",
            .moderate => "⚠️ ",
            .severe => "🔴",
            .critical => "🔴",
        };

        std.debug.print("{s} {s}\n", .{ icon, reg.message });
        std.debug.print("    Severity: {s}\n", .{reg.severity.toString()});
        std.debug.print("    Significant: {}\n", .{reg.is_significant});
        std.debug.print("    Action: ", .{});

        switch (reg.severity) {
            .none => std.debug.print("Continue monitoring\n", .{}),
            .minor => std.debug.print("Schedule review\n", .{}),
            .moderate => std.debug.print("Investigate immediately\n", .{}),
            .severe => std.debug.print("Roll back deployment\n", .{}),
            .critical => std.debug.print("EMERGENCY: Roll back NOW\n", .{}),
        }
        std.debug.print("\n", .{});
    }

    std.debug.print("{s}\n\n", .{"-" ** 70});

    // ========================================================================
    // Step 6: Single Metric Check
    // ========================================================================
    std.debug.print("Step 6: Quick single-metric check...\n", .{});

    const quick_check = try detector.checkMetric(allocator, "accuracy", 0.88);
    if (quick_check) |reg| {
        defer reg.deinit();
        std.debug.print("  {s}\n", .{reg.message});
        std.debug.print("  Severity: {s}\n\n", .{reg.severity.toString()});
    } else {
        std.debug.print("  ✓ No regression detected\n\n", .{});
    }

    // ========================================================================
    // Step 7: Custom Thresholds
    // ========================================================================
    std.debug.print("Step 7: Setting custom thresholds...\n", .{});

    // Be more strict with accuracy (3% threshold instead of 5%)
    try detector.setThreshold("accuracy", 3.0);
    std.debug.print("  ✓ Accuracy threshold set to 3%\n", .{});

    // Be more lenient with cost (10% threshold)
    try detector.setThreshold("cost_usd", 10.0);
    std.debug.print("  ✓ Cost threshold set to 10%\n\n", .{});

    // ========================================================================
    // Summary
    // ========================================================================
    std.debug.print("Summary:\n", .{});
    std.debug.print("  ✓ Baseline establishment\n", .{});
    std.debug.print("  ✓ Multi-metric regression detection\n", .{});
    std.debug.print("  ✓ Severity classification (none → critical)\n", .{});
    std.debug.print("  ✓ Statistical significance testing\n", .{});
    std.debug.print("  ✓ Custom threshold configuration\n", .{});
    std.debug.print("  ✓ Single-metric quick checks\n", .{});

    std.debug.print("\nSeverity Levels:\n", .{});
    std.debug.print("  • None:     < 5% change\n", .{});
    std.debug.print("  • Minor:    5-10% change\n", .{});
    std.debug.print("  • Moderate: 10-25% change\n", .{});
    std.debug.print("  • Severe:   25-50% change\n", .{});
    std.debug.print("  • Critical: > 50% change\n", .{});

    std.debug.print("\nRecommended Actions:\n", .{});
    std.debug.print("  • None/Minor:   Continue monitoring, schedule review\n", .{});
    std.debug.print("  • Moderate:     Investigate immediately, may need rollback\n", .{});
    std.debug.print("  • Severe/Critical: Emergency rollback, incident response\n", .{});

    std.debug.print("\nIntegration with CI/CD:\n", .{});
    std.debug.print("  1. Run evaluation in pre-production\n", .{});
    std.debug.print("  2. Compare against baseline\n", .{});
    std.debug.print("  3. Block deployment if severe/critical regression\n", .{});
    std.debug.print("  4. Alert team if moderate regression\n", .{});
    std.debug.print("  5. Update baseline periodically with production data\n", .{});

    std.debug.print("\n{s}\n", .{"=" ** 70});
}

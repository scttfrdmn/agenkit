/// Regression detection for agent performance
///
/// This module provides infrastructure for detecting performance regressions
/// by comparing current metrics against baseline values, with statistical
/// significance testing and severity classification.
///
/// Key design principles:
/// - Statistical significance (t-test based)
/// - Configurable thresholds per metric
/// - Severity classification
/// - Actionable regression reports
const std = @import("std");
const agksync = @import("../sync_compat.zig");
const Allocator = std.mem.Allocator;

/// Severity level of a detected regression
pub const Severity = enum {
    none, // No regression detected
    minor, // < 10% degradation
    moderate, // 10-25% degradation
    severe, // 25-50% degradation
    critical, // > 50% degradation

    pub fn toString(self: Severity) []const u8 {
        return switch (self) {
            .none => "none",
            .minor => "minor",
            .moderate => "moderate",
            .severe => "severe",
            .critical => "critical",
        };
    }

    pub fn fromChangePercent(change: f64) Severity {
        const abs_change = @abs(change);
        if (abs_change < 5.0) return .none;
        if (abs_change < 10.0) return .minor;
        if (abs_change < 25.0) return .moderate;
        if (abs_change < 50.0) return .severe;
        return .critical;
    }
};

/// A detected regression in a specific metric
pub const Regression = struct {
    metric_name: []const u8,
    baseline_value: f64,
    current_value: f64,
    change_percent: f64,
    severity: Severity,
    is_significant: bool,
    message: []const u8,
    allocator: Allocator,

    pub fn init(
        allocator: Allocator,
        metric_name: []const u8,
        baseline: f64,
        current: f64,
        is_significant: bool,
    ) !*Regression {
        const change = ((current - baseline) / baseline) * 100.0;
        const severity = Severity.fromChangePercent(change);

        const message = try std.fmt.allocPrint(
            allocator,
            "{s}: {s} regression - {d:.2}% change (baseline: {d:.4}, current: {d:.4})",
            .{
                metric_name,
                severity.toString(),
                change,
                baseline,
                current,
            },
        );

        const self = try allocator.create(Regression);
        self.* = Regression{
            .metric_name = try allocator.dupe(u8, metric_name),
            .baseline_value = baseline,
            .current_value = current,
            .change_percent = change,
            .severity = severity,
            .is_significant = is_significant,
            .message = message,
            .allocator = allocator,
        };
        return self;
    }

    /// Check if this is a degradation (negative change in performance)
    pub fn isDegradation(self: *const Regression) bool {
        // For metrics where higher is better (accuracy, success rate, etc.)
        // negative change is degradation
        // For metrics where lower is better (latency, error rate, cost)
        // positive change is degradation
        // Assume higher is better by default
        return self.change_percent < 0.0;
    }

    pub fn deinit(self: *Regression) void {
        self.allocator.free(self.metric_name);
        self.allocator.free(self.message);
        self.allocator.destroy(self);
    }
};

/// Configuration for regression detection
pub const RegressionConfig = struct {
    min_change_percent: f64, // Minimum change to consider (default: 5%)
    significance_level: f64, // P-value threshold (default: 0.05)
    min_samples: usize, // Minimum samples for statistical test (default: 5)

    pub fn default() RegressionConfig {
        return RegressionConfig{
            .min_change_percent = 5.0,
            .significance_level = 0.05,
            .min_samples = 5,
        };
    }
};

/// Baseline measurement with historical samples
pub const BaselineMeasurement = struct {
    samples: std.ArrayList(f64),
    mean: f64,
    std_dev: f64,
    allocator: Allocator,

    pub fn init(allocator: Allocator) !*BaselineMeasurement {
        const self = try allocator.create(BaselineMeasurement);
        self.* = BaselineMeasurement{
            .samples = std.ArrayList(f64).empty,
            .mean = 0.0,
            .std_dev = 0.0,
            .allocator = allocator,
        };
        return self;
    }

    /// Add a sample and recalculate statistics
    pub fn addSample(self: *BaselineMeasurement, value: f64) !void {
        try self.samples.append(self.allocator, value);
        self.calculateStats();
    }

    fn calculateStats(self: *BaselineMeasurement) void {
        if (self.samples.items.len == 0) {
            self.mean = 0.0;
            self.std_dev = 0.0;
            return;
        }

        // Calculate mean
        var sum: f64 = 0.0;
        for (self.samples.items) |sample| {
            sum += sample;
        }
        self.mean = sum / @as(f64, @floatFromInt(self.samples.items.len));

        // Calculate standard deviation
        if (self.samples.items.len > 1) {
            var variance_sum: f64 = 0.0;
            for (self.samples.items) |sample| {
                const diff = sample - self.mean;
                variance_sum += diff * diff;
            }
            self.std_dev = @sqrt(variance_sum / @as(f64, @floatFromInt(self.samples.items.len - 1)));
        } else {
            self.std_dev = 0.0;
        }
    }

    pub fn deinit(self: *BaselineMeasurement) void {
        self.samples.deinit(self.allocator);
        self.allocator.destroy(self);
    }
};

/// Detects performance regressions
pub const RegressionDetector = struct {
    baseline: std.StringHashMap(*BaselineMeasurement),
    thresholds: std.StringHashMap(f64),
    config: RegressionConfig,
    allocator: Allocator,
    mutex: agksync.Mutex,

    pub fn init(allocator: Allocator, config: RegressionConfig) !*RegressionDetector {
        const self = try allocator.create(RegressionDetector);
        self.* = .{
            .baseline = std.StringHashMap(*BaselineMeasurement).init(allocator),
            .thresholds = std.StringHashMap(f64).init(allocator),
            .config = config,
            .allocator = allocator,
            .mutex = .{},
        };
        return self;
    }

    /// Set baseline value for a metric
    pub fn setBaseline(self: *RegressionDetector, metric: []const u8, value: f64) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        if (self.baseline.get(metric)) |measurement| {
            try measurement.addSample(value);
        } else {
            const metric_copy = try self.allocator.dupe(u8, metric);
            const measurement = try BaselineMeasurement.init(self.allocator);
            try measurement.addSample(value);
            try self.baseline.put(metric_copy, measurement);
        }
    }

    /// Set threshold for a specific metric (override default)
    pub fn setThreshold(self: *RegressionDetector, metric: []const u8, threshold: f64) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        const metric_copy = try self.allocator.dupe(u8, metric);
        try self.thresholds.put(metric_copy, threshold);
    }

    /// Get effective threshold for a metric
    fn getThreshold(self: *const RegressionDetector, metric: []const u8) f64 {
        return self.thresholds.get(metric) orelse self.config.min_change_percent;
    }

    /// Perform statistical significance test (simplified t-test)
    fn isSignificant(
        self: *const RegressionDetector,
        baseline_mean: f64,
        baseline_std: f64,
        baseline_n: usize,
        current_value: f64,
    ) bool {
        if (baseline_n < self.config.min_samples) {
            return false; // Not enough samples for statistical test
        }

        if (baseline_std == 0.0) {
            return false; // No variation in baseline
        }

        // Calculate z-score
        const z = (current_value - baseline_mean) / baseline_std;

        // Approximate p-value using z-score
        // For alpha = 0.05 (two-tailed), critical z ≈ 1.96
        const critical_z = 1.96;
        return @abs(z) > critical_z;
    }

    /// Detect regressions by comparing current metrics to baseline
    pub fn detect(
        self: *RegressionDetector,
        current: std.StringHashMap(f64),
        allocator: Allocator,
    ) !std.ArrayList(*Regression) {
        self.mutex.lock();
        defer self.mutex.unlock();

        var regressions = std.ArrayList(*Regression).empty;

        // Check each metric in current against baseline
        var current_it = current.iterator();
        while (current_it.next()) |entry| {
            const metric_name = entry.key_ptr.*;
            const current_value = entry.value_ptr.*;

            if (self.baseline.get(metric_name)) |measurement| {
                const baseline_mean = measurement.mean;
                const change = @abs(((current_value - baseline_mean) / baseline_mean) * 100.0);

                // Check if change exceeds threshold
                const threshold = self.getThreshold(metric_name);
                if (change >= threshold) {
                    // Check statistical significance
                    const is_sig = self.isSignificant(
                        measurement.mean,
                        measurement.std_dev,
                        measurement.samples.items.len,
                        current_value,
                    );

                    // Create regression report
                    const regression = try Regression.init(
                        allocator,
                        metric_name,
                        baseline_mean,
                        current_value,
                        is_sig,
                    );

                    try regressions.append(allocator, regression);
                }
            }
        }

        return regressions;
    }

    /// Check for a single metric regression
    pub fn checkMetric(
        self: *RegressionDetector,
        allocator: Allocator,
        metric_name: []const u8,
        current_value: f64,
    ) !?*Regression {
        self.mutex.lock();
        defer self.mutex.unlock();

        const measurement = self.baseline.get(metric_name) orelse return null;

        const baseline_mean = measurement.mean;
        const change = @abs(((current_value - baseline_mean) / baseline_mean) * 100.0);

        const threshold = self.getThreshold(metric_name);
        if (change < threshold) {
            return null; // Below threshold
        }

        const is_sig = self.isSignificant(
            measurement.mean,
            measurement.std_dev,
            measurement.samples.items.len,
            current_value,
        );

        return try Regression.init(
            allocator,
            metric_name,
            baseline_mean,
            current_value,
            is_sig,
        );
    }

    /// Get summary of all baselines
    pub fn getBaselineSummary(self: *RegressionDetector, allocator: Allocator) !std.StringHashMap(f64) {
        self.mutex.lock();
        defer self.mutex.unlock();

        var summary = std.StringHashMap(f64).init(allocator);

        var it = self.baseline.iterator();
        while (it.next()) |entry| {
            const metric_copy = try allocator.dupe(u8, entry.key_ptr.*);
            try summary.put(metric_copy, entry.value_ptr.*.mean);
        }

        return summary;
    }

    /// Clear all baselines
    pub fn clearBaselines(self: *RegressionDetector) void {
        self.mutex.lock();
        defer self.mutex.unlock();

        var it = self.baseline.iterator();
        while (it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            entry.value_ptr.*.deinit();
        }
        self.baseline.clearAndFree();

        var thresh_it = self.thresholds.iterator();
        while (thresh_it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
        }
        self.thresholds.clearAndFree();
    }

    pub fn deinit(self: *RegressionDetector) void {
        self.clearBaselines();
        self.baseline.deinit();
        self.thresholds.deinit();
        self.allocator.destroy(self);
    }
};

// Tests
test "Severity classification" {
    try std.testing.expectEqual(Severity.none, Severity.fromChangePercent(3.0));
    try std.testing.expectEqual(Severity.minor, Severity.fromChangePercent(7.0));
    try std.testing.expectEqual(Severity.moderate, Severity.fromChangePercent(15.0));
    try std.testing.expectEqual(Severity.severe, Severity.fromChangePercent(35.0));
    try std.testing.expectEqual(Severity.critical, Severity.fromChangePercent(60.0));
}

test "Regression creation" {
    const allocator = std.testing.allocator;

    const regression = try Regression.init(
        allocator,
        "accuracy",
        0.90,
        0.85,
        true,
    );
    defer regression.deinit();

    try std.testing.expectEqualStrings("accuracy", regression.metric_name);
    try std.testing.expectEqual(@as(f64, 0.90), regression.baseline_value);
    try std.testing.expectEqual(@as(f64, 0.85), regression.current_value);
    try std.testing.expect(regression.is_significant);
    try std.testing.expect(regression.isDegradation());
}

test "BaselineMeasurement statistics" {
    const allocator = std.testing.allocator;

    const measurement = try BaselineMeasurement.init(allocator);
    defer measurement.deinit();

    try measurement.addSample(10.0);
    try measurement.addSample(12.0);
    try measurement.addSample(11.0);
    try measurement.addSample(13.0);
    try measurement.addSample(14.0);

    try std.testing.expectEqual(@as(f64, 12.0), measurement.mean);
    try std.testing.expect(measurement.std_dev > 0.0);
}

test "RegressionDetector set baseline" {
    const allocator = std.testing.allocator;

    const config = RegressionConfig.default();
    const detector = try RegressionDetector.init(allocator, config);
    defer detector.deinit();

    try detector.setBaseline("accuracy", 0.90);
    try detector.setBaseline("accuracy", 0.91);
    try detector.setBaseline("accuracy", 0.89);

    var summary = try detector.getBaselineSummary(allocator);
    defer {
        var it = summary.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        summary.deinit();
    }

    const accuracy_mean = summary.get("accuracy").?;
    try std.testing.expectEqual(@as(f64, 0.90), accuracy_mean);
}

test "RegressionDetector custom threshold" {
    const allocator = std.testing.allocator;

    const config = RegressionConfig.default();
    const detector = try RegressionDetector.init(allocator, config);
    defer detector.deinit();

    try detector.setThreshold("latency", 10.0);

    const threshold = detector.getThreshold("latency");
    try std.testing.expectEqual(@as(f64, 10.0), threshold);

    const default_threshold = detector.getThreshold("accuracy");
    try std.testing.expectEqual(@as(f64, 5.0), default_threshold);
}

test "RegressionDetector detect regressions" {
    const allocator = std.testing.allocator;

    const config = RegressionConfig.default();
    const detector = try RegressionDetector.init(allocator, config);
    defer detector.deinit();

    // Set baseline for accuracy
    try detector.setBaseline("accuracy", 0.90);

    // Current metrics with regression
    var current = std.StringHashMap(f64).init(allocator);
    defer current.deinit();

    const accuracy_key = try allocator.dupe(u8, "accuracy");
    try current.put(accuracy_key, 0.80); // 11% drop - should trigger

    var regressions = try detector.detect(current, allocator);
    defer {
        for (regressions.items) |regression| {
            regression.deinit();
        }
        regressions.deinit(allocator);
    }

    try std.testing.expectEqual(@as(usize, 1), regressions.items.len);

    const regression = regressions.items[0];
    try std.testing.expectEqualStrings("accuracy", regression.metric_name);
    try std.testing.expect(regression.severity == .moderate);

    allocator.free(accuracy_key);
}

test "RegressionDetector no regression when below threshold" {
    const allocator = std.testing.allocator;

    const config = RegressionConfig.default();
    const detector = try RegressionDetector.init(allocator, config);
    defer detector.deinit();

    try detector.setBaseline("accuracy", 0.90);

    var current = std.StringHashMap(f64).init(allocator);
    defer current.deinit();

    const accuracy_key = try allocator.dupe(u8, "accuracy");
    try current.put(accuracy_key, 0.89); // Only 1.1% drop - below 5% threshold

    var regressions = try detector.detect(current, allocator);
    defer regressions.deinit(allocator);

    try std.testing.expectEqual(@as(usize, 0), regressions.items.len);

    allocator.free(accuracy_key);
}

test "RegressionDetector check single metric" {
    const allocator = std.testing.allocator;

    const config = RegressionConfig.default();
    const detector = try RegressionDetector.init(allocator, config);
    defer detector.deinit();

    try detector.setBaseline("latency", 100.0);

    const regression = try detector.checkMetric(allocator, "latency", 120.0);
    if (regression) |r| {
        defer r.deinit();
        try std.testing.expectEqualStrings("latency", r.metric_name);
        try std.testing.expectEqual(@as(f64, 100.0), r.baseline_value);
        try std.testing.expectEqual(@as(f64, 120.0), r.current_value);
    }
}

test "RegressionDetector clear baselines" {
    const allocator = std.testing.allocator;

    const config = RegressionConfig.default();
    const detector = try RegressionDetector.init(allocator, config);
    defer detector.deinit();

    try detector.setBaseline("accuracy", 0.90);
    try detector.setBaseline("latency", 100.0);

    detector.clearBaselines();

    var summary = try detector.getBaselineSummary(allocator);
    defer summary.deinit();

    try std.testing.expectEqual(@as(usize, 0), summary.count());
}

/// A/B testing framework with statistical significance
///
/// This module provides infrastructure for comparing two agent versions
/// using statistical tests to determine if observed differences are significant.
///
/// Key design principles:
/// - Multiple statistical tests (t-test, Mann-Whitney, Chi-square, Bootstrap)
/// - Configurable significance levels
/// - Effect size calculation (Cohen's d)
/// - Confidence intervals
/// - Sample size calculation

const std = @import("std");
const core = @import("core.zig");
const Allocator = std.mem.Allocator;
const Agent = @import("../agent.zig").Agent;
const Message = @import("../message.zig").Message;

/// Statistical test type
pub const StatisticalTestType = enum {
    t_test, // Parametric test for normally distributed data
    mann_whitney, // Non-parametric test
    chi_square, // For categorical data
    bootstrap, // Resampling-based test

    pub fn toString(self: StatisticalTestType) []const u8 {
        return switch (self) {
            .t_test => "t-test",
            .mann_whitney => "Mann-Whitney U",
            .chi_square => "Chi-square",
            .bootstrap => "Bootstrap",
        };
    }
};

/// Significance level (alpha)
pub const SignificanceLevel = enum {
    p_0_001, // 99.9% confidence
    p_0_01, // 99% confidence
    p_0_05, // 95% confidence
    p_0_10, // 90% confidence

    pub fn alpha(self: SignificanceLevel) f64 {
        return switch (self) {
            .p_0_001 => 0.001,
            .p_0_01 => 0.01,
            .p_0_05 => 0.05,
            .p_0_10 => 0.10,
        };
    }
};

/// Variant statistics
pub const ABVariant = struct {
    name: []const u8,
    samples: std.ArrayList(f64),
    mean: f64,
    std_dev: f64,
    sample_size: usize,
    allocator: Allocator,

    pub fn init(allocator: Allocator, name: []const u8) !*ABVariant {
        const self = try allocator.create(ABVariant);
        self.* = ABVariant{
            .name = try allocator.dupe(u8, name),
            .samples = std.ArrayList(f64){},
            .mean = 0.0,
            .std_dev = 0.0,
            .sample_size = 0,
            .allocator = allocator,
        };
        return self;
    }

    pub fn addSample(self: *ABVariant, value: f64) !void {
        try self.samples.append(self.allocator, value);
        self.calculateStatistics();
    }

    fn calculateStatistics(self: *ABVariant) void {
        self.sample_size = self.samples.items.len;

        if (self.sample_size == 0) {
            self.mean = 0.0;
            self.std_dev = 0.0;
            return;
        }

        // Calculate mean
        var sum: f64 = 0.0;
        for (self.samples.items) |sample| {
            sum += sample;
        }
        self.mean = sum / @as(f64, @floatFromInt(self.sample_size));

        // Calculate standard deviation
        if (self.sample_size > 1) {
            var variance_sum: f64 = 0.0;
            for (self.samples.items) |sample| {
                const diff = sample - self.mean;
                variance_sum += diff * diff;
            }
            self.std_dev = @sqrt(variance_sum / @as(f64, @floatFromInt(self.sample_size - 1)));
        } else {
            self.std_dev = 0.0;
        }
    }

    pub fn deinit(self: *ABVariant) void {
        self.allocator.free(self.name);
        self.samples.deinit(self.allocator);
        self.allocator.destroy(self);
    }
};

/// A/B test result
pub const ABResult = struct {
    control: *ABVariant,
    treatment: *ABVariant,
    p_value: f64,
    effect_size: f64, // Cohen's d
    confidence_interval: struct { lower: f64, upper: f64 },
    is_significant: bool,
    winner: []const u8,
    test_type: StatisticalTestType,
    allocator: Allocator,

    pub fn summary(self: *const ABResult) ![]const u8 {
        return try std.fmt.allocPrint(
            self.allocator,
            "A/B Test Results ({s}):\n" ++
                "  Control:    mean={d:.4}, std={d:.4}, n={d}\n" ++
                "  Treatment:  mean={d:.4}, std={d:.4}, n={d}\n" ++
                "  P-value:    {d:.4}\n" ++
                "  Effect size: {d:.4}\n" ++
                "  CI 95%:     [{d:.4}, {d:.4}]\n" ++
                "  Significant: {}\n" ++
                "  Winner:     {s}",
            .{
                self.test_type.toString(),
                self.control.mean,
                self.control.std_dev,
                self.control.sample_size,
                self.treatment.mean,
                self.treatment.std_dev,
                self.treatment.sample_size,
                self.p_value,
                self.effect_size,
                self.confidence_interval.lower,
                self.confidence_interval.upper,
                self.is_significant,
                self.winner,
            },
        );
    }

    pub fn deinit(self: *ABResult) void {
        self.control.deinit();
        self.treatment.deinit();
        self.allocator.free(self.winner);
        self.allocator.destroy(self);
    }
};

/// A/B test framework
pub const ABTest = struct {
    test_type: StatisticalTestType,
    significance_level: SignificanceLevel,
    allocator: Allocator,

    pub fn init(
        allocator: Allocator,
        test_type: StatisticalTestType,
        significance_level: SignificanceLevel,
    ) !*ABTest {
        const self = try allocator.create(ABTest);
        self.* = ABTest{
            .test_type = test_type,
            .significance_level = significance_level,
            .allocator = allocator,
        };
        return self;
    }

    /// Run A/B test
    pub fn run(
        self: *ABTest,
        control_samples: []const f64,
        treatment_samples: []const f64,
    ) !*ABResult {
        // Create variants
        const control = try ABVariant.init(self.allocator, "control");
        for (control_samples) |sample| {
            try control.addSample(sample);
        }

        const treatment = try ABVariant.init(self.allocator, "treatment");
        for (treatment_samples) |sample| {
            try treatment.addSample(sample);
        }

        // Calculate p-value
        const p_value = switch (self.test_type) {
            .t_test => try self.tTest(control, treatment),
            .mann_whitney => try self.mannWhitney(control, treatment),
            .chi_square => try self.chiSquare(control, treatment),
            .bootstrap => try self.bootstrap(control, treatment),
        };

        // Calculate effect size (Cohen's d)
        const effect_size = self.cohensD(control, treatment);

        // Calculate confidence interval (simplified)
        const mean_diff = treatment.mean - control.mean;
        const pooled_std = @sqrt((control.std_dev * control.std_dev +
            treatment.std_dev * treatment.std_dev) / 2.0);
        const margin = 1.96 * pooled_std; // 95% CI

        // Determine significance and winner
        const is_significant = p_value < self.significance_level.alpha();
        const winner = if (!is_significant)
            try self.allocator.dupe(u8, "inconclusive")
        else if (treatment.mean > control.mean)
            try self.allocator.dupe(u8, "treatment")
        else
            try self.allocator.dupe(u8, "control");

        const result = try self.allocator.create(ABResult);
        result.* = ABResult{
            .control = control,
            .treatment = treatment,
            .p_value = p_value,
            .effect_size = effect_size,
            .confidence_interval = .{
                .lower = mean_diff - margin,
                .upper = mean_diff + margin,
            },
            .is_significant = is_significant,
            .winner = winner,
            .test_type = self.test_type,
            .allocator = self.allocator,
        };

        return result;
    }

    /// Welch's t-test (unequal variances)
    fn tTest(self: *ABTest, control: *ABVariant, treatment: *ABVariant) !f64 {
        _ = self;
        if (control.sample_size < 2 or treatment.sample_size < 2) {
            return 1.0; // Not enough samples
        }

        const mean_diff = treatment.mean - control.mean;
        const var1 = control.std_dev * control.std_dev;
        const var2 = treatment.std_dev * treatment.std_dev;
        const n1 = @as(f64, @floatFromInt(control.sample_size));
        const n2 = @as(f64, @floatFromInt(treatment.sample_size));

        const se = @sqrt(var1 / n1 + var2 / n2);
        if (se == 0.0) return 1.0;

        const t = mean_diff / se;

        // Approximate p-value using normal distribution
        const z = @abs(t);
        const p = 2.0 * (1.0 - normalCDF(z));

        return p;
    }

    /// Mann-Whitney U test (simplified)
    fn mannWhitney(self: *ABTest, control: *ABVariant, treatment: *ABVariant) !f64 {
        _ = self;
        _ = control;
        _ = treatment;
        // Simplified: return mean comparison as proxy
        return 0.05; // Placeholder
    }

    /// Chi-square test (simplified)
    fn chiSquare(self: *ABTest, control: *ABVariant, treatment: *ABVariant) !f64 {
        _ = self;
        _ = control;
        _ = treatment;
        // Simplified: for categorical data
        return 0.05; // Placeholder
    }

    /// Bootstrap resampling test
    fn bootstrap(self: *ABTest, control: *ABVariant, treatment: *ABVariant) !f64 {
        _ = self;
        const mean_diff = treatment.mean - control.mean;

        // Simplified bootstrap: use normal approximation
        const pooled_std = @sqrt((control.std_dev * control.std_dev +
            treatment.std_dev * treatment.std_dev) / 2.0);

        if (pooled_std == 0.0) return 1.0;

        const z = @abs(mean_diff) / pooled_std;
        return 2.0 * (1.0 - normalCDF(z));
    }

    /// Cohen's d effect size
    fn cohensD(self: *ABTest, control: *ABVariant, treatment: *ABVariant) f64 {
        _ = self;
        const mean_diff = treatment.mean - control.mean;
        const n1 = @as(f64, @floatFromInt(control.sample_size));
        const n2 = @as(f64, @floatFromInt(treatment.sample_size));

        const pooled_var = ((n1 - 1.0) * control.std_dev * control.std_dev +
            (n2 - 1.0) * treatment.std_dev * treatment.std_dev) / (n1 + n2 - 2.0);

        const pooled_std = @sqrt(pooled_var);

        if (pooled_std == 0.0) return 0.0;

        return mean_diff / pooled_std;
    }

    /// Calculate sample size needed
    pub fn calculateSampleSize(
        baseline_mean: f64,
        min_detectable_effect: f64,
        alpha: f64,
        power: f64,
        std_dev: f64,
    ) usize {
        _ = baseline_mean;
        _ = alpha; // Simplified calculation ignores these
        _ = power;
        // Simplified calculation (using fixed constants for now)
        const z_alpha = 1.96; // For alpha = 0.05
        const z_beta = 0.84; // For power = 0.80

        const effect_size = min_detectable_effect / std_dev;
        if (effect_size == 0.0) return 1000;

        const n = 2.0 * std.math.pow(f64, (z_alpha + z_beta) / effect_size, 2.0);
        return @intFromFloat(@max(10.0, n));
    }

    pub fn deinit(self: *ABTest) void {
        self.allocator.destroy(self);
    }
};

/// Normal CDF approximation
fn normalCDF(z: f64) f64 {
    // Approximation using error function
    const t = 1.0 / (1.0 + 0.2316419 * @abs(z));
    const d = 0.3989423 * @exp(-z * z / 2.0);
    const prob = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));

    return if (z >= 0.0) 1.0 - prob else prob;
}

// Tests
test "ABVariant statistics" {
    const allocator = std.testing.allocator;

    const variant = try ABVariant.init(allocator, "test");
    defer variant.deinit();

    try variant.addSample(1.0);
    try variant.addSample(2.0);
    try variant.addSample(3.0);

    try std.testing.expectEqual(@as(usize, 3), variant.sample_size);
    try std.testing.expectApproxEqAbs(@as(f64, 2.0), variant.mean, 0.01);
    try std.testing.expect(variant.std_dev > 0.0);
}

test "SignificanceLevel alpha values" {
    try std.testing.expectEqual(@as(f64, 0.001), SignificanceLevel.p_0_001.alpha());
    try std.testing.expectEqual(@as(f64, 0.05), SignificanceLevel.p_0_05.alpha());
}

test "ABTest t-test" {
    const allocator = std.testing.allocator;

    const ab_test = try ABTest.init(allocator, .t_test, .p_0_05);
    defer ab_test.deinit();

    const control_samples = [_]f64{ 0.80, 0.82, 0.81, 0.79, 0.83 };
    const treatment_samples = [_]f64{ 0.85, 0.87, 0.86, 0.84, 0.88 };

    var result = try ab_test.run(&control_samples, &treatment_samples);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 5), result.control.sample_size);
    try std.testing.expectEqual(@as(usize, 5), result.treatment.sample_size);
    try std.testing.expect(result.p_value >= 0.0 and result.p_value <= 1.0);
}

test "ABTest sample size calculation" {
    const n = ABTest.calculateSampleSize(0.75, 0.10, 0.05, 0.80, 0.12);
    try std.testing.expect(n > 0);
    try std.testing.expect(n < 10000);
}

test "normalCDF approximation" {
    const cdf_0 = normalCDF(0.0);
    try std.testing.expectApproxEqAbs(@as(f64, 0.5), cdf_0, 0.01);

    const cdf_2 = normalCDF(2.0);
    try std.testing.expectApproxEqAbs(@as(f64, 0.977), cdf_2, 0.01);
}

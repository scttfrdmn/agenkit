/// Bayesian optimization using Gaussian Process
///
/// This module provides Gaussian Process-based hyperparameter optimization
/// with various acquisition functions for exploration/exploitation balance.
///
/// Key design principles:
/// - Simplified GP (local statistics + similarity)
/// - Multiple acquisition functions (EI, UCB, PI)
/// - Exploration/exploitation balance
/// - Integration with SearchSpace
const std = @import("std");
const agktime = @import("../time_compat.zig");
const optimizer = @import("optimizer.zig");
const Allocator = std.mem.Allocator;
const SearchSpace = optimizer.SearchSpace;
const ConfigValue = optimizer.ConfigValue;
const OptimizationResult = optimizer.OptimizationResult;
const OptimizationStep = optimizer.OptimizationStep;

/// Acquisition function type
pub const AcquisitionFunction = enum {
    ei, // Expected Improvement
    ucb, // Upper Confidence Bound
    pi, // Probability of Improvement

    pub fn toString(self: AcquisitionFunction) []const u8 {
        return switch (self) {
            .ei => "Expected Improvement",
            .ucb => "Upper Confidence Bound",
            .pi => "Probability of Improvement",
        };
    }
};

/// Performance estimate (mean, uncertainty)
pub const PerformanceEstimate = struct {
    mean: f64,
    std_dev: f64,
};

/// Bayesian optimizer configuration
pub const BayesianConfig = struct {
    n_initial: usize, // Random samples before GP
    xi: f64, // Exploration parameter for EI/PI
    kappa: f64, // Exploration parameter for UCB
    acq_func: AcquisitionFunction,
    maximize: bool,
};

/// Bayesian optimizer using Gaussian Process
pub const BayesianOptimizer = struct {
    search_space: *SearchSpace,
    config: BayesianConfig,
    allocator: Allocator,

    pub fn init(
        allocator: Allocator,
        search_space: *SearchSpace,
        config: BayesianConfig,
    ) !*BayesianOptimizer {
        const self = try allocator.create(BayesianOptimizer);
        self.* = BayesianOptimizer{
            .search_space = search_space,
            .config = config,
            .allocator = allocator,
        };
        return self;
    }

    /// Objective function type
    pub const ObjectiveFn = *const fn (std.StringHashMap(ConfigValue)) anyerror!f64;

    /// Run Bayesian optimization
    pub fn optimize(
        self: *BayesianOptimizer,
        objective: ObjectiveFn,
        n_iterations: usize,
    ) !*OptimizationResult {
        const result = try OptimizationResult.init(self.allocator);
        result.n_iterations = n_iterations;

        // Phase 1: Random exploration
        const n_random = @min(self.config.n_initial, n_iterations);
        for (0..n_random) |_| {
            var config = try self.search_space.sample();
            const score = try objective(config);

            const is_better = if (self.config.maximize)
                score > result.best_score
            else
                score < result.best_score;

            if (is_better or result.history.items.len == 0) {
                try self.updateBestConfig(result, &config, score);
            }

            const step = OptimizationStep{
                .config = config,
                .score = score,
                .allocator = self.allocator,
            };
            try result.history.append(self.allocator, step);
        }

        // Phase 2: Bayesian optimization
        for (n_random..n_iterations) |_| {
            // Propose next configuration using acquisition function
            var config = try self.proposeLocation(result);

            // Evaluate objective
            const score = try objective(config);

            // Update best if improved
            const is_better = if (self.config.maximize)
                score > result.best_score
            else
                score < result.best_score;

            if (is_better) {
                try self.updateBestConfig(result, &config, score);
            }

            // Record in history
            const step = OptimizationStep{
                .config = config,
                .score = score,
                .allocator = self.allocator,
            };
            try result.history.append(self.allocator, step);
        }

        result.end_time = agktime.timestamp();
        return result;
    }

    /// Update best configuration
    fn updateBestConfig(
        self: *BayesianOptimizer,
        result: *OptimizationResult,
        config: *std.StringHashMap(ConfigValue),
        score: f64,
    ) !void {
        // Clear old best config
        var old_it = result.best_config.iterator();
        while (old_it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            entry.value_ptr.deinit(self.allocator);
        }
        result.best_config.clearAndFree();

        // Copy new best config
        var it = config.iterator();
        while (it.next()) |entry| {
            const key_copy = try self.allocator.dupe(u8, entry.key_ptr.*);
            const value_copy = switch (entry.value_ptr.*) {
                .float => |v| ConfigValue{ .float = v },
                .int => |v| ConfigValue{ .int = v },
                .string => |s| ConfigValue{ .string = try self.allocator.dupe(u8, s) },
            };
            try result.best_config.put(key_copy, value_copy);
        }

        result.best_score = score;
    }

    /// Propose next location using acquisition function
    fn proposeLocation(self: *BayesianOptimizer, result: *const OptimizationResult) !std.StringHashMap(ConfigValue) {
        const n_candidates = 100; // Sample candidates
        var best_acquisition: f64 = -std.math.inf(f64);
        var best_config_opt: ?std.StringHashMap(ConfigValue) = null;

        for (0..n_candidates) |_| {
            var candidate = try self.search_space.sample();

            // Estimate performance at candidate
            const estimate = try self.estimatePerformance(&candidate, result);

            // Calculate acquisition function value
            const acq_value = switch (self.config.acq_func) {
                .ei => self.expectedImprovement(estimate, result.best_score),
                .ucb => self.upperConfidenceBound(estimate),
                .pi => self.probabilityOfImprovement(estimate, result.best_score),
            };

            if (acq_value > best_acquisition) {
                if (best_config_opt) |*old_config| {
                    var it = old_config.iterator();
                    while (it.next()) |entry| {
                        self.allocator.free(entry.key_ptr.*);
                        entry.value_ptr.deinit(self.allocator);
                    }
                    old_config.deinit();
                }

                best_acquisition = acq_value;
                best_config_opt = candidate;
            } else {
                // Clean up candidate
                var it = candidate.iterator();
                while (it.next()) |entry| {
                    self.allocator.free(entry.key_ptr.*);
                    entry.value_ptr.deinit(self.allocator);
                }
                candidate.deinit();
            }
        }

        return best_config_opt orelse try self.search_space.sample();
    }

    /// Estimate performance using simplified Gaussian Process
    fn estimatePerformance(
        self: *BayesianOptimizer,
        config: *const std.StringHashMap(ConfigValue),
        result: *const OptimizationResult,
    ) !PerformanceEstimate {
        if (result.history.items.len == 0) {
            return PerformanceEstimate{
                .mean = 0.0,
                .std_dev = 1.0,
            };
        }

        // Simplified GP: weighted average based on similarity
        var weighted_sum: f64 = 0.0;
        var weight_sum: f64 = 0.0;
        var scores = std.ArrayList(f64).empty;
        defer scores.deinit(self.allocator);

        for (result.history.items) |step| {
            const similarity = self.calculateSimilarity(config, &step.config);
            const weight = @exp(-5.0 * (1.0 - similarity)); // RBF kernel

            weighted_sum += weight * step.score;
            weight_sum += weight;

            if (similarity > 0.5) {
                try scores.append(self.allocator, step.score);
            }
        }

        const mean = if (weight_sum > 0.0) weighted_sum / weight_sum else 0.0;

        // Estimate uncertainty
        var variance: f64 = 0.0;
        if (scores.items.len > 1) {
            var sum_sq_diff: f64 = 0.0;
            for (scores.items) |score| {
                const diff = score - mean;
                sum_sq_diff += diff * diff;
            }
            variance = sum_sq_diff / @as(f64, @floatFromInt(scores.items.len - 1));
        } else {
            variance = 1.0; // High uncertainty
        }

        return PerformanceEstimate{
            .mean = mean,
            .std_dev = @sqrt(variance),
        };
    }

    /// Calculate similarity between configurations (0.0 to 1.0)
    fn calculateSimilarity(
        self: *BayesianOptimizer,
        config1: *const std.StringHashMap(ConfigValue),
        config2: *const std.StringHashMap(ConfigValue),
    ) f64 {
        _ = self;
        var similarity_sum: f64 = 0.0;
        var param_count: usize = 0;

        var it = config1.iterator();
        while (it.next()) |entry1| {
            const key = entry1.key_ptr.*;
            const val1 = entry1.value_ptr.*;

            if (config2.get(key)) |val2| {
                param_count += 1;

                const param_similarity = switch (val1) {
                    .float => |f1| blk: {
                        if (val2 == .float) {
                            const f2 = val2.float;
                            const diff = @abs(f1 - f2);
                            break :blk 1.0 / (1.0 + diff);
                        }
                        break :blk 0.0;
                    },
                    .int => |int1| blk: {
                        if (val2 == .int) {
                            const int2 = val2.int;
                            const diff = @as(f64, @floatFromInt(@abs(int1 - int2)));
                            break :blk 1.0 / (1.0 + diff);
                        }
                        break :blk 0.0;
                    },
                    .string => |s1| blk: {
                        if (val2 == .string) {
                            const s2 = val2.string;
                            const match: f64 = if (std.mem.eql(u8, s1, s2)) 1.0 else 0.0;
                            break :blk match;
                        }
                        break :blk 0.0;
                    },
                };

                similarity_sum += param_similarity;
            }
        }

        return if (param_count > 0)
            similarity_sum / @as(f64, @floatFromInt(param_count))
        else
            0.0;
    }

    /// Expected Improvement acquisition function
    fn expectedImprovement(self: *BayesianOptimizer, estimate: PerformanceEstimate, best_score: f64) f64 {
        const mu = estimate.mean;
        const sigma = estimate.std_dev;

        if (sigma < 1e-10) return 0.0;

        const improvement = if (self.config.maximize)
            mu - best_score - self.config.xi
        else
            best_score - mu - self.config.xi;

        const z = improvement / sigma;
        const cdf = normalCDF(z);
        const pdf = normalPDF(z);

        return improvement * cdf + sigma * pdf;
    }

    /// Upper Confidence Bound acquisition function
    fn upperConfidenceBound(self: *BayesianOptimizer, estimate: PerformanceEstimate) f64 {
        const mu = estimate.mean;
        const sigma = estimate.std_dev;

        return if (self.config.maximize)
            mu + self.config.kappa * sigma
        else
            -(mu - self.config.kappa * sigma);
    }

    /// Probability of Improvement acquisition function
    fn probabilityOfImprovement(self: *BayesianOptimizer, estimate: PerformanceEstimate, best_score: f64) f64 {
        const mu = estimate.mean;
        const sigma = estimate.std_dev;

        if (sigma < 1e-10) return 0.0;

        const improvement = if (self.config.maximize)
            mu - best_score - self.config.xi
        else
            best_score - mu - self.config.xi;

        const z = improvement / sigma;
        return normalCDF(z);
    }

    pub fn deinit(self: *BayesianOptimizer) void {
        self.allocator.destroy(self);
    }
};

/// Normal CDF approximation
fn normalCDF(z: f64) f64 {
    const t = 1.0 / (1.0 + 0.2316419 * @abs(z));
    const d = 0.3989423 * @exp(-z * z / 2.0);
    const prob = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));

    return if (z >= 0.0) 1.0 - prob else prob;
}

/// Normal PDF
fn normalPDF(z: f64) f64 {
    return (1.0 / @sqrt(2.0 * std.math.pi)) * @exp(-z * z / 2.0);
}

// Tests
test "AcquisitionFunction toString" {
    try std.testing.expectEqualStrings("Expected Improvement", AcquisitionFunction.ei.toString());
    try std.testing.expectEqualStrings("Upper Confidence Bound", AcquisitionFunction.ucb.toString());
    try std.testing.expectEqualStrings("Probability of Improvement", AcquisitionFunction.pi.toString());
}

test "PerformanceEstimate basic" {
    const estimate = PerformanceEstimate{
        .mean = 0.85,
        .std_dev = 0.05,
    };

    try std.testing.expectEqual(@as(f64, 0.85), estimate.mean);
    try std.testing.expectEqual(@as(f64, 0.05), estimate.std_dev);
}

test "BayesianOptimizer initialization" {
    const allocator = std.testing.allocator;

    const space = try SearchSpace.init(allocator);
    defer space.deinit();

    try space.addContinuous("x", 0.0, 10.0);

    const config = BayesianConfig{
        .n_initial = 5,
        .xi = 0.01,
        .kappa = 2.576,
        .acq_func = .ei,
        .maximize = false,
    };

    const optimizer_inst = try BayesianOptimizer.init(allocator, space, config);
    defer optimizer_inst.deinit();

    try std.testing.expectEqual(@as(usize, 5), optimizer_inst.config.n_initial);
    try std.testing.expectEqual(AcquisitionFunction.ei, optimizer_inst.config.acq_func);
}

test "BayesianOptimizer optimize simple" {
    const allocator = std.testing.allocator;

    const space = try SearchSpace.init(allocator);
    defer space.deinit();

    try space.addContinuous("x", -10.0, 10.0);

    const config = BayesianConfig{
        .n_initial = 3,
        .xi = 0.01,
        .kappa = 2.576,
        .acq_func = .ei,
        .maximize = false,
    };

    const optimizer_inst = try BayesianOptimizer.init(allocator, space, config);
    defer optimizer_inst.deinit();

    // Objective: minimize (x - 5)^2
    const objective = struct {
        fn eval(cfg: std.StringHashMap(ConfigValue)) !f64 {
            const x = cfg.get("x").?.float;
            const diff = x - 5.0;
            return diff * diff;
        }
    }.eval;

    var result = try optimizer_inst.optimize(objective, 10);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 10), result.n_iterations);
    try std.testing.expect(result.best_score < 100.0); // Should find reasonable solution
}

test "BayesianOptimizer similarity calculation" {
    const allocator = std.testing.allocator;

    const space = try SearchSpace.init(allocator);
    defer space.deinit();

    const config = BayesianConfig{
        .n_initial = 5,
        .xi = 0.01,
        .kappa = 2.576,
        .acq_func = .ei,
        .maximize = true,
    };

    const optimizer_inst = try BayesianOptimizer.init(allocator, space, config);
    defer optimizer_inst.deinit();

    // Same configs
    var config1 = std.StringHashMap(ConfigValue).init(allocator);
    defer {
        var it = config1.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        config1.deinit();
    }
    try config1.put(try allocator.dupe(u8, "x"), ConfigValue{ .float = 5.0 });

    var config2 = std.StringHashMap(ConfigValue).init(allocator);
    defer {
        var it = config2.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        config2.deinit();
    }
    try config2.put(try allocator.dupe(u8, "x"), ConfigValue{ .float = 5.0 });

    const similarity = optimizer_inst.calculateSimilarity(&config1, &config2);
    try std.testing.expectEqual(@as(f64, 1.0), similarity);
}

test "BayesianOptimizer acquisition functions" {
    const allocator = std.testing.allocator;

    const space = try SearchSpace.init(allocator);
    defer space.deinit();

    const config_ei = BayesianConfig{
        .n_initial = 5,
        .xi = 0.01,
        .kappa = 2.576,
        .acq_func = .ei,
        .maximize = true,
    };

    const optimizer_ei = try BayesianOptimizer.init(allocator, space, config_ei);
    defer optimizer_ei.deinit();

    const estimate = PerformanceEstimate{
        .mean = 0.8,
        .std_dev = 0.1,
    };

    const ei = optimizer_ei.expectedImprovement(estimate, 0.7);
    try std.testing.expect(ei > 0.0);

    const ucb = optimizer_ei.upperConfidenceBound(estimate);
    try std.testing.expect(ucb > estimate.mean);

    const pi = optimizer_ei.probabilityOfImprovement(estimate, 0.7);
    try std.testing.expect(pi >= 0.0 and pi <= 1.0);
}

test "normalCDF approximation" {
    const cdf_0 = normalCDF(0.0);
    try std.testing.expectApproxEqAbs(@as(f64, 0.5), cdf_0, 0.01);

    const cdf_2 = normalCDF(2.0);
    try std.testing.expectApproxEqAbs(@as(f64, 0.977), cdf_2, 0.01);

    const cdf_neg = normalCDF(-1.0);
    try std.testing.expectApproxEqAbs(@as(f64, 0.159), cdf_neg, 0.01);
}

test "normalPDF approximation" {
    const pdf_0 = normalPDF(0.0);
    try std.testing.expectApproxEqAbs(@as(f64, 0.3989), pdf_0, 0.001);

    const pdf_1 = normalPDF(1.0);
    try std.testing.expectApproxEqAbs(@as(f64, 0.242), pdf_1, 0.01);
}

test "BayesianOptimizer estimatePerformance" {
    const allocator = std.testing.allocator;

    const space = try SearchSpace.init(allocator);
    defer space.deinit();

    try space.addContinuous("x", 0.0, 10.0);

    const config = BayesianConfig{
        .n_initial = 5,
        .xi = 0.01,
        .kappa = 2.576,
        .acq_func = .ei,
        .maximize = true,
    };

    const optimizer_inst = try BayesianOptimizer.init(allocator, space, config);
    defer optimizer_inst.deinit();

    const result = try OptimizationResult.init(allocator);
    defer result.deinit();

    // Add some history
    var hist_config1 = std.StringHashMap(ConfigValue).init(allocator);
    try hist_config1.put(try allocator.dupe(u8, "x"), ConfigValue{ .float = 5.0 });
    try result.history.append(allocator, OptimizationStep{
        .config = hist_config1,
        .score = 0.8,
        .allocator = allocator,
    });

    var hist_config2 = std.StringHashMap(ConfigValue).init(allocator);
    try hist_config2.put(try allocator.dupe(u8, "x"), ConfigValue{ .float = 5.5 });
    try result.history.append(allocator, OptimizationStep{
        .config = hist_config2,
        .score = 0.85,
        .allocator = allocator,
    });

    // Test estimate
    var test_config = std.StringHashMap(ConfigValue).init(allocator);
    defer {
        var it = test_config.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        test_config.deinit();
    }
    try test_config.put(try allocator.dupe(u8, "x"), ConfigValue{ .float = 5.2 });

    const estimate = try optimizer_inst.estimatePerformance(&test_config, result);
    try std.testing.expect(estimate.mean >= 0.0);
    try std.testing.expect(estimate.std_dev >= 0.0);
}

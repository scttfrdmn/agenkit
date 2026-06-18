//! Error tracking — per-step error rate and failure compounding.
//!
//! Long-running agents execute many steps; even a small per-step error rate
//! compounds into a high probability of at least one failure over a long run.
//! `ErrorTracker` records each step's outcome and exposes:
//!
//! - `p_a` (`perStepErrorRate`) — per-step error rate, failed/total.
//! - `P_error` (`cumulativeFailureProbability`) — probability of at least one
//!   failure across `n` independent steps, `1 - (1 - p_a)^n`. With `null`, `n`
//!   is the number of recorded steps (observed); pass a value to project the
//!   compounding over a planned run.
//!
//! Tracking is opt-in: a tracker with `enabled = false` (the default) treats
//! `recordStep` as a no-op and reports zero, so it is cheap to leave wired in.
//!
//! Mirrors the Python reference (agenkit/evaluation/error_tracker.py).

const std = @import("std");

/// Outcome of a single agent step.
///
/// `name`/`err` are borrowed slices: the caller owns their backing memory and
/// must keep it alive for the tracker's lifetime (the tracker does not dupe).
/// (`err` rather than `error`, which is a Zig keyword.)
pub const StepResult = struct {
    success: bool,
    name: ?[]const u8 = null,
    err: ?[]const u8 = null,
};

/// Records step outcomes and computes error-rate / compounding metrics.
pub const ErrorTracker = struct {
    enabled: bool,
    step_results: std.ArrayList(StepResult),
    allocator: std.mem.Allocator,

    /// Initialize a tracker. `enabled = false` makes `recordStep` a no-op.
    pub fn init(allocator: std.mem.Allocator, enabled: bool) ErrorTracker {
        return .{
            .enabled = enabled,
            .step_results = std.ArrayList(StepResult).empty,
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *ErrorTracker) void {
        self.step_results.deinit(self.allocator);
    }

    /// Record one step's outcome. No-op when disabled. Returns an error only if
    /// the backing append allocation fails.
    pub fn recordStep(
        self: *ErrorTracker,
        success: bool,
        name: ?[]const u8,
        err: ?[]const u8,
    ) !void {
        if (!self.enabled) return;
        try self.step_results.append(self.allocator, .{
            .success = success,
            .name = name,
            .err = err,
        });
    }

    /// Number of recorded steps.
    pub fn totalSteps(self: *const ErrorTracker) usize {
        return self.step_results.items.len;
    }

    /// Number of recorded steps that failed.
    pub fn failedSteps(self: *const ErrorTracker) usize {
        var count: usize = 0;
        for (self.step_results.items) |r| {
            if (!r.success) count += 1;
        }
        return count;
    }

    /// Per-step error rate `p_a` = failed/total. 0.0 when no steps recorded.
    pub fn perStepErrorRate(self: *const ErrorTracker) f64 {
        const total = self.totalSteps();
        if (total == 0) return 0.0;
        return @as(f64, @floatFromInt(self.failedSteps())) / @as(f64, @floatFromInt(total));
    }

    /// Probability of at least one failure over `steps` steps:
    /// `P_error = 1 - (1 - p_a)^n`, where `n` is `steps` if given, otherwise the
    /// number of recorded steps. Returns 0.0 if `p_a` is 0 or `n == 0`.
    pub fn cumulativeFailureProbability(self: *const ErrorTracker, steps: ?usize) f64 {
        const n = steps orelse self.totalSteps();
        if (n == 0) return 0.0;
        const p_a = self.perStepErrorRate();
        if (p_a == 0.0) return 0.0;
        return 1.0 - std.math.pow(f64, 1.0 - p_a, @floatFromInt(n));
    }

    /// Clear all recorded step results.
    pub fn reset(self: *ErrorTracker) void {
        self.step_results.clearRetainingCapacity();
    }
};

// ---------------------------------------------------------------------------
// Tests (ported from tests/evaluation/test_error_tracker.py)
// ---------------------------------------------------------------------------

const testing = std.testing;

test "StepResult defaults" {
    const r = StepResult{ .success = true };
    try testing.expect(r.success);
    try testing.expect(r.name == null);
    try testing.expect(r.err == null);
}

test "disabled by default records nothing" {
    var t = ErrorTracker.init(testing.allocator, false);
    defer t.deinit();
    try testing.expect(!t.enabled);
    try t.recordStep(false, null, "boom");
    try testing.expectEqual(@as(usize, 0), t.totalSteps());
    try testing.expectEqual(@as(usize, 0), t.failedSteps());
    try testing.expectEqual(@as(f64, 0.0), t.perStepErrorRate());
    try testing.expectEqual(@as(f64, 0.0), t.cumulativeFailureProbability(null));
}

test "enabled records steps" {
    var t = ErrorTracker.init(testing.allocator, true);
    defer t.deinit();
    try t.recordStep(true, null, null);
    try t.recordStep(false, null, "x");
    try testing.expectEqual(@as(usize, 2), t.totalSteps());
    try testing.expectEqual(@as(usize, 1), t.failedSteps());
}

test "per_step_error_rate empty/all-pass/all-fail/mixed" {
    var empty = ErrorTracker.init(testing.allocator, true);
    defer empty.deinit();
    try testing.expectEqual(@as(f64, 0.0), empty.perStepErrorRate());

    var pass = ErrorTracker.init(testing.allocator, true);
    defer pass.deinit();
    for (0..5) |_| try pass.recordStep(true, null, null);
    try testing.expectEqual(@as(f64, 0.0), pass.perStepErrorRate());

    var fail = ErrorTracker.init(testing.allocator, true);
    defer fail.deinit();
    for (0..4) |_| try fail.recordStep(false, null, null);
    try testing.expectEqual(@as(f64, 1.0), fail.perStepErrorRate());

    var mixed = ErrorTracker.init(testing.allocator, true);
    defer mixed.deinit();
    const outcomes = [_]bool{ true, false, true, true, false, true, true, true };
    for (outcomes) |ok| try mixed.recordStep(ok, null, null);
    try testing.expectApproxEqAbs(@as(f64, 0.25), mixed.perStepErrorRate(), 1e-9);
}

test "cumulative observed uses recorded step count" {
    var t = ErrorTracker.init(testing.allocator, true);
    defer t.deinit();
    try t.recordStep(true, null, null);
    try t.recordStep(false, null, null);
    // p_a = 0.5, n = 2 -> 1 - 0.5^2 = 0.75
    try testing.expectApproxEqAbs(@as(f64, 0.75), t.cumulativeFailureProbability(null), 1e-9);
}

test "cumulative projected steps" {
    var t = ErrorTracker.init(testing.allocator, true);
    defer t.deinit();
    try t.recordStep(true, null, null);
    try t.recordStep(false, null, null);
    const expected = 1.0 - std.math.pow(f64, 0.5, 10);
    try testing.expectApproxEqAbs(expected, t.cumulativeFailureProbability(10), 1e-9);
}

test "cumulative compounding small rate (1% over 100 ~= 0.634)" {
    var t = ErrorTracker.init(testing.allocator, true);
    defer t.deinit();
    try t.recordStep(false, null, null);
    for (0..99) |_| try t.recordStep(true, null, null);
    try testing.expectApproxEqAbs(@as(f64, 0.01), t.perStepErrorRate(), 1e-9);
    const p_error = t.cumulativeFailureProbability(100);
    try testing.expect(p_error > 0.63 and p_error < 0.64);
}

test "cumulative zero rate is zero / full rate is one / non-positive n" {
    var zero = ErrorTracker.init(testing.allocator, true);
    defer zero.deinit();
    for (0..10) |_| try zero.recordStep(true, null, null);
    try testing.expectEqual(@as(f64, 0.0), zero.cumulativeFailureProbability(1000));

    var full = ErrorTracker.init(testing.allocator, true);
    defer full.deinit();
    try full.recordStep(false, null, null);
    try testing.expectApproxEqAbs(@as(f64, 1.0), full.cumulativeFailureProbability(5), 1e-9);
    // n == 0 -> 0.0
    try testing.expectEqual(@as(f64, 0.0), full.cumulativeFailureProbability(0));
}

test "cumulative stays in [0,1]" {
    var t = ErrorTracker.init(testing.allocator, true);
    defer t.deinit();
    const outcomes = [_]bool{ true, false, true, false, false };
    for (outcomes) |ok| try t.recordStep(ok, null, null);
    var n: usize = 1;
    while (n < 50) : (n += 1) {
        const p = t.cumulativeFailureProbability(n);
        try testing.expect(p >= 0.0 and p <= 1.0);
    }
}

test "reset clears steps" {
    var t = ErrorTracker.init(testing.allocator, true);
    defer t.deinit();
    try t.recordStep(true, null, null);
    try t.recordStep(false, null, null);
    t.reset();
    try testing.expectEqual(@as(usize, 0), t.totalSteps());
    try testing.expectEqual(@as(f64, 0.0), t.perStepErrorRate());
}

test "docstring example values" {
    var t = ErrorTracker.init(testing.allocator, true);
    defer t.deinit();
    try t.recordStep(true, null, null);
    try t.recordStep(false, null, "timeout");
    try testing.expectEqual(@as(f64, 0.5), t.perStepErrorRate());
    // 1 - 0.5^10 rounds to 0.999
    try testing.expectApproxEqAbs(@as(f64, 0.999), t.cumulativeFailureProbability(10), 1e-3);
}

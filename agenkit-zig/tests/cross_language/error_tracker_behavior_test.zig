/// Cross-language error tracker behavior tests for Zig
///
/// Validates that Agenkit's Zig ErrorTracker (p_a / P_error) behaves
/// consistently with the cross-language error tracker behavior specification
/// (#652, follow-up to #321).

const std = @import("std");
const json = std.json;
const testing = std.testing;
const agenkit = @import("agenkit");
const ErrorTracker = agenkit.evaluation.ErrorTracker;

/// Load fixtures from JSON file.
fn loadFixtures(allocator: std.mem.Allocator) !json.Parsed(json.Value) {
    const fixtures_path = "../tests/cross_language/fixtures/error_tracker_behavior.json";
    const content = try std.Io.Dir.cwd().readFileAlloc(agenkit.io_compat.io(), fixtures_path, allocator, .limited(1024 * 1024));
    defer allocator.free(content);

    return try json.parseFromSlice(json.Value, allocator, content, .{});
}

/// Helper to get number from JSON value (handles both integer and float).
fn getJsonNumber(value: json.Value) f64 {
    return switch (value) {
        .integer => |i| @floatFromInt(i),
        .float => |f| f,
        else => 0.0,
    };
}

/// Build the step outcome sequence from a test case's `steps` or `steps_spec`.
fn buildSteps(allocator: std.mem.Allocator, test_case: json.Value) !std.ArrayList(bool) {
    var steps = try std.ArrayList(bool).initCapacity(allocator, 8);
    if (test_case.object.get("steps")) |steps_value| {
        for (steps_value.array.items) |item| {
            try steps.append(allocator, item.bool);
        }
        return steps;
    }
    const spec = test_case.object.get("steps_spec").?.object;
    const fail: usize = @intFromFloat(getJsonNumber(spec.get("fail").?));
    const success: usize = @intFromFloat(getJsonNumber(spec.get("success").?));
    for (0..fail) |_| try steps.append(allocator, false);
    for (0..success) |_| try steps.append(allocator, true);
    return steps;
}

test "error_tracker_behavior matches shared fixture for every test case" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    const test_cases = fixtures.value.object.get("test_cases").?.array;
    try testing.expect(test_cases.items.len > 0);

    for (test_cases.items) |test_case| {
        const id = test_case.object.get("id").?.string;
        const expected = test_case.object.get("expected").?.object;
        const tolerance: f64 = if (expected.get("tolerance")) |t| getJsonNumber(t) else 1e-6;

        var tracker = ErrorTracker.init(allocator, true);
        defer tracker.deinit();

        var steps = try buildSteps(allocator, test_case);
        defer steps.deinit(allocator);
        for (steps.items) |success| {
            try tracker.recordStep(success, null, null);
        }

        const expected_total: usize = @intFromFloat(getJsonNumber(expected.get("total_steps").?));
        const expected_failed: usize = @intFromFloat(getJsonNumber(expected.get("failed_steps").?));
        try testing.expectEqual(expected_total, tracker.totalSteps());
        try testing.expectEqual(expected_failed, tracker.failedSteps());

        const expected_rate = getJsonNumber(expected.get("per_step_error_rate").?);
        errdefer std.debug.print("[{s}] per_step_error_rate mismatch\n", .{id});
        try testing.expectApproxEqAbs(expected_rate, tracker.perStepErrorRate(), tolerance);

        if (expected.get("cumulative_failure_probability_observed")) |observed_value| {
            const expected_observed = getJsonNumber(observed_value);
            try testing.expectApproxEqAbs(expected_observed, tracker.cumulativeFailureProbability(null), tolerance);
        }

        const steps_map = expected.get("cumulative_failure_probability_steps").?.object;
        var it = steps_map.iterator();
        while (it.next()) |entry| {
            const n = try std.fmt.parseInt(usize, entry.key_ptr.*, 10);
            const expected_p = getJsonNumber(entry.value_ptr.*);
            const got = tracker.cumulativeFailureProbability(n);
            try testing.expectApproxEqAbs(expected_p, got, tolerance);
        }
    }
}

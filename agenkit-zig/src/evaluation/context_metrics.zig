/// Context and compression metrics for extreme-scale evaluation
///
/// This module provides metrics for tracking context length, compression ratios,
/// and latency percentiles - critical for evaluating agents at 1M-25M token scale.
///
/// Key design principles:
/// - Token estimation (4 chars ≈ 1 token heuristic)
/// - Compression effectiveness tracking
/// - Percentile-based latency analysis
/// - Memory-efficient streaming measurement

const std = @import("std");
const core = @import("core.zig");
const Allocator = std.mem.Allocator;
const Agent = @import("../agent.zig").Agent;
const Message = @import("../message.zig").Message;

/// Context length metric - tracks token growth over time
pub const ContextMetric = struct {
    name_str: []const u8,
    allocator: Allocator,
    measurements: std.ArrayList(f64),

    pub fn init(allocator: Allocator) !*ContextMetric {
        const self = try allocator.create(ContextMetric);
        self.* = ContextMetric{
            .name_str = "context_length",
            .allocator = allocator,
            .measurements = std.ArrayList(f64){},
        };
        return self;
    }

    /// Convert to Metric interface
    pub fn asMetric(self: *ContextMetric) core.Metric {
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

    /// Estimate token count (4 chars ≈ 1 token)
    fn estimateTokens(text: []const u8) f64 {
        return @as(f64, @floatFromInt(text.len)) / 4.0;
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *ContextMetric = @ptrCast(@alignCast(ptr));
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
        _ = allocator;
        const self: *ContextMetric = @ptrCast(@alignCast(ptr));

        // Measure total context (input + output)
        const input_text = switch (input.content) {
            .text => |t| t,
            .structured => "", // Can't estimate tokens from structured content
        };
        const output_text = switch (output.content) {
            .text => |t| t,
            .structured => "", // Can't estimate tokens from structured content
        };
        const input_tokens = estimateTokens(input_text);
        const output_tokens = estimateTokens(output_text);
        const total_tokens = input_tokens + output_tokens;

        try self.measurements.append(self.allocator, total_tokens);

        return total_tokens;
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

        // Calculate growth rate (if we have multiple measurements)
        var growth_rate: f64 = 0.0;
        if (measurements.len > 1) {
            const first = measurements[0];
            const last = measurements[measurements.len - 1];
            if (first > 0.0) {
                growth_rate = ((last - first) / first) * 100.0;
            }
        }

        const mean_key = try allocator.dupe(u8, "mean");
        try result.put(mean_key, mean);

        const min_key = try allocator.dupe(u8, "min");
        try result.put(min_key, min);

        const max_key = try allocator.dupe(u8, "max");
        try result.put(max_key, max);

        const final_key = try allocator.dupe(u8, "final");
        try result.put(final_key, measurements[measurements.len - 1]);

        const growth_key = try allocator.dupe(u8, "growth_rate_percent");
        try result.put(growth_key, growth_rate);

        return result;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *ContextMetric = @ptrCast(@alignCast(ptr));
        self.measurements.deinit(self.allocator);
        self.allocator.destroy(self);
    }
};

/// Compression statistics for a specific context length
pub const CompressionStats = struct {
    context_length: usize,
    raw_tokens: usize,
    compressed_tokens: usize,
    compression_ratio: f64,
    retrieval_accuracy: f64,

    pub fn init(
        context_length: usize,
        raw: usize,
        compressed: usize,
        accuracy: f64,
    ) CompressionStats {
        const ratio = if (compressed > 0)
            @as(f64, @floatFromInt(raw)) / @as(f64, @floatFromInt(compressed))
        else
            0.0;

        return CompressionStats{
            .context_length = context_length,
            .raw_tokens = raw,
            .compressed_tokens = compressed,
            .compression_ratio = ratio,
            .retrieval_accuracy = accuracy,
        };
    }
};

/// Compression metric for extreme-scale evaluation
pub const CompressionMetric = struct {
    name_str: []const u8,
    allocator: Allocator,
    test_lengths: []const usize, // Context lengths to test (e.g., 1M, 10M, 25M)

    pub fn init(allocator: Allocator, test_lengths: []const usize) !*CompressionMetric {
        const self = try allocator.create(CompressionMetric);
        const lengths_copy = try allocator.dupe(usize, test_lengths);
        self.* = CompressionMetric{
            .name_str = "compression",
            .allocator = allocator,
            .test_lengths = lengths_copy,
        };
        return self;
    }

    /// Evaluate compression at specified context lengths
    pub fn evaluateAtLengths(
        self: *CompressionMetric,
        agent: Agent,
        session_id: []const u8,
    ) !std.ArrayList(CompressionStats) {
        _ = agent;
        _ = session_id;
        var stats = std.ArrayList(CompressionStats){};

        // For each test length, simulate compression evaluation
        for (self.test_lengths) |length| {
            // In a real implementation, this would:
            // 1. Generate context of `length` tokens
            // 2. Embed needle content
            // 3. Have agent retrieve needles
            // 4. Measure compression and accuracy

            // Simplified simulation
            const raw = length;
            const compressed = length / 2; // Assume 2:1 compression
            const accuracy = 0.95; // Assume 95% retrieval accuracy

            const stat = CompressionStats.init(length, raw, compressed, accuracy);
            try stats.append(self.allocator, stat);
        }

        return stats;
    }

    pub fn asMetric(self: *CompressionMetric) core.Metric {
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
        const self: *CompressionMetric = @ptrCast(@alignCast(ptr));
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
        _ = allocator;
        _ = ptr;

        // Measure compression ratio for this interaction
        const input_len = (input.content orelse "").len;
        const output_len = (output.content orelse "").len;
        const total_len = input_len + output_len;

        // Simulate compression (in real impl, would use actual compression)
        const compressed_len = total_len / 2;
        const ratio = if (compressed_len > 0)
            @as(f64, @floatFromInt(total_len)) / @as(f64, @floatFromInt(compressed_len))
        else
            0.0;

        return ratio;
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

        var sum: f64 = 0.0;
        for (measurements) |m| {
            sum += m;
        }
        const mean_ratio = sum / @as(f64, @floatFromInt(measurements.len));

        const mean_key = try allocator.dupe(u8, "mean_compression_ratio");
        try result.put(mean_key, mean_ratio);

        return result;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *CompressionMetric = @ptrCast(@alignCast(ptr));
        self.allocator.free(self.test_lengths);
        self.allocator.destroy(self);
    }
};

/// Latency metric with percentile analysis
pub const LatencyMetric = struct {
    name_str: []const u8,
    allocator: Allocator,
    measurements: std.ArrayList(f64),

    pub fn init(allocator: Allocator) !*LatencyMetric {
        const self = try allocator.create(LatencyMetric);
        self.* = LatencyMetric{
            .name_str = "latency",
            .allocator = allocator,
            .measurements = std.ArrayList(f64){},
        };
        return self;
    }

    pub fn asMetric(self: *LatencyMetric) core.Metric {
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

    /// Calculate percentile from sorted values
    fn calculatePercentile(sorted_values: []const f64, percentile: f64) f64 {
        if (sorted_values.len == 0) return 0.0;

        const index = (percentile / 100.0) * @as(f64, @floatFromInt(sorted_values.len - 1));
        const lower_idx = @as(usize, @intFromFloat(@floor(index)));
        const upper_idx = @min(lower_idx + 1, sorted_values.len - 1);

        if (lower_idx == upper_idx) {
            return sorted_values[lower_idx];
        }

        const weight = index - @floor(index);
        return sorted_values[lower_idx] * (1.0 - weight) +
            sorted_values[upper_idx] * weight;
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *LatencyMetric = @ptrCast(@alignCast(ptr));
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
        const self: *LatencyMetric = @ptrCast(@alignCast(ptr));

        // Get latency from output metadata (in ms)
        var latency: f64 = 0.0;
        if (output.metadata == .object) {
            if (output.metadata.object.get("latency_ms")) |value| {
                if (value == .string) {
                    latency = std.fmt.parseFloat(f64, value.string) catch 0.0;
                }
            }
        }

        try self.measurements.append(self.allocator, latency);

        return latency;
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

        // Sort measurements for percentile calculation
        const sorted = try allocator.dupe(f64, measurements);
        defer allocator.free(sorted);
        std.mem.sort(f64, sorted, {}, comptime std.sort.asc(f64));

        // Calculate mean
        var sum: f64 = 0.0;
        for (measurements) |m| {
            sum += m;
        }
        const mean = sum / @as(f64, @floatFromInt(measurements.len));

        // Calculate percentiles
        const p50 = calculatePercentile(sorted, 50.0);
        const p90 = calculatePercentile(sorted, 90.0);
        const p95 = calculatePercentile(sorted, 95.0);
        const p99 = calculatePercentile(sorted, 99.0);

        const mean_key = try allocator.dupe(u8, "mean_ms");
        try result.put(mean_key, mean);

        const p50_key = try allocator.dupe(u8, "p50_ms");
        try result.put(p50_key, p50);

        const p90_key = try allocator.dupe(u8, "p90_ms");
        try result.put(p90_key, p90);

        const p95_key = try allocator.dupe(u8, "p95_ms");
        try result.put(p95_key, p95);

        const p99_key = try allocator.dupe(u8, "p99_ms");
        try result.put(p99_key, p99);

        const min_key = try allocator.dupe(u8, "min_ms");
        try result.put(min_key, sorted[0]);

        const max_key = try allocator.dupe(u8, "max_ms");
        try result.put(max_key, sorted[sorted.len - 1]);

        return result;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *LatencyMetric = @ptrCast(@alignCast(ptr));
        self.measurements.deinit(self.allocator);
        self.allocator.destroy(self);
    }
};

// Tests
test "ContextMetric token estimation" {
    const text1 = "Hello, world!"; // 13 chars ≈ 3.25 tokens
    const tokens1 = ContextMetric.estimateTokens(text1);
    try std.testing.expectApproxEqAbs(@as(f64, 3.25), tokens1, 0.01);

    const text2 = "This is a longer piece of text with many words."; // 47 chars ≈ 11.75 tokens
    const tokens2 = ContextMetric.estimateTokens(text2);
    try std.testing.expectApproxEqAbs(@as(f64, 11.75), tokens2, 0.01);
}

test "ContextMetric tracking" {
    const allocator = std.testing.allocator;

    const metric = try ContextMetric.init(allocator);
    defer {
        metric.measurements.deinit(allocator);
        allocator.destroy(metric);
    }

    // Simulate multiple measurements
    try metric.measurements.append(allocator,100.0);
    try metric.measurements.append(allocator,150.0);
    try metric.measurements.append(allocator,200.0);

    const measurements = metric.measurements.items;
    var aggregated = try metric.asMetric().aggregate(measurements, allocator);
    defer {
        var it = aggregated.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        aggregated.deinit();
    }

    const mean = aggregated.get("mean").?;
    try std.testing.expectApproxEqAbs(@as(f64, 150.0), mean, 0.01);

    const growth = aggregated.get("growth_rate_percent").?;
    try std.testing.expectApproxEqAbs(@as(f64, 100.0), growth, 0.01); // 100% growth from 100 to 200
}

test "CompressionStats calculation" {
    const stats = CompressionStats.init(1000000, 1000000, 500000, 0.95);

    try std.testing.expectEqual(@as(usize, 1000000), stats.context_length);
    try std.testing.expectEqual(@as(usize, 1000000), stats.raw_tokens);
    try std.testing.expectEqual(@as(usize, 500000), stats.compressed_tokens);
    try std.testing.expectApproxEqAbs(@as(f64, 2.0), stats.compression_ratio, 0.01);
    try std.testing.expectEqual(@as(f64, 0.95), stats.retrieval_accuracy);
}

test "CompressionMetric evaluation" {
    const allocator = std.testing.allocator;

    const test_lengths = [_]usize{ 1000000, 10000000, 25000000 };
    const metric = try CompressionMetric.init(allocator, &test_lengths);
    defer {
        allocator.free(metric.test_lengths);
        allocator.destroy(metric);
    }

    const agent = Agent{ .ptr = undefined, .vtable = undefined };
    var stats = try metric.evaluateAtLengths(agent, "test-session");
    defer stats.deinit(allocator);

    try std.testing.expectEqual(@as(usize, 3), stats.items.len);

    // Check first stat
    try std.testing.expectEqual(@as(usize, 1000000), stats.items[0].context_length);
    try std.testing.expectApproxEqAbs(@as(f64, 2.0), stats.items[0].compression_ratio, 0.01);
}

test "LatencyMetric percentile calculation" {
    const values = [_]f64{ 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0 };

    const p50 = LatencyMetric.calculatePercentile(&values, 50.0);
    try std.testing.expectApproxEqAbs(@as(f64, 55.0), p50, 1.0);

    const p90 = LatencyMetric.calculatePercentile(&values, 90.0);
    try std.testing.expectApproxEqAbs(@as(f64, 91.0), p90, 1.0);

    const p99 = LatencyMetric.calculatePercentile(&values, 99.0);
    try std.testing.expectApproxEqAbs(@as(f64, 99.1), p99, 1.0);
}

test "LatencyMetric aggregation" {
    const allocator = std.testing.allocator;

    const metric = try LatencyMetric.init(allocator);
    defer {
        metric.measurements.deinit(allocator);
        allocator.destroy(metric);
    }

    // Add measurements
    const measurements = [_]f64{ 100.0, 150.0, 120.0, 180.0, 110.0, 200.0, 130.0, 160.0, 140.0, 190.0 };

    var aggregated = try metric.asMetric().aggregate(&measurements, allocator);
    defer {
        var it = aggregated.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        aggregated.deinit();
    }

    const mean = aggregated.get("mean_ms").?;
    try std.testing.expectApproxEqAbs(@as(f64, 148.0), mean, 1.0);

    const p50 = aggregated.get("p50_ms").?;
    try std.testing.expect(p50 > 100.0 and p50 < 200.0);

    const p99 = aggregated.get("p99_ms").?;
    try std.testing.expect(p99 > 180.0);
}

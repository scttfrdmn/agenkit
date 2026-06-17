/// Anomaly Detection for Agent Behavior Monitoring
///
/// Detects suspicious patterns in agent behavior such as:
/// - High request rates
/// - Burst activity
/// - Repeated failures
/// - Unusual input/output sizes
const std = @import("std");
const agktime = @import("../time_compat.zig");
const mem = std.mem;
const Allocator = std.mem.Allocator;
const ArrayList = std.ArrayList;
const StringHashMap = std.StringHashMap;
const AutoHashMap = std.AutoHashMap;

/// Security event types
pub const SecurityEvent = enum {
    high_request_rate,
    burst_detected,
    repeated_failures,
    permission_denied_spike,
    validation_failures,
    unusual_input_size,
    unusual_output_size,
    unusual_processing_time,
    suspicious_content_pattern,
    repetitive_content,
};

/// Anomaly Detector tracks patterns and identifies suspicious behavior
pub const AnomalyDetector = struct {
    max_requests_per_minute: i32,
    max_burst_size: i32,
    failure_rate_threshold: f64,
    input_size_threshold: f64,
    output_size_threshold: f64,
    processing_time_threshold: f64,
    max_stats_size: usize,
    max_content_history: usize,
    request_timestamps: StringHashMap(ArrayList(f64)),
    failure_counts: StringHashMap(i32),
    request_counts: StringHashMap(i32),
    input_sizes: ArrayList(f64),
    output_sizes: ArrayList(f64),
    processing_times: ArrayList(f64),
    recent_content: ArrayList([]const u8),
    allocator: Allocator,

    pub const Config = struct {
        max_requests_per_minute: i32 = 60,
        max_burst_size: i32 = 10,
        failure_rate_threshold: f64 = 0.5,
        input_size_threshold: f64 = 3.0,
        output_size_threshold: f64 = 3.0,
        processing_time_threshold: f64 = 30.0,
        max_stats_size: usize = 100,
        max_content_history: usize = 10,
    };

    pub fn init(allocator: Allocator, config: Config) !AnomalyDetector {
        return AnomalyDetector{
            .max_requests_per_minute = config.max_requests_per_minute,
            .max_burst_size = config.max_burst_size,
            .failure_rate_threshold = config.failure_rate_threshold,
            .input_size_threshold = config.input_size_threshold,
            .output_size_threshold = config.output_size_threshold,
            .processing_time_threshold = config.processing_time_threshold,
            .max_stats_size = config.max_stats_size,
            .max_content_history = config.max_content_history,
            .request_timestamps = StringHashMap(ArrayList(f64)).init(allocator),
            .failure_counts = StringHashMap(i32).init(allocator),
            .request_counts = StringHashMap(i32).init(allocator),
            .input_sizes = std.ArrayList(f64).empty,
            .output_sizes = std.ArrayList(f64).empty,
            .processing_times = std.ArrayList(f64).empty,
            .recent_content = std.ArrayList([]const u8).empty,
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *AnomalyDetector) void {
        var timestamp_iter = self.request_timestamps.valueIterator();
        while (timestamp_iter.next()) |timestamps| {
            timestamps.deinit(self.allocator);
        }
        self.request_timestamps.deinit();
        self.failure_counts.deinit();
        self.request_counts.deinit();
        self.input_sizes.deinit(self.allocator);
        self.output_sizes.deinit(self.allocator);
        self.processing_times.deinit(self.allocator);
        self.recent_content.deinit(self.allocator);
    }

    pub const AnomalyResult = struct {
        event: SecurityEvent,
        details: []const u8,
    };

    pub fn detectRateAnomaly(self: *AnomalyDetector, user_id: []const u8) !?AnomalyResult {
        const now = @as(f64, @floatFromInt(agktime.timestamp()));

        // Get or create timestamp list for this user
        const result = try self.request_timestamps.getOrPut(user_id);
        if (!result.found_existing) {
            result.value_ptr.* = std.ArrayList(f64).empty;
        }

        var timestamps = result.value_ptr;
        try timestamps.append(self.allocator, now);

        // Clean old timestamps (> 60 seconds)
        var i: usize = 0;
        while (i < timestamps.items.len) {
            if (now - timestamps.items[i] > 60.0) {
                _ = timestamps.orderedRemove(i);
            } else {
                i += 1;
            }
        }

        // Check request rate
        const requests_per_minute = @as(i32, @intCast(timestamps.items.len));
        if (requests_per_minute > self.max_requests_per_minute) {
            return AnomalyResult{
                .event = .high_request_rate,
                .details = "Request rate exceeds threshold",
            };
        }

        return null;
    }

    pub fn detectBurstAnomaly(self: *AnomalyDetector, user_id: []const u8) !?AnomalyResult {
        const now = @as(f64, @floatFromInt(agktime.timestamp()));

        const result = try self.request_timestamps.getOrPut(user_id);
        if (!result.found_existing) {
            result.value_ptr.* = std.ArrayList(f64).empty;
        }

        const timestamps = result.value_ptr;

        // Check for burst (many requests in short time window - 10 seconds)
        var recent_count: i32 = 0;
        for (timestamps.items) |ts| {
            if (now - ts <= 10.0) {
                recent_count += 1;
            }
        }

        if (recent_count > self.max_burst_size) {
            return AnomalyResult{
                .event = .burst_detected,
                .details = "Request burst detected",
            };
        }

        return null;
    }

    pub fn detectFailureAnomaly(self: *AnomalyDetector, user_id: []const u8) !?AnomalyResult {
        const failure_count = self.failure_counts.get(user_id) orelse 0;
        const request_count = self.request_counts.get(user_id) orelse 0;

        if (request_count > 0) {
            const failure_rate = @as(f64, @floatFromInt(failure_count)) / @as(f64, @floatFromInt(request_count));
            if (failure_rate > self.failure_rate_threshold) {
                return AnomalyResult{
                    .event = .repeated_failures,
                    .details = "High failure rate detected",
                };
            }
        }

        return null;
    }

    pub fn recordRequest(self: *AnomalyDetector, user_id: []const u8, success: bool) !void {
        // Increment request count
        const req_count = self.request_counts.get(user_id) orelse 0;
        try self.request_counts.put(user_id, req_count + 1);

        // Increment failure count if failed
        if (!success) {
            const fail_count = self.failure_counts.get(user_id) orelse 0;
            try self.failure_counts.put(user_id, fail_count + 1);
        }
    }

    pub fn recordInputSize(self: *AnomalyDetector, size: usize) !?AnomalyResult {
        try self.input_sizes.append(self.allocator, @as(f64, @floatFromInt(size)));

        // Keep stats size limited
        if (self.input_sizes.items.len > self.max_stats_size) {
            _ = self.input_sizes.orderedRemove(0);
        }

        // Check if size is anomalous (simple threshold check)
        if (@as(f64, @floatFromInt(size)) > self.input_size_threshold * 1000.0) {
            return AnomalyResult{
                .event = .unusual_input_size,
                .details = "Input size exceeds threshold",
            };
        }

        return null;
    }

    pub fn recordOutputSize(self: *AnomalyDetector, size: usize) !?AnomalyResult {
        try self.output_sizes.append(self.allocator, @as(f64, @floatFromInt(size)));

        // Keep stats size limited
        if (self.output_sizes.items.len > self.max_stats_size) {
            _ = self.output_sizes.orderedRemove(0);
        }

        // Check if size is anomalous (simple threshold check)
        if (@as(f64, @floatFromInt(size)) > self.output_size_threshold * 1000.0) {
            return AnomalyResult{
                .event = .unusual_output_size,
                .details = "Output size exceeds threshold",
            };
        }

        return null;
    }
};

test "AnomalyDetector detects high request rate" {
    const allocator = std.testing.allocator;

    var detector = try AnomalyDetector.init(allocator, .{ .max_requests_per_minute = 5 });
    defer detector.deinit();

    const user_id = "user123";

    // Simulate 6 requests (exceeds limit of 5)
    var i: usize = 0;
    while (i < 6) : (i += 1) {
        const anomaly = try detector.detectRateAnomaly(user_id);
        if (i >= 5) {
            try std.testing.expect(anomaly != null);
            if (anomaly) |a| {
                try std.testing.expect(a.event == .high_request_rate);
            }
        }
    }
}

test "AnomalyDetector records request stats" {
    const allocator = std.testing.allocator;

    var detector = try AnomalyDetector.init(allocator, .{});
    defer detector.deinit();

    const user_id = "user456";

    // Record successful and failed requests
    try detector.recordRequest(user_id, true);
    try detector.recordRequest(user_id, true);
    try detector.recordRequest(user_id, false);

    // Check failure rate
    const anomaly = try detector.detectFailureAnomaly(user_id);
    try std.testing.expect(anomaly == null); // 1/3 = 0.33 < 0.5 threshold
}

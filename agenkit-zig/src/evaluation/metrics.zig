/// Metrics collection and aggregation
///
/// This module provides infrastructure for tracking and aggregating metrics
/// across agent sessions, including success rates, quality scores, costs,
/// and performance measurements.
///
/// Key design principles:
/// - Thread-safe metrics collection (with Mutex)
/// - Time-based session tracking
/// - Flexible metric aggregation
/// - JSON serialization support
const std = @import("std");
const agksync = @import("../sync_compat.zig");
const agktime = @import("../time_compat.zig");
const Allocator = std.mem.Allocator;

/// Session execution status
pub const SessionStatus = enum {
    running,
    completed,
    failed,
    timeout,
    cancelled,

    pub fn toString(self: SessionStatus) []const u8 {
        return switch (self) {
            .running => "running",
            .completed => "completed",
            .failed => "failed",
            .timeout => "timeout",
            .cancelled => "cancelled",
        };
    }

    pub fn fromString(s: []const u8) ?SessionStatus {
        if (std.mem.eql(u8, s, "running")) return .running;
        if (std.mem.eql(u8, s, "completed")) return .completed;
        if (std.mem.eql(u8, s, "failed")) return .failed;
        if (std.mem.eql(u8, s, "timeout")) return .timeout;
        if (std.mem.eql(u8, s, "cancelled")) return .cancelled;
        return null;
    }
};

/// Type of metric being measured
pub const MetricType = enum {
    success_rate,
    quality_score,
    cost,
    duration,
    context_length,
    error_rate,
    latency,
    throughput,
    accuracy,
    precision,
    recall,
    f1_score,

    pub fn toString(self: MetricType) []const u8 {
        return switch (self) {
            .success_rate => "success_rate",
            .quality_score => "quality_score",
            .cost => "cost",
            .duration => "duration",
            .context_length => "context_length",
            .error_rate => "error_rate",
            .latency => "latency",
            .throughput => "throughput",
            .accuracy => "accuracy",
            .precision => "precision",
            .recall => "recall",
            .f1_score => "f1_score",
        };
    }

    pub fn fromString(s: []const u8) ?MetricType {
        if (std.mem.eql(u8, s, "success_rate")) return .success_rate;
        if (std.mem.eql(u8, s, "quality_score")) return .quality_score;
        if (std.mem.eql(u8, s, "cost")) return .cost;
        if (std.mem.eql(u8, s, "duration")) return .duration;
        if (std.mem.eql(u8, s, "context_length")) return .context_length;
        if (std.mem.eql(u8, s, "error_rate")) return .error_rate;
        if (std.mem.eql(u8, s, "latency")) return .latency;
        if (std.mem.eql(u8, s, "throughput")) return .throughput;
        if (std.mem.eql(u8, s, "accuracy")) return .accuracy;
        if (std.mem.eql(u8, s, "precision")) return .precision;
        if (std.mem.eql(u8, s, "recall")) return .recall;
        if (std.mem.eql(u8, s, "f1_score")) return .f1_score;
        return null;
    }
};

/// A single metric measurement
pub const MetricMeasurement = struct {
    metric_type: MetricType,
    value: f64,
    timestamp: i64,
    session_id: []const u8,
    allocator: Allocator,

    pub fn init(
        allocator: Allocator,
        metric_type: MetricType,
        value: f64,
        session_id: []const u8,
    ) !*MetricMeasurement {
        const self = try allocator.create(MetricMeasurement);
        self.* = MetricMeasurement{
            .metric_type = metric_type,
            .value = value,
            .timestamp = agktime.timestamp(),
            .session_id = try allocator.dupe(u8, session_id),
            .allocator = allocator,
        };
        return self;
    }

    pub fn deinit(self: *MetricMeasurement) void {
        self.allocator.free(self.session_id);
        self.allocator.destroy(self);
    }
};

/// Result of a session execution
pub const SessionResult = struct {
    session_id: []const u8,
    agent_name: []const u8,
    status: SessionStatus,
    metrics: std.StringHashMap(f64),
    start_time: i64,
    end_time: i64,
    error_message: ?[]const u8,
    allocator: Allocator,

    pub fn init(
        allocator: Allocator,
        session_id: []const u8,
        agent_name: []const u8,
    ) !*SessionResult {
        const self = try allocator.create(SessionResult);
        self.* = SessionResult{
            .session_id = try allocator.dupe(u8, session_id),
            .agent_name = try allocator.dupe(u8, agent_name),
            .status = .running,
            .metrics = std.StringHashMap(f64).init(allocator),
            .start_time = agktime.timestamp(),
            .end_time = 0,
            .error_message = null,
            .allocator = allocator,
        };
        return self;
    }

    /// Calculate session duration in seconds
    pub fn duration(self: *const SessionResult) f64 {
        if (self.end_time == 0) {
            // Session still running, use current time
            const now = agktime.timestamp();
            return @as(f64, @floatFromInt(now - self.start_time));
        }
        return @as(f64, @floatFromInt(self.end_time - self.start_time));
    }

    /// Mark session as completed
    pub fn complete(self: *SessionResult) void {
        self.status = .completed;
        self.end_time = agktime.timestamp();
    }

    /// Mark session as failed with error message
    pub fn fail(self: *SessionResult, error_msg: []const u8) !void {
        self.status = .failed;
        self.end_time = agktime.timestamp();
        self.error_message = try self.allocator.dupe(u8, error_msg);
    }

    /// Add a metric value
    pub fn addMetric(self: *SessionResult, name: []const u8, value: f64) !void {
        const name_copy = try self.allocator.dupe(u8, name);
        try self.metrics.put(name_copy, value);
    }

    /// Get a metric value
    pub fn getMetric(self: *const SessionResult, name: []const u8) ?f64 {
        return self.metrics.get(name);
    }

    pub fn deinit(self: *SessionResult) void {
        self.allocator.free(self.session_id);
        self.allocator.free(self.agent_name);

        var metrics_it = self.metrics.iterator();
        while (metrics_it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
        }
        self.metrics.deinit();

        if (self.error_message) |msg| {
            self.allocator.free(msg);
        }

        self.allocator.destroy(self);
    }
};

/// Aggregated statistics across sessions
pub const Statistics = struct {
    total_sessions: usize,
    successful_sessions: usize,
    failed_sessions: usize,
    avg_duration: f64,
    total_cost: f64,
    avg_quality_score: f64,
    success_rate: f64,

    pub fn init() Statistics {
        return Statistics{
            .total_sessions = 0,
            .successful_sessions = 0,
            .failed_sessions = 0,
            .avg_duration = 0.0,
            .total_cost = 0.0,
            .avg_quality_score = 0.0,
            .success_rate = 0.0,
        };
    }
};

/// Collects and aggregates metrics across multiple sessions
pub const MetricsCollector = struct {
    sessions: std.ArrayList(*SessionResult),
    allocator: Allocator,
    mutex: agksync.Mutex,

    pub fn init(allocator: Allocator) !*MetricsCollector {
        const self = try allocator.create(MetricsCollector);
        self.* = .{
            .sessions = std.ArrayList(*SessionResult).empty,
            .allocator = allocator,
            .mutex = .{},
        };
        return self;
    }

    /// Record a completed session
    pub fn recordSession(self: *MetricsCollector, result: *SessionResult) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        // Create a copy of the session result
        const session_copy = try SessionResult.init(
            self.allocator,
            result.session_id,
            result.agent_name,
        );
        session_copy.status = result.status;
        session_copy.start_time = result.start_time;
        session_copy.end_time = result.end_time;

        // Copy metrics
        var metrics_it = result.metrics.iterator();
        while (metrics_it.next()) |entry| {
            try session_copy.addMetric(entry.key_ptr.*, entry.value_ptr.*);
        }

        // Copy error message if present
        if (result.error_message) |msg| {
            session_copy.error_message = try self.allocator.dupe(u8, msg);
        }

        try self.sessions.append(self.allocator, session_copy);
    }

    /// Get aggregated statistics
    pub fn getStatistics(self: *MetricsCollector) Statistics {
        self.mutex.lock();
        defer self.mutex.unlock();

        var stats = Statistics.init();
        stats.total_sessions = self.sessions.items.len;

        if (stats.total_sessions == 0) {
            return stats;
        }

        var total_duration: f64 = 0.0;
        var total_quality: f64 = 0.0;
        var quality_count: usize = 0;

        for (self.sessions.items) |session| {
            // Count successful/failed
            if (session.status == .completed) {
                stats.successful_sessions += 1;
            } else if (session.status == .failed) {
                stats.failed_sessions += 1;
            }

            // Accumulate duration
            total_duration += session.duration();

            // Accumulate cost
            if (session.getMetric("cost")) |cost| {
                stats.total_cost += cost;
            }

            // Accumulate quality scores
            if (session.getMetric("quality_score")) |quality| {
                total_quality += quality;
                quality_count += 1;
            }
        }

        // Calculate averages
        stats.avg_duration = total_duration / @as(f64, @floatFromInt(stats.total_sessions));

        if (quality_count > 0) {
            stats.avg_quality_score = total_quality / @as(f64, @floatFromInt(quality_count));
        }

        if (stats.total_sessions > 0) {
            stats.success_rate = @as(f64, @floatFromInt(stats.successful_sessions)) /
                @as(f64, @floatFromInt(stats.total_sessions));
        }

        return stats;
    }

    /// Filter sessions by agent name
    pub fn filterByAgent(
        self: *MetricsCollector,
        allocator: Allocator,
        agent_name: []const u8,
    ) !std.ArrayList(*SessionResult) {
        self.mutex.lock();
        defer self.mutex.unlock();

        var filtered = std.ArrayList(*SessionResult).empty;

        for (self.sessions.items) |session| {
            if (std.mem.eql(u8, session.agent_name, agent_name)) {
                try filtered.append(allocator, session);
            }
        }

        return filtered;
    }

    /// Filter sessions by status
    pub fn filterByStatus(
        self: *MetricsCollector,
        allocator: Allocator,
        status: SessionStatus,
    ) !std.ArrayList(*SessionResult) {
        self.mutex.lock();
        defer self.mutex.unlock();

        var filtered = std.ArrayList(*SessionResult).empty;

        for (self.sessions.items) |session| {
            if (session.status == status) {
                try filtered.append(allocator, session);
            }
        }

        return filtered;
    }

    /// Get sessions within a time range
    pub fn filterByTimeRange(
        self: *const MetricsCollector,
        allocator: Allocator,
        start: i64,
        end: i64,
    ) !std.ArrayList(*SessionResult) {
        self.mutex.lock();
        defer self.mutex.unlock();

        var filtered = std.ArrayList(*SessionResult).empty;

        for (self.sessions.items) |session| {
            if (session.start_time >= start and session.start_time <= end) {
                try filtered.append(allocator, session);
            }
        }

        return filtered;
    }

    /// Clear all recorded sessions
    pub fn clear(self: *MetricsCollector) void {
        self.mutex.lock();
        defer self.mutex.unlock();

        for (self.sessions.items) |session| {
            session.deinit();
        }
        self.sessions.clearAndFree(self.allocator);
    }

    pub fn deinit(self: *MetricsCollector) void {
        for (self.sessions.items) |session| {
            session.deinit();
        }
        self.sessions.deinit(self.allocator);
        self.allocator.destroy(self);
    }
};

// Tests
test "SessionStatus string conversion" {
    const allocator = std.testing.allocator;
    _ = allocator;

    try std.testing.expectEqualStrings("completed", SessionStatus.completed.toString());
    try std.testing.expectEqualStrings("failed", SessionStatus.failed.toString());

    try std.testing.expect(SessionStatus.fromString("completed") == .completed);
    try std.testing.expect(SessionStatus.fromString("failed") == .failed);
    try std.testing.expect(SessionStatus.fromString("invalid") == null);
}

test "MetricType string conversion" {
    const allocator = std.testing.allocator;
    _ = allocator;

    try std.testing.expectEqualStrings("success_rate", MetricType.success_rate.toString());
    try std.testing.expectEqualStrings("quality_score", MetricType.quality_score.toString());

    try std.testing.expect(MetricType.fromString("success_rate") == .success_rate);
    try std.testing.expect(MetricType.fromString("cost") == .cost);
    try std.testing.expect(MetricType.fromString("invalid") == null);
}

test "MetricMeasurement creation" {
    const allocator = std.testing.allocator;

    const measurement = try MetricMeasurement.init(
        allocator,
        .success_rate,
        0.85,
        "test-session",
    );
    defer measurement.deinit();

    try std.testing.expectEqual(MetricType.success_rate, measurement.metric_type);
    try std.testing.expectEqual(@as(f64, 0.85), measurement.value);
    try std.testing.expectEqualStrings("test-session", measurement.session_id);
}

test "SessionResult lifecycle" {
    const allocator = std.testing.allocator;

    const result = try SessionResult.init(allocator, "session-1", "test-agent");
    defer result.deinit();

    try std.testing.expectEqualStrings("session-1", result.session_id);
    try std.testing.expectEqualStrings("test-agent", result.agent_name);
    try std.testing.expectEqual(SessionStatus.running, result.status);

    // Add metrics
    try result.addMetric("accuracy", 0.95);
    try result.addMetric("latency", 123.45);

    try std.testing.expectEqual(@as(f64, 0.95), result.getMetric("accuracy").?);
    try std.testing.expectEqual(@as(f64, 123.45), result.getMetric("latency").?);

    // Complete session
    result.complete();
    try std.testing.expectEqual(SessionStatus.completed, result.status);
}

test "SessionResult duration calculation" {
    const allocator = std.testing.allocator;

    const result = try SessionResult.init(allocator, "session-1", "test-agent");
    defer result.deinit();

    // Manually set end time for testing
    result.start_time = 1000;
    result.end_time = 1005;

    const dur = result.duration();
    try std.testing.expectEqual(@as(f64, 5.0), dur);
}

test "SessionResult failure" {
    const allocator = std.testing.allocator;

    const result = try SessionResult.init(allocator, "session-1", "test-agent");
    defer result.deinit();

    try result.fail("Connection timeout");

    try std.testing.expectEqual(SessionStatus.failed, result.status);
    try std.testing.expectEqualStrings("Connection timeout", result.error_message.?);
}

test "MetricsCollector record and statistics" {
    const allocator = std.testing.allocator;

    const collector = try MetricsCollector.init(allocator);
    defer collector.deinit();

    // Create and record successful session
    const result1 = try SessionResult.init(allocator, "session-1", "agent-1");
    try result1.addMetric("quality_score", 0.85);
    try result1.addMetric("cost", 0.05);
    result1.complete();
    try collector.recordSession(result1);
    result1.deinit();

    // Create and record failed session
    const result2 = try SessionResult.init(allocator, "session-2", "agent-1");
    try result2.fail("Error");
    try collector.recordSession(result2);
    result2.deinit();

    const stats = collector.getStatistics();

    try std.testing.expectEqual(@as(usize, 2), stats.total_sessions);
    try std.testing.expectEqual(@as(usize, 1), stats.successful_sessions);
    try std.testing.expectEqual(@as(usize, 1), stats.failed_sessions);
    try std.testing.expectEqual(@as(f64, 0.5), stats.success_rate);
    try std.testing.expectEqual(@as(f64, 0.85), stats.avg_quality_score);
    try std.testing.expectEqual(@as(f64, 0.05), stats.total_cost);
}

test "MetricsCollector filter by agent" {
    const allocator = std.testing.allocator;

    const collector = try MetricsCollector.init(allocator);
    defer collector.deinit();

    // Record sessions for different agents
    const result1 = try SessionResult.init(allocator, "session-1", "agent-1");
    result1.complete();
    try collector.recordSession(result1);
    result1.deinit();

    const result2 = try SessionResult.init(allocator, "session-2", "agent-2");
    result2.complete();
    try collector.recordSession(result2);
    result2.deinit();

    const result3 = try SessionResult.init(allocator, "session-3", "agent-1");
    result3.complete();
    try collector.recordSession(result3);
    result3.deinit();

    // Filter by agent-1
    var filtered = try collector.filterByAgent(allocator, "agent-1");
    defer filtered.deinit(allocator);

    try std.testing.expectEqual(@as(usize, 2), filtered.items.len);
}

test "MetricsCollector filter by status" {
    const allocator = std.testing.allocator;

    const collector = try MetricsCollector.init(allocator);
    defer collector.deinit();

    const result1 = try SessionResult.init(allocator, "session-1", "agent-1");
    result1.complete();
    try collector.recordSession(result1);
    result1.deinit();

    const result2 = try SessionResult.init(allocator, "session-2", "agent-1");
    try result2.fail("Error");
    try collector.recordSession(result2);
    result2.deinit();

    // Filter completed
    var completed = try collector.filterByStatus(allocator, .completed);
    defer completed.deinit(allocator);
    try std.testing.expectEqual(@as(usize, 1), completed.items.len);

    // Filter failed
    var failed = try collector.filterByStatus(allocator, .failed);
    defer failed.deinit(allocator);
    try std.testing.expectEqual(@as(usize, 1), failed.items.len);
}

test "MetricsCollector clear" {
    const allocator = std.testing.allocator;

    const collector = try MetricsCollector.init(allocator);
    defer collector.deinit();

    const result = try SessionResult.init(allocator, "session-1", "agent-1");
    result.complete();
    try collector.recordSession(result);
    result.deinit();

    try std.testing.expectEqual(@as(usize, 1), collector.sessions.items.len);

    collector.clear();

    try std.testing.expectEqual(@as(usize, 0), collector.sessions.items.len);
}

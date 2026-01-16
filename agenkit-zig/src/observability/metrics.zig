/// Metrics module for Agenkit Zig observability
///
/// This module provides OpenTelemetry-compatible metrics collection including:
/// - Counter metrics for request counts
/// - Histogram metrics for latency measurements
/// - MetricsMiddleware for automatic agent instrumentation
///
/// ## Example
///
/// ```zig
/// const metrics = @import("metrics.zig");
/// const std = @import("std");
///
/// // Initialize metrics (TODO: implement exporters)
/// try metrics.init(allocator);
///
/// // Create middleware to wrap an agent
/// var middleware = try metrics.MetricsMiddleware.init(allocator, inner_agent);
/// defer middleware.deinit();
///
/// // Process message - automatically records metrics
/// const result = try middleware.agent().process(msg);
/// ```

const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const Message = @import("../message.zig").Message;
const AgentError = @import("../agent.zig").AgentError;
const Result = @import("../agent.zig").Result;
const StreamCallbacks = @import("../agent.zig").StreamCallbacks;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;

const Allocator = std.mem.Allocator;

/// Counter metric for tracking counts (e.g., request counts)
pub const Counter = struct {
    allocator: Allocator,
    name: []const u8,
    value: u64,
    labels: std.StringHashMap([]const u8),

    pub fn init(allocator: Allocator, name: []const u8) !Counter {
        return Counter{
            .allocator = allocator,
            .name = try allocator.dupe(u8, name),
            .value = 0,
            .labels = std.StringHashMap([]const u8).init(allocator),
        };
    }

    pub fn deinit(self: *Counter) void {
        self.allocator.free(self.name);
        var iter = self.labels.iterator();
        while (iter.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            self.allocator.free(entry.value_ptr.*);
        }
        self.labels.deinit();
    }

    pub fn add(self: *Counter, delta: u64) void {
        self.value += delta;
    }

    pub fn withLabel(self: *Counter, key: []const u8, value: []const u8) !void {
        const key_copy = try self.allocator.dupe(u8, key);
        const value_copy = try self.allocator.dupe(u8, value);
        try self.labels.put(key_copy, value_copy);
    }
};

/// Histogram metric for tracking distributions (e.g., latencies)
pub const Histogram = struct {
    allocator: Allocator,
    name: []const u8,
    observations: std.ArrayList(f64),

    pub fn init(allocator: Allocator, name: []const u8) !Histogram {
        return Histogram{
            .allocator = allocator,
            .name = try allocator.dupe(u8, name),
            .observations = std.ArrayList(f64){},
        };
    }

    pub fn deinit(self: *Histogram) void {
        self.allocator.free(self.name);
        self.observations.deinit(self.allocator);
    }

    pub fn observe(self: *Histogram, value: f64) !void {
        try self.observations.append(self.allocator, value);
    }

    pub fn count(self: *const Histogram) usize {
        return self.observations.items.len;
    }

    pub fn sum(self: *const Histogram) f64 {
        var total: f64 = 0.0;
        for (self.observations.items) |val| {
            total += val;
        }
        return total;
    }

    pub fn mean(self: *const Histogram) ?f64 {
        if (self.observations.items.len == 0) return null;
        return self.sum() / @as(f64, @floatFromInt(self.observations.items.len));
    }

    pub fn min(self: *const Histogram) ?f64 {
        if (self.observations.items.len == 0) return null;
        var minimum = self.observations.items[0];
        for (self.observations.items[1..]) |val| {
            if (val < minimum) minimum = val;
        }
        return minimum;
    }

    pub fn max(self: *const Histogram) ?f64 {
        if (self.observations.items.len == 0) return null;
        var maximum = self.observations.items[0];
        for (self.observations.items[1..]) |val| {
            if (val > maximum) maximum = val;
        }
        return maximum;
    }
};

/// MetricsMiddleware wraps an Agent to automatically record metrics
pub const MetricsMiddleware = struct {
    allocator: Allocator,
    inner: Agent,
    requests_total: Counter,
    request_duration: Histogram,

    pub fn init(allocator: Allocator, inner: Agent) !MetricsMiddleware {
        return MetricsMiddleware{
            .allocator = allocator,
            .inner = inner,
            .requests_total = try Counter.init(allocator, "agent_requests_total"),
            .request_duration = try Histogram.init(allocator, "agent_request_duration_seconds"),
        };
    }

    pub fn deinit(self: *MetricsMiddleware) void {
        self.requests_total.deinit();
        self.request_duration.deinit();
    }

    pub fn agent(self: *MetricsMiddleware) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = name,
                .capabilities = capabilities,
                .process = process,
                .process_stream = processStream,
                .introspect = introspect,
                .deinit = vtableDeinit,
            },
        };
    }

    fn name(ptr: *anyopaque) []const u8 {
        const self: *MetricsMiddleware = @ptrCast(@alignCast(ptr));
        return self.inner.name();
    }

    fn capabilities(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *MetricsMiddleware = @ptrCast(@alignCast(ptr));
        return self.inner.capabilities(allocator);
    }

    fn process(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *MetricsMiddleware = @ptrCast(@alignCast(ptr));

        const start_time = std.time.milliTimestamp();
        const result = self.inner.process(message);
        const end_time = std.time.milliTimestamp();

        const duration_ms = @as(f64, @floatFromInt(end_time - start_time));
        const duration_secs = duration_ms / 1000.0;

        // Record metrics
        self.requests_total.add(1);
        self.request_duration.observe(duration_secs) catch {};

        return result;
    }

    fn processStream(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        callbacks.onError(AgentError.NotImplemented);
    }

    fn introspect(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *MetricsMiddleware = @ptrCast(@alignCast(ptr));
        const caps = try capabilities(ptr, allocator);
        defer allocator.free(caps);
        return createDefaultIntrospectionResult(allocator, self.inner.name(), caps);
    }

    fn vtableDeinit(ptr: *anyopaque) void {
        const self: *MetricsMiddleware = @ptrCast(@alignCast(ptr));
        self.requests_total.deinit();
        self.request_duration.deinit();
    }
};

// Tests

test "Counter creation and increment" {
    const allocator = std.testing.allocator;

    var counter = try Counter.init(allocator, "test_counter");
    defer counter.deinit();

    try std.testing.expectEqual(@as(u64, 0), counter.value);

    counter.add(1);
    try std.testing.expectEqual(@as(u64, 1), counter.value);

    counter.add(5);
    try std.testing.expectEqual(@as(u64, 6), counter.value);
}

test "Counter with labels" {
    const allocator = std.testing.allocator;

    var counter = try Counter.init(allocator, "test_counter");
    defer counter.deinit();

    try counter.withLabel("status", "success");
    try counter.withLabel("method", "POST");

    const status = counter.labels.get("status");
    try std.testing.expect(status != null);
    try std.testing.expectEqualStrings("success", status.?);
}

test "Histogram observation" {
    const allocator = std.testing.allocator;

    var histogram = try Histogram.init(allocator, "test_histogram");
    defer histogram.deinit();

    try histogram.observe(1.0);
    try histogram.observe(2.0);
    try histogram.observe(3.0);

    try std.testing.expectEqual(@as(usize, 3), histogram.count());
    try std.testing.expectEqual(@as(f64, 6.0), histogram.sum());
}

test "MetricsMiddleware wraps agent" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var middleware = try MetricsMiddleware.init(allocator, echo.agent());
    defer middleware.deinit();

    var msg = try Message.withText(allocator, .user, "test");
    defer msg.deinit();

    var result = try middleware.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    // Should have recorded one request
    try std.testing.expectEqual(@as(u64, 1), middleware.requests_total.value);
    try std.testing.expectEqual(@as(usize, 1), middleware.request_duration.count());
}

test "Counter with multiple labels" {
    const allocator = std.testing.allocator;

    var counter = try Counter.init(allocator, "http_requests");
    defer counter.deinit();

    try counter.withLabel("method", "GET");
    try counter.withLabel("path", "/api/users");
    try counter.withLabel("status", "200");

    counter.add(10);

    try std.testing.expectEqual(@as(u64, 10), counter.value);
    try std.testing.expectEqual(@as(usize, 3), counter.labels.count());

    const method = counter.labels.get("method");
    try std.testing.expectEqualStrings("GET", method.?);
}

test "Histogram statistics" {
    const allocator = std.testing.allocator;

    var histogram = try Histogram.init(allocator, "latency");
    defer histogram.deinit();

    try histogram.observe(1.5);
    try histogram.observe(2.5);
    try histogram.observe(3.5);
    try histogram.observe(4.5);
    try histogram.observe(5.5);

    // Test statistics
    try std.testing.expectEqual(@as(usize, 5), histogram.count());
    try std.testing.expectEqual(@as(f64, 17.5), histogram.sum());

    const mean_val = histogram.mean();
    try std.testing.expect(mean_val != null);
    try std.testing.expectApproxEqAbs(@as(f64, 3.5), mean_val.?, 0.001);

    const min_val = histogram.min();
    try std.testing.expect(min_val != null);
    try std.testing.expectEqual(@as(f64, 1.5), min_val.?);

    const max_val = histogram.max();
    try std.testing.expect(max_val != null);
    try std.testing.expectEqual(@as(f64, 5.5), max_val.?);
}

test "Histogram empty statistics" {
    const allocator = std.testing.allocator;

    var histogram = try Histogram.init(allocator, "empty");
    defer histogram.deinit();

    try std.testing.expectEqual(@as(usize, 0), histogram.count());
    try std.testing.expectEqual(@as(f64, 0.0), histogram.sum());
    try std.testing.expect(histogram.mean() == null);
    try std.testing.expect(histogram.min() == null);
    try std.testing.expect(histogram.max() == null);
}

test "MetricsMiddleware multiple requests" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var middleware = try MetricsMiddleware.init(allocator, echo.agent());
    defer middleware.deinit();

    // Process multiple messages
    var i: usize = 0;
    while (i < 5) : (i += 1) {
        var msg = try Message.withText(allocator, .user, "test");
        defer msg.deinit();

        var result = try middleware.agent().process(msg);
        var response = try result.unwrap();
        defer response.deinit();
    }

    // Should have recorded 5 requests
    try std.testing.expectEqual(@as(u64, 5), middleware.requests_total.value);
    try std.testing.expectEqual(@as(usize, 5), middleware.request_duration.count());

    // All durations should be non-negative
    for (middleware.request_duration.observations.items) |duration| {
        try std.testing.expect(duration >= 0.0);
    }
}

test "MetricsMiddleware tracks duration" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var middleware = try MetricsMiddleware.init(allocator, echo.agent());
    defer middleware.deinit();

    var msg = try Message.withText(allocator, .user, "test message");
    defer msg.deinit();

    var result = try middleware.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    // Verify duration was recorded
    try std.testing.expectEqual(@as(usize, 1), middleware.request_duration.count());

    const duration = middleware.request_duration.observations.items[0];
    // Duration should be a small positive number (< 1 second for echo)
    try std.testing.expect(duration >= 0.0);
    try std.testing.expect(duration < 1.0);
}

test "Counter label retrieval" {
    const allocator = std.testing.allocator;

    var counter = try Counter.init(allocator, "api_calls");
    defer counter.deinit();

    try counter.withLabel("version", "v1");
    try counter.withLabel("region", "us-east");

    // Verify labels can be retrieved
    const version = counter.labels.get("version");
    try std.testing.expect(version != null);
    try std.testing.expectEqualStrings("v1", version.?);

    const region = counter.labels.get("region");
    try std.testing.expect(region != null);
    try std.testing.expectEqualStrings("us-east", region.?);

    // Non-existent label should return null
    const missing = counter.labels.get("missing");
    try std.testing.expect(missing == null);
}

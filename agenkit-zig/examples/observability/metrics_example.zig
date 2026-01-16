/// Metrics Collection Example
///
/// This example demonstrates metrics collection and aggregation for monitoring
/// agent performance and behavior.
///
/// Features demonstrated:
/// 1. Counter metrics for request counting
/// 2. Histogram metrics for latency distribution
/// 3. MetricsMiddleware for automatic instrumentation
/// 4. Statistical aggregations (mean, min, max)
/// 5. Label-based metrics organization
///
/// Usage:
///   zig build run-metrics-example

const std = @import("std");
const agenkit = @import("agenkit");
const EchoAgent = agenkit.EchoAgent;
const Message = agenkit.Message;
const MetricsMiddleware = agenkit.observability.MetricsMiddleware;
const Counter = agenkit.observability.Counter;
const Histogram = agenkit.observability.Histogram;

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Metrics Collection Example ===\n\n", .{});

    // Example 1: Basic counter metrics
    std.debug.print("--- Example 1: Counter Metrics ---\n", .{});
    try counterMetrics(allocator);

    // Example 2: Histogram metrics
    std.debug.print("\n--- Example 2: Histogram Metrics ---\n", .{});
    try histogramMetrics(allocator);

    // Example 3: MetricsMiddleware automatic instrumentation
    std.debug.print("\n--- Example 3: Automatic Instrumentation ---\n", .{});
    try automaticInstrumentation(allocator);

    // Example 4: Labeled metrics
    std.debug.print("\n--- Example 4: Labeled Metrics ---\n", .{});
    try labeledMetrics(allocator);

    std.debug.print("\n=== All Examples Complete ===\n", .{});
}

/// Example 1: Counter metrics for request counting
fn counterMetrics(allocator: std.mem.Allocator) !void {
    var counter = try Counter.init(allocator, "requests_total");
    defer counter.deinit();

    std.debug.print("Initial value: {}\n", .{counter.value});

    // Simulate some requests
    counter.add(1);
    std.debug.print("After 1 request: {}\n", .{counter.value});

    counter.add(5);
    std.debug.print("After 5 more requests: {}\n", .{counter.value});

    counter.add(10);
    std.debug.print("After 10 more requests: {}\n", .{counter.value});

    std.debug.print("Total requests: {}\n", .{counter.value});
    std.debug.print("✅ Counter tracks cumulative values!\n", .{});
}

/// Example 2: Histogram metrics for latency distribution
fn histogramMetrics(allocator: std.mem.Allocator) !void {
    var histogram = try Histogram.init(allocator, "request_duration_seconds");
    defer histogram.deinit();

    // Simulate request latencies
    const latencies = [_]f64{ 0.015, 0.023, 0.018, 0.045, 0.012, 0.067, 0.019, 0.034, 0.021, 0.029 };

    for (latencies) |latency| {
        try histogram.observe(latency);
    }

    // Calculate statistics
    const count = histogram.count();
    const sum = histogram.sum();
    const mean_val = histogram.mean();
    const min_val = histogram.min();
    const max_val = histogram.max();

    std.debug.print("Observations: {}\n", .{count});
    std.debug.print("Total time: {d:.3}s\n", .{sum});
    if (mean_val) |m| {
        std.debug.print("Mean latency: {d:.3}s\n", .{m});
    }
    if (min_val) |min| {
        std.debug.print("Min latency: {d:.3}s\n", .{min});
    }
    if (max_val) |max| {
        std.debug.print("Max latency: {d:.3}s\n", .{max});
    }

    std.debug.print("✅ Histogram provides latency distribution!\n", .{});
}

/// Example 3: MetricsMiddleware for automatic instrumentation
fn automaticInstrumentation(allocator: std.mem.Allocator) !void {
    // Create base agent
    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    // Wrap with metrics middleware
    var metrics = try MetricsMiddleware.init(allocator, echo.agent());
    defer metrics.deinit();

    std.debug.print("Processing messages...\n\n", .{});

    // Process multiple messages
    var i: usize = 0;
    while (i < 5) : (i += 1) {
        var msg = try Message.withText(allocator, .user, "Test message");
        defer msg.deinit();

        var result = try metrics.agent().process(msg);
        var response = try result.unwrap();
        defer response.deinit();

        std.debug.print("Request {}: completed\n", .{i + 1});
    }

    // Display collected metrics
    std.debug.print("\nCollected Metrics:\n", .{});
    std.debug.print("Total requests: {}\n", .{metrics.requests_total.value});
    std.debug.print("Latency observations: {}\n", .{metrics.request_duration.count()});

    if (metrics.request_duration.mean()) |mean| {
        std.debug.print("Mean duration: {d:.6}s\n", .{mean});
    }
    if (metrics.request_duration.min()) |min| {
        std.debug.print("Min duration: {d:.6}s\n", .{min});
    }
    if (metrics.request_duration.max()) |max| {
        std.debug.print("Max duration: {d:.6}s\n", .{max});
    }

    std.debug.print("✅ Metrics automatically collected!\n", .{});
}

/// Example 4: Labeled metrics for multi-dimensional tracking
fn labeledMetrics(allocator: std.mem.Allocator) !void {
    // HTTP request counter with labels
    var http_requests = try Counter.init(allocator, "http_requests_total");
    defer http_requests.deinit();

    // Add labels for method, path, status
    try http_requests.withLabel("method", "GET");
    try http_requests.withLabel("path", "/api/agents");
    try http_requests.withLabel("status", "200");

    // Simulate requests
    http_requests.add(42);

    std.debug.print("Metric: {s}\n", .{http_requests.name});
    std.debug.print("Value: {}\n", .{http_requests.value});
    std.debug.print("Labels:\n", .{});

    var iter = http_requests.labels.iterator();
    while (iter.next()) |entry| {
        std.debug.print("  {s}=\"{s}\"\n", .{ entry.key_ptr.*, entry.value_ptr.* });
    }

    std.debug.print("\nPrometheus format:\n", .{});
    std.debug.print("{s}{{", .{http_requests.name});
    var first = true;
    var iter2 = http_requests.labels.iterator();
    while (iter2.next()) |entry| {
        if (!first) std.debug.print(",", .{});
        std.debug.print("{s}=\"{s}\"", .{ entry.key_ptr.*, entry.value_ptr.* });
        first = false;
    }
    std.debug.print("}} {}\n", .{http_requests.value});

    std.debug.print("✅ Labels enable multi-dimensional metrics!\n", .{});
}

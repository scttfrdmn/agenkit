//! Production-ready agent with load balancing, health checks, and enhanced retry.
//!
//! This example demonstrates how to build a production agent system with:
//! - Load balancing across multiple backend agents
//! - Health monitoring with Kubernetes-style probes
//! - Enhanced retry with jitter and backpressure detection
//! - Prometheus metrics export
//!
//! Perfect for 30-hour autonomous agent deployments.

const std = @import("std");
const agenkit = @import("agenkit");

const Agent = agenkit.core.Agent;
const Message = agenkit.core.Message;
const LoadBalancer = agenkit.infrastructure.LoadBalancer;
const LoadBalancerConfig = agenkit.infrastructure.LoadBalancerConfig;
const LoadBalancingStrategy = agenkit.infrastructure.LoadBalancingStrategy;
const HealthChecker = agenkit.infrastructure.HealthChecker;
const HealthCheckConfig = agenkit.infrastructure.HealthCheckConfig;
const EnhancedRetryDecorator = agenkit.infrastructure.EnhancedRetryDecorator;
const EnhancedRetryConfig = agenkit.infrastructure.EnhancedRetryConfig;
const JitterType = agenkit.infrastructure.JitterType;

/// Simulated agent for testing production infrastructure.
const SimulatedAgent = struct {
    allocator: std.mem.Allocator,
    agent_name: []const u8,
    failure_rate: f64,
    request_count: std.atomic.Value(u64),

    const Self = @This();

    pub fn init(allocator: std.mem.Allocator, name: []const u8, failure_rate: f64) !*Self {
        const self = try allocator.create(Self);
        self.* = .{
            .allocator = allocator,
            .agent_name = try allocator.dupe(u8, name),
            .failure_rate = failure_rate,
            .request_count = std.atomic.Value(u64).init(0),
        };
        return self;
    }

    pub fn deinit(self: *Self) void {
        self.allocator.free(self.agent_name);
        self.allocator.destroy(self);
    }

    pub fn name(self: *const Self) []const u8 {
        return self.agent_name;
    }

    pub fn capabilities(self: *const Self, allocator: std.mem.Allocator) ![]const []const u8 {
        _ = self;
        var caps = try allocator.alloc([]const u8, 2);
        caps[0] = try allocator.dupe(u8, "text_generation");
        caps[1] = try allocator.dupe(u8, "reasoning");
        return caps;
    }

    pub fn process(self: *Self, allocator: std.mem.Allocator, message: Message) !Message {
        _ = self.request_count.fetchAdd(1, .monotonic);

        // Simulate processing time
        std.time.sleep(100 * std.time.ns_per_ms);

        // Simulate occasional failures
        var prng = std.rand.DefaultPrng.init(@intCast(std.time.milliTimestamp()));
        const random = prng.random();
        if (random.float(f64) < self.failure_rate) {
            return error.ProcessingError;
        }

        const content = try std.fmt.allocPrint(
            allocator,
            "{s} processed: {s}",
            .{ self.agent_name, message.content },
        );

        var metadata = std.StringHashMap([]const u8).init(allocator);
        try metadata.put("agent", self.agent_name);
        try metadata.put(
            "request_count",
            try std.fmt.allocPrint(allocator, "{d}", .{self.request_count.load(.monotonic)}),
        );

        return Message{
            .role = try allocator.dupe(u8, "agent"),
            .content = content,
            .metadata = metadata,
        };
    }
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("Starting production agent system...\n", .{});

    // 1. Create backend agents with varying failure rates
    const backend1 = try SimulatedAgent.init(allocator, "agent-1", 0.1);
    defer backend1.deinit();
    const backend2 = try SimulatedAgent.init(allocator, "agent-2", 0.05);
    defer backend2.deinit();
    const backend3 = try SimulatedAgent.init(allocator, "agent-3", 0.15);
    defer backend3.deinit();

    // 2. Wrap each backend with enhanced retry
    var retry_config = EnhancedRetryConfig{
        .max_attempts = 3,
        .initial_backoff_ms = 100,
        .max_backoff_ms = 5000,
        .backoff_multiplier = 2.0,
        .jitter_type = JitterType.full,
        .enable_backpressure = true,
        .backpressure_threshold = 0.3,
        .backpressure_window = 10,
    };

    const retry_backend1 = try EnhancedRetryDecorator.init(
        allocator,
        @ptrCast(backend1),
        retry_config,
    );
    defer retry_backend1.deinit();
    const retry_backend2 = try EnhancedRetryDecorator.init(
        allocator,
        @ptrCast(backend2),
        retry_config,
    );
    defer retry_backend2.deinit();
    const retry_backend3 = try EnhancedRetryDecorator.init(
        allocator,
        @ptrCast(backend3),
        retry_config,
    );
    defer retry_backend3.deinit();

    // 3. Create load balancer with health checking
    const lb_config = LoadBalancerConfig{
        .strategy = LoadBalancingStrategy.least_connections,
        .health_check_enabled = true,
        .health_check_interval_ms = 5000,
        .health_check_timeout_ms = 2000,
        .max_retries_per_backend = 2,
    };

    var backends = [_]Agent{
        @ptrCast(retry_backend1),
        @ptrCast(retry_backend2),
        @ptrCast(retry_backend3),
    };

    const load_balancer = try LoadBalancer.init(allocator, &backends, lb_config);
    defer load_balancer.deinit();

    // 4. Set up health checker for the load balancer
    const health_config = HealthCheckConfig{
        .liveness_enabled = true,
        .liveness_interval_ms = 10000,
        .liveness_failure_threshold = 3,
        .readiness_enabled = true,
        .readiness_interval_ms = 5000,
        .readiness_failure_threshold = 2,
        .startup_enabled = true,
        .startup_timeout_ms = 30000,
        .startup_failure_threshold = 5,
    };

    const health_checker = try HealthChecker.init(
        allocator,
        @ptrCast(load_balancer),
        health_config,
    );
    defer health_checker.deinit();
    try health_checker.start();
    defer health_checker.stop();

    // Wait for startup to complete
    std.debug.print("Waiting for startup checks...\n", .{});
    std.time.sleep(2 * std.time.ns_per_s);

    if (!health_checker.isHealthy()) {
        std.debug.print("System failed startup checks\n", .{});
        return;
    }

    std.debug.print("System is healthy and ready!\n", .{});

    // 5. Process requests through the production system
    var successful: u32 = 0;
    var failed: u32 = 0;

    var i: u32 = 0;
    while (i < 20) : (i += 1) {
        const content = try std.fmt.allocPrint(allocator, "Request {d}", .{i});
        defer allocator.free(content);

        const message = Message{
            .role = try allocator.dupe(u8, "user"),
            .content = content,
            .metadata = null,
        };

        const response = load_balancer.process(allocator, message) catch |err| {
            std.debug.print("Request {d}: FAILED - {}\n", .{ i, err });
            failed += 1;
            continue;
        };
        defer response.deinit(allocator);

        std.debug.print("Request {d}: SUCCESS - {s}\n", .{ i, response.content });
        successful += 1;

        // Brief pause between requests
        std.time.sleep(200 * std.time.ns_per_ms);
    }

    // 6. Export metrics
    std.debug.print("\n{s}\n", .{"=" ** 60});
    std.debug.print("FINAL METRICS\n", .{});
    std.debug.print("{s}\n", .{"=" ** 60});

    // Load balancer metrics
    const lb_metrics = load_balancer.getMetrics();
    std.debug.print("\nLoad Balancer:\n", .{});
    std.debug.print("  Total requests: {d}\n", .{lb_metrics.total_requests});
    std.debug.print("  Successful: {d}\n", .{lb_metrics.successful_requests});
    std.debug.print("  Failed: {d}\n", .{lb_metrics.failed_requests});
    if (lb_metrics.total_requests > 0) {
        const success_rate = @as(f64, @floatFromInt(lb_metrics.successful_requests)) /
            @as(f64, @floatFromInt(lb_metrics.total_requests)) * 100.0;
        std.debug.print("  Success rate: {d:.1}%\n", .{success_rate});
    }

    // Backend distribution
    std.debug.print("\nBackend Distribution:\n", .{});
    var it = lb_metrics.backend_request_counts.iterator();
    while (it.next()) |entry| {
        std.debug.print("  {s}: {d} requests\n", .{ entry.key_ptr.*, entry.value_ptr.* });
    }

    // Retry metrics for each backend
    std.debug.print("\nRetry Metrics:\n", .{});
    const retry_backends = [_]*EnhancedRetryDecorator{
        retry_backend1,
        retry_backend2,
        retry_backend3,
    };
    for (retry_backends, 0..) |backend, idx| {
        const metrics = backend.getMetrics();
        std.debug.print("  Agent {d}:\n", .{idx + 1});
        std.debug.print("    Total attempts: {d}\n", .{metrics.total_attempts});
        std.debug.print("    Successful on first: {d}\n", .{metrics.successful_first_attempt});
        std.debug.print("    Successful on retry: {d}\n", .{metrics.successful_on_retry});
        std.debug.print("    Failed after retries: {d}\n", .{metrics.failed_after_retries});
        std.debug.print("    Total retries: {d}\n", .{metrics.total_retries});
        if (metrics.backpressure_detected > 0) {
            std.debug.print("    Backpressure detected: {d} times\n", .{metrics.backpressure_detected});
        }
    }

    // Health metrics
    const health_metrics = health_checker.getMetrics();
    std.debug.print("\nHealth Checks:\n", .{});
    var health_it = health_metrics.total_checks.iterator();
    while (health_it.next()) |entry| {
        const probe_type = entry.key_ptr.*;
        const count = entry.value_ptr.*;
        const success = health_metrics.successful_checks.get(probe_type) orelse 0;
        const failed_count = health_metrics.failed_checks.get(probe_type) orelse 0;
        std.debug.print("  {s}: {d}/{d} passed ({d} failed)\n", .{
            @tagName(probe_type),
            success,
            count,
            failed_count,
        });
    }

    // Export Prometheus metrics
    std.debug.print("\nPrometheus Metrics:\n", .{});
    std.debug.print("{s}\n", .{"=" ** 60});
    const prometheus_metrics = try health_checker.exportPrometheusMetrics(allocator);
    defer allocator.free(prometheus_metrics);
    std.debug.print("{s}\n", .{prometheus_metrics});

    std.debug.print("\nProduction agent system stopped.\n", .{});
}

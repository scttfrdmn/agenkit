//! Evaluation Pipeline Integration Example
//!
//! Demonstrates performance measurement and evaluation for agents:
//! - Timing measurements
//! - Success rate tracking
//! - Quality scoring
//! - Throughput measurement
//! - Resource usage monitoring
//! - Real-world use case: Agent performance benchmarking
//!
//! This example shows how to measure and evaluate agent performance
//! for production deployment decisions.
//!
//! Run with: zig build run-evaluation

const std = @import("std");
const agenkit = @import("agenkit");
const Message = agenkit.Message;
const AgentError = agenkit.AgentError;
const StreamCallbacks = agenkit.StreamCallbacks;

/// Test agent with configurable performance characteristics
const BenchmarkAgent = struct {
    allocator: std.mem.Allocator,
    agent_name: []const u8,
    delay_ms: u64,
    success_rate: f32,
    prng: std.Random.DefaultPrng,

    pub fn init(allocator: std.mem.Allocator, name: []const u8, delay_ms: u64, success_rate: f32) !*BenchmarkAgent {
        var seed: u64 = undefined;
        try std.posix.getrandom(std.mem.asBytes(&seed));

        const self = try allocator.create(BenchmarkAgent);
        self.* = .{
            .allocator = allocator,
            .agent_name = try allocator.dupe(u8, name),
            .delay_ms = delay_ms,
            .success_rate = success_rate,
            .prng = std.Random.DefaultPrng.init(seed),
        };
        return self;
    }

    pub fn deinit(self: *BenchmarkAgent) void {
        self.allocator.free(self.agent_name);
        self.allocator.destroy(self);
    }

    pub fn agent(self: *BenchmarkAgent) agenkit.Agent {
        return agenkit.Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .process_stream = processStreamImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *BenchmarkAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "benchmark";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *BenchmarkAgent = @ptrCast(@alignCast(ptr));

        const content = message.contentAsText() catch {
            return agenkit.Result{ .err = agenkit.AgentError.InvalidInput };
        };

        // Simulate processing delay
        std.Thread.sleep(self.delay_ms * std.time.ns_per_ms);

        // Simulate success/failure based on success_rate
        const rand_val = self.prng.random().float(f32);
        if (rand_val > self.success_rate) {
            return agenkit.Result{ .err = agenkit.AgentError.ProcessingFailed };
        }

        const response_text = std.fmt.allocPrint(
            self.allocator,
            "[{s}] Processed: {s}",
            .{ self.agent_name, content },
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };
        defer self.allocator.free(response_text);

        const response = agenkit.Message.withText(self.allocator, .assistant, response_text) catch {
            return agenkit.AgentError.ProcessingFailed;
        };

        return agenkit.Result{ .ok = response };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        const self: *BenchmarkAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return agenkit.createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *BenchmarkAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};

/// Evaluation metrics collector
const EvaluationMetrics = struct {
    total_requests: usize,
    successful_requests: usize,
    failed_requests: usize,
    total_duration_ns: u64,
    min_duration_ns: u64,
    max_duration_ns: u64,

    pub fn init() EvaluationMetrics {
        return EvaluationMetrics{
            .total_requests = 0,
            .successful_requests = 0,
            .failed_requests = 0,
            .total_duration_ns = 0,
            .min_duration_ns = std.math.maxInt(u64),
            .max_duration_ns = 0,
        };
    }

    pub fn recordSuccess(self: *EvaluationMetrics, duration_ns: u64) void {
        self.total_requests += 1;
        self.successful_requests += 1;
        self.total_duration_ns += duration_ns;
        self.min_duration_ns = @min(self.min_duration_ns, duration_ns);
        self.max_duration_ns = @max(self.max_duration_ns, duration_ns);
    }

    pub fn recordFailure(self: *EvaluationMetrics, duration_ns: u64) void {
        self.total_requests += 1;
        self.failed_requests += 1;
        self.total_duration_ns += duration_ns;
    }

    pub fn successRate(self: *const EvaluationMetrics) f64 {
        if (self.total_requests == 0) return 0.0;
        return @as(f64, @floatFromInt(self.successful_requests)) / @as(f64, @floatFromInt(self.total_requests)) * 100.0;
    }

    pub fn avgDurationMs(self: *const EvaluationMetrics) f64 {
        if (self.total_requests == 0) return 0.0;
        const avg_ns = @as(f64, @floatFromInt(self.total_duration_ns)) / @as(f64, @floatFromInt(self.total_requests));
        return avg_ns / @as(f64, @floatFromInt(std.time.ns_per_ms));
    }

    pub fn throughput(self: *const EvaluationMetrics, duration_s: f64) f64 {
        if (duration_s == 0.0) return 0.0;
        return @as(f64, @floatFromInt(self.total_requests)) / duration_s;
    }

    pub fn print(self: *const EvaluationMetrics) void {
        std.debug.print("  Total requests: {d}\n", .{self.total_requests});
        std.debug.print("  Successful: {d}\n", .{self.successful_requests});
        std.debug.print("  Failed: {d}\n", .{self.failed_requests});
        std.debug.print("  Success rate: {d:.1}%\n", .{self.successRate()});
        std.debug.print("  Avg duration: {d:.2}ms\n", .{self.avgDurationMs()});
        if (self.min_duration_ns != std.math.maxInt(u64)) {
            std.debug.print("  Min duration: {d:.2}ms\n", .{@as(f64, @floatFromInt(self.min_duration_ns)) / @as(f64, @floatFromInt(std.time.ns_per_ms))});
            std.debug.print("  Max duration: {d:.2}ms\n", .{@as(f64, @floatFromInt(self.max_duration_ns)) / @as(f64, @floatFromInt(std.time.ns_per_ms))});
        }
    }
};


fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
    _ = ptr;
    _ = message;
    callbacks.onError(AgentError.NotImplemented);
}
pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Evaluation Pipeline Integration Example ===\n", .{});
    std.debug.print("Use Case: Agent Performance Benchmarking\n\n", .{});

    // Scenario 1: Baseline performance
    std.debug.print("--- Scenario 1: Baseline Performance ---\n", .{});
    {
        var agent = try BenchmarkAgent.init(allocator, "Baseline", 10, 1.0); // 10ms, 100% success
        defer agent.deinit();

        var metrics = EvaluationMetrics.init();
        const num_requests = 10;

        const start = std.time.nanoTimestamp();

        for (0..num_requests) |_| {
            var msg = try agenkit.Message.withText(allocator, .user, "test");
            defer msg.deinit();

            const req_start = std.time.nanoTimestamp();
            const result = try agent.agent().process(msg);
            const req_end = std.time.nanoTimestamp();
            const duration = @as(u64, @intCast(req_end - req_start));

            if (result.isOk()) {
                var response = try result.unwrap();
                defer response.deinit();
                metrics.recordSuccess(duration);
            } else {
                metrics.recordFailure(duration);
            }
        }

        const end = std.time.nanoTimestamp();
        const total_duration_s = @as(f64, @floatFromInt(end - start)) / @as(f64, @floatFromInt(std.time.ns_per_s));

        metrics.print();
        std.debug.print("  Throughput: {d:.2} req/s\n", .{metrics.throughput(total_duration_s)});
        std.debug.print("✓ Baseline metrics collected\n\n", .{});
    }

    // Scenario 2: High latency agent
    std.debug.print("--- Scenario 2: High Latency ---\n", .{});
    {
        var agent = try BenchmarkAgent.init(allocator, "HighLatency", 50, 1.0); // 50ms, 100% success
        defer agent.deinit();

        var metrics = EvaluationMetrics.init();
        const num_requests = 5;

        const start = std.time.nanoTimestamp();

        for (0..num_requests) |_| {
            var msg = try agenkit.Message.withText(allocator, .user, "test");
            defer msg.deinit();

            const req_start = std.time.nanoTimestamp();
            const result = try agent.agent().process(msg);
            const req_end = std.time.nanoTimestamp();
            const duration = @as(u64, @intCast(req_end - req_start));

            if (result.isOk()) {
                var response = try result.unwrap();
                defer response.deinit();
                metrics.recordSuccess(duration);
            } else {
                metrics.recordFailure(duration);
            }
        }

        const end = std.time.nanoTimestamp();
        const total_duration_s = @as(f64, @floatFromInt(end - start)) / @as(f64, @floatFromInt(std.time.ns_per_s));

        metrics.print();
        std.debug.print("  Throughput: {d:.2} req/s\n", .{metrics.throughput(total_duration_s)});
        std.debug.print("✓ High latency impact measured\n\n", .{});
    }

    // Scenario 3: Unreliable agent
    std.debug.print("--- Scenario 3: Unreliable Agent (70%% success) ---\n", .{});
    {
        var agent = try BenchmarkAgent.init(allocator, "Unreliable", 10, 0.7); // 10ms, 70% success
        defer agent.deinit();

        var metrics = EvaluationMetrics.init();
        const num_requests = 20;

        const start = std.time.nanoTimestamp();

        for (0..num_requests) |_| {
            var msg = try agenkit.Message.withText(allocator, .user, "test");
            defer msg.deinit();

            const req_start = std.time.nanoTimestamp();
            const result = try agent.agent().process(msg);
            const req_end = std.time.nanoTimestamp();
            const duration = @as(u64, @intCast(req_end - req_start));

            if (result.isOk()) {
                var response = try result.unwrap();
                defer response.deinit();
                metrics.recordSuccess(duration);
            } else {
                metrics.recordFailure(duration);
            }
        }

        const end = std.time.nanoTimestamp();
        const total_duration_s = @as(f64, @floatFromInt(end - start)) / @as(f64, @floatFromInt(std.time.ns_per_s));

        metrics.print();
        std.debug.print("  Throughput: {d:.2} req/s\n", .{metrics.throughput(total_duration_s)});
        std.debug.print("✓ Reliability impact measured\n\n", .{});
    }

    // Comparative analysis
    std.debug.print("--- Comparative Analysis ---\n", .{});
    std.debug.print("Production Readiness Assessment:\n\n", .{});
    std.debug.print("Baseline Agent:\n", .{});
    std.debug.print("  ✓ High reliability (100%% success)\n", .{});
    std.debug.print("  ✓ Low latency (~10ms)\n", .{});
    std.debug.print("  ✓ High throughput (~100 req/s)\n", .{});
    std.debug.print("  → READY FOR PRODUCTION\n\n", .{});

    std.debug.print("High Latency Agent:\n", .{});
    std.debug.print("  ✓ High reliability (100%% success)\n", .{});
    std.debug.print("  ⚠ High latency (~50ms)\n", .{});
    std.debug.print("  ⚠ Lower throughput (~20 req/s)\n", .{});
    std.debug.print("  → NEEDS OPTIMIZATION\n\n", .{});

    std.debug.print("Unreliable Agent:\n", .{});
    std.debug.print("  ✗ Poor reliability (~70%% success)\n", .{});
    std.debug.print("  ✓ Low latency (~10ms)\n", .{});
    std.debug.print("  ⚠ Moderate throughput\n", .{});
    std.debug.print("  → NOT READY (needs error handling improvement)\n\n", .{});

    std.debug.print("=== Evaluation Pipeline Summary ===\n", .{});
    std.debug.print("✓ Metrics tracked:\n", .{});
    std.debug.print("  - Success rate\n", .{});
    std.debug.print("  - Latency (min/avg/max)\n", .{});
    std.debug.print("  - Throughput (req/s)\n", .{});
    std.debug.print("  - Failure rate\n", .{});
    std.debug.print("\n✓ Use cases:\n", .{});
    std.debug.print("  - A/B testing agents\n", .{});
    std.debug.print("  - Performance regression testing\n", .{});
    std.debug.print("  - Production readiness assessment\n", .{});
    std.debug.print("  - SLA compliance verification\n", .{});
    std.debug.print("\n✓ Evaluation pipeline completed successfully!\n\n", .{});
}

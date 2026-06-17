/// Example demonstrating BatchingMiddleware usage
///
/// Shows how to:
/// 1. Configure batching behavior
/// 2. Process concurrent requests as batches
/// 3. Track batching metrics
/// 4. Observe batch size and wait time

const std = @import("std");
const agktime = @import("../../src/time_compat.zig");
const agenkit = @import("agenkit");

// Slow agent that simulates processing time
const SlowAgent = struct {
    allocator: std.mem.Allocator,
    call_count: std.atomic.Value(u32),
    delay_ms: u64,

    pub fn init(allocator: std.mem.Allocator, delay_ms: u64) !*SlowAgent {
        const self = try allocator.create(SlowAgent);
        self.* = SlowAgent{
            .allocator = allocator,
            .call_count = std.atomic.Value(u32).init(0),
            .delay_ms = delay_ms,
        };
        return self;
    }

    pub fn agent(self: *SlowAgent) agenkit.Agent {
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
        _ = ptr;
        return "slow_agent";
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "slow";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *SlowAgent = @ptrCast(@alignCast(ptr));

        const count = self.call_count.fetchAdd(1, .monotonic);
        std.debug.print("  [Slow Agent] Processing request #{d}\\n", .{count + 1});

        // Simulate slow processing
        agktime.sleep(self.delay_ms * std.time.ns_per_ms);

        return agenkit.Result{ .ok = message };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        _ = ptr;
        return agenkit.createDefaultIntrospectionResult(allocator, "slow_agent", &.{"slow"});
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *SlowAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};

// Thread function for concurrent requests
fn sendRequest(args: struct {
    agent: agenkit.Agent,
    allocator: std.mem.Allocator,
    id: u32,
}) void {
    const text = std.fmt.allocPrint(args.allocator, "Request {d}", .{args.id}) catch return;
    defer args.allocator.free(text);

    var message = agenkit.Message.withText(args.allocator, .user, text) catch return;
    defer message.deinit();

    const result = args.agent.process(message) catch |err| {
        std.debug.print("  Thread {d}: ERROR - {}\n", .{ args.id, err });
        return;
    };
    var response = result.unwrap() catch return;
    response.deinit();

    std.debug.print("  Thread {d}: SUCCESS\n", .{args.id});
}


fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
    _ = ptr;
    _ = message;
    callbacks.onError(AgentError.NotImplemented);
}
pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Batching Middleware Example ===\n\n", .{});

    // Example 1: Basic batching
    std.debug.print("Example 1: Basic Batching (batch size = 5)\n", .{});
    try basicBatchingExample(allocator);

    std.debug.print("\n", .{});

    // Example 2: Wait time batching
    std.debug.print("Example 2: Wait Time Batching (100ms timeout)\n", .{});
    try waitTimeBatchingExample(allocator);

    std.debug.print("\n", .{});

    // Example 3: Metrics tracking
    std.debug.print("Example 3: Metrics Tracking\n", .{});
    try metricsExample(allocator);

    std.debug.print("\n=== All examples completed successfully ===\n", .{});
}

fn basicBatchingExample(allocator: std.mem.Allocator) !void {
    // Create slow agent (50ms per request)
    var slow = try SlowAgent.init(allocator, 50);
    defer slow.agent().deinit();

    // Configure batching
    const config = agenkit.middleware.BatchingConfig{
        .max_batch_size = 5,
        .max_wait_time_ms = 1000,
        .max_queue_size = 100,
    };
    var batching_agent = try agenkit.middleware.BatchingDecorator.init(allocator, slow.agent(), config);
    defer batching_agent.agent().deinit();

    // Start batch processor
    try batching_agent.start();
    defer batching_agent.stop();

    std.debug.print("  Sending 10 requests concurrently...\n", .{});
    const start_time = agktime.milliTimestamp();

    // Spawn 10 concurrent threads
    var threads: [10]std.Thread = undefined;
    var i: u32 = 0;
    while (i < 10) : (i += 1) {
        threads[i] = try std.Thread.spawn(.{}, sendRequest, .{.{
            .agent = batching_agent.agent(),
            .allocator = allocator,
            .id = i + 1,
        }});
    }

    // Wait for all threads
    for (threads) |thread| {
        thread.join();
    }

    const elapsed_ms = agktime.milliTimestamp() - start_time;
    std.debug.print("\n  Completed in {d}ms\n", .{elapsed_ms});

    const metrics = batching_agent.metrics();
    std.debug.print("  Metrics:\n", .{});
    std.debug.print("    Total requests:      {d}\n", .{metrics.total_requests});
    std.debug.print("    Total batches:       {d}\n", .{metrics.total_batches});
    std.debug.print("    Avg batch size:      {d:.1}\n", .{metrics.avgBatchSize().?});
    std.debug.print("    Agent called only {} times (vs 10 requests)\n", .{metrics.total_batches});
}

fn waitTimeBatchingExample(allocator: std.mem.Allocator) !void {
    // Create slow agent (20ms per request)
    var slow = try SlowAgent.init(allocator, 20);
    defer slow.agent().deinit();

    // Configure batching with wait time
    const config = agenkit.middleware.BatchingConfig{
        .max_batch_size = 10,
        .max_wait_time_ms = 100, // Wait up to 100ms for batch
        .max_queue_size = 100,
    };
    var batching_agent = try agenkit.middleware.BatchingDecorator.init(allocator, slow.agent(), config);
    defer batching_agent.agent().deinit();

    // Start batch processor
    try batching_agent.start();
    defer batching_agent.stop();

    std.debug.print("  Sending 3 requests with delays...\n", .{});
    const start_time = agktime.milliTimestamp();

    // Send 3 requests with 50ms delays between them
    var i: u32 = 0;
    while (i < 3) : (i += 1) {
        const thread = try std.Thread.spawn(.{}, sendRequest, .{.{
            .agent = batching_agent.agent(),
            .allocator = allocator,
            .id = i + 1,
        }});
        thread.detach();

        if (i < 2) {
            agktime.sleep(50 * std.time.ns_per_ms);
        }
    }

    // Wait for processing
    agktime.sleep(300 * std.time.ns_per_ms);

    const elapsed_ms = agktime.milliTimestamp() - start_time;
    std.debug.print("\n  Completed in {d}ms\n", .{elapsed_ms});

    const metrics = batching_agent.metrics();
    std.debug.print("  Metrics:\n", .{});
    std.debug.print("    Total requests:      {d}\n", .{metrics.total_requests});
    std.debug.print("    Total batches:       {d}\n", .{metrics.total_batches});
    std.debug.print("    Avg wait time:       {d:.1}ms\n", .{metrics.avgWaitTime().?});
    std.debug.print("    Batch triggered by timeout (100ms wait)\n", .{});
}

fn metricsExample(allocator: std.mem.Allocator) !void {
    // Create slow agent (30ms per request)
    var slow = try SlowAgent.init(allocator, 30);
    defer slow.agent().deinit();

    // Configure batching
    const config = agenkit.middleware.BatchingConfig{
        .max_batch_size = 5,
        .max_wait_time_ms = 200,
        .max_queue_size = 100,
    };
    var batching_agent = try agenkit.middleware.BatchingDecorator.init(allocator, slow.agent(), config);
    defer batching_agent.agent().deinit();

    // Start batch processor
    try batching_agent.start();
    defer batching_agent.stop();

    std.debug.print("  Sending 25 requests in 5 waves...\n", .{});
    const start_time = agktime.milliTimestamp();

    // Send 5 waves of 5 requests
    var wave: u32 = 0;
    while (wave < 5) : (wave += 1) {
        var i: u32 = 0;
        while (i < 5) : (i += 1) {
            const id = wave * 5 + i + 1;
            const thread = try std.Thread.spawn(.{}, sendRequest, .{.{
                .agent = batching_agent.agent(),
                .allocator = allocator,
                .id = id,
            }});
            thread.detach();
        }

        // Wait between waves
        if (wave < 4) {
            agktime.sleep(100 * std.time.ns_per_ms);
        }
    }

    // Wait for all processing
    agktime.sleep(500 * std.time.ns_per_ms);

    const elapsed_ms = agktime.milliTimestamp() - start_time;
    const metrics = batching_agent.metrics();

    std.debug.print("\n  Final Metrics:\n", .{});
    std.debug.print("    Total requests:        {d}\n", .{metrics.total_requests});
    std.debug.print("    Total batches:         {d}\n", .{metrics.total_batches});
    std.debug.print("    Successful batches:    {d}\n", .{metrics.successful_batches});
    std.debug.print("    Failed batches:        {d}\n", .{metrics.failed_batches});
    std.debug.print("    Partial batches:       {d}\n", .{metrics.partial_batches});
    std.debug.print("    Min batch size:        {d}\n", .{metrics.min_batch_size.?});
    std.debug.print("    Max batch size:        {d}\n", .{metrics.max_batch_size.?});
    std.debug.print("    Avg batch size:        {d:.2}\n", .{metrics.avgBatchSize().?});
    std.debug.print("    Avg wait time:         {d:.1}ms\n", .{metrics.avgWaitTime().?});
    std.debug.print("    Total time:            {d}ms\n", .{elapsed_ms});
    std.debug.print("\n    Throughput improvement: {d:.1}x\n", .{
        @as(f64, @floatFromInt(metrics.total_requests)) / @as(f64, @floatFromInt(metrics.total_batches)),
    });
}

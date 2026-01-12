/// Example demonstrating TimeoutMiddleware usage
///
/// Shows how to:
/// 1. Configure timeout behavior
/// 2. Use method-specific timeouts
/// 3. Track timeout metrics
/// 4. Handle timeout errors

const std = @import("std");
const agenkit = @import("agenkit");

// Slow agent that takes variable time to respond
const SlowAgent = struct {
    allocator: std.mem.Allocator,
    delay_ms: u64,

    pub fn init(allocator: std.mem.Allocator, delay_ms: u64) !*SlowAgent {
        const self = try allocator.create(SlowAgent);
        self.* = SlowAgent{
            .allocator = allocator,
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

        // Check if message has custom delay in metadata
        const delay_ms = if (message.metadata.get("delay_ms")) |delay_str|
            std.fmt.parseInt(u64, delay_str, 10) catch self.delay_ms
        else
            self.delay_ms;

        std.debug.print("  [Slow Agent] Processing (will take {d}ms)...\n", .{delay_ms});

        // Simulate slow processing
        std.time.sleep(delay_ms * std.time.ns_per_ms);

        std.debug.print("  [Slow Agent] Done!\n", .{});

        // Echo back the message
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

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Timeout Middleware Example ===\n\n", .{});

    // Example 1: Basic timeout
    std.debug.print("Example 1: Basic Timeout (1s timeout, 500ms operation)\n", .{});
    try basicTimeoutExample(allocator);

    std.debug.print("\n", .{});

    // Example 2: Timeout triggers
    std.debug.print("Example 2: Timeout Triggers (500ms timeout, 1s operation)\n", .{});
    try timeoutTriggersExample(allocator);

    std.debug.print("\n", .{});

    // Example 3: Method-specific timeouts
    std.debug.print("Example 3: Method-Specific Timeouts\n", .{});
    try methodSpecificTimeoutsExample(allocator);

    std.debug.print("\n", .{});

    // Example 4: Metrics tracking
    std.debug.print("Example 4: Metrics Tracking (multiple requests)\n", .{});
    try metricsExample(allocator);

    std.debug.print("\n=== All examples completed successfully ===\n", .{});
}

fn basicTimeoutExample(allocator: std.mem.Allocator) !void {
    // Create a slow agent (500ms delay)
    var slow = try SlowAgent.init(allocator, 500);
    defer slow.agent().deinit();

    // Wrap with timeout middleware (1000ms timeout)
    const config = agenkit.middleware.TimeoutConfig{
        .timeout_ms = 1000,
    };
    var timeout_agent = try agenkit.middleware.TimeoutDecorator.init(allocator, slow.agent(), config);
    defer timeout_agent.agent().deinit();

    // Create a test message
    var message = try agenkit.Message.withText(allocator, .user, "Test message");
    defer message.deinit();

    // Process with timeout (should succeed)
    std.debug.print("  Processing message (should succeed)...\n", .{});
    const result = try timeout_agent.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    const metrics = timeout_agent.metrics();
    std.debug.print("  Result: SUCCESS\n", .{});
    std.debug.print("  Duration: ~500ms (timeout: 1000ms)\n", .{});
    std.debug.print("  Metrics: {d} requests, {d} successful, {d} timed out\n", .{
        metrics.total_requests,
        metrics.successful_requests,
        metrics.timed_out_requests,
    });
}

fn timeoutTriggersExample(allocator: std.mem.Allocator) !void {
    // Create a slow agent (1000ms delay)
    var slow = try SlowAgent.init(allocator, 1000);
    defer slow.agent().deinit();

    // Wrap with timeout middleware (500ms timeout)
    const config = agenkit.middleware.TimeoutConfig{
        .timeout_ms = 500,
    };
    var timeout_agent = try agenkit.middleware.TimeoutDecorator.init(allocator, slow.agent(), config);
    defer timeout_agent.agent().deinit();

    // Create a test message
    var message = try agenkit.Message.withText(allocator, .user, "Test message");
    defer message.deinit();

    // Process with timeout (should timeout)
    std.debug.print("  Processing message (should timeout)...\n", .{});
    const result = timeout_agent.agent().process(message);

    if (result) |_| {
        std.debug.print("  ERROR: Should have timed out!\n", .{});
        return error.TestFailed;
    } else |err| {
        if (err == agenkit.AgentError.Timeout) {
            std.debug.print("  Result: TIMEOUT (as expected)\n", .{});

            const metrics = timeout_agent.metrics();
            std.debug.print("  Metrics: {d} requests, {d} timed out\n", .{
                metrics.total_requests,
                metrics.timed_out_requests,
            });
        } else {
            return err;
        }
    }
}

fn methodSpecificTimeoutsExample(allocator: std.mem.Allocator) !void {
    // Create a slow agent
    var slow = try SlowAgent.init(allocator, 100);
    defer slow.agent().deinit();

    // Configure method-specific timeouts
    const method_timeouts = [_]agenkit.middleware.MethodTimeout{
        .{ .name = "fast", .timeout_ms = 200 },
        .{ .name = "slow", .timeout_ms = 2000 },
    };

    const config = agenkit.middleware.TimeoutConfig{
        .timeout_ms = 500, // default
        .method_timeouts = &method_timeouts,
    };
    var timeout_agent = try agenkit.middleware.TimeoutDecorator.init(allocator, slow.agent(), config);
    defer timeout_agent.agent().deinit();

    // Test "fast" method (200ms timeout)
    std.debug.print("  Testing 'fast' method (200ms timeout, 100ms operation)...\n", .{});
    {
        var message = try agenkit.Message.withText(allocator, .user, "Fast operation");
        defer message.deinit();
        try message.metadata.put("method", "fast");

        const result = try timeout_agent.agent().process(message);
        var response = try result.unwrap();
        response.deinit();
        std.debug.print("    Result: SUCCESS\n", .{});
    }

    // Test "slow" method (2000ms timeout)
    std.debug.print("  Testing 'slow' method (2000ms timeout, 1500ms operation)...\n", .{});
    {
        var message = try agenkit.Message.withText(allocator, .user, "Slow operation");
        defer message.deinit();
        try message.metadata.put("method", "slow");
        try message.metadata.put("delay_ms", "1500");

        const result = try timeout_agent.agent().process(message);
        var response = try result.unwrap();
        response.deinit();
        std.debug.print("    Result: SUCCESS\n", .{});
    }

    const metrics = timeout_agent.metrics();
    std.debug.print("  Total requests: {d}, all successful: {d}\n", .{
        metrics.total_requests,
        metrics.successful_requests,
    });
}

fn metricsExample(allocator: std.mem.Allocator) !void {
    // Create a slow agent
    var slow = try SlowAgent.init(allocator, 100);
    defer slow.agent().deinit();

    // Configure timeout
    const config = agenkit.middleware.TimeoutConfig{
        .timeout_ms = 500,
    };
    var timeout_agent = try agenkit.middleware.TimeoutDecorator.init(allocator, slow.agent(), config);
    defer timeout_agent.agent().deinit();

    // Process 10 messages with varying delays
    std.debug.print("  Processing 10 messages with varying delays...\n", .{});
    const delays = [_]u64{ 100, 200, 150, 300, 400, 100, 600, 200, 250, 700 };

    var i: usize = 0;
    while (i < delays.len) : (i += 1) {
        var message = try agenkit.Message.withText(allocator, .user, "Test message");
        defer message.deinit();

        const delay_str = try std.fmt.allocPrint(allocator, "{d}", .{delays[i]});
        defer allocator.free(delay_str);
        try message.metadata.put("delay_ms", delay_str);

        const result = timeout_agent.agent().process(message) catch |err| {
            if (err == agenkit.AgentError.Timeout) {
                std.debug.print("    Message {d}: TIMEOUT (delay: {d}ms)\n", .{ i + 1, delays[i] });
                continue;
            }
            return err;
        };
        var response = try result.unwrap();
        response.deinit();
    }

    // Print final metrics
    const metrics = timeout_agent.metrics();
    std.debug.print("\n  Final Metrics:\n", .{});
    std.debug.print("    Total requests:      {d}\n", .{metrics.total_requests});
    std.debug.print("    Successful:          {d}\n", .{metrics.successful_requests});
    std.debug.print("    Timed out:           {d}\n", .{metrics.timed_out_requests});
    std.debug.print("    Failed:              {d}\n", .{metrics.failed_requests});

    if (metrics.min_duration_ms) |min| {
        std.debug.print("    Min duration:        {d}ms\n", .{min});
    }
    if (metrics.max_duration_ms) |max| {
        std.debug.print("    Max duration:        {d}ms\n", .{max});
    }
    if (metrics.avgDuration()) |avg| {
        std.debug.print("    Avg duration:        {d:.0}ms\n", .{avg});
    }
    if (metrics.timeoutRate()) |rate| {
        std.debug.print("    Timeout rate:        {d:.1}%\n", .{rate});
    }
    if (metrics.errorRate()) |err_rate| {
        std.debug.print("    Error rate:          {d:.1}%\n", .{err_rate});
    }
}

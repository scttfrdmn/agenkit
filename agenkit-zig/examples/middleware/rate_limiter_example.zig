/// Example demonstrating RateLimiterMiddleware usage
///
/// Shows how to:
/// 1. Configure token bucket rate limiting
/// 2. Handle burst traffic with capacity
/// 3. Track rate limiter metrics
/// 4. Observe token refill behavior

const std = @import("std");
const agenkit = @import("agenkit");

// Echo agent that simply returns the message
const EchoAgent = struct {
    allocator: std.mem.Allocator,
    request_count: std.atomic.Value(u32),

    pub fn init(allocator: std.mem.Allocator) !*EchoAgent {
        const self = try allocator.create(EchoAgent);
        self.* = EchoAgent{
            .allocator = allocator,
            .request_count = std.atomic.Value(u32).init(0),
        };
        return self;
    }

    pub fn agent(self: *EchoAgent) agenkit.Agent {
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
        return "echo_agent";
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "echo";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *EchoAgent = @ptrCast(@alignCast(ptr));

        const count = self.request_count.fetchAdd(1, .monotonic);
        std.debug.print("  [Echo Agent] Processing request #{d}\\n", .{count + 1});

        // Echo back the message
        return agenkit.Result{ .ok = message };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        _ = ptr;
        return agenkit.createDefaultIntrospectionResult(allocator, "echo_agent", &.{"echo"});
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *EchoAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\\n=== Rate Limiter Middleware Example ===\\n\\n", .{});

    // Example 1: Basic rate limiting
    std.debug.print("Example 1: Basic Rate Limiting (10 req/sec)\\n", .{});
    try basicRateLimitingExample(allocator);

    std.debug.print("\\n", .{});

    // Example 2: Burst capacity
    std.debug.print("Example 2: Burst Capacity (20 req/sec, capacity 50)\\n", .{});
    try burstCapacityExample(allocator);

    std.debug.print("\\n", .{});

    // Example 3: Token refill behavior
    std.debug.print("Example 3: Token Refill (5 req/sec)\\n", .{});
    try tokenRefillExample(allocator);

    std.debug.print("\\n", .{});

    // Example 4: Metrics tracking
    std.debug.print("Example 4: Metrics Tracking\\n", .{});
    try metricsExample(allocator);

    std.debug.print("\\n=== All examples completed successfully ===\\n", .{});
}

fn basicRateLimitingExample(allocator: std.mem.Allocator) !void {
    // Create echo agent
    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    // Configure rate limiter: 10 requests/second
    const config = agenkit.middleware.RateLimiterConfig{
        .rate = 10.0,
        .capacity = 10,
        .tokens_per_request = 1,
    };
    var limiter = try agenkit.middleware.RateLimiterDecorator.init(allocator, echo.agent(), config);
    defer limiter.agent().deinit();

    var message = try agenkit.Message.withText(allocator, .user, "Test message");
    defer message.deinit();

    std.debug.print("  Sending 5 requests (should succeed immediately)...\\n", .{});
    const start_time = std.time.milliTimestamp();

    var i: u32 = 0;
    while (i < 5) : (i += 1) {
        const result = try limiter.agent().process(message);
        var response = try result.unwrap();
        response.deinit();
        std.debug.print("    Request {d}: SUCCESS\\n", .{i + 1});
    }

    const elapsed_ms = std.time.milliTimestamp() - start_time;
    std.debug.print("  Completed in {d}ms\\n", .{elapsed_ms});

    const metrics = limiter.metrics();
    std.debug.print("  Metrics: {d} total, {d} allowed, {d} rejected\\n", .{
        metrics.total_requests,
        metrics.allowed_requests,
        metrics.rejected_requests,
    });
    std.debug.print("  Current tokens: {d:.2}\\n", .{metrics.current_tokens});
}

fn burstCapacityExample(allocator: std.mem.Allocator) !void {
    // Create echo agent
    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    // Configure rate limiter with burst capacity
    const config = agenkit.middleware.RateLimiterConfig{
        .rate = 20.0, // 20 tokens/sec
        .capacity = 50, // Can handle burst of 50 requests
        .tokens_per_request = 1,
    };
    var limiter = try agenkit.middleware.RateLimiterDecorator.init(allocator, echo.agent(), config);
    defer limiter.agent().deinit();

    var message = try agenkit.Message.withText(allocator, .user, "Test message");
    defer message.deinit();

    std.debug.print("  Sending 30 requests in burst...\\n", .{});
    const start_time = std.time.milliTimestamp();

    var i: u32 = 0;
    while (i < 30) : (i += 1) {
        const result = try limiter.agent().process(message);
        var response = try result.unwrap();
        response.deinit();

        if (i < 5 or i >= 25) {
            std.debug.print("    Request {d}: SUCCESS\\n", .{i + 1});
        } else if (i == 5) {
            std.debug.print("    ... (requests 6-25) ...\\n", .{});
        }
    }

    const elapsed_ms = std.time.milliTimestamp() - start_time;
    std.debug.print("  Completed in {d}ms\\n", .{elapsed_ms});

    const metrics = limiter.metrics();
    std.debug.print("  Metrics: {d} total, {d} allowed\\n", .{
        metrics.total_requests,
        metrics.allowed_requests,
    });
    std.debug.print("  Current tokens: {d:.2}\\n", .{metrics.current_tokens});
}

fn tokenRefillExample(allocator: std.mem.Allocator) !void {
    // Create echo agent
    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    // Configure slow rate: 5 requests/second
    const config = agenkit.middleware.RateLimiterConfig{
        .rate = 5.0,
        .capacity = 10,
        .tokens_per_request = 1,
    };
    var limiter = try agenkit.middleware.RateLimiterDecorator.init(allocator, echo.agent(), config);
    defer limiter.agent().deinit();

    var message = try agenkit.Message.withText(allocator, .user, "Test message");
    defer message.deinit();

    // Exhaust tokens
    std.debug.print("  Exhausting tokens (10 requests)...\\n", .{});
    var i: u32 = 0;
    while (i < 10) : (i += 1) {
        const result = try limiter.agent().process(message);
        var response = try result.unwrap();
        response.deinit();
    }

    var metrics = limiter.metrics();
    std.debug.print("    Tokens after burst: {d:.2}\\n", .{metrics.current_tokens});

    // Wait for refill
    std.debug.print("  Waiting 1 second for refill...\\n", .{});
    std.time.sleep(1000 * std.time.ns_per_ms);

    // Send one more request (should wait for tokens)
    std.debug.print("  Sending request (will wait for tokens)...\\n", .{});
    const start_time = std.time.milliTimestamp();
    const result = try limiter.agent().process(message);
    const elapsed_ms = std.time.milliTimestamp() - start_time;
    var response = try result.unwrap();
    response.deinit();

    std.debug.print("    Request completed after {d}ms\\n", .{elapsed_ms});

    metrics = limiter.metrics();
    std.debug.print("  Final tokens: {d:.2}\\n", .{metrics.current_tokens});
    std.debug.print("  Total wait time: {d}ms\\n", .{metrics.total_wait_time_ms});
}

fn metricsExample(allocator: std.mem.Allocator) !void {
    // Create echo agent
    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    // Configure rate limiter
    const config = agenkit.middleware.RateLimiterConfig{
        .rate = 50.0, // 50 tokens/sec
        .capacity = 100,
        .tokens_per_request = 1,
    };
    var limiter = try agenkit.middleware.RateLimiterDecorator.init(allocator, echo.agent(), config);
    defer limiter.agent().deinit();

    var message = try agenkit.Message.withText(allocator, .user, "Test message");
    defer message.deinit();

    // Send 150 requests
    std.debug.print("  Sending 150 requests...\\n", .{});
    const start_time = std.time.milliTimestamp();

    var i: u32 = 0;
    while (i < 150) : (i += 1) {
        const result = try limiter.agent().process(message);
        var response = try result.unwrap();
        response.deinit();

        // Print progress every 50 requests
        if ((i + 1) % 50 == 0) {
            const elapsed_ms = std.time.milliTimestamp() - start_time;
            std.debug.print("    Completed {d} requests in {d}ms\\n", .{ i + 1, elapsed_ms });
        }
    }

    const total_time = std.time.milliTimestamp() - start_time;
    const metrics = limiter.metrics();

    std.debug.print("\\n  Final Metrics:\\n", .{});
    std.debug.print("    Total requests:      {d}\\n", .{metrics.total_requests});
    std.debug.print("    Allowed requests:    {d}\\n", .{metrics.allowed_requests});
    std.debug.print("    Rejected requests:   {d}\\n", .{metrics.rejected_requests});
    std.debug.print("    Total wait time:     {d}ms\\n", .{metrics.total_wait_time_ms});
    std.debug.print("    Current tokens:      {d:.2}\\n", .{metrics.current_tokens});
    std.debug.print("    Total elapsed time:  {d}ms\\n", .{total_time});

    if (metrics.avgWaitTime()) |avg| {
        std.debug.print("    Avg wait time:       {d:.2}ms\\n", .{avg});
    }
    if (metrics.rejectionRate()) |rate| {
        std.debug.print("    Rejection rate:      {d:.2}%\\n", .{rate});
    }

    // Calculate actual rate
    const actual_rate = @as(f64, @floatFromInt(metrics.allowed_requests)) / (@as(f64, @floatFromInt(total_time)) / 1000.0);
    std.debug.print("    Actual rate:         {d:.1} req/sec\\n", .{actual_rate});
}

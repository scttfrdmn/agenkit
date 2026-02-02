/// Example demonstrating RetryMiddleware usage
///
/// Shows how to:
/// 1. Configure retry behavior
/// 2. Wrap an agent with retry logic
/// 3. Track retry metrics
/// 4. Use custom retry predicates

const std = @import("std");
const agenkit = @import("agenkit");

// Flaky agent that fails intermittently
const FlakyAgent = struct {
    allocator: std.mem.Allocator,
    failure_rate: f64,  // 0.0 to 1.0
    call_count: std.atomic.Value(u32),

    pub fn init(allocator: std.mem.Allocator, failure_rate: f64) !*FlakyAgent {
        const self = try allocator.create(FlakyAgent);
        self.* = FlakyAgent{
            .allocator = allocator,
            .failure_rate = failure_rate,
            .call_count = std.atomic.Value(u32).init(0),
        };
        return self;
    }

    pub fn agent(self: *FlakyAgent) agenkit.Agent {
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
        return "flaky_agent";
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "flaky";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *FlakyAgent = @ptrCast(@alignCast(ptr));

        const count = self.call_count.fetchAdd(1, .monotonic);

        // Generate random number to determine if we fail
        const rand = std.crypto.random.float(f64);

        if (rand < self.failure_rate) {
            std.debug.print("  [Flaky Agent] Call #{d}: FAILED (random={d:.2})\n", .{count + 1, rand});
            return error.ProcessingFailed;
        }

        std.debug.print("  [Flaky Agent] Call #{d}: SUCCESS (random={d:.2})\n", .{count + 1, rand});

        // Echo back the message
        return agenkit.Result{ .ok = message };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        const self: *FlakyAgent = @ptrCast(@alignCast(ptr));
        return agenkit.createDefaultIntrospectionResult(allocator, "flaky_agent", &.{"flaky"});
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *FlakyAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
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

    std.debug.print("\n=== Retry Middleware Example ===\n\n", .{});

    // Example 1: Basic retry with default config
    std.debug.print("Example 1: Basic Retry (70% failure rate, 3 max attempts)\n", .{});
    try basicRetryExample(allocator);

    std.debug.print("\n", .{});

    // Example 2: Custom retry configuration
    std.debug.print("Example 2: Custom Config (90% failure rate, 5 attempts, fast backoff)\n", .{});
    try customConfigExample(allocator);

    std.debug.print("\n", .{});

    // Example 3: Metrics tracking
    std.debug.print("Example 3: Metrics Tracking (multiple requests)\n", .{});
    try metricsExample(allocator);

    std.debug.print("\n=== All examples completed successfully ===\n", .{});
}

fn basicRetryExample(allocator: std.mem.Allocator) !void {
    // Create a flaky agent (70% failure rate)
    var flaky = try FlakyAgent.init(allocator, 0.7);
    defer flaky.agent().deinit();

    // Wrap with retry middleware (default config)
    const config = agenkit.middleware.RetryConfig{};
    var retry = try agenkit.middleware.RetryDecorator.init(allocator, flaky.agent(), config);
    defer retry.agent().deinit();

    // Create a test message
    var message = try agenkit.Message.withText(allocator, .user, "Test message");
    defer message.deinit();

    // Process with retry
    std.debug.print("  Processing message with retry...\n", .{});
    const result = try retry.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    const metrics = retry.metrics();
    std.debug.print("  Result: SUCCESS\n", .{});
    std.debug.print("  Metrics: {d} attempts, {d} retries\n", .{metrics.total_attempts, metrics.total_retries});
}

fn customConfigExample(allocator: std.mem.Allocator) !void {
    // Create a very flaky agent (90% failure rate)
    var flaky = try FlakyAgent.init(allocator, 0.9);
    defer flaky.agent().deinit();

    // Custom config: more attempts, faster backoff
    const config = agenkit.middleware.RetryConfig{
        .max_retries = 5,
        .initial_delay_ms = 10,  // Fast for demo
        .max_delay_ms = 100,
        .multiplier = 1.5,
    };
    var retry = try agenkit.middleware.RetryDecorator.init(allocator, flaky.agent(), config);
    defer retry.agent().deinit();

    // Create a test message
    var message = try agenkit.Message.withText(allocator, .user, "Test message");
    defer message.deinit();

    // Process with retry
    std.debug.print("  Processing message with custom config...\n", .{});
    const result = try retry.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    const metrics = retry.metrics();
    std.debug.print("  Result: SUCCESS\n", .{});
    std.debug.print("  Metrics: {d} attempts, {d} retries\n", .{metrics.total_attempts, metrics.total_retries});
}

fn metricsExample(allocator: std.mem.Allocator) !void {
    // Create a moderately flaky agent (50% failure rate)
    var flaky = try FlakyAgent.init(allocator, 0.5);
    defer flaky.agent().deinit();

    // Configure retry
    const config = agenkit.middleware.RetryConfig{
        .max_retries = 3,
        .initial_delay_ms = 10,  // Fast for demo
        .max_delay_ms = 100,
        .multiplier = 2.0,
    };
    var retry = try agenkit.middleware.RetryDecorator.init(allocator, flaky.agent(), config);
    defer retry.agent().deinit();

    // Process 10 messages
    std.debug.print("  Processing 10 messages...\n", .{});
    var i: u32 = 0;
    while (i < 10) : (i += 1) {
        var message = try agenkit.Message.withText(allocator, .user, "Test message");
        defer message.deinit();

        const result = retry.agent().process(message) catch |err| {
            std.debug.print("  Message {d}: FAILED after all retries ({s})\n", .{i + 1, @errorName(err)});
            continue;
        };
        var response = try result.unwrap();
        response.deinit();
    }

    // Print final metrics
    const metrics = retry.metrics();
    std.debug.print("\n  Final Metrics:\n", .{});
    std.debug.print("    Total attempts:           {d}\n", .{metrics.total_attempts});
    std.debug.print("    Successful first attempt: {d}\n", .{metrics.successful_first_attempt});
    std.debug.print("    Successful on retry:      {d}\n", .{metrics.successful_on_retry});
    std.debug.print("    Failed after retries:     {d}\n", .{metrics.failed_after_retries});
    std.debug.print("    Total retries:            {d}\n", .{metrics.total_retries});

    if (metrics.total_attempts > 0) {
        const success_rate = (@as(f64, @floatFromInt(metrics.successful_first_attempt + metrics.successful_on_retry)) / @as(f64, @floatFromInt(10))) * 100.0;
        std.debug.print("    Success rate:             {d:.1}%\n", .{success_rate});
    }
}

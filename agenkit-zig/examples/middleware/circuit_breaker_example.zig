/// Example demonstrating CircuitBreakerMiddleware usage
///
/// Shows how to:
/// 1. Configure circuit breaker behavior
/// 2. Observe state transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
/// 3. Track circuit breaker metrics
/// 4. Handle rejected requests when circuit is open

const std = @import("std");
const agktime = @import("../../src/time_compat.zig");
const agenkit = @import("agenkit");

// Unreliable agent that fails based on configuration
const UnreliableAgent = struct {
    allocator: std.mem.Allocator,
    should_fail: std.atomic.Value(bool),
    call_count: std.atomic.Value(u32),

    pub fn init(allocator: std.mem.Allocator, should_fail: bool) !*UnreliableAgent {
        const self = try allocator.create(UnreliableAgent);
        self.* = UnreliableAgent{
            .allocator = allocator,
            .should_fail = std.atomic.Value(bool).init(should_fail),
            .call_count = std.atomic.Value(u32).init(0),
        };
        return self;
    }

    pub fn setFailure(self: *UnreliableAgent, should_fail: bool) void {
        self.should_fail.store(should_fail, .monotonic);
    }

    pub fn agent(self: *UnreliableAgent) agenkit.Agent {
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
        return "unreliable_agent";
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "unreliable";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *UnreliableAgent = @ptrCast(@alignCast(ptr));

        const count = self.call_count.fetchAdd(1, .monotonic);
        const should_fail = self.should_fail.load(.monotonic);

        if (should_fail) {
            std.debug.print("  [Unreliable Agent] Call #{d}: FAILED\n", .{count + 1});
            return error.ProcessingFailed;
        }

        std.debug.print("  [Unreliable Agent] Call #{d}: SUCCESS\n", .{count + 1});
        return agenkit.Result{ .ok = message };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        _ = ptr;
        return agenkit.createDefaultIntrospectionResult(allocator, "unreliable_agent", &.{"unreliable"});
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *UnreliableAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};


fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
    _ = ptr;
    _ = message;
    callbacks.onError(AgentError.NotImplemented);
}
pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Circuit Breaker Middleware Example ===\n\n", .{});

    // Example 1: Circuit opens after failures
    std.debug.print("Example 1: Circuit Opens After Threshold\n", .{});
    try circuitOpensExample(allocator);

    std.debug.print("\n", .{});

    // Example 2: Circuit recovers (HALF_OPEN → CLOSED)
    std.debug.print("Example 2: Circuit Recovery\n", .{});
    try circuitRecoveryExample(allocator);

    std.debug.print("\n", .{});

    // Example 3: Half-open failure reopens circuit
    std.debug.print("Example 3: Half-Open Failure\n", .{});
    try halfOpenFailureExample(allocator);

    std.debug.print("\n", .{});

    // Example 4: Metrics tracking
    std.debug.print("Example 4: Metrics Tracking\n", .{});
    try metricsExample(allocator);

    std.debug.print("\n=== All examples completed successfully ===\n", .{});
}

fn circuitOpensExample(allocator: std.mem.Allocator) !void {
    // Create an unreliable agent (always fails)
    var unreliable = try UnreliableAgent.init(allocator, true);
    defer unreliable.agent().deinit();

    // Configure circuit breaker (5 failures to open)
    const config = agenkit.middleware.CircuitBreakerConfig{
        .failure_threshold = 5,
        .success_threshold = 2,
        .recovery_timeout_ms = 1000,
    };
    var breaker = try agenkit.middleware.CircuitBreakerDecorator.init(allocator, unreliable.agent(), config);
    defer breaker.agent().deinit();

    // Create a test message
    var message = try agenkit.Message.withText(allocator, .user, "Test message");
    defer message.deinit();

    std.debug.print("  Initial state: {s}\n", .{breaker.getState().toString()});

    // Send requests until circuit opens (5 failures)
    var i: u32 = 0;
    while (i < 7) : (i += 1) {
        const result = breaker.agent().process(message);

        if (result) |res| {
            var response = try res.unwrap();
            response.deinit();
            std.debug.print("  Request {d}: SUCCESS\n", .{i + 1});
        } else |err| {
            if (err == agenkit.AgentError.Cancelled) {
                std.debug.print("  Request {d}: REJECTED (circuit open)\n", .{i + 1});
            } else {
                std.debug.print("  Request {d}: FAILED\n", .{i + 1});
            }
        }

        const state = breaker.getState();
        std.debug.print("    State: {s}\n", .{state.toString()});

        if (state == .OPEN) break;
    }

    const metrics = try breaker.metrics();
    defer metrics.state_transitions.deinit();
    std.debug.print("  Final state: {s}\n", .{breaker.getState().toString()});
    std.debug.print("  Metrics: {d} failed, {d} rejected\n", .{metrics.failed_requests, metrics.rejected_requests});
}

fn circuitRecoveryExample(allocator: std.mem.Allocator) !void {
    // Create an unreliable agent (starts failing, then recovers)
    var unreliable = try UnreliableAgent.init(allocator, true);
    defer unreliable.agent().deinit();

    // Configure circuit breaker with fast recovery for demo
    const config = agenkit.middleware.CircuitBreakerConfig{
        .failure_threshold = 3,
        .success_threshold = 2,
        .recovery_timeout_ms = 100, // Fast recovery for demo
    };
    var breaker = try agenkit.middleware.CircuitBreakerDecorator.init(allocator, unreliable.agent(), config);
    defer breaker.agent().deinit();

    var message = try agenkit.Message.withText(allocator, .user, "Test message");
    defer message.deinit();

    // Step 1: Fail enough times to open circuit
    std.debug.print("  Step 1: Opening circuit (3 failures)...\n", .{});
    var i: u32 = 0;
    while (i < 3) : (i += 1) {
        _ = breaker.agent().process(message) catch {};
    }
    std.debug.print("    State: {s}\n", .{breaker.getState().toString()});

    // Step 2: Wait for recovery timeout
    std.debug.print("  Step 2: Waiting for recovery timeout (100ms)...\n", .{});
    agktime.sleep(150 * std.time.ns_per_ms);

    // Step 3: Service recovers
    unreliable.setFailure(false);
    std.debug.print("  Step 3: Service recovered, sending requests...\n", .{});

    // Send 2 successful requests to close circuit
    i = 0;
    while (i < 2) : (i += 1) {
        const result = try breaker.agent().process(message);
        var response = try result.unwrap();
        response.deinit();
        std.debug.print("    Request {d}: SUCCESS, State: {s}\n", .{ i + 1, breaker.getState().toString() });
    }

    const metrics = try breaker.metrics();
    defer metrics.state_transitions.deinit();
    std.debug.print("  Final state: {s}\n", .{breaker.getState().toString()});
    std.debug.print("  State transitions:\n", .{});
    var iter = metrics.state_transitions.iterator();
    while (iter.next()) |entry| {
        std.debug.print("    {s}: {d}\n", .{ entry.key_ptr.*, entry.value_ptr.* });
    }
}

fn halfOpenFailureExample(allocator: std.mem.Allocator) !void {
    // Create an unreliable agent
    var unreliable = try UnreliableAgent.init(allocator, true);
    defer unreliable.agent().deinit();

    // Configure circuit breaker
    const config = agenkit.middleware.CircuitBreakerConfig{
        .failure_threshold = 3,
        .success_threshold = 2,
        .recovery_timeout_ms = 100,
    };
    var breaker = try agenkit.middleware.CircuitBreakerDecorator.init(allocator, unreliable.agent(), config);
    defer breaker.agent().deinit();

    var message = try agenkit.Message.withText(allocator, .user, "Test message");
    defer message.deinit();

    // Step 1: Open circuit
    std.debug.print("  Step 1: Opening circuit...\n", .{});
    var i: u32 = 0;
    while (i < 3) : (i += 1) {
        _ = breaker.agent().process(message) catch {};
    }
    std.debug.print("    State: {s}\n", .{breaker.getState().toString()});

    // Step 2: Wait for recovery
    std.debug.print("  Step 2: Waiting for recovery timeout...\n", .{});
    agktime.sleep(150 * std.time.ns_per_ms);

    // Step 3: Service still failing - fails in HALF_OPEN
    std.debug.print("  Step 3: Service still failing...\n", .{});
    const result = breaker.agent().process(message);
    if (result) |_| {
        std.debug.print("    ERROR: Should have failed!\n", .{});
    } else |_| {
        std.debug.print("    Request FAILED in HALF_OPEN state\n", .{});
    }
    std.debug.print("    State: {s} (should be OPEN again)\n", .{breaker.getState().toString()});

    const metrics = try breaker.metrics();
    defer metrics.state_transitions.deinit();
    std.debug.print("  Final state: {s}\n", .{breaker.getState().toString()});
}

fn metricsExample(allocator: std.mem.Allocator) !void {
    var unreliable = try UnreliableAgent.init(allocator, false);
    defer unreliable.agent().deinit();

    const config = agenkit.middleware.CircuitBreakerConfig{
        .failure_threshold = 5,
        .success_threshold = 2,
        .recovery_timeout_ms = 100,
    };
    var breaker = try agenkit.middleware.CircuitBreakerDecorator.init(allocator, unreliable.agent(), config);
    defer breaker.agent().deinit();

    var message = try agenkit.Message.withText(allocator, .user, "Test message");
    defer message.deinit();

    // Process mix of successes and failures
    std.debug.print("  Processing 20 requests (mix of success/failure)...\n", .{});
    var i: u32 = 0;
    while (i < 20) : (i += 1) {
        // Fail every 3rd request
        unreliable.setFailure(i % 3 == 2);

        const result = breaker.agent().process(message);
        if (result) |res| {
            var response = try res.unwrap();
            response.deinit();
        } else |_| {
            // Ignored
        }

        // Add small delay to avoid opening circuit too fast
        if (i % 3 == 2) {
            agktime.sleep(50 * std.time.ns_per_ms);
        }
    }

    const metrics = try breaker.metrics();
    defer metrics.state_transitions.deinit();
    std.debug.print("\n  Final Metrics:\n", .{});
    std.debug.print("    Total requests:      {d}\n", .{metrics.total_requests});
    std.debug.print("    Successful:          {d}\n", .{metrics.successful_requests});
    std.debug.print("    Failed:              {d}\n", .{metrics.failed_requests});
    std.debug.print("    Rejected:            {d}\n", .{metrics.rejected_requests});
    std.debug.print("    Current state:       {s}\n", .{metrics.current_state.toString()});
    if (metrics.last_state_change_ms) |timestamp| {
        std.debug.print("    Last state change:   {d}ms ago\n", .{agktime.milliTimestamp() - timestamp});
    }
}

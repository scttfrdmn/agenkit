/// Test utilities for Agenkit Zig
///
/// Provides reusable mocks, fixtures, and helpers for testing agents.
const std = @import("std");
const agktime = @import("time_compat.zig");
const Agent = @import("agent.zig").Agent;
const AgentError = @import("agent.zig").AgentError;
const Result = @import("agent.zig").Result;
const StreamCallbacks = @import("agent.zig").StreamCallbacks;
const Message = @import("message.zig").Message;
const CallOptions = @import("call_options.zig").CallOptions;
const IntrospectionResult = @import("introspection.zig").IntrospectionResult;
const Allocator = std.mem.Allocator;

/// Build the IntrospectionResult every mock starts from.
///
/// Wraps createDefaultIntrospectionResult so each mock only has to add its own
/// internal_state entries.
fn introspectBase(allocator: Allocator, name: []const u8, self_agent: Agent) Allocator.Error!IntrospectionResult {
    const caps = try self_agent.capabilities(allocator);
    defer allocator.free(caps);
    return @import("introspection.zig").createDefaultIntrospectionResult(allocator, name, caps);
}

/// Put a usize into a JSON object as an integer.
fn putInt(allocator: Allocator, value: *std.json.Value, key: []const u8, n: usize) Allocator.Error!void {
    try value.object.put(allocator, key, .{ .integer = @as(i64, @intCast(n)) });
}

/// Mock agent for testing
///
/// Provides configurable responses for testing agent interactions.
/// Cycles through provided responses on each process() call.
///
/// Deliberately does *not* implement the optional `processWith` capability
/// (#801) — it is the stand-in for the many agents that only ever implement
/// `process()`, so tests can exercise the fallback path and assert that a
/// dropped temperature is reported rather than hidden. Use
/// `OptionsAwareMockAgent` when the options are what is under test.
///
/// Example:
/// ```zig
/// var mock = try MockAgent.init(allocator, &[_][]const u8{
///     "Response 1",
///     "Response 2",
/// });
/// defer mock.deinit();
///
/// const agent = mock.agent();
/// const result = try agent.process(message);
/// ```
pub const MockAgent = struct {
    allocator: Allocator,
    responses: []const []const u8,
    call_count: usize,
    agent_name: []const u8,

    pub fn init(allocator: Allocator, responses: []const []const u8) !*MockAgent {
        const self = try allocator.create(MockAgent);
        self.* = MockAgent{
            .allocator = allocator,
            .responses = responses,
            .call_count = 0,
            .agent_name = "mock_agent",
        };
        return self;
    }

    pub fn deinit(self: *MockAgent) void {
        self.allocator.destroy(self);
    }

    pub fn agent(self: *MockAgent) Agent {
        return Agent{
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

    pub fn getCallCount(self: *const MockAgent) usize {
        return self.call_count;
    }

    pub fn resetCallCount(self: *MockAgent) void {
        self.call_count = 0;
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *MockAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 2);
        caps[0] = "mock";
        caps[1] = "testing";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *MockAgent = @ptrCast(@alignCast(ptr));
        // The request is ignored on purpose: responses are scripted.
        _ = message;

        // Get response (cycle through responses)
        const response_text = self.responses[self.call_count % self.responses.len];
        self.call_count += 1;

        // Create response message
        const response = Message.withText(self.allocator, .assistant, response_text) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        return Result{ .ok = response };
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        _ = callbacks;
        return AgentError.NotImplemented;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *MockAgent = @ptrCast(@alignCast(ptr));
        var result = try introspectBase(allocator, self.agent_name, self.agent());
        errdefer result.deinit();
        try putInt(allocator, &result.internal_state, "responses", self.responses.len);
        try putInt(allocator, &result.internal_state, "calls", self.call_count);
        return result;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        _ = ptr;
        // MockAgent deinit is handled by test cleanup
    }
};

/// Mock agent that honours per-call options and records what it received.
///
/// The counterpart to `MockAgent`: it sets the optional `process_with` vtable
/// slot, so `Agent.supportsOptions()` is true and options actually arrive. Every
/// call's temperature is recorded in order, because the interesting assertions
/// are about *which* calls got the options — a technique that forwards them on
/// its first LLM call and drops them on the rest still looks correct if only the
/// first is checked (#801).
///
/// Example:
/// ```zig
/// var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{"answer"});
/// defer mock.deinit();
///
/// _ = try mock.agent().processWith(message, &options);
/// try std.testing.expectEqual(@as(f64, 0.9), mock.temperatures.items[0].?);
/// ```
pub const OptionsAwareMockAgent = struct {
    allocator: Allocator,
    responses: []const []const u8,
    call_count: usize,
    /// One entry per call, in call order. `null` means the call arrived through
    /// `process()` with no options at all.
    temperatures: std.ArrayListUnmanaged(?f64),
    agent_name: []const u8,

    pub fn init(allocator: Allocator, responses: []const []const u8) !*OptionsAwareMockAgent {
        const self = try allocator.create(OptionsAwareMockAgent);
        self.* = OptionsAwareMockAgent{
            .allocator = allocator,
            .responses = responses,
            .call_count = 0,
            .temperatures = .empty,
            .agent_name = "options_aware_mock_agent",
        };
        return self;
    }

    pub fn deinit(self: *OptionsAwareMockAgent) void {
        self.temperatures.deinit(self.allocator);
        self.allocator.destroy(self);
    }

    pub fn agent(self: *OptionsAwareMockAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .process_stream = processStreamImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
                .process_with = processWithImpl,
            },
        };
    }

    pub fn getCallCount(self: *const OptionsAwareMockAgent) usize {
        return self.call_count;
    }

    /// Whether every recorded call saw `want` as its temperature.
    ///
    /// The assertion most tests want: "the options reached *all* of the LLM
    /// calls", not just the one that was easy to check.
    pub fn allTemperaturesEqual(self: *const OptionsAwareMockAgent, want: ?f64) bool {
        if (self.temperatures.items.len == 0) return false;
        for (self.temperatures.items) |seen| {
            if (want) |w| {
                if (seen == null or seen.? != w) return false;
            } else if (seen != null) {
                return false;
            }
        }
        return true;
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *OptionsAwareMockAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 3);
        caps[0] = "mock";
        caps[1] = "testing";
        caps[2] = "call_options";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *OptionsAwareMockAgent = @ptrCast(@alignCast(ptr));
        return self.respond(message, null);
    }

    fn processWithImpl(ptr: *anyopaque, message: Message, options: *const CallOptions) AgentError!Result {
        const self: *OptionsAwareMockAgent = @ptrCast(@alignCast(ptr));
        return self.respond(message, options.temperature);
    }

    fn respond(self: *OptionsAwareMockAgent, message: Message, temperature: ?f64) AgentError!Result {
        // The request is ignored on purpose: responses are scripted.
        _ = message;

        self.temperatures.append(self.allocator, temperature) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        const response_text = self.responses[self.call_count % self.responses.len];
        self.call_count += 1;

        const response = Message.withText(self.allocator, .assistant, response_text) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        return Result{ .ok = response };
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        _ = callbacks;
        return AgentError.NotImplemented;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *OptionsAwareMockAgent = @ptrCast(@alignCast(ptr));
        var result = try introspectBase(allocator, self.agent_name, self.agent());
        errdefer result.deinit();
        try putInt(allocator, &result.internal_state, "responses", self.responses.len);
        try putInt(allocator, &result.internal_state, "calls", self.call_count);
        return result;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        _ = ptr;
        // Deinit is handled by test cleanup, matching MockAgent.
    }
};

/// Mock agent that always fails with a specific error
///
/// Useful for testing error handling paths.
pub const FailingMockAgent = struct {
    allocator: Allocator,
    error_to_return: AgentError,
    agent_name: []const u8,

    pub fn init(allocator: Allocator, error_to_return: AgentError) !*FailingMockAgent {
        const self = try allocator.create(FailingMockAgent);
        self.* = FailingMockAgent{
            .allocator = allocator,
            .error_to_return = error_to_return,
            .agent_name = "failing_mock_agent",
        };
        return self;
    }

    pub fn deinit(self: *FailingMockAgent) void {
        self.allocator.destroy(self);
    }

    pub fn agent(self: *FailingMockAgent) Agent {
        return Agent{
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
        const self: *FailingMockAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "failing";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *FailingMockAgent = @ptrCast(@alignCast(ptr));
        _ = message;
        return Result{ .err = self.error_to_return };
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        _ = callbacks;
        return AgentError.NotImplemented;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *FailingMockAgent = @ptrCast(@alignCast(ptr));
        var result = try introspectBase(allocator, self.agent_name, self.agent());
        errdefer result.deinit();
        // @errorName yields a comptime string literal, so no copy is needed and
        // IntrospectionResult.deinit must not free it (it does not).
        try result.internal_state.object.put(
            allocator,
            "error",
            .{ .string = @errorName(self.error_to_return) },
        );
        return result;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        _ = ptr;
    }
};

/// Mock LLM agent for testing
///
/// Provides a mock LLM implementation with configurable responses,
/// delays, and failure modes. Useful for testing without external API calls.
///
/// Example:
/// ```zig
/// var mock_llm = try MockLLM.init(allocator, &[_][]const u8{
///     "Response 1",
///     "Response 2",
/// }, "mock-llm");
/// defer mock_llm.deinit();
///
/// mock_llm.setTemperature(0.7);
/// mock_llm.setMaxTokens(100);
///
/// const agent = mock_llm.agent();
/// const result = try agent.process(message);
/// ```
pub const MockLLM = struct {
    allocator: Allocator,
    responses: []const []const u8,
    call_count: usize,
    model_name: []const u8,

    // LLM parameters
    temperature: f64,
    max_tokens: ?u32,
    top_p: ?f64,

    // Testing configuration
    delay_ms: u64,
    should_fail: bool,
    failure_error: AgentError,

    pub fn init(allocator: Allocator, responses: []const []const u8, model_name: []const u8) !*MockLLM {
        const self = try allocator.create(MockLLM);
        self.* = MockLLM{
            .allocator = allocator,
            .responses = responses,
            .call_count = 0,
            .model_name = model_name,
            .temperature = 1.0,
            .max_tokens = null,
            .top_p = null,
            .delay_ms = 0,
            .should_fail = false,
            .failure_error = AgentError.ProcessingFailed,
        };
        return self;
    }

    pub fn deinit(self: *MockLLM) void {
        self.allocator.destroy(self);
    }

    pub fn agent(self: *MockLLM) Agent {
        return Agent{
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

    // LLM-specific configuration methods

    pub fn setTemperature(self: *MockLLM, temp: f64) void {
        self.temperature = temp;
    }

    pub fn getTemperature(self: *const MockLLM) f64 {
        return self.temperature;
    }

    pub fn setMaxTokens(self: *MockLLM, tokens: u32) void {
        self.max_tokens = tokens;
    }

    pub fn getMaxTokens(self: *const MockLLM) ?u32 {
        return self.max_tokens;
    }

    pub fn setTopP(self: *MockLLM, p: f64) void {
        self.top_p = p;
    }

    pub fn getTopP(self: *const MockLLM) ?f64 {
        return self.top_p;
    }

    pub fn setDelay(self: *MockLLM, ms: u64) void {
        self.delay_ms = ms;
    }

    pub fn setFailureMode(self: *MockLLM, should_fail: bool, error_type: AgentError) void {
        self.should_fail = should_fail;
        self.failure_error = error_type;
    }

    pub fn getCallCount(self: *const MockLLM) usize {
        return self.call_count;
    }

    pub fn resetCallCount(self: *MockLLM) void {
        self.call_count = 0;
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *MockLLM = @ptrCast(@alignCast(ptr));
        return self.model_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 4);
        caps[0] = "text-generation";
        caps[1] = "chat";
        caps[2] = "mock";
        caps[3] = "testing";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *MockLLM = @ptrCast(@alignCast(ptr));
        // The request is ignored on purpose: responses are scripted.
        _ = message;

        // Simulate network delay if configured
        if (self.delay_ms > 0) {
            agktime.sleep(self.delay_ms * std.time.ns_per_ms);
        }

        // Simulate failure if configured
        if (self.should_fail) {
            return Result{ .err = self.failure_error };
        }

        // Get response (cycle through responses)
        const response_text = self.responses[self.call_count % self.responses.len];
        self.call_count += 1;

        // Create response message
        const response = Message.withText(self.allocator, .assistant, response_text) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        // Add LLM metadata (simplified - would need json module for full metadata)
        // In production, this would add model, temperature, etc. to metadata

        return Result{ .ok = response };
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        _ = callbacks;
        return AgentError.NotImplemented;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *MockLLM = @ptrCast(@alignCast(ptr));
        var result = try introspectBase(allocator, self.model_name, self.agent());
        errdefer result.deinit();

        const state = &result.internal_state;
        try putInt(allocator, state, "responses", self.responses.len);
        try putInt(allocator, state, "calls", self.call_count);
        try state.object.put(allocator, "temperature", .{ .float = self.temperature });
        // max_tokens and top_p are optional: absent means the caller never set
        // one, which is not the same as setting it to zero.
        if (self.max_tokens) |tokens| {
            try putInt(allocator, state, "max_tokens", tokens);
        }
        if (self.top_p) |p| {
            try state.object.put(allocator, "top_p", .{ .float = p });
        }
        return result;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        _ = ptr;
        // MockLLM deinit is handled by test cleanup
    }
};

// Tests for test utilities
test "MockAgent basic functionality" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{ "Response 1", "Response 2" });
    defer mock.deinit();

    const agent_impl = mock.agent();
    try testing.expectEqualStrings("mock_agent", agent_impl.name());

    // Test first response
    var msg1 = try Message.withText(allocator, .user, "Test 1");
    defer msg1.deinit();

    var response1 = try (try agent_impl.process(msg1)).unwrap();
    defer response1.deinit();

    try testing.expectEqualStrings("Response 1", try response1.contentAsText());
    try testing.expectEqual(@as(usize, 1), mock.getCallCount());

    // Test second response
    var msg2 = try Message.withText(allocator, .user, "Test 2");
    defer msg2.deinit();

    var response2 = try (try agent_impl.process(msg2)).unwrap();
    defer response2.deinit();

    try testing.expectEqualStrings("Response 2", try response2.contentAsText());
    try testing.expectEqual(@as(usize, 2), mock.getCallCount());

    // Test cycling back to first response
    var msg3 = try Message.withText(allocator, .user, "Test 3");
    defer msg3.deinit();

    var response3 = try (try agent_impl.process(msg3)).unwrap();
    defer response3.deinit();

    try testing.expectEqualStrings("Response 1", try response3.contentAsText());
    try testing.expectEqual(@as(usize, 3), mock.getCallCount());
}

test "MockAgent capabilities" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"Response"});
    defer mock.deinit();

    const agent_impl = mock.agent();
    const caps = try agent_impl.capabilities(allocator);
    defer allocator.free(caps);

    try testing.expectEqual(@as(usize, 2), caps.len);
    try testing.expectEqualStrings("mock", caps[0]);
    try testing.expectEqualStrings("testing", caps[1]);
}

test "MockAgent reset call count" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"Response"});
    defer mock.deinit();

    const agent_impl = mock.agent();

    // Make some calls
    var msg1 = try Message.withText(allocator, .user, "Test 1");
    defer msg1.deinit();
    var response1 = try (try agent_impl.process(msg1)).unwrap();
    defer response1.deinit();

    try testing.expectEqual(@as(usize, 1), mock.getCallCount());

    // Reset
    mock.resetCallCount();
    try testing.expectEqual(@as(usize, 0), mock.getCallCount());
}

test "FailingMockAgent returns error" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var failing = try FailingMockAgent.init(allocator, AgentError.ProcessingFailed);
    defer failing.deinit();

    const agent_impl = failing.agent();
    try testing.expectEqualStrings("failing_mock_agent", agent_impl.name());

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    const result = try agent_impl.process(msg);
    try testing.expectEqual(AgentError.ProcessingFailed, result.err);
}

test "FailingMockAgent introspection reports its error" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var failing = try FailingMockAgent.init(allocator, AgentError.Timeout);
    defer failing.deinit();

    var info = try failing.agent().introspect(allocator);
    defer info.deinit();

    try testing.expectEqualStrings("failing_mock_agent", info.agent_name);
    try testing.expectEqualStrings("Timeout", info.internal_state.object.get("error").?.string);
}

test "MockAgent introspection" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{ "R1", "R2" });
    defer mock.deinit();

    const agent_impl = mock.agent();
    var info = try agent_impl.introspect(allocator);
    defer info.deinit();

    try testing.expectEqualStrings("mock_agent", info.agent_name);
    try testing.expectEqual(@as(i64, 2), info.internal_state.object.get("responses").?.integer);
    try testing.expectEqual(@as(i64, 0), info.internal_state.object.get("calls").?.integer);
}

test "MockLLM basic functionality" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock_llm = try MockLLM.init(allocator, &[_][]const u8{ "LLM Response 1", "LLM Response 2" }, "mock-gpt-4");
    defer mock_llm.deinit();

    const agent_impl = mock_llm.agent();
    try testing.expectEqualStrings("mock-gpt-4", agent_impl.name());

    // Test first response
    var msg1 = try Message.withText(allocator, .user, "What is AI?");
    defer msg1.deinit();

    var response1 = try (try agent_impl.process(msg1)).unwrap();
    defer response1.deinit();

    try testing.expectEqualStrings("LLM Response 1", try response1.contentAsText());
    try testing.expectEqual(@as(usize, 1), mock_llm.getCallCount());
}

test "MockLLM LLM parameters" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock_llm = try MockLLM.init(allocator, &[_][]const u8{"Response"}, "mock-llm");
    defer mock_llm.deinit();

    // Test temperature
    mock_llm.setTemperature(0.7);
    try testing.expectEqual(@as(f64, 0.7), mock_llm.getTemperature());

    // Test max_tokens
    mock_llm.setMaxTokens(100);
    try testing.expectEqual(@as(?u32, 100), mock_llm.getMaxTokens());

    // Test top_p
    mock_llm.setTopP(0.9);
    try testing.expectEqual(@as(?f64, 0.9), mock_llm.getTopP());
}

test "MockLLM failure mode" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock_llm = try MockLLM.init(allocator, &[_][]const u8{"Response"}, "mock-llm");
    defer mock_llm.deinit();

    mock_llm.setFailureMode(true, AgentError.Timeout);

    const agent_impl = mock_llm.agent();
    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    const result = try agent_impl.process(msg);
    try testing.expectEqual(AgentError.Timeout, result.err);
}

test "MockLLM introspection" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock_llm = try MockLLM.init(allocator, &[_][]const u8{ "R1", "R2" }, "mock-gpt-4");
    defer mock_llm.deinit();

    mock_llm.setTemperature(0.8);
    mock_llm.setMaxTokens(150);

    const agent_impl = mock_llm.agent();
    var info = try agent_impl.introspect(allocator);
    defer info.deinit();

    try testing.expectEqualStrings("mock-gpt-4", info.agent_name);
    try testing.expectEqual(@as(f64, 0.8), info.internal_state.object.get("temperature").?.float);
    try testing.expectEqual(@as(i64, 150), info.internal_state.object.get("max_tokens").?.integer);
    // top_p was never set, so it must be absent rather than reported as 0.
    try testing.expect(info.internal_state.object.get("top_p") == null);
}

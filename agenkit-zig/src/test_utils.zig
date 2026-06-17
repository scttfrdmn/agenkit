/// Test utilities for Agenkit Zig
///
/// Provides reusable mocks, fixtures, and helpers for testing agents.
const std = @import("std");
const agktime = @import("time_compat.zig");
const Agent = @import("agent.zig").Agent;
const AgentError = @import("agent.zig").AgentError;
const Result = @import("agent.zig").Result;
const Message = @import("message.zig").Message;
const Allocator = std.mem.Allocator;

/// Mock agent for testing
///
/// Provides configurable responses for testing agent interactions.
/// Cycles through provided responses on each process() call.
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

        // Get response (cycle through responses)
        const response_text = self.responses[self.call_count % self.responses.len];
        self.call_count += 1;

        // Create response message
        var response = Message.withText(self.allocator, .assistant, response_text) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        return Result{ .ok = response };
    }

    fn processStreamImpl(
        ptr: *anyopaque,
        message: Message,
        stream_callback: *const fn (chunk: []const u8, userdata: ?*anyopaque) void,
        userdata: ?*anyopaque,
    ) AgentError!void {
        _ = ptr;
        _ = message;
        _ = stream_callback;
        _ = userdata;
        return AgentError.NotImplemented;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const u8 {
        const self: *MockAgent = @ptrCast(@alignCast(ptr));
        return std.fmt.allocPrint(
            allocator,
            "MockAgent(name={s}, responses={d}, calls={d})",
            .{ self.agent_name, self.responses.len, self.call_count },
        );
    }

    fn deinitImpl(ptr: *anyopaque) void {
        _ = ptr;
        // MockAgent deinit is handled by test cleanup
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

    fn processStreamImpl(
        ptr: *anyopaque,
        message: Message,
        stream_callback: *const fn (chunk: []const u8, userdata: ?*anyopaque) void,
        userdata: ?*anyopaque,
    ) AgentError!void {
        _ = ptr;
        _ = message;
        _ = stream_callback;
        _ = userdata;
        return AgentError.NotImplemented;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const u8 {
        const self: *FailingMockAgent = @ptrCast(@alignCast(ptr));
        return std.fmt.allocPrint(
            allocator,
            "FailingMockAgent(name={s}, error={s})",
            .{ self.agent_name, @tagName(self.error_to_return) },
        );
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
        var response = Message.withText(self.allocator, .assistant, response_text) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        // Add LLM metadata (simplified - would need json module for full metadata)
        // In production, this would add model, temperature, etc. to metadata

        return Result{ .ok = response };
    }

    fn processStreamImpl(
        ptr: *anyopaque,
        message: Message,
        stream_callback: *const fn (chunk: []const u8, userdata: ?*anyopaque) void,
        userdata: ?*anyopaque,
    ) AgentError!void {
        _ = ptr;
        _ = message;
        _ = stream_callback;
        _ = userdata;
        return AgentError.NotImplemented;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const u8 {
        const self: *MockLLM = @ptrCast(@alignCast(ptr));

        if (self.max_tokens) |tokens| {
            return std.fmt.allocPrint(
                allocator,
                "MockLLM(model={s}, responses={d}, calls={d}, temperature={d:.2}, max_tokens={d})",
                .{ self.model_name, self.responses.len, self.call_count, self.temperature, tokens },
            );
        } else {
            return std.fmt.allocPrint(
                allocator,
                "MockLLM(model={s}, responses={d}, calls={d}, temperature={d:.2})",
                .{ self.model_name, self.responses.len, self.call_count, self.temperature },
            );
        }
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
    const msg1 = try Message.withText(allocator, .user, "Test 1");
    defer msg1.deinit();

    const result1 = try agent_impl.process(msg1);
    defer result1.ok.deinit();

    try testing.expectEqualStrings("Response 1", result1.ok.content.string);
    try testing.expectEqual(@as(usize, 1), mock.getCallCount());

    // Test second response
    const msg2 = try Message.withText(allocator, .user, "Test 2");
    defer msg2.deinit();

    const result2 = try agent_impl.process(msg2);
    defer result2.ok.deinit();

    try testing.expectEqualStrings("Response 2", result2.ok.content.string);
    try testing.expectEqual(@as(usize, 2), mock.getCallCount());

    // Test cycling back to first response
    const msg3 = try Message.withText(allocator, .user, "Test 3");
    defer msg3.deinit();

    const result3 = try agent_impl.process(msg3);
    defer result3.ok.deinit();

    try testing.expectEqualStrings("Response 1", result3.ok.content.string);
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
    const msg1 = try Message.withText(allocator, .user, "Test 1");
    defer msg1.deinit();
    const result1 = try agent_impl.process(msg1);
    defer result1.ok.deinit();

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

    const msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    const result = try agent_impl.process(msg);
    try testing.expectEqual(AgentError.ProcessingFailed, result.err);
}

test "MockAgent introspection" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{ "R1", "R2" });
    defer mock.deinit();

    const agent_impl = mock.agent();
    const info = try agent_impl.introspect(allocator);
    defer allocator.free(info);

    try testing.expect(std.mem.indexOf(u8, info, "MockAgent") != null);
    try testing.expect(std.mem.indexOf(u8, info, "responses=2") != null);
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
    const msg1 = try Message.withText(allocator, .user, "What is AI?");
    defer msg1.deinit();

    const result1 = try agent_impl.process(msg1);
    defer result1.ok.deinit();

    try testing.expectEqualStrings("LLM Response 1", result1.ok.content.string);
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
    const msg = try Message.withText(allocator, .user, "Test");
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
    const info = try agent_impl.introspect(allocator);
    defer allocator.free(info);

    try testing.expect(std.mem.indexOf(u8, info, "MockLLM") != null);
    try testing.expect(std.mem.indexOf(u8, info, "mock-gpt-4") != null);
    try testing.expect(std.mem.indexOf(u8, info, "temperature=") != null);
    try testing.expect(std.mem.indexOf(u8, info, "max_tokens=150") != null);
}

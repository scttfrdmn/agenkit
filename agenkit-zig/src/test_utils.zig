/// Test utilities for Agenkit Zig
///
/// Provides reusable mocks, fixtures, and helpers for testing agents.

const std = @import("std");
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

// Tests for test utilities
test "MockAgent basic functionality" {
    const testing = std.testing;

    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
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

    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
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

    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
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

    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
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

    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
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

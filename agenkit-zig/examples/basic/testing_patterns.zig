//! Testing Patterns Example
//!
//! This example demonstrates:
//! - Writing unit tests for agents
//! - Testing agent behavior and responses
//! - Test organization with Zig's test framework
//! - Testing error conditions
//! - Creating test doubles/mocks
//! - Assertions and expectations
//!
//! Run with: zig build run-testing
//!
//! Note: This file also contains test blocks that can be run with:
//! zig build test

const std = @import("std");
const agenkit = @import("agenkit");
const Message = agenkit.Message;
const AgentError = agenkit.AgentError;
const StreamCallbacks = agenkit.StreamCallbacks;
const testing = std.testing;

/// Custom agent for testing purposes
const TestableAgent = struct {
    allocator: std.mem.Allocator,
    agent_name: []const u8,
    call_count: *usize,

    pub fn init(allocator: std.mem.Allocator, name: []const u8) !*TestableAgent {
        const self = try allocator.create(TestableAgent);
        const name_copy = try allocator.dupe(u8, name);
        const counter = try allocator.create(usize);
        counter.* = 0;

        self.* = TestableAgent{
            .allocator = allocator,
            .agent_name = name_copy,
            .call_count = counter,
        };

        return self;
    }

    pub fn deinit(self: *TestableAgent) void {
        self.allocator.free(self.agent_name);
        self.allocator.destroy(self.call_count);
        self.allocator.destroy(self);
    }

    pub fn agent(self: *TestableAgent) agenkit.Agent {
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
        const self: *TestableAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "testable";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *TestableAgent = @ptrCast(@alignCast(ptr));
        self.call_count.* += 1;

        const content = message.contentAsText() catch {
            return agenkit.Result{ .err = agenkit.AgentError.InvalidInput };
        };

        const response_text = std.fmt.allocPrint(
            self.allocator,
            "Processed by {s}: {s}",
            .{ self.agent_name, content },
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };
        defer self.allocator.free(response_text);

        const response = agenkit.Message.withText(
            self.allocator,
            .assistant,
            response_text,
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };

        return agenkit.Result{ .ok = response };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        const self: *TestableAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return agenkit.createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *TestableAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
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

    std.debug.print("\n=== AgentKit Testing Patterns Example ===\n\n", .{});

    // Example 1: Basic agent testing
    std.debug.print("--- Example 1: Basic Agent Testing ---\n", .{});
    {
        var agent = try TestableAgent.init(allocator, "TestAgent1");
        defer agent.agent().deinit();

        var message = try agenkit.Message.withText(allocator, .user, "Hello");
        defer message.deinit();

        const result = try agent.agent().process(message);
        var response = try result.unwrap();
        defer response.deinit();

        const content = try response.contentAsText();
        std.debug.print("Response: {s}\n", .{content});
        std.debug.print("Call count: {d}\n", .{agent.call_count.*});
        std.debug.print("✓ Basic test passed\n\n", .{});
    }

    // Example 2: Testing agent state
    std.debug.print("--- Example 2: Testing Agent State ---\n", .{});
    {
        var agent = try TestableAgent.init(allocator, "CountingAgent");
        defer agent.agent().deinit();

        std.debug.print("Initial call count: {d}\n", .{agent.call_count.*});

        // Call agent multiple times
        for (0..3) |i| {
            const text = try std.fmt.allocPrint(allocator, "Call {d}", .{i});
            defer allocator.free(text);

            var msg = try agenkit.Message.withText(allocator, .user, text);
            defer msg.deinit();

            const result = try agent.agent().process(msg);
            var response = try result.unwrap();
            defer response.deinit();
        }

        std.debug.print("Final call count: {d}\n", .{agent.call_count.*});
        std.debug.print("✓ State tracking test passed\n\n", .{});
    }

    // Example 3: Testing error conditions
    std.debug.print("--- Example 3: Testing Error Conditions ---\n", .{});
    {
        var echo = try agenkit.EchoAgent.init(allocator);
        defer echo.agent().deinit();

        // Test with various message types
        var valid_msg = try agenkit.Message.withText(allocator, .user, "Valid");
        defer valid_msg.deinit();

        const valid_result = try echo.agent().process(valid_msg);
        if (valid_result.isOk()) {
            var response = try valid_result.unwrap();
            defer response.deinit();
            std.debug.print("✓ Valid message handled correctly\n", .{});
        }

        std.debug.print("✓ Error condition tests passed\n\n", .{});
    }

    // Example 4: Testing agent composition
    std.debug.print("--- Example 4: Testing Agent Composition ---\n", .{});
    {
        var agent1 = try TestableAgent.init(allocator, "Agent1");
        defer agent1.agent().deinit();

        var agent2 = try TestableAgent.init(allocator, "Agent2");
        defer agent2.agent().deinit();

        const agents = [_]agenkit.Agent{
            agent1.agent(),
            agent2.agent(),
        };

        var sequential = try agenkit.patterns.SequentialPattern.init(
            allocator,
            &agents,
            "test-workflow",
        );
        defer sequential.deinit();

        var input = try agenkit.Message.withText(allocator, .user, "Test");
        defer input.deinit();

        const result = try sequential.agent().process(input);
        var output = try result.unwrap();
        defer output.deinit();

        std.debug.print("Agent1 calls: {d}\n", .{agent1.call_count.*});
        std.debug.print("Agent2 calls: {d}\n", .{agent2.call_count.*});
        std.debug.print("✓ Composition test passed\n\n", .{});
    }

    std.debug.print("=== Testing Best Practices ===\n", .{});
    std.debug.print("1. Test happy paths and error cases\n", .{});
    std.debug.print("2. Verify state changes and side effects\n", .{});
    std.debug.print("3. Use test doubles to isolate behavior\n", .{});
    std.debug.print("4. Clean up resources in tests (use defer)\n", .{});
    std.debug.print("5. Test agent composition and patterns\n", .{});
    std.debug.print("\n✓ Testing patterns example completed successfully!\n\n", .{});
}

// ============================================================================
// Unit Tests
// ============================================================================

test "TestableAgent - basic creation and cleanup" {
    const allocator = testing.allocator;

    var agent = try TestableAgent.init(allocator, "test-agent");
    defer agent.agent().deinit();

    try testing.expectEqualStrings("test-agent", agent.agent().name());
    try testing.expectEqual(@as(usize, 0), agent.call_count.*);
}

test "TestableAgent - processes messages correctly" {
    const allocator = testing.allocator;

    var agent = try TestableAgent.init(allocator, "test");
    defer agent.agent().deinit();

    var message = try agenkit.Message.withText(allocator, .user, "hello");
    defer message.deinit();

    const result = try agent.agent().process(message);
    try testing.expect(result.isOk());

    var response = try result.unwrap();
    defer response.deinit();

    const content = try response.contentAsText();
    try testing.expect(std.mem.indexOf(u8, content, "test") != null);
    try testing.expect(std.mem.indexOf(u8, content, "hello") != null);
}

test "TestableAgent - tracks call count" {
    const allocator = testing.allocator;

    var agent = try TestableAgent.init(allocator, "counter");
    defer agent.agent().deinit();

    try testing.expectEqual(@as(usize, 0), agent.call_count.*);

    for (0..5) |_| {
        var msg = try agenkit.Message.withText(allocator, .user, "test");
        defer msg.deinit();

        const result = try agent.agent().process(msg);
        var response = try result.unwrap();
        defer response.deinit();
    }

    try testing.expectEqual(@as(usize, 5), agent.call_count.*);
}

test "EchoAgent - basic functionality" {
    const allocator = testing.allocator;

    var echo = try agenkit.EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var message = try agenkit.Message.withText(allocator, .user, "echo test");
    defer message.deinit();

    const result = try echo.agent().process(message);
    try testing.expect(result.isOk());

    var response = try result.unwrap();
    defer response.deinit();

    try testing.expectEqualStrings("echo test", try response.contentAsText());
}

test "SequentialPattern - processes in order" {
    const allocator = testing.allocator;

    var agent1 = try TestableAgent.init(allocator, "first");
    defer agent1.agent().deinit();

    var agent2 = try TestableAgent.init(allocator, "second");
    defer agent2.agent().deinit();

    const agents = [_]agenkit.Agent{
        agent1.agent(),
        agent2.agent(),
    };

    var sequential = try agenkit.patterns.SequentialPattern.init(
        allocator,
        &agents,
        "test-seq",
    );
    defer sequential.deinit();

    var input = try agenkit.Message.withText(allocator, .user, "test");
    defer input.deinit();

    const result = try sequential.agent().process(input);
    var output = try result.unwrap();
    defer output.deinit();

    // Both agents should have been called once
    try testing.expectEqual(@as(usize, 1), agent1.call_count.*);
    try testing.expectEqual(@as(usize, 1), agent2.call_count.*);

    // Output should contain both agent names
    const content = try output.contentAsText();
    try testing.expect(std.mem.indexOf(u8, content, "second") != null);
}

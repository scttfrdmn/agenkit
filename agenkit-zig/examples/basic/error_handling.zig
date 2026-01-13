//! Error Handling Example
//!
//! This example demonstrates:
//! - Error propagation patterns in Zig
//! - Handling errors from agent processing
//! - Using Result.unwrap() and Result.isError()
//! - Proper cleanup with defer even when errors occur
//! - Error recovery strategies
//!
//! Run with: zig build run-error-handling

const std = @import("std");
const agenkit = @import("agenkit");
const Message = agenkit.Message;
const AgentError = agenkit.AgentError;
const StreamCallbacks = agenkit.StreamCallbacks;

/// Custom agent that can fail on demand for demonstration
const FailableAgent = struct {
    allocator: std.mem.Allocator,
    should_fail: bool,
    agent_name: []const u8,

    pub fn init(allocator: std.mem.Allocator, should_fail: bool) !*FailableAgent {
        const self = try allocator.create(FailableAgent);
        const name = try allocator.dupe(u8, if (should_fail) "FailingAgent" else "SuccessAgent");

        self.* = FailableAgent{
            .allocator = allocator,
            .should_fail = should_fail,
            .agent_name = name,
        };

        return self;
    }

    pub fn deinit(self: *FailableAgent) void {
        self.allocator.free(self.agent_name);
        self.allocator.destroy(self);
    }

    pub fn agent(self: *FailableAgent) agenkit.Agent {
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
        const self: *FailableAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "error-demo";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *FailableAgent = @ptrCast(@alignCast(ptr));

        if (self.should_fail) {
            // Demonstrate error case
            return agenkit.Result{ .err = agenkit.AgentError.ProcessingFailed };
        }

        // Success case - echo the message
        const content = message.contentAsText() catch {
            return agenkit.Result{ .err = agenkit.AgentError.InvalidInput };
        };

        const response = agenkit.Message.withText(
            self.allocator,
            .assistant,
            content,
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };

        return agenkit.Result{ .ok = response };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        const self: *FailableAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return agenkit.createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *FailableAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};


fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
    _ = ptr;
    _ = message;
    callbacks.onError(AgentError.NotImplemented);
}
pub fn main() !void {
    // Initialize allocator
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== AgentKit Error Handling Example ===\n\n", .{});

    // Example 1: Successful processing
    std.debug.print("--- Example 1: Successful Processing ---\n", .{});
    var success_agent = try FailableAgent.init(allocator, false);
    defer success_agent.agent().deinit();

    var message1 = try agenkit.Message.withText(
        allocator,
        .user,
        "This should succeed",
    );
    defer message1.deinit();

    const result1 = try success_agent.agent().process(message1);
    if (result1.isErr()) {
        std.debug.print("Unexpected error: {s}\n\n", .{@errorName(result1.unwrapErr())});
    } else {
        var response1 = try result1.unwrap();
        defer response1.deinit();
        std.debug.print("Success! Response: {s}\n\n", .{try response1.contentAsText()});
    }

    // Example 2: Handling errors
    std.debug.print("--- Example 2: Handling Errors ---\n", .{});
    var failing_agent = try FailableAgent.init(allocator, true);
    defer failing_agent.agent().deinit();

    var message2 = try agenkit.Message.withText(
        allocator,
        .user,
        "This will fail",
    );
    defer message2.deinit();

    const result2 = try failing_agent.agent().process(message2);
    if (result2.isErr()) {
        const err = result2.unwrapErr();
        std.debug.print("Expected error caught: {s}\n", .{@errorName(err)});
        std.debug.print("Error handling successful!\n\n", .{});
    } else {
        // This branch won't execute in our test
        var response2 = try result2.unwrap();
        defer response2.deinit();
        std.debug.print("Unexpected success: {s}\n\n", .{try response2.contentAsText()});
    }

    // Example 3: Error recovery pattern
    std.debug.print("--- Example 3: Error Recovery ---\n", .{});

    var message3 = try agenkit.Message.withText(
        allocator,
        .user,
        "Try with fallback",
    );
    defer message3.deinit();

    // Try primary agent
    const primary_result = try failing_agent.agent().process(message3);

    // If primary fails, use fallback
    if (primary_result.isErr()) {
        std.debug.print("Primary agent failed, trying fallback...\n", .{});

        const fallback_result = try success_agent.agent().process(message3);
        var fallback_response = try fallback_result.unwrap();
        defer fallback_response.deinit();

        std.debug.print("Fallback succeeded! Response: {s}\n\n", .{try fallback_response.contentAsText()});
    }

    // Example 4: Cleanup guarantees with defer
    std.debug.print("--- Example 4: Cleanup with Defer ---\n", .{});
    {
        var temp_agent = try FailableAgent.init(allocator, true);
        defer temp_agent.agent().deinit(); // This always runs, even if process fails

        var temp_message = try agenkit.Message.withText(
            allocator,
            .user,
            "Testing cleanup",
        );
        defer temp_message.deinit(); // This also always runs

        const temp_result = try temp_agent.agent().process(temp_message);
        if (temp_result.isErr()) {
            std.debug.print("Agent failed, but cleanup is guaranteed by defer\n", .{});
        }
    }
    std.debug.print("✓ All resources properly cleaned up\n\n", .{});

    std.debug.print("✓ Error handling example completed successfully!\n\n", .{});
}

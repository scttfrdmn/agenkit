/// Agent interface for agenkit
///
/// An Agent is the core abstraction in Agenkit. Agents process messages and
/// return responses. They can wrap LLMs, implement patterns, or provide
/// custom logic.
///
/// Key design principles:
/// - Explicit error handling with error union types
/// - Explicit memory management with allocators
/// - Composable through interface-based design
const std = @import("std");
const Message = @import("message.zig").Message;
const IntrospectionResult = @import("introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("introspection.zig").createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;

/// Error types for agent operations
pub const AgentError = error{
    ProcessingFailed,
    InvalidInput,
    Timeout,
    Cancelled,
    NotImplemented,
};

/// Callbacks for streaming responses
pub const StreamCallbacks = struct {
    ptr: *anyopaque,
    on_message_fn: *const fn (ptr: *anyopaque, message: Message) void,
    on_error_fn: *const fn (ptr: *anyopaque, err: AgentError) void,
    on_complete_fn: *const fn (ptr: *anyopaque) void,

    /// Invoke the message callback
    pub fn onMessage(self: StreamCallbacks, message: Message) void {
        self.on_message_fn(self.ptr, message);
    }

    /// Invoke the error callback
    pub fn onError(self: StreamCallbacks, err: AgentError) void {
        self.on_error_fn(self.ptr, err);
    }

    /// Invoke the completion callback
    pub fn onComplete(self: StreamCallbacks) void {
        self.on_complete_fn(self.ptr);
    }
};

/// Result type for agent processing
pub const Result = union(enum) {
    ok: Message,
    err: AgentError,

    pub fn isOk(self: Result) bool {
        return self == .ok;
    }

    pub fn isErr(self: Result) bool {
        return self == .err;
    }

    pub fn unwrap(self: Result) !Message {
        return switch (self) {
            .ok => |msg| msg,
            .err => |e| e,
        };
    }

    pub fn unwrapErr(self: Result) AgentError {
        return switch (self) {
            .ok => unreachable,
            .err => |e| e,
        };
    }
};

/// Agent interface - all agents must implement these methods
pub const Agent = struct {
    ptr: *anyopaque,
    vtable: *const VTable,

    pub const VTable = struct {
        name: *const fn (ptr: *anyopaque) []const u8,
        capabilities: *const fn (ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8,
        process: *const fn (ptr: *anyopaque, message: Message) AgentError!Result,
        process_stream: *const fn (ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void,
        introspect: *const fn (ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult,
        deinit: *const fn (ptr: *anyopaque) void,
    };

    /// Get the agent's name
    pub fn name(self: Agent) []const u8 {
        return self.vtable.name(self.ptr);
    }

    /// Get the agent's capabilities
    pub fn capabilities(self: Agent, allocator: Allocator) ![]const []const u8 {
        return self.vtable.capabilities(self.ptr, allocator);
    }

    /// Process a message and return a result
    pub fn process(self: Agent, message: Message) !Result {
        return self.vtable.process(self.ptr, message);
    }

    /// Process a message with streaming response (optional)
    ///
    /// This method enables streaming responses where the agent can return
    /// multiple message chunks over time. The implementation uses callbacks
    /// to deliver messages and errors asynchronously.
    ///
    /// Callbacks:
    /// - on_message: Called for each message chunk
    /// - on_error: Called on error (terminates stream)
    /// - on_complete: Called when stream completes successfully
    ///
    /// Default implementation (if not overridden) will call on_error with
    /// AgentError.NotImplemented.
    ///
    /// Example:
    /// ```zig
    /// const Context = struct {
    ///     chunks: *std.ArrayList(Message),
    /// };
    /// var ctx = Context{ .chunks = &chunks };
    ///
    /// const callbacks = StreamCallbacks{
    ///     .ptr = &ctx,
    ///     .on_message_fn = struct {
    ///         fn callback(ptr: *anyopaque, msg: Message) void {
    ///             const c: *Context = @ptrCast(@alignCast(ptr));
    ///             c.chunks.append(msg) catch {};
    ///         }
    ///     }.callback,
    ///     .on_error_fn = ...,
    ///     .on_complete_fn = ...,
    /// };
    ///
    /// try agent.processStream(message, callbacks);
    /// ```
    pub fn processStream(self: Agent, message: Message, callbacks: StreamCallbacks) !void {
        return self.vtable.process_stream(self.ptr, message, callbacks);
    }

    /// Examine agent's internal state, memory, and capabilities.
    ///
    /// This is introspection (examining "what I know"), not reflection
    /// (analyzing "how I did"). Returns a snapshot of current internal state.
    ///
    /// Introspection is useful for:
    /// - Debugging: Examine agent state during development
    /// - Monitoring: Track agent state in production
    /// - Coordination: Agents can inspect each other's capabilities
    /// - Testing: Verify agent state in tests
    /// - Explainability: Understand what an agent "knows"
    ///
    /// Default implementation returns basic information using
    /// createDefaultIntrospectionResult with the agent's name and capabilities.
    ///
    /// Override this in your agent implementation to provide custom memory
    /// and internal state information.
    ///
    /// Caller must call deinit() on the returned IntrospectionResult when done.
    pub fn introspect(self: Agent, allocator: Allocator) !IntrospectionResult {
        return self.vtable.introspect(self.ptr, allocator);
    }

    /// Clean up resources
    pub fn deinit(self: Agent) void {
        self.vtable.deinit(self.ptr);
    }
};

/// Echo agent - simple agent that echoes back messages (useful for testing)
pub const EchoAgent = struct {
    allocator: Allocator,
    agent_name: []const u8,

    pub fn init(allocator: Allocator) !*EchoAgent {
        const self = try allocator.create(EchoAgent);
        self.* = EchoAgent{
            .allocator = allocator,
            .agent_name = "echo",
        };
        return self;
    }

    pub fn agent(self: *EchoAgent) Agent {
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
        const self: *EchoAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "echo";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *EchoAgent = @ptrCast(@alignCast(ptr));

        // Echo the message back as assistant
        const text = message.contentAsText() catch {
            return Result{ .err = AgentError.InvalidInput };
        };

        var response = Message.withText(self.allocator, .assistant, text) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        // Preserve metadata
        var it = message.metadata.object.iterator();
        while (it.next()) |entry| {
            response.setMetadata(entry.key_ptr.*, entry.value_ptr.*) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            };
        }

        return Result{ .ok = response };
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        // Default implementation: streaming not supported
        _ = ptr;
        _ = message;
        callbacks.onError(AgentError.NotImplemented);
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *EchoAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        // Capability strings are borrowed (see SequentialAgent/ParallelAgent:
        // they pass inner cap strings through by reference). Only the array is
        // owned here; `createDefaultIntrospectionResult` duplicates the strings.
        defer allocator.free(caps);
        return createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *EchoAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};

test "EchoAgent basic functionality" {
    const allocator = std.testing.allocator;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    const agent_iface = echo.agent();
    try std.testing.expectEqualStrings("echo", agent_iface.name());

    var msg = try Message.withText(allocator, .user, "Hello!");
    defer msg.deinit();

    const result = try agent_iface.process(msg);
    try std.testing.expect(result.isOk());

    var response = try result.unwrap();
    defer response.deinit();

    const text = try response.contentAsText();
    try std.testing.expectEqualStrings("Hello!", text);
}

test "EchoAgent preserves metadata" {
    const allocator = std.testing.allocator;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var msg = try Message.withText(allocator, .user, "Test");
    try msg.setMetadata("test_key", std.json.Value{ .string = "test_value" });
    defer msg.deinit();

    const result = try echo.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const metadata = response.getMetadata("test_key");
    try std.testing.expect(metadata != null);
}

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
const CallOptions = @import("call_options.zig").CallOptions;
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

        /// Optional: process a message under per-call inference options.
        ///
        /// Defaulted to null so every existing vtable literal keeps compiling
        /// untouched — the required contract stays the six fields above, and an
        /// agent that has no use for options simply does not set this one.
        ///
        /// A null slot is the honest answer to "can you honour options?", and
        /// `supportsOptions()` reports it. That is what lets
        /// `SelfConsistencyAgent.temperatureApplied()` say the temperature was
        /// dropped instead of accepting it and discarding it in silence, which
        /// is the bug this whole change exists to fix (#801).
        ///
        /// Zig has no way to query a struct for a method the way Go's type
        /// assertion or TypeScript's `typeof agent.processWith` can, so the
        /// capability has to be declared. It is still a genuine check rather
        /// than a claim: the slot holds the implementation itself, so an agent
        /// cannot advertise the capability without also providing it.
        process_with: ?*const fn (
            ptr: *anyopaque,
            message: Message,
            options: *const CallOptions,
        ) AgentError!Result = null,
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

    /// Whether this agent honours per-call `CallOptions`.
    ///
    /// Ask before assuming a temperature or token limit will reach the provider.
    /// `processWithOptions` does this check for you; call this directly only when
    /// you need to *report* the answer rather than act on it — as
    /// `SelfConsistencyAgent.temperatureApplied()` does.
    pub fn supportsOptions(self: Agent) bool {
        return self.vtable.process_with != null;
    }

    /// Process a message under per-call inference options.
    ///
    /// Fails with `AgentError.NotImplemented` when the agent does not support
    /// options, rather than silently falling back to `process()`. An error is the
    /// right answer for the direct call: a caller who reached for this method
    /// asked for the options to take effect, and quietly running without them is
    /// exactly the silent-wrong behaviour of the bug this fixes (#801). Wrappers
    /// that want the graceful path should call `processWithOptions`, which makes
    /// the fallback explicit at the call site.
    pub fn processWith(self: Agent, message: Message, options: *const CallOptions) !Result {
        const impl = self.vtable.process_with orelse return AgentError.NotImplemented;
        return impl(self.ptr, message, options);
    }

    /// Process a message under options where the agent supports them, plainly
    /// where it does not.
    ///
    /// The one place the capability check lives, so wrappers do not each
    /// reimplement it. An empty option set takes the plain `process` path, so an
    /// options-aware agent is never handed an all-null `CallOptions` merely
    /// because this helper was used — "the caller asked for nothing" and "the
    /// caller asked" must stay distinguishable.
    ///
    /// This *does* drop the options when the agent cannot honour them, which is
    /// the pragmatic choice for a wrapper that did not construct what it wraps.
    /// It is safe only because the dropping is observable: `supportsOptions()`
    /// answers the question up front, and techniques report the outcome in their
    /// response metadata rather than leaving it invisible.
    pub fn processWithOptions(self: Agent, message: Message, options: *const CallOptions) !Result {
        if (options.isEmpty() or !self.supportsOptions()) {
            return self.process(message);
        }
        return self.processWith(message, options);
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

// ============================================================================
// Per-call options capability (#801)
// ============================================================================
//
// These call through the `Agent` interface rather than the concrete type. The
// vtable slot is a function pointer, so referencing `processWith` proves nothing
// about the forward inside it — Zig only analyses what it reaches (#811), and a
// helper that accepts an `options` parameter and drops it compiles perfectly.
// Every assertion below is on the options the *implementation* received.

/// Agent that records the options it was handed, and can be built with or
/// without the `process_with` slot.
const OptionsRecordingAgent = struct {
    allocator: Allocator,
    /// Options seen by the most recent processWith call.
    seen_temperature: ?f64 = null,
    seen_max_tokens: ?usize = null,
    /// How each call arrived. A phase that drops its options still returns a
    /// response, so the entry path is the only thing that distinguishes a
    /// working forward from a discarded one.
    plain_calls: usize = 0,
    options_calls: usize = 0,

    fn agent(self: *OptionsRecordingAgent) Agent {
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

    /// The same agent with the optional slot left unset — what every agent in
    /// the tree looked like before this change, and what most still look like.
    fn agentWithoutOptions(self: *OptionsRecordingAgent) Agent {
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
        _ = ptr;
        return "options_recorder";
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "recording";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *OptionsRecordingAgent = @ptrCast(@alignCast(ptr));
        self.plain_calls += 1;
        _ = message;
        const response = Message.withText(self.allocator, .assistant, "ok") catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };
        return Result{ .ok = response };
    }

    fn processWithImpl(ptr: *anyopaque, message: Message, options: *const CallOptions) AgentError!Result {
        const self: *OptionsRecordingAgent = @ptrCast(@alignCast(ptr));
        self.options_calls += 1;
        self.seen_temperature = options.temperature;
        self.seen_max_tokens = options.max_tokens;
        _ = message;
        const response = Message.withText(self.allocator, .assistant, "ok") catch {
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
        const self: *OptionsRecordingAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(self, allocator);
        defer allocator.free(caps);
        return createDefaultIntrospectionResult(allocator, "options_recorder", caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        _ = ptr;
    }
};

test "supportsOptions reflects whether the vtable slot is set" {
    const allocator = std.testing.allocator;

    var recorder = OptionsRecordingAgent{ .allocator = allocator };

    try std.testing.expect(recorder.agent().supportsOptions());
    // The slot defaults to null, so an agent that never heard of options says so
    // rather than claiming a capability it lacks.
    try std.testing.expect(!recorder.agentWithoutOptions().supportsOptions());
}

test "EchoAgent does not claim the options capability" {
    const allocator = std.testing.allocator;

    var echo = try EchoAgent.init(allocator);
    const echo_agent = echo.agent();
    defer echo_agent.deinit();

    // Adding a defaulted field must not silently opt 90-odd existing vtable
    // literals into a capability none of them implement.
    try std.testing.expect(!echo_agent.supportsOptions());
}

test "processWith delivers the options to the implementation" {
    const allocator = std.testing.allocator;

    var recorder = OptionsRecordingAgent{ .allocator = allocator };
    const recorder_agent = recorder.agent();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var options = CallOptions.init(allocator);
    defer options.deinit();
    try options.withTemperature(0.85);
    try options.withMaxTokens(64);

    var response = try (try recorder_agent.processWith(msg, &options)).unwrap();
    defer response.deinit();

    try std.testing.expectEqual(@as(usize, 1), recorder.options_calls);
    try std.testing.expectEqual(@as(usize, 0), recorder.plain_calls);
    try std.testing.expectEqual(@as(f64, 0.85), recorder.seen_temperature.?);
    try std.testing.expectEqual(@as(usize, 64), recorder.seen_max_tokens.?);
}

test "processWith errors rather than silently ignoring the options" {
    const allocator = std.testing.allocator;

    var recorder = OptionsRecordingAgent{ .allocator = allocator };
    const plain_agent = recorder.agentWithoutOptions();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var options = CallOptions.init(allocator);
    defer options.deinit();
    try options.withTemperature(0.85);

    // Falling back to process() here would accept a temperature and discard it —
    // the exact failure mode of #801. The caller asked for the options to apply.
    try std.testing.expectError(
        AgentError.NotImplemented,
        plain_agent.processWith(msg, &options),
    );
    try std.testing.expectEqual(@as(usize, 0), recorder.plain_calls);
}

test "processWithOptions takes the options path when it can" {
    const allocator = std.testing.allocator;

    var recorder = OptionsRecordingAgent{ .allocator = allocator };
    const recorder_agent = recorder.agent();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var options = CallOptions.init(allocator);
    defer options.deinit();
    try options.withTemperature(0.3);

    var response = try (try recorder_agent.processWithOptions(msg, &options)).unwrap();
    defer response.deinit();

    try std.testing.expectEqual(@as(usize, 1), recorder.options_calls);
    try std.testing.expectEqual(@as(usize, 0), recorder.plain_calls);
    try std.testing.expectEqual(@as(f64, 0.3), recorder.seen_temperature.?);
}

test "processWithOptions falls back to process when the agent cannot honour options" {
    const allocator = std.testing.allocator;

    var recorder = OptionsRecordingAgent{ .allocator = allocator };
    const plain_agent = recorder.agentWithoutOptions();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var options = CallOptions.init(allocator);
    defer options.deinit();
    try options.withTemperature(0.3);

    var response = try (try plain_agent.processWithOptions(msg, &options)).unwrap();
    defer response.deinit();

    // The wrapper keeps working; the drop is observable via supportsOptions.
    try std.testing.expectEqual(@as(usize, 1), recorder.plain_calls);
    try std.testing.expectEqual(@as(usize, 0), recorder.options_calls);
}

test "processWithOptions takes the plain path for an empty option set" {
    const allocator = std.testing.allocator;

    var recorder = OptionsRecordingAgent{ .allocator = allocator };
    const recorder_agent = recorder.agent();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var options = CallOptions.init(allocator);
    defer options.deinit();

    var response = try (try recorder_agent.processWithOptions(msg, &options)).unwrap();
    defer response.deinit();

    // An options-aware agent must not be handed an all-null CallOptions just
    // because the helper was used: "asked for nothing" is not "asked".
    try std.testing.expectEqual(@as(usize, 1), recorder.plain_calls);
    try std.testing.expectEqual(@as(usize, 0), recorder.options_calls);
}

test "processWithOptions treats temperature 0 as a real request" {
    const allocator = std.testing.allocator;

    var recorder = OptionsRecordingAgent{ .allocator = allocator };
    const recorder_agent = recorder.agent();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var options = CallOptions.init(allocator);
    defer options.deinit();
    try options.withTemperature(0.0);

    var response = try (try recorder_agent.processWithOptions(msg, &options)).unwrap();
    defer response.deinit();

    // 0.0 is greedy decoding, not an absent option. A truthiness check on the
    // value — rather than on the optional — would route this to process() and
    // drop it.
    try std.testing.expectEqual(@as(usize, 1), recorder.options_calls);
    try std.testing.expectEqual(@as(f64, 0.0), recorder.seen_temperature.?);
}

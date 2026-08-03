/// Minimal LLM interface for agent-LLM interaction
///
/// This module provides the minimal contract that all LLM adapters must implement.
/// The interface is intentionally small to maximize flexibility while ensuring
/// consistency across providers.
///
/// Design principles:
/// - Minimal: Only core methods (complete, stream, model)
/// - Flexible: Accepts CallOptions for provider-specific options
/// - Consistent: Works with Agenkit Message interface
/// - Swappable: Change providers without changing agent code
///
/// Example:
/// ```zig
/// const openai = @import("adapter/openai.zig");
///
/// var llm_impl = try openai.OpenAILLM.init(allocator, api_key, "gpt-4-turbo");
/// defer llm_impl.deinit();
/// const llm = llm_impl.asLLM();
///
/// const messages = [_]*Message{ /* ... */ };
/// var options = CallOptions.init(allocator);
/// defer options.deinit();
/// options.temperature = 0.7;
///
/// const response = try llm.complete(allocator, &messages, &options);
/// defer response.deinit();
/// ```
const std = @import("std");
const Message = @import("../message.zig").Message;
const Allocator = std.mem.Allocator;

/// Minimal LLM interface for agent-LLM interaction
pub const LLM = struct {
    ptr: *anyopaque,
    vtable: *const VTable,

    pub const VTable = struct {
        /// Complete generates a single completion from the LLM
        complete: *const fn (
            ptr: *anyopaque,
            allocator: Allocator,
            messages: []const *Message,
            options: *const CallOptions,
        ) anyerror!*Message,

        /// Stream generates completion chunks from the LLM
        stream: *const fn (
            ptr: *anyopaque,
            allocator: Allocator,
            messages: []const *Message,
            options: *const CallOptions,
        ) anyerror!StreamIterator,

        /// Model returns the model identifier
        model: *const fn (ptr: *anyopaque) []const u8,

        /// Deinit cleans up resources
        deinit: *const fn (ptr: *anyopaque) void,
    };

    /// Complete generates a single completion from the LLM
    ///
    /// This method sends a list of messages to the LLM and returns a single
    /// response message. The conversation history is passed as a list of
    /// Agenkit Messages, which the adapter converts to the provider's format.
    ///
    /// Parameters:
    ///   - allocator: Allocator for response allocation
    ///   - messages: Conversation history as Agenkit Messages
    ///   - options: Provider-specific options (temperature, max_tokens, etc.)
    ///
    /// Returns:
    ///   - Response from the LLM as an Agenkit Message with:
    ///     * Role: "assistant"
    ///     * Content: The generated text
    ///     * Metadata: Provider-specific data (usage stats, model name, etc.)
    ///
    /// Errors:
    ///   - Provider-specific errors for API failures (auth, rate limits, etc.)
    pub fn complete(
        self: LLM,
        allocator: Allocator,
        messages: []const *Message,
        options: *const CallOptions,
    ) !*Message {
        return try self.vtable.complete(self.ptr, allocator, messages, options);
    }

    /// Stream generates completion chunks from the LLM
    ///
    /// This method sends messages to the LLM and streams back response chunks
    /// as they're generated. Each chunk is yielded through the iterator.
    ///
    /// Parameters:
    ///   - allocator: Allocator for stream allocation
    ///   - messages: Conversation history as Agenkit Messages
    ///   - options: Provider-specific options
    ///
    /// Returns:
    ///   - StreamIterator that yields Message chunks as they arrive. Each chunk contains:
    ///     * Role: "assistant"
    ///     * Content: Partial text (may be a single token or character)
    ///     * Metadata: {"streaming": true, ...}
    ///
    /// Note:
    ///   If streaming is not supported, return error immediately.
    pub fn stream(
        self: LLM,
        allocator: Allocator,
        messages: []const *Message,
        options: *const CallOptions,
    ) !StreamIterator {
        return try self.vtable.stream(self.ptr, allocator, messages, options);
    }

    /// Model returns the model identifier for this LLM instance
    ///
    /// Returns:
    ///   Model name/identifier (e.g., "claude-3-5-sonnet-20241022", "gpt-4-turbo")
    pub fn model(self: LLM) []const u8 {
        return self.vtable.model(self.ptr);
    }

    /// Deinit cleans up LLM resources
    pub fn deinit(self: LLM) void {
        self.vtable.deinit(self.ptr);
    }
};

/// Call options for LLM requests
///
/// Re-exported from `call_options.zig`, which is core rather than adapter-level:
/// `agent.zig` needs this type for the optional `processWith` capability that
/// wrappers use to vary inference settings per call (#801), and core cannot
/// depend on `adapter/`. Every adapter keeps referring to it as
/// `llm.CallOptions`, so nothing at this layer changed.
pub const CallOptions = @import("../call_options.zig").CallOptions;

/// Stream iterator for streaming responses
pub const StreamIterator = struct {
    ptr: *anyopaque,
    vtable: *const StreamVTable,

    pub const StreamVTable = struct {
        /// Next returns the next message chunk, or null if done
        next: *const fn (ptr: *anyopaque, allocator: Allocator) anyerror!?*Message,

        /// Deinit cleans up stream resources
        deinit: *const fn (ptr: *anyopaque) void,
    };

    /// Get next message chunk
    ///
    /// Returns:
    ///   - Next Message chunk, or null if stream is complete
    ///
    /// Errors:
    ///   - Provider-specific errors for streaming failures
    pub fn next(self: *StreamIterator, allocator: Allocator) !?*Message {
        return try self.vtable.next(self.ptr, allocator);
    }

    /// Clean up stream resources
    pub fn deinit(self: *StreamIterator) void {
        self.vtable.deinit(self.ptr);
    }
};

/// Common LLM errors
pub const LLMError = error{
    AuthenticationFailed,
    RateLimitExceeded,
    ModelNotFound,
    InvalidRequest,
    ServerError,
    NetworkError,
    StreamingNotSupported,
    InvalidResponse,
    InvalidTemperature,
    InvalidMaxTokens,
    InvalidTopP,
};

// ============================================================================
// Tests
// ============================================================================
//
// The CallOptions tests moved with the type to `call_options.zig`. What is left
// here is the part of this file no test had ever exercised: the `LLM` and
// `StreamIterator` interface wrappers. Their bodies are one-line vtable
// forwards, and Zig only analyses functions it reaches — the #811 lesson — so
// they have to be called through the interface, not merely referenced.

/// LLM stub that records what it was handed and replays scripted chunks.
const RecordingLLM = struct {
    allocator: Allocator,
    /// The options pointer of the most recent complete()/stream() call.
    last_temperature: ?f64 = null,
    complete_calls: usize = 0,
    stream_calls: usize = 0,
    deinit_calls: usize = 0,

    fn asLLM(self: *RecordingLLM) LLM {
        return LLM{
            .ptr = self,
            .vtable = &.{
                .complete = completeImpl,
                .stream = streamImpl,
                .model = modelImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn completeImpl(
        ptr: *anyopaque,
        allocator: Allocator,
        messages: []const *Message,
        options: *const CallOptions,
    ) anyerror!*Message {
        const self: *RecordingLLM = @ptrCast(@alignCast(ptr));
        self.complete_calls += 1;
        self.last_temperature = options.temperature;

        const text = if (messages.len > 0) try messages[0].contentAsText() else "";
        const msg = try allocator.create(Message);
        errdefer allocator.destroy(msg);
        msg.* = try Message.withText(allocator, .assistant, text);
        return msg;
    }

    fn streamImpl(
        ptr: *anyopaque,
        allocator: Allocator,
        messages: []const *Message,
        options: *const CallOptions,
    ) anyerror!StreamIterator {
        const self: *RecordingLLM = @ptrCast(@alignCast(ptr));
        self.stream_calls += 1;
        self.last_temperature = options.temperature;
        _ = messages;

        const iter = try allocator.create(ChunkIterator);
        iter.* = ChunkIterator{ .allocator = allocator, .remaining = 2 };
        return iter.asIterator();
    }

    fn modelImpl(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "recording-llm";
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *RecordingLLM = @ptrCast(@alignCast(ptr));
        self.deinit_calls += 1;
    }
};

/// Stream that yields a fixed number of chunks, then null.
const ChunkIterator = struct {
    allocator: Allocator,
    remaining: usize,

    fn asIterator(self: *ChunkIterator) StreamIterator {
        return StreamIterator{
            .ptr = self,
            .vtable = &.{ .next = nextImpl, .deinit = deinitImpl },
        };
    }

    fn nextImpl(ptr: *anyopaque, allocator: Allocator) anyerror!?*Message {
        const self: *ChunkIterator = @ptrCast(@alignCast(ptr));
        if (self.remaining == 0) return null;
        self.remaining -= 1;

        const msg = try allocator.create(Message);
        errdefer allocator.destroy(msg);
        msg.* = try Message.withText(allocator, .assistant, "chunk");
        return msg;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *ChunkIterator = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};

test "LLM.complete forwards messages and options through the vtable" {
    const allocator = std.testing.allocator;

    var impl = RecordingLLM{ .allocator = allocator };
    const llm = impl.asLLM();

    var prompt = try Message.withText(allocator, .user, "hello");
    defer prompt.deinit();

    var options = CallOptions.init(allocator);
    defer options.deinit();
    try options.withTemperature(0.4);

    const messages = [_]*Message{&prompt};
    const response = try llm.complete(allocator, &messages, &options);
    defer {
        response.deinit();
        allocator.destroy(response);
    }

    try std.testing.expectEqual(@as(usize, 1), impl.complete_calls);
    // The options must arrive as configured, not as a default.
    try std.testing.expectEqual(@as(f64, 0.4), impl.last_temperature.?);
    try std.testing.expectEqualStrings("hello", try response.contentAsText());
}

test "LLM.complete forwards an unset temperature as unset" {
    const allocator = std.testing.allocator;

    var impl = RecordingLLM{ .allocator = allocator };
    const llm = impl.asLLM();

    var prompt = try Message.withText(allocator, .user, "hi");
    defer prompt.deinit();

    var options = CallOptions.init(allocator);
    defer options.deinit();

    const messages = [_]*Message{&prompt};
    const response = try llm.complete(allocator, &messages, &options);
    defer {
        response.deinit();
        allocator.destroy(response);
    }

    // Substituting a default here is the #801 failure mode one layer down: the
    // adapter would send a temperature the caller never asked for.
    try std.testing.expect(impl.last_temperature == null);
}

test "LLM.stream yields every chunk and then null" {
    const allocator = std.testing.allocator;

    var impl = RecordingLLM{ .allocator = allocator };
    const llm = impl.asLLM();

    var prompt = try Message.withText(allocator, .user, "go");
    defer prompt.deinit();

    var options = CallOptions.init(allocator);
    defer options.deinit();
    try options.withTopP(0.8);

    const messages = [_]*Message{&prompt};
    var iter = try llm.stream(allocator, &messages, &options);
    defer iter.deinit();

    var count: usize = 0;
    while (try iter.next(allocator)) |chunk| {
        defer {
            chunk.deinit();
            allocator.destroy(chunk);
        }
        try std.testing.expectEqualStrings("chunk", try chunk.contentAsText());
        count += 1;
    }

    try std.testing.expectEqual(@as(usize, 2), count);
    try std.testing.expectEqual(@as(usize, 1), impl.stream_calls);
}

test "LLM.model and LLM.deinit reach the implementation" {
    const allocator = std.testing.allocator;

    var impl = RecordingLLM{ .allocator = allocator };
    const llm = impl.asLLM();

    try std.testing.expectEqualStrings("recording-llm", llm.model());

    try std.testing.expectEqual(@as(usize, 0), impl.deinit_calls);
    llm.deinit();
    try std.testing.expectEqual(@as(usize, 1), impl.deinit_calls);
}

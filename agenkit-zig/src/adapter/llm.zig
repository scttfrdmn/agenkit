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
pub const CallOptions = struct {
    /// Sampling temperature (typically 0.0-2.0)
    temperature: ?f64 = null,

    /// Maximum tokens to generate
    max_tokens: ?usize = null,

    /// Nucleus sampling parameter
    top_p: ?f64 = null,

    /// Provider-specific options
    extra: std.StringHashMap([]const u8),

    /// Initialize call options
    pub fn init(allocator: Allocator) CallOptions {
        return CallOptions{
            .extra = std.StringHashMap([]const u8).init(allocator),
        };
    }

    /// Set temperature (must be between 0 and 2)
    pub fn withTemperature(self: *CallOptions, temperature: f64) !void {
        if (temperature < 0.0 or temperature > 2.0) {
            return error.InvalidTemperature;
        }
        self.temperature = temperature;
    }

    /// Set max tokens (must be positive)
    pub fn withMaxTokens(self: *CallOptions, max_tokens: usize) !void {
        if (max_tokens == 0) {
            return error.InvalidMaxTokens;
        }
        self.max_tokens = max_tokens;
    }

    /// Set top_p (must be between 0 and 1)
    pub fn withTopP(self: *CallOptions, top_p: f64) !void {
        if (top_p < 0.0 or top_p > 1.0) {
            return error.InvalidTopP;
        }
        self.top_p = top_p;
    }

    /// Add provider-specific option
    pub fn withExtra(self: *CallOptions, key: []const u8, value: []const u8) !void {
        try self.extra.put(key, value);
    }

    /// Clean up resources
    pub fn deinit(self: *CallOptions) void {
        self.extra.deinit();
    }
};

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

// Tests
test "CallOptions initialization" {
    const allocator = std.testing.allocator;

    var options = CallOptions.init(allocator);
    defer options.deinit();

    try std.testing.expect(options.temperature == null);
    try std.testing.expect(options.max_tokens == null);
    try std.testing.expect(options.top_p == null);
}

test "CallOptions with values" {
    const allocator = std.testing.allocator;

    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTemperature(0.7);
    try options.withMaxTokens(1024);
    try options.withTopP(0.9);

    try std.testing.expectEqual(@as(f64, 0.7), options.temperature.?);
    try std.testing.expectEqual(@as(usize, 1024), options.max_tokens.?);
    try std.testing.expectEqual(@as(f64, 0.9), options.top_p.?);
}

test "CallOptions with extra" {
    const allocator = std.testing.allocator;

    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withExtra("frequency_penalty", "0.5");
    try options.withExtra("presence_penalty", "0.3");

    try std.testing.expect(options.extra.contains("frequency_penalty"));
    try std.testing.expect(options.extra.contains("presence_penalty"));
}

// ============================================================================
// Temperature Validation Tests
// ============================================================================

test "CallOptions valid temperature 0" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTemperature(0.0);
    try std.testing.expectEqual(@as(f64, 0.0), options.temperature.?);
}

test "CallOptions valid temperature 1" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTemperature(1.0);
    try std.testing.expectEqual(@as(f64, 1.0), options.temperature.?);
}

test "CallOptions valid temperature 2" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTemperature(2.0);
    try std.testing.expectEqual(@as(f64, 2.0), options.temperature.?);
}

test "CallOptions invalid temperature negative" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    const result = options.withTemperature(-0.5);
    try std.testing.expectError(error.InvalidTemperature, result);
}

test "CallOptions invalid temperature too high" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    const result = options.withTemperature(3.0);
    try std.testing.expectError(error.InvalidTemperature, result);
}

// ============================================================================
// Max Tokens Validation Tests
// ============================================================================

test "CallOptions valid max_tokens" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withMaxTokens(1024);
    try std.testing.expectEqual(@as(usize, 1024), options.max_tokens.?);
}

test "CallOptions invalid max_tokens zero" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    const result = options.withMaxTokens(0);
    try std.testing.expectError(error.InvalidMaxTokens, result);
}

// ============================================================================
// Top P Validation Tests
// ============================================================================

test "CallOptions valid top_p" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTopP(0.9);
    try std.testing.expectEqual(@as(f64, 0.9), options.top_p.?);
}

test "CallOptions invalid top_p negative" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    const result = options.withTopP(-0.1);
    try std.testing.expectError(error.InvalidTopP, result);
}

test "CallOptions invalid top_p too high" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    const result = options.withTopP(1.5);
    try std.testing.expectError(error.InvalidTopP, result);
}

// ============================================================================
// Boundary Value Tests
// ============================================================================

test "CallOptions boundary temperature exactly 0" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTemperature(0.0);
    try std.testing.expectEqual(@as(f64, 0.0), options.temperature.?);
}

test "CallOptions boundary temperature exactly 2" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTemperature(2.0);
    try std.testing.expectEqual(@as(f64, 2.0), options.temperature.?);
}

test "CallOptions boundary max_tokens exactly 1" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withMaxTokens(1);
    try std.testing.expectEqual(@as(usize, 1), options.max_tokens.?);
}

test "CallOptions boundary top_p exactly 0" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTopP(0.0);
    try std.testing.expectEqual(@as(f64, 0.0), options.top_p.?);
}

test "CallOptions boundary top_p exactly 1" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTopP(1.0);
    try std.testing.expectEqual(@as(f64, 1.0), options.top_p.?);
}

/// Anthropic LLM adapter (Claude models)
///
/// This adapter wraps Anthropic's Messages API to provide a consistent Agenkit
/// interface for Claude models (Opus, Sonnet, Haiku).
///
/// Example:
/// ```zig
/// var llm_impl = try AnthropicLLM.init(allocator, api_key, "claude-sonnet-4-6");
/// defer llm_impl.deinit();
/// const llm = llm_impl.asLLM();
///
/// const messages = [_]*Message{ /* ... */ };
/// var options = CallOptions.init(allocator);
/// defer options.deinit();
/// options.withMaxTokens(1024); // max_tokens is required for Anthropic
///
/// const response = try llm.complete(allocator, &messages, &options);
/// defer response.deinit();
/// ```
const std = @import("std");
const ioc = @import("../io_compat.zig");
const agkenv = @import("../env_compat.zig");
const llm = @import("llm.zig");
const Message = @import("../message.zig").Message;
const Role = @import("../message.zig").Role;
const Allocator = std.mem.Allocator;

/// Anthropic streaming iterator implementation
const AnthropicStream = struct {
    allocator: Allocator,
    self: *AnthropicLLM,
    buffer: std.ArrayList(u8),
    chunks: std.ArrayList([]const u8),
    current_index: usize,
    completed: bool,

    /// Make streaming HTTP request to Anthropic API
    fn makeStreamRequest(self: *AnthropicStream, body: []const u8) !void {
        var client = std.http.Client{ .allocator = self.allocator, .io = ioc.io() };
        defer client.deinit();

        const uri_str = try std.fmt.allocPrint(
            self.allocator,
            "{s}/v1/messages",
            .{self.self.base_url},
        );
        defer self.allocator.free(uri_str);

        const headers = [_]std.http.Header{
            .{ .name = "Content-Type", .value = "application/json" },
            .{ .name = "x-api-key", .value = self.self.api_key },
            .{ .name = "anthropic-version", .value = self.self.api_version },
        };

        var response_buffer: std.Io.Writer.Allocating = .init(self.allocator);
        defer response_buffer.deinit();

        const result = try client.fetch(.{
            .location = .{ .url = uri_str },
            .method = .POST,
            .payload = body,
            .extra_headers = &headers,
            .response_writer = &response_buffer.writer,
        });

        if (result.status != .ok) {
            return error.ServerError;
        }

        const data = try response_buffer.toOwnedSlice();
        defer self.allocator.free(data);
        try self.parseSSEStream(data);
    }

    /// Parse SSE stream and extract text chunks
    fn parseSSEStream(self: *AnthropicStream, data: []const u8) !void {
        var lines = std.mem.splitSequence(u8, data, "\n");

        while (lines.next()) |line| {
            // Skip empty lines
            if (line.len == 0) continue;

            // Look for "data: " prefix
            if (std.mem.startsWith(u8, line, "data: ")) {
                const json_str = line[6..]; // Skip "data: " prefix

                // Skip [DONE] marker
                if (std.mem.eql(u8, json_str, "[DONE]")) {
                    continue;
                }

                // Parse JSON event
                const parsed = std.json.parseFromSlice(
                    std.json.Value,
                    self.allocator,
                    json_str,
                    .{},
                ) catch continue;
                defer parsed.deinit();

                const event = parsed.value.object;

                // Look for content_block_delta events
                if (event.get("type")) |event_type| {
                    if (std.mem.eql(u8, event_type.string, "content_block_delta")) {
                        if (event.get("delta")) |delta| {
                            if (delta.object.get("type")) |delta_type| {
                                if (std.mem.eql(u8, delta_type.string, "text_delta")) {
                                    if (delta.object.get("text")) |text| {
                                        // Store text chunk
                                        const chunk = try self.allocator.dupe(u8, text.string);
                                        try self.chunks.append(self.allocator, chunk);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    fn deinit(self: *AnthropicStream) void {
        // Free all chunks
        for (self.chunks.items) |chunk| {
            self.allocator.free(chunk);
        }
        self.chunks.deinit(self.allocator);
        self.buffer.deinit(self.allocator);
        self.allocator.destroy(self);
    }
};

/// Stream next implementation
fn streamNext(ptr: *anyopaque, allocator: Allocator) !?*Message {
    const self: *AnthropicStream = @ptrCast(@alignCast(ptr));

    if (self.current_index >= self.chunks.items.len) {
        return null; // Stream complete
    }

    const text = self.chunks.items[self.current_index];
    self.current_index += 1;

    // Create message chunk
    const msg = try allocator.create(Message);
    msg.* = try Message.withText(allocator, .assistant, text);
    try msg.setMetadata("streaming", std.json.Value{ .bool = true });

    return msg;
}

/// Stream deinit implementation
fn streamDeinit(ptr: *anyopaque) void {
    const self: *AnthropicStream = @ptrCast(@alignCast(ptr));
    self.deinit();
}

/// Anthropic LLM adapter
pub const AnthropicLLM = struct {
    allocator: Allocator,
    api_key: []const u8,
    model_name: []const u8,
    base_url: []const u8,
    api_version: []const u8,

    /// Initialize Anthropic adapter
    ///
    /// Parameters:
    ///   - allocator: Memory allocator
    ///   - api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
    ///   - model: Model identifier (e.g., "claude-3-opus-20240229", "claude-3-sonnet-20240229")
    ///
    /// Returns:
    ///   Initialized AnthropicLLM instance
    pub fn init(
        allocator: Allocator,
        api_key: []const u8,
        model_str: []const u8,
    ) !*AnthropicLLM {
        const self = try allocator.create(AnthropicLLM);
        errdefer allocator.destroy(self);

        const key = if (api_key.len > 0)
            try allocator.dupe(u8, api_key)
        else blk: {
            const env_key = agkenv.getEnvVarOwned(allocator, "ANTHROPIC_API_KEY") catch {
                return error.MissingAPIKey;
            };
            break :blk env_key;
        };

        const model_copy = if (model_str.len > 0)
            try allocator.dupe(u8, model_str)
        else
            try allocator.dupe(u8, "claude-sonnet-4-6");

        self.* = AnthropicLLM{
            .allocator = allocator,
            .api_key = key,
            .model_name = model_copy,
            .base_url = try allocator.dupe(u8, "https://api.anthropic.com"),
            .api_version = try allocator.dupe(u8, "2023-06-01"),
        };

        return self;
    }

    /// Convert to LLM interface
    pub fn asLLM(self: *AnthropicLLM) llm.LLM {
        return llm.LLM{
            .ptr = self,
            .vtable = &.{
                .complete = complete,
                .stream = stream,
                .model = model,
                .deinit = deinitVTable,
            },
        };
    }

    /// Public deinit for direct use
    pub fn deinit(self: *AnthropicLLM) void {
        self.allocator.free(self.api_key);
        self.allocator.free(self.model_name);
        self.allocator.free(self.base_url);
        self.allocator.free(self.api_version);
        self.allocator.destroy(self);
    }

    /// Complete implementation
    fn complete(
        ptr: *anyopaque,
        allocator: Allocator,
        messages: []const *Message,
        options: *const llm.CallOptions,
    ) !*Message {
        const self: *AnthropicLLM = @ptrCast(@alignCast(ptr));

        const request_body = try self.buildRequestBody(allocator, messages, options);
        defer allocator.free(request_body);

        const response_body = try self.makeRequest(allocator, request_body);
        defer allocator.free(response_body);

        return try self.parseResponse(allocator, response_body);
    }

    /// Stream implementation
    fn stream(
        ptr: *anyopaque,
        allocator: Allocator,
        messages: []const *Message,
        options: *const llm.CallOptions,
    ) !llm.StreamIterator {
        const self: *AnthropicLLM = @ptrCast(@alignCast(ptr));

        // Build request body with stream=true
        const request_body = try self.buildStreamRequestBody(allocator, messages, options);
        defer allocator.free(request_body);

        // Create stream iterator
        const stream_impl = try allocator.create(AnthropicStream);
        errdefer allocator.destroy(stream_impl);

        stream_impl.* = AnthropicStream{
            .allocator = allocator,
            .self = self,
            .buffer = std.ArrayList(u8).empty,
            .chunks = std.ArrayList([]const u8).empty,
            .current_index = 0,
            .completed = false,
        };

        // Make streaming request
        try stream_impl.makeStreamRequest(request_body);

        return llm.StreamIterator{
            .ptr = stream_impl,
            .vtable = &.{
                .next = streamNext,
                .deinit = streamDeinit,
            },
        };
    }

    /// Model implementation
    fn model(ptr: *anyopaque) []const u8 {
        const self: *AnthropicLLM = @ptrCast(@alignCast(ptr));
        return self.model_name;
    }

    /// Deinit implementation for VTable
    fn deinitVTable(ptr: *anyopaque) void {
        const self: *AnthropicLLM = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    /// Build Anthropic API streaming request body
    fn buildStreamRequestBody(
        self: *AnthropicLLM,
        allocator: Allocator,
        messages: []const *Message,
        options: *const llm.CallOptions,
    ) ![]const u8 {
        var json = std.ArrayList(u8).empty;
        defer json.deinit(allocator);

        try json.appendSlice(allocator, "{\"model\":\"");
        try json.appendSlice(allocator, self.model_name);
        try json.appendSlice(allocator, "\",\"stream\":true,\"messages\":[");

        // Separate system message (same logic as buildRequestBody)
        var has_system = false;
        var system_content: []const u8 = "";

        for (messages) |msg| {
            if (msg.role == .system) {
                system_content = switch (msg.content) {
                    .text => |t| t,
                    .structured => "",
                };
                has_system = true;
                break;
            }
        }

        var first = true;
        for (messages) |msg| {
            if (msg.role == .system) continue;

            if (!first) try json.append(allocator, ',');
            first = false;

            try json.appendSlice(allocator, "{\"role\":\"");
            const role_str = switch (msg.role) {
                .user => "user",
                .assistant => "assistant",
                .system => "user",
                .tool => "user",
                .agent => "assistant",
            };
            try json.appendSlice(allocator, role_str);
            try json.appendSlice(allocator, "\",\"content\":\"");

            const content = switch (msg.content) {
                .text => |t| t,
                .structured => "",
            };

            for (content) |c| {
                if (c == '"') {
                    try json.appendSlice(allocator, "\\\"");
                } else if (c == '\\') {
                    try json.appendSlice(allocator, "\\\\");
                } else if (c == '\n') {
                    try json.appendSlice(allocator, "\\n");
                } else if (c == '\r') {
                    try json.appendSlice(allocator, "\\r");
                } else if (c == '\t') {
                    try json.appendSlice(allocator, "\\t");
                } else {
                    try json.append(allocator, c);
                }
            }

            try json.appendSlice(allocator, "\"}");
        }

        try json.append(allocator, ']');

        if (has_system) {
            try json.appendSlice(allocator, ",\"system\":\"");
            for (system_content) |c| {
                if (c == '"') {
                    try json.appendSlice(allocator, "\\\"");
                } else if (c == '\\') {
                    try json.appendSlice(allocator, "\\\\");
                } else if (c == '\n') {
                    try json.appendSlice(allocator, "\\n");
                } else if (c == '\r') {
                    try json.appendSlice(allocator, "\\r");
                } else if (c == '\t') {
                    try json.appendSlice(allocator, "\\t");
                } else {
                    try json.append(allocator, c);
                }
            }
            try json.append(allocator, '"');
        }

        const max_tokens = options.max_tokens orelse 4096;
        const max_tokens_str = try std.fmt.allocPrint(allocator, ",\"max_tokens\":{d}", .{max_tokens});
        defer allocator.free(max_tokens_str);
        try json.appendSlice(allocator, max_tokens_str);

        if (options.temperature) |temp| {
            const temp_str = try std.fmt.allocPrint(allocator, ",\"temperature\":{d}", .{temp});
            defer allocator.free(temp_str);
            try json.appendSlice(allocator, temp_str);
        }

        if (options.top_p) |top_p_val| {
            const top_p_str = try std.fmt.allocPrint(allocator, ",\"top_p\":{d}", .{top_p_val});
            defer allocator.free(top_p_str);
            try json.appendSlice(allocator, top_p_str);
        }

        try json.append(allocator, '}');

        return try json.toOwnedSlice(allocator);
    }

    /// Build Anthropic API request body
    fn buildRequestBody(
        self: *AnthropicLLM,
        allocator: Allocator,
        messages: []const *Message,
        options: *const llm.CallOptions,
    ) ![]const u8 {
        var json = std.ArrayList(u8).empty;
        defer json.deinit(allocator);

        try json.appendSlice(allocator, "{\"model\":\"");
        try json.appendSlice(allocator, self.model_name);
        try json.appendSlice(allocator, "\",\"messages\":[");

        // Separate system message from other messages (Anthropic requires this)
        var has_system = false;
        var system_content: []const u8 = "";

        // First pass: extract system message
        for (messages) |msg| {
            if (msg.role == .system) {
                system_content = switch (msg.content) {
                    .text => |t| t,
                    .structured => "",
                };
                has_system = true;
                break;
            }
        }

        // Second pass: add non-system messages
        var first = true;
        for (messages) |msg| {
            if (msg.role == .system) continue; // Skip system messages

            if (!first) try json.append(allocator, ',');
            first = false;

            try json.appendSlice(allocator, "{\"role\":\"");

            // Map roles (tool messages become user)
            const role_str = switch (msg.role) {
                .user => "user",
                .assistant => "assistant",
                .system => "user", // Should not happen due to filtering
                .tool => "user",
                .agent => "assistant",
            };

            try json.appendSlice(allocator, role_str);
            try json.appendSlice(allocator, "\",\"content\":\"");

            const content = switch (msg.content) {
                .text => |t| t,
                .structured => "",
            };

            // Escape special characters
            for (content) |c| {
                if (c == '"') {
                    try json.appendSlice(allocator, "\\\"");
                } else if (c == '\\') {
                    try json.appendSlice(allocator, "\\\\");
                } else if (c == '\n') {
                    try json.appendSlice(allocator, "\\n");
                } else if (c == '\r') {
                    try json.appendSlice(allocator, "\\r");
                } else if (c == '\t') {
                    try json.appendSlice(allocator, "\\t");
                } else {
                    try json.append(allocator, c);
                }
            }

            try json.appendSlice(allocator, "\"}");
        }

        try json.append(allocator, ']');

        // Add system message if present (as top-level field)
        if (has_system) {
            try json.appendSlice(allocator, ",\"system\":\"");
            for (system_content) |c| {
                if (c == '"') {
                    try json.appendSlice(allocator, "\\\"");
                } else if (c == '\\') {
                    try json.appendSlice(allocator, "\\\\");
                } else if (c == '\n') {
                    try json.appendSlice(allocator, "\\n");
                } else if (c == '\r') {
                    try json.appendSlice(allocator, "\\r");
                } else if (c == '\t') {
                    try json.appendSlice(allocator, "\\t");
                } else {
                    try json.append(allocator, c);
                }
            }
            try json.append(allocator, '"');
        }

        // max_tokens is REQUIRED for Anthropic
        const max_tokens = options.max_tokens orelse 4096;
        const max_tokens_str = try std.fmt.allocPrint(allocator, ",\"max_tokens\":{d}", .{max_tokens});
        defer allocator.free(max_tokens_str);
        try json.appendSlice(allocator, max_tokens_str);

        // Optional parameters
        if (options.temperature) |temp| {
            const temp_str = try std.fmt.allocPrint(allocator, ",\"temperature\":{d}", .{temp});
            defer allocator.free(temp_str);
            try json.appendSlice(allocator, temp_str);
        }

        if (options.top_p) |top_p_val| {
            const top_p_str = try std.fmt.allocPrint(allocator, ",\"top_p\":{d}", .{top_p_val});
            defer allocator.free(top_p_str);
            try json.appendSlice(allocator, top_p_str);
        }

        try json.append(allocator, '}');

        return try json.toOwnedSlice(allocator);
    }

    /// Make HTTP request to Anthropic API
    fn makeRequest(self: *AnthropicLLM, allocator: Allocator, body: []const u8) ![]const u8 {
        var client = std.http.Client{ .allocator = allocator, .io = ioc.io() };
        defer client.deinit();

        const uri_str = try std.fmt.allocPrint(
            allocator,
            "{s}/v1/messages",
            .{self.base_url},
        );
        defer allocator.free(uri_str);

        // Anthropic uses x-api-key header
        const headers = [_]std.http.Header{
            .{ .name = "Content-Type", .value = "application/json" },
            .{ .name = "x-api-key", .value = self.api_key },
            .{ .name = "anthropic-version", .value = self.api_version },
        };

        var response_body: std.Io.Writer.Allocating = .init(allocator);
        defer response_body.deinit();

        const result = try client.fetch(.{
            .location = .{ .url = uri_str },
            .method = .POST,
            .payload = body,
            .extra_headers = &headers,
            .response_writer = &response_body.writer,
        });

        if (result.status != .ok) {
            return error.ServerError;
        }

        return try response_body.toOwnedSlice();
    }

    /// Parse Anthropic API response
    fn parseResponse(self: *AnthropicLLM, allocator: Allocator, response_body: []const u8) !*Message {
        _ = self;

        const parsed = try std.json.parseFromSlice(
            std.json.Value,
            allocator,
            response_body,
            .{},
        );
        defer parsed.deinit();

        const root = parsed.value.object;

        // Extract content from content[0].text
        const content_array = root.get("content") orelse return error.InvalidResponse;
        if (content_array.array.items.len == 0) return error.InvalidResponse;

        const first_content = content_array.array.items[0].object;
        const text = first_content.get("text") orelse return error.InvalidResponse;

        // Create response message
        const msg = try allocator.create(Message);
        msg.* = try Message.withText(allocator, .assistant, text.string);

        // Add metadata
        if (root.get("stop_reason")) |stop_reason| {
            try msg.setMetadata("stop_reason", stop_reason);
        }

        if (root.get("usage")) |usage| {
            try msg.setMetadata("usage", usage);
        }

        if (root.get("model")) |model_val| {
            try msg.setMetadata("model", model_val);
        }

        return msg;
    }
};

// Tests
test "AnthropicLLM initialization" {
    const allocator = std.testing.allocator;

    var llm_impl = try AnthropicLLM.init(allocator, "test-api-key", "claude-sonnet-4-6");
    defer llm_impl.deinit();

    const llm_interface = llm_impl.asLLM();
    try std.testing.expectEqualStrings("claude-sonnet-4-6", llm_interface.model());
}

test "AnthropicLLM buildRequestBody" {
    const allocator = std.testing.allocator;

    var llm_impl = try AnthropicLLM.init(allocator, "test-key", "claude-3-opus-20240229");
    defer llm_impl.deinit();

    var system = try Message.withText(allocator, .system, "You are helpful.");
    defer system.deinit();

    var user = try Message.withText(allocator, .user, "Hello");
    defer user.deinit();

    const messages = [_]*Message{ &system, &user };

    var options = llm.CallOptions.init(allocator);
    defer options.deinit();
    options.temperature = 0.7;
    options.max_tokens = 512;

    const body = try llm_impl.buildRequestBody(allocator, &messages, &options);
    defer allocator.free(body);

    // Verify JSON structure
    try std.testing.expect(std.mem.indexOf(u8, body, "\"model\":\"claude-3-opus-20240229\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"system\":\"You are helpful.\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"max_tokens\":512") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"temperature\":0.7") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"role\":\"user\"") != null);
}

test "AnthropicLLM buildRequestBody without system" {
    const allocator = std.testing.allocator;

    var llm_impl = try AnthropicLLM.init(allocator, "test-key", "claude-3-haiku-20240307");
    defer llm_impl.deinit();

    var user = try Message.withText(allocator, .user, "Test");
    defer user.deinit();

    const messages = [_]*Message{&user};

    var options = llm.CallOptions.init(allocator);
    defer options.deinit();
    options.max_tokens = 100;

    const body = try llm_impl.buildRequestBody(allocator, &messages, &options);
    defer allocator.free(body);

    // Verify no system field
    try std.testing.expect(std.mem.indexOf(u8, body, "\"system\"") == null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"max_tokens\":100") != null);
}

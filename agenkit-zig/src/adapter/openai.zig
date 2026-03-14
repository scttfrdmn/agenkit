/// OpenAI LLM adapter for GPT models
///
/// This adapter wraps OpenAI's Chat Completions API to provide a consistent
/// Agenkit interface for GPT models. Supports both completion and streaming.
///
/// Example:
/// ```zig
/// var llm_impl = try OpenAILLM.init(allocator, api_key, "gpt-4-turbo");
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
const llm = @import("llm.zig");
const Message = @import("../message.zig").Message;
const Role = @import("../message.zig").Role;
const Allocator = std.mem.Allocator;

/// OpenAI streaming iterator implementation
const OpenAIStream = struct {
    allocator: Allocator,
    self: *OpenAILLM,
    chunks: std.ArrayList([]const u8),
    current_index: usize,

    fn makeStreamRequest(self: *OpenAIStream, body: []const u8) !void {
        var client = std.http.Client{ .allocator = self.allocator };
        defer client.deinit();

        const uri_str = try std.fmt.allocPrint(
            self.allocator,
            "{s}/chat/completions",
            .{self.self.base_url},
        );
        defer self.allocator.free(uri_str);

        const auth_value = try std.fmt.allocPrint(
            self.allocator,
            "Bearer {s}",
            .{self.self.api_key},
        );
        defer self.allocator.free(auth_value);

        const headers = [_]std.http.Header{
            .{ .name = "Content-Type", .value = "application/json" },
            .{ .name = "Authorization", .value = auth_value },
        };

        var response_buffer: std.io.Writer.Allocating = .init(self.allocator);
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

    fn parseSSEStream(self: *OpenAIStream, data: []const u8) !void {
        var lines = std.mem.splitSequence(u8, data, "\n");

        while (lines.next()) |line| {
            if (line.len == 0) continue;

            if (std.mem.startsWith(u8, line, "data: ")) {
                const json_str = line[6..];

                if (std.mem.eql(u8, json_str, "[DONE]")) {
                    continue;
                }

                const parsed = std.json.parseFromSlice(
                    std.json.Value,
                    self.allocator,
                    json_str,
                    .{},
                ) catch continue;
                defer parsed.deinit();

                const event = parsed.value.object;

                // Extract text from choices[0].delta.content
                if (event.get("choices")) |choices| {
                    if (choices.array.items.len > 0) {
                        const choice = choices.array.items[0].object;
                        if (choice.get("delta")) |delta| {
                            if (delta.object.get("content")) |content| {
                                const chunk = try self.allocator.dupe(u8, content.string);
                                try self.chunks.append(self.allocator, chunk);
                            }
                        }
                    }
                }
            }
        }
    }

    fn deinit(self: *OpenAIStream) void {
        for (self.chunks.items) |chunk| {
            self.allocator.free(chunk);
        }
        self.chunks.deinit(self.allocator);
        self.allocator.destroy(self);
    }
};

fn openaiStreamNext(ptr: *anyopaque, allocator: Allocator) !?*Message {
    const self: *OpenAIStream = @ptrCast(@alignCast(ptr));

    if (self.current_index >= self.chunks.items.len) {
        return null;
    }

    const text = self.chunks.items[self.current_index];
    self.current_index += 1;

    const msg = try allocator.create(Message);
    msg.* = try Message.withText(allocator, .assistant, text);
    try msg.setMetadata("streaming", std.json.Value{ .bool = true });

    return msg;
}

fn openaiStreamDeinit(ptr: *anyopaque) void {
    const self: *OpenAIStream = @ptrCast(@alignCast(ptr));
    self.deinit();
}

/// OpenAI LLM adapter
pub const OpenAILLM = struct {
    allocator: Allocator,
    api_key: []const u8,
    model_name: []const u8,
    base_url: []const u8,

    /// Initialize OpenAI adapter
    ///
    /// Parameters:
    ///   - allocator: Memory allocator
    ///   - api_key: OpenAI API key (or use OPENAI_API_KEY env var)
    ///   - model: Model identifier (e.g., "gpt-4-turbo", "gpt-4o")
    ///
    /// Returns:
    ///   Initialized OpenAILLM instance
    pub fn init(
        allocator: Allocator,
        api_key: []const u8,
        model_str: []const u8,
    ) !*OpenAILLM {
        const self = try allocator.create(OpenAILLM);
        errdefer allocator.destroy(self);

        const key = if (api_key.len > 0)
            try allocator.dupe(u8, api_key)
        else blk: {
            // Try environment variable
            const env_key = std.process.getEnvVarOwned(allocator, "OPENAI_API_KEY") catch {
                return error.MissingAPIKey;
            };
            break :blk env_key;
        };

        const model_copy = if (model_str.len > 0)
            try allocator.dupe(u8, model_str)
        else
            try allocator.dupe(u8, "gpt-4-turbo");

        self.* = OpenAILLM{
            .allocator = allocator,
            .api_key = key,
            .model_name = model_copy,
            .base_url = try allocator.dupe(u8, "https://api.openai.com/v1"),
        };

        return self;
    }

    /// Convert to LLM interface
    pub fn asLLM(self: *OpenAILLM) llm.LLM {
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
    pub fn deinit(self: *OpenAILLM) void {
        self.allocator.free(self.api_key);
        self.allocator.free(self.model_name);
        self.allocator.free(self.base_url);
        self.allocator.destroy(self);
    }

    /// Complete implementation
    fn complete(
        ptr: *anyopaque,
        allocator: Allocator,
        messages: []const *Message,
        options: *const llm.CallOptions,
    ) !*Message {
        const self: *OpenAILLM = @ptrCast(@alignCast(ptr));

        // Build request body
        const request_body = try self.buildRequestBody(allocator, messages, options, false);
        defer allocator.free(request_body);

        // Make HTTP request
        const response_body = try self.makeRequest(allocator, request_body);
        defer allocator.free(response_body);

        // Parse response
        return try self.parseResponse(allocator, response_body);
    }

    /// Stream implementation
    fn stream(
        ptr: *anyopaque,
        allocator: Allocator,
        messages: []const *Message,
        options: *const llm.CallOptions,
    ) !llm.StreamIterator {
        const self: *OpenAILLM = @ptrCast(@alignCast(ptr));

        // Build request body with stream=true
        const request_body = try self.buildRequestBody(allocator, messages, options, true);
        defer allocator.free(request_body);

        // Create stream iterator
        const stream_impl = try allocator.create(OpenAIStream);
        errdefer allocator.destroy(stream_impl);

        stream_impl.* = OpenAIStream{
            .allocator = allocator,
            .self = self,
            .chunks = std.ArrayList([]const u8){},
            .current_index = 0,
        };

        // Make streaming request
        try stream_impl.makeStreamRequest(request_body);

        return llm.StreamIterator{
            .ptr = stream_impl,
            .vtable = &.{
                .next = openaiStreamNext,
                .deinit = openaiStreamDeinit,
            },
        };
    }

    /// Model implementation
    fn model(ptr: *anyopaque) []const u8 {
        const self: *OpenAILLM = @ptrCast(@alignCast(ptr));
        return self.model_name;
    }

    /// Deinit implementation for VTable
    fn deinitVTable(ptr: *anyopaque) void {
        const self: *OpenAILLM = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    /// Build OpenAI API request body
    fn buildRequestBody(
        self: *OpenAILLM,
        allocator: Allocator,
        messages: []const *Message,
        options: *const llm.CallOptions,
        is_stream: bool,
    ) ![]const u8 {
        // Build JSON manually for now (simpler than using std.json API)
        // In Zig 0.15.2, ArrayList is unmanaged and requires allocator parameter
        var json = std.ArrayList(u8){};
        defer json.deinit(allocator);

        try json.appendSlice(allocator, "{\"model\":\"");
        try json.appendSlice(allocator, self.model_name);
        try json.appendSlice(allocator, "\",\"messages\":[");

        // Messages array
        for (messages, 0..) |msg, i| {
            if (i > 0) try json.append(allocator, ',');

            try json.appendSlice(allocator, "{\"role\":\"");
            try json.appendSlice(allocator, msg.role.toString());
            try json.appendSlice(allocator, "\",\"content\":");

            switch (msg.content) {
                .text => |t| {
                    // Text content: serialize as a JSON string
                    try json.append(allocator, '"');
                    for (t) |c| {
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
                },
                .structured => |val| {
                    // Structured content: serialize as JSON array (OpenAI multimodal format)
                    const val_json = try std.json.Stringify.valueAlloc(allocator, val, .{});
                    defer allocator.free(val_json);
                    try json.appendSlice(allocator, val_json);
                },
            }

            try json.append(allocator, '}');
        }

        try json.append(allocator, ']');

        // Options
        if (options.temperature) |temp| {
            const temp_str = try std.fmt.allocPrint(allocator, ",\"temperature\":{d}", .{temp});
            defer allocator.free(temp_str);
            try json.appendSlice(allocator, temp_str);
        }

        if (options.max_tokens) |max_tok| {
            const max_str = try std.fmt.allocPrint(allocator, ",\"max_tokens\":{d}", .{max_tok});
            defer allocator.free(max_str);
            try json.appendSlice(allocator, max_str);
        }

        if (options.top_p) |top_p_val| {
            const top_p_str = try std.fmt.allocPrint(allocator, ",\"top_p\":{d}", .{top_p_val});
            defer allocator.free(top_p_str);
            try json.appendSlice(allocator, top_p_str);
        }

        if (is_stream) {
            try json.appendSlice(allocator, ",\"stream\":true");
        }

        try json.append(allocator, '}');

        return try json.toOwnedSlice(allocator);
    }

    /// Make HTTP request to OpenAI API
    fn makeRequest(self: *OpenAILLM, allocator: Allocator, body: []const u8) ![]const u8 {
        var client = std.http.Client{ .allocator = allocator };
        defer client.deinit();

        // Build URI
        const uri_str = try std.fmt.allocPrint(
            allocator,
            "{s}/chat/completions",
            .{self.base_url},
        );
        defer allocator.free(uri_str);

        // Build authorization header
        const auth_value = try std.fmt.allocPrint(
            allocator,
            "Bearer {s}",
            .{self.api_key},
        );
        defer allocator.free(auth_value);

        // Prepare headers
        const headers = [_]std.http.Header{
            .{ .name = "Authorization", .value = auth_value },
            .{ .name = "Content-Type", .value = "application/json" },
        };

        // Use std.io.Writer.Allocating for response body (Zig 0.15 pattern)
        var response_body: std.io.Writer.Allocating = .init(allocator);
        defer response_body.deinit();

        // Make request using fetch API
        const result = try client.fetch(.{
            .location = .{ .url = uri_str },
            .method = .POST,
            .payload = body,
            .extra_headers = &headers,
            .response_writer = &response_body.writer,
        });

        // Check status
        if (result.status != .ok) {
            return error.ServerError;
        }

        return try response_body.toOwnedSlice();
    }

    /// Parse OpenAI API response
    fn parseResponse(self: *OpenAILLM, allocator: Allocator, response_body: []const u8) !*Message {
        _ = self;

        // Parse JSON response
        const parsed = try std.json.parseFromSlice(
            std.json.Value,
            allocator,
            response_body,
            .{},
        );
        defer parsed.deinit();

        const root = parsed.value.object;

        // Extract message content from choices[0].message.content
        const choices = root.get("choices") orelse return error.InvalidResponse;
        if (choices.array.items.len == 0) return error.InvalidResponse;

        const first_choice = choices.array.items[0].object;
        const message = first_choice.get("message") orelse return error.InvalidResponse;
        const content = message.object.get("content") orelse return error.InvalidResponse;

        // Create response message
        const msg = try allocator.create(Message);
        msg.* = try Message.withText(allocator, .assistant, content.string);

        // Add metadata
        if (root.get("model")) |model_val| {
            try msg.setMetadata("model", model_val);
        }

        if (root.get("usage")) |usage| {
            try msg.setMetadata("usage", usage);
        }

        if (first_choice.get("finish_reason")) |finish_reason| {
            try msg.setMetadata("finish_reason", finish_reason);
        }

        return msg;
    }
};

// Tests
test "OpenAILLM initialization" {
    const allocator = std.testing.allocator;

    var llm_impl = try OpenAILLM.init(allocator, "sk-test-key", "gpt-4-turbo");
    defer llm_impl.deinit();

    const llm_interface = llm_impl.asLLM();
    try std.testing.expectEqualStrings("gpt-4-turbo", llm_interface.model());
}

test "OpenAILLM buildRequestBody" {
    const allocator = std.testing.allocator;

    var llm_impl = try OpenAILLM.init(allocator, "sk-test-key", "gpt-4");
    defer llm_impl.deinit();

    // Create test messages
    var msg1 = try Message.withText(allocator, .user, "Hello");
    defer msg1.deinit();

    const messages = [_]*Message{&msg1};

    var options = llm.CallOptions.init(allocator);
    defer options.deinit();
    try options.withTemperature(0.7);

    const body = try llm_impl.buildRequestBody(allocator, &messages, &options, false);
    defer allocator.free(body);

    // Verify JSON structure
    try std.testing.expect(std.mem.indexOf(u8, body, "\"model\":\"gpt-4\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"temperature\":0.7") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"role\":\"user\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"content\":\"Hello\"") != null);
}

/// Ollama LLM adapter for local models
///
/// This adapter wraps Ollama's API to provide a consistent Agenkit interface
/// for running local LLMs (Llama, Mistral, etc.). No API key required.
///
/// Example:
/// ```zig
/// var llm_impl = try OllamaLLM.init(allocator, "llama2", "http://localhost:11434");
/// defer llm_impl.deinit();
/// const llm = llm_impl.asLLM();
///
/// const messages = [_]*Message{ /* ... */ };
/// var options = CallOptions.init(allocator);
/// defer options.deinit();
///
/// const response = try llm.complete(allocator, &messages, &options);
/// defer response.deinit();
/// ```

const std = @import("std");
const llm = @import("llm.zig");
const Message = @import("../message.zig").Message;
const Role = @import("../message.zig").Role;
const Allocator = std.mem.Allocator;

/// Ollama streaming iterator
const OllamaStream = struct {
    allocator: Allocator,
    self: *OllamaLLM,
    chunks: std.ArrayList([]const u8),
    current_index: usize,

    fn makeStreamRequest(self: *OllamaStream, body: []const u8) !void {
        var client = std.http.Client{ .allocator = self.allocator };
        defer client.deinit();

        const uri_str = try std.fmt.allocPrint(self.allocator, "{s}/api/chat", .{self.self.base_url});
        defer self.allocator.free(uri_str);

        const headers = [_]std.http.Header{.{ .name = "Content-Type", .value = "application/json" }};

        var response_buffer: std.io.Writer.Allocating = .init(self.allocator);
        defer response_buffer.deinit();

        const result = try client.fetch(.{
            .location = .{ .url = uri_str },
            .method = .POST,
            .payload = body,
            .extra_headers = &headers,
            .response_writer = &response_buffer.writer,
        });

        if (result.status != .ok) return error.ServerError;

        const data = try response_buffer.toOwnedSlice();
        defer self.allocator.free(data);
        try self.parseNewlineJSON(data);
    }

    fn parseNewlineJSON(self: *OllamaStream, data: []const u8) !void {
        var lines = std.mem.splitSequence(u8, data, "\n");
        while (lines.next()) |line| {
            if (line.len == 0) continue;
            const parsed = std.json.parseFromSlice(std.json.Value, self.allocator, line, .{}) catch continue;
            defer parsed.deinit();

            if (parsed.value.object.get("message")) |msg| {
                if (msg.object.get("content")) |content| {
                    const chunk = try self.allocator.dupe(u8, content.string);
                    try self.chunks.append(self.allocator, chunk);
                }
            }
        }
    }

    fn deinit(self: *OllamaStream) void {
        for (self.chunks.items) |chunk| self.allocator.free(chunk);
        self.chunks.deinit(self.allocator);
        self.allocator.destroy(self);
    }
};

fn ollamaStreamNext(ptr: *anyopaque, allocator: Allocator) !?*Message {
    const self: *OllamaStream = @ptrCast(@alignCast(ptr));
    if (self.current_index >= self.chunks.items.len) return null;
    const text = self.chunks.items[self.current_index];
    self.current_index += 1;
    const msg = try allocator.create(Message);
    msg.* = try Message.withText(allocator, .assistant, text);
    try msg.setMetadata("streaming", std.json.Value{ .bool = true });
    return msg;
}

fn ollamaStreamDeinit(ptr: *anyopaque) void {
    const self: *OllamaStream = @ptrCast(@alignCast(ptr));
    self.deinit();
}

/// Ollama LLM adapter
pub const OllamaLLM = struct {
    allocator: Allocator,
    model_name: []const u8,
    base_url: []const u8,

    /// Initialize Ollama adapter
    ///
    /// Parameters:
    ///   - allocator: Memory allocator
    ///   - model: Model name (e.g., "llama2", "mistral", "codellama")
    ///   - base_url: Ollama server URL (default: "http://localhost:11434")
    ///
    /// Returns:
    ///   Initialized OllamaLLM instance
    pub fn init(
        allocator: Allocator,
        model_str: []const u8,
        url: []const u8,
    ) !*OllamaLLM {
        const self = try allocator.create(OllamaLLM);
        errdefer allocator.destroy(self);

        const model_copy = if (model_str.len > 0)
            try allocator.dupe(u8, model_str)
        else
            try allocator.dupe(u8, "llama2");

        const url_copy = if (url.len > 0)
            try allocator.dupe(u8, url)
        else
            try allocator.dupe(u8, "http://localhost:11434");

        self.* = OllamaLLM{
            .allocator = allocator,
            .model_name = model_copy,
            .base_url = url_copy,
        };

        return self;
    }

    /// Convert to LLM interface
    pub fn asLLM(self: *OllamaLLM) llm.LLM {
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
    pub fn deinit(self: *OllamaLLM) void {
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
        const self: *OllamaLLM = @ptrCast(@alignCast(ptr));

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
        const self: *OllamaLLM = @ptrCast(@alignCast(ptr));
        const request_body = try self.buildRequestBody(allocator, messages, options, true);
        defer allocator.free(request_body);

        const stream_impl = try allocator.create(OllamaStream);
        errdefer allocator.destroy(stream_impl);
        stream_impl.* = OllamaStream{
            .allocator = allocator,
            .self = self,
            .chunks = std.ArrayList([]const u8){},
            .current_index = 0,
        };

        try stream_impl.makeStreamRequest(request_body);

        return llm.StreamIterator{
            .ptr = stream_impl,
            .vtable = &.{
                .next = ollamaStreamNext,
                .deinit = ollamaStreamDeinit,
            },
        };
    }

    /// Model implementation
    fn model(ptr: *anyopaque) []const u8 {
        const self: *OllamaLLM = @ptrCast(@alignCast(ptr));
        return self.model_name;
    }

    /// Deinit implementation for VTable
    fn deinitVTable(ptr: *anyopaque) void {
        const self: *OllamaLLM = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    /// Build Ollama API request body
    fn buildRequestBody(
        self: *OllamaLLM,
        allocator: Allocator,
        messages: []const *Message,
        options: *const llm.CallOptions,
        is_stream: bool,
    ) ![]const u8 {
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

        // Options (Ollama uses different names)
        if (options.temperature) |temp| {
            const temp_str = try std.fmt.allocPrint(allocator, ",\"options\":{{\"temperature\":{d}", .{temp});
            defer allocator.free(temp_str);
            try json.appendSlice(allocator, temp_str);

            if (options.top_p) |top_p_val| {
                const top_p_str = try std.fmt.allocPrint(allocator, ",\"top_p\":{d}", .{top_p_val});
                defer allocator.free(top_p_str);
                try json.appendSlice(allocator, top_p_str);
            }

            try json.append(allocator, '}');
        }

        if (is_stream) {
            try json.appendSlice(allocator, ",\"stream\":true");
        } else {
            try json.appendSlice(allocator, ",\"stream\":false");
        }

        try json.append(allocator, '}');

        return try json.toOwnedSlice(allocator);
    }

    /// Make HTTP request to Ollama API
    fn makeRequest(self: *OllamaLLM, allocator: Allocator, body: []const u8) ![]const u8 {
        var client = std.http.Client{ .allocator = allocator };
        defer client.deinit();

        const uri_str = try std.fmt.allocPrint(
            allocator,
            "{s}/api/chat",
            .{self.base_url},
        );
        defer allocator.free(uri_str);

        const headers = [_]std.http.Header{
            .{ .name = "Content-Type", .value = "application/json" },
        };

        var response_body: std.io.Writer.Allocating = .init(allocator);
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

    /// Parse Ollama API response
    fn parseResponse(self: *OllamaLLM, allocator: Allocator, response_body: []const u8) !*Message {
        _ = self;

        const parsed = try std.json.parseFromSlice(
            std.json.Value,
            allocator,
            response_body,
            .{},
        );
        defer parsed.deinit();

        const root = parsed.value.object;

        // Extract message content from message.content
        const message = root.get("message") orelse return error.InvalidResponse;
        const content = message.object.get("content") orelse return error.InvalidResponse;

        // Create response message
        const msg = try allocator.create(Message);
        msg.* = try Message.withText(allocator, .assistant, content.string);

        // Add metadata
        if (root.get("model")) |model_val| {
            try msg.setMetadata("model", model_val);
        }

        if (root.get("done")) |done| {
            try msg.setMetadata("done", done);
        }

        if (root.get("total_duration")) |duration| {
            try msg.setMetadata("total_duration", duration);
        }

        return msg;
    }
};

// Tests
test "OllamaLLM initialization" {
    const allocator = std.testing.allocator;

    var llm_impl = try OllamaLLM.init(allocator, "llama2", "http://localhost:11434");
    defer llm_impl.deinit();

    const llm_interface = llm_impl.asLLM();
    try std.testing.expectEqualStrings("llama2", llm_interface.model());
}

test "OllamaLLM buildRequestBody" {
    const allocator = std.testing.allocator;

    var llm_impl = try OllamaLLM.init(allocator, "mistral", "http://localhost:11434");
    defer llm_impl.deinit();

    var msg1 = try Message.withText(allocator, .user, "Hello");
    defer msg1.deinit();

    const messages = [_]*Message{&msg1};

    var options = llm.CallOptions.init(allocator);
    defer options.deinit();
    options.temperature = 0.7;

    const body = try llm_impl.buildRequestBody(allocator, &messages, &options, false);
    defer allocator.free(body);

    // Verify JSON structure
    try std.testing.expect(std.mem.indexOf(u8, body, "\"model\":\"mistral\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"temperature\":0.7") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"stream\":false") != null);
}

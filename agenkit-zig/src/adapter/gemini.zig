/// Google Gemini LLM adapter
///
/// This adapter wraps Google's Gemini API to provide a consistent Agenkit
/// interface for Gemini Pro and other models.
///
/// Example:
/// ```zig
/// var llm_impl = try GeminiLLM.init(allocator, api_key, "gemini-pro");
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
const ioc = @import("../io_compat.zig");
const agkenv = @import("../env_compat.zig");
const llm = @import("llm.zig");
const Message = @import("../message.zig").Message;
const Role = @import("../message.zig").Role;
const Allocator = std.mem.Allocator;

/// Gemini streaming iterator implementation
const GeminiStream = struct {
    allocator: Allocator,
    self: *GeminiLLM,
    chunks: std.ArrayList([]const u8),
    current_index: usize,

    fn makeStreamRequest(self: *GeminiStream, body: []const u8) !void {
        var client = std.http.Client{ .allocator = self.allocator, .io = ioc.io() };
        defer client.deinit();

        // Use streamGenerateContent endpoint
        const uri_str = try std.fmt.allocPrint(
            self.allocator,
            "{s}/models/{s}:streamGenerateContent?key={s}",
            .{ self.self.base_url, self.self.model_name, self.self.api_key },
        );
        defer self.allocator.free(uri_str);

        const headers = [_]std.http.Header{
            .{ .name = "Content-Type", .value = "application/json" },
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
        try self.parseNewlineDelimitedJSON(data);
    }

    fn parseNewlineDelimitedJSON(self: *GeminiStream, data: []const u8) !void {
        var lines = std.mem.splitSequence(u8, data, "\n");

        while (lines.next()) |line| {
            if (line.len == 0) continue;

            const parsed = std.json.parseFromSlice(
                std.json.Value,
                self.allocator,
                line,
                .{},
            ) catch continue;
            defer parsed.deinit();

            const response = parsed.value.object;

            // Extract text from candidates[0].content.parts[0].text
            if (response.get("candidates")) |candidates| {
                if (candidates.array.items.len > 0) {
                    const candidate = candidates.array.items[0].object;
                    if (candidate.get("content")) |content| {
                        if (content.object.get("parts")) |parts| {
                            if (parts.array.items.len > 0) {
                                const part = parts.array.items[0].object;
                                if (part.get("text")) |text| {
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

    fn deinit(self: *GeminiStream) void {
        for (self.chunks.items) |chunk| {
            self.allocator.free(chunk);
        }
        self.chunks.deinit(self.allocator);
        self.allocator.destroy(self);
    }
};

fn geminiStreamNext(ptr: *anyopaque, allocator: Allocator) !?*Message {
    const self: *GeminiStream = @ptrCast(@alignCast(ptr));

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

fn geminiStreamDeinit(ptr: *anyopaque) void {
    const self: *GeminiStream = @ptrCast(@alignCast(ptr));
    self.deinit();
}

/// Gemini LLM adapter
pub const GeminiLLM = struct {
    allocator: Allocator,
    api_key: []const u8,
    model_name: []const u8,
    base_url: []const u8,

    /// Initialize Gemini adapter
    ///
    /// Parameters:
    ///   - allocator: Memory allocator
    ///   - api_key: Google API key (or use GEMINI_API_KEY env var)
    ///   - model: Model identifier (e.g., "gemini-pro", "gemini-pro-vision")
    ///
    /// Returns:
    ///   Initialized GeminiLLM instance
    pub fn init(
        allocator: Allocator,
        api_key: []const u8,
        model_str: []const u8,
    ) !*GeminiLLM {
        const self = try allocator.create(GeminiLLM);
        errdefer allocator.destroy(self);

        const key = if (api_key.len > 0)
            try allocator.dupe(u8, api_key)
        else blk: {
            const env_key = agkenv.getEnvVarOwned(allocator, "GEMINI_API_KEY") catch {
                return error.MissingAPIKey;
            };
            break :blk env_key;
        };

        const model_copy = if (model_str.len > 0)
            try allocator.dupe(u8, model_str)
        else
            try allocator.dupe(u8, "gemini-pro");

        self.* = GeminiLLM{
            .allocator = allocator,
            .api_key = key,
            .model_name = model_copy,
            .base_url = try allocator.dupe(u8, "https://generativelanguage.googleapis.com/v1beta"),
        };

        return self;
    }

    /// Convert to LLM interface
    pub fn asLLM(self: *GeminiLLM) llm.LLM {
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
    pub fn deinit(self: *GeminiLLM) void {
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
        const self: *GeminiLLM = @ptrCast(@alignCast(ptr));

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
        const self: *GeminiLLM = @ptrCast(@alignCast(ptr));

        // Build request body (same as non-streaming)
        const request_body = try self.buildRequestBody(allocator, messages, options);
        defer allocator.free(request_body);

        // Create stream iterator
        const stream_impl = try allocator.create(GeminiStream);
        errdefer allocator.destroy(stream_impl);

        stream_impl.* = GeminiStream{
            .allocator = allocator,
            .self = self,
            .chunks = std.ArrayList([]const u8).empty,
            .current_index = 0,
        };

        // Make streaming request
        try stream_impl.makeStreamRequest(request_body);

        return llm.StreamIterator{
            .ptr = stream_impl,
            .vtable = &.{
                .next = geminiStreamNext,
                .deinit = geminiStreamDeinit,
            },
        };
    }

    /// Model implementation
    fn model(ptr: *anyopaque) []const u8 {
        const self: *GeminiLLM = @ptrCast(@alignCast(ptr));
        return self.model_name;
    }

    /// Deinit implementation for VTable
    fn deinitVTable(ptr: *anyopaque) void {
        const self: *GeminiLLM = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    /// Build Gemini API request body
    fn buildRequestBody(
        self: *GeminiLLM,
        allocator: Allocator,
        messages: []const *Message,
        options: *const llm.CallOptions,
    ) ![]const u8 {
        _ = self;
        var json = std.ArrayList(u8).empty;
        defer json.deinit(allocator);

        try json.appendSlice(allocator, "{\"contents\":[");

        // Gemini uses a different message format
        for (messages, 0..) |msg, i| {
            if (i > 0) try json.append(allocator, ',');

            // Map Agenkit roles to Gemini roles
            const gemini_role = switch (msg.role) {
                .user => "user",
                .assistant => "model",
                .system => "user", // Gemini doesn't have system role, use user
                .tool => "user", // Gemini doesn't have tool role, use user
                .agent => "model", // Agent messages are similar to assistant
            };

            try json.appendSlice(allocator, "{\"role\":\"");
            try json.appendSlice(allocator, gemini_role);
            try json.appendSlice(allocator, "\",\"parts\":[{\"text\":\"");

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

            try json.appendSlice(allocator, "\"}]}");
        }

        try json.append(allocator, ']');

        // Generation config
        if (options.temperature != null or options.max_tokens != null or options.top_p != null) {
            try json.appendSlice(allocator, ",\"generationConfig\":{");
            var has_config = false;

            if (options.temperature) |temp| {
                const temp_str = try std.fmt.allocPrint(allocator, "\"temperature\":{d}", .{temp});
                defer allocator.free(temp_str);
                try json.appendSlice(allocator, temp_str);
                has_config = true;
            }

            if (options.max_tokens) |max_tok| {
                if (has_config) try json.append(allocator, ',');
                const max_str = try std.fmt.allocPrint(allocator, "\"maxOutputTokens\":{d}", .{max_tok});
                defer allocator.free(max_str);
                try json.appendSlice(allocator, max_str);
                has_config = true;
            }

            if (options.top_p) |top_p_val| {
                if (has_config) try json.append(allocator, ',');
                const top_p_str = try std.fmt.allocPrint(allocator, "\"topP\":{d}", .{top_p_val});
                defer allocator.free(top_p_str);
                try json.appendSlice(allocator, top_p_str);
            }

            try json.append(allocator, '}');
        }

        try json.append(allocator, '}');

        return try json.toOwnedSlice(allocator);
    }

    /// Make HTTP request to Gemini API
    fn makeRequest(self: *GeminiLLM, allocator: Allocator, body: []const u8) ![]const u8 {
        var client = std.http.Client{ .allocator = allocator, .io = ioc.io() };
        defer client.deinit();

        // Gemini uses query parameter for API key
        const uri_str = try std.fmt.allocPrint(
            allocator,
            "{s}/models/{s}:generateContent?key={s}",
            .{ self.base_url, self.model_name, self.api_key },
        );
        defer allocator.free(uri_str);

        const headers = [_]std.http.Header{
            .{ .name = "Content-Type", .value = "application/json" },
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

    /// Parse Gemini API response
    fn parseResponse(self: *GeminiLLM, allocator: Allocator, response_body: []const u8) !*Message {
        _ = self;

        const parsed = try std.json.parseFromSlice(
            std.json.Value,
            allocator,
            response_body,
            .{},
        );
        defer parsed.deinit();

        const root = parsed.value.object;

        // Extract content from candidates[0].content.parts[0].text
        const candidates = root.get("candidates") orelse return error.InvalidResponse;
        if (candidates.array.items.len == 0) return error.InvalidResponse;

        const first_candidate = candidates.array.items[0].object;
        const content = first_candidate.get("content") orelse return error.InvalidResponse;
        const parts = content.object.get("parts") orelse return error.InvalidResponse;
        if (parts.array.items.len == 0) return error.InvalidResponse;

        const first_part = parts.array.items[0].object;
        const text = first_part.get("text") orelse return error.InvalidResponse;

        // Create response message
        const msg = try allocator.create(Message);
        msg.* = try Message.withText(allocator, .assistant, text.string);

        // Add metadata
        if (first_candidate.get("finishReason")) |finish_reason| {
            try msg.setMetadata("finish_reason", finish_reason);
        }

        if (root.get("usageMetadata")) |usage| {
            try msg.setMetadata("usage", usage);
        }

        return msg;
    }
};

// Tests
test "GeminiLLM initialization" {
    const allocator = std.testing.allocator;

    var llm_impl = try GeminiLLM.init(allocator, "test-api-key", "gemini-pro");
    defer llm_impl.deinit();

    const llm_interface = llm_impl.asLLM();
    try std.testing.expectEqualStrings("gemini-pro", llm_interface.model());
}

test "GeminiLLM buildRequestBody" {
    const allocator = std.testing.allocator;

    var llm_impl = try GeminiLLM.init(allocator, "test-key", "gemini-pro");
    defer llm_impl.deinit();

    var msg1 = try Message.withText(allocator, .user, "Hello");
    defer msg1.deinit();

    const messages = [_]*Message{&msg1};

    var options = llm.CallOptions.init(allocator);
    defer options.deinit();
    options.temperature = 0.7;

    const body = try llm_impl.buildRequestBody(allocator, &messages, &options);
    defer allocator.free(body);

    // Verify JSON structure
    try std.testing.expect(std.mem.indexOf(u8, body, "\"contents\":[") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"temperature\":0.7") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"role\":\"user\"") != null);
}

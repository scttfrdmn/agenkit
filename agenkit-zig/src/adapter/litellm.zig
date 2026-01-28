/// LiteLLM adapter (Universal LLM proxy)
///
/// This adapter wraps LiteLLM's OpenAI-compatible API to provide access to
/// 100+ LLM providers (OpenAI, Anthropic, Cohere, Azure, etc.) through a
/// unified interface.
///
/// LiteLLM can be:
/// - Self-hosted proxy: https://github.com/BerriAI/litellm
/// - Cloud service: https://litellm.ai/
///
/// Example:
/// ```zig
/// var llm_impl = try LiteLLMLLM.init(
///     allocator,
///     api_key,
///     "gpt-4", // Or any model: claude-3-opus, command-r-plus, etc.
///     "http://localhost:4000" // Your LiteLLM proxy URL
/// );
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
/// LiteLLM streaming iterator
const LiteLLMStream = struct {
    allocator: Allocator,
    self: *LiteLLMLLM,
    chunks: std.ArrayList([]const u8),
    current_index: usize,
    fn makeStreamRequest(self: *LiteLLMStream, body: []const u8) !void {
        var client = std.http.Client{ .allocator = self.allocator };
        defer client.deinit();
        const uri_str = try std.fmt.allocPrint(self.allocator, "{s}/chat/completions", .{self.self.base_url});
        defer self.allocator.free(uri_str);
        const auth_value = if (self.self.api_key.len > 0) try std.fmt.allocPrint(self.allocator, "Bearer {s}", .{self.self.api_key}) else try self.allocator.dupe(u8, "");
        defer self.allocator.free(auth_value);
        const headers = if (self.self.api_key.len > 0) [_]std.http.Header{.{ .name = "Content-Type", .value = "application/json" }, .{ .name = "Authorization", .value = auth_value }} else [_]std.http.Header{.{ .name = "Content-Type", .value = "application/json" }};
        var response_buffer = std.ArrayList(u8).init(self.allocator);
        defer response_buffer.deinit();
        const result = try client.fetch(.{ .location = .{ .url = uri_str }, .method = .POST, .payload = body, .extra_headers = &headers, .response_storage = .{ .dynamic = &response_buffer } });
        if (result.status != .ok) return error.ServerError;
        try self.parseSSEStream(response_buffer.items);
    }
    fn parseSSEStream(self: *LiteLLMStream, data: []const u8) !void {
        var lines = std.mem.split(u8, data, "\n");
        while (lines.next()) |line| {
            if (line.len == 0 or !std.mem.startsWith(u8, line, "data: ")) continue;
            const json_str = line[6..];
            if (std.mem.eql(u8, json_str, "[DONE]")) continue;
            const parsed = std.json.parseFromSlice(std.json.Value, self.allocator, json_str, .{}) catch continue;
            defer parsed.deinit();
            if (parsed.value.object.get("choices")) |choices| {
                if (choices.array.items.len > 0) {
                    const choice = choices.array.items[0].object;
                    if (choice.get("delta")) |delta| {
                        if (delta.object.get("content")) |content| {
                            const chunk = try self.allocator.dupe(u8, content.string);
                            try self.chunks.append(chunk);
                        }
                    }
                }
            }
        }
    }
    fn deinit(self: *LiteLLMStream) void { for (self.chunks.items) |chunk| self.allocator.free(chunk); self.chunks.deinit(); self.allocator.destroy(self); }
};
fn litellmStreamNext(ptr: *anyopaque, allocator: Allocator) !?*Message { const self: *LiteLLMStream = @ptrCast(@alignCast(ptr)); if (self.current_index >= self.chunks.items.len) return null; const text = self.chunks.items[self.current_index]; self.current_index += 1; const msg = try allocator.create(Message); msg.* = try Message.withText(allocator, .assistant, text); try msg.setMetadata("streaming", std.json.Value{ .bool = true }); return msg; }
fn litellmStreamDeinit(ptr: *anyopaque) void { const self: *LiteLLMStream = @ptrCast(@alignCast(ptr)); self.deinit(); }

const Allocator = std.mem.Allocator;

/// LiteLLM adapter
pub const LiteLLMLLM = struct {
    allocator: Allocator,
    api_key: []const u8,
    model_name: []const u8,
    base_url: []const u8,

    /// Initialize LiteLLM adapter
    ///
    /// Parameters:
    ///   - allocator: Memory allocator
    ///   - api_key: LiteLLM API key (or use LITELLM_API_KEY env var)
    ///   - model: Model identifier (any LiteLLM-supported model)
    ///   - base_url: LiteLLM proxy URL (default: "http://localhost:4000")
    ///
    /// Returns:
    ///   Initialized LiteLLMLLM instance
    pub fn init(
        allocator: Allocator,
        api_key: []const u8,
        model_str: []const u8,
        url: []const u8,
    ) !*LiteLLMLLM {
        const self = try allocator.create(LiteLLMLLM);
        errdefer allocator.destroy(self);

        const key = if (api_key.len > 0)
            try allocator.dupe(u8, api_key)
        else blk: {
            // Try LITELLM_API_KEY, fallback to empty (for local deployments)
            const env_key = std.process.getEnvVarOwned(allocator, "LITELLM_API_KEY") catch {
                break :blk try allocator.dupe(u8, "");
            };
            break :blk env_key;
        };

        const model_copy = if (model_str.len > 0)
            try allocator.dupe(u8, model_str)
        else
            try allocator.dupe(u8, "gpt-3.5-turbo");

        const url_copy = if (url.len > 0)
            try allocator.dupe(u8, url)
        else
            try allocator.dupe(u8, "http://localhost:4000");

        self.* = LiteLLMLLM{
            .allocator = allocator,
            .api_key = key,
            .model_name = model_copy,
            .base_url = url_copy,
        };

        return self;
    }

    /// Convert to LLM interface
    pub fn asLLM(self: *LiteLLMLLM) llm.LLM {
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
    pub fn deinit(self: *LiteLLMLLM) void {
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
        const self: *LiteLLMLLM = @ptrCast(@alignCast(ptr));

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
        _ = ptr;
        _ = allocator;
        _ = messages;
        _ = options;
        return error.StreamingNotSupported;
    }

    /// Model implementation
    fn model(ptr: *anyopaque) []const u8 {
        const self: *LiteLLMLLM = @ptrCast(@alignCast(ptr));
        return self.model_name;
    }

    /// Deinit implementation for VTable
    fn deinitVTable(ptr: *anyopaque) void {
        const self: *LiteLLMLLM = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    /// Build LiteLLM API request body (OpenAI-compatible)
    fn buildRequestBody(
        self: *LiteLLMLLM,
        allocator: Allocator,
        messages: []const *Message,
        options: *const llm.CallOptions,
    ) ![]const u8 {
        var json = std.ArrayList(u8){};
        defer json.deinit(allocator);

        try json.appendSlice(allocator, "{\"model\":\"");
        try json.appendSlice(allocator, self.model_name);
        try json.appendSlice(allocator, "\",\"messages\":[");

        // Messages array (OpenAI format)
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

        // Optional parameters
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

        try json.append(allocator, '}');

        return try json.toOwnedSlice(allocator);
    }

    /// Make HTTP request to LiteLLM API
    fn makeRequest(self: *LiteLLMLLM, allocator: Allocator, body: []const u8) ![]const u8 {
        var client = std.http.Client{ .allocator = allocator };
        defer client.deinit();

        const uri_str = try std.fmt.allocPrint(
            allocator,
            "{s}/chat/completions",
            .{self.base_url},
        );
        defer allocator.free(uri_str);

        // Build headers (Authorization if API key provided)
        var headers_buf: [3]std.http.Header = undefined;
        var headers_count: usize = 1;
        headers_buf[0] = .{ .name = "Content-Type", .value = "application/json" };

        if (self.api_key.len > 0) {
            const auth_header = try std.fmt.allocPrint(allocator, "Bearer {s}", .{self.api_key});
            defer allocator.free(auth_header);

            const auth_header_owned = try allocator.dupe(u8, auth_header);
            defer allocator.free(auth_header_owned);

            headers_buf[1] = .{ .name = "Authorization", .value = auth_header_owned };
            headers_count = 2;
        }

        const headers = headers_buf[0..headers_count];

        var response_body: std.io.Writer.Allocating = .init(allocator);
        defer response_body.deinit();

        const result = try client.fetch(.{
            .location = .{ .url = uri_str },
            .method = .POST,
            .payload = body,
            .extra_headers = headers,
            .response_writer = &response_body.writer,
        });

        if (result.status != .ok) {
            return error.ServerError;
        }

        return try response_body.toOwnedSlice();
    }

    /// Parse LiteLLM API response (OpenAI-compatible)
    fn parseResponse(self: *LiteLLMLLM, allocator: Allocator, response_body: []const u8) !*Message {
        _ = self;

        const parsed = try std.json.parseFromSlice(
            std.json.Value,
            allocator,
            response_body,
            .{},
        );
        defer parsed.deinit();

        const root = parsed.value.object;

        // Extract content from choices[0].message.content
        const choices = root.get("choices") orelse return error.InvalidResponse;
        if (choices.array.items.len == 0) return error.InvalidResponse;

        const first_choice = choices.array.items[0].object;
        const message = first_choice.get("message") orelse return error.InvalidResponse;
        const content = message.object.get("content") orelse return error.InvalidResponse;

        // Create response message
        const msg = try allocator.create(Message);
        msg.* = try Message.withText(allocator, .assistant, content.string);

        // Add metadata
        if (first_choice.get("finish_reason")) |finish_reason| {
            try msg.setMetadata("finish_reason", finish_reason);
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
test "LiteLLMLLM initialization" {
    const allocator = std.testing.allocator;

    var llm_impl = try LiteLLMLLM.init(allocator, "test-api-key", "gpt-4", "http://localhost:4000");
    defer llm_impl.deinit();

    const llm_interface = llm_impl.asLLM();
    try std.testing.expectEqualStrings("gpt-4", llm_interface.model());
}

test "LiteLLMLLM buildRequestBody" {
    const allocator = std.testing.allocator;

    var llm_impl = try LiteLLMLLM.init(allocator, "test-key", "claude-3-opus", "http://localhost:4000");
    defer llm_impl.deinit();

    var msg1 = try Message.withText(allocator, .user, "Hello");
    defer msg1.deinit();

    const messages = [_]*Message{&msg1};

    var options = llm.CallOptions.init(allocator);
    defer options.deinit();
    options.temperature = 0.7;
    options.max_tokens = 500;

    const body = try llm_impl.buildRequestBody(allocator, &messages, &options);
    defer allocator.free(body);

    // Verify JSON structure
    try std.testing.expect(std.mem.indexOf(u8, body, "\"model\":\"claude-3-opus\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"temperature\":0.7") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"max_tokens\":500") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"role\":\"user\"") != null);
}

test "LiteLLMLLM initialization without API key" {
    const allocator = std.testing.allocator;

    // Should work - LiteLLM can run without auth in local mode
    var llm_impl = try LiteLLMLLM.init(allocator, "", "mistral-7b", "http://localhost:4000");
    defer llm_impl.deinit();

    try std.testing.expectEqualStrings("", llm_impl.api_key);
    try std.testing.expectEqualStrings("mistral-7b", llm_impl.model_name);
}

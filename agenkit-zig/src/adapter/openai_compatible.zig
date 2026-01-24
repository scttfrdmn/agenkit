/// OpenAI-compatible LLM adapter for local/self-hosted inference services
///
/// This adapter wraps OpenAI-compatible Chat Completions APIs to provide a consistent
/// Agenkit interface for local and self-hosted inference engines. Supports vLLM,
/// llama.cpp, SGLang, TensorRT-LLM, and other OpenAI-compatible services.
///
/// Supported Services:
///   - vLLM: High-throughput batch inference
///   - llama.cpp: Lightweight C++ implementation (CPU-friendly)
///   - SGLang: Optimized for complex prompts
///   - TensorRT-LLM: NVIDIA GPU optimized
///   - OpenLLM: Multi-model serving platform
///   - MLC LLM: Mobile and edge deployment
///   - Text Generation Inference (TGI): HuggingFace inference server
///   - Inferflow: High-performance inference
///
/// Example:
/// ```zig
/// var llm_impl = try OpenAICompatibleLLM.init(
///     allocator,
///     "http://localhost:8000/v1",
///     "meta-llama/Llama-3.3-8B-Instruct",
///     null,  // api_key optional for local services
///     "vllm"  // provider name
/// );
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

/// OpenAI-compatible LLM adapter
pub const OpenAICompatibleLLM = struct {
    allocator: Allocator,
    base_url: []const u8,
    model_name: []const u8,
    api_key: ?[]const u8,
    provider: ?[]const u8,

    /// Initialize OpenAI-compatible adapter
    ///
    /// Parameters:
    ///   - allocator: Memory allocator
    ///   - base_url: Base URL of the inference service (e.g., "http://localhost:8000/v1")
    ///   - model: Model identifier (service-specific format)
    ///   - api_key: Optional API key (not needed for most local services)
    ///   - provider: Optional provider name for metadata (e.g., "vllm", "llamacpp")
    ///
    /// Returns:
    ///   Initialized OpenAICompatibleLLM instance
    pub fn init(
        allocator: Allocator,
        base_url: []const u8,
        model_str: []const u8,
        api_key: ?[]const u8,
        provider: ?[]const u8,
    ) !*OpenAICompatibleLLM {
        const self = try allocator.create(OpenAICompatibleLLM);
        errdefer allocator.destroy(self);

        const url_copy = try allocator.dupe(u8, base_url);
        const model_copy = try allocator.dupe(u8, model_str);

        const key_copy = if (api_key) |k|
            try allocator.dupe(u8, k)
        else
            null;

        const provider_copy = if (provider) |p|
            try allocator.dupe(u8, p)
        else
            null;

        self.* = OpenAICompatibleLLM{
            .allocator = allocator,
            .base_url = url_copy,
            .model_name = model_copy,
            .api_key = key_copy,
            .provider = provider_copy,
        };

        return self;
    }

    /// Provider helper: vLLM configuration
    pub fn vllm(allocator: Allocator, model_str: []const u8) !*OpenAICompatibleLLM {
        return try init(
            allocator,
            "http://localhost:8000/v1",
            model_str,
            null,
            "vllm",
        );
    }

    /// Provider helper: llama.cpp configuration
    pub fn llamacpp(allocator: Allocator, model_str: []const u8) !*OpenAICompatibleLLM {
        return try init(
            allocator,
            "http://localhost:8080/v1",
            model_str,
            null,
            "llamacpp",
        );
    }

    /// Provider helper: SGLang configuration
    pub fn sglang(allocator: Allocator, model_str: []const u8) !*OpenAICompatibleLLM {
        return try init(
            allocator,
            "http://localhost:30000/v1",
            model_str,
            null,
            "sglang",
        );
    }

    /// Provider helper: TensorRT-LLM configuration
    pub fn tensorrt(allocator: Allocator, model_str: []const u8) !*OpenAICompatibleLLM {
        return try init(
            allocator,
            "http://localhost:8001/v1",
            model_str,
            null,
            "tensorrt",
        );
    }

    /// Convert to LLM interface
    pub fn asLLM(self: *OpenAICompatibleLLM) llm.LLM {
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
    pub fn deinit(self: *OpenAICompatibleLLM) void {
        self.allocator.free(self.base_url);
        self.allocator.free(self.model_name);
        if (self.api_key) |k| self.allocator.free(k);
        if (self.provider) |p| self.allocator.free(p);
        self.allocator.destroy(self);
    }

    /// Complete implementation
    fn complete(
        ptr: *anyopaque,
        allocator: Allocator,
        messages: []const *Message,
        options: *const llm.CallOptions,
    ) !*Message {
        const self: *OpenAICompatibleLLM = @ptrCast(@alignCast(ptr));

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
        _ = ptr;
        _ = allocator;
        _ = messages;
        _ = options;
        // Streaming implementation would go here
        // For now, return error as streaming is complex
        return error.StreamingNotSupported;
    }

    /// Model implementation
    fn model(ptr: *anyopaque) []const u8 {
        const self: *OpenAICompatibleLLM = @ptrCast(@alignCast(ptr));
        return self.model_name;
    }

    /// Deinit implementation for VTable
    fn deinitVTable(ptr: *anyopaque) void {
        const self: *OpenAICompatibleLLM = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    /// Build OpenAI-compatible API request body
    fn buildRequestBody(
        self: *OpenAICompatibleLLM,
        allocator: Allocator,
        messages: []const *Message,
        options: *const llm.CallOptions,
        is_stream: bool,
    ) ![]const u8 {
        // Build JSON manually for now (simpler than using std.json API)
        var json = std.ArrayList(u8){};
        defer json.deinit(allocator);

        try json.appendSlice(allocator, "{\"model\":\"");
        try json.appendSlice(allocator, self.model_name);
        try json.appendSlice(allocator, "\",\"messages\":[");

        // Messages array
        for (messages, 0..) |msg, i| {
            if (i > 0) try json.append(allocator, ',');

            try json.appendSlice(allocator, "{\"role\":\"");
            // Map agent role to assistant for OpenAI compatibility
            const role_str = if (msg.role == .agent) "assistant" else msg.role.toString();
            try json.appendSlice(allocator, role_str);
            try json.appendSlice(allocator, "\",\"content\":\"");

            const content = switch (msg.content) {
                .text => |t| t,
                .structured => "", // TODO: Handle structured content
            };

            // Escape special characters in content
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

    /// Make HTTP request to OpenAI-compatible API
    fn makeRequest(self: *OpenAICompatibleLLM, allocator: Allocator, body: []const u8) ![]const u8 {
        var client = std.http.Client{ .allocator = allocator };
        defer client.deinit();

        // Build URI
        const uri_str = try std.fmt.allocPrint(
            allocator,
            "{s}/chat/completions",
            .{self.base_url},
        );
        defer allocator.free(uri_str);

        // Build authorization header (use "not-needed" if no API key)
        const auth_key = self.api_key orelse "not-needed";
        const auth_value = try std.fmt.allocPrint(
            allocator,
            "Bearer {s}",
            .{auth_key},
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

    /// Parse OpenAI-compatible API response
    fn parseResponse(self: *OpenAICompatibleLLM, allocator: Allocator, response_body: []const u8) !*Message {
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

        return msg;
    }
};

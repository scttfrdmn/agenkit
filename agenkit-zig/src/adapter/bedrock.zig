/// AWS Bedrock LLM adapter
///
/// This adapter wraps AWS Bedrock Runtime API to provide access to foundation
/// models from Anthropic, AI21, Cohere, Meta, and Stability AI.
///
/// This implementation focuses on Anthropic Claude models on Bedrock, which is
/// the most common use case.
///
/// Example:
/// ```zig
/// var llm_impl = try BedrockLLM.init(
///     allocator,
///     access_key_id,
///     secret_access_key,
///     "anthropic.claude-3-sonnet-20240229-v1:0",
///     "us-east-1"
/// );
/// defer llm_impl.deinit();
/// const llm = llm_impl.asLLM();
///
/// const messages = [_]*Message{ /* ... */ };
/// var options = CallOptions.init(allocator);
/// defer options.deinit();
/// options.withMaxTokens(1024);
///
/// const response = try llm.complete(allocator, &messages, &options);
/// defer response.deinit();
/// ```

const std = @import("std");
const llm = @import("llm.zig");
const Message = @import("../message.zig").Message;
const Role = @import("../message.zig").Role;
const Allocator = std.mem.Allocator;

/// AWS Bedrock LLM adapter
pub const BedrockLLM = struct {
    allocator: Allocator,
    access_key_id: []const u8,
    secret_access_key: []const u8,
    session_token: ?[]const u8,
    model_id: []const u8,
    region: []const u8,

    /// Initialize Bedrock adapter
    ///
    /// Parameters:
    ///   - allocator: Memory allocator
    ///   - access_key_id: AWS access key ID (or use AWS_ACCESS_KEY_ID env var)
    ///   - secret_access_key: AWS secret access key (or use AWS_SECRET_ACCESS_KEY env var)
    ///   - model_id: Bedrock model identifier (e.g., "anthropic.claude-3-sonnet-20240229-v1:0")
    ///   - region: AWS region (e.g., "us-east-1", or use AWS_REGION env var)
    ///
    /// Returns:
    ///   Initialized BedrockLLM instance
    pub fn init(
        allocator: Allocator,
        access_key_id: []const u8,
        secret_access_key: []const u8,
        model_id: []const u8,
        region: []const u8,
    ) !*BedrockLLM {
        const self = try allocator.create(BedrockLLM);
        errdefer allocator.destroy(self);

        // Access Key ID
        const key_id = if (access_key_id.len > 0)
            try allocator.dupe(u8, access_key_id)
        else blk: {
            const env_key = std.process.getEnvVarOwned(allocator, "AWS_ACCESS_KEY_ID") catch {
                return error.MissingAccessKeyID;
            };
            break :blk env_key;
        };

        // Secret Access Key
        const secret = if (secret_access_key.len > 0)
            try allocator.dupe(u8, secret_access_key)
        else blk: {
            const env_secret = std.process.getEnvVarOwned(allocator, "AWS_SECRET_ACCESS_KEY") catch {
                return error.MissingSecretAccessKey;
            };
            break :blk env_secret;
        };

        // Session Token (optional)
        const token = std.process.getEnvVarOwned(allocator, "AWS_SESSION_TOKEN") catch null;

        // Model ID
        const model_copy = if (model_id.len > 0)
            try allocator.dupe(u8, model_id)
        else
            try allocator.dupe(u8, "anthropic.claude-3-sonnet-20240229-v1:0");

        // Region
        const region_copy = if (region.len > 0)
            try allocator.dupe(u8, region)
        else blk: {
            const env_region = std.process.getEnvVarOwned(allocator, "AWS_REGION") catch {
                // Default to us-east-1
                break :blk try allocator.dupe(u8, "us-east-1");
            };
            break :blk env_region;
        };

        self.* = BedrockLLM{
            .allocator = allocator,
            .access_key_id = key_id,
            .secret_access_key = secret,
            .session_token = token,
            .model_id = model_copy,
            .region = region_copy,
        };

        return self;
    }

    /// Convert to LLM interface
    pub fn asLLM(self: *BedrockLLM) llm.LLM {
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
    pub fn deinit(self: *BedrockLLM) void {
        self.allocator.free(self.access_key_id);
        self.allocator.free(self.secret_access_key);
        if (self.session_token) |token| {
            self.allocator.free(token);
        }
        self.allocator.free(self.model_id);
        self.allocator.free(self.region);
        self.allocator.destroy(self);
    }

    /// Complete implementation
    fn complete(
        ptr: *anyopaque,
        allocator: Allocator,
        messages: []const *Message,
        options: *const llm.CallOptions,
    ) !*Message {
        const self: *BedrockLLM = @ptrCast(@alignCast(ptr));

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
        const self: *BedrockLLM = @ptrCast(@alignCast(ptr));
        return self.model_id;
    }

    /// Deinit implementation for VTable
    fn deinitVTable(ptr: *anyopaque) void {
        const self: *BedrockLLM = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    /// Build Bedrock API request body (Anthropic Claude format)
    fn buildRequestBody(
        self: *BedrockLLM,
        allocator: Allocator,
        messages: []const *Message,
        options: *const llm.CallOptions,
    ) ![]const u8 {
        _ = self;

        var json = std.ArrayList(u8){};
        defer json.deinit(allocator);

        // Anthropic format on Bedrock
        try json.appendSlice(allocator, "{\"anthropic_version\":\"bedrock-2023-05-31\",\"messages\":[");

        // Separate system message (Anthropic Claude requirement)
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

        // Add non-system messages
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

        // System message
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

        // max_tokens is required
        const max_tokens = options.max_tokens orelse 1024;
        const max_str = try std.fmt.allocPrint(allocator, ",\"max_tokens\":{d}", .{max_tokens});
        defer allocator.free(max_str);
        try json.appendSlice(allocator, max_str);

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

    /// Make HTTP request to Bedrock API (with AWS SigV4 signing)
    fn makeRequest(self: *BedrockLLM, allocator: Allocator, body: []const u8) ![]const u8 {
        // Note: Full AWS SigV4 implementation is complex and would require
        // significant code (~300-400 lines for proper implementation).
        // For production use, recommend using AWS SDK or a dedicated library.
        //
        // This is a simplified placeholder that shows the structure.
        // In practice, you would need to implement:
        // 1. Canonical request creation
        // 2. String to sign
        // 3. Signing key derivation
        // 4. Authorization header generation

        _ = self;
        _ = allocator;
        _ = body;

        // TODO: Implement full AWS SigV4 signing
        // For now, return an error indicating this needs AWS SDK
        return error.BedrockRequiresAWSSDK;
    }

    /// Parse Bedrock API response
    fn parseResponse(self: *BedrockLLM, allocator: Allocator, response_body: []const u8) !*Message {
        _ = self;

        const parsed = try std.json.parseFromSlice(
            std.json.Value,
            allocator,
            response_body,
            .{},
        );
        defer parsed.deinit();

        const root = parsed.value.object;

        // Anthropic Claude format
        const content_array = root.get("content") orelse return error.InvalidResponse;
        if (content_array.array.items.len == 0) return error.InvalidResponse;

        const first_content = content_array.array.items[0].object;
        const text = first_content.get("text") orelse return error.InvalidResponse;

        const msg = try allocator.create(Message);
        msg.* = try Message.withText(allocator, .assistant, text.string);

        if (root.get("stop_reason")) |stop_reason| {
            try msg.setMetadata("stop_reason", stop_reason);
        }

        if (root.get("usage")) |usage| {
            try msg.setMetadata("usage", usage);
        }

        return msg;
    }
};

// Tests
test "BedrockLLM initialization" {
    const allocator = std.testing.allocator;

    var llm_impl = try BedrockLLM.init(
        allocator,
        "test-access-key",
        "test-secret-key",
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "us-east-1",
    );
    defer llm_impl.deinit();

    const llm_interface = llm_impl.asLLM();
    try std.testing.expectEqualStrings("anthropic.claude-3-sonnet-20240229-v1:0", llm_interface.model());
}

test "BedrockLLM buildRequestBody" {
    const allocator = std.testing.allocator;

    var llm_impl = try BedrockLLM.init(
        allocator,
        "test-key",
        "test-secret",
        "anthropic.claude-3-haiku-20240307-v1:0",
        "us-west-2",
    );
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
    try std.testing.expect(std.mem.indexOf(u8, body, "\"anthropic_version\":\"bedrock-2023-05-31\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"system\":\"You are helpful.\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"max_tokens\":512") != null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"temperature\":0.7") != null);
}

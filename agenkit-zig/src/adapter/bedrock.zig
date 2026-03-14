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
                    .structured => "", // system prompt must be plain text per Bedrock API
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
                .agent => "assistant",
            };

            try json.appendSlice(allocator, role_str);
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
                    // Structured content: serialize as JSON array (Bedrock Converse API format)
                    const val_json = try std.json.Stringify.valueAlloc(allocator, val, .{});
                    defer allocator.free(val_json);
                    try json.appendSlice(allocator, val_json);
                },
            }

            try json.append(allocator, '}');
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

    /// Make HTTP request to Bedrock API with AWS SigV4 signing
    fn makeRequest(self: *BedrockLLM, allocator: Allocator, body: []const u8) ![]const u8 {
        // Build the Bedrock endpoint URL
        // Format: https://bedrock-runtime.<region>.amazonaws.com/model/<model-id>/invoke
        const host = try std.fmt.allocPrint(
            allocator,
            "bedrock-runtime.{s}.amazonaws.com",
            .{self.region},
        );
        defer allocator.free(host);

        const uri_path = try std.fmt.allocPrint(
            allocator,
            "/model/{s}/invoke",
            .{self.model_id},
        );
        defer allocator.free(uri_path);

        // Get current timestamp for signing
        const timestamp_secs = std.time.timestamp();
        const timestamp = try formatTimestamp(allocator, timestamp_secs);
        defer allocator.free(timestamp);

        const date = timestamp[0..8]; // "YYYYMMDD"

        // Compute payload SHA-256 hash
        var payload_hash_bytes: [std.crypto.hash.sha2.Sha256.digest_length]u8 = undefined;
        std.crypto.hash.sha2.Sha256.hash(body, &payload_hash_bytes, .{});
        const payload_hash = try hexEncode(allocator, &payload_hash_bytes);
        defer allocator.free(payload_hash);

        // Build canonical headers (must be sorted and lowercase)
        const canonical_headers = try std.fmt.allocPrint(
            allocator,
            "content-type:application/json\nhost:{s}\nx-amz-date:{s}\n",
            .{ host, timestamp },
        );
        defer allocator.free(canonical_headers);

        const signed_headers = "content-type;host;x-amz-date";

        // Add session token header if present
        const canonical_headers_with_token = if (self.session_token) |token| blk: {
            const with_token = try std.fmt.allocPrint(
                allocator,
                "content-type:application/json\nhost:{s}\nx-amz-date:{s}\nx-amz-security-token:{s}\n",
                .{ host, timestamp, token },
            );
            break :blk with_token;
        } else null;
        defer if (canonical_headers_with_token) |s| allocator.free(s);

        const final_canonical_headers = canonical_headers_with_token orelse canonical_headers;
        const final_signed_headers = if (self.session_token != null)
            "content-type;host;x-amz-date;x-amz-security-token"
        else
            signed_headers;

        // Step 1: Build canonical request
        const canonical_request = try std.fmt.allocPrint(
            allocator,
            "POST\n{s}\n\n{s}\n{s}\n{s}",
            .{ uri_path, final_canonical_headers, final_signed_headers, payload_hash },
        );
        defer allocator.free(canonical_request);

        // Hash the canonical request
        var cr_hash_bytes: [std.crypto.hash.sha2.Sha256.digest_length]u8 = undefined;
        std.crypto.hash.sha2.Sha256.hash(canonical_request, &cr_hash_bytes, .{});
        const cr_hash = try hexEncode(allocator, &cr_hash_bytes);
        defer allocator.free(cr_hash);

        // Step 2: Build string to sign
        const credential_scope = try std.fmt.allocPrint(
            allocator,
            "{s}/{s}/bedrock/aws4_request",
            .{ date, self.region },
        );
        defer allocator.free(credential_scope);

        const string_to_sign = try std.fmt.allocPrint(
            allocator,
            "AWS4-HMAC-SHA256\n{s}\n{s}\n{s}",
            .{ timestamp, credential_scope, cr_hash },
        );
        defer allocator.free(string_to_sign);

        // Step 3: Build signing key chain
        // signingKey = HMAC(HMAC(HMAC(HMAC("AWS4" + secret, date), region), "bedrock"), "aws4_request")
        const aws4_secret = try std.fmt.allocPrint(allocator, "AWS4{s}", .{self.secret_access_key});
        defer allocator.free(aws4_secret);

        var k_date: [std.crypto.auth.hmac.sha2.HmacSha256.mac_length]u8 = undefined;
        std.crypto.auth.hmac.sha2.HmacSha256.create(&k_date, date, aws4_secret);

        var k_region: [std.crypto.auth.hmac.sha2.HmacSha256.mac_length]u8 = undefined;
        std.crypto.auth.hmac.sha2.HmacSha256.create(&k_region, self.region, &k_date);

        var k_service: [std.crypto.auth.hmac.sha2.HmacSha256.mac_length]u8 = undefined;
        std.crypto.auth.hmac.sha2.HmacSha256.create(&k_service, "bedrock", &k_region);

        var k_signing: [std.crypto.auth.hmac.sha2.HmacSha256.mac_length]u8 = undefined;
        std.crypto.auth.hmac.sha2.HmacSha256.create(&k_signing, "aws4_request", &k_service);

        // Step 4: Compute signature
        var sig_bytes: [std.crypto.auth.hmac.sha2.HmacSha256.mac_length]u8 = undefined;
        std.crypto.auth.hmac.sha2.HmacSha256.create(&sig_bytes, string_to_sign, &k_signing);
        const signature = try hexEncode(allocator, &sig_bytes);
        defer allocator.free(signature);

        // Build Authorization header
        const auth_header = try std.fmt.allocPrint(
            allocator,
            "AWS4-HMAC-SHA256 Credential={s}/{s}, SignedHeaders={s}, Signature={s}",
            .{ self.access_key_id, credential_scope, final_signed_headers, signature },
        );
        defer allocator.free(auth_header);

        // Make the HTTP request
        var client = std.http.Client{ .allocator = allocator };
        defer client.deinit();

        const full_url = try std.fmt.allocPrint(
            allocator,
            "https://{s}{s}",
            .{ host, uri_path },
        );
        defer allocator.free(full_url);

        // Build headers slice (unmanaged ArrayList, Zig 0.15 pattern)
        var headers_list = std.ArrayList(std.http.Header){};
        defer headers_list.deinit(allocator);

        try headers_list.append(allocator, .{ .name = "Content-Type", .value = "application/json" });
        try headers_list.append(allocator, .{ .name = "Authorization", .value = auth_header });
        try headers_list.append(allocator, .{ .name = "x-amz-date", .value = timestamp });
        if (self.session_token) |token| {
            try headers_list.append(allocator, .{ .name = "x-amz-security-token", .value = token });
        }

        var response_body: std.io.Writer.Allocating = .init(allocator);
        defer response_body.deinit();

        const result = try client.fetch(.{
            .location = .{ .url = full_url },
            .method = .POST,
            .payload = body,
            .extra_headers = headers_list.items,
            .response_writer = &response_body.writer,
        });

        if (result.status != .ok) {
            return error.ServerError;
        }

        return try response_body.toOwnedSlice();
    }

    /// Format a Unix timestamp as "YYYYMMDDTHHmmSSZ"
    fn formatTimestamp(allocator: Allocator, secs: i64) ![]const u8 {
        const epoch = std.time.epoch.EpochSeconds{ .secs = @intCast(secs) };
        const epoch_day = epoch.getEpochDay();
        const year_day = epoch_day.calculateYearDay();
        const month_day = year_day.calculateMonthDay();
        const day_seconds = epoch.getDaySeconds();

        return std.fmt.allocPrint(
            allocator,
            "{d:0>4}{d:0>2}{d:0>2}T{d:0>2}{d:0>2}{d:0>2}Z",
            .{
                year_day.year,
                month_day.month.numeric(),
                month_day.day_index + 1,
                day_seconds.getHoursIntoDay(),
                day_seconds.getMinutesIntoHour(),
                day_seconds.getSecondsIntoMinute(),
            },
        );
    }

    /// Hex-encode a byte slice into a lowercase hex string
    fn hexEncode(allocator: Allocator, bytes: []const u8) ![]const u8 {
        const hex_chars = "0123456789abcdef";
        const result = try allocator.alloc(u8, bytes.len * 2);
        for (bytes, 0..) |b, i| {
            result[i * 2] = hex_chars[b >> 4];
            result[i * 2 + 1] = hex_chars[b & 0x0f];
        }
        return result;
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

test "hexEncode produces correct lowercase hex" {
    const allocator = std.testing.allocator;

    const input = [_]u8{ 0x00, 0xff, 0x1a, 0xb3 };
    const result = try BedrockLLM.hexEncode(allocator, &input);
    defer allocator.free(result);

    try std.testing.expectEqualStrings("00ff1ab3", result);
}

test "SigV4 signing key derivation" {
    // Test vector from AWS SigV4 test suite
    // https://docs.aws.amazon.com/general/latest/gr/sigv4-create-signed-request.html
    const secret = "AWS4wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY";
    const date = "20130524";
    const region = "us-east-1";

    var k_date: [std.crypto.auth.hmac.sha2.HmacSha256.mac_length]u8 = undefined;
    std.crypto.auth.hmac.sha2.HmacSha256.create(&k_date, date, secret);

    var k_region: [std.crypto.auth.hmac.sha2.HmacSha256.mac_length]u8 = undefined;
    std.crypto.auth.hmac.sha2.HmacSha256.create(&k_region, region, &k_date);

    var k_service: [std.crypto.auth.hmac.sha2.HmacSha256.mac_length]u8 = undefined;
    std.crypto.auth.hmac.sha2.HmacSha256.create(&k_service, "bedrock", &k_region);

    var k_signing: [std.crypto.auth.hmac.sha2.HmacSha256.mac_length]u8 = undefined;
    std.crypto.auth.hmac.sha2.HmacSha256.create(&k_signing, "aws4_request", &k_service);

    // Signing key is 32 bytes (HMAC-SHA256 output)
    try std.testing.expectEqual(@as(usize, 32), k_signing.len);
}

test "SigV4 payload hash" {
    // SHA-256("") = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    const allocator = std.testing.allocator;

    var hash_bytes: [std.crypto.hash.sha2.Sha256.digest_length]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash("", &hash_bytes, .{});
    const hex = try BedrockLLM.hexEncode(allocator, &hash_bytes);
    defer allocator.free(hex);

    try std.testing.expectEqualStrings(
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        hex,
    );
}

test "formatTimestamp produces correct format" {
    const allocator = std.testing.allocator;

    // 2026-03-14T12:00:00Z = 1773568800 (approx)
    // Use a known timestamp: 2020-01-01T00:00:00Z = 1577836800
    const ts = try BedrockLLM.formatTimestamp(allocator, 1577836800);
    defer allocator.free(ts);

    // Should be 16 chars: "YYYYMMDDTHHmmSSZ"
    try std.testing.expectEqual(@as(usize, 16), ts.len);
    try std.testing.expectEqualStrings("20200101T000000Z", ts);
}

test "BedrockLLM structured content in request body" {
    const allocator = std.testing.allocator;

    var llm_impl = try BedrockLLM.init(
        allocator,
        "test-key",
        "test-secret",
        "anthropic.claude-3-haiku-20240307-v1:0",
        "us-west-2",
    );
    defer llm_impl.deinit();

    // Build a structured json.Value directly (array of content blocks)
    const parsed = try std.json.parseFromSlice(
        std.json.Value,
        allocator,
        "[{\"type\":\"text\",\"text\":\"Hello from structured\"}]",
        .{},
    );
    defer parsed.deinit();

    var user = Message.withStructured(allocator, .user, parsed.value);
    defer user.deinit();

    const messages = [_]*Message{&user};
    var options = llm.CallOptions.init(allocator);
    defer options.deinit();

    const body = try llm_impl.buildRequestBody(allocator, &messages, &options);
    defer allocator.free(body);

    // Structured content should appear as a JSON array, not an empty string
    try std.testing.expect(std.mem.indexOf(u8, body, "\"content\":\"\"") == null);
    try std.testing.expect(std.mem.indexOf(u8, body, "\"content\":[") != null);
}

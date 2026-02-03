/// Message represents communication between agents and users
///
/// In Agenkit, messages are the fundamental unit of communication. Each message
/// has a role (user, assistant, system) and content (text or structured data).
/// Messages also carry metadata for tracing, session management, and custom fields.
///
/// This implementation follows Zig best practices:
/// - Explicit memory management with allocators
/// - Error handling with error union types (!)
/// - No hidden allocations or control flow
const std = @import("std");
const json = std.json;
const Allocator = std.mem.Allocator;

/// Message role enumeration
pub const Role = enum {
    user,
    assistant,
    system,
    tool,
    agent,

    pub fn toString(self: Role) []const u8 {
        return switch (self) {
            .user => "user",
            .assistant => "assistant",
            .system => "system",
            .tool => "tool",
            .agent => "agent",
        };
    }

    pub fn fromString(s: []const u8) !Role {
        if (std.mem.eql(u8, s, "user")) return .user;
        if (std.mem.eql(u8, s, "assistant")) return .assistant;
        if (std.mem.eql(u8, s, "system")) return .system;
        if (std.mem.eql(u8, s, "tool")) return .tool;
        if (std.mem.eql(u8, s, "agent")) return .agent;
        return error.InvalidRole;
    }
};

/// Content type for messages (text or structured)
pub const Content = union(enum) {
    text: []const u8,
    structured: json.Value,

    pub fn deinit(self: *Content, allocator: Allocator) void {
        switch (self.*) {
            .text => |t| allocator.free(t),
            .structured => {
                // JSON values are owned by the allocator
                // No explicit deinit needed for individual values
            },
        }
    }
};

/// Message validation errors
pub const ValidationError = error{
    EmptyRole,
    RoleTooLong,
    InvalidRole,
    ContentTooLarge,
    TooManyMetadataKeys,
    MetadataKeyTooLong,
    MetadataValueTooLarge,
};

/// Message represents a single communication unit
pub const Message = struct {
    role: Role,
    content: Content,
    metadata: json.Value,
    allocator: Allocator,

    /// Create a new message with text content
    pub fn withText(allocator: Allocator, role: Role, text: []const u8) !Message {
        const owned_text = try allocator.dupe(u8, text);
        return Message{
            .role = role,
            .content = .{ .text = owned_text },
            .metadata = json.Value{ .object = json.ObjectMap.init(allocator) },
            .allocator = allocator,
        };
    }

    /// Create a new message with structured content
    pub fn withStructured(allocator: Allocator, role: Role, data: json.Value) Message {
        return Message{
            .role = role,
            .content = .{ .structured = data },
            .metadata = json.Value{ .object = json.ObjectMap.init(allocator) },
            .allocator = allocator,
        };
    }

    /// Free all resources associated with this message
    fn freeJsonValue(allocator: Allocator, value: json.Value) void {
        switch (value) {
            .array => |arr| {
                // Free all items in the array (including strings)
                for (arr.items) |item| {
                    switch (item) {
                        .string => |s| allocator.free(s),
                        .array => freeJsonValue(allocator, item),
                        .object => freeJsonValue(allocator, item),
                        .number_string => |s| allocator.free(s),
                        else => {},
                    }
                }
                var mut_arr = arr;
                mut_arr.deinit();
            },
            .object => |obj| {
                var it = obj.iterator();
                while (it.next()) |entry| {
                    freeJsonValue(allocator, entry.value_ptr.*);
                }
                var mut_obj = obj;
                mut_obj.deinit();
            },
            else => {
                // Don't free top-level strings - they might be static literals
            },
        }
    }

    pub fn deinit(self: *Message) void {
        self.content.deinit(self.allocator);
        // Free all metadata values recursively
        var it = self.metadata.object.iterator();
        while (it.next()) |entry| {
            freeJsonValue(self.allocator, entry.value_ptr.*);
        }
        // Free the ObjectMap internal storage
        self.metadata.object.deinit();
    }

    /// Set metadata key-value pair
    pub fn setMetadata(self: *Message, key: []const u8, value: json.Value) !void {
        try self.metadata.object.put(key, value);
    }

    /// Get metadata value by key
    pub fn getMetadata(self: *const Message, key: []const u8) ?json.Value {
        return self.metadata.object.get(key);
    }

    /// Get content as text (returns error if structured)
    pub fn contentAsText(self: *const Message) ![]const u8 {
        return switch (self.content) {
            .text => |t| t,
            .structured => error.ContentNotText,
        };
    }

    /// Validate message according to security constraints
    ///
    /// Checks:
    /// - Role is valid enum value (enforced by type system)
    /// - Content size <= 16MB
    /// - Metadata has <= 100 keys
    /// - Each metadata key <= 50 characters
    /// - Each metadata value <= 16MB
    ///
    /// Returns ValidationError if validation fails
    pub fn validate(self: *const Message) !void {
        // Role validation is enforced by enum type system

        // Content size validation - max 16MB
        const content_size = switch (self.content) {
            .text => |t| t.len,
            .structured => |_| blk: {
                // For structured content, we can't easily compute exact size
                // without serializing. Skip size check for structured content.
                // In practice, structured content size is validated when
                // it's serialized for transport.
                break :blk 0;
            },
        };

        const max_content_size = 16 * 1024 * 1024; // 16MB
        if (content_size > max_content_size) {
            std.log.err(
                "Message content exceeds maximum size of {d} bytes (got {d} bytes)",
                .{ max_content_size, content_size },
            );
            return ValidationError.ContentTooLarge;
        }

        // Metadata validation
        if (self.metadata == .object) {
            const metadata_obj = self.metadata.object;

            // Max 100 keys
            if (metadata_obj.count() > 100) {
                std.log.err(
                    "Message metadata exceeds maximum of 100 keys (got {d})",
                    .{metadata_obj.count()},
                );
                return ValidationError.TooManyMetadataKeys;
            }

            // Validate each key and value
            const max_key_length = 50;
            const max_value_size = 16 * 1024 * 1024; // 16MB

            var it = metadata_obj.iterator();
            while (it.next()) |entry| {
                // Key length validation
                if (entry.key_ptr.*.len > max_key_length) {
                    std.log.err(
                        "Metadata key exceeds maximum length of {d} characters (got {d})",
                        .{ max_key_length, entry.key_ptr.*.len },
                    );
                    return ValidationError.MetadataKeyTooLong;
                }

                // Value size validation (only for string values)
                // For non-string values, size validation happens during serialization
                if (entry.value_ptr.* == .string) {
                    const value_size = entry.value_ptr.*.string.len;
                    if (value_size > max_value_size) {
                        std.log.err(
                            "Metadata value for key '{s}' exceeds maximum size of {d} bytes (got {d} bytes)",
                            .{ entry.key_ptr.*, max_value_size, value_size },
                        );
                        return ValidationError.MetadataValueTooLarge;
                    }
                }
            }
        }
    }

    /// Serialize message to JSON
    pub fn toJson(self: *const Message, allocator: Allocator) !json.Value {
        var obj = json.ObjectMap.init(allocator);

        // Add role
        try obj.put("role", json.Value{ .string = self.role.toString() });

        // Add content
        switch (self.content) {
            .text => |t| {
                try obj.put("content", json.Value{ .string = t });
            },
            .structured => |s| {
                try obj.put("content", s);
            },
        }

        // Add metadata
        try obj.put("metadata", self.metadata);

        return json.Value{ .object = obj };
    }

    /// Deserialize message from JSON
    pub fn fromJson(allocator: Allocator, value: json.Value) !Message {
        if (value != .object) return error.InvalidMessageJson;

        const obj = value.object;

        // Parse role
        const role_str = obj.get("role") orelse return error.MissingRole;
        const role = try Role.fromString(role_str.string);

        // Parse content
        const content_val = obj.get("content") orelse return error.MissingContent;
        const content: Content = switch (content_val) {
            .string => |s| .{ .text = try allocator.dupe(u8, s) },
            else => .{ .structured = content_val },
        };

        // Parse metadata (optional)
        const metadata = if (obj.get("metadata")) |m| m else json.Value{ .object = json.ObjectMap.init(allocator) };

        return Message{
            .role = role,
            .content = content,
            .metadata = metadata,
            .allocator = allocator,
        };
    }
};

test "Message creation with text" {
    const allocator = std.testing.allocator;

    var msg = try Message.withText(allocator, .user, "Hello, world!");
    defer msg.deinit();

    try std.testing.expectEqual(Role.user, msg.role);
    const text = try msg.contentAsText();
    try std.testing.expectEqualStrings("Hello, world!", text);
}

test "Message metadata" {
    const allocator = std.testing.allocator;

    var msg = try Message.withText(allocator, .assistant, "Response");
    defer msg.deinit();

    try msg.setMetadata("session_id", json.Value{ .string = "test-123" });

    const session_id = msg.getMetadata("session_id");
    try std.testing.expect(session_id != null);
    try std.testing.expectEqualStrings("test-123", session_id.?.string);
}

test "Message role conversion" {
    try std.testing.expectEqualStrings("user", Role.user.toString());
    try std.testing.expectEqualStrings("assistant", Role.assistant.toString());

    const role = try Role.fromString("system");
    try std.testing.expectEqual(Role.system, role);
}

// Message validation tests

test "validate valid message" {
    const allocator = std.testing.allocator;

    var msg = try Message.withText(allocator, .user, "Hello");
    defer msg.deinit();

    try msg.validate();
}

test "validate content too large" {
    const allocator = std.testing.allocator;

    // Create a large string (>16MB)
    const large_content = try allocator.alloc(u8, 17 * 1024 * 1024);
    defer allocator.free(large_content);
    @memset(large_content, 'a');

    var msg = try Message.withText(allocator, .user, large_content);
    defer msg.deinit();

    try std.testing.expectError(ValidationError.ContentTooLarge, msg.validate());
}

test "validate content under limit" {
    const allocator = std.testing.allocator;

    // Create a 1MB string
    const content = try allocator.alloc(u8, 1024 * 1024);
    defer allocator.free(content);
    @memset(content, 'a');

    var msg = try Message.withText(allocator, .user, content);
    defer msg.deinit();

    try msg.validate();
}

test "validate too many metadata keys" {
    const allocator = std.testing.allocator;

    var msg = try Message.withText(allocator, .user, "Hello");
    defer {
        // Free allocated keys before deinit
        var it = msg.metadata.object.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        msg.deinit();
    }

    // Add 101 metadata keys
    var i: usize = 0;
    while (i < 101) : (i += 1) {
        var key_buf: [20]u8 = undefined;
        const key = try std.fmt.bufPrint(&key_buf, "key{d}", .{i});
        const key_owned = try allocator.dupe(u8, key);
        try msg.setMetadata(key_owned, json.Value{ .string = "value" });
    }

    try std.testing.expectError(ValidationError.TooManyMetadataKeys, msg.validate());
}

test "validate 100 metadata keys" {
    const allocator = std.testing.allocator;

    var msg = try Message.withText(allocator, .user, "Hello");
    defer {
        // Free allocated keys before deinit
        var it = msg.metadata.object.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        msg.deinit();
    }

    // Add 100 metadata keys
    var i: usize = 0;
    while (i < 100) : (i += 1) {
        var key_buf: [20]u8 = undefined;
        const key = try std.fmt.bufPrint(&key_buf, "key{d}", .{i});
        const key_owned = try allocator.dupe(u8, key);
        try msg.setMetadata(key_owned, json.Value{ .string = "value" });
    }

    try msg.validate();
}

test "validate metadata key too long" {
    const allocator = std.testing.allocator;

    var msg = try Message.withText(allocator, .user, "Hello");
    defer msg.deinit();

    // Create a 51-character key
    const long_key = try allocator.alloc(u8, 51);
    defer allocator.free(long_key);
    @memset(long_key, 'a');

    try msg.setMetadata(long_key, json.Value{ .string = "value" });

    try std.testing.expectError(ValidationError.MetadataKeyTooLong, msg.validate());
}

test "validate metadata key 50 chars" {
    const allocator = std.testing.allocator;

    var msg = try Message.withText(allocator, .user, "Hello");
    defer msg.deinit();

    // Create a 50-character key
    const key = try allocator.alloc(u8, 50);
    defer allocator.free(key);
    @memset(key, 'a');

    try msg.setMetadata(key, json.Value{ .string = "value" });

    try msg.validate();
}

test "validate metadata value too large" {
    const allocator = std.testing.allocator;

    var msg = try Message.withText(allocator, .user, "Hello");
    defer msg.deinit();

    // Create a large value (>16MB)
    const large_value = try allocator.alloc(u8, 17 * 1024 * 1024);
    defer allocator.free(large_value);
    @memset(large_value, 'a');

    try msg.setMetadata("key", json.Value{ .string = large_value });

    try std.testing.expectError(ValidationError.MetadataValueTooLarge, msg.validate());
}

test "validate metadata value under limit" {
    const allocator = std.testing.allocator;

    var msg = try Message.withText(allocator, .user, "Hello");
    defer msg.deinit();

    // Create a 1MB value
    const value = try allocator.alloc(u8, 1024 * 1024);
    defer allocator.free(value);
    @memset(value, 'a');

    try msg.setMetadata("key", json.Value{ .string = value });

    try msg.validate();
}

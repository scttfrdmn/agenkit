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

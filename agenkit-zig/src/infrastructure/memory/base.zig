/// Memory system base interfaces and types.
///
/// This module provides the foundational types for conversational memory:
/// - MemoryEntry: Individual memory records
/// - Memory: Interface for memory implementations
///
/// Memory systems enable agents to maintain context across conversations by:
/// - Storing and retrieving conversation history
/// - Managing context window limits
/// - Applying retention strategies
/// - Supporting hierarchical memory tiers
///
/// Example:
/// ```zig
/// const memory = @import("memory/base.zig");
///
/// var entry = try memory.MemoryEntry.init(
///     allocator,
///     "session-123",
///     .user,
///     "What's the weather?",
/// );
/// defer entry.deinit();
///
/// try mem_store.store(entry);
/// const entries = try mem_store.retrieve("session-123", 10);
/// ```
const std = @import("std");
const ioc = @import("../../io_compat.zig");
const agktime = @import("../../time_compat.zig");
const json = std.json;
const Allocator = std.mem.Allocator;

/// Generate a UUID v4 string.
fn generateUuid(allocator: Allocator) ![]const u8 {
    var uuid: [16]u8 = undefined;
    ioc.randomBytes(&uuid);

    // Set version (4) and variant bits
    uuid[6] = (uuid[6] & 0x0f) | 0x40;
    uuid[8] = (uuid[8] & 0x3f) | 0x80;

    // Format as string: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    const uuid_str = try std.fmt.allocPrint(
        allocator,
        "{x:0>2}{x:0>2}{x:0>2}{x:0>2}-{x:0>2}{x:0>2}-{x:0>2}{x:0>2}-{x:0>2}{x:0>2}-{x:0>2}{x:0>2}{x:0>2}{x:0>2}{x:0>2}{x:0>2}",
        .{
            uuid[0],  uuid[1],  uuid[2],  uuid[3],
            uuid[4],  uuid[5],  uuid[6],  uuid[7],
            uuid[8],  uuid[9],  uuid[10], uuid[11],
            uuid[12], uuid[13], uuid[14], uuid[15],
        },
    );

    return uuid_str;
}

/// Role of a memory entry (matches message roles)
pub const Role = enum {
    user,
    assistant,
    system,

    pub fn toString(self: Role) []const u8 {
        return switch (self) {
            .user => "user",
            .assistant => "assistant",
            .system => "system",
        };
    }

    pub fn fromString(s: []const u8) !Role {
        if (std.mem.eql(u8, s, "user")) return .user;
        if (std.mem.eql(u8, s, "assistant")) return .assistant;
        if (std.mem.eql(u8, s, "system")) return .system;
        return error.InvalidRole;
    }
};

/// MemoryEntry represents a single memory record.
///
/// Each entry captures:
/// - Who said it (role)
/// - What was said (content)
/// - When it was said (timestamp)
/// - How important it is (importance score)
/// - Additional context (metadata)
pub const MemoryEntry = struct {
    /// Unique identifier for this entry
    id: []const u8,

    /// Session this entry belongs to
    session_id: []const u8,

    /// Role of the speaker
    role: Role,

    /// Content of the memory
    content: []const u8,

    /// Timestamp (Unix milliseconds)
    timestamp: i64,

    /// Importance score (0.0-1.0, higher = more important)
    importance: f32,

    /// Additional metadata
    metadata: json.Value,

    /// Allocator for memory management
    allocator: Allocator,

    /// Initialize a new memory entry.
    ///
    /// Args:
    ///   allocator: Memory allocator
    ///   session_id: Session identifier
    ///   role: Speaker role
    ///   content: Memory content
    ///
    /// Returns:
    ///   New memory entry with generated ID and current timestamp
    pub fn init(
        allocator: Allocator,
        session_id: []const u8,
        role: Role,
        content: []const u8,
    ) !MemoryEntry {
        // Generate UUID v4 for entry ID
        const id = try generateUuid(allocator);

        return MemoryEntry{
            .id = id,
            .session_id = try allocator.dupe(u8, session_id),
            .role = role,
            .content = try allocator.dupe(u8, content),
            .timestamp = agktime.milliTimestamp(),
            .importance = 0.5, // Default neutral importance
            .metadata = json.Value{ .object = json.ObjectMap.empty },
            .allocator = allocator,
        };
    }

    /// Free all resources.
    pub fn deinit(self: *MemoryEntry) void {
        self.allocator.free(self.id);
        self.allocator.free(self.session_id);
        self.allocator.free(self.content);

        // Free metadata keys
        var iter = self.metadata.object.iterator();
        while (iter.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
        }
        self.metadata.object.deinit(self.allocator);
    }

    /// Set importance score.
    ///
    /// Args:
    ///   score: Importance (0.0-1.0)
    pub fn setImportance(self: *MemoryEntry, score: f32) void {
        self.importance = std.math.clamp(score, 0.0, 1.0);
    }

    /// Set metadata value.
    ///
    /// Args:
    ///   key: Metadata key
    ///   value: Metadata value
    pub fn setMetadata(self: *MemoryEntry, key: []const u8, value: json.Value) !void {
        const key_copy = try self.allocator.dupe(u8, key);
        try self.metadata.object.put(key_copy, value);
    }

    /// Get metadata value.
    ///
    /// Args:
    ///   key: Metadata key
    ///
    /// Returns:
    ///   Metadata value or null
    pub fn getMetadata(self: *const MemoryEntry, key: []const u8) ?json.Value {
        return self.metadata.object.get(key);
    }
};

/// Memory interface for storage implementations.
///
/// All memory implementations must provide:
/// - store: Save a memory entry
/// - retrieve: Get entries for a session
/// - summarize: Create a summary of memories
/// - clear: Remove entries
pub const Memory = struct {
    ptr: *anyopaque,
    vtable: *const VTable,

    pub const VTable = struct {
        store: *const fn (ptr: *anyopaque, entry: *const MemoryEntry) anyerror!void,
        retrieve: *const fn (
            ptr: *anyopaque,
            session_id: []const u8,
            limit: usize,
        ) anyerror![]const *MemoryEntry,
        summarize: *const fn (
            ptr: *anyopaque,
            session_id: []const u8,
            max_entries: usize,
        ) anyerror![]const u8,
        clear: *const fn (ptr: *anyopaque, session_id: []const u8) anyerror!usize,
        deinit: *const fn (ptr: *anyopaque) void,
    };

    /// Store a memory entry.
    ///
    /// Args:
    ///   entry: Memory entry to store
    pub fn store(self: Memory, entry: *const MemoryEntry) !void {
        return self.vtable.store(self.ptr, entry);
    }

    /// Retrieve memory entries for a session.
    ///
    /// Args:
    ///   session_id: Session identifier
    ///   limit: Maximum number of entries to return (0 = all)
    ///
    /// Returns:
    ///   Array of memory entries (caller owns memory)
    pub fn retrieve(self: Memory, session_id: []const u8, limit: usize) ![]const *MemoryEntry {
        return self.vtable.retrieve(self.ptr, session_id, limit);
    }

    /// Create a summary of memories.
    ///
    /// Args:
    ///   session_id: Session identifier
    ///   max_entries: Maximum entries to summarize
    ///
    /// Returns:
    ///   Summary text (caller owns memory)
    pub fn summarize(self: Memory, session_id: []const u8, max_entries: usize) ![]const u8 {
        return self.vtable.summarize(self.ptr, session_id, max_entries);
    }

    /// Clear memories for a session.
    ///
    /// Args:
    ///   session_id: Session identifier
    ///
    /// Returns:
    ///   Number of entries cleared
    pub fn clear(self: Memory, session_id: []const u8) !usize {
        return self.vtable.clear(self.ptr, session_id);
    }

    /// Free all resources.
    pub fn deinit(self: Memory) void {
        return self.vtable.deinit(self.ptr);
    }
};

// Tests
const testing = std.testing;

test "MemoryEntry creation" {
    const allocator = testing.allocator;

    var entry = try MemoryEntry.init(
        allocator,
        "session-123",
        .user,
        "Hello, world!",
    );
    defer entry.deinit();

    try testing.expectEqualStrings("session-123", entry.session_id);
    try testing.expectEqual(Role.user, entry.role);
    try testing.expectEqualStrings("Hello, world!", entry.content);
    try testing.expectEqual(@as(f32, 0.5), entry.importance);
}

test "MemoryEntry importance" {
    const allocator = testing.allocator;

    var entry = try MemoryEntry.init(allocator, "session-1", .assistant, "Test");
    defer entry.deinit();

    entry.setImportance(0.8);
    try testing.expectEqual(@as(f32, 0.8), entry.importance);

    // Test clamping
    entry.setImportance(1.5);
    try testing.expectEqual(@as(f32, 1.0), entry.importance);

    entry.setImportance(-0.5);
    try testing.expectEqual(@as(f32, 0.0), entry.importance);
}

test "MemoryEntry metadata" {
    const allocator = testing.allocator;

    var entry = try MemoryEntry.init(allocator, "session-1", .user, "Test");
    defer entry.deinit();

    try entry.setMetadata("key1", json.Value{ .string = "value1" });
    try entry.setMetadata("key2", json.Value{ .integer = 42 });

    const val1 = entry.getMetadata("key1");
    try testing.expect(val1 != null);
    try testing.expect(val1.? == .string);

    const val2 = entry.getMetadata("key2");
    try testing.expect(val2 != null);
    try testing.expect(val2.? == .integer);
    try testing.expectEqual(@as(i64, 42), val2.?.integer);
}

test "Role toString and fromString" {
    try testing.expectEqualStrings("user", Role.user.toString());
    try testing.expectEqualStrings("assistant", Role.assistant.toString());
    try testing.expectEqualStrings("system", Role.system.toString());

    try testing.expectEqual(Role.user, try Role.fromString("user"));
    try testing.expectEqual(Role.assistant, try Role.fromString("assistant"));
    try testing.expectEqual(Role.system, try Role.fromString("system"));

    try testing.expectError(error.InvalidRole, Role.fromString("invalid"));
}

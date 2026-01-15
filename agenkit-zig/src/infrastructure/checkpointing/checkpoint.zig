/// Checkpointing functionality for durable agent execution.
///
/// Checkpoints capture agent state at a point in time, enabling:
///   - Resume after crashes/restarts
///   - Time-travel debugging
///   - Durable execution for long-running agents
///
/// Components:
///   - Checkpoint: Data structure capturing agent state
///   - JSON serialization/deserialization
///
/// Example:
///   var checkpoint = try Checkpoint.init(allocator, "session-1", "assistant", 5);
///   defer checkpoint.deinit();
///   try checkpoint.setState("counter", .{ .integer = 5 });
///   const json_str = try checkpoint.toJson();
const std = @import("std");
const json = std.json;
const Allocator = std.mem.Allocator;
const Message = @import("../../message.zig").Message;

/// Free a JSON value recursively (including all allocated strings and objects).
fn freeJsonValue(allocator: Allocator, value: json.Value) void {
    switch (value) {
        .null, .bool, .integer, .float => {},
        .number_string => |ns| allocator.free(ns),
        .string => |s| allocator.free(s),
        .array => |arr| {
            for (arr.items) |item| {
                freeJsonValue(allocator, item);
            }
            // Free the ArrayList backing storage (json.Array is Managed)
            var mut_arr = arr;
            mut_arr.deinit();
        },
        .object => |obj| {
            var iter = obj.iterator();
            while (iter.next()) |entry| {
                allocator.free(entry.key_ptr.*);
                freeJsonValue(allocator, entry.value_ptr.*);
            }
            var mut_obj = obj;
            mut_obj.deinit();
        },
    }
}

/// Deep copy a JSON value to avoid dangling pointers.
fn deepCopyJsonValue(allocator: Allocator, value: json.Value) !json.Value {
    return switch (value) {
        .null => .null,
        .bool => |b| .{ .bool = b },
        .integer => |i| .{ .integer = i },
        .float => |f| .{ .float = f },
        .number_string => |ns| .{ .number_string = try allocator.dupe(u8, ns) },
        .string => |s| .{ .string = try allocator.dupe(u8, s) },
        .array => |arr| {
            var array_copy = json.Array.init(allocator);
            for (arr.items) |item| {
                try array_copy.append(try deepCopyJsonValue(allocator, item));
            }
            return .{ .array = array_copy };
        },
        .object => |obj| {
            var object_copy = json.ObjectMap.init(allocator);
            var iter = obj.iterator();
            while (iter.next()) |entry| {
                const key_copy = try allocator.dupe(u8, entry.key_ptr.*);
                const value_copy = try deepCopyJsonValue(allocator, entry.value_ptr.*);
                try object_copy.put(key_copy, value_copy);
            }
            return .{ .object = object_copy };
        },
    };
}

/// Checkpoint captures agent state at a point in time.
///
/// Fields:
///   - checkpoint_id: Unique checkpoint identifier
///   - session_id: Session this checkpoint belongs to
///   - agent_name: Name of the agent
///   - timestamp: When checkpoint was created (Unix timestamp in milliseconds)
///   - step_number: Sequential step number in session
///   - state: Agent state (custom data as JSON)
///   - messages: Conversation messages up to this point
///   - metadata: Additional metadata (cost, tokens, etc.)
///   - parent_checkpoint_id: ID of previous checkpoint (for history)
pub const Checkpoint = struct {
    checkpoint_id: []const u8,
    session_id: []const u8,
    agent_name: []const u8,
    timestamp: i64,
    step_number: usize,
    state: json.Value,
    messages: []Message,
    metadata: json.Value,
    parent_checkpoint_id: ?[]const u8,
    allocator: Allocator,

    /// Initialize a new checkpoint.
    ///
    /// Args:
    ///   allocator: Memory allocator
    ///   session_id: Session identifier
    ///   agent_name: Agent name
    ///   step_number: Sequential step number
    ///
    /// Returns:
    ///   New checkpoint with generated UUID
    pub fn init(
        allocator: Allocator,
        session_id: []const u8,
        agent_name: []const u8,
        step_number: usize,
    ) !Checkpoint {
        // Generate UUID for checkpoint
        const checkpoint_id = try generateUuid(allocator);

        // Get current timestamp in milliseconds
        const timestamp = std.time.milliTimestamp();

        return Checkpoint{
            .checkpoint_id = checkpoint_id,
            .session_id = try allocator.dupe(u8, session_id),
            .agent_name = try allocator.dupe(u8, agent_name),
            .timestamp = timestamp,
            .step_number = step_number,
            .state = json.Value{ .object = json.ObjectMap.init(allocator) },
            .messages = try allocator.alloc(Message, 0),
            .metadata = json.Value{ .object = json.ObjectMap.init(allocator) },
            .parent_checkpoint_id = null,
            .allocator = allocator,
        };
    }

    /// Initialize checkpoint with parent checkpoint ID.
    ///
    /// Args:
    ///   allocator: Memory allocator
    ///   session_id: Session identifier
    ///   agent_name: Agent name
    ///   step_number: Sequential step number
    ///   parent_id: Parent checkpoint ID
    ///
    /// Returns:
    ///   New checkpoint with parent link
    pub fn initWithParent(
        allocator: Allocator,
        session_id: []const u8,
        agent_name: []const u8,
        step_number: usize,
        parent_id: []const u8,
    ) !Checkpoint {
        var checkpoint = try init(allocator, session_id, agent_name, step_number);
        checkpoint.parent_checkpoint_id = try allocator.dupe(u8, parent_id);
        return checkpoint;
    }

    /// Free all resources associated with this checkpoint.
    pub fn deinit(self: *Checkpoint) void {
        self.allocator.free(self.checkpoint_id);
        self.allocator.free(self.session_id);
        self.allocator.free(self.agent_name);

        if (self.parent_checkpoint_id) |parent_id| {
            self.allocator.free(parent_id);
        }

        // Free state ObjectMap (including all keys and values recursively)
        var state_iter = self.state.object.iterator();
        while (state_iter.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            freeJsonValue(self.allocator, entry.value_ptr.*);
        }
        self.state.object.deinit();

        // Free metadata ObjectMap (including all keys and values recursively)
        var metadata_iter = self.metadata.object.iterator();
        while (metadata_iter.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            freeJsonValue(self.allocator, entry.value_ptr.*);
        }
        self.metadata.object.deinit();

        // Free messages
        for (self.messages) |*msg| {
            msg.deinit();
        }
        self.allocator.free(self.messages);
    }

    /// Set state value.
    ///
    /// Args:
    ///   key: State key
    ///   value: State value (JSON)
    ///
    /// Note: Takes ownership of value. Key is duplicated.
    pub fn setState(self: *Checkpoint, key: []const u8, value: json.Value) !void {
        // Check if key exists and free old value
        if (self.state.object.getPtr(key)) |old_value| {
            // Free the old value
            freeJsonValue(self.allocator, old_value.*);
            // Update with new value
            old_value.* = value;
        } else {
            // Duplicate key and store
            const key_copy = try self.allocator.dupe(u8, key);
            try self.state.object.put(key_copy, value);
        }
    }

    /// Get state value.
    ///
    /// Args:
    ///   key: State key
    ///
    /// Returns:
    ///   State value or null if not found
    pub fn getState(self: *const Checkpoint, key: []const u8) ?json.Value {
        return self.state.object.get(key);
    }

    /// Set messages.
    ///
    /// Args:
    ///   messages: Message array (ownership transferred)
    pub fn setMessages(self: *Checkpoint, messages: []Message) void {
        // Free old messages
        for (self.messages) |*msg| {
            msg.deinit();
        }
        self.allocator.free(self.messages);

        self.messages = messages;
    }

    /// Set metadata value.
    ///
    /// Args:
    ///   key: Metadata key
    ///   value: Metadata value (JSON)
    ///
    /// Note: Takes ownership of value. Key is duplicated.
    pub fn setMetadata(self: *Checkpoint, key: []const u8, value: json.Value) !void {
        // Check if key exists and free old value
        if (self.metadata.object.getPtr(key)) |old_value| {
            // Free the old value
            freeJsonValue(self.allocator, old_value.*);
            // Update with new value
            old_value.* = value;
        } else {
            // Duplicate key and store
            const key_copy = try self.allocator.dupe(u8, key);
            try self.metadata.object.put(key_copy, value);
        }
    }

    /// Get metadata value.
    ///
    /// Args:
    ///   key: Metadata key
    ///
    /// Returns:
    ///   Metadata value or null if not found
    pub fn getMetadata(self: *const Checkpoint, key: []const u8) ?json.Value {
        return self.metadata.object.get(key);
    }

    /// Convert checkpoint to JSON object.
    ///
    /// Returns:
    ///   JSON representation as ObjectMap
    pub fn toJsonObject(self: *const Checkpoint) !json.Value {
        var obj = json.ObjectMap.init(self.allocator);

        // Add checkpoint_id
        try obj.put("checkpoint_id", json.Value{ .string = self.checkpoint_id });

        // Add session_id
        try obj.put("session_id", json.Value{ .string = self.session_id });

        // Add agent_name
        try obj.put("agent_name", json.Value{ .string = self.agent_name });

        // Add timestamp as RFC3339 string
        const timestamp_str = try formatTimestamp(self.allocator, self.timestamp);
        try obj.put("timestamp", json.Value{ .string = timestamp_str });

        // Add step_number
        try obj.put("step_number", json.Value{ .integer = @intCast(self.step_number) });

        // Add state
        try obj.put("state", self.state);

        // Add messages as JSON array
        const messages_array = try self.allocator.alloc(json.Value, self.messages.len);
        for (self.messages, 0..) |*msg, i| {
            messages_array[i] = try msg.toJson(self.allocator);
        }
        const messages_array_list = json.Array.fromOwnedSlice(self.allocator, messages_array);
        try obj.put("messages", json.Value{ .array = messages_array_list });

        // Add metadata
        try obj.put("metadata", self.metadata);

        // Add parent_checkpoint_id if present
        if (self.parent_checkpoint_id) |parent_id| {
            try obj.put("parent_checkpoint_id", json.Value{ .string = parent_id });
        }

        return json.Value{ .object = obj };
    }

    /// Serialize checkpoint to JSON string.
    ///
    /// Returns:
    ///   JSON string (caller owns memory)
    pub fn toJson(self: *const Checkpoint) ![]const u8 {
        var json_obj = try self.toJsonObject();
        defer {
            // Free allocated values before deinit
            // 1. Free timestamp string (allocated in toJsonObject)
            if (json_obj.object.get("timestamp")) |timestamp_val| {
                if (timestamp_val == .string) {
                    self.allocator.free(timestamp_val.string);
                }
            }
            // 2. Free messages array and ObjectMaps (but not the strings inside, which are refs)
            if (json_obj.object.get("messages")) |messages_val| {
                if (messages_val == .array) {
                    // Free each message's ObjectMap (not the strings, they're refs to message data)
                    for (messages_val.array.items) |msg_val| {
                        if (msg_val == .object) {
                            var mut_obj = msg_val.object;
                            mut_obj.deinit();
                        }
                    }
                    // Free the array backing storage
                    var mut_array = messages_val.array;
                    mut_array.deinit();
                }
            }
            json_obj.object.deinit();
        }

        var buffer: [16384]u8 = undefined;
        var fba = std.heap.FixedBufferAllocator.init(&buffer);
        const fba_alloc = fba.allocator();
        var string_list: std.ArrayList(u8) = .{};
        defer string_list.deinit(fba_alloc);

        try std.fmt.format(string_list.writer(fba_alloc), "{f}", .{json.fmt(json_obj, .{})});
        return try self.allocator.dupe(u8, string_list.items);
    }

    /// Deserialize checkpoint from JSON string.
    ///
    /// Args:
    ///   allocator: Memory allocator
    ///   json_str: JSON string
    ///
    /// Returns:
    ///   Checkpoint (caller owns memory)
    pub fn fromJson(allocator: Allocator, json_str: []const u8) !Checkpoint {
        const parsed = try json.parseFromSlice(json.Value, allocator, json_str, .{});
        defer parsed.deinit();

        const obj = parsed.value.object;

        // Parse checkpoint_id
        const checkpoint_id = obj.get("checkpoint_id") orelse return error.MissingCheckpointId;

        // Parse session_id
        const session_id = obj.get("session_id") orelse return error.MissingSessionId;

        // Parse agent_name
        const agent_name = obj.get("agent_name") orelse return error.MissingAgentName;

        // Parse timestamp
        const timestamp_str = obj.get("timestamp") orelse return error.MissingTimestamp;
        const timestamp = try parseTimestamp(timestamp_str.string);

        // Parse step_number
        const step_number_val = obj.get("step_number") orelse return error.MissingStepNumber;
        const step_number: usize = @intCast(step_number_val.integer);

        // Parse state (deep copy to avoid dangling pointers after parsed.deinit())
        var state = json.Value{ .object = json.ObjectMap.init(allocator) };
        if (obj.get("state")) |state_val| {
            state = try deepCopyJsonValue(allocator, state_val);
        }

        // Parse messages
        var messages: std.ArrayList(Message) = .{};
        if (obj.get("messages")) |messages_val| {
            for (messages_val.array.items) |msg_val| {
                const msg = try Message.fromJson(allocator, msg_val);
                try messages.append(allocator, msg);
            }
        }

        // Parse metadata (deep copy to avoid dangling pointers after parsed.deinit())
        var metadata = json.Value{ .object = json.ObjectMap.init(allocator) };
        if (obj.get("metadata")) |metadata_val| {
            metadata = try deepCopyJsonValue(allocator, metadata_val);
        }

        // Parse parent_checkpoint_id (optional)
        const parent_checkpoint_id = if (obj.get("parent_checkpoint_id")) |parent_val|
            try allocator.dupe(u8, parent_val.string)
        else
            null;

        return Checkpoint{
            .checkpoint_id = try allocator.dupe(u8, checkpoint_id.string),
            .session_id = try allocator.dupe(u8, session_id.string),
            .agent_name = try allocator.dupe(u8, agent_name.string),
            .timestamp = timestamp,
            .step_number = step_number,
            .state = state,
            .messages = try messages.toOwnedSlice(allocator),
            .metadata = metadata,
            .parent_checkpoint_id = parent_checkpoint_id,
            .allocator = allocator,
        };
    }
};

/// Generate a UUID v4 string.
///
/// Returns:
///   UUID string (caller owns memory)
fn generateUuid(allocator: Allocator) ![]const u8 {
    var uuid: [16]u8 = undefined;
    std.crypto.random.bytes(&uuid);

    // Set version (4) and variant (10)
    uuid[6] = (uuid[6] & 0x0F) | 0x40;
    uuid[8] = (uuid[8] & 0x3F) | 0x80;

    return try std.fmt.allocPrint(allocator, "{x:0>2}{x:0>2}{x:0>2}{x:0>2}-{x:0>2}{x:0>2}-{x:0>2}{x:0>2}-{x:0>2}{x:0>2}-{x:0>2}{x:0>2}{x:0>2}{x:0>2}{x:0>2}{x:0>2}", .{
        uuid[0],  uuid[1],  uuid[2],  uuid[3],
        uuid[4],  uuid[5],  uuid[6],  uuid[7],
        uuid[8],  uuid[9],  uuid[10], uuid[11],
        uuid[12], uuid[13], uuid[14], uuid[15],
    });
}

/// Format timestamp as RFC3339 string.
///
/// Args:
///   allocator: Memory allocator
///   timestamp: Unix timestamp in milliseconds
///
/// Returns:
///   RFC3339 formatted string (caller owns memory)
fn formatTimestamp(allocator: Allocator, timestamp: i64) ![]const u8 {
    const seconds: i64 = @divFloor(timestamp, 1000);
    const nanos: u32 = @intCast(@mod(timestamp, 1000) * 1_000_000);

    const epoch = std.time.epoch.EpochSeconds{ .secs = @intCast(seconds) };
    const day_seconds = epoch.getDaySeconds();
    const year_day = epoch.getEpochDay().calculateYearDay();
    const month_day = year_day.calculateMonthDay();

    return try std.fmt.allocPrint(allocator, "{d:0>4}-{d:0>2}-{d:0>2}T{d:0>2}:{d:0>2}:{d:0>2}.{d:0>3}Z", .{
        year_day.year,
        month_day.month.numeric(),
        month_day.day_index + 1,
        day_seconds.getHoursIntoDay(),
        day_seconds.getMinutesIntoHour(),
        day_seconds.getSecondsIntoMinute(),
        @divFloor(nanos, 1_000_000),
    });
}

/// Parse RFC3339 timestamp string.
///
/// Args:
///   timestamp_str: RFC3339 formatted string
///
/// Returns:
///   Unix timestamp in milliseconds
fn parseTimestamp(timestamp_str: []const u8) !i64 {
    // Simple RFC3339 parser: YYYY-MM-DDTHH:MM:SS.sssZ
    // For production, use a proper ISO8601 parser

    if (timestamp_str.len < 20) return error.InvalidTimestamp;

    const year = try std.fmt.parseInt(i32, timestamp_str[0..4], 10);
    const month = try std.fmt.parseInt(u8, timestamp_str[5..7], 10);
    const day = try std.fmt.parseInt(u8, timestamp_str[8..10], 10);
    const hour = try std.fmt.parseInt(u8, timestamp_str[11..13], 10);
    const minute = try std.fmt.parseInt(u8, timestamp_str[14..16], 10);
    const second = try std.fmt.parseInt(u8, timestamp_str[17..19], 10);

    // Parse milliseconds if present
    var milliseconds: u32 = 0;
    if (timestamp_str.len > 20 and timestamp_str[19] == '.') {
        const ms_end = std.mem.indexOfScalar(u8, timestamp_str[20..], 'Z') orelse (timestamp_str.len - 20);
        if (ms_end > 0) {
            const ms_str = timestamp_str[20 .. 20 + ms_end];
            milliseconds = try std.fmt.parseInt(u32, ms_str, 10);
        }
    }

    // Convert to Unix timestamp
    // This is a simplified calculation - for production use std.time epoch calculations
    const days_since_epoch = daysSinceEpoch(year, month, day);
    const seconds: i64 = @as(i64, days_since_epoch) * 86400 +
                        @as(i64, hour) * 3600 +
                        @as(i64, minute) * 60 +
                        @as(i64, second);

    return seconds * 1000 + @as(i64, milliseconds);
}

/// Calculate days since Unix epoch (1970-01-01).
fn daysSinceEpoch(year: i32, month: u8, day: u8) i32 {
    const y = year - 1970;
    var days: i32 = y * 365;

    // Add leap days
    days += @divFloor(y, 4) - @divFloor(y, 100) + @divFloor(y, 400);

    // Add days for months
    const days_in_month = [_]i32{ 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 };
    for (0..month - 1) |m| {
        days += days_in_month[m];
    }

    // Add leap day for current year if needed
    if (month > 2 and isLeapYear(year)) {
        days += 1;
    }

    // Add day of month
    days += @as(i32, day) - 1;

    return days;
}

/// Check if year is a leap year.
fn isLeapYear(year: i32) bool {
    return (@rem(year, 4) == 0 and @rem(year, 100) != 0) or (@rem(year, 400) == 0);
}

// Tests
test "Checkpoint creation" {
    const allocator = std.testing.allocator;

    var checkpoint = try Checkpoint.init(allocator, "session-1", "assistant", 5);
    defer checkpoint.deinit();

    try std.testing.expectEqualStrings("session-1", checkpoint.session_id);
    try std.testing.expectEqualStrings("assistant", checkpoint.agent_name);
    try std.testing.expectEqual(@as(usize, 5), checkpoint.step_number);
    try std.testing.expect(checkpoint.checkpoint_id.len > 0);
}

test "Checkpoint with state" {
    const allocator = std.testing.allocator;

    var checkpoint = try Checkpoint.init(allocator, "session-1", "assistant", 5);
    defer checkpoint.deinit();

    try checkpoint.setState("counter", json.Value{ .integer = 42 });

    const counter = checkpoint.getState("counter");
    try std.testing.expect(counter != null);
    try std.testing.expectEqual(@as(i64, 42), counter.?.integer);
}

test "Checkpoint with parent" {
    const allocator = std.testing.allocator;

    var checkpoint = try Checkpoint.initWithParent(
        allocator,
        "session-1",
        "assistant",
        10,
        "parent-checkpoint-id",
    );
    defer checkpoint.deinit();

    try std.testing.expect(checkpoint.parent_checkpoint_id != null);
    try std.testing.expectEqualStrings("parent-checkpoint-id", checkpoint.parent_checkpoint_id.?);
}

test "Checkpoint JSON serialization" {
    const allocator = std.testing.allocator;

    var checkpoint = try Checkpoint.init(allocator, "session-1", "assistant", 5);
    defer checkpoint.deinit();

    try checkpoint.setState("counter", json.Value{ .integer = 42 });
    try checkpoint.setMetadata("model", json.Value{ .string = "gpt-4" });

    const json_str = try checkpoint.toJson();
    defer allocator.free(json_str);

    // Verify JSON contains expected fields
    try std.testing.expect(std.mem.indexOf(u8, json_str, "checkpoint_id") != null);
    try std.testing.expect(std.mem.indexOf(u8, json_str, "session-1") != null);
    try std.testing.expect(std.mem.indexOf(u8, json_str, "assistant") != null);
}

test "UUID generation" {
    const allocator = std.testing.allocator;

    const uuid1 = try generateUuid(allocator);
    defer allocator.free(uuid1);

    const uuid2 = try generateUuid(allocator);
    defer allocator.free(uuid2);

    // UUIDs should be 36 characters (32 hex + 4 hyphens)
    try std.testing.expectEqual(@as(usize, 36), uuid1.len);
    try std.testing.expectEqual(@as(usize, 36), uuid2.len);

    // UUIDs should be different
    try std.testing.expect(!std.mem.eql(u8, uuid1, uuid2));
}

test "Timestamp formatting" {
    const allocator = std.testing.allocator;

    // Test known timestamp: 2024-01-01T00:00:00.000Z
    const timestamp: i64 = 1704067200000; // 2024-01-01 00:00:00 UTC
    const formatted = try formatTimestamp(allocator, timestamp);
    defer allocator.free(formatted);

    // Should be RFC3339 format
    try std.testing.expect(std.mem.indexOf(u8, formatted, "2024-01-01T") != null);
    try std.testing.expect(std.mem.endsWith(u8, formatted, "Z"));
}

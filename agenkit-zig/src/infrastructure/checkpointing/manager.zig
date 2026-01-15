/// CheckpointManager manages checkpoints for long-running agents.
///
/// Features:
///   - Create checkpoints at key points
///   - Resume from latest checkpoint
///   - Replay from specific checkpoint
///   - Time-travel debugging
///   - Automatic checkpoint creation (every N steps)
///
/// Example:
///   var manager = CheckpointManager.init(allocator, storage, 10);
///   defer manager.deinit();
///   const checkpoint_id = try manager.createCheckpoint(session_id, agent_name, 5, state, messages, null, null);
///   const latest = try manager.getLatest(session_id);
const std = @import("std");
const Allocator = std.mem.Allocator;
const Checkpoint = @import("checkpoint.zig").Checkpoint;
const CheckpointStorage = @import("storage.zig").CheckpointStorage;
const InMemoryStorage = @import("storage.zig").InMemoryStorage;

pub const CheckpointManager = struct {
    allocator: Allocator,
    storage: CheckpointStorage,
    auto_checkpoint_interval: usize,
    session_steps: std.StringHashMap(usize),
    session_last_checkpoint: std.StringHashMap([]const u8),

    /// Create a new checkpoint manager.
    ///
    /// Args:
    ///   allocator: Memory allocator
    ///   storage: Checkpoint storage backend
    ///   auto_checkpoint_interval: Automatically checkpoint every N steps (0 = manual only)
    ///
    /// Example:
    ///   var in_memory = InMemoryStorage.init(allocator);
    ///   var manager = CheckpointManager.init(allocator, in_memory.storage(), 10);
    pub fn init(allocator: Allocator, storage: CheckpointStorage, auto_checkpoint_interval: usize) CheckpointManager {
        return .{
            .allocator = allocator,
            .storage = storage,
            .auto_checkpoint_interval = auto_checkpoint_interval,
            .session_steps = std.StringHashMap(usize).init(allocator),
            .session_last_checkpoint = std.StringHashMap([]const u8).init(allocator),
        };
    }

    /// Free all resources.
    pub fn deinit(self: *CheckpointManager) void {
        self.session_steps.deinit();

        // Free checkpoint IDs
        var iter = self.session_last_checkpoint.valueIterator();
        while (iter.next()) |checkpoint_id| {
            self.allocator.free(checkpoint_id.*);
        }
        self.session_last_checkpoint.deinit();
    }

    /// Deep copy a JSON value to avoid dangling pointers.
    fn deepCopyJsonValue(self: *CheckpointManager, value: std.json.Value) !std.json.Value {
        return switch (value) {
            .null => .null,
            .bool => |b| .{ .bool = b },
            .integer => |i| .{ .integer = i },
            .float => |f| .{ .float = f },
            .number_string => |ns| .{ .number_string = try self.allocator.dupe(u8, ns) },
            .string => |s| .{ .string = try self.allocator.dupe(u8, s) },
            .array => |arr| {
                var array_copy = std.json.Array.init(self.allocator);
                for (arr.items) |item| {
                    try array_copy.append(try self.deepCopyJsonValue(item));
                }
                return .{ .array = array_copy };
            },
            .object => |obj| {
                var object_copy = std.json.ObjectMap.init(self.allocator);
                var iter = obj.iterator();
                while (iter.next()) |entry| {
                    const key_copy = try self.allocator.dupe(u8, entry.key_ptr.*);
                    const value_copy = try self.deepCopyJsonValue(entry.value_ptr.*);
                    try object_copy.put(key_copy, value_copy);
                }
                return .{ .object = object_copy };
            },
        };
    }

    /// Create a new checkpoint.
    ///
    /// Args:
    ///   session_id: Session identifier
    ///   agent_name: Agent name
    ///   step_number: Sequential step number
    ///   state: Agent state to save
    ///   messages: Conversation messages
    ///   metadata: Optional metadata
    ///   parent_checkpoint_id: ID of previous checkpoint
    ///
    /// Returns:
    ///   checkpoint_id: Unique identifier for this checkpoint
    pub fn createCheckpoint(
        self: *CheckpointManager,
        session_id: []const u8,
        agent_name: []const u8,
        step_number: usize,
        state: std.json.Value,
        messages: []const @import("../../message.zig").Message,
        metadata: ?std.json.Value,
        parent_checkpoint_id: ?[]const u8,
    ) ![]const u8 {
        // Use last checkpoint as parent if not specified
        var parent_id = parent_checkpoint_id;
        if (parent_id == null) {
            if (self.session_last_checkpoint.get(session_id)) |last_id| {
                parent_id = last_id;
            }
        }

        // Create checkpoint
        var checkpoint = if (parent_id) |pid|
            try Checkpoint.initWithParent(self.allocator, session_id, agent_name, step_number, pid)
        else
            try Checkpoint.init(self.allocator, session_id, agent_name, step_number);

        // Set state (make a deep copy)
        var state_iter = state.object.iterator();
        while (state_iter.next()) |entry| {
            const key = entry.key_ptr.*;
            const value = entry.value_ptr.*;
            // Use setState which will dupe the key and take ownership of value
            // But we need to deep copy the value first
            const value_copy = try self.deepCopyJsonValue(value);
            try checkpoint.setState(key, value_copy);
        }

        // Set messages (make a deep copy)
        const Message = @import("../../message.zig").Message;
        const messages_copy = try self.allocator.alloc(Message, messages.len);
        for (messages, 0..) |msg, i| {
            // Deep copy each message to avoid shared memory
            messages_copy[i] = try Message.withText(self.allocator, msg.role, try msg.contentAsText());
        }
        checkpoint.messages = messages_copy;

        // Set metadata (make a deep copy)
        if (metadata) |m| {
            var metadata_iter = m.object.iterator();
            while (metadata_iter.next()) |entry| {
                const key = entry.key_ptr.*;
                const value = entry.value_ptr.*;
                // Use setMetadata which will dupe the key and take ownership of value
                // But we need to deep copy the value first
                const value_copy = try self.deepCopyJsonValue(value);
                try checkpoint.setMetadata(key, value_copy);
            }
        }

        // Save checkpoint
        try self.storage.save(&checkpoint);

        // Update tracking
        const checkpoint_id_copy = try self.allocator.dupe(u8, checkpoint.checkpoint_id);

        // Free old last checkpoint ID if exists
        if (self.session_last_checkpoint.get(session_id)) |old_id| {
            self.allocator.free(old_id);
        }

        try self.session_last_checkpoint.put(session_id, checkpoint_id_copy);
        try self.session_steps.put(session_id, step_number);

        std.log.info("Created checkpoint {s} for {s} at step {d}", .{ checkpoint.checkpoint_id, session_id, step_number });

        // Return owned copy of checkpoint ID
        const result = try self.allocator.dupe(u8, checkpoint.checkpoint_id);
        checkpoint.deinit();
        return result;
    }

    /// Determine if checkpoint should be created (for auto-checkpointing).
    ///
    /// Args:
    ///   session_id: Session identifier
    ///   step_number: Current step number
    ///
    /// Returns:
    ///   true if checkpoint should be created
    pub fn shouldCheckpoint(self: *CheckpointManager, session_id: []const u8, step_number: usize) bool {
        if (self.auto_checkpoint_interval == 0) {
            return false;
        }

        const last_step = self.session_steps.get(session_id) orelse 0;

        // Handle case where step_number might be less than last_step after session reset
        if (step_number < last_step) {
            return false;
        }

        const steps_since_checkpoint = step_number - last_step;

        return steps_since_checkpoint >= self.auto_checkpoint_interval;
    }

    /// Get latest checkpoint for session.
    ///
    /// Args:
    ///   session_id: Session identifier
    ///
    /// Returns:
    ///   Latest checkpoint or null
    pub fn getLatest(self: *CheckpointManager, session_id: []const u8) !?*Checkpoint {
        return try self.storage.getLatest(session_id);
    }

    /// Load specific checkpoint.
    ///
    /// Args:
    ///   checkpoint_id: Checkpoint identifier
    ///
    /// Returns:
    ///   Checkpoint or null if not found
    pub fn loadCheckpoint(self: *CheckpointManager, checkpoint_id: []const u8) !?*Checkpoint {
        return try self.storage.load(checkpoint_id);
    }

    /// List all checkpoints for session.
    ///
    /// Args:
    ///   session_id: Session identifier
    ///   limit: Optional limit on number of checkpoints (0 = no limit)
    ///
    /// Returns:
    ///   List of checkpoints (most recent first)
    pub fn listCheckpoints(self: *CheckpointManager, session_id: []const u8, limit: usize) ![]const *Checkpoint {
        return try self.storage.listCheckpoints(session_id, limit);
    }

    /// Restore agent state from checkpoint.
    ///
    /// Args:
    ///   checkpoint: Checkpoint to restore from
    ///
    /// Returns:
    ///   Restored state (caller owns memory)
    pub fn restoreState(_: *CheckpointManager, checkpoint: *const Checkpoint) !std.json.Value {
        std.log.info("Restoring state from checkpoint {s} (step {d})", .{
            checkpoint.checkpoint_id,
            checkpoint.step_number,
        });

        // Return a reference to the state (caller should not modify it)
        return checkpoint.state;
    }

    /// Get checkpoint history by following parent links.
    ///
    /// Args:
    ///   checkpoint_id: Starting checkpoint
    ///   max_depth: Maximum number of parents to follow
    ///
    /// Returns:
    ///   List of checkpoints from most recent to oldest
    pub fn getCheckpointHistory(self: *CheckpointManager, checkpoint_id: []const u8, max_depth: usize) ![]const *Checkpoint {
        return try self.storage.getCheckpointHistory(checkpoint_id, max_depth);
    }

    /// Delete specific checkpoint.
    ///
    /// Args:
    ///   checkpoint_id: Checkpoint identifier
    ///
    /// Returns:
    ///   true if deleted, false if not found
    pub fn deleteCheckpoint(self: *CheckpointManager, checkpoint_id: []const u8) !bool {
        return try self.storage.delete(checkpoint_id);
    }

    /// Delete all checkpoints for session.
    ///
    /// Args:
    ///   session_id: Session identifier
    ///
    /// Returns:
    ///   Number of checkpoints deleted
    pub fn deleteSession(self: *CheckpointManager, session_id: []const u8) !usize {
        const count = try self.storage.deleteSession(session_id);

        // Clean up tracking
        _ = self.session_steps.remove(session_id);
        if (self.session_last_checkpoint.get(session_id)) |checkpoint_id| {
            self.allocator.free(checkpoint_id);
            _ = self.session_last_checkpoint.remove(session_id);
        }

        return count;
    }

    /// Get statistics for session checkpoints.
    ///
    /// Args:
    ///   session_id: Session identifier
    ///
    /// Returns:
    ///   Map with statistics (caller owns memory)
    pub fn getSessionStats(self: *CheckpointManager, session_id: []const u8) !std.json.Value {
        const checkpoints = try self.listCheckpoints(session_id, 0);
        defer {
            for (checkpoints) |cp| {
                cp.deinit();
                self.allocator.destroy(cp);
            }
            self.allocator.free(checkpoints);
        }

        if (checkpoints.len == 0) {
            var obj = std.json.ObjectMap.init(self.allocator);
            try obj.put("total_checkpoints", .{ .integer = 0 });
            try obj.put("first_checkpoint", .null);
            try obj.put("latest_checkpoint", .null);
            try obj.put("steps_covered", .{ .integer = 0 });
            return std.json.Value{ .object = obj };
        }

        const first_checkpoint = checkpoints[checkpoints.len - 1];
        const latest_checkpoint = checkpoints[0];

        var obj = std.json.ObjectMap.init(self.allocator);
        try obj.put("total_checkpoints", .{ .integer = @intCast(checkpoints.len) });
        try obj.put("first_checkpoint", .{ .string = first_checkpoint.checkpoint_id });
        try obj.put("latest_checkpoint", .{ .string = latest_checkpoint.checkpoint_id });
        try obj.put("first_step", .{ .integer = @intCast(first_checkpoint.step_number) });
        try obj.put("latest_step", .{ .integer = @intCast(latest_checkpoint.step_number) });

        // Calculate steps_covered safely (handle case where order might be reversed)
        const steps_covered = if (latest_checkpoint.step_number >= first_checkpoint.step_number)
            latest_checkpoint.step_number - first_checkpoint.step_number
        else
            0;
        try obj.put("steps_covered", .{ .integer = @intCast(steps_covered) });

        const time_span = @as(f64, @floatFromInt(latest_checkpoint.timestamp - first_checkpoint.timestamp)) / 1000.0;
        try obj.put("time_span_seconds", .{ .float = time_span });

        return std.json.Value{ .object = obj };
    }

    /// Prune old checkpoints, keeping only the most recent N.
    ///
    /// Args:
    ///   session_id: Session identifier
    ///   keep_last: Number of most recent checkpoints to keep
    ///
    /// Returns:
    ///   Number of checkpoints deleted
    pub fn pruneOldCheckpoints(self: *CheckpointManager, session_id: []const u8, keep_last: usize) !usize {
        const checkpoints = try self.listCheckpoints(session_id, 0);
        defer {
            for (checkpoints) |cp| {
                cp.deinit();
                self.allocator.destroy(cp);
            }
            self.allocator.free(checkpoints);
        }

        if (checkpoints.len <= keep_last) {
            return 0;
        }

        // Delete old checkpoints
        const to_delete = checkpoints[keep_last..];
        var deleted_count: usize = 0;

        for (to_delete) |checkpoint| {
            const deleted = try self.storage.delete(checkpoint.checkpoint_id);
            if (deleted) {
                deleted_count += 1;
            }
        }

        std.log.info("Pruned {d} old checkpoints for {s}, kept {d} most recent", .{
            deleted_count,
            session_id,
            keep_last,
        });

        return deleted_count;
    }
};

// Tests
test "CheckpointManager creation" {
    const allocator = std.testing.allocator;

    var in_memory = InMemoryStorage.init(allocator);
    defer in_memory.deinit();

    var manager = CheckpointManager.init(allocator, in_memory.storage(), 10);
    defer manager.deinit();

    try std.testing.expect(manager.auto_checkpoint_interval == 10);
}

test "CheckpointManager shouldCheckpoint" {
    const allocator = std.testing.allocator;

    var in_memory = InMemoryStorage.init(allocator);
    defer in_memory.deinit();

    var manager = CheckpointManager.init(allocator, in_memory.storage(), 5);
    defer manager.deinit();

    // First checkpoint should not be automatic
    try std.testing.expect(!manager.shouldCheckpoint("session-1", 1));

    // After 5 steps, should checkpoint
    try std.testing.expect(manager.shouldCheckpoint("session-1", 5));

    // After manually setting step, should not checkpoint immediately
    try manager.session_steps.put("session-1", 5);
    try std.testing.expect(!manager.shouldCheckpoint("session-1", 6));

    // After 5 more steps, should checkpoint again
    try std.testing.expect(manager.shouldCheckpoint("session-1", 10));
}

test "CheckpointManager createCheckpoint and getLatest" {
    const allocator = std.testing.allocator;
    const Message = @import("../../message.zig").Message;

    var in_memory = InMemoryStorage.init(allocator);
    defer in_memory.deinit();

    var manager = CheckpointManager.init(allocator, in_memory.storage(), 0);
    defer manager.deinit();

    // Create empty state
    var state = std.json.Value{ .object = std.json.ObjectMap.init(allocator) };
    defer state.object.deinit();

    const messages = try allocator.alloc(Message, 0);
    defer allocator.free(messages);

    // Create checkpoint
    const checkpoint_id = try manager.createCheckpoint(
        "session-1",
        "assistant",
        5,
        state,
        messages,
        null,
        null,
    );
    defer allocator.free(checkpoint_id);

    // Get latest
    const latest = try manager.getLatest("session-1");
    try std.testing.expect(latest != null);
    defer {
        if (latest) |cp| {
            cp.deinit();
            allocator.destroy(cp);
        }
    }

    try std.testing.expectEqualStrings("session-1", latest.?.session_id);
    try std.testing.expectEqualStrings("assistant", latest.?.agent_name);
    try std.testing.expectEqual(@as(usize, 5), latest.?.step_number);
}

test "CheckpointManager deleteSession" {
    const allocator = std.testing.allocator;
    const Message = @import("../../message.zig").Message;

    var in_memory = InMemoryStorage.init(allocator);
    defer in_memory.deinit();

    var manager = CheckpointManager.init(allocator, in_memory.storage(), 0);
    defer manager.deinit();

    // Create empty state
    var state = std.json.Value{ .object = std.json.ObjectMap.init(allocator) };
    defer state.object.deinit();

    const messages = try allocator.alloc(Message, 0);
    defer allocator.free(messages);

    // Create checkpoint
    const checkpoint_id = try manager.createCheckpoint(
        "session-1",
        "assistant",
        5,
        state,
        messages,
        null,
        null,
    );
    defer allocator.free(checkpoint_id);

    // Delete session
    const count = try manager.deleteSession("session-1");
    try std.testing.expectEqual(@as(usize, 1), count);

    // Verify deleted
    const latest = try manager.getLatest("session-1");
    try std.testing.expect(latest == null);
}

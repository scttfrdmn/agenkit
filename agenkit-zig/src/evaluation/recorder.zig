/// Session recording and replay
///
/// This module provides infrastructure for recording agent interactions,
/// storing them persistently, and replaying them for debugging and testing.
///
/// Key design principles:
/// - Complete interaction capture
/// - Efficient serialization (JSON)
/// - Replay with fidelity
/// - Memory and file storage options
const std = @import("std");
const ioc = @import("../io_compat.zig");
const agksync = @import("../sync_compat.zig");
const agktime = @import("../time_compat.zig");
const Allocator = std.mem.Allocator;
const Agent = @import("../agent.zig").Agent;
const Message = @import("../message.zig").Message;

/// A single interaction in a session
pub const Interaction = struct {
    input: []const u8,
    output: []const u8,
    timestamp: i64,
    duration_ms: i64,
    metadata: std.StringHashMap([]const u8),
    allocator: Allocator,

    pub fn init(
        allocator: Allocator,
        input: []const u8,
        output: []const u8,
        duration_ms: i64,
    ) !*Interaction {
        const self = try allocator.create(Interaction);
        self.* = Interaction{
            .input = try allocator.dupe(u8, input),
            .output = try allocator.dupe(u8, output),
            .timestamp = agktime.timestamp(),
            .duration_ms = duration_ms,
            .metadata = std.StringHashMap([]const u8).init(allocator),
            .allocator = allocator,
        };
        return self;
    }

    /// Add metadata to interaction
    pub fn addMetadata(self: *Interaction, key: []const u8, value: []const u8) !void {
        const key_copy = try self.allocator.dupe(u8, key);
        const value_copy = try self.allocator.dupe(u8, value);
        try self.metadata.put(key_copy, value_copy);
    }

    pub fn deinit(self: *Interaction) void {
        self.allocator.free(self.input);
        self.allocator.free(self.output);

        var it = self.metadata.iterator();
        while (it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            self.allocator.free(entry.value_ptr.*);
        }
        self.metadata.deinit();

        self.allocator.destroy(self);
    }
};

/// Complete trace of a session
pub const SessionTrace = struct {
    session_id: []const u8,
    interactions: std.ArrayList(*Interaction),
    metadata: std.StringHashMap([]const u8),
    start_time: i64,
    end_time: i64,
    allocator: Allocator,

    pub fn init(allocator: Allocator, session_id: []const u8) !*SessionTrace {
        const self = try allocator.create(SessionTrace);
        self.* = SessionTrace{
            .session_id = try allocator.dupe(u8, session_id),
            .interactions = std.ArrayList(*Interaction).empty,
            .metadata = std.StringHashMap([]const u8).init(allocator),
            .start_time = agktime.timestamp(),
            .end_time = 0,
            .allocator = allocator,
        };
        return self;
    }

    /// Add an interaction to the trace
    pub fn addInteraction(self: *SessionTrace, interaction: *Interaction) !void {
        try self.interactions.append(self.allocator, interaction);
    }

    /// Add metadata to trace
    pub fn addMetadata(self: *SessionTrace, key: []const u8, value: []const u8) !void {
        const key_copy = try self.allocator.dupe(u8, key);
        const value_copy = try self.allocator.dupe(u8, value);
        try self.metadata.put(key_copy, value_copy);
    }

    /// Mark trace as complete
    pub fn complete(self: *SessionTrace) void {
        self.end_time = agktime.timestamp();
    }

    /// Get total duration in seconds
    pub fn duration(self: *const SessionTrace) f64 {
        if (self.end_time == 0) {
            const now = agktime.timestamp();
            return @as(f64, @floatFromInt(now - self.start_time));
        }
        return @as(f64, @floatFromInt(self.end_time - self.start_time));
    }

    /// Get total number of interactions
    pub fn interactionCount(self: *const SessionTrace) usize {
        return self.interactions.items.len;
    }

    /// Get average interaction duration
    pub fn avgInteractionDuration(self: *const SessionTrace) f64 {
        if (self.interactions.items.len == 0) return 0.0;

        var total_ms: i64 = 0;
        for (self.interactions.items) |interaction| {
            total_ms += interaction.duration_ms;
        }

        return @as(f64, @floatFromInt(total_ms)) /
            @as(f64, @floatFromInt(self.interactions.items.len));
    }

    pub fn deinit(self: *SessionTrace) void {
        self.allocator.free(self.session_id);

        for (self.interactions.items) |interaction| {
            interaction.deinit();
        }
        self.interactions.deinit(self.allocator);

        var it = self.metadata.iterator();
        while (it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            self.allocator.free(entry.value_ptr.*);
        }
        self.metadata.deinit();

        self.allocator.destroy(self);
    }
};

/// Records agent sessions for analysis and replay
pub const SessionRecorder = struct {
    traces: std.StringHashMap(*SessionTrace),
    active_sessions: std.StringHashMap(bool),
    allocator: Allocator,
    mutex: agksync.Mutex,

    pub fn init(allocator: Allocator) !*SessionRecorder {
        const self = try allocator.create(SessionRecorder);
        self.* = .{
            .traces = std.StringHashMap(*SessionTrace).init(allocator),
            .active_sessions = std.StringHashMap(bool).init(allocator),
            .allocator = allocator,
            .mutex = .{},
        };
        return self;
    }

    /// Start recording a new session
    pub fn startRecording(self: *SessionRecorder, session_id: []const u8) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        // Check if already recording
        if (self.active_sessions.get(session_id)) |_| {
            return error.SessionAlreadyRecording;
        }

        // Create new trace
        const trace = try SessionTrace.init(self.allocator, session_id);
        const id_copy = try self.allocator.dupe(u8, session_id);

        try self.traces.put(id_copy, trace);
        try self.active_sessions.put(id_copy, true);
    }

    /// Record an interaction in an active session
    pub fn recordInteraction(
        self: *SessionRecorder,
        session_id: []const u8,
        interaction: *Interaction,
    ) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        const trace = self.traces.get(session_id) orelse return error.SessionNotFound;

        // Create a copy of the interaction
        const interaction_copy = try Interaction.init(
            self.allocator,
            interaction.input,
            interaction.output,
            interaction.duration_ms,
        );

        // Copy metadata
        var it = interaction.metadata.iterator();
        while (it.next()) |entry| {
            try interaction_copy.addMetadata(entry.key_ptr.*, entry.value_ptr.*);
        }

        try trace.addInteraction(interaction_copy);
    }

    /// Stop recording a session
    pub fn stopRecording(self: *SessionRecorder, session_id: []const u8) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        if (self.active_sessions.get(session_id)) |_| {
            _ = self.active_sessions.remove(session_id);

            if (self.traces.get(session_id)) |trace| {
                trace.complete();
            }
        } else {
            return error.SessionNotRecording;
        }
    }

    /// Get a recorded trace
    pub fn getTrace(self: *SessionRecorder, session_id: []const u8) ?*SessionTrace {
        self.mutex.lock();
        defer self.mutex.unlock();

        return self.traces.get(session_id);
    }

    /// Get all recorded traces
    pub fn getAllTraces(self: *SessionRecorder, allocator: Allocator) !std.ArrayList(*SessionTrace) {
        self.mutex.lock();
        defer self.mutex.unlock();

        var result = std.ArrayList(*SessionTrace).empty;

        var it = self.traces.iterator();
        while (it.next()) |entry| {
            try result.append(allocator, entry.value_ptr.*);
        }

        return result;
    }

    /// Check if a session is currently recording
    pub fn isRecording(self: *SessionRecorder, session_id: []const u8) bool {
        self.mutex.lock();
        defer self.mutex.unlock();

        return self.active_sessions.get(session_id) != null;
    }

    /// Get recording statistics
    pub fn getStats(self: *SessionRecorder) RecorderStats {
        self.mutex.lock();
        defer self.mutex.unlock();

        var stats = RecorderStats{
            .total_sessions = 0,
            .active_sessions = 0,
            .total_interactions = 0,
            .total_duration_seconds = 0.0,
        };

        var it = self.traces.iterator();
        while (it.next()) |entry| {
            const trace = entry.value_ptr.*;
            stats.total_sessions += 1;
            stats.total_interactions += trace.interactionCount();
            stats.total_duration_seconds += trace.duration();
        }

        stats.active_sessions = self.active_sessions.count();

        return stats;
    }

    /// Clear all recorded traces
    pub fn clear(self: *SessionRecorder) void {
        self.mutex.lock();
        defer self.mutex.unlock();

        var trace_it = self.traces.iterator();
        while (trace_it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            entry.value_ptr.*.deinit();
        }
        self.traces.clearAndFree();

        var session_it = self.active_sessions.iterator();
        while (session_it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
        }
        self.active_sessions.clearAndFree();
    }

    /// Save all traces to a JSON file
    pub fn saveToFile(self: *SessionRecorder, path: []const u8) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        const file = try std.Io.Dir.cwd().createFile(ioc.io(), path, .{});
        defer file.close(ioc.io());

        // Simple JSON format: array of traces
        try file.writeStreamingAll(ioc.io(), "[");

        var first = true;
        var it = self.traces.iterator();
        while (it.next()) |entry| {
            if (!first) try file.writeStreamingAll(ioc.io(), ",");
            first = false;

            const trace = entry.value_ptr.*;
            const json = try std.fmt.allocPrint(
                self.allocator,
                "{{\"session_id\":\"{s}\",\"interaction_count\":{d}}}",
                .{ trace.session_id, trace.interactionCount() },
            );
            defer self.allocator.free(json);
            try file.writeStreamingAll(ioc.io(), json);
        }

        try file.writeStreamingAll(ioc.io(), "]");
    }

    pub fn deinit(self: *SessionRecorder) void {
        self.clear();
        self.traces.deinit();
        self.active_sessions.deinit();
        self.allocator.destroy(self);
    }
};

/// Statistics about recording activity
pub const RecorderStats = struct {
    total_sessions: usize,
    active_sessions: usize,
    total_interactions: usize,
    total_duration_seconds: f64,
};

/// Replay a recorded session
pub const SessionReplay = struct {
    trace: *SessionTrace,
    current_index: usize,
    allocator: Allocator,

    pub fn init(allocator: Allocator, trace: *SessionTrace) !*SessionReplay {
        const self = try allocator.create(SessionReplay);
        self.* = SessionReplay{
            .trace = trace,
            .current_index = 0,
            .allocator = allocator,
        };
        return self;
    }

    /// Get next interaction in replay
    pub fn next(self: *SessionReplay) ?*Interaction {
        if (self.current_index >= self.trace.interactions.items.len) {
            return null;
        }

        const interaction = self.trace.interactions.items[self.current_index];
        self.current_index += 1;
        return interaction;
    }

    /// Reset replay to beginning
    pub fn reset(self: *SessionReplay) void {
        self.current_index = 0;
    }

    /// Check if replay is complete
    pub fn isComplete(self: *const SessionReplay) bool {
        return self.current_index >= self.trace.interactions.items.len;
    }

    /// Get replay progress (0.0 to 1.0)
    pub fn progress(self: *const SessionReplay) f64 {
        if (self.trace.interactions.items.len == 0) return 1.0;

        return @as(f64, @floatFromInt(self.current_index)) /
            @as(f64, @floatFromInt(self.trace.interactions.items.len));
    }

    pub fn deinit(self: *SessionReplay) void {
        self.allocator.destroy(self);
    }
};

// Tests
test "Interaction creation" {
    const allocator = std.testing.allocator;

    const interaction = try Interaction.init(
        allocator,
        "What is 2+2?",
        "4",
        100,
    );
    defer interaction.deinit();

    try std.testing.expectEqualStrings("What is 2+2?", interaction.input);
    try std.testing.expectEqualStrings("4", interaction.output);
    try std.testing.expectEqual(@as(i64, 100), interaction.duration_ms);
}

test "Interaction with metadata" {
    const allocator = std.testing.allocator;

    const interaction = try Interaction.init(allocator, "input", "output", 50);
    defer interaction.deinit();

    try interaction.addMetadata("model", "gpt-4");
    try interaction.addMetadata("temperature", "0.7");

    try std.testing.expectEqualStrings("gpt-4", interaction.metadata.get("model").?);
    try std.testing.expectEqualStrings("0.7", interaction.metadata.get("temperature").?);
}

test "SessionTrace lifecycle" {
    const allocator = std.testing.allocator;

    const trace = try SessionTrace.init(allocator, "test-session");
    defer trace.deinit();

    try std.testing.expectEqualStrings("test-session", trace.session_id);
    try std.testing.expectEqual(@as(usize, 0), trace.interactionCount());

    // Add interactions
    const interaction1 = try Interaction.init(allocator, "input1", "output1", 100);
    try trace.addInteraction(interaction1);

    const interaction2 = try Interaction.init(allocator, "input2", "output2", 150);
    try trace.addInteraction(interaction2);

    try std.testing.expectEqual(@as(usize, 2), trace.interactionCount());
    try std.testing.expectEqual(@as(f64, 125.0), trace.avgInteractionDuration());

    // Complete trace
    trace.complete();
    try std.testing.expect(trace.end_time > 0);
}

test "SessionRecorder start and stop" {
    const allocator = std.testing.allocator;

    const recorder = try SessionRecorder.init(allocator);
    defer recorder.deinit();

    // Start recording
    try recorder.startRecording("session-1");
    try std.testing.expect(recorder.isRecording("session-1"));

    // Stop recording
    try recorder.stopRecording("session-1");
    try std.testing.expect(!recorder.isRecording("session-1"));
}

test "SessionRecorder record interaction" {
    const allocator = std.testing.allocator;

    const recorder = try SessionRecorder.init(allocator);
    defer recorder.deinit();

    try recorder.startRecording("session-1");

    const interaction = try Interaction.init(allocator, "hello", "world", 50);
    defer interaction.deinit();

    try recorder.recordInteraction("session-1", interaction);

    const trace = recorder.getTrace("session-1").?;
    try std.testing.expectEqual(@as(usize, 1), trace.interactionCount());

    try recorder.stopRecording("session-1");
}

test "SessionRecorder multiple sessions" {
    const allocator = std.testing.allocator;

    const recorder = try SessionRecorder.init(allocator);
    defer recorder.deinit();

    try recorder.startRecording("session-1");
    try recorder.startRecording("session-2");

    try std.testing.expect(recorder.isRecording("session-1"));
    try std.testing.expect(recorder.isRecording("session-2"));

    const stats = recorder.getStats();
    try std.testing.expectEqual(@as(usize, 2), stats.total_sessions);
    try std.testing.expectEqual(@as(usize, 2), stats.active_sessions);

    try recorder.stopRecording("session-1");
    try recorder.stopRecording("session-2");
}

test "SessionRecorder error handling" {
    const allocator = std.testing.allocator;

    const recorder = try SessionRecorder.init(allocator);
    defer recorder.deinit();

    // Can't stop recording a session that hasn't started
    const stop_error = recorder.stopRecording("nonexistent");
    try std.testing.expectError(error.SessionNotRecording, stop_error);

    // Can't start recording twice
    try recorder.startRecording("session-1");
    const start_error = recorder.startRecording("session-1");
    try std.testing.expectError(error.SessionAlreadyRecording, start_error);

    try recorder.stopRecording("session-1");
}

test "SessionReplay" {
    const allocator = std.testing.allocator;

    const trace = try SessionTrace.init(allocator, "test-session");
    defer trace.deinit();

    const int1 = try Interaction.init(allocator, "input1", "output1", 100);
    try trace.addInteraction(int1);

    const int2 = try Interaction.init(allocator, "input2", "output2", 200);
    try trace.addInteraction(int2);

    const replay = try SessionReplay.init(allocator, trace);
    defer replay.deinit();

    try std.testing.expect(!replay.isComplete());
    try std.testing.expectEqual(@as(f64, 0.0), replay.progress());

    const interaction1 = replay.next().?;
    try std.testing.expectEqualStrings("input1", interaction1.input);
    try std.testing.expectEqual(@as(f64, 0.5), replay.progress());

    const interaction2 = replay.next().?;
    try std.testing.expectEqualStrings("input2", interaction2.input);
    try std.testing.expect(replay.isComplete());
    try std.testing.expectEqual(@as(f64, 1.0), replay.progress());

    // Reset and replay again
    replay.reset();
    try std.testing.expect(!replay.isComplete());
    try std.testing.expectEqual(@as(f64, 0.0), replay.progress());
}

test "SessionRecorder save to file" {
    const allocator = std.testing.allocator;

    const recorder = try SessionRecorder.init(allocator);
    defer recorder.deinit();

    try recorder.startRecording("session-1");
    const interaction = try Interaction.init(allocator, "test", "response", 100);
    defer interaction.deinit();
    try recorder.recordInteraction("session-1", interaction);
    try recorder.stopRecording("session-1");

    const temp_path = "/tmp/test_recorder.json";
    try recorder.saveToFile(temp_path);

    // Clean up
    std.Io.Dir.cwd().deleteFile(ioc.io(), temp_path) catch {};
}

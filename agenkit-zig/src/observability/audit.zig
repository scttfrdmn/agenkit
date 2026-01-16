/// Audit module for Agenkit Zig observability
///
/// This module provides compliance-ready audit logging with:
/// - Event types for different audit events
/// - Buffered async logging for performance
/// - Query API for filtering and retrieving audit events
/// - JSON Lines file format for persistence
///
/// ## Example
///
/// ```zig
/// const audit = @import("audit.zig");
/// const std = @import("std");
///
/// // Create audit logger
/// var logger = try audit.AuditLogger.init(allocator, "audit.log");
/// defer logger.deinit();
///
/// // Log events
/// var event = try audit.AuditEvent.create(
///     allocator,
///     .message_processed,
///     "echo_agent",
///     "session_123"
/// );
/// defer event.deinit(allocator);
///
/// try logger.log(&event);
/// try logger.flush();
/// ```

const std = @import("std");
const Allocator = std.mem.Allocator;

/// Audit event types
pub const AuditEventType = enum {
    agent_created,
    agent_destroyed,
    message_processed,
    message_failed,
    security_violation,
    configuration_changed,
    checkpoint_created,
    checkpoint_restored,

    pub fn toString(self: AuditEventType) []const u8 {
        return switch (self) {
            .agent_created => "agent_created",
            .agent_destroyed => "agent_destroyed",
            .message_processed => "message_processed",
            .message_failed => "message_failed",
            .security_violation => "security_violation",
            .configuration_changed => "configuration_changed",
            .checkpoint_created => "checkpoint_created",
            .checkpoint_restored => "checkpoint_restored",
        };
    }
};

/// Severity levels for audit events
pub const Severity = enum {
    info,
    warning,
    error_level,
    critical,

    pub fn toString(self: Severity) []const u8 {
        return switch (self) {
            .info => "INFO",
            .warning => "WARNING",
            .error_level => "ERROR",
            .critical => "CRITICAL",
        };
    }
};

/// Audit event structure
pub const AuditEvent = struct {
    event_id: []const u8,
    timestamp: i64,
    event_type: AuditEventType,
    agent_name: []const u8,
    session_id: ?[]const u8,
    severity: Severity,
    details: std.StringHashMap([]const u8),

    pub fn create(
        allocator: Allocator,
        event_type: AuditEventType,
        agent_name: []const u8,
        session_id: ?[]const u8,
    ) !AuditEvent {
        // Generate event ID (simplified UUID)
        var event_id_buf: [36]u8 = undefined;
        const timestamp = std.time.milliTimestamp();
        _ = try std.fmt.bufPrint(&event_id_buf, "{x:0>16}-{x:0>4}-{x:0>4}", .{
            @as(u64, @intCast(timestamp)),
            @as(u16, @truncate(@as(u64, @intCast(timestamp)) >> 16)),
            @as(u16, @truncate(@as(u64, @intCast(timestamp)) >> 32)),
        });

        return AuditEvent{
            .event_id = try allocator.dupe(u8, &event_id_buf),
            .timestamp = timestamp,
            .event_type = event_type,
            .agent_name = try allocator.dupe(u8, agent_name),
            .session_id = if (session_id) |sid| try allocator.dupe(u8, sid) else null,
            .severity = .info,
            .details = std.StringHashMap([]const u8).init(allocator),
        };
    }

    pub fn deinit(self: *AuditEvent, allocator: Allocator) void {
        allocator.free(self.event_id);
        allocator.free(self.agent_name);
        if (self.session_id) |sid| allocator.free(sid);

        var iter = self.details.iterator();
        while (iter.next()) |entry| {
            allocator.free(entry.key_ptr.*);
            allocator.free(entry.value_ptr.*);
        }
        self.details.deinit();
    }

    pub fn withSeverity(self: *AuditEvent, severity: Severity) *AuditEvent {
        self.severity = severity;
        return self;
    }

    pub fn withDetail(self: *AuditEvent, allocator: Allocator, key: []const u8, value: []const u8) !void {
        const key_copy = try allocator.dupe(u8, key);
        const value_copy = try allocator.dupe(u8, value);
        try self.details.put(key_copy, value_copy);
    }

    pub fn toJson(self: *const AuditEvent, allocator: Allocator) ![]const u8 {
        var buf = std.ArrayList(u8){};
        errdefer buf.deinit(allocator);

        try buf.appendSlice(allocator, "{\"event_id\":\"");
        try buf.appendSlice(allocator, self.event_id);
        try buf.appendSlice(allocator, "\",\"timestamp\":");
        try std.fmt.format(buf.writer(allocator), "{d}", .{self.timestamp});
        try buf.appendSlice(allocator, ",\"event_type\":\"");
        try buf.appendSlice(allocator, self.event_type.toString());
        try buf.appendSlice(allocator, "\",\"agent_name\":\"");
        try buf.appendSlice(allocator, self.agent_name);
        try buf.appendSlice(allocator, "\",\"severity\":\"");
        try buf.appendSlice(allocator, self.severity.toString());
        try buf.appendSlice(allocator, "\"");

        if (self.session_id) |sid| {
            try buf.appendSlice(allocator, ",\"session_id\":\"");
            try buf.appendSlice(allocator, sid);
            try buf.appendSlice(allocator, "\"");
        }

        if (self.details.count() > 0) {
            try buf.appendSlice(allocator, ",\"details\":{");
            var first = true;
            var iter = self.details.iterator();
            while (iter.next()) |entry| {
                if (!first) try buf.appendSlice(allocator, ",");
                first = false;
                try buf.appendSlice(allocator, "\"");
                try buf.appendSlice(allocator, entry.key_ptr.*);
                try buf.appendSlice(allocator, "\":\"");
                try buf.appendSlice(allocator, entry.value_ptr.*);
                try buf.appendSlice(allocator, "\"");
            }
            try buf.appendSlice(allocator, "}");
        }

        try buf.appendSlice(allocator, "}");

        return buf.toOwnedSlice(allocator);
    }
};

/// Audit logger with buffered I/O
pub const AuditLogger = struct {
    allocator: Allocator,
    log_path: []const u8,
    buffer: std.ArrayList(AuditEvent),
    buffer_size: usize,
    file: ?std.fs.File,

    pub fn init(allocator: Allocator, log_path: []const u8) !AuditLogger {
        return AuditLogger{
            .allocator = allocator,
            .log_path = try allocator.dupe(u8, log_path),
            .buffer = std.ArrayList(AuditEvent){},
            .buffer_size = 100,
            .file = null,
        };
    }

    pub fn deinit(self: *AuditLogger) void {
        self.flush() catch {};
        if (self.file) |f| f.close();
        for (self.buffer.items) |*event| {
            event.deinit(self.allocator);
        }
        self.buffer.deinit(self.allocator);
        self.allocator.free(self.log_path);
    }

    pub fn log(self: *AuditLogger, event: *const AuditEvent) !void {
        // Create a copy of the event
        var event_copy = try AuditEvent.create(
            self.allocator,
            event.event_type,
            event.agent_name,
            event.session_id,
        );
        event_copy.timestamp = event.timestamp;
        event_copy.severity = event.severity;

        // Copy details
        var iter = event.details.iterator();
        while (iter.next()) |entry| {
            try event_copy.withDetail(self.allocator, entry.key_ptr.*, entry.value_ptr.*);
        }

        try self.buffer.append(self.allocator, event_copy);

        // Auto-flush if buffer is full
        if (self.buffer.items.len >= self.buffer_size) {
            try self.flush();
        }
    }

    pub fn flush(self: *AuditLogger) !void {
        if (self.buffer.items.len == 0) return;

        // Open file if not already open
        if (self.file == null) {
            const file = try std.fs.cwd().createFile(self.log_path, .{
                .read = false,
                .truncate = false,
            });
            try file.seekFromEnd(0); // Append to end
            self.file = file;
        }

        const file = self.file.?;

        // Write all buffered events as JSON Lines
        for (self.buffer.items) |*event| {
            const json = try event.toJson(self.allocator);
            defer self.allocator.free(json);

            try file.writeAll(json);
            try file.writeAll("\n");

            event.deinit(self.allocator);
        }

        self.buffer.clearRetainingCapacity();
    }

    pub fn query(self: *AuditLogger, allocator: Allocator, session_id: ?[]const u8) !std.ArrayList(AuditEvent) {
        var results = std.ArrayList(AuditEvent){};
        errdefer {
            for (results.items) |*event| {
                event.deinit(allocator);
            }
            results.deinit(allocator);
        }

        // First flush any buffered events
        try self.flush();

        // Read file and parse JSON Lines
        // TODO: Implement proper JSON parsing and line-by-line reading
        // For now, this is a stub that returns empty results
        _ = session_id;

        return results;
    }

    pub fn countEvents(self: *const AuditLogger) usize {
        return self.buffer.items.len;
    }

    pub fn queryByType(self: *AuditLogger, event_type: AuditEventType) !std.ArrayList(*const AuditEvent) {
        var results = std.ArrayList(*const AuditEvent){};
        errdefer results.deinit(self.allocator);

        for (self.buffer.items) |*event| {
            if (event.event_type == event_type) {
                try results.append(self.allocator, event);
            }
        }

        return results;
    }

    pub fn queryBySeverity(self: *AuditLogger, severity: Severity) !std.ArrayList(*const AuditEvent) {
        var results = std.ArrayList(*const AuditEvent){};
        errdefer results.deinit(self.allocator);

        for (self.buffer.items) |*event| {
            if (event.severity == severity) {
                try results.append(self.allocator, event);
            }
        }

        return results;
    }

    pub fn clear(self: *AuditLogger) void {
        for (self.buffer.items) |*event| {
            event.deinit(self.allocator);
        }
        self.buffer.clearRetainingCapacity();
    }
};

// Tests

test "AuditEventType toString" {
    try std.testing.expectEqualStrings("message_processed", AuditEventType.message_processed.toString());
    try std.testing.expectEqualStrings("security_violation", AuditEventType.security_violation.toString());
}

test "Severity toString" {
    try std.testing.expectEqualStrings("INFO", Severity.info.toString());
    try std.testing.expectEqualStrings("CRITICAL", Severity.critical.toString());
}

test "AuditEvent creation" {
    const allocator = std.testing.allocator;

    var event = try AuditEvent.create(
        allocator,
        .message_processed,
        "test_agent",
        "session_123",
    );
    defer event.deinit(allocator);

    try std.testing.expect(event.event_id.len > 0);
    try std.testing.expectEqualStrings("test_agent", event.agent_name);
    try std.testing.expectEqualStrings("session_123", event.session_id.?);
}

test "AuditEvent with severity" {
    const allocator = std.testing.allocator;

    var event = try AuditEvent.create(allocator, .security_violation, "agent", null);
    defer event.deinit(allocator);

    _ = event.withSeverity(.critical);
    try std.testing.expectEqual(Severity.critical, event.severity);
}

test "AuditEvent with details" {
    const allocator = std.testing.allocator;

    var event = try AuditEvent.create(allocator, .message_processed, "agent", null);
    defer event.deinit(allocator);

    try event.withDetail(allocator, "key1", "value1");
    try event.withDetail(allocator, "key2", "value2");

    const value1 = event.details.get("key1");
    try std.testing.expect(value1 != null);
    try std.testing.expectEqualStrings("value1", value1.?);
}

test "AuditEvent JSON serialization" {
    const allocator = std.testing.allocator;

    var event = try AuditEvent.create(allocator, .message_processed, "test_agent", "session_123");
    defer event.deinit(allocator);

    try event.withDetail(allocator, "success", "true");

    const json = try event.toJson(allocator);
    defer allocator.free(json);

    try std.testing.expect(std.mem.indexOf(u8, json, "\"event_type\":\"message_processed\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, json, "\"agent_name\":\"test_agent\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, json, "\"session_id\":\"session_123\"") != null);
}

test "AuditLogger creation" {
    const allocator = std.testing.allocator;

    var logger = try AuditLogger.init(allocator, "test_audit.log");
    defer logger.deinit();

    try std.testing.expectEqualStrings("test_audit.log", logger.log_path);
    try std.testing.expectEqual(@as(usize, 0), logger.buffer.items.len);
}

test "AuditLogger buffering" {
    const allocator = std.testing.allocator;

    var logger = try AuditLogger.init(allocator, "test_audit_buffer.log");
    defer logger.deinit();
    defer std.fs.cwd().deleteFile("test_audit_buffer.log") catch {};

    var event1 = try AuditEvent.create(allocator, .agent_created, "agent1", null);
    defer event1.deinit(allocator);

    var event2 = try AuditEvent.create(allocator, .agent_created, "agent2", null);
    defer event2.deinit(allocator);

    try logger.log(&event1);
    try logger.log(&event2);

    try std.testing.expectEqual(@as(usize, 2), logger.buffer.items.len);
}

test "AuditLogger flush" {
    const allocator = std.testing.allocator;

    var logger = try AuditLogger.init(allocator, "test_audit_flush.log");
    defer logger.deinit();
    defer std.fs.cwd().deleteFile("test_audit_flush.log") catch {};

    var event = try AuditEvent.create(allocator, .message_processed, "agent", "session");
    defer event.deinit(allocator);

    try logger.log(&event);
    try logger.flush();

    try std.testing.expectEqual(@as(usize, 0), logger.buffer.items.len);

    // Verify file was written
    const file = try std.fs.cwd().openFile("test_audit_flush.log", .{});
    defer file.close();
    const stat = try file.stat();
    try std.testing.expect(stat.size > 0);
}

test "AuditLogger auto-flush on buffer full" {
    const allocator = std.testing.allocator;

    var logger = try AuditLogger.init(allocator, "test_audit_autoflush.log");
    defer logger.deinit();
    defer std.fs.cwd().deleteFile("test_audit_autoflush.log") catch {};

    logger.buffer_size = 3; // Small buffer for testing

    var event = try AuditEvent.create(allocator, .agent_created, "agent", null);
    defer event.deinit(allocator);

    try logger.log(&event);
    try logger.log(&event);
    try logger.log(&event);

    // Should auto-flush after 3 events
    try std.testing.expectEqual(@as(usize, 0), logger.buffer.items.len);
}

test "AuditLogger query by session" {
    const allocator = std.testing.allocator;

    var logger = try AuditLogger.init(allocator, "test_audit_query.log");
    defer logger.deinit();
    defer std.fs.cwd().deleteFile("test_audit_query.log") catch {};

    var event1 = try AuditEvent.create(allocator, .message_processed, "agent", "session1");
    defer event1.deinit(allocator);

    var event2 = try AuditEvent.create(allocator, .message_processed, "agent", "session2");
    defer event2.deinit(allocator);

    try logger.log(&event1);
    try logger.log(&event2);
    try logger.flush();

    // Query functionality is a stub for now
    var results = try logger.query(allocator, "session1");
    defer {
        for (results.items) |*evt| {
            evt.deinit(allocator);
        }
        results.deinit(allocator);
    }

    // TODO: Implement actual query functionality
}

test "AuditEvent all event types" {
    const allocator = std.testing.allocator;

    const event_types = [_]AuditEventType{
        .agent_created,
        .agent_destroyed,
        .message_processed,
        .message_failed,
        .security_violation,
        .configuration_changed,
        .checkpoint_created,
        .checkpoint_restored,
    };

    for (event_types) |event_type| {
        var event = try AuditEvent.create(allocator, event_type, "test_agent", null);
        defer event.deinit(allocator);

        try std.testing.expect(event.event_type == event_type);
    }
}

test "AuditEvent all severity levels" {
    const allocator = std.testing.allocator;

    var event = try AuditEvent.create(allocator, .message_processed, "agent", null);
    defer event.deinit(allocator);

    _ = event.withSeverity(.info);
    try std.testing.expectEqual(Severity.info, event.severity);

    _ = event.withSeverity(.warning);
    try std.testing.expectEqual(Severity.warning, event.severity);

    _ = event.withSeverity(.error_level);
    try std.testing.expectEqual(Severity.error_level, event.severity);

    _ = event.withSeverity(.critical);
    try std.testing.expectEqual(Severity.critical, event.severity);
}

test "Severity toString all levels" {
    try std.testing.expectEqualStrings("INFO", Severity.info.toString());
    try std.testing.expectEqualStrings("WARNING", Severity.warning.toString());
    try std.testing.expectEqualStrings("ERROR", Severity.error_level.toString());
    try std.testing.expectEqualStrings("CRITICAL", Severity.critical.toString());
}

test "AuditLogger countEvents" {
    const allocator = std.testing.allocator;

    var logger = try AuditLogger.init(allocator, "test_count.log");
    defer logger.deinit();
    defer std.fs.cwd().deleteFile("test_count.log") catch {};

    try std.testing.expectEqual(@as(usize, 0), logger.countEvents());

    var event = try AuditEvent.create(allocator, .agent_created, "agent1", null);
    defer event.deinit(allocator);

    try logger.log(&event);
    try std.testing.expectEqual(@as(usize, 1), logger.countEvents());

    try logger.log(&event);
    try std.testing.expectEqual(@as(usize, 2), logger.countEvents());

    try logger.log(&event);
    try std.testing.expectEqual(@as(usize, 3), logger.countEvents());
}

test "AuditLogger queryByType" {
    const allocator = std.testing.allocator;

    var logger = try AuditLogger.init(allocator, "test_query_type.log");
    defer logger.deinit();
    defer std.fs.cwd().deleteFile("test_query_type.log") catch {};

    var event1 = try AuditEvent.create(allocator, .agent_created, "agent1", null);
    defer event1.deinit(allocator);

    var event2 = try AuditEvent.create(allocator, .message_processed, "agent2", null);
    defer event2.deinit(allocator);

    var event3 = try AuditEvent.create(allocator, .agent_created, "agent3", null);
    defer event3.deinit(allocator);

    try logger.log(&event1);
    try logger.log(&event2);
    try logger.log(&event3);

    var results = try logger.queryByType(.agent_created);
    defer results.deinit(allocator);

    try std.testing.expectEqual(@as(usize, 2), results.items.len);
    try std.testing.expectEqual(AuditEventType.agent_created, results.items[0].event_type);
    try std.testing.expectEqual(AuditEventType.agent_created, results.items[1].event_type);
}

test "AuditLogger queryBySeverity" {
    const allocator = std.testing.allocator;

    var logger = try AuditLogger.init(allocator, "test_query_severity.log");
    defer logger.deinit();
    defer std.fs.cwd().deleteFile("test_query_severity.log") catch {};

    var event1 = try AuditEvent.create(allocator, .message_processed, "agent", null);
    defer event1.deinit(allocator);
    _ = event1.withSeverity(.info);

    var event2 = try AuditEvent.create(allocator, .security_violation, "agent", null);
    defer event2.deinit(allocator);
    _ = event2.withSeverity(.critical);

    var event3 = try AuditEvent.create(allocator, .message_failed, "agent", null);
    defer event3.deinit(allocator);
    _ = event3.withSeverity(.error_level);

    try logger.log(&event1);
    try logger.log(&event2);
    try logger.log(&event3);

    var results = try logger.queryBySeverity(.critical);
    defer results.deinit(allocator);

    try std.testing.expectEqual(@as(usize, 1), results.items.len);
    try std.testing.expectEqual(Severity.critical, results.items[0].severity);
}

test "AuditLogger clear" {
    const allocator = std.testing.allocator;

    var logger = try AuditLogger.init(allocator, "test_clear.log");
    defer logger.deinit();
    defer std.fs.cwd().deleteFile("test_clear.log") catch {};

    var event = try AuditEvent.create(allocator, .agent_created, "agent", null);
    defer event.deinit(allocator);

    try logger.log(&event);
    try logger.log(&event);
    try logger.log(&event);

    try std.testing.expectEqual(@as(usize, 3), logger.countEvents());

    logger.clear();
    try std.testing.expectEqual(@as(usize, 0), logger.countEvents());
}

test "AuditEvent JSON with all fields" {
    const allocator = std.testing.allocator;

    var event = try AuditEvent.create(allocator, .security_violation, "security_agent", "session_xyz");
    defer event.deinit(allocator);

    _ = event.withSeverity(.critical);
    try event.withDetail(allocator, "violation_type", "unauthorized_access");
    try event.withDetail(allocator, "ip_address", "192.168.1.100");
    try event.withDetail(allocator, "user_id", "user_123");

    const json = try event.toJson(allocator);
    defer allocator.free(json);

    try std.testing.expect(std.mem.indexOf(u8, json, "\"event_type\":\"security_violation\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, json, "\"agent_name\":\"security_agent\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, json, "\"session_id\":\"session_xyz\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, json, "\"severity\":\"CRITICAL\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, json, "\"violation_type\":\"unauthorized_access\"") != null);
}

test "AuditLogger multiple event types" {
    const allocator = std.testing.allocator;

    var logger = try AuditLogger.init(allocator, "test_multi_types.log");
    defer logger.deinit();
    defer std.fs.cwd().deleteFile("test_multi_types.log") catch {};

    var event1 = try AuditEvent.create(allocator, .agent_created, "agent1", null);
    defer event1.deinit(allocator);

    var event2 = try AuditEvent.create(allocator, .message_processed, "agent1", "session1");
    defer event2.deinit(allocator);

    var event3 = try AuditEvent.create(allocator, .configuration_changed, "agent1", null);
    defer event3.deinit(allocator);

    try logger.log(&event1);
    try logger.log(&event2);
    try logger.log(&event3);

    try std.testing.expectEqual(@as(usize, 3), logger.countEvents());

    var created_events = try logger.queryByType(.agent_created);
    defer created_events.deinit(allocator);
    try std.testing.expectEqual(@as(usize, 1), created_events.items.len);

    var processed_events = try logger.queryByType(.message_processed);
    defer processed_events.deinit(allocator);
    try std.testing.expectEqual(@as(usize, 1), processed_events.items.len);
}

test "AuditEvent empty details" {
    const allocator = std.testing.allocator;

    var event = try AuditEvent.create(allocator, .agent_destroyed, "agent", null);
    defer event.deinit(allocator);

    try std.testing.expectEqual(@as(usize, 0), event.details.count());

    const json = try event.toJson(allocator);
    defer allocator.free(json);

    // Should not have a details field if empty
    try std.testing.expect(std.mem.indexOf(u8, json, "\"agent_destroyed\"") != null);
}

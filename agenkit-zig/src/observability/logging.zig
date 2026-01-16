/// Logging module for Agenkit Zig observability
///
/// This module provides structured logging with trace context correlation:
/// - JSON, Compact, and Pretty log formats
/// - Automatic trace context inclusion from spans
/// - Log levels (trace, debug, info, warn, error, critical)
///
/// ## Example
///
/// ```zig
/// const logging = @import("logging.zig");
/// const std = @import("std");
///
/// // Configure logging
/// try logging.configure(allocator, .json, .info);
///
/// // Log with trace context
/// try logging.logInfo("Agent processing started", .{
///     .agent_name = "echo",
///     .session_id = "abc123",
/// });
/// ```

const std = @import("std");
const Allocator = std.mem.Allocator;

/// Log level enumeration
pub const LogLevel = enum {
    trace,
    debug,
    info,
    warn,
    err,
    critical,

    pub fn toString(self: LogLevel) []const u8 {
        return switch (self) {
            .trace => "TRACE",
            .debug => "DEBUG",
            .info => "INFO",
            .warn => "WARN",
            .err => "ERROR",
            .critical => "CRITICAL",
        };
    }

    pub fn fromString(s: []const u8) !LogLevel {
        if (std.mem.eql(u8, s, "trace")) return .trace;
        if (std.mem.eql(u8, s, "debug")) return .debug;
        if (std.mem.eql(u8, s, "info")) return .info;
        if (std.mem.eql(u8, s, "warn")) return .warn;
        if (std.mem.eql(u8, s, "error")) return .err;
        if (std.mem.eql(u8, s, "critical")) return .critical;
        return error.InvalidLogLevel;
    }
};

/// Log format enumeration
pub const LogFormat = enum {
    json,
    compact,
    pretty,
};

/// Log entry structure
pub const LogEntry = struct {
    timestamp: i64,
    level: LogLevel,
    message: []const u8,
    trace_id: ?[]const u8,
    span_id: ?[]const u8,
    fields: std.StringHashMap([]const u8),

    pub fn init(allocator: Allocator, level: LogLevel, message: []const u8) !LogEntry {
        return LogEntry{
            .timestamp = std.time.milliTimestamp(),
            .level = level,
            .message = try allocator.dupe(u8, message),
            .trace_id = null,
            .span_id = null,
            .fields = std.StringHashMap([]const u8).init(allocator),
        };
    }

    pub fn deinit(self: *LogEntry, allocator: Allocator) void {
        allocator.free(self.message);
        if (self.trace_id) |tid| allocator.free(tid);
        if (self.span_id) |sid| allocator.free(sid);

        var iter = self.fields.iterator();
        while (iter.next()) |entry| {
            allocator.free(entry.key_ptr.*);
            allocator.free(entry.value_ptr.*);
        }
        self.fields.deinit();
    }

    pub fn withField(self: *LogEntry, allocator: Allocator, key: []const u8, value: []const u8) !void {
        const key_copy = try allocator.dupe(u8, key);
        const value_copy = try allocator.dupe(u8, value);
        try self.fields.put(key_copy, value_copy);
    }

    pub fn withTraceContext(self: *LogEntry, allocator: Allocator, trace_id: []const u8, span_id: []const u8) !void {
        self.trace_id = try allocator.dupe(u8, trace_id);
        self.span_id = try allocator.dupe(u8, span_id);
    }
};

/// Global logger state
var global_format: LogFormat = .compact;
var global_level: LogLevel = .info;
var global_configured: bool = false;

/// Configure global logging settings
pub fn configure(format: LogFormat, level: LogLevel) void {
    global_format = format;
    global_level = level;
    global_configured = true;
}

/// Check if a log level should be logged based on global configuration
pub fn shouldLog(level: LogLevel) bool {
    if (!global_configured) return true;

    const current_idx = @intFromEnum(level);
    const min_idx = @intFromEnum(global_level);

    return current_idx >= min_idx;
}

/// Format log entry as JSON
pub fn formatJson(entry: *const LogEntry, allocator: Allocator) ![]const u8 {
    var buf = std.ArrayList(u8){};
    errdefer buf.deinit(allocator);

    try buf.appendSlice(allocator, "{\"timestamp\":");
    try std.fmt.format(buf.writer(allocator), "{d}", .{entry.timestamp});
    try buf.appendSlice(allocator, ",\"level\":\"");
    try buf.appendSlice(allocator, entry.level.toString());
    try buf.appendSlice(allocator, "\",\"message\":\"");
    try buf.appendSlice(allocator, entry.message);
    try buf.appendSlice(allocator, "\"");

    if (entry.trace_id) |tid| {
        try buf.appendSlice(allocator, ",\"trace_id\":\"");
        try buf.appendSlice(allocator, tid);
        try buf.appendSlice(allocator, "\"");
    }

    if (entry.span_id) |sid| {
        try buf.appendSlice(allocator, ",\"span_id\":\"");
        try buf.appendSlice(allocator, sid);
        try buf.appendSlice(allocator, "\"");
    }

    var iter = entry.fields.iterator();
    while (iter.next()) |field| {
        try buf.appendSlice(allocator, ",\"");
        try buf.appendSlice(allocator, field.key_ptr.*);
        try buf.appendSlice(allocator, "\":\"");
        try buf.appendSlice(allocator, field.value_ptr.*);
        try buf.appendSlice(allocator, "\"");
    }

    try buf.appendSlice(allocator, "}");

    return buf.toOwnedSlice(allocator);
}

/// Format log entry as compact text
pub fn formatCompact(entry: *const LogEntry, allocator: Allocator) ![]const u8 {
    var buf = std.ArrayList(u8){};
    errdefer buf.deinit(allocator);

    try std.fmt.format(buf.writer(allocator), "[{d}] {s} {s}", .{
        entry.timestamp,
        entry.level.toString(),
        entry.message,
    });

    if (entry.trace_id) |tid| {
        try std.fmt.format(buf.writer(allocator), " trace_id={s}", .{tid});
    }

    return buf.toOwnedSlice(allocator);
}

/// Format log entry as pretty text with indentation
pub fn formatPretty(entry: *const LogEntry, allocator: Allocator) ![]const u8 {
    var buf = std.ArrayList(u8){};
    errdefer buf.deinit(allocator);

    // Header line
    try std.fmt.format(buf.writer(allocator), "{s} | {s}\n", .{
        entry.level.toString(),
        entry.message,
    });

    // Timestamp
    try std.fmt.format(buf.writer(allocator), "  timestamp: {d}\n", .{entry.timestamp});

    // Trace context if present
    if (entry.trace_id) |tid| {
        try std.fmt.format(buf.writer(allocator), "  trace_id: {s}\n", .{tid});
    }
    if (entry.span_id) |sid| {
        try std.fmt.format(buf.writer(allocator), "  span_id: {s}\n", .{sid});
    }

    // Fields
    if (entry.fields.count() > 0) {
        try buf.appendSlice(allocator, "  fields:\n");
        var iter = entry.fields.iterator();
        while (iter.next()) |field| {
            try std.fmt.format(buf.writer(allocator), "    {s}: {s}\n", .{
                field.key_ptr.*,
                field.value_ptr.*,
            });
        }
    }

    return buf.toOwnedSlice(allocator);
}

/// Log helper function
pub fn log(allocator: Allocator, level: LogLevel, message: []const u8) !void {
    if (!shouldLog(level)) return;

    var entry = try LogEntry.init(allocator, level, message);
    defer entry.deinit(allocator);

    const formatted = switch (global_format) {
        .json => try formatJson(&entry, allocator),
        .compact => try formatCompact(&entry, allocator),
        .pretty => try formatPretty(&entry, allocator),
    };
    defer allocator.free(formatted);

    // For now, just print to stderr
    std.debug.print("{s}\n", .{formatted});
}

// Tests

test "LogLevel toString" {
    try std.testing.expectEqualStrings("INFO", LogLevel.info.toString());
    try std.testing.expectEqualStrings("ERROR", LogLevel.err.toString());
}

test "LogLevel fromString" {
    try std.testing.expectEqual(LogLevel.info, try LogLevel.fromString("info"));
    try std.testing.expectEqual(LogLevel.err, try LogLevel.fromString("error"));
}

test "LogEntry creation" {
    const allocator = std.testing.allocator;

    var entry = try LogEntry.init(allocator, .info, "test message");
    defer entry.deinit(allocator);

    try std.testing.expectEqual(LogLevel.info, entry.level);
    try std.testing.expectEqualStrings("test message", entry.message);
}

test "LogEntry with fields" {
    const allocator = std.testing.allocator;

    var entry = try LogEntry.init(allocator, .info, "test");
    defer entry.deinit(allocator);

    try entry.withField(allocator, "key1", "value1");
    try entry.withField(allocator, "key2", "value2");

    const value1 = entry.fields.get("key1");
    try std.testing.expect(value1 != null);
    try std.testing.expectEqualStrings("value1", value1.?);
}

test "LogEntry with trace context" {
    const allocator = std.testing.allocator;

    var entry = try LogEntry.init(allocator, .info, "test");
    defer entry.deinit(allocator);

    try entry.withTraceContext(allocator, "trace123", "span456");

    try std.testing.expect(entry.trace_id != null);
    try std.testing.expectEqualStrings("trace123", entry.trace_id.?);
}

test "JSON formatting" {
    const allocator = std.testing.allocator;

    var entry = try LogEntry.init(allocator, .info, "test message");
    defer entry.deinit(allocator);

    const json = try formatJson(&entry, allocator);
    defer allocator.free(json);

    try std.testing.expect(std.mem.indexOf(u8, json, "\"level\":\"INFO\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, json, "\"message\":\"test message\"") != null);
}

test "Compact formatting" {
    const allocator = std.testing.allocator;

    var entry = try LogEntry.init(allocator, .info, "test message");
    defer entry.deinit(allocator);

    const compact = try formatCompact(&entry, allocator);
    defer allocator.free(compact);

    try std.testing.expect(std.mem.indexOf(u8, compact, "INFO") != null);
    try std.testing.expect(std.mem.indexOf(u8, compact, "test message") != null);
}

test "Log level filtering" {
    configure(.compact, .warn);

    try std.testing.expect(!shouldLog(.info));
    try std.testing.expect(!shouldLog(.debug));
    try std.testing.expect(shouldLog(.warn));
    try std.testing.expect(shouldLog(.err));
}

test "Pretty formatting" {
    const allocator = std.testing.allocator;

    var entry = try LogEntry.init(allocator, .warn, "Warning message");
    defer entry.deinit(allocator);

    const pretty = try formatPretty(&entry, allocator);
    defer allocator.free(pretty);

    try std.testing.expect(std.mem.indexOf(u8, pretty, "WARN") != null);
    try std.testing.expect(std.mem.indexOf(u8, pretty, "Warning message") != null);
    try std.testing.expect(std.mem.indexOf(u8, pretty, "timestamp:") != null);
}

test "Pretty formatting with trace context" {
    const allocator = std.testing.allocator;

    var entry = try LogEntry.init(allocator, .info, "Traced operation");
    defer entry.deinit(allocator);

    try entry.withTraceContext(allocator, "trace-abc-123", "span-xyz-789");

    const pretty = try formatPretty(&entry, allocator);
    defer allocator.free(pretty);

    try std.testing.expect(std.mem.indexOf(u8, pretty, "trace_id: trace-abc-123") != null);
    try std.testing.expect(std.mem.indexOf(u8, pretty, "span_id: span-xyz-789") != null);
}

test "Pretty formatting with fields" {
    const allocator = std.testing.allocator;

    var entry = try LogEntry.init(allocator, .info, "Request processed");
    defer entry.deinit(allocator);

    try entry.withField(allocator, "method", "POST");
    try entry.withField(allocator, "path", "/api/users");

    const pretty = try formatPretty(&entry, allocator);
    defer allocator.free(pretty);

    try std.testing.expect(std.mem.indexOf(u8, pretty, "fields:") != null);
    try std.testing.expect(std.mem.indexOf(u8, pretty, "method: POST") != null);
    try std.testing.expect(std.mem.indexOf(u8, pretty, "path: /api/users") != null);
}

test "JSON formatting with trace context" {
    const allocator = std.testing.allocator;

    var entry = try LogEntry.init(allocator, .info, "API call");
    defer entry.deinit(allocator);

    try entry.withTraceContext(allocator, "trace123", "span456");

    const json = try formatJson(&entry, allocator);
    defer allocator.free(json);

    try std.testing.expect(std.mem.indexOf(u8, json, "\"trace_id\":\"trace123\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, json, "\"span_id\":\"span456\"") != null);
}

test "JSON formatting with multiple fields" {
    const allocator = std.testing.allocator;

    var entry = try LogEntry.init(allocator, .err, "Database error");
    defer entry.deinit(allocator);

    try entry.withField(allocator, "table", "users");
    try entry.withField(allocator, "operation", "insert");
    try entry.withField(allocator, "error_code", "23505");

    const json = try formatJson(&entry, allocator);
    defer allocator.free(json);

    try std.testing.expect(std.mem.indexOf(u8, json, "\"table\":\"users\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, json, "\"operation\":\"insert\"") != null);
    try std.testing.expect(std.mem.indexOf(u8, json, "\"error_code\":\"23505\"") != null);
}

test "All log levels" {
    try std.testing.expectEqualStrings("TRACE", LogLevel.trace.toString());
    try std.testing.expectEqualStrings("DEBUG", LogLevel.debug.toString());
    try std.testing.expectEqualStrings("INFO", LogLevel.info.toString());
    try std.testing.expectEqualStrings("WARN", LogLevel.warn.toString());
    try std.testing.expectEqualStrings("ERROR", LogLevel.err.toString());
    try std.testing.expectEqualStrings("CRITICAL", LogLevel.critical.toString());
}

test "Log level fromString all levels" {
    try std.testing.expectEqual(LogLevel.trace, try LogLevel.fromString("trace"));
    try std.testing.expectEqual(LogLevel.debug, try LogLevel.fromString("debug"));
    try std.testing.expectEqual(LogLevel.info, try LogLevel.fromString("info"));
    try std.testing.expectEqual(LogLevel.warn, try LogLevel.fromString("warn"));
    try std.testing.expectEqual(LogLevel.err, try LogLevel.fromString("error"));
    try std.testing.expectEqual(LogLevel.critical, try LogLevel.fromString("critical"));
}

test "LogEntry with multiple fields" {
    const allocator = std.testing.allocator;

    var entry = try LogEntry.init(allocator, .info, "Multi-field log");
    defer entry.deinit(allocator);

    try entry.withField(allocator, "user_id", "12345");
    try entry.withField(allocator, "session_id", "sess-abc");
    try entry.withField(allocator, "ip_address", "192.168.1.1");

    try std.testing.expectEqual(@as(usize, 3), entry.fields.count());

    const user_id = entry.fields.get("user_id");
    try std.testing.expectEqualStrings("12345", user_id.?);
}

test "Configuration changes" {
    // Test that configuration can be changed
    configure(.json, .info);
    try std.testing.expect(shouldLog(.info));
    try std.testing.expect(!shouldLog(.debug));

    configure(.pretty, .debug);
    try std.testing.expect(shouldLog(.debug));
    try std.testing.expect(shouldLog(.info));

    configure(.compact, .err);
    try std.testing.expect(!shouldLog(.warn));
    try std.testing.expect(shouldLog(.err));
}

test "Compact format with trace context" {
    const allocator = std.testing.allocator;

    var entry = try LogEntry.init(allocator, .debug, "Debug message");
    defer entry.deinit(allocator);

    try entry.withTraceContext(allocator, "trace-id-123", "span-id-456");

    const compact = try formatCompact(&entry, allocator);
    defer allocator.free(compact);

    try std.testing.expect(std.mem.indexOf(u8, compact, "DEBUG") != null);
    try std.testing.expect(std.mem.indexOf(u8, compact, "Debug message") != null);
    try std.testing.expect(std.mem.indexOf(u8, compact, "trace_id=trace-id-123") != null);
}

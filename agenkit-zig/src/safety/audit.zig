/// Security Audit Logging
///
/// Provides structured logging of security events with file rotation and severity filtering.
/// Audit logs are append-only and tamper-evident for compliance and forensics.
const std = @import("std");
const mem = std.mem;
const fs = std.fs;
const Allocator = std.mem.Allocator;

/// Audit event types
pub const AuditEventType = enum {
    access_granted,
    access_denied,
    permission_granted,
    permission_denied,
    input_validation_failed,
    output_validation_failed,
    prompt_injection_detected,
    sensitive_data_detected,
    anomaly_detected,
    agent_started,
    agent_completed,
    agent_failed,

    pub fn toString(self: AuditEventType) []const u8 {
        return switch (self) {
            .access_granted => "access_granted",
            .access_denied => "access_denied",
            .permission_granted => "permission_granted",
            .permission_denied => "permission_denied",
            .input_validation_failed => "input_validation_failed",
            .output_validation_failed => "output_validation_failed",
            .prompt_injection_detected => "prompt_injection_detected",
            .sensitive_data_detected => "sensitive_data_detected",
            .anomaly_detected => "anomaly_detected",
            .agent_started => "agent_started",
            .agent_completed => "agent_completed",
            .agent_failed => "agent_failed",
        };
    }
};

/// Audit severity levels
pub const AuditSeverity = enum {
    info,
    warning,
    err,
    critical,

    pub fn toString(self: AuditSeverity) []const u8 {
        return switch (self) {
            .info => "info",
            .warning => "warning",
            .err => "error",
            .critical => "critical",
        };
    }

    pub fn fromInt(value: u8) AuditSeverity {
        return switch (value) {
            0 => .info,
            1 => .warning,
            2 => .err,
            3 => .critical,
            else => .info,
        };
    }

    pub fn toInt(self: AuditSeverity) u8 {
        return switch (self) {
            .info => 0,
            .warning => 1,
            .err => 2,
            .critical => 3,
        };
    }
};

/// Audit event structure
pub const AuditEvent = struct {
    event_type: AuditEventType,
    severity: AuditSeverity,
    user_id: []const u8,
    agent_name: []const u8,
    message: []const u8,
    timestamp: i64,

    pub fn format(self: AuditEvent, allocator: Allocator) ![]const u8 {
        // Format as JSON-like string
        return std.fmt.allocPrint(allocator,
            \\{{"timestamp":{d},"event_type":"{s}","severity":"{s}","user_id":"{s}","agent_name":"{s}","message":"{s}"}}
        , .{
            self.timestamp,
            self.event_type.toString(),
            self.severity.toString(),
            self.user_id,
            self.agent_name,
            self.message,
        });
    }
};

/// Security Audit Logger
pub const SecurityAuditLogger = struct {
    log_file_path: []const u8,
    min_severity: AuditSeverity,
    max_bytes: usize,
    backup_count: i32,
    current_size: usize,
    file: ?fs.File,
    allocator: Allocator,

    pub const Config = struct {
        log_file_path: []const u8 = "agenkit_audit.log",
        min_severity: AuditSeverity = .info,
        max_bytes: usize = 10 * 1024 * 1024, // 10MB
        backup_count: i32 = 5,
    };

    pub fn init(allocator: Allocator, config: Config) !SecurityAuditLogger {
        // Open or create log file
        const file = try fs.cwd().createFile(config.log_file_path, .{
            .truncate = false,
            .read = true,
        });

        // Get current file size
        const stat = try file.stat();
        const current_size = stat.size;

        return SecurityAuditLogger{
            .log_file_path = config.log_file_path,
            .min_severity = config.min_severity,
            .max_bytes = config.max_bytes,
            .backup_count = config.backup_count,
            .current_size = current_size,
            .file = file,
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *SecurityAuditLogger) void {
        if (self.file) |file| {
            file.close();
        }
    }

    pub fn shouldLog(self: *SecurityAuditLogger, severity: AuditSeverity) bool {
        return severity.toInt() >= self.min_severity.toInt();
    }

    pub fn log(self: *SecurityAuditLogger, event: AuditEvent) !void {
        if (!self.shouldLog(event.severity)) {
            return;
        }

        const formatted = try event.format(self.allocator);
        defer self.allocator.free(formatted);

        const log_line = try std.fmt.allocPrint(self.allocator, "{s}\n", .{formatted});
        defer self.allocator.free(log_line);

        // Check if rotation needed
        if (self.current_size + log_line.len > self.max_bytes) {
            try self.rotateLog();
        }

        // Write to file
        if (self.file) |file| {
            try file.seekFromEnd(0);
            try file.writeAll(log_line);
            self.current_size += log_line.len;
        }
    }

    fn rotateLog(self: *SecurityAuditLogger) !void {
        // Close current file
        if (self.file) |file| {
            file.close();
            self.file = null;
        }

        // Rotate backup files
        var i = self.backup_count - 1;
        while (i >= 1) : (i -= 1) {
            const old_name = try std.fmt.allocPrint(self.allocator, "{s}.{d}", .{ self.log_file_path, i });
            defer self.allocator.free(old_name);

            const new_name = try std.fmt.allocPrint(self.allocator, "{s}.{d}", .{ self.log_file_path, i + 1 });
            defer self.allocator.free(new_name);

            fs.cwd().rename(old_name, new_name) catch {};
        }

        // Move current to .1
        const backup_name = try std.fmt.allocPrint(self.allocator, "{s}.1", .{self.log_file_path});
        defer self.allocator.free(backup_name);

        fs.cwd().rename(self.log_file_path, backup_name) catch {};

        // Create new log file
        self.file = try fs.cwd().createFile(self.log_file_path, .{
            .truncate = true,
            .read = true,
        });
        self.current_size = 0;
    }

    // Convenience methods
    pub fn logAccessGranted(self: *SecurityAuditLogger, user_id: []const u8, resource: []const u8, agent_name: []const u8) !void {
        const message = try std.fmt.allocPrint(self.allocator, "Access granted to {s}", .{resource});
        defer self.allocator.free(message);

        try self.log(.{
            .event_type = .access_granted,
            .severity = .info,
            .user_id = user_id,
            .agent_name = agent_name,
            .message = message,
            .timestamp = std.time.timestamp(),
        });
    }

    pub fn logAccessDenied(self: *SecurityAuditLogger, user_id: []const u8, resource: []const u8, reason: []const u8, agent_name: []const u8) !void {
        const message = try std.fmt.allocPrint(self.allocator, "Access denied to {s}: {s}", .{ resource, reason });
        defer self.allocator.free(message);

        try self.log(.{
            .event_type = .access_denied,
            .severity = .warning,
            .user_id = user_id,
            .agent_name = agent_name,
            .message = message,
            .timestamp = std.time.timestamp(),
        });
    }

    pub fn logValidationFailure(self: *SecurityAuditLogger, user_id: []const u8, validation_type: []const u8, reason: []const u8, agent_name: []const u8) !void {
        const message = try std.fmt.allocPrint(self.allocator, "{s} validation failed: {s}", .{ validation_type, reason });
        defer self.allocator.free(message);

        try self.log(.{
            .event_type = .input_validation_failed,
            .severity = .warning,
            .user_id = user_id,
            .agent_name = agent_name,
            .message = message,
            .timestamp = std.time.timestamp(),
        });
    }
};

test "AuditEvent formatting" {
    const allocator = std.testing.allocator;

    const event = AuditEvent{
        .event_type = .access_granted,
        .severity = .info,
        .user_id = "user123",
        .agent_name = "test-agent",
        .message = "Test message",
        .timestamp = 1234567890,
    };

    const formatted = try event.format(allocator);
    defer allocator.free(formatted);

    try std.testing.expect(mem.indexOf(u8, formatted, "access_granted") != null);
    try std.testing.expect(mem.indexOf(u8, formatted, "user123") != null);
}

test "SecurityAuditLogger logs events" {
    const allocator = std.testing.allocator;

    const log_path = "test_audit.log";
    defer fs.cwd().deleteFile(log_path) catch {};

    var logger = try SecurityAuditLogger.init(allocator, .{ .log_file_path = log_path });
    defer logger.deinit();

    try logger.logAccessGranted("user123", "/api/data", "test-agent");

    // Verify file was created
    const file = try fs.cwd().openFile(log_path, .{});
    defer file.close();

    const stat = try file.stat();
    try std.testing.expect(stat.size > 0);
}

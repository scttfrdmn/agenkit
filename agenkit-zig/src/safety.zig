/// Agenkit Safety Framework for Zig
///
/// Comprehensive security infrastructure for agent applications.
/// Provides validation, permissions, anomaly detection, and audit logging.
///
/// Features:
/// - Prompt injection detection and content filtering
/// - Role-based access control (RBAC) and sandboxing
/// - Behavioral anomaly detection
/// - Security audit logging with rotation
///
/// Example usage:
/// ```zig
/// const safety = @import("safety.zig");
///
/// // Input validation
/// var detector = try safety.validation.PromptInjectionDetector.init(allocator, .{});
/// defer detector.deinit();
/// const is_safe = try detector.isSafe(user_input);
///
/// // Access control
/// const perms = safety.permissions.Role.user.getPermissions();
/// if (perms.contains(.read_file)) {
///     // Allow file read
/// }
///
/// // Audit logging
/// var logger = try safety.audit.SecurityAuditLogger.init(allocator, .{});
/// defer logger.deinit();
/// try logger.logAccessGranted("user123", "/api/data", "my-agent");
/// ```
pub const validation = @import("safety/validation.zig");
pub const permissions = @import("safety/permissions.zig");
pub const anomaly = @import("safety/anomaly.zig");
pub const audit = @import("safety/audit.zig");

pub const version = "0.47.0";

test {
    @import("std").testing.refAllDecls(@This());
}

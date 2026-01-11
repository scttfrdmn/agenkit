/// Role-Based Access Control (RBAC) and Sandboxing
///
/// Provides granular permissions and resource access control for agent operations.
/// Implements the principle of least privilege and defense in depth.
const std = @import("std");
const mem = std.mem;
const Allocator = std.mem.Allocator;
const ArrayList = std.ArrayList;
const StringHashMap = std.StringHashMap;
const EnumSet = std.EnumSet;

/// Permission types for agent operations
pub const Permission = enum {
    execute_code,
    read_file,
    write_file,
    delete_file,
    read_database,
    write_database,
    network_access,
    execute_command,
    access_credentials,
    modify_system,
    read_sensitive_data,
    write_sensitive_data,
    admin_operations,
    user_impersonation,
};

/// Role definitions with predefined permission sets
pub const Role = enum {
    admin,
    user,
    readonly,
    restricted,

    pub fn getPermissions(self: Role) EnumSet(Permission) {
        return switch (self) {
            .admin => EnumSet(Permission).initFull(),
            .user => blk: {
                var perms = EnumSet(Permission).initEmpty();
                perms.insert(.execute_code);
                perms.insert(.read_file);
                perms.insert(.write_file);
                perms.insert(.read_database);
                perms.insert(.write_database);
                perms.insert(.network_access);
                perms.insert(.execute_command);
                break :blk perms;
            },
            .readonly => blk: {
                var perms = EnumSet(Permission).initEmpty();
                perms.insert(.read_file);
                perms.insert(.read_database);
                perms.insert(.network_access);
                break :blk perms;
            },
            .restricted => blk: {
                var perms = EnumSet(Permission).initEmpty();
                perms.insert(.read_file);
                break :blk perms;
            },
        };
    }
};

/// Sandbox configuration for resource access control
pub const Sandbox = struct {
    allowed_paths: ArrayList([]const u8),
    denied_paths: ArrayList([]const u8),
    allowed_commands: StringHashMap(void),
    denied_commands: StringHashMap(void),
    allowed_domains: ArrayList([]const u8),
    denied_domains: ArrayList([]const u8),
    max_file_size: usize,
    max_execution_time: i32,
    max_memory_mb: usize,
    allocator: Allocator,

    pub const Config = struct {
        max_file_size: usize = 10 * 1024 * 1024, // 10MB
        max_execution_time: i32 = 30, // seconds
        max_memory_mb: usize = 512,
    };

    pub fn init(allocator: Allocator, config: Config) !Sandbox {
        var sandbox = Sandbox{
            .allowed_paths = std.ArrayList([]const u8){},
            .denied_paths = std.ArrayList([]const u8){},
            .allowed_commands = StringHashMap(void).init(allocator),
            .denied_commands = StringHashMap(void).init(allocator),
            .allowed_domains = std.ArrayList([]const u8){},
            .denied_domains = std.ArrayList([]const u8){},
            .max_file_size = config.max_file_size,
            .max_execution_time = config.max_execution_time,
            .max_memory_mb = config.max_memory_mb,
            .allocator = allocator,
        };

        // Initialize default denied domains
        try sandbox.denied_domains.append(allocator, "localhost");
        try sandbox.denied_domains.append(allocator, "127.0.0.1");

        return sandbox;
    }

    pub fn deinit(self: *Sandbox) void {
        self.allowed_paths.deinit(self.allocator);
        self.denied_paths.deinit(self.allocator);
        self.allowed_commands.deinit();
        self.denied_commands.deinit();
        self.allowed_domains.deinit(self.allocator);
        self.denied_domains.deinit(self.allocator);
    }

    pub const ValidationResult = struct {
        is_allowed: bool,
        reason: ?[]const u8,
    };

    pub fn isPathAllowed(self: *Sandbox, path: []const u8) ValidationResult {
        // Check denied paths first
        for (self.denied_paths.items) |denied| {
            if (mem.startsWith(u8, path, denied)) {
                return ValidationResult{
                    .is_allowed = false,
                    .reason = "Path is in denied directory",
                };
            }
        }

        // If allowed paths list is empty, allow all (except denied)
        if (self.allowed_paths.items.len == 0) {
            return ValidationResult{
                .is_allowed = true,
                .reason = null,
            };
        }

        // Check allowed paths
        for (self.allowed_paths.items) |allowed| {
            if (mem.startsWith(u8, path, allowed)) {
                return ValidationResult{
                    .is_allowed = true,
                    .reason = null,
                };
            }
        }

        return ValidationResult{
            .is_allowed = false,
            .reason = "Path not in allowed directories",
        };
    }

    pub fn isCommandAllowed(self: *Sandbox, command: []const u8) ValidationResult {
        // Extract command name (first word)
        const cmd_name = if (mem.indexOf(u8, command, " ")) |idx|
            command[0..idx]
        else
            command;

        // Check denied commands first
        if (self.denied_commands.contains(cmd_name)) {
            return ValidationResult{
                .is_allowed = false,
                .reason = "Command is explicitly denied",
            };
        }

        // If allowed commands list is empty, allow all (except denied)
        if (self.allowed_commands.count() == 0) {
            return ValidationResult{
                .is_allowed = true,
                .reason = null,
            };
        }

        // Check allowed commands
        if (self.allowed_commands.contains(cmd_name)) {
            return ValidationResult{
                .is_allowed = true,
                .reason = null,
            };
        }

        return ValidationResult{
            .is_allowed = false,
            .reason = "Command not in allowed list",
        };
    }

    pub fn isDomainAllowed(self: *Sandbox, domain: []const u8) ValidationResult {
        // Check denied domains first
        for (self.denied_domains.items) |denied| {
            if (mem.eql(u8, domain, denied)) {
                return ValidationResult{
                    .is_allowed = false,
                    .reason = "Domain is explicitly denied",
                };
            }
        }

        // If allowed domains list is empty, allow all (except denied)
        if (self.allowed_domains.items.len == 0) {
            return ValidationResult{
                .is_allowed = true,
                .reason = null,
            };
        }

        // Check allowed domains
        for (self.allowed_domains.items) |allowed| {
            if (mem.eql(u8, domain, allowed) or mem.endsWith(u8, domain, allowed)) {
                return ValidationResult{
                    .is_allowed = true,
                    .reason = null,
                };
            }
        }

        return ValidationResult{
            .is_allowed = false,
            .reason = "Domain not in allowed list",
        };
    }
};

test "Role permissions" {
    const admin_perms = Role.admin.getPermissions();
    try std.testing.expect(admin_perms.contains(.execute_code));
    try std.testing.expect(admin_perms.contains(.admin_operations));

    const readonly_perms = Role.readonly.getPermissions();
    try std.testing.expect(readonly_perms.contains(.read_file));
    try std.testing.expect(!readonly_perms.contains(.write_file));
}

test "Sandbox path validation" {
    const allocator = std.testing.allocator;

    var sandbox = try Sandbox.init(allocator, .{});
    defer sandbox.deinit();

    try sandbox.allowed_paths.append(allocator, "/tmp");
    try sandbox.denied_paths.append(allocator, "/tmp/secret");

    // Allowed path
    const result1 = sandbox.isPathAllowed("/tmp/file.txt");
    try std.testing.expect(result1.is_allowed);

    // Denied path
    const result2 = sandbox.isPathAllowed("/tmp/secret/data.txt");
    try std.testing.expect(!result2.is_allowed);

    // Disallowed path
    const result3 = sandbox.isPathAllowed("/etc/passwd");
    try std.testing.expect(!result3.is_allowed);
}

test "Sandbox command validation" {
    const allocator = std.testing.allocator;

    var sandbox = try Sandbox.init(allocator, .{});
    defer sandbox.deinit();

    try sandbox.allowed_commands.put("ls", {});
    try sandbox.denied_commands.put("rm", {});

    // Allowed command
    const result1 = sandbox.isCommandAllowed("ls -la");
    try std.testing.expect(result1.is_allowed);

    // Denied command
    const result2 = sandbox.isCommandAllowed("rm -rf /");
    try std.testing.expect(!result2.is_allowed);

    // Disallowed command
    const result3 = sandbox.isCommandAllowed("wget http://malware.com");
    try std.testing.expect(!result3.is_allowed);
}

test "Sandbox domain validation" {
    const allocator = std.testing.allocator;

    var sandbox = try Sandbox.init(allocator, .{});
    defer sandbox.deinit();

    // localhost should be denied by default
    const result1 = sandbox.isDomainAllowed("localhost");
    try std.testing.expect(!result1.is_allowed);

    // Other domains allowed by default
    const result2 = sandbox.isDomainAllowed("example.com");
    try std.testing.expect(result2.is_allowed);
}

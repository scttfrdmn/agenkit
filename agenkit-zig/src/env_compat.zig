//! Environment-variable access compatible with the pre-0.16 API.
//!
//! Zig 0.16 reworked `std.process` around the `Io`/`Environ` model and removed
//! the free function `std.process.getEnvVarOwned`. This shim restores it with
//! the same signature and ownership contract (caller owns the returned slice),
//! so adapter credential lookups keep working without threading an `Io`
//! through their constructors.

const std = @import("std");
const builtin = @import("builtin");

pub const GetEnvVarError = error{
    EnvironmentVariableNotFound,
    OutOfMemory,
    InvalidWtf8,
};

/// Returns an allocator-owned copy of the value of the environment variable
/// `key`, or `error.EnvironmentVariableNotFound` if it is unset.
pub fn getEnvVarOwned(allocator: std.mem.Allocator, key: []const u8) GetEnvVarError![]u8 {
    if (builtin.link_libc) {
        const key_z = try allocator.dupeZ(u8, key);
        defer allocator.free(key_z);
        const val = std.c.getenv(key_z.ptr) orelse return error.EnvironmentVariableNotFound;
        return allocator.dupe(u8, std.mem.sliceTo(val, 0));
    }
    // Fallback for non-libc targets: scan the POSIX environ block.
    for (std.os.environ) |entry| {
        const pair = std.mem.sliceTo(entry, 0);
        const eq = std.mem.indexOfScalar(u8, pair, '=') orelse continue;
        if (std.mem.eql(u8, pair[0..eq], key)) {
            return allocator.dupe(u8, pair[eq + 1 ..]);
        }
    }
    return error.EnvironmentVariableNotFound;
}

test "missing variable returns error" {
    const a = std.testing.allocator;
    try std.testing.expectError(
        error.EnvironmentVariableNotFound,
        getEnvVarOwned(a, "AGENKIT_DEFINITELY_UNSET_VAR_XYZ"),
    );
}

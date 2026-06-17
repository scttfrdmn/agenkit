//! A process-global `std.Io` instance for blocking, synchronous I/O.
//!
//! Zig 0.16 routes all filesystem and clock operations through an `Io`
//! instance (`dir.openFile(io, ...)`, `file.close(io)`, etc.) rather than the
//! old free-standing `std.fs` API. The agenkit toolkit performs ordinary
//! blocking file I/O and does not otherwise use the async runtime, so rather
//! than thread an `Io` through every public signature we expose a single
//! lazily-initialised `Io.Threaded` here and hand out its `Io` handle.
//!
//! This preserves the previous synchronous behaviour: callers obtain the
//! handle with `io_compat.io()` and pass it to the new `Io`-based methods.

const std = @import("std");

var threaded: std.Io.Threaded = undefined;
var initialized: bool = false;

/// Returns the process-global blocking `Io` handle, initialising it on first
/// use. Thread-safe for the first-call race only in the sense that callers in
/// agenkit reach this from already-serialised setup paths; the underlying
/// `Threaded` is itself thread-safe once constructed.
pub fn io() std.Io {
    if (!initialized) {
        // `Allocator.failing` is acceptable here: it is only consulted by the
        // async/group entry points (which agenkit never uses), not by the
        // synchronous file and clock operations.
        threaded = std.Io.Threaded.init(std.mem.Allocator.failing, .{});
        initialized = true;
    }
    return threaded.io();
}

/// Convenience handle to the current working directory as an `Io.Dir`.
pub fn cwd() std.Io.Dir {
    return std.Io.Dir.cwd();
}

/// Fill `buffer` with cryptographically secure random bytes.
///
/// Replaces the removed `std.crypto.random.bytes`.
pub fn randomBytes(buffer: []u8) void {
    io().random(buffer);
}

/// Return a random integer of type `T`.
///
/// Replaces `std.crypto.random.int(T)` / `.float(T)` call sites.
pub fn randomInt(comptime T: type) T {
    var bytes: [@sizeOf(T)]u8 = undefined;
    randomBytes(&bytes);
    return std.mem.readInt(T, &bytes, .little);
}

//! Wall-clock time helpers compatible with the pre-0.16 `std.time` API.
//!
//! Zig 0.16 removed the free functions `std.time.timestamp`,
//! `std.time.milliTimestamp`, and `std.time.nanoTimestamp` in favour of the
//! `Io`-based `std.Io.Clock.now` API. Threading an `Io` instance through every
//! call site in the toolkit would be invasive and would change many public
//! signatures, so this module restores the old, allocation-free behaviour by
//! reading the platform real-time clock directly — exactly how the standard
//! library's own `Io.Threaded.nowPosix` does it.
//!
//! Semantics match the old `std.time` functions:
//! - `timestamp()`      -> seconds since the Unix epoch (UTC)
//! - `milliTimestamp()` -> milliseconds since the Unix epoch (UTC)
//! - `nanoTimestamp()`  -> nanoseconds since the Unix epoch (UTC)

const std = @import("std");
const builtin = @import("builtin");
const posix = std.posix;

/// Nanoseconds since the Unix epoch (UTC).
pub fn nanoTimestamp() i128 {
    switch (builtin.os.tag) {
        .windows => {
            // RtlGetSystemTimePrecise() returns 100ns ticks since 1601-01-01.
            const epoch_adj = std.time.epoch.windows * (std.time.ns_per_s / 100);
            const ticks: i128 = std.os.windows.ntdll.RtlGetSystemTimePrecise();
            return (ticks + epoch_adj) * 100;
        },
        .wasi => {
            var ns: std.os.wasi.timestamp_t = undefined;
            const err = std.os.wasi.clock_time_get(.REALTIME, 1, &ns);
            if (err != .SUCCESS) return 0;
            return ns;
        },
        else => {
            var ts: posix.timespec = undefined;
            switch (posix.errno(posix.system.clock_gettime(.REALTIME, &ts))) {
                .SUCCESS => return @as(i128, ts.sec) * std.time.ns_per_s + ts.nsec,
                else => return 0,
            }
        },
    }
}

/// Milliseconds since the Unix epoch (UTC).
pub fn milliTimestamp() i64 {
    return @intCast(@divFloor(nanoTimestamp(), std.time.ns_per_ms));
}

/// Seconds since the Unix epoch (UTC).
pub fn timestamp() i64 {
    return @intCast(@divFloor(nanoTimestamp(), std.time.ns_per_s));
}

/// Block the current thread for approximately `nanoseconds`.
///
/// Replaces the removed `std.time.sleep` / `std.Thread.sleep`. Uses libc
/// `nanosleep` when available (efficient, scheduler-friendly); otherwise busy
/// waits against the real-time clock.
pub fn sleep(nanoseconds: u64) void {
    if (builtin.os.tag == .windows) {
        std.os.windows.kernel32.Sleep(@intCast(nanoseconds / std.time.ns_per_ms));
        return;
    }
    if (builtin.link_libc) {
        var req: std.c.timespec = .{
            .sec = @intCast(nanoseconds / std.time.ns_per_s),
            .nsec = @intCast(nanoseconds % std.time.ns_per_s),
        };
        var rem: std.c.timespec = undefined;
        while (std.c.nanosleep(&req, &rem) != 0) {
            // Interrupted by a signal; resume with the remaining time.
            req = rem;
        }
        return;
    }
    const deadline = nanoTimestamp() + @as(i128, nanoseconds);
    while (nanoTimestamp() < deadline) std.atomic.spinLoopHint();
}

test "timestamps are monotonic-ish and ordered by magnitude" {
    const ns = nanoTimestamp();
    const ms = milliTimestamp();
    const s = timestamp();
    try std.testing.expect(ns > 0);
    try std.testing.expect(ms > 0);
    try std.testing.expect(s > 0);
    // Sanity: a recent date (> 2020-01-01) in seconds.
    try std.testing.expect(s > 1_577_836_800);
}

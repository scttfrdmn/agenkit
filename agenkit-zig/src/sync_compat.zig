//! Synchronization primitives compatible with the pre-0.16 `std.Thread` API.
//!
//! Zig 0.16 moved `Mutex`, `RwLock`, and `Condition` into the `Io` model
//! (`std.Io.Mutex.lock(io)` etc.), which would require threading an `Io`
//! instance through every lock site in the toolkit. To preserve the existing
//! `lock()` / `unlock()` / `wait(&mutex)` API (and behaviour) without that
//! invasive change, this module provides drop-in equivalents built on atomics
//! and cooperative yielding.
//!
//! These are intentionally simple. The toolkit's hot paths are not
//! lock-bound; correctness (mutual exclusion, blocking wait/signal across the
//! batch-processor thread) matters more than raw throughput here.

const std = @import("std");
const builtin = @import("builtin");

fn spin() void {
    if (builtin.single_threaded) return;
    std.Thread.yield() catch {};
}

/// Mutual-exclusion lock mirroring the old `std.Thread.Mutex` API.
pub const Mutex = struct {
    state: std.atomic.Value(u32) = std.atomic.Value(u32).init(0),

    pub fn tryLock(self: *Mutex) bool {
        return self.state.cmpxchgStrong(0, 1, .acquire, .monotonic) == null;
    }

    pub fn lock(self: *Mutex) void {
        while (!self.tryLock()) spin();
    }

    pub fn unlock(self: *Mutex) void {
        self.state.store(0, .release);
    }
};

/// Reader/writer lock mirroring the old `std.Thread.RwLock` API.
///
/// Writers are exclusive; readers share. A positive count means that many
/// readers hold the lock; the sentinel value means a writer holds it.
pub const RwLock = struct {
    state: std.atomic.Value(u32) = std.atomic.Value(u32).init(0),

    const writer_locked: u32 = std.math.maxInt(u32);

    pub fn tryLock(self: *RwLock) bool {
        return self.state.cmpxchgStrong(0, writer_locked, .acquire, .monotonic) == null;
    }

    pub fn lock(self: *RwLock) void {
        while (!self.tryLock()) spin();
    }

    pub fn unlock(self: *RwLock) void {
        self.state.store(0, .release);
    }

    pub fn tryLockShared(self: *RwLock) bool {
        var current = self.state.load(.monotonic);
        while (current != writer_locked) {
            if (self.state.cmpxchgWeak(current, current + 1, .acquire, .monotonic)) |actual| {
                current = actual;
            } else {
                return true;
            }
        }
        return false;
    }

    pub fn lockShared(self: *RwLock) void {
        while (!self.tryLockShared()) spin();
    }

    pub fn unlockShared(self: *RwLock) void {
        _ = self.state.fetchSub(1, .release);
    }
};

/// Condition variable mirroring the old `std.Thread.Condition` API.
///
/// `wait` releases the supplied mutex, blocks until a `signal`/`broadcast`
/// bumps the generation counter, then re-acquires the mutex — exactly the
/// contract callers relied on.
pub const Condition = struct {
    generation: std.atomic.Value(u32) = std.atomic.Value(u32).init(0),

    pub fn wait(self: *Condition, mutex: *Mutex) void {
        const gen = self.generation.load(.acquire);
        mutex.unlock();
        while (self.generation.load(.acquire) == gen) spin();
        mutex.lock();
    }

    pub fn signal(self: *Condition) void {
        _ = self.generation.fetchAdd(1, .release);
    }

    pub fn broadcast(self: *Condition) void {
        _ = self.generation.fetchAdd(1, .release);
    }
};

test "mutex provides mutual exclusion" {
    var m: Mutex = .{};
    m.lock();
    try std.testing.expect(!m.tryLock());
    m.unlock();
    try std.testing.expect(m.tryLock());
    m.unlock();
}

test "rwlock allows shared readers, exclusive writer" {
    var rw: RwLock = .{};
    rw.lockShared();
    try std.testing.expect(rw.tryLockShared());
    try std.testing.expect(!rw.tryLock());
    rw.unlockShared();
    rw.unlockShared();
    try std.testing.expect(rw.tryLock());
    rw.unlock();
}

test "condition wake across threads" {
    var m: Mutex = .{};
    var cond: Condition = .{};
    var ready = std.atomic.Value(bool).init(false);

    const Ctx = struct {
        m: *Mutex,
        cond: *Condition,
        ready: *std.atomic.Value(bool),
        fn run(ctx: @This()) void {
            var i: usize = 0;
            while (i < 1000) : (i += 1) std.atomic.spinLoopHint();
            ctx.ready.store(true, .release);
            ctx.cond.signal();
        }
    };

    m.lock();
    const t = try std.Thread.spawn(.{}, Ctx.run, .{Ctx{ .m = &m, .cond = &cond, .ready = &ready }});
    while (!ready.load(.acquire)) {
        cond.wait(&m);
    }
    m.unlock();
    t.join();
    try std.testing.expect(ready.load(.acquire));
}

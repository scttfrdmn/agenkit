/// Sliding window memory strategy.
///
/// SlidingWindowStrategy implements a simple FIFO (First-In-First-Out) approach:
/// - Keeps the most recent N messages
/// - Evicts oldest messages when window size is exceeded
/// - No prioritization by importance or content
///
/// Good for:
/// - Simple conversational agents with fixed context
/// - Chatbots with short-term memory requirements
/// - Development and testing
///
/// Not suitable for:
/// - Long conversations where important context might be evicted
/// - Applications requiring selective memory retention
///
/// Example:
/// ```zig
/// var strategy = SlidingWindowStrategy.init(allocator, .{ .window_size = 50 });
/// defer strategy.deinit();
///
/// const filtered = try strategy.strategy().apply(entries, context);
/// ```
const std = @import("std");
const Allocator = std.mem.Allocator;
const memory_base = @import("../base.zig");
const MemoryEntry = memory_base.MemoryEntry;
const strategy_base = @import("base.zig");
const MemoryStrategy = strategy_base.MemoryStrategy;
const StrategyContext = strategy_base.StrategyContext;

/// Configuration for sliding window strategy.
pub const SlidingWindowConfig = struct {
    /// Maximum number of entries to keep
    /// Default: 50
    window_size: usize = 50,
};

/// SlidingWindowStrategy keeps the most recent N entries.
pub const SlidingWindowStrategy = struct {
    allocator: Allocator,
    config: SlidingWindowConfig,

    /// Initialize sliding window strategy.
    ///
    /// Args:
    ///   allocator: Memory allocator
    ///   config: Configuration options
    ///
    /// Returns:
    ///   Initialized strategy
    pub fn init(allocator: Allocator, config: SlidingWindowConfig) SlidingWindowStrategy {
        return .{
            .allocator = allocator,
            .config = config,
        };
    }

    /// Free all resources.
    pub fn deinit(self: *SlidingWindowStrategy) void {
        _ = self;
    }

    /// Get MemoryStrategy interface.
    pub fn strategy(self: *SlidingWindowStrategy) MemoryStrategy {
        return .{
            .ptr = self,
            .vtable = &.{
                .apply = applyImpl,
                .deinit = deinitImpl,
            },
        };
    }

    /// Apply sliding window to entries.
    ///
    /// Returns the most recent window_size entries, copying them.
    pub fn apply(
        self: *SlidingWindowStrategy,
        entries: []const *MemoryEntry,
        context: StrategyContext,
    ) ![]const *MemoryEntry {
        _ = context; // Sliding window doesn't use context

        // If entries fit in window, return all
        if (entries.len <= self.config.window_size) {
            const result = try self.allocator.alloc(*MemoryEntry, entries.len);
            for (entries, 0..) |entry, i| {
                const copy = try self.allocator.create(MemoryEntry);
                copy.* = try self.copyEntry(entry);
                result[i] = copy;
            }
            return result;
        }

        // Return most recent window_size entries
        const start_idx = entries.len - self.config.window_size;
        const result = try self.allocator.alloc(*MemoryEntry, self.config.window_size);

        for (entries[start_idx..], 0..) |entry, i| {
            const copy = try self.allocator.create(MemoryEntry);
            copy.* = try self.copyEntry(entry);
            result[i] = copy;
        }

        return result;
    }

    // Private helper methods

    /// Copy a memory entry.
    fn copyEntry(self: *SlidingWindowStrategy, entry: *const MemoryEntry) !MemoryEntry {
        return MemoryEntry{
            .id = try self.allocator.dupe(u8, entry.id),
            .session_id = try self.allocator.dupe(u8, entry.session_id),
            .role = entry.role,
            .content = try self.allocator.dupe(u8, entry.content),
            .timestamp = entry.timestamp,
            .importance = entry.importance,
            .metadata = entry.metadata, // Shallow copy for now
            .allocator = self.allocator,
        };
    }

    // VTable implementations

    fn applyImpl(
        ptr: *anyopaque,
        entries: []const *MemoryEntry,
        context: StrategyContext,
    ) ![]const *MemoryEntry {
        const self: *SlidingWindowStrategy = @ptrCast(@alignCast(ptr));
        return self.apply(entries, context);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *SlidingWindowStrategy = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};

// Tests
const testing = std.testing;

test "SlidingWindowStrategy with small window" {
    const allocator = testing.allocator;

    var strat = SlidingWindowStrategy.init(allocator, .{ .window_size = 2 });
    defer strat.deinit();

    // Create 4 entries
    var entries: [4]*MemoryEntry = undefined;
    for (&entries, 0..) |*e, i| {
        const entry = try allocator.create(MemoryEntry);
        const content = try std.fmt.allocPrint(allocator, "Message {d}", .{i});
        entry.* = try MemoryEntry.init(
            allocator,
            "session-1",
            .user,
            content,
        );
        e.* = entry;
    }
    defer {
        for (entries) |e| {
            e.deinit();
            allocator.destroy(e);
        }
    }

    // Apply strategy
    const context = StrategyContext{
        .context_limit_tokens = 4000,
        .session_id = "session-1",
        .metadata = .null,
        .allocator = allocator,
    };

    const filtered = try strat.apply(&entries, context);
    defer {
        for (filtered) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(filtered);
    }

    // Should only keep last 2 entries
    try testing.expectEqual(@as(usize, 2), filtered.len);
    try testing.expect(std.mem.indexOf(u8, filtered[0].content, "Message 2") != null);
    try testing.expect(std.mem.indexOf(u8, filtered[1].content, "Message 3") != null);
}

test "SlidingWindowStrategy with large window" {
    const allocator = testing.allocator;

    var strat = SlidingWindowStrategy.init(allocator, .{ .window_size = 100 });
    defer strat.deinit();

    // Create 3 entries
    var entries: [3]*MemoryEntry = undefined;
    for (&entries, 0..) |*e, i| {
        const entry = try allocator.create(MemoryEntry);
        const content = try std.fmt.allocPrint(allocator, "Message {d}", .{i});
        entry.* = try MemoryEntry.init(
            allocator,
            "session-1",
            .user,
            content,
        );
        e.* = entry;
    }
    defer {
        for (entries) |e| {
            e.deinit();
            allocator.destroy(e);
        }
    }

    const context = StrategyContext{
        .context_limit_tokens = 4000,
        .session_id = "session-1",
        .metadata = .null,
        .allocator = allocator,
    };

    const filtered = try strat.apply(&entries, context);
    defer {
        for (filtered) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(filtered);
    }

    // Window is larger than entries, should keep all
    try testing.expectEqual(@as(usize, 3), filtered.len);
}

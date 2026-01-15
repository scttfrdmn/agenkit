/// Base interface for memory strategies.
///
/// Memory strategies control how entries are retained, prioritized, and evicted:
/// - **Sliding Window**: Keep most recent N messages (FIFO)
/// - **Importance Weighting**: Prioritize high-importance entries
/// - **Summarization**: Compress old messages while keeping recent ones
/// - **Token Limit**: Respect context window constraints
///
/// Strategies can be composed and customized based on application needs.
///
/// Example:
/// ```zig
/// const strategy = SlidingWindowStrategy.init(allocator, .{ .window_size = 50 });
/// const filtered = try strategy.apply(entries, 4000);
/// ```
const std = @import("std");
const Allocator = std.mem.Allocator;
const memory_base = @import("../base.zig");
const MemoryEntry = memory_base.MemoryEntry;

/// Configuration for strategy application.
pub const StrategyContext = struct {
    /// Maximum context tokens available
    context_limit_tokens: usize,

    /// Session identifier
    session_id: []const u8,

    /// Additional metadata for strategy decisions
    metadata: std.json.Value,

    allocator: Allocator,
};

/// Memory strategy interface.
///
/// All strategies must implement the apply() method to filter/transform entries.
pub const MemoryStrategy = struct {
    ptr: *anyopaque,
    vtable: *const VTable,

    pub const VTable = struct {
        apply: *const fn (
            ptr: *anyopaque,
            entries: []const *MemoryEntry,
            context: StrategyContext,
        ) anyerror![]const *MemoryEntry,
        deinit: *const fn (ptr: *anyopaque) void,
    };

    /// Apply strategy to filter/transform entries.
    ///
    /// Args:
    ///   entries: Input entries to process
    ///   context: Strategy execution context
    ///
    /// Returns:
    ///   Filtered/transformed entries (caller owns memory)
    pub fn apply(
        self: MemoryStrategy,
        entries: []const *MemoryEntry,
        context: StrategyContext,
    ) ![]const *MemoryEntry {
        return self.vtable.apply(self.ptr, entries, context);
    }

    /// Free all resources.
    pub fn deinit(self: MemoryStrategy) void {
        return self.vtable.deinit(self.ptr);
    }
};

/// Importance weighting memory strategy.
///
/// ImportanceWeightingStrategy prioritizes entries based on importance scores:
/// - Keeps high-importance entries longer
/// - Decays importance over time
/// - Maintains top K entries by weighted score
///
/// Score calculation: importance * decay_factor(age)
///
/// Good for:
/// - Retaining critical information
/// - Applications where some messages are more valuable
/// - Long conversations with varying importance
///
/// Example:
/// ```zig
/// var strategy = ImportanceWeightingStrategy.init(allocator, .{
///     .min_importance = 0.5,
///     .decay_rate = 0.95,
/// });
/// defer strategy.deinit();
/// ```
const std = @import("std");
const Allocator = std.mem.Allocator;
const memory_base = @import("../base.zig");
const MemoryEntry = memory_base.MemoryEntry;
const strategy_base = @import("base.zig");
const MemoryStrategy = strategy_base.MemoryStrategy;
const StrategyContext = strategy_base.StrategyContext;

/// Configuration for importance weighting strategy.
pub const ImportanceWeightingConfig = struct {
    /// Minimum importance to keep (0.0-1.0)
    /// Default: 0.3
    min_importance: f32 = 0.3,

    /// Maximum entries to keep
    /// Default: 100
    max_entries: usize = 100,

    /// Decay rate per day (0.0-1.0)
    /// Default: 0.95 (5% decay per day)
    decay_rate: f32 = 0.95,
};

/// Entry with calculated weighted score.
const ScoredEntry = struct {
    entry: *MemoryEntry,
    score: f32,
};

/// ImportanceWeightingStrategy prioritizes by importance.
pub const ImportanceWeightingStrategy = struct {
    allocator: Allocator,
    config: ImportanceWeightingConfig,

    pub fn init(allocator: Allocator, config: ImportanceWeightingConfig) ImportanceWeightingStrategy {
        return .{
            .allocator = allocator,
            .config = config,
        };
    }

    pub fn deinit(self: *ImportanceWeightingStrategy) void {
        _ = self;
    }

    pub fn strategy(self: *ImportanceWeightingStrategy) MemoryStrategy {
        return .{
            .ptr = self,
            .vtable = &.{
                .apply = applyImpl,
                .deinit = deinitImpl,
            },
        };
    }

    pub fn apply(
        self: *ImportanceWeightingStrategy,
        entries: []const *MemoryEntry,
        context: StrategyContext,
    ) ![]const *MemoryEntry {
        _ = context;

        // Score all entries
        var scored = try self.allocator.alloc(ScoredEntry, entries.len);
        defer self.allocator.free(scored);

        const now = std.time.milliTimestamp();

        for (entries, 0..) |entry, i| {
            const age_days = @as(f32, @floatFromInt(now - entry.timestamp)) / (1000.0 * 60.0 * 60.0 * 24.0);
            const decay = std.math.pow(f32, self.config.decay_rate, age_days);
            const score = entry.importance * decay;

            scored[i] = .{ .entry = entry, .score = score };
        }

        // Sort by score (descending)
        std.mem.sort(ScoredEntry, scored, {}, struct {
            fn lessThan(_: void, a: ScoredEntry, b: ScoredEntry) bool {
                return a.score > b.score;
            }
        }.lessThan);

        // Filter by min_importance and max_entries
        var keep_count: usize = 0;
        for (scored) |s| {
            if (s.score >= self.config.min_importance and keep_count < self.config.max_entries) {
                keep_count += 1;
            } else {
                break;
            }
        }

        // Copy filtered entries
        const result = try self.allocator.alloc(*MemoryEntry, keep_count);
        for (scored[0..keep_count], 0..) |s, i| {
            const copy = try self.allocator.create(MemoryEntry);
            copy.* = try self.copyEntry(s.entry);
            result[i] = copy;
        }

        return result;
    }

    fn copyEntry(self: *ImportanceWeightingStrategy, entry: *const MemoryEntry) !MemoryEntry {
        return MemoryEntry{
            .id = try self.allocator.dupe(u8, entry.id),
            .session_id = try self.allocator.dupe(u8, entry.session_id),
            .role = entry.role,
            .content = try self.allocator.dupe(u8, entry.content),
            .timestamp = entry.timestamp,
            .importance = entry.importance,
            .metadata = entry.metadata,
            .allocator = self.allocator,
        };
    }

    fn applyImpl(
        ptr: *anyopaque,
        entries: []const *MemoryEntry,
        context: StrategyContext,
    ) ![]const *MemoryEntry {
        const self: *ImportanceWeightingStrategy = @ptrCast(@alignCast(ptr));
        return self.apply(entries, context);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *ImportanceWeightingStrategy = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};

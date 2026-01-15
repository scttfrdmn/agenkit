/// Memory strategies module.
///
/// This module provides various memory management strategies:
/// - **SlidingWindow**: FIFO retention of recent N messages
/// - **ImportanceWeighting**: Priority-based retention with decay
///
/// Example:
/// ```zig
/// const strategies = @import("strategies/mod.zig");
///
/// var sliding = strategies.SlidingWindowStrategy.init(allocator, .{
///     .window_size = 50,
/// });
/// defer sliding.deinit();
/// ```

pub const base = @import("base.zig");
pub const MemoryStrategy = base.MemoryStrategy;
pub const StrategyContext = base.StrategyContext;

pub const sliding_window = @import("sliding_window.zig");
pub const SlidingWindowStrategy = sliding_window.SlidingWindowStrategy;
pub const SlidingWindowConfig = sliding_window.SlidingWindowConfig;

pub const importance_weighting = @import("importance_weighting.zig");
pub const ImportanceWeightingStrategy = importance_weighting.ImportanceWeightingStrategy;
pub const ImportanceWeightingConfig = importance_weighting.ImportanceWeightingConfig;

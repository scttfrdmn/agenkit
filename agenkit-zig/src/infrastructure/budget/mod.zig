/// Budget tracking and enforcement system
///
/// This module provides comprehensive cost tracking and budget management for LLM usage:
///
/// **Core Components:**
/// - `models`: Cost records and model pricing data
/// - `tracker`: Cost tracking and storage
/// - `limiter`: Budget enforcement middleware
///
/// **Features:**
/// - Real-time cost calculation for major LLM models
/// - Per-session and global budget limits
/// - Thread-safe cost recording and querying
/// - Pluggable storage backends (in-memory, file, Redis)
/// - Budget limiter middleware for agents
/// - Soft/hard limit enforcement
/// - Comprehensive metrics and reporting
///
/// **Example Usage:**
/// ```zig
/// const budget = @import("infrastructure/budget/mod.zig");
///
/// // Track costs
/// var tracker = try budget.CostTracker.init(allocator, null);
/// defer tracker.deinit();
///
/// const cost = try tracker.recordCost(
///     "session-123",
///     "assistant",
///     "claude-sonnet-4",
///     1000,  // input tokens
///     500,   // output tokens
///     0,     // thinking tokens
///     null   // metadata
/// );
/// defer allocator.destroy(cost);
///
/// const total = try tracker.getSessionCost("session-123", null, null);
/// std.debug.print("Session cost: ${d:.2}\n", .{total});
///
/// // Enforce budgets
/// const config = budget.BudgetLimiterConfig{
///     .per_session_limit = 10.0,  // $10 per session
///     .global_limit = 1000.0,      // $1000 total
/// };
///
/// var limiter = try budget.BudgetLimiterDecorator.init(
///     allocator,
///     base_agent,
///     &tracker,
///     config
/// );
/// defer limiter.deinit();
///
/// const result = try limiter.agent().process(message);
/// ```

// Re-export all public APIs
pub const Cost = @import("models.zig").Cost;
pub const ModelPricing = @import("models.zig").ModelPricing;
pub const PricingData = @import("models.zig").PricingData;
pub const Direction = @import("models.zig").Direction;

pub const Storage = @import("tracker.zig").Storage;
pub const InMemoryStorage = @import("tracker.zig").InMemoryStorage;
pub const CostTracker = @import("tracker.zig").CostTracker;

pub const BudgetError = @import("limiter.zig").BudgetError;
pub const BudgetLimiterConfig = @import("limiter.zig").BudgetLimiterConfig;
pub const BudgetLimiterMetrics = @import("limiter.zig").BudgetLimiterMetrics;
pub const BudgetLimiterDecorator = @import("limiter.zig").BudgetLimiterDecorator;

pub const ComplexityLevel = @import("optimizer.zig").ComplexityLevel;
pub const ModelTier = @import("optimizer.zig").ModelTier;
pub const ModelOptimizerConfig = @import("optimizer.zig").ModelOptimizerConfig;
pub const ModelOptimizerMetrics = @import("optimizer.zig").ModelOptimizerMetrics;
pub const ModelOptimizer = @import("optimizer.zig").ModelOptimizer;

// Tests to verify exports work
const std = @import("std");
const testing = std.testing;

test "module exports" {
    // Just verify all types are accessible
    _ = Cost;
    _ = ModelPricing;
    _ = PricingData;
    _ = Direction;
    _ = Storage;
    _ = InMemoryStorage;
    _ = CostTracker;
    _ = BudgetError;
    _ = BudgetLimiterConfig;
    _ = BudgetLimiterMetrics;
    _ = BudgetLimiterDecorator;
    _ = ComplexityLevel;
    _ = ModelTier;
    _ = ModelOptimizerConfig;
    _ = ModelOptimizerMetrics;
    _ = ModelOptimizer;
}

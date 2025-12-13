/// Orchestration Patterns - Core composition primitives
///
/// This module provides the fundamental orchestration patterns for composing agents:
/// - Sequential: Execute agents one after another (pipeline)
/// - Parallel: Execute agents concurrently (fan-out)
/// - Router: Route to one agent based on condition (dispatch)
///
/// These patterns are the building blocks for more complex agent systems.
///
/// # Design Principles
/// - Simple, obvious implementations
/// - No magic, no surprises
/// - Composable (patterns can contain patterns)
/// - Observable (hooks for monitoring/telemetry)
///
/// # Example
/// ```zig
/// const std = @import("std");
/// const agenkit = @import("agenkit");
///
/// // Sequential: agent1 → agent2 → agent3
/// var pipeline = try agenkit.patterns.SequentialPattern.init(
///     allocator,
///     &[_]Agent{ agent1.agent(), agent2.agent(), agent3.agent() },
///     "data_pipeline"
/// );
/// defer pipeline.deinit();
///
/// // Parallel: agent1 + agent2 + agent3 → aggregator
/// var parallel = try agenkit.patterns.ParallelPattern.init(
///     allocator,
///     &[_]Agent{ agent1.agent(), agent2.agent(), agent3.agent() },
///     agenkit.patterns.defaultAggregator,
///     "concurrent_analysis"
/// );
/// defer parallel.deinit();
///
/// // Router: condition → agent
/// var router = try agenkit.patterns.RouterAgent.init(
///     allocator,
///     classifier,
///     agents_map,
///     "default"
/// );
/// defer router.deinit();
/// ```

// Re-export orchestration patterns from their respective modules
pub const SequentialPattern = @import("sequential.zig").SequentialPattern;
pub const ParallelPattern = @import("parallel.zig").ParallelPattern;
pub const defaultAggregator = @import("parallel.zig").defaultAggregator;
pub const Aggregator = @import("parallel.zig").Aggregator;
pub const RouterAgent = @import("router.zig").RouterAgent;
pub const SimpleClassifier = @import("router.zig").SimpleClassifier;
pub const Classifier = @import("router.zig").Classifier;

// Run tests for all orchestration patterns
test {
    _ = @import("sequential.zig");
    _ = @import("parallel.zig");
    _ = @import("router.zig");
}

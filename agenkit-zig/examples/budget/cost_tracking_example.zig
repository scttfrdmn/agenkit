/// Cost tracking example
///
/// This example demonstrates how to:
/// - Track LLM costs across sessions
/// - Query costs by session and agent
/// - Generate cost statistics
/// - Use the model optimizer for intelligent routing
///
/// Run: zig build run-example -- budget/cost_tracking
const std = @import("std");
const budget = @import("../../src/infrastructure/budget/mod.zig");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Cost Tracking Example ===\n\n", .{});

    // Create cost tracker
    std.debug.print("1. Initializing cost tracker...\n", .{});
    var tracker = try budget.CostTracker.init(allocator, null);
    defer tracker.deinit();

    // Record some costs
    std.debug.print("\n2. Recording costs for multiple sessions...\n", .{});

    // Session 1: User asking simple questions
    _ = try tracker.recordCost(
        "session-alice",
        "assistant",
        "gpt-4o-mini", // Cheap model for simple queries
        500, // input tokens
        200, // output tokens
        0, // thinking tokens
        null,
    );
    std.debug.print("  ✓ Recorded cost for session-alice (simple query)\n", .{});

    // Session 2: Complex reasoning task
    _ = try tracker.recordCost(
        "session-bob",
        "analyst",
        "claude-opus-4", // Expensive model for complex reasoning
        2000, // input tokens
        1500, // output tokens
        5000, // thinking tokens (extended thinking)
        null,
    );
    std.debug.print("  ✓ Recorded cost for session-bob (complex reasoning)\n", .{});

    // Session 1 again: Another simple query
    _ = try tracker.recordCost(
        "session-alice",
        "assistant",
        "gpt-4o-mini",
        300,
        150,
        0,
        null,
    );
    std.debug.print("  ✓ Recorded another cost for session-alice\n", .{});

    // Query costs by session
    std.debug.print("\n3. Querying costs by session...\n", .{});

    const alice_cost = try tracker.getSessionCost("session-alice", null, null);
    std.debug.print("  Alice's total cost: ${d:.4}\n", .{alice_cost});

    const bob_cost = try tracker.getSessionCost("session-bob", null, null);
    std.debug.print("  Bob's total cost: ${d:.4}\n", .{bob_cost});

    // Get global costs
    std.debug.print("\n4. Global cost analysis...\n", .{});

    const total_cost = try tracker.getTotalCost(null, null);
    std.debug.print("  Total cost across all sessions: ${d:.4}\n", .{total_cost});

    // Get cost breakdown by model
    var cost_by_model = try tracker.getCostByModel(null, null);
    defer {
        var it = cost_by_model.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        cost_by_model.deinit();
    }

    std.debug.print("\n  Cost breakdown by model:\n", .{});
    var it = cost_by_model.iterator();
    while (it.next()) |entry| {
        std.debug.print("    {s}: ${d:.4}\n", .{ entry.key_ptr.*, entry.value_ptr.* });
    }

    // Get session statistics
    std.debug.print("\n5. Session statistics...\n", .{});

    var stats = try tracker.getSessionStats("session-bob", null, null);
    defer {
        var stat_it = stats.iterator();
        while (stat_it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        stats.deinit();
    }

    std.debug.print("  Bob's session stats:\n", .{});
    if (stats.get("total_cost")) |cost| {
        std.debug.print("    Total cost: ${d:.4}\n", .{cost});
    }
    if (stats.get("input_tokens")) |tokens| {
        std.debug.print("    Input tokens: {d:.0}\n", .{tokens});
    }
    if (stats.get("output_tokens")) |tokens| {
        std.debug.print("    Output tokens: {d:.0}\n", .{tokens});
    }
    if (stats.get("thinking_tokens")) |tokens| {
        std.debug.print("    Thinking tokens: {d:.0}\n", .{tokens});
    }

    // Demonstrate model optimizer
    std.debug.print("\n6. Model optimizer demo...\n", .{});

    var pricing = try budget.ModelPricing.init(allocator);
    defer pricing.deinit();

    var optimizer = try budget.ModelOptimizer.init(allocator, &pricing, budget.ModelOptimizerConfig{
        .cost_weight = 0.7, // Favor cost savings
        .quality_weight = 0.3,
    });
    defer optimizer.deinit();

    // Test with different query complexities
    const queries = [_]struct {
        text: []const u8,
        desc: []const u8,
    }{
        .{
            .text = "What is 2+2?",
            .desc = "Simple math",
        },
        .{
            .text = "Explain the difference between REST and GraphQL APIs",
            .desc = "Moderate explanation",
        },
        .{
            .text = "Write a complete implementation of a B-tree data structure in C with detailed comments explaining the algorithm, including insertion, deletion, and rebalancing operations. Also explain the time complexity.",
            .desc = "Complex coding task",
        },
    };

    for (queries) |query| {
        const model = try optimizer.selectModel(query.text);
        const complexity = optimizer.estimateComplexity(query.text);
        std.debug.print("  Query: {s}\n", .{query.desc});
        std.debug.print("    Complexity: {s} (score: {d})\n", .{ @tagName(complexity), complexity.score() });
        std.debug.print("    Selected model: {s}\n\n", .{model});
    }

    // Show optimizer metrics
    const opt_metrics = optimizer.metrics();
    std.debug.print("  Optimizer metrics:\n", .{});
    std.debug.print("    Total decisions: {d}\n", .{opt_metrics.total_decisions});
    std.debug.print("    Economy model usage: {d}\n", .{opt_metrics.economy_count});
    std.debug.print("    Standard model usage: {d}\n", .{opt_metrics.standard_count});
    std.debug.print("    Advanced model usage: {d}\n", .{opt_metrics.advanced_count});
    if (opt_metrics.avgComplexity()) |avg| {
        std.debug.print("    Average complexity: {d:.1}\n", .{avg});
    }

    std.debug.print("\n=== Example Complete ===\n\n", .{});
}

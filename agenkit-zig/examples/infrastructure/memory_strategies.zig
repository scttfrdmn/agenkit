/// Memory Strategies Example
///
/// This example demonstrates:
/// - Sliding Window strategy (FIFO retention)
/// - Importance Weighting strategy (priority-based)
/// - Comparing different strategies on same data
/// - Strategy configuration and customization
///
/// Run with: zig build run-memory-strategies

const std = @import("std");
const agenkit = @import("agenkit");

const MemoryEntry = agenkit.infrastructure.memory.MemoryEntry;
const strategies = agenkit.infrastructure.memory.strategies;
const StrategyContext = strategies.StrategyContext;

pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Memory Strategies Example ===\n\n", .{});

    const session_id = "strategy-demo";

    // Create a diverse set of memory entries with varying importance
    std.debug.print("Creating 10 memory entries with varying importance...\n\n", .{});

    var entries: [10]*MemoryEntry = undefined;
    const messages = [_]struct { content: []const u8, importance: f32 }{
        .{ .content = "What is machine learning?", .importance = 0.9 },
        .{ .content = "ML is a subset of AI...", .importance = 0.8 },
        .{ .content = "Tell me a joke", .importance = 0.1 },
        .{ .content = "Why did the programmer quit?...", .importance = 0.1 },
        .{ .content = "Explain neural networks", .importance = 0.9 },
        .{ .content = "Neural networks are inspired by...", .importance = 0.8 },
        .{ .content = "What's for lunch?", .importance = 0.2 },
        .{ .content = "I don't have that information", .importance = 0.2 },
        .{ .content = "How do transformers work?", .importance = 0.95 },
        .{ .content = "Transformers use attention mechanisms...", .importance = 0.95 },
    };

    for (&entries, 0..) |*e, i| {
        const role = if (i % 2 == 0)
            agenkit.infrastructure.memory.Role.user
        else
            agenkit.infrastructure.memory.Role.assistant;

        const entry = try allocator.create(MemoryEntry);
        entry.* = try MemoryEntry.init(allocator, session_id, role, messages[i].content);
        entry.setImportance(messages[i].importance);
        e.* = entry;

        std.debug.print("{d}. [{s}] {s} (importance: {d:.2})\n", .{
            i + 1,
            entry.role.toString(),
            entry.content,
            entry.importance,
        });
    }
    defer {
        for (entries) |e| {
            e.deinit();
            allocator.destroy(e);
        }
    }

    const context = StrategyContext{
        .context_limit_tokens = 4000,
        .session_id = session_id,
        .metadata = .null,
        .allocator = allocator,
    };

    // Strategy 1: Sliding Window (keep most recent N)
    std.debug.print("\n--- Strategy 1: Sliding Window ---\n\n", .{});
    std.debug.print("Configuration: window_size = 5 (keep 5 most recent)\n", .{});
    std.debug.print("Behavior: Simple FIFO - oldest entries evicted first\n\n", .{});

    var sliding = strategies.SlidingWindowStrategy.init(allocator, .{ .window_size = 5 });
    defer sliding.deinit();

    const sliding_result = try sliding.apply(&entries, context);
    defer {
        for (sliding_result) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(sliding_result);
    }

    std.debug.print("Retained {d} entries:\n", .{sliding_result.len});
    for (sliding_result, 1..) |entry, i| {
        const preview = if (entry.content.len > 40)
            entry.content[0..40]
        else
            entry.content;
        std.debug.print("{d}. [{s}] {s}... (importance: {d:.2})\n", .{
            i,
            entry.role.toString(),
            preview,
            entry.importance,
        });
    }

    // Strategy 2: Importance Weighting
    std.debug.print("\n--- Strategy 2: Importance Weighting ---\n\n", .{});
    std.debug.print("Configuration: min_importance = 0.5, max_entries = 6\n", .{});
    std.debug.print("Behavior: Keep high-importance entries, decay over time\n\n", .{});

    var importance = strategies.ImportanceWeightingStrategy.init(allocator, .{
        .min_importance = 0.5,
        .max_entries = 6,
        .decay_rate = 0.95, // 5% decay per day
    });
    defer importance.deinit();

    const importance_result = try importance.apply(&entries, context);
    defer {
        for (importance_result) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(importance_result);
    }

    std.debug.print("Retained {d} entries (filtered by importance >= 0.5):\n", .{importance_result.len});
    for (importance_result, 1..) |entry, i| {
        const preview = if (entry.content.len > 40)
            entry.content[0..40]
        else
            entry.content;
        std.debug.print("{d}. [{s}] {s}... (importance: {d:.2})\n", .{
            i,
            entry.role.toString(),
            preview,
            entry.importance,
        });
    }

    // Compare strategies
    std.debug.print("\n--- Strategy Comparison ---\n\n", .{});

    std.debug.print("Original entries: 10\n", .{});
    std.debug.print("Sliding Window (5): {d} entries - keeps most recent regardless of importance\n", .{sliding_result.len});
    std.debug.print("Importance Weighting (min 0.5): {d} entries - keeps high-importance entries\n", .{importance_result.len});

    std.debug.print("\nKey Differences:\n", .{});
    std.debug.print("1. Sliding Window is simple and predictable (FIFO)\n", .{});
    std.debug.print("2. Importance Weighting preserves critical information\n", .{});
    std.debug.print("3. Sliding Window may lose important context from earlier\n", .{});
    std.debug.print("4. Importance Weighting may skip recent low-importance messages\n", .{});

    // Demonstrate with extreme window size
    std.debug.print("\n--- Extreme Configurations ---\n\n", .{});

    // Very small window
    var tiny_window = strategies.SlidingWindowStrategy.init(allocator, .{ .window_size = 2 });
    defer tiny_window.deinit();

    const tiny_result = try tiny_window.apply(&entries, context);
    defer {
        for (tiny_result) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(tiny_result);
    }

    std.debug.print("Tiny Window (2 entries): Keeps only the last 2 messages\n", .{});
    for (tiny_result, 1..) |entry, i| {
        std.debug.print("{d}. {s}\n", .{ i, entry.content });
    }

    // Very strict importance
    var strict_importance = strategies.ImportanceWeightingStrategy.init(allocator, .{
        .min_importance = 0.9,
        .max_entries = 100,
        .decay_rate = 1.0, // No decay
    });
    defer strict_importance.deinit();

    const strict_result = try strict_importance.apply(&entries, context);
    defer {
        for (strict_result) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(strict_result);
    }

    std.debug.print("\nStrict Importance (>= 0.9): Keeps only critical information\n", .{});
    for (strict_result, 1..) |entry, i| {
        std.debug.print("{d}. {s} (importance: {d:.2})\n", .{ i, entry.content, entry.importance });
    }

    // Use case recommendations
    std.debug.print("\n--- Strategy Selection Guide ---\n\n", .{});
    std.debug.print("Use Sliding Window when:\n", .{});
    std.debug.print("  ✓ All messages are equally important\n", .{});
    std.debug.print("  ✓ You want predictable, simple behavior\n", .{});
    std.debug.print("  ✓ Recent context is all that matters\n", .{});
    std.debug.print("  ✓ Development/testing with fixed-size context\n\n", .{});

    std.debug.print("Use Importance Weighting when:\n", .{});
    std.debug.print("  ✓ Some messages are more valuable than others\n", .{});
    std.debug.print("  ✓ You want to preserve critical information\n", .{});
    std.debug.print("  ✓ Conversations have varying signal-to-noise\n", .{});
    std.debug.print("  ✓ You need intelligent memory management\n", .{});

    std.debug.print("\n=== Example Complete ===\n", .{});
}

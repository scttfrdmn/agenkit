//! Memory Hierarchy Pattern Example
//!
//! The Memory Hierarchy pattern implements three-tier memory with different
//! retention and retrieval characteristics.
//!
//! This example demonstrates:
//! - Working memory (FIFO, immediate access)
//! - Short-term memory (TTL + LRU eviction)
//! - Long-term memory (importance-based semantic retrieval)
//! - Memory tier coordination
//!
//! Run with: zig build run-memory-hierarchy

const std = @import("std");
const agenkit = @import("agenkit");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== AgentKit Memory Hierarchy Pattern Example ===\n\n", .{});

    // Example 1: Working Memory (FIFO)
    std.debug.print("--- Example 1: Working Memory ---\n", .{});
    {
        var working = try agenkit.patterns.WorkingMemory.init(allocator, 3);
        defer working.deinit();

        const entry1 = try agenkit.patterns.MemoryEntry.init(allocator, "fact1", null, 1.0, "session1");
        const entry2 = try agenkit.patterns.MemoryEntry.init(allocator, "fact2", null, 1.0, "session1");
        const entry3 = try agenkit.patterns.MemoryEntry.init(allocator, "fact3", null, 1.0, "session1");
        const entry4 = try agenkit.patterns.MemoryEntry.init(allocator, "fact4", null, 1.0, "session1");

        try working.store(entry1);
        try working.store(entry2);
        try working.store(entry3);
        std.debug.print("Stored 3 entries (capacity: 3)\n", .{});

        try working.store(entry4);
        std.debug.print("Stored 4th entry - oldest evicted (FIFO)\n", .{});
        std.debug.print("✓ Working memory manages immediate context\n\n", .{});
    }

    // Example 2: Short-term Memory (TTL + LRU)
    std.debug.print("--- Example 2: Short-Term Memory ---\n", .{});
    {
        var short_term = try agenkit.patterns.ShortTermMemory.init(
            allocator,
            5, // capacity
            3600, // ttl_seconds
        );
        defer short_term.deinit();

        const entry1 = try agenkit.patterns.MemoryEntry.init(allocator, "recent1", null, 0.8, "session2");
        const entry2 = try agenkit.patterns.MemoryEntry.init(allocator, "recent2", null, 0.7, "session2");

        try short_term.store(entry1);
        try short_term.store(entry2);

        var results = try short_term.retrieve(allocator, "recent", 10);
        defer {
            for (results.items) |*r| {
                r.deinit();
            }
            results.deinit(allocator);
        }

        std.debug.print("Retrieved {d} entries\n", .{results.items.len});
        std.debug.print("✓ Short-term memory with TTL and LRU\n\n", .{});
    }

    // Example 3: Long-term Memory (Importance-based)
    std.debug.print("--- Example 3: Long-Term Memory ---\n", .{});
    {
        var long_term = try agenkit.patterns.LongTermMemory.init(allocator, 0.5); // min importance
        defer long_term.deinit();

        const high_importance = try agenkit.patterns.MemoryEntry.init(allocator, "critical", null, 0.9, "session3");
        const low_importance = try agenkit.patterns.MemoryEntry.init(allocator, "trivial", null, 0.3, "session3");

        try long_term.store(high_importance);
        try long_term.store(low_importance); // Below threshold, not stored

        var all = try long_term.retrieve(allocator, "", 100);
        defer {
            for (all.items) |*entry| {
                entry.deinit();
            }
            all.deinit(allocator);
        }

        std.debug.print("Stored entries: {d}\n", .{all.items.len});
        std.debug.print("✓ Only high-importance entries retained\n\n", .{});
    }

    // Example 4: Full Hierarchy
    std.debug.print("--- Example 4: Complete Memory Hierarchy ---\n", .{});
    {
        // Create individual tiers
        var working = try agenkit.patterns.WorkingMemory.init(allocator, 3);
        defer working.deinit();

        var short_term = try agenkit.patterns.ShortTermMemory.init(allocator, 10, 3600);
        defer short_term.deinit();

        var long_term = try agenkit.patterns.LongTermMemory.init(allocator, 0.7);
        defer long_term.deinit();

        // Combine into hierarchy
        var hierarchy = try agenkit.patterns.MemoryHierarchy.init(
            allocator,
            &working,
            &short_term,
            &long_term,
        );
        defer hierarchy.deinit();

        _ = try hierarchy.store("important data", null, 0.85, "session4");

        var results = try hierarchy.retrieve(allocator, "data", 5, null);
        defer {
            for (results.items) |*r| {
                r.deinit();
            }
            results.deinit(allocator);
        }

        std.debug.print("Retrieved from hierarchy: {d} entries\n", .{results.items.len});
        std.debug.print("✓ Three-tier memory coordination\n\n", .{});
    }

    std.debug.print("=== Memory Hierarchy Summary ===\n", .{});
    std.debug.print("✓ Working: FIFO, immediate context\n", .{});
    std.debug.print("✓ Short-term: TTL + LRU eviction\n", .{});
    std.debug.print("✓ Long-term: Importance-based retention\n", .{});
    std.debug.print("✓ Automatic promotion between tiers\n", .{});
    std.debug.print("✓ Useful for: agents needing persistent memory\n", .{});
    std.debug.print("\n✓ Memory Hierarchy pattern example completed successfully!\n\n", .{});
}

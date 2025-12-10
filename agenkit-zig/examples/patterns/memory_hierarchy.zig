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

        const entry1 = try agenkit.patterns.MemoryEntry.init(allocator, "fact1", 1.0);
        const entry2 = try agenkit.patterns.MemoryEntry.init(allocator, "fact2", 1.0);
        const entry3 = try agenkit.patterns.MemoryEntry.init(allocator, "fact3", 1.0);
        const entry4 = try agenkit.patterns.MemoryEntry.init(allocator, "fact4", 1.0);

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

        const entry1 = try agenkit.patterns.MemoryEntry.init(allocator, "recent1", 0.8);
        const entry2 = try agenkit.patterns.MemoryEntry.init(allocator, "recent2", 0.7);

        try short_term.store(entry1);
        try short_term.store(entry2);

        const results = try short_term.retrieve(allocator, "recent", 10);
        defer {
            for (results) |*r| {
                r.deinit();
            }
            allocator.free(results);
        }

        std.debug.print("Retrieved {d} entries\n", .{results.len});
        std.debug.print("✓ Short-term memory with TTL and LRU\n\n", .{});
    }

    // Example 3: Long-term Memory (Importance-based)
    std.debug.print("--- Example 3: Long-Term Memory ---\n", .{});
    {
        var long_term = try agenkit.patterns.LongTermMemory.init(allocator, 0.5); // min importance
        defer long_term.deinit();

        const high_importance = try agenkit.patterns.MemoryEntry.init(allocator, "critical", 0.9);
        const low_importance = try agenkit.patterns.MemoryEntry.init(allocator, "trivial", 0.3);

        try long_term.store(high_importance);
        try long_term.store(low_importance); // Below threshold, not stored

        const all = try long_term.retrieveAll(allocator);
        defer {
            for (all) |*entry| {
                entry.deinit();
            }
            allocator.free(all);
        }

        std.debug.print("Stored entries: {d}\n", .{all.len});
        std.debug.print("✓ Only high-importance entries retained\n\n", .{});
    }

    // Example 4: Full Hierarchy
    std.debug.print("--- Example 4: Complete Memory Hierarchy ---\n", .{});
    {
        var hierarchy = try agenkit.patterns.MemoryHierarchy.init(
            allocator,
            3, // working_capacity
            10, // short_term_capacity
            3600, // short_term_ttl
            0.7, // long_term_threshold
        );
        defer hierarchy.deinit();

        const entry = try agenkit.patterns.MemoryEntry.init(allocator, "important data", 0.85);
        try hierarchy.store(entry);

        const results = try hierarchy.retrieve(allocator, "data", 5);
        defer {
            for (results) |*r| {
                r.deinit();
            }
            allocator.free(results);
        }

        std.debug.print("Retrieved from hierarchy: {d} entries\n", .{results.len});
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

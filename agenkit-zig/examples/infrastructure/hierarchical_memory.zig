/// Hierarchical Memory System Example
///
/// This example demonstrates:
/// - 3-tier memory hierarchy (working, short-term, long-term)
/// - Automatic tier management
/// - Cross-tier retrieval with deduplication
/// - Tier-specific summaries
///
/// Run with: zig build run-hierarchical-memory

const std = @import("std");
const agenkit = @import("agenkit");

const MemoryEntry = agenkit.infrastructure.memory.MemoryEntry;
const HierarchyMemory = agenkit.infrastructure.memory.HierarchyMemory;

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Hierarchical Memory System Example ===\n\n", .{});

    // Initialize hierarchical memory with 3 tiers
    var hierarchy = HierarchyMemory.init(allocator, .{
        .working_capacity = 5, // Keep 5 recent messages in working memory
        .short_term_capacity = 20, // Keep 20 messages in short-term
        .long_term_summary_threshold = 50, // Summarize after 50 messages
        .importance_threshold = 0.3, // Min importance for retention
    });
    defer hierarchy.deinit();

    const session_id = "conversation-001";

    std.debug.print("Memory Configuration:\n", .{});
    std.debug.print("  Working memory: 5 entries (most recent)\n", .{});
    std.debug.print("  Short-term memory: 20 entries (recent with importance)\n", .{});
    std.debug.print("  Long-term memory: unlimited (summarized history)\n\n", .{});

    // Simulate a long conversation
    std.debug.print("Simulating a conversation about AI and software development...\n\n", .{});

    const conversation = [_]struct { role: []const u8, content: []const u8, importance: f32 }{
        .{ .role = "user", .content = "Tell me about neural networks", .importance = 0.8 },
        .{ .role = "assistant", .content = "Neural networks are computing systems inspired by biological neural networks...", .importance = 0.7 },
        .{ .role = "user", .content = "What about deep learning?", .importance = 0.8 },
        .{ .role = "assistant", .content = "Deep learning uses multiple layers of neural networks...", .importance = 0.7 },
        .{ .role = "user", .content = "Can you explain backpropagation?", .importance = 0.9 },
        .{ .role = "assistant", .content = "Backpropagation is the algorithm for training neural networks...", .importance = 0.9 },
        .{ .role = "user", .content = "What's the weather today?", .importance = 0.2 }, // Low importance
        .{ .role = "assistant", .content = "I don't have access to weather data.", .importance = 0.2 },
        .{ .role = "user", .content = "Back to AI - what about transformers?", .importance = 0.9 },
        .{ .role = "assistant", .content = "Transformers are a revolutionary architecture using attention mechanisms...", .importance = 0.9 },
        .{ .role = "user", .content = "How do I implement this in Zig?", .importance = 0.8 },
        .{ .role = "assistant", .content = "In Zig, you'd use allocators for memory management and explicit error handling...", .importance = 0.8 },
    };

    // Store all entries
    for (conversation) |msg| {
        const role = if (std.mem.eql(u8, msg.role, "user"))
            agenkit.infrastructure.memory.Role.user
        else
            agenkit.infrastructure.memory.Role.assistant;

        var entry = try MemoryEntry.init(allocator, session_id, role, msg.content);
        entry.setImportance(msg.importance);
        try hierarchy.store(&entry);
        entry.deinit();

        std.debug.print("[{s}] {s}\n", .{ msg.role, msg.content });
    }

    // Retrieve from all tiers
    std.debug.print("\n--- Retrieving from Memory Hierarchy ---\n\n", .{});

    // Get most recent entries (will come from working memory first)
    const recent = try hierarchy.retrieve(session_id, 5);
    defer {
        for (recent) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(recent);
    }

    std.debug.print("Most Recent {d} Entries (Working Memory):\n", .{recent.len});
    for (recent, 1..) |entry, i| {
        std.debug.print("{d}. [{s}] {s}\n", .{ i, entry.role.toString(), entry.content });
    }

    // Get more entries (will pull from short-term and long-term)
    std.debug.print("\n--- Extended Retrieval (All Tiers) ---\n\n", .{});
    const extended = try hierarchy.retrieve(session_id, 10);
    defer {
        for (extended) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(extended);
    }

    std.debug.print("Retrieved {d} entries across all memory tiers:\n", .{extended.len});
    for (extended, 1..) |entry, i| {
        std.debug.print("{d}. [{s}] {s} (importance: {d:.2})\n", .{
            i,
            entry.role.toString(),
            entry.content,
            entry.importance,
        });
    }

    // Generate hierarchical summary
    std.debug.print("\n--- Hierarchical Memory Summary ---\n\n", .{});
    const summary = try hierarchy.summarize(session_id, 20);
    defer allocator.free(summary);
    std.debug.print("{s}\n", .{summary});

    // Demonstrate importance filtering
    std.debug.print("\n--- Importance-Based Filtering ---\n\n", .{});
    std.debug.print("High-importance entries (>= 0.8) are retained longer in memory\n", .{});
    std.debug.print("Low-importance entries (< 0.3) are evicted first\n", .{});
    std.debug.print("Weather question (importance 0.2) will be evicted before AI topics (0.8-0.9)\n", .{});

    // Add more entries to trigger eviction
    std.debug.print("\n--- Testing Memory Capacity ---\n\n", .{});
    var i: usize = 0;
    while (i < 3) : (i += 1) {
        const content = try std.fmt.allocPrint(
            allocator,
            "Additional message {d} to test capacity",
            .{i + 1},
        );
        defer allocator.free(content);

        var entry = try MemoryEntry.init(allocator, session_id, .user, content);
        entry.setImportance(0.5);
        try hierarchy.store(&entry);
        entry.deinit();
    }

    const final = try hierarchy.retrieve(session_id, 8);
    defer {
        for (final) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(final);
    }

    std.debug.print("After adding more entries, retrieved {d} most recent:\n", .{final.len});
    for (final, 1..) |entry, idx| {
        const preview = if (entry.content.len > 50)
            entry.content[0..50]
        else
            entry.content;
        std.debug.print("{d}. [{s}] {s}... (importance: {d:.2})\n", .{
            idx,
            entry.role.toString(),
            preview,
            entry.importance,
        });
    }

    // Clear all tiers
    std.debug.print("\n--- Clearing All Memory Tiers ---\n\n", .{});
    const cleared = try hierarchy.clear(session_id);
    std.debug.print("Cleared {d} total entries from all tiers\n", .{cleared});

    std.debug.print("\n=== Example Complete ===\n", .{});
}

/// Basic Memory System Example
///
/// This example demonstrates:
/// - Creating memory entries
/// - Storing and retrieving memories
/// - Basic memory operations (summarize, clear)
/// - Session isolation
///
/// Run with: zig build run-basic-memory

const std = @import("std");
const agenkit = @import("agenkit");

const MemoryEntry = agenkit.infrastructure.memory.MemoryEntry;
const InMemoryMemory = agenkit.infrastructure.memory.InMemoryMemory;
const Role = agenkit.infrastructure.memory.Role;

pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Basic Memory System Example ===\n\n", .{});

    // Initialize memory storage
    var memory = InMemoryMemory.init(allocator, .{
        .max_entries_per_session = 10,
        .context_limit_tokens = 4000,
    });
    defer memory.deinit();

    const session_id = "user-123";

    // Simulate a conversation
    std.debug.print("Simulating a conversation...\n\n", .{});

    // User asks about weather
    var entry1 = try MemoryEntry.init(
        allocator,
        session_id,
        .user,
        "What's the weather like today?",
    );
    entry1.setImportance(0.7); // Moderately important
    try memory.store(&entry1);
    entry1.deinit();
    std.debug.print("User: What's the weather like today?\n", .{});

    // Assistant responds
    var entry2 = try MemoryEntry.init(
        allocator,
        session_id,
        .assistant,
        "It's sunny with a high of 72°F (22°C). Perfect weather for outdoor activities!",
    );
    entry2.setImportance(0.6);
    try memory.store(&entry2);
    entry2.deinit();
    std.debug.print("Assistant: It's sunny with a high of 72°F...\n\n", .{});

    // User asks follow-up
    var entry3 = try MemoryEntry.init(
        allocator,
        session_id,
        .user,
        "Should I bring an umbrella?",
    );
    entry3.setImportance(0.5);
    try memory.store(&entry3);
    entry3.deinit();
    std.debug.print("User: Should I bring an umbrella?\n", .{});

    // Assistant responds
    var entry4 = try MemoryEntry.init(
        allocator,
        session_id,
        .assistant,
        "No, you won't need an umbrella today. The forecast is clear with no chance of rain.",
    );
    entry4.setImportance(0.4);
    try memory.store(&entry4);
    entry4.deinit();
    std.debug.print("Assistant: No, you won't need an umbrella...\n\n", .{});

    // Retrieve recent conversation history
    std.debug.print("--- Retrieving Recent History ---\n\n", .{});
    const entries = try memory.retrieve(session_id, 4);
    defer {
        for (entries) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(entries);
    }

    std.debug.print("Retrieved {d} entries:\n", .{entries.len});
    for (entries, 1..) |entry, i| {
        std.debug.print("{d}. [{s}] {s} (importance: {d:.2})\n", .{
            i,
            entry.role.toString(),
            entry.content,
            entry.importance,
        });
    }

    // Generate summary
    std.debug.print("\n--- Memory Summary ---\n\n", .{});
    const summary = try memory.summarize(session_id, 10);
    defer allocator.free(summary);
    std.debug.print("{s}\n", .{summary});

    // Demonstrate session isolation
    std.debug.print("\n--- Session Isolation ---\n\n", .{});

    const session2_id = "user-456";
    var entry5 = try MemoryEntry.init(
        allocator,
        session2_id,
        .user,
        "Hello from another session!",
    );
    try memory.store(&entry5);
    entry5.deinit();

    const session1_entries = try memory.retrieve(session_id, 0);
    defer {
        for (session1_entries) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(session1_entries);
    }

    const session2_entries = try memory.retrieve(session2_id, 0);
    defer {
        for (session2_entries) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(session2_entries);
    }

    std.debug.print("Session 1 entries: {d}\n", .{session1_entries.len});
    std.debug.print("Session 2 entries: {d}\n", .{session2_entries.len});

    // Clear session
    std.debug.print("\n--- Clearing Session ---\n\n", .{});
    const cleared = try memory.clear(session_id);
    std.debug.print("Cleared {d} entries from session {s}\n", .{ cleared, session_id });

    const remaining = try memory.retrieve(session_id, 0);
    defer allocator.free(remaining);
    std.debug.print("Remaining entries: {d}\n", .{remaining.len});

    std.debug.print("\n=== Example Complete ===\n", .{});
}

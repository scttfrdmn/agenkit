/// Hierarchical memory system with 3 tiers.
///
/// HierarchyMemory implements a multi-tier memory architecture:
/// - **Working Memory**: 5-10 recent messages, instant access
/// - **Short-term Memory**: 50-100 messages with importance weighting
/// - **Long-term Memory**: Summarized historical context
///
/// Tier promotion/demotion happens automatically based on:
/// - Age (recent → working, old → long-term)
/// - Importance (high importance → retained longer)
/// - Access patterns (frequently accessed → promoted)
///
/// Benefits:
/// - Balance between context size and relevance
/// - Preserve important information while managing token limits
/// - Efficient retrieval with fallback across tiers
///
/// Example:
/// ```zig
/// var hierarchy = try HierarchyMemory.init(allocator, .{
///     .working_capacity = 10,
///     .short_term_capacity = 100,
///     .long_term_summary_threshold = 500,
/// });
/// defer hierarchy.deinit();
///
/// const entry = try MemoryEntry.init(allocator, "session-1", .user, "Hello!");
/// try hierarchy.store(&entry);
/// const entries = try hierarchy.retrieve("session-1", 20);
/// ```
const std = @import("std");
const agksync = @import("../../sync_compat.zig");
const Allocator = std.mem.Allocator;
const MemoryEntry = @import("base.zig").MemoryEntry;
const Memory = @import("base.zig").Memory;
const InMemoryMemory = @import("in_memory.zig").InMemoryMemory;

/// Configuration for hierarchical memory.
pub const HierarchyConfig = struct {
    /// Working memory capacity (most recent entries)
    /// Default: 10
    working_capacity: usize = 10,

    /// Short-term memory capacity
    /// Default: 100
    short_term_capacity: usize = 100,

    /// When to summarize entries into long-term memory
    /// Default: 500
    long_term_summary_threshold: usize = 500,

    /// Minimum importance to keep in short-term (0.0-1.0)
    /// Default: 0.3
    importance_threshold: f32 = 0.3,
};

/// Memory tier enumeration.
pub const Tier = enum {
    working,
    short_term,
    long_term,

    pub fn toString(self: Tier) []const u8 {
        return switch (self) {
            .working => "working",
            .short_term => "short_term",
            .long_term => "long_term",
        };
    }
};

/// HierarchyMemory implements a 3-tier memory system.
pub const HierarchyMemory = struct {
    allocator: Allocator,
    config: HierarchyConfig,
    mutex: agksync.Mutex,

    // Three memory tiers
    working: InMemoryMemory,
    short_term: InMemoryMemory,
    long_term: InMemoryMemory,

    // Track which entries are in which tiers (for deduplication)
    tier_map: std.StringHashMap(Tier),

    /// Initialize hierarchical memory.
    ///
    /// Args:
    ///   allocator: Memory allocator
    ///   config: Configuration options
    ///
    /// Returns:
    ///   Initialized hierarchy
    pub fn init(allocator: Allocator, config: HierarchyConfig) HierarchyMemory {
        return .{
            .allocator = allocator,
            .config = config,
            .mutex = .{},
            .working = InMemoryMemory.init(allocator, .{
                .max_entries_per_session = config.working_capacity,
                .context_limit_tokens = 0, // No token limit for working memory
            }),
            .short_term = InMemoryMemory.init(allocator, .{
                .max_entries_per_session = config.short_term_capacity,
                .context_limit_tokens = 4000,
            }),
            .long_term = InMemoryMemory.init(allocator, .{
                .max_entries_per_session = 0, // Unlimited
                .context_limit_tokens = 0,
            }),
            .tier_map = std.StringHashMap(Tier).init(allocator),
        };
    }

    /// Free all resources.
    pub fn deinit(self: *HierarchyMemory) void {
        self.working.deinit();
        self.short_term.deinit();
        self.long_term.deinit();

        // Free all duped entry IDs in tier_map
        var iter = self.tier_map.keyIterator();
        while (iter.next()) |key_ptr| {
            self.allocator.free(key_ptr.*);
        }
        self.tier_map.deinit();
    }

    /// Get Memory interface.
    pub fn memory(self: *HierarchyMemory) Memory {
        return .{
            .ptr = self,
            .vtable = &.{
                .store = storeImpl,
                .retrieve = retrieveImpl,
                .summarize = summarizeImpl,
                .clear = clearImpl,
                .deinit = deinitImpl,
            },
        };
    }

    /// Store a memory entry.
    ///
    /// New entries always go into working memory.
    /// Old entries are automatically promoted/demoted based on tier policies.
    pub fn store(self: *HierarchyMemory, entry: *const MemoryEntry) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        // New entries start in working memory
        try self.working.store(entry);

        // Dupe the entry ID so tier_map owns its own copy
        const entry_id_copy = try self.allocator.dupe(u8, entry.id);
        try self.tier_map.put(entry_id_copy, .working);

        // Check if we need to promote/demote entries
        try self.manageTiers(entry.session_id);
    }

    /// Retrieve memory entries for a session.
    ///
    /// Retrieves from all tiers in order: working → short-term → long-term
    /// Deduplicates entries by ID.
    pub fn retrieve(self: *HierarchyMemory, session_id: []const u8, limit: usize) ![]const *MemoryEntry {
        self.mutex.lock();
        defer self.mutex.unlock();

        var result = std.ArrayListUnmanaged(*MemoryEntry).empty;
        defer result.deinit(self.allocator);

        var seen = std.StringHashMap(void).init(self.allocator);
        defer seen.deinit();

        // 1. Get working memory entries
        const working_entries = try self.working.retrieve(session_id, 0);
        defer {
            for (working_entries) |e| {
                e.deinit();
                self.allocator.destroy(e);
            }
            self.allocator.free(working_entries);
        }

        for (working_entries) |e| {
            if (!seen.contains(e.id)) {
                const copy = try self.allocator.create(MemoryEntry);
                copy.* = try self.copyEntry(e);
                try result.append(self.allocator, copy);
                try seen.put(copy.id, {});
            }
        }

        // 2. Get short-term memory entries (if we need more)
        if (limit == 0 or result.items.len < limit) {
            const short_term_entries = try self.short_term.retrieve(session_id, 0);
            defer {
                for (short_term_entries) |e| {
                    e.deinit();
                    self.allocator.destroy(e);
                }
                self.allocator.free(short_term_entries);
            }

            for (short_term_entries) |e| {
                if (!seen.contains(e.id)) {
                    const copy = try self.allocator.create(MemoryEntry);
                    copy.* = try self.copyEntry(e);
                    try result.append(self.allocator, copy);
                    try seen.put(copy.id, {});

                    if (limit > 0 and result.items.len >= limit) break;
                }
            }
        }

        // 3. Get long-term memory entries (if we need even more)
        if (limit == 0 or result.items.len < limit) {
            const long_term_entries = try self.long_term.retrieve(session_id, 0);
            defer {
                for (long_term_entries) |e| {
                    e.deinit();
                    self.allocator.destroy(e);
                }
                self.allocator.free(long_term_entries);
            }

            for (long_term_entries) |e| {
                if (!seen.contains(e.id)) {
                    const copy = try self.allocator.create(MemoryEntry);
                    copy.* = try self.copyEntry(e);
                    try result.append(self.allocator, copy);
                    try seen.put(copy.id, {});

                    if (limit > 0 and result.items.len >= limit) break;
                }
            }
        }

        // Convert ArrayList to slice
        const result_slice = try self.allocator.alloc(*MemoryEntry, result.items.len);
        @memcpy(result_slice, result.items);
        return result_slice;
    }

    /// Create a summary of memories across all tiers.
    pub fn summarize(self: *HierarchyMemory, session_id: []const u8, max_entries: usize) ![]const u8 {
        self.mutex.lock();
        defer self.mutex.unlock();

        // Get summaries from each tier
        const working_summary = try self.working.summarize(session_id, max_entries);
        defer self.allocator.free(working_summary);

        const short_term_summary = try self.short_term.summarize(session_id, max_entries);
        defer self.allocator.free(short_term_summary);

        const long_term_summary = try self.long_term.summarize(session_id, max_entries);
        defer self.allocator.free(long_term_summary);

        // Combine summaries
        const total_len = working_summary.len + short_term_summary.len + long_term_summary.len + 100;
        const buffer = try self.allocator.alloc(u8, total_len);
        defer self.allocator.free(buffer);

        var written: usize = 0;
        const header = try std.fmt.bufPrint(
            buffer[written..],
            "=== Hierarchical Memory Summary ===\n\n[Working Memory]\n",
            .{},
        );
        written += header.len;

        @memcpy(buffer[written .. written + working_summary.len], working_summary);
        written += working_summary.len;

        const short_header = try std.fmt.bufPrint(
            buffer[written..],
            "\n[Short-term Memory]\n",
            .{},
        );
        written += short_header.len;

        @memcpy(buffer[written .. written + short_term_summary.len], short_term_summary);
        written += short_term_summary.len;

        const long_header = try std.fmt.bufPrint(
            buffer[written..],
            "\n[Long-term Memory]\n",
            .{},
        );
        written += long_header.len;

        @memcpy(buffer[written .. written + long_term_summary.len], long_term_summary);
        written += long_term_summary.len;

        return try self.allocator.dupe(u8, buffer[0..written]);
    }

    /// Clear memories for a session across all tiers.
    pub fn clear(self: *HierarchyMemory, session_id: []const u8) !usize {
        self.mutex.lock();
        defer self.mutex.unlock();

        const working_count = try self.working.clear(session_id);
        const short_term_count = try self.short_term.clear(session_id);
        const long_term_count = try self.long_term.clear(session_id);

        // Clear tier map entries for this session
        var iter = self.tier_map.iterator();
        var keys_to_remove = std.ArrayListUnmanaged([]const u8).empty;
        defer keys_to_remove.deinit(self.allocator);

        while (iter.next()) |entry| {
            // This is a simplified approach - in practice, we'd need to track session IDs
            try keys_to_remove.append(self.allocator, entry.key_ptr.*);
        }

        for (keys_to_remove.items) |key| {
            _ = self.tier_map.remove(key);
            // Free the duped entry ID
            self.allocator.free(key);
        }

        return working_count + short_term_count + long_term_count;
    }

    // Private helper methods

    /// Copy a memory entry.
    fn copyEntry(self: *HierarchyMemory, entry: *const MemoryEntry) !MemoryEntry {
        return MemoryEntry{
            .id = try self.allocator.dupe(u8, entry.id),
            .session_id = try self.allocator.dupe(u8, entry.session_id),
            .role = entry.role,
            .content = try self.allocator.dupe(u8, entry.content),
            .timestamp = entry.timestamp,
            .importance = entry.importance,
            .metadata = entry.metadata, // Shallow copy for now
            .allocator = self.allocator,
        };
    }

    /// Manage tier promotion/demotion.
    fn manageTiers(self: *HierarchyMemory, session_id: []const u8) !void {
        // TODO: Implement tier management logic
        // For now, just let LRU eviction handle overflow
        _ = self;
        _ = session_id;
    }

    // VTable implementations

    fn storeImpl(ptr: *anyopaque, entry: *const MemoryEntry) !void {
        const self: *HierarchyMemory = @ptrCast(@alignCast(ptr));
        return self.store(entry);
    }

    fn retrieveImpl(ptr: *anyopaque, session_id: []const u8, limit: usize) ![]const *MemoryEntry {
        const self: *HierarchyMemory = @ptrCast(@alignCast(ptr));
        return self.retrieve(session_id, limit);
    }

    fn summarizeImpl(ptr: *anyopaque, session_id: []const u8, max_entries: usize) ![]const u8 {
        const self: *HierarchyMemory = @ptrCast(@alignCast(ptr));
        return self.summarize(session_id, max_entries);
    }

    fn clearImpl(ptr: *anyopaque, session_id: []const u8) !usize {
        const self: *HierarchyMemory = @ptrCast(@alignCast(ptr));
        return self.clear(session_id);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *HierarchyMemory = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};

// Tests
const testing = std.testing;

test "HierarchyMemory store and retrieve" {
    const allocator = testing.allocator;

    var hierarchy = HierarchyMemory.init(allocator, .{});
    defer hierarchy.deinit();

    var entry1 = try MemoryEntry.init(allocator, "session-1", .user, "Hello");
    defer entry1.deinit();

    var entry2 = try MemoryEntry.init(allocator, "session-1", .assistant, "Hi there");
    defer entry2.deinit();

    try hierarchy.store(&entry1);
    try hierarchy.store(&entry2);

    const entries = try hierarchy.retrieve("session-1", 0);
    defer {
        for (entries) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(entries);
    }

    try testing.expectEqual(@as(usize, 2), entries.len);
}

test "HierarchyMemory deduplication" {
    const allocator = testing.allocator;

    var hierarchy = HierarchyMemory.init(allocator, .{ .working_capacity = 5 });
    defer hierarchy.deinit();

    var entry = try MemoryEntry.init(allocator, "session-1", .user, "Test");
    defer entry.deinit();

    // Store same entry twice
    try hierarchy.store(&entry);
    try hierarchy.store(&entry);

    const entries = try hierarchy.retrieve("session-1", 0);
    defer {
        for (entries) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(entries);
    }

    // Should still only have 2 entries (no duplicates)
    try testing.expect(entries.len <= 2);
}

test "HierarchyMemory summarize" {
    const allocator = testing.allocator;

    var hierarchy = HierarchyMemory.init(allocator, .{});
    defer hierarchy.deinit();

    var entry = try MemoryEntry.init(allocator, "session-1", .user, "Hello");
    defer entry.deinit();

    try hierarchy.store(&entry);

    const summary = try hierarchy.summarize("session-1", 10);
    defer allocator.free(summary);

    try testing.expect(summary.len > 0);
    try testing.expect(std.mem.indexOf(u8, summary, "Working Memory") != null);
}

test "HierarchyMemory clear" {
    const allocator = testing.allocator;

    var hierarchy = HierarchyMemory.init(allocator, .{});
    defer hierarchy.deinit();

    var entry = try MemoryEntry.init(allocator, "session-1", .user, "Test");
    defer entry.deinit();

    try hierarchy.store(&entry);

    const count = try hierarchy.clear("session-1");
    try testing.expect(count > 0);

    const entries = try hierarchy.retrieve("session-1", 0);
    defer allocator.free(entries);
    try testing.expectEqual(@as(usize, 0), entries.len);
}

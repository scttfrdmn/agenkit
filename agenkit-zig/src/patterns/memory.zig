/// Memory Hierarchy Pattern - Multi-tier Agent Memory
///
/// Provides a three-tier memory system for agents:
/// - Working Memory: Current conversation context (fast, small, in-memory)
/// - Short-Term Memory: Recent sessions (medium, TTL-based, recency retrieval)
/// - Long-Term Memory: Persistent facts (large, semantic retrieval, importance-based)
///
/// # Key Concepts
///
/// - **Working Memory**: Current conversation context (FIFO eviction)
/// - **Short-Term Memory**: Recent sessions with TTL expiration
/// - **Long-Term Memory**: Important facts with semantic search
/// - **Automatic Promotion**: Important memories move between tiers
/// - **Intelligent Retrieval**: Search across tiers with relevance ranking
///
/// # Use Cases
///
/// - Long-running conversational agents
/// - Personalization and user preferences
/// - Context-aware agents with limited context windows
/// - Multi-session continuity
/// - Learning and adaptation
///
/// # Example
///
/// ```zig
/// const std = @import("std");
/// const agenkit = @import("agenkit");
///
/// pub fn main() !void {
///     var gpa = std.heap.DebugAllocator(.{}){};
///     defer _ = gpa.deinit();
///     const allocator = gpa.allocator();
///
///     var wm = try agenkit.patterns.WorkingMemory.init(allocator, 10);
///     defer wm.deinit();
///
///     var stm = try agenkit.patterns.ShortTermMemory.init(allocator, 100, 3600);
///     defer stm.deinit();
///
///     var ltm = try agenkit.patterns.LongTermMemory.init(allocator, 0.7);
///     defer ltm.deinit();
///
///     var hierarchy = try agenkit.patterns.MemoryHierarchy.init(allocator, &wm, &stm, &ltm);
///     defer hierarchy.deinit();
///
///     const id = try hierarchy.store("User prefers Python", null, 0.8, "");
///     const results = try hierarchy.retrieve(allocator, "preferences", 5, null);
///     defer {
///         for (results.items) |*entry| {
///             entry.deinit();
///         }
///         results.deinit(allocator);
///     }
/// }
/// ```
const std = @import("std");
const ioc = @import("../io_compat.zig");
const agktime = @import("../time_compat.zig");
const Allocator = std.mem.Allocator;
const AgentError = @import("../agent.zig").AgentError;

/// Memory entry representing a single memory across all tiers
pub const MemoryEntry = struct {
    id: []const u8,
    content: []const u8,
    metadata: std.StringHashMap([]const u8),
    timestamp: i64,
    access_count: usize,
    last_accessed: ?i64,
    importance: f64,
    session_id: []const u8,
    allocator: Allocator,

    pub fn init(
        allocator: Allocator,
        content: []const u8,
        metadata: ?std.StringHashMap([]const u8),
        importance: f64,
        session_id: []const u8,
    ) !MemoryEntry {
        // Generate UUID-like ID
        var id_buf: [36]u8 = undefined;
        const id_str = std.fmt.bufPrint(&id_buf, "{x:0>32}", .{ioc.randomInt(u128)}) catch unreachable;

        const meta = if (metadata) |m| blk: {
            var new_map = std.StringHashMap([]const u8).init(allocator);
            var iter = m.iterator();
            while (iter.next()) |entry| {
                const key = try allocator.dupe(u8, entry.key_ptr.*);
                const val = try allocator.dupe(u8, entry.value_ptr.*);
                try new_map.put(key, val);
            }
            break :blk new_map;
        } else std.StringHashMap([]const u8).init(allocator);

        return MemoryEntry{
            .id = try allocator.dupe(u8, id_str),
            .content = try allocator.dupe(u8, content),
            .metadata = meta,
            .timestamp = agktime.timestamp(),
            .access_count = 0,
            .last_accessed = null,
            .importance = importance,
            .session_id = try allocator.dupe(u8, session_id),
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *MemoryEntry) void {
        self.allocator.free(self.id);
        self.allocator.free(self.content);
        self.allocator.free(self.session_id);

        var iter = self.metadata.iterator();
        while (iter.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            self.allocator.free(entry.value_ptr.*);
        }
        self.metadata.deinit();
    }

    /// Clone this entry for storage in another tier
    pub fn clone(self: *const MemoryEntry) !MemoryEntry {
        var new_metadata = std.StringHashMap([]const u8).init(self.allocator);
        var iter = self.metadata.iterator();
        while (iter.next()) |entry| {
            const key = try self.allocator.dupe(u8, entry.key_ptr.*);
            const val = try self.allocator.dupe(u8, entry.value_ptr.*);
            try new_metadata.put(key, val);
        }

        return MemoryEntry{
            .id = try self.allocator.dupe(u8, self.id),
            .content = try self.allocator.dupe(u8, self.content),
            .metadata = new_metadata,
            .timestamp = self.timestamp,
            .access_count = self.access_count,
            .last_accessed = self.last_accessed,
            .importance = self.importance,
            .session_id = try self.allocator.dupe(u8, self.session_id),
            .allocator = self.allocator,
        };
    }

    /// Update access tracking
    pub fn markAccessed(self: *MemoryEntry) void {
        self.access_count += 1;
        self.last_accessed = agktime.timestamp();
    }
};

/// Working memory - current conversation context
///
/// Characteristics:
/// - Fast: O(1) append, O(n) retrieval
/// - Small capacity: 10-20 messages typically
/// - FIFO eviction: Oldest messages removed first
/// - No persistence: Exists only in memory
pub const WorkingMemory = struct {
    allocator: Allocator,
    max_messages: usize,
    messages: std.ArrayList(MemoryEntry),

    pub fn init(allocator: Allocator, max_messages: usize) !WorkingMemory {
        if (max_messages < 1) {
            return AgentError.InvalidInput;
        }

        return WorkingMemory{
            .allocator = allocator,
            .max_messages = max_messages,
            .messages = std.ArrayList(MemoryEntry).empty,
        };
    }

    pub fn deinit(self: *WorkingMemory) void {
        for (self.messages.items) |*entry| {
            entry.deinit();
        }
        self.messages.deinit(self.allocator);
    }

    /// Store a memory entry in working memory
    pub fn store(self: *WorkingMemory, entry: MemoryEntry) !void {
        try self.messages.append(self.allocator, entry);

        // FIFO eviction if over capacity
        if (self.messages.items.len > self.max_messages) {
            var first = self.messages.orderedRemove(0);
            first.deinit();
        }
    }

    /// Retrieve recent messages from working memory
    pub fn retrieve(self: *WorkingMemory, allocator: Allocator, query: []const u8, limit: usize) !std.ArrayList(MemoryEntry) {
        _ = query; // Working memory returns all recent messages

        var results = std.ArrayList(MemoryEntry).empty;

        const start = if (self.messages.items.len > limit)
            self.messages.items.len - limit
        else
            0;

        for (self.messages.items[start..]) |*entry| {
            const cloned = try entry.clone();
            try results.append(allocator, cloned);
        }

        return results;
    }

    /// Delete a memory entry from working memory
    pub fn delete(self: *WorkingMemory, entry_id: []const u8) !void {
        var i: usize = 0;
        while (i < self.messages.items.len) {
            if (std.mem.eql(u8, self.messages.items[i].id, entry_id)) {
                var removed = self.messages.orderedRemove(i);
                removed.deinit();
                return;
            }
            i += 1;
        }
    }

    /// Get all working memory entries
    pub fn getAll(self: *const WorkingMemory, allocator: Allocator) !std.ArrayList(MemoryEntry) {
        var results = std.ArrayList(MemoryEntry).empty;
        for (self.messages.items) |*entry| {
            const cloned = try entry.clone();
            try results.append(allocator, cloned);
        }
        return results;
    }

    /// Clear all working memory
    pub fn clear(self: *WorkingMemory) void {
        for (self.messages.items) |*entry| {
            entry.deinit();
        }
        self.messages.clearRetainingCapacity();
    }

    /// Get length of working memory
    pub fn length(self: *const WorkingMemory) usize {
        return self.messages.items.len;
    }
};

/// Short-term memory - recent session memory with TTL-based expiration
///
/// Characteristics:
/// - Medium capacity: 100-1000 messages typically
/// - TTL-based: Entries expire after time period
/// - Recency retrieval: Most recent first
/// - LRU eviction: Least recently used removed first
pub const ShortTermMemory = struct {
    allocator: Allocator,
    max_messages: usize,
    ttl_seconds: i64,
    messages: std.ArrayList(MemoryEntry),

    pub fn init(allocator: Allocator, max_messages: usize, ttl_seconds: i64) !ShortTermMemory {
        if (max_messages < 1) {
            return AgentError.InvalidInput;
        }
        if (ttl_seconds < 1) {
            return AgentError.InvalidInput;
        }

        return ShortTermMemory{
            .allocator = allocator,
            .max_messages = max_messages,
            .ttl_seconds = ttl_seconds,
            .messages = std.ArrayList(MemoryEntry).empty,
        };
    }

    pub fn deinit(self: *ShortTermMemory) void {
        for (self.messages.items) |*entry| {
            entry.deinit();
        }
        self.messages.deinit(self.allocator);
    }

    /// Clean expired entries
    fn cleanExpired(self: *ShortTermMemory) void {
        const now = agktime.timestamp();
        var i: usize = 0;
        while (i < self.messages.items.len) {
            const age = now - self.messages.items[i].timestamp;
            if (age >= self.ttl_seconds) {
                var removed = self.messages.orderedRemove(i);
                removed.deinit();
            } else {
                i += 1;
            }
        }
    }

    /// Store a memory entry in short-term memory
    pub fn store(self: *ShortTermMemory, entry: MemoryEntry) !void {
        self.cleanExpired();

        try self.messages.append(self.allocator, entry);

        // LRU eviction if over capacity
        if (self.messages.items.len > self.max_messages) {
            // Sort by last access time (least recently used first)
            std.mem.sort(MemoryEntry, self.messages.items, {}, struct {
                fn lessThan(_: void, a: MemoryEntry, b: MemoryEntry) bool {
                    const a_time = a.last_accessed orelse a.timestamp;
                    const b_time = b.last_accessed orelse b.timestamp;
                    return a_time < b_time;
                }
            }.lessThan);

            var removed = self.messages.orderedRemove(0);
            removed.deinit();
        }
    }

    /// Retrieve recent messages from short-term memory
    pub fn retrieve(self: *ShortTermMemory, allocator: Allocator, query: []const u8, limit: usize) !std.ArrayList(MemoryEntry) {
        _ = query; // Short-term returns by recency
        self.cleanExpired();

        // Sort by timestamp (most recent first)
        var sorted = std.ArrayList(MemoryEntry).empty;
        for (self.messages.items) |*entry| {
            const cloned = try entry.clone();
            try sorted.append(allocator, cloned);
        }

        std.mem.sort(MemoryEntry, sorted.items, {}, struct {
            fn lessThan(_: void, a: MemoryEntry, b: MemoryEntry) bool {
                return a.timestamp > b.timestamp;
            }
        }.lessThan);

        // Take top limit
        var results = std.ArrayList(MemoryEntry).empty;
        const count = @min(sorted.items.len, limit);
        for (sorted.items[0..count]) |*entry| {
            // Mark accessed in original
            for (self.messages.items) |*orig| {
                if (std.mem.eql(u8, orig.id, entry.id)) {
                    orig.markAccessed();
                    break;
                }
            }
            // Clone for results
            const cloned = try entry.clone();
            try results.append(allocator, cloned);
        }

        // Clean up sorted list
        for (sorted.items) |*entry| {
            entry.deinit();
        }
        sorted.deinit(allocator);

        return results;
    }

    /// Delete a memory entry from short-term memory
    pub fn delete(self: *ShortTermMemory, entry_id: []const u8) !void {
        var i: usize = 0;
        while (i < self.messages.items.len) {
            if (std.mem.eql(u8, self.messages.items[i].id, entry_id)) {
                var removed = self.messages.orderedRemove(i);
                removed.deinit();
                return;
            }
            i += 1;
        }
    }

    /// Get length of short-term memory
    pub fn length(self: *const ShortTermMemory) usize {
        return self.messages.items.len;
    }
};

/// Long-term memory - persistent semantic memory with importance-based retention
///
/// Characteristics:
/// - Large capacity: Unlimited (depends on storage backend)
/// - Semantic retrieval: By relevance/similarity
/// - Persistent: Survives restarts
/// - Importance-based: Only important memories stored
pub const LongTermMemory = struct {
    allocator: Allocator,
    storage: std.StringHashMap(MemoryEntry),
    min_importance: f64,

    pub fn init(allocator: Allocator, min_importance: f64) !LongTermMemory {
        if (min_importance < 0.0 or min_importance > 1.0) {
            return AgentError.InvalidInput;
        }

        return LongTermMemory{
            .allocator = allocator,
            .storage = std.StringHashMap(MemoryEntry).init(allocator),
            .min_importance = min_importance,
        };
    }

    pub fn deinit(self: *LongTermMemory) void {
        var iter = self.storage.iterator();
        while (iter.next()) |kv| {
            self.allocator.free(kv.key_ptr.*);
            var entry = kv.value_ptr.*;
            entry.deinit();
        }
        self.storage.deinit();
    }

    /// Store a memory entry in long-term memory
    pub fn store(self: *LongTermMemory, entry: MemoryEntry) !void {
        // Check importance threshold
        if (entry.importance < self.min_importance) {
            return; // Not important enough
        }

        const key = try self.allocator.dupe(u8, entry.id);
        try self.storage.put(key, entry);
    }

    /// Retrieve relevant memories from long-term memory
    pub fn retrieve(self: *LongTermMemory, allocator: Allocator, query: []const u8, limit: usize) !std.ArrayList(MemoryEntry) {
        const ScoredEntry = struct {
            entry: *MemoryEntry,
            score: f64,
        };

        var scored_entries = std.ArrayList(ScoredEntry).empty;
        defer scored_entries.deinit(allocator);

        const query_lower = try std.ascii.allocLowerString(allocator, query);
        defer allocator.free(query_lower);

        var iter = self.storage.valueIterator();
        while (iter.next()) |entry| {
            var score: f64 = 0.0;

            // Keyword match
            const content_lower = try std.ascii.allocLowerString(allocator, entry.content);
            defer allocator.free(content_lower);

            if (std.mem.indexOf(u8, content_lower, query_lower) != null) {
                score += 0.5;
            }

            // Importance weight
            score += entry.importance * 0.3;

            // Recency weight
            const now = agktime.timestamp();
            const age_days: f64 = @as(f64, @floatFromInt(now - entry.timestamp)) / 86400.0;
            const recency_score = @max(0.0, 1.0 - age_days / 365.0);
            score += recency_score * 0.2;

            try scored_entries.append(allocator, .{ .entry = entry, .score = score });
        }

        // Sort by score (descending)
        std.mem.sort(ScoredEntry, scored_entries.items, {}, struct {
            fn lessThan(_: void, a: ScoredEntry, b: ScoredEntry) bool {
                return a.score > b.score;
            }
        }.lessThan);

        // Take top limit and clone
        var results = std.ArrayList(MemoryEntry).empty;
        const count = @min(scored_entries.items.len, limit);
        for (scored_entries.items[0..count]) |scored| {
            // Mark accessed in original
            scored.entry.markAccessed();
            // Clone for results
            const cloned = try scored.entry.clone();
            try results.append(allocator, cloned);
        }

        return results;
    }

    /// Delete a memory entry from long-term memory
    pub fn delete(self: *LongTermMemory, entry_id: []const u8) !void {
        if (self.storage.fetchRemove(entry_id)) |kv| {
            self.allocator.free(kv.key);
            var entry = kv.value;
            entry.deinit();
        }
    }

    /// Get length of long-term memory
    pub fn length(self: *const LongTermMemory) usize {
        return self.storage.count();
    }
};

/// Memory hierarchy - multi-tier memory system for agents
///
/// Manages working, short-term, and long-term memory with automatic
/// promotion and intelligent retrieval across tiers.
pub const MemoryHierarchy = struct {
    allocator: Allocator,
    working: *WorkingMemory,
    short_term: ?*ShortTermMemory,
    long_term: ?*LongTermMemory,

    pub fn init(
        allocator: Allocator,
        working: *WorkingMemory,
        short_term: ?*ShortTermMemory,
        long_term: ?*LongTermMemory,
    ) !MemoryHierarchy {
        return MemoryHierarchy{
            .allocator = allocator,
            .working = working,
            .short_term = short_term,
            .long_term = long_term,
        };
    }

    pub fn deinit(self: *MemoryHierarchy) void {
        _ = self;
        // Note: Individual memory tiers are managed by caller
    }

    /// Store memory across appropriate tiers
    pub fn store(
        self: *MemoryHierarchy,
        content: []const u8,
        metadata: ?std.StringHashMap([]const u8),
        importance: f64,
        session_id: []const u8,
    ) ![]const u8 {
        if (importance < 0.0 or importance > 1.0) {
            return AgentError.InvalidInput;
        }

        // Create entry
        const entry = try MemoryEntry.init(self.allocator, content, metadata, importance, session_id);
        const id = try self.allocator.dupe(u8, entry.id);

        // Store in working memory
        const working_entry = try entry.clone();
        try self.working.store(working_entry);

        // Store in short-term if available
        if (self.short_term) |stm| {
            const st_entry = try entry.clone();
            try stm.store(st_entry);
        }

        // Store in long-term if important enough
        if (self.long_term) |ltm| {
            if (importance >= ltm.min_importance) {
                const lt_entry = try entry.clone();
                try ltm.store(lt_entry);
            }
        }

        // Clean up original entry
        var mutable_entry = entry;
        mutable_entry.deinit();

        return id;
    }

    /// Retrieve memories from hierarchy
    ///
    /// Searches across all enabled tiers and returns deduplicated, ranked results.
    pub fn retrieve(
        self: *MemoryHierarchy,
        allocator: Allocator,
        query: []const u8,
        limit: usize,
        search_tiers: ?[]const []const u8,
    ) !std.ArrayList(MemoryEntry) {
        var all_results = std.ArrayList(MemoryEntry).empty;
        errdefer {
            for (all_results.items) |*entry| {
                entry.deinit();
            }
            all_results.deinit(allocator);
        }

        const tiers = search_tiers orelse &[_][]const u8{ "working", "short_term", "long_term" };

        // Search working memory
        if (containsTier(tiers, "working")) {
            var working_results = try self.working.retrieve(allocator, query, limit);
            defer {
                for (working_results.items) |*entry| {
                    entry.deinit();
                }
                working_results.deinit(allocator);
            }
            for (working_results.items) |*entry| {
                try all_results.append(allocator, try entry.clone());
            }
        }

        // Search short-term memory
        if (self.short_term) |stm| {
            if (containsTier(tiers, "short_term")) {
                var st_results = try stm.retrieve(allocator, query, limit);
                defer {
                    for (st_results.items) |*entry| {
                        entry.deinit();
                    }
                    st_results.deinit(allocator);
                }
                for (st_results.items) |*entry| {
                    try all_results.append(allocator, try entry.clone());
                }
            }
        }

        // Search long-term memory
        if (self.long_term) |ltm| {
            if (containsTier(tiers, "long_term")) {
                var lt_results = try ltm.retrieve(allocator, query, limit);
                defer {
                    for (lt_results.items) |*entry| {
                        entry.deinit();
                    }
                    lt_results.deinit(allocator);
                }
                for (lt_results.items) |*entry| {
                    try all_results.append(allocator, try entry.clone());
                }
            }
        }

        // Deduplicate by ID
        var seen = std.StringHashMap(void).init(allocator);
        defer seen.deinit();

        var unique = std.ArrayList(MemoryEntry).empty;
        for (all_results.items) |*entry| {
            if (!seen.contains(entry.id)) {
                try seen.put(entry.id, {});
                try unique.append(allocator, try entry.clone());
            }
        }

        // Clean up all_results
        for (all_results.items) |*entry| {
            entry.deinit();
        }
        all_results.deinit(allocator);

        // Sort by importance and recency
        std.mem.sort(MemoryEntry, unique.items, {}, struct {
            fn lessThan(_: void, a: MemoryEntry, b: MemoryEntry) bool {
                if (a.importance != b.importance) {
                    return a.importance > b.importance;
                }
                return a.timestamp > b.timestamp;
            }
        }.lessThan);

        // Return top limit
        if (unique.items.len > limit) {
            // Free excess entries
            for (unique.items[limit..]) |*entry| {
                entry.deinit();
            }
            unique.shrinkRetainingCapacity(limit);
        }

        return unique;
    }

    /// Delete memory from all tiers
    pub fn delete(self: *MemoryHierarchy, entry_id: []const u8) !void {
        try self.working.delete(entry_id);

        if (self.short_term) |stm| {
            try stm.delete(entry_id);
        }

        if (self.long_term) |ltm| {
            try ltm.delete(entry_id);
        }
    }

    /// Clear all working memory
    pub fn clearWorking(self: *MemoryHierarchy) void {
        self.working.clear();
    }

    /// Get working memory entries
    pub fn getWorking(self: *MemoryHierarchy, allocator: Allocator) !std.ArrayList(MemoryEntry) {
        return try self.working.getAll(allocator);
    }
};

fn containsTier(tiers: []const []const u8, tier: []const u8) bool {
    for (tiers) |t| {
        if (std.mem.eql(u8, t, tier)) {
            return true;
        }
    }
    return false;
}

// Tests
const testing = std.testing;

test "MemoryEntry creation" {
    const allocator = testing.allocator;

    var entry = try MemoryEntry.init(allocator, "Test content", null, 0.8, "session1");
    defer entry.deinit();

    try testing.expectEqualStrings("Test content", entry.content);
    try testing.expectEqual(@as(f64, 0.8), entry.importance);
    try testing.expectEqualStrings("session1", entry.session_id);
    try testing.expectEqual(@as(usize, 0), entry.access_count);
    try testing.expect(entry.id.len > 0);
}

test "MemoryEntry clone" {
    const allocator = testing.allocator;

    var entry = try MemoryEntry.init(allocator, "Test", null, 0.5, "");
    defer entry.deinit();

    var cloned = try entry.clone();
    defer cloned.deinit();

    try testing.expectEqualStrings(entry.id, cloned.id);
    try testing.expectEqualStrings(entry.content, cloned.content);
}

test "MemoryEntry markAccessed" {
    const allocator = testing.allocator;

    var entry = try MemoryEntry.init(allocator, "Test", null, 0.5, "");
    defer entry.deinit();

    try testing.expectEqual(@as(usize, 0), entry.access_count);
    try testing.expect(entry.last_accessed == null);

    entry.markAccessed();

    try testing.expectEqual(@as(usize, 1), entry.access_count);
    try testing.expect(entry.last_accessed != null);
}

test "WorkingMemory creation" {
    const allocator = testing.allocator;

    var wm = try WorkingMemory.init(allocator, 10);
    defer wm.deinit();

    try testing.expectEqual(@as(usize, 0), wm.length());
}

test "WorkingMemory validation" {
    const allocator = testing.allocator;

    const result = WorkingMemory.init(allocator, 0);
    try testing.expectError(AgentError.InvalidInput, result);
}

test "WorkingMemory store" {
    const allocator = testing.allocator;

    var wm = try WorkingMemory.init(allocator, 10);
    defer wm.deinit();

    const entry = try MemoryEntry.init(allocator, "Test", null, 0.5, "");
    try wm.store(entry);

    try testing.expectEqual(@as(usize, 1), wm.length());
}

test "WorkingMemory FIFO eviction" {
    const allocator = testing.allocator;

    var wm = try WorkingMemory.init(allocator, 3);
    defer wm.deinit();

    // Add 5 entries
    var i: usize = 0;
    while (i < 5) : (i += 1) {
        const content = try std.fmt.allocPrint(allocator, "Entry {d}", .{i});
        defer allocator.free(content);
        const entry = try MemoryEntry.init(allocator, content, null, 0.5, "");
        try wm.store(entry);
    }

    // Should only keep last 3
    try testing.expectEqual(@as(usize, 3), wm.length());

    var all = try wm.getAll(allocator);
    defer {
        for (all.items) |*entry| {
            entry.deinit();
        }
        all.deinit(allocator);
    }

    try testing.expect(std.mem.indexOf(u8, all.items[0].content, "Entry 2") != null);
}

test "WorkingMemory retrieve with limit" {
    const allocator = testing.allocator;

    var wm = try WorkingMemory.init(allocator, 10);
    defer wm.deinit();

    var i: usize = 0;
    while (i < 5) : (i += 1) {
        const content = try std.fmt.allocPrint(allocator, "Entry {d}", .{i});
        defer allocator.free(content);
        const entry = try MemoryEntry.init(allocator, content, null, 0.5, "");
        try wm.store(entry);
    }

    var results = try wm.retrieve(allocator, "", 3);
    defer {
        for (results.items) |*entry| {
            entry.deinit();
        }
        results.deinit(allocator);
    }

    try testing.expectEqual(@as(usize, 3), results.items.len);
}

test "WorkingMemory delete" {
    const allocator = testing.allocator;

    var wm = try WorkingMemory.init(allocator, 10);
    defer wm.deinit();

    const entry = try MemoryEntry.init(allocator, "Test", null, 0.5, "");
    const id = try allocator.dupe(u8, entry.id);
    defer allocator.free(id);

    try wm.store(entry);
    try testing.expectEqual(@as(usize, 1), wm.length());

    try wm.delete(id);
    try testing.expectEqual(@as(usize, 0), wm.length());
}

test "WorkingMemory clear" {
    const allocator = testing.allocator;

    var wm = try WorkingMemory.init(allocator, 10);
    defer wm.deinit();

    var i: usize = 0;
    while (i < 5) : (i += 1) {
        const entry = try MemoryEntry.init(allocator, "Test", null, 0.5, "");
        try wm.store(entry);
    }

    wm.clear();
    try testing.expectEqual(@as(usize, 0), wm.length());
}

test "ShortTermMemory creation" {
    const allocator = testing.allocator;

    var stm = try ShortTermMemory.init(allocator, 100, 3600);
    defer stm.deinit();

    try testing.expectEqual(@as(usize, 0), stm.length());
}

test "ShortTermMemory validation" {
    const allocator = testing.allocator;

    const result1 = ShortTermMemory.init(allocator, 0, 3600);
    try testing.expectError(AgentError.InvalidInput, result1);

    const result2 = ShortTermMemory.init(allocator, 100, 0);
    try testing.expectError(AgentError.InvalidInput, result2);
}

test "ShortTermMemory store and retrieve" {
    const allocator = testing.allocator;

    var stm = try ShortTermMemory.init(allocator, 100, 3600);
    defer stm.deinit();

    const entry = try MemoryEntry.init(allocator, "Test", null, 0.5, "");
    try stm.store(entry);

    try testing.expectEqual(@as(usize, 1), stm.length());

    var results = try stm.retrieve(allocator, "", 10);
    defer {
        for (results.items) |*e| {
            e.deinit();
        }
        results.deinit(allocator);
    }

    try testing.expectEqual(@as(usize, 1), results.items.len);
}

test "LongTermMemory creation" {
    const allocator = testing.allocator;

    var ltm = try LongTermMemory.init(allocator, 0.7);
    defer ltm.deinit();

    try testing.expectEqual(@as(usize, 0), ltm.length());
}

test "LongTermMemory validation" {
    const allocator = testing.allocator;

    const result1 = LongTermMemory.init(allocator, -0.1);
    try testing.expectError(AgentError.InvalidInput, result1);

    const result2 = LongTermMemory.init(allocator, 1.5);
    try testing.expectError(AgentError.InvalidInput, result2);
}

test "LongTermMemory importance threshold" {
    const allocator = testing.allocator;

    var ltm = try LongTermMemory.init(allocator, 0.7);
    defer ltm.deinit();

    // High importance - should store
    const high_entry = try MemoryEntry.init(allocator, "Important", null, 0.8, "");
    try ltm.store(high_entry);
    try testing.expectEqual(@as(usize, 1), ltm.length());

    // Low importance - should not store
    const low_entry = try MemoryEntry.init(allocator, "Not important", null, 0.5, "");
    var mutable_low = low_entry;
    try ltm.store(low_entry);
    try testing.expectEqual(@as(usize, 1), ltm.length());

    // Clean up low entry since it wasn't stored
    mutable_low.deinit();
}

test "LongTermMemory keyword retrieval" {
    const allocator = testing.allocator;

    var ltm = try LongTermMemory.init(allocator, 0.5);
    defer ltm.deinit();

    const entry1 = try MemoryEntry.init(allocator, "User prefers Python", null, 0.8, "");
    const entry2 = try MemoryEntry.init(allocator, "User likes Java", null, 0.7, "");

    try ltm.store(entry1);
    try ltm.store(entry2);

    var results = try ltm.retrieve(allocator, "Python", 10);
    defer {
        for (results.items) |*e| {
            e.deinit();
        }
        results.deinit(allocator);
    }

    try testing.expect(results.items.len > 0);
    try testing.expect(std.mem.indexOf(u8, results.items[0].content, "Python") != null);
}

test "MemoryHierarchy creation" {
    const allocator = testing.allocator;

    var wm = try WorkingMemory.init(allocator, 10);
    defer wm.deinit();

    var stm = try ShortTermMemory.init(allocator, 100, 3600);
    defer stm.deinit();

    var ltm = try LongTermMemory.init(allocator, 0.7);
    defer ltm.deinit();

    var hierarchy = try MemoryHierarchy.init(allocator, &wm, &stm, &ltm);
    defer hierarchy.deinit();

    try testing.expect(hierarchy.working == &wm);
}

test "MemoryHierarchy store all tiers" {
    const allocator = testing.allocator;

    var wm = try WorkingMemory.init(allocator, 10);
    defer wm.deinit();

    var stm = try ShortTermMemory.init(allocator, 100, 3600);
    defer stm.deinit();

    var ltm = try LongTermMemory.init(allocator, 0.7);
    defer ltm.deinit();

    var hierarchy = try MemoryHierarchy.init(allocator, &wm, &stm, &ltm);
    defer hierarchy.deinit();

    const id = try hierarchy.store("Important fact", null, 0.8, "");
    defer allocator.free(id);

    try testing.expect(id.len > 0);
    try testing.expectEqual(@as(usize, 1), wm.length());
    try testing.expectEqual(@as(usize, 1), stm.length());
    try testing.expectEqual(@as(usize, 1), ltm.length());
}

test "MemoryHierarchy store low importance" {
    const allocator = testing.allocator;

    var wm = try WorkingMemory.init(allocator, 10);
    defer wm.deinit();

    var stm = try ShortTermMemory.init(allocator, 100, 3600);
    defer stm.deinit();

    var ltm = try LongTermMemory.init(allocator, 0.7);
    defer ltm.deinit();

    var hierarchy = try MemoryHierarchy.init(allocator, &wm, &stm, &ltm);
    defer hierarchy.deinit();

    const id = try hierarchy.store("Low importance fact", null, 0.5, "");
    defer allocator.free(id);

    // Should be in working and short-term, but not long-term
    try testing.expectEqual(@as(usize, 1), wm.length());
    try testing.expectEqual(@as(usize, 1), stm.length());
    try testing.expectEqual(@as(usize, 0), ltm.length());
}

test "MemoryHierarchy retrieve deduplication" {
    const allocator = testing.allocator;

    var wm = try WorkingMemory.init(allocator, 10);
    defer wm.deinit();

    var stm = try ShortTermMemory.init(allocator, 100, 3600);
    defer stm.deinit();

    var ltm = try LongTermMemory.init(allocator, 0.7);
    defer ltm.deinit();

    var hierarchy = try MemoryHierarchy.init(allocator, &wm, &stm, &ltm);
    defer hierarchy.deinit();

    const id = try hierarchy.store("Test content", null, 0.8, "");
    defer allocator.free(id);

    var results = try hierarchy.retrieve(allocator, "", 10, null);
    defer {
        for (results.items) |*entry| {
            entry.deinit();
        }
        results.deinit(allocator);
    }

    // Should deduplicate (same entry across tiers)
    try testing.expectEqual(@as(usize, 1), results.items.len);
}

test "MemoryHierarchy retrieve specific tiers" {
    const allocator = testing.allocator;

    var wm = try WorkingMemory.init(allocator, 10);
    defer wm.deinit();

    var stm = try ShortTermMemory.init(allocator, 100, 3600);
    defer stm.deinit();

    var ltm = try LongTermMemory.init(allocator, 0.7);
    defer ltm.deinit();

    var hierarchy = try MemoryHierarchy.init(allocator, &wm, &stm, &ltm);
    defer hierarchy.deinit();

    const id = try hierarchy.store("Test", null, 0.8, "");
    defer allocator.free(id);

    const tiers = [_][]const u8{"working"};
    var results = try hierarchy.retrieve(allocator, "", 10, &tiers);
    defer {
        for (results.items) |*entry| {
            entry.deinit();
        }
        results.deinit(allocator);
    }

    try testing.expectEqual(@as(usize, 1), results.items.len);
}

test "MemoryHierarchy delete all tiers" {
    const allocator = testing.allocator;

    var wm = try WorkingMemory.init(allocator, 10);
    defer wm.deinit();

    var stm = try ShortTermMemory.init(allocator, 100, 3600);
    defer stm.deinit();

    var ltm = try LongTermMemory.init(allocator, 0.7);
    defer ltm.deinit();

    var hierarchy = try MemoryHierarchy.init(allocator, &wm, &stm, &ltm);
    defer hierarchy.deinit();

    const id = try hierarchy.store("Test", null, 0.8, "");
    defer allocator.free(id);

    try hierarchy.delete(id);

    try testing.expectEqual(@as(usize, 0), wm.length());
    try testing.expectEqual(@as(usize, 0), stm.length());
    try testing.expectEqual(@as(usize, 0), ltm.length());
}

test "MemoryHierarchy clearWorking" {
    const allocator = testing.allocator;

    var wm = try WorkingMemory.init(allocator, 10);
    defer wm.deinit();

    var hierarchy = try MemoryHierarchy.init(allocator, &wm, null, null);
    defer hierarchy.deinit();

    const id = try hierarchy.store("Test", null, 0.5, "");
    defer allocator.free(id);

    hierarchy.clearWorking();

    var working = try hierarchy.getWorking(allocator);
    defer working.deinit(allocator);

    try testing.expectEqual(@as(usize, 0), working.items.len);
}

test "MemoryHierarchy invalid importance" {
    const allocator = testing.allocator;

    var wm = try WorkingMemory.init(allocator, 10);
    defer wm.deinit();

    var hierarchy = try MemoryHierarchy.init(allocator, &wm, null, null);
    defer hierarchy.deinit();

    const result1 = hierarchy.store("Test", null, -0.1, "");
    try testing.expectError(AgentError.InvalidInput, result1);

    const result2 = hierarchy.store("Test", null, 1.5, "");
    try testing.expectError(AgentError.InvalidInput, result2);
}

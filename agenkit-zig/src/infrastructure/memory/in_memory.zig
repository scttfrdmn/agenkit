/// In-memory storage implementation with LRU eviction.
///
/// InMemoryMemory provides fast, volatile storage for conversational memory:
/// - HashMap-based storage for O(1) access
/// - LRU eviction to manage memory usage
/// - Context limit awareness (token-based)
/// - Thread-safe operations
/// - Session isolation
///
/// Good for:
/// - Testing and development
/// - Short-lived sessions
/// - High-performance applications with memory constraints
///
/// Not suitable for:
/// - Long-term persistence (lost on restart)
/// - Large-scale deployments (no sharing across instances)
///
/// Example:
/// ```zig
/// var memory = InMemoryMemory.init(allocator, .{
///     .max_entries_per_session = 100,
///     .context_limit_tokens = 4000,
/// });
/// defer memory.deinit();
///
/// const entry = try MemoryEntry.init(allocator, "session-1", .user, "Hello!");
/// try memory.store(&entry);
/// const entries = try memory.retrieve("session-1", 10);
/// ```
const std = @import("std");
const Allocator = std.mem.Allocator;
const MemoryEntry = @import("base.zig").MemoryEntry;
const Memory = @import("base.zig").Memory;

/// Configuration for in-memory storage.
pub const InMemoryConfig = struct {
    /// Maximum entries per session (0 = unlimited)
    /// When exceeded, LRU entries are evicted
    /// Default: 100
    max_entries_per_session: usize = 100,

    /// Context limit in tokens (approximate)
    /// Used to estimate when to evict old entries
    /// Default: 4000 (typical for many LLMs)
    context_limit_tokens: usize = 4000,

    /// Average tokens per entry (for estimation)
    /// Default: 50
    avg_tokens_per_entry: usize = 50,
};

/// LRU node for tracking entry access order.
const LRUNode = struct {
    entry_id: []const u8,
    map_key: []const u8,  // The key used in lru_nodes HashMap (for reliable removal)
    evicted: bool,  // Set to true when node is evicted (for deinit to skip)
    prev: ?*LRUNode,
    next: ?*LRUNode,
};

/// InMemoryMemory provides in-memory storage with LRU eviction.
pub const InMemoryMemory = struct {
    allocator: Allocator,
    config: InMemoryConfig,
    mutex: std.Thread.Mutex,

    // Storage: session_id -> list of entries
    entries: std.StringHashMap(std.ArrayList(*MemoryEntry)),

    // LRU tracking: session_id -> LRU list
    lru_heads: std.StringHashMap(*LRUNode),
    lru_tails: std.StringHashMap(*LRUNode),

    // Quick lookup: entry_id -> LRU node
    lru_nodes: std.StringHashMap(*LRUNode),

    /// Initialize in-memory storage.
    ///
    /// Args:
    ///   allocator: Memory allocator
    ///   config: Configuration options
    ///
    /// Returns:
    ///   Initialized storage
    pub fn init(allocator: Allocator, config: InMemoryConfig) InMemoryMemory {
        return .{
            .allocator = allocator,
            .config = config,
            .mutex = .{},
            .entries = std.StringHashMap(std.ArrayList(*MemoryEntry)).init(allocator),
            .lru_heads = std.StringHashMap(*LRUNode).init(allocator),
            .lru_tails = std.StringHashMap(*LRUNode).init(allocator),
            .lru_nodes = std.StringHashMap(*LRUNode).init(allocator),
        };
    }

    /// Free all resources.
    pub fn deinit(self: *InMemoryMemory) void {
        // Free all entries
        var entries_iter = self.entries.iterator();
        while (entries_iter.next()) |kv| {
            // Free the session_id key
            self.allocator.free(kv.key_ptr.*);

            // Free all entries in this session
            for (kv.value_ptr.items) |entry| {
                entry.deinit();
                self.allocator.destroy(entry);
            }
            kv.value_ptr.deinit(self.allocator);
        }
        self.entries.deinit();

        // Free LRU nodes (skip if already evicted)
        var lru_iter = self.lru_nodes.iterator();
        while (lru_iter.next()) |kv| {
            if (!kv.value_ptr.*.evicted) {
                // entry_id and map_key (kv.key_ptr.*) are the same - only free entry_id
                self.allocator.free(kv.value_ptr.*.entry_id);
                self.allocator.destroy(kv.value_ptr.*);
            }
        }
        self.lru_nodes.deinit();
        self.lru_heads.deinit();
        self.lru_tails.deinit();
    }

    /// Get Memory interface.
    pub fn memory(self: *InMemoryMemory) Memory {
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
    pub fn store(self: *InMemoryMemory, entry: *const MemoryEntry) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        // Get or create entry list for session
        // Use getPtr to check if key exists, then use that key for consistency
        var session_key: []const u8 = undefined;
        var entry_list: *std.ArrayList(*MemoryEntry) = undefined;

        if (self.entries.getPtr(entry.session_id)) |existing_list| {
            // Reuse existing session_id key
            var iter = self.entries.iterator();
            while (iter.next()) |kv| {
                if (std.mem.eql(u8, kv.key_ptr.*, entry.session_id)) {
                    session_key = kv.key_ptr.*;
                    break;
                }
            }
            entry_list = existing_list;
        } else {
            // Create new session with duped key
            session_key = try self.allocator.dupe(u8, entry.session_id);
            const new_list = std.ArrayList(*MemoryEntry){};
            try self.entries.put(session_key, new_list);
            entry_list = self.entries.getPtr(session_key).?;
        }

        // Create a copy of the entry
        const entry_copy = try self.allocator.create(MemoryEntry);
        entry_copy.* = try self.copyEntry(entry);

        // Add to session entries
        try entry_list.append(self.allocator, entry_copy);

        // Update LRU tracking
        try self.updateLRU(session_key, entry_copy.id);

        // Check if eviction needed
        if (self.config.max_entries_per_session > 0) {
            while (entry_list.items.len > self.config.max_entries_per_session) {
                try self.evictOldest(session_key);
            }
        }
    }

    /// Retrieve memory entries for a session.
    pub fn retrieve(self: *InMemoryMemory, session_id: []const u8, limit: usize) ![]const *MemoryEntry {
        self.mutex.lock();
        defer self.mutex.unlock();

        const entry_list = self.entries.get(session_id) orelse {
            return &[_]*MemoryEntry{};
        };

        const actual_limit = if (limit > 0 and limit < entry_list.items.len)
            limit
        else
            entry_list.items.len;

        // Return most recent entries
        const result = try self.allocator.alloc(*MemoryEntry, actual_limit);
        const start_idx = entry_list.items.len - actual_limit;

        for (result, 0..) |*item, i| {
            const original = entry_list.items[start_idx + i];
            const entry_copy = try self.allocator.create(MemoryEntry);
            entry_copy.* = try self.copyEntry(original);
            item.* = entry_copy;

            // Update LRU on access
            try self.updateLRU(session_id, entry_copy.id);
        }

        return result;
    }

    /// Create a summary of memories.
    pub fn summarize(self: *InMemoryMemory, session_id: []const u8, max_entries: usize) ![]const u8 {
        self.mutex.lock();
        defer self.mutex.unlock();

        const entry_list = self.entries.get(session_id) orelse {
            return try self.allocator.dupe(u8, "No memories found.");
        };

        const actual_limit = if (max_entries > 0 and max_entries < entry_list.items.len)
            max_entries
        else
            entry_list.items.len;

        // Build summary by calculating size first
        const start_idx = entry_list.items.len - actual_limit;

        // Calculate total size needed
        var total_size: usize = 0;
        total_size += 50; // Header: "Summary of N recent memories:\n\n"

        for (entry_list.items[start_idx..]) |entry| {
            total_size += 10; // "N. [role] " prefix
            total_size += entry.role.toString().len;
            total_size += entry.content.len;
            total_size += 1; // newline
        }

        // Allocate buffer
        const buffer = try self.allocator.alloc(u8, total_size);
        defer self.allocator.free(buffer);

        // Build summary
        var written: usize = 0;
        const header = try std.fmt.bufPrint(
            buffer[written..],
            "Summary of {d} recent memories:\n\n",
            .{actual_limit},
        );
        written += header.len;

        for (entry_list.items[start_idx..], 1..) |entry, i| {
            const line = try std.fmt.bufPrint(
                buffer[written..],
                "{d}. [{s}] {s}\n",
                .{ i, entry.role.toString(), entry.content },
            );
            written += line.len;
        }

        // Return only the written portion (dupe before buffer is freed by defer)
        return try self.allocator.dupe(u8, buffer[0..written]);
    }

    /// Clear memories for a session.
    pub fn clear(self: *InMemoryMemory, session_id: []const u8) !usize {
        self.mutex.lock();
        defer self.mutex.unlock();

        const entry_list_ptr = self.entries.getPtr(session_id) orelse return 0;
        const count = entry_list_ptr.items.len;

        // Find the actual session_id key used in the HashMap
        var session_key: ?[]const u8 = null;
        var iter = self.entries.iterator();
        while (iter.next()) |kv| {
            if (std.mem.eql(u8, kv.key_ptr.*, session_id)) {
                session_key = kv.key_ptr.*;
                break;
            }
        }

        // Free all entries
        for (entry_list_ptr.items) |entry| {
            // Remove from LRU tracking
            if (self.lru_nodes.get(entry.id)) |node| {
                self.removeLRUNode(session_id, node);
                // Remove from HashMap first (using the HashMap key which is node.entry_id)
                _ = self.lru_nodes.remove(node.entry_id);
                // Now free the node and its duped key
                self.allocator.free(node.entry_id);
                self.allocator.destroy(node);
            }

            entry.deinit();
            self.allocator.destroy(entry);
        }

        // Deinit the ArrayList before removing
        entry_list_ptr.deinit(self.allocator);
        _ = self.entries.remove(session_id);
        _ = self.lru_heads.remove(session_id);
        _ = self.lru_tails.remove(session_id);

        // Free the session_id key
        if (session_key) |key| {
            self.allocator.free(key);
        }

        return count;
    }

    // Private helper methods

    /// Copy a memory entry.
    fn copyEntry(self: *InMemoryMemory, entry: *const MemoryEntry) !MemoryEntry {
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

    /// Update LRU tracking when entry is accessed.
    fn updateLRU(self: *InMemoryMemory, session_id: []const u8, entry_id: []const u8) !void {
        // Check if node already exists
        var node: *LRUNode = undefined;

        if (self.lru_nodes.get(entry_id)) |existing_node| {
            node = existing_node;
            // Remove from current position
            self.removeLRUNode(session_id, node);
        } else {
            // Create new node with duped entry_id for HashMap key
            const entry_id_copy = try self.allocator.dupe(u8, entry_id);
            node = try self.allocator.create(LRUNode);
            node.* = .{
                .entry_id = entry_id_copy,  // This IS the HashMap key
                .map_key = entry_id_copy,   // Same pointer - we'll only free once
                .evicted = false,
                .prev = null,
                .next = null,
            };
            // Put with the duped key
            try self.lru_nodes.put(entry_id_copy, node);
        }

        // Add to head (most recently used)
        const head_gop = try self.lru_heads.getOrPut(session_id);
        if (!head_gop.found_existing) {
            // First node in list
            head_gop.value_ptr.* = node;
            try self.lru_tails.put(session_id, node);
        } else {
            // Add before current head
            const old_head = head_gop.value_ptr.*;
            node.next = old_head;
            old_head.prev = node;
            head_gop.value_ptr.* = node;
        }
    }

    /// Remove node from LRU list.
    fn removeLRUNode(self: *InMemoryMemory, session_id: []const u8, node: *LRUNode) void {
        if (node.prev) |prev| {
            prev.next = node.next;
        } else {
            // This was the head
            if (self.lru_heads.getPtr(session_id)) |head_ptr| {
                if (node.next) |next_node| {
                    head_ptr.* = next_node;
                } else {
                    // List is now empty
                    _ = self.lru_heads.remove(session_id);
                }
            }
        }

        if (node.next) |next| {
            next.prev = node.prev;
        } else {
            // This was the tail
            if (self.lru_tails.getPtr(session_id)) |tail_ptr| {
                if (node.prev) |prev_node| {
                    tail_ptr.* = prev_node;
                } else {
                    // List is now empty
                    _ = self.lru_tails.remove(session_id);
                }
            }
        }

        node.prev = null;
        node.next = null;
    }

    /// Evict the oldest (LRU) entry for a session.
    fn evictOldest(self: *InMemoryMemory, session_id: []const u8) !void {
        const tail = self.lru_tails.get(session_id) orelse return;
        const entry_id_to_find = tail.entry_id;
        const map_key = tail.map_key;  // The exact key used in lru_nodes

        // Find and remove entry from list
        if (self.entries.getPtr(session_id)) |entry_list| {
            var i: usize = 0;
            while (i < entry_list.items.len) {
                if (std.mem.eql(u8, entry_list.items[i].id, entry_id_to_find)) {
                    const removed = entry_list.orderedRemove(i);
                    removed.deinit();
                    self.allocator.destroy(removed);
                    break;
                }
                i += 1;
            }
        }

        // Remove LRU node from list structure
        self.removeLRUNode(session_id, tail);

        // Mark as evicted so deinit skips it
        tail.evicted = true;

        // Remove from lru_nodes map
        _ = self.lru_nodes.remove(map_key);

        // Free the node's entry_id (which is the same as map_key - only free once!)
        self.allocator.free(tail.entry_id);
        self.allocator.destroy(tail);
    }

    // VTable implementations

    fn storeImpl(ptr: *anyopaque, entry: *const MemoryEntry) !void {
        const self: *InMemoryMemory = @ptrCast(@alignCast(ptr));
        return self.store(entry);
    }

    fn retrieveImpl(ptr: *anyopaque, session_id: []const u8, limit: usize) ![]const *MemoryEntry {
        const self: *InMemoryMemory = @ptrCast(@alignCast(ptr));
        return self.retrieve(session_id, limit);
    }

    fn summarizeImpl(ptr: *anyopaque, session_id: []const u8, max_entries: usize) ![]const u8 {
        const self: *InMemoryMemory = @ptrCast(@alignCast(ptr));
        return self.summarize(session_id, max_entries);
    }

    fn clearImpl(ptr: *anyopaque, session_id: []const u8) !usize {
        const self: *InMemoryMemory = @ptrCast(@alignCast(ptr));
        return self.clear(session_id);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *InMemoryMemory = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};

// Tests
const testing = std.testing;

test "InMemoryMemory store and retrieve" {
    const allocator = testing.allocator;

    var mem = InMemoryMemory.init(allocator, .{});
    defer mem.deinit();

    var entry1 = try MemoryEntry.init(allocator, "session-1", .user, "Hello");
    defer entry1.deinit();

    var entry2 = try MemoryEntry.init(allocator, "session-1", .assistant, "Hi there");
    defer entry2.deinit();

    try mem.store(&entry1);
    try mem.store(&entry2);

    const entries = try mem.retrieve("session-1", 0);
    defer {
        for (entries) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(entries);
    }

    try testing.expectEqual(@as(usize, 2), entries.len);
}

test "InMemoryMemory LRU eviction" {
    const allocator = testing.allocator;

    var mem = InMemoryMemory.init(allocator, .{ .max_entries_per_session = 3 });
    defer mem.deinit();

    var entry1 = try MemoryEntry.init(allocator, "session-1", .user, "Message 1");
    defer entry1.deinit();

    var entry2 = try MemoryEntry.init(allocator, "session-1", .user, "Message 2");
    defer entry2.deinit();

    var entry3 = try MemoryEntry.init(allocator, "session-1", .user, "Message 3");
    defer entry3.deinit();

    var entry4 = try MemoryEntry.init(allocator, "session-1", .user, "Message 4");
    defer entry4.deinit();

    try mem.store(&entry1);
    try mem.store(&entry2);
    try mem.store(&entry3);
    try mem.store(&entry4);

    const entries = try mem.retrieve("session-1", 0);
    defer {
        for (entries) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(entries);
    }

    // Should have evicted entry1
    try testing.expectEqual(@as(usize, 3), entries.len);
}

test "InMemoryMemory summarize" {
    const allocator = testing.allocator;

    var mem = InMemoryMemory.init(allocator, .{});
    defer mem.deinit();

    var entry1 = try MemoryEntry.init(allocator, "session-1", .user, "Hello");
    defer entry1.deinit();

    var entry2 = try MemoryEntry.init(allocator, "session-1", .assistant, "Hi");
    defer entry2.deinit();

    try mem.store(&entry1);
    try mem.store(&entry2);

    const summary = try mem.summarize("session-1", 10);
    defer allocator.free(summary);

    try testing.expect(summary.len > 0);
    try testing.expect(std.mem.indexOf(u8, summary, "Hello") != null);
    try testing.expect(std.mem.indexOf(u8, summary, "Hi") != null);
}

test "InMemoryMemory clear" {
    const allocator = testing.allocator;

    var mem = InMemoryMemory.init(allocator, .{});
    defer mem.deinit();

    var entry = try MemoryEntry.init(allocator, "session-1", .user, "Test");
    defer entry.deinit();

    try mem.store(&entry);

    const count = try mem.clear("session-1");
    try testing.expectEqual(@as(usize, 1), count);

    const entries = try mem.retrieve("session-1", 0);
    defer allocator.free(entries);
    try testing.expectEqual(@as(usize, 0), entries.len);
}

test "InMemoryMemory session isolation" {
    const allocator = testing.allocator;

    var mem = InMemoryMemory.init(allocator, .{});
    defer mem.deinit();

    var entry1 = try MemoryEntry.init(allocator, "session-1", .user, "Session 1");
    defer entry1.deinit();

    var entry2 = try MemoryEntry.init(allocator, "session-2", .user, "Session 2");
    defer entry2.deinit();

    try mem.store(&entry1);
    try mem.store(&entry2);

    const s1_entries = try mem.retrieve("session-1", 0);
    defer {
        for (s1_entries) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(s1_entries);
    }

    const s2_entries = try mem.retrieve("session-2", 0);
    defer {
        for (s2_entries) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(s2_entries);
    }

    try testing.expectEqual(@as(usize, 1), s1_entries.len);
    try testing.expectEqual(@as(usize, 1), s2_entries.len);
    try testing.expectEqualStrings("Session 1", s1_entries[0].content);
    try testing.expectEqualStrings("Session 2", s2_entries[0].content);
}

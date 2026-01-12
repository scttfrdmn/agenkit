/// Caching middleware with LRU eviction and TTL expiration
///
/// The caching middleware reduces latency and cost by caching agent responses.
/// It implements:
/// - LRU (Least Recently Used) eviction when cache is full
/// - TTL (Time To Live) based expiration with automatic cleanup
/// - Cache invalidation (specific entries or entire cache)
/// - Thread-safe operations with std.Thread.RwLock
/// - Comprehensive metrics (hits, misses, hit rate, evictions)
///
/// Example:
/// ```zig
/// const config = CachingConfig{
///     .max_cache_size = 1000,
///     .default_ttl_ms = 300000,  // 5 minutes
/// };
///
/// var caching_agent = try CachingDecorator.init(allocator, base_agent, config);
/// defer caching_agent.deinit();
///
/// const result = try caching_agent.agent().process(message);
/// const metrics = caching_agent.metrics();
/// ```
const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;

/// Configuration for caching behavior
pub const CachingConfig = struct {
    /// Maximum number of entries in cache
    /// Default: 1000
    max_cache_size: u32 = 1000,

    /// Time-to-live for cache entries (milliseconds)
    /// Default: 300000ms (5 minutes)
    default_ttl_ms: u64 = 300000,

    /// Validate configuration
    pub fn validate(self: CachingConfig) !void {
        if (self.max_cache_size < 1) {
            return error.InvalidConfig;
        }
        if (self.default_ttl_ms == 0) {
            return error.InvalidConfig;
        }
    }
};

/// Cache entry with expiration and LRU tracking
const CacheEntry = struct {
    response: Message,
    expires_at_ms: i64,
    created_at_ms: i64,
    last_access_ms: i64, // For LRU tracking

    fn isExpired(self: *const CacheEntry) bool {
        return std.time.milliTimestamp() >= self.expires_at_ms;
    }
};

/// Metrics tracked by caching middleware
pub const CachingMetrics = struct {
    /// Total number of requests
    total_requests: u64 = 0,

    /// Number of cache hits
    cache_hits: u64 = 0,

    /// Number of cache misses
    cache_misses: u64 = 0,

    /// Number of evictions (LRU + expired)
    evictions: u64 = 0,

    /// Number of invalidations
    invalidations: u64 = 0,

    /// Current cache size
    current_size: u64 = 0,

    /// Cache hit rate (percentage)
    pub fn hitRate(self: *const CachingMetrics) ?f64 {
        if (self.total_requests == 0) return null;
        return (@as(f64, @floatFromInt(self.cache_hits)) / @as(f64, @floatFromInt(self.total_requests))) * 100.0;
    }

    /// Cache miss rate (percentage)
    pub fn missRate(self: *const CachingMetrics) ?f64 {
        if (self.total_requests == 0) return null;
        return (@as(f64, @floatFromInt(self.cache_misses)) / @as(f64, @floatFromInt(self.total_requests))) * 100.0;
    }

    /// Create a snapshot of metrics
    pub fn snapshot(self: *const CachingMetrics) CachingMetrics {
        return CachingMetrics{
            .total_requests = self.total_requests,
            .cache_hits = self.cache_hits,
            .cache_misses = self.cache_misses,
            .evictions = self.evictions,
            .invalidations = self.invalidations,
            .current_size = self.current_size,
        };
    }
};

/// Caching decorator - wraps an agent with caching
pub const CachingDecorator = struct {
    allocator: Allocator,
    inner_agent: Agent,
    config: CachingConfig,
    metrics_data: CachingMetrics,
    cache: std.StringHashMap(CacheEntry),
    rwlock: std.Thread.RwLock,
    cleanup_counter: u64,

    pub fn init(allocator: Allocator, inner_agent: Agent, config: CachingConfig) !*CachingDecorator {
        // Validate configuration
        try config.validate();

        const self = try allocator.create(CachingDecorator);
        self.* = CachingDecorator{
            .allocator = allocator,
            .inner_agent = inner_agent,
            .config = config,
            .metrics_data = CachingMetrics{},
            .cache = std.StringHashMap(CacheEntry).init(allocator),
            .rwlock = std.Thread.RwLock{},
            .cleanup_counter = 0,
        };
        return self;
    }

    pub fn deinit(self: *CachingDecorator) void {
        // Clean up cache entries
        var iter = self.cache.iterator();
        while (iter.next()) |entry| {
            // Free the key (owned by hashmap)
            self.allocator.free(entry.key_ptr.*);
            // Response message is owned by cache, deinit it
            entry.value_ptr.response.deinit();
        }
        self.cache.deinit();
    }

    pub fn agent(self: *CachingDecorator) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
            },
        };
    }

    /// Get current metrics (thread-safe)
    pub fn metrics(self: *CachingDecorator) CachingMetrics {
        self.rwlock.lockShared();
        defer self.rwlock.unlockShared();
        return self.metrics_data.snapshot();
    }

    /// Generate cache key from message
    fn generateCacheKey(self: *CachingDecorator, message: Message) ![]const u8 {
        // Hash role + content + metadata
        var hasher = std.crypto.hash.sha2.Sha256.init(.{});

        // Add role
        const role_str = @tagName(message.role);
        hasher.update(role_str);

        // Add content
        const content_str = message.content();
        hasher.update(content_str);

        // Add metadata (simplified: just hash keys and values)
        var meta_iter = message.metadata.iterator();
        while (meta_iter.next()) |entry| {
            hasher.update(entry.key_ptr.*);
            hasher.update(entry.value_ptr.*);
        }

        var hash_bytes: [32]u8 = undefined;
        hasher.final(&hash_bytes);

        // Convert to hex string
        const key = try self.allocator.alloc(u8, 64); // 32 bytes * 2 hex chars
        _ = std.fmt.bufPrint(key, "{s}", .{std.fmt.fmtSliceHexLower(&hash_bytes)}) catch unreachable;
        return key;
    }

    /// Cleanup expired entries
    fn cleanupExpired(self: *CachingDecorator) void {
        var keys_to_remove = std.ArrayList([]const u8).init(self.allocator);
        defer keys_to_remove.deinit();

        // Find expired entries
        var iter = self.cache.iterator();
        while (iter.next()) |entry| {
            if (entry.value_ptr.isExpired()) {
                keys_to_remove.append(entry.key_ptr.*) catch continue;
            }
        }

        // Remove expired entries
        for (keys_to_remove.items) |key| {
            if (self.cache.fetchRemove(key)) |kv| {
                self.allocator.free(kv.key);
                kv.value.response.deinit();
                self.metrics_data.evictions += 1;
            }
        }

        if (keys_to_remove.items.len > 0) {
            self.metrics_data.current_size = self.cache.count();
        }
    }

    /// Evict LRU entry when cache is full
    fn evictLRU(self: *CachingDecorator) void {
        if (self.cache.count() >= self.config.max_cache_size) {
            // Find oldest entry (smallest last_access_ms)
            var oldest_key: ?[]const u8 = null;
            var oldest_time: i64 = std.math.maxInt(i64);

            var iter = self.cache.iterator();
            while (iter.next()) |entry| {
                if (entry.value_ptr.last_access_ms < oldest_time) {
                    oldest_time = entry.value_ptr.last_access_ms;
                    oldest_key = entry.key_ptr.*;
                }
            }

            // Remove oldest entry
            if (oldest_key) |key| {
                if (self.cache.fetchRemove(key)) |kv| {
                    self.allocator.free(kv.key);
                    kv.value.response.deinit();
                    self.metrics_data.evictions += 1;
                    self.metrics_data.current_size = self.cache.count();
                }
            }
        }
    }

    /// Invalidate cache (entire cache or specific message)
    pub fn invalidate(self: *CachingDecorator, message: ?Message) !void {
        self.rwlock.lock();
        defer self.rwlock.unlock();

        if (message) |msg| {
            // Invalidate specific entry
            const key = try self.generateCacheKey(msg);
            defer self.allocator.free(key);

            if (self.cache.fetchRemove(key)) |kv| {
                self.allocator.free(kv.key);
                kv.value.response.deinit();
                self.metrics_data.invalidations += 1;
                self.metrics_data.current_size = self.cache.count();
            }
        } else {
            // Invalidate entire cache
            var count: u64 = 0;
            var iter = self.cache.iterator();
            while (iter.next()) |entry| {
                self.allocator.free(entry.key_ptr.*);
                entry.value_ptr.response.deinit();
                count += 1;
            }
            self.cache.clearRetainingCapacity();
            self.metrics_data.invalidations += count;
            self.metrics_data.current_size = 0;
        }
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *CachingDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.name();
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *CachingDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.capabilities(allocator);
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *CachingDecorator = @ptrCast(@alignCast(ptr));

        // Generate cache key (no lock needed)
        const cache_key = self.generateCacheKey(message) catch {
            // If key generation fails, bypass cache
            return self.inner_agent.process(message);
        };
        defer self.allocator.free(cache_key);

        // Check cache with read lock
        self.rwlock.lockShared();
        if (self.cache.get(cache_key)) |entry| {
            if (!entry.isExpired()) {
                // Cache hit
                const response = entry.response;
                self.rwlock.unlockShared();

                // Update metrics (outside lock)
                self.rwlock.lock();
                self.metrics_data.total_requests += 1;
                self.metrics_data.cache_hits += 1;
                self.rwlock.unlock();

                return Result{ .ok = response };
            }
        }
        self.rwlock.unlockShared();

        // Cache miss - update metrics
        self.rwlock.lock();
        self.metrics_data.total_requests += 1;
        self.metrics_data.cache_misses += 1;
        self.cleanup_counter += 1;
        const do_cleanup = self.cleanup_counter % 100 == 0;
        self.rwlock.unlock();

        // Process message (outside lock)
        const result = try self.inner_agent.process(message);
        const response = try result.unwrap();

        // Cache response (write lock)
        self.rwlock.lock();
        defer self.rwlock.unlock();

        // Periodic cleanup
        if (do_cleanup) {
            self.cleanupExpired();
        }

        // Evict LRU if needed
        self.evictLRU();

        // Add to cache
        const now_ms = std.time.milliTimestamp();
        const key_owned = try self.allocator.dupe(u8, cache_key);
        const entry = CacheEntry{
            .response = response,
            .expires_at_ms = now_ms + @as(i64, @intCast(self.config.default_ttl_ms)),
            .created_at_ms = now_ms,
            .last_access_ms = now_ms,
        };
        try self.cache.put(key_owned, entry);
        self.metrics_data.current_size = self.cache.count();

        return Result{ .ok = response };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *CachingDecorator = @ptrCast(@alignCast(ptr));

        // Get introspection from inner agent
        const inner_result = try self.inner_agent.introspect(allocator);

        // Add caching metrics to metadata
        const metrics_snapshot = self.metrics();

        var metadata = std.StringHashMap([]const u8).init(allocator);
        errdefer metadata.deinit();

        // Add metrics as metadata
        try metadata.put("total_requests", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.total_requests}));
        try metadata.put("cache_hits", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.cache_hits}));
        try metadata.put("cache_misses", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.cache_misses}));
        try metadata.put("evictions", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.evictions}));
        try metadata.put("invalidations", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.invalidations}));
        try metadata.put("current_size", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.current_size}));

        if (metrics_snapshot.hitRate()) |rate| {
            try metadata.put("hit_rate", try std.fmt.allocPrint(allocator, "{d:.2}%", .{rate}));
        }
        if (metrics_snapshot.missRate()) |rate| {
            try metadata.put("miss_rate", try std.fmt.allocPrint(allocator, "{d:.2}%", .{rate}));
        }

        // Add configuration
        try metadata.put("max_cache_size", try std.fmt.allocPrint(allocator, "{d}", .{self.config.max_cache_size}));
        try metadata.put("default_ttl_ms", try std.fmt.allocPrint(allocator, "{d}", .{self.config.default_ttl_ms}));

        // Merge with inner metadata
        var inner_iter = inner_result.metadata.iterator();
        while (inner_iter.next()) |entry| {
            if (!std.mem.startsWith(u8, entry.key_ptr.*, "cache_")) {
                try metadata.put(entry.key_ptr.*, entry.value_ptr.*);
            }
        }

        return IntrospectionResult{
            .agent_name = inner_result.agent_name,
            .capabilities = inner_result.capabilities,
            .metadata = metadata,
            .memory = inner_result.memory,
        };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *CachingDecorator = @ptrCast(@alignCast(ptr));
        self.deinit();
        self.allocator.destroy(self);
    }
};

// Tests
const testing = std.testing;

test "CachingConfig validation" {
    var config = CachingConfig{};
    try config.validate();

    // Invalid: max_cache_size < 1
    config.max_cache_size = 0;
    try testing.expectError(error.InvalidConfig, config.validate());
    config.max_cache_size = 1000;

    // Invalid: default_ttl_ms == 0
    config.default_ttl_ms = 0;
    try testing.expectError(error.InvalidConfig, config.validate());
}

test "CachingMetrics calculations" {
    var metrics = CachingMetrics{
        .total_requests = 100,
        .cache_hits = 80,
        .cache_misses = 20,
    };

    // Hit rate
    const hit_rate = metrics.hitRate().?;
    try testing.expectApproxEqRel(@as(f64, 80.0), hit_rate, 0.01);

    // Miss rate
    const miss_rate = metrics.missRate().?;
    try testing.expectApproxEqRel(@as(f64, 20.0), miss_rate, 0.01);
}

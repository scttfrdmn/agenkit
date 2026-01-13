/// Example demonstrating CachingMiddleware usage
///
/// Shows how to:
/// 1. Configure caching with LRU and TTL
/// 2. Observe cache hits and misses
/// 3. Track caching metrics
/// 4. Test cache invalidation

const std = @import("std");
const agenkit = @import("agenkit");

// Counter agent that tracks how many times it's actually called
const CounterAgent = struct {
    allocator: std.mem.Allocator,
    call_count: std.atomic.Value(u32),

    pub fn init(allocator: std.mem.Allocator) !*CounterAgent {
        const self = try allocator.create(CounterAgent);
        self.* = CounterAgent{
            .allocator = allocator,
            .call_count = std.atomic.Value(u32).init(0),
        };
        return self;
    }

    pub fn agent(self: *CounterAgent) agenkit.Agent {
        return agenkit.Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .process_stream = processStreamImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "counter_agent";
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "counter";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *CounterAgent = @ptrCast(@alignCast(ptr));

        const count = self.call_count.fetchAdd(1, .monotonic);
        std.debug.print("  [Counter Agent] Processing request #{d}\\n", .{count + 1});

        // Echo back the message
        return agenkit.Result{ .ok = message };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        _ = ptr;
        return agenkit.createDefaultIntrospectionResult(allocator, "counter_agent", &.{"counter"});
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *CounterAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};


fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
    _ = ptr;
    _ = message;
    callbacks.onError(AgentError.NotImplemented);
}
pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\\n=== Caching Middleware Example ===\\n\\n", .{});

    // Example 1: Basic caching
    std.debug.print("Example 1: Basic Caching\\n", .{});
    try basicCachingExample(allocator);

    std.debug.print("\\n", .{});

    // Example 2: Cache expiration
    std.debug.print("Example 2: Cache Expiration (TTL)\\n", .{});
    try cacheExpirationExample(allocator);

    std.debug.print("\\n", .{});

    // Example 3: LRU eviction
    std.debug.print("Example 3: LRU Eviction\\n", .{});
    try lruEvictionExample(allocator);

    std.debug.print("\\n", .{});

    // Example 4: Metrics tracking
    std.debug.print("Example 4: Metrics Tracking\\n", .{});
    try metricsExample(allocator);

    std.debug.print("\\n=== All examples completed successfully ===\\n", .{});
}

fn basicCachingExample(allocator: std.mem.Allocator) !void {
    // Create counter agent
    var counter = try CounterAgent.init(allocator);
    defer counter.agent().deinit();

    // Configure caching
    const config = agenkit.middleware.CachingConfig{
        .max_cache_size = 100,
        .default_ttl_ms = 60000, // 60 seconds
    };
    var caching_agent = try agenkit.middleware.CachingDecorator.init(allocator, counter.agent(), config);
    defer caching_agent.agent().deinit();

    var message = try agenkit.Message.withText(allocator, .user, "Test message");
    defer message.deinit();

    // First request - cache miss
    std.debug.print("  Request 1 (cache miss)...\\n", .{});
    {
        const result = try caching_agent.agent().process(message);
        var response = try result.unwrap();
        response.deinit();
    }

    // Second request - cache hit
    std.debug.print("  Request 2 (cache hit)...\\n", .{});
    {
        const result = try caching_agent.agent().process(message);
        var response = try result.unwrap();
        response.deinit();
    }

    // Third request - cache hit
    std.debug.print("  Request 3 (cache hit)...\\n", .{});
    {
        const result = try caching_agent.agent().process(message);
        var response = try result.unwrap();
        response.deinit();
    }

    const metrics = caching_agent.metrics();
    std.debug.print("\\n  Metrics:\\n", .{});
    std.debug.print("    Total requests: {d}\\n", .{metrics.total_requests});
    std.debug.print("    Cache hits: {d}\\n", .{metrics.cache_hits});
    std.debug.print("    Cache misses: {d}\\n", .{metrics.cache_misses});
    std.debug.print("    Hit rate: {d:.1}%\\n", .{metrics.hitRate().?});
    std.debug.print("    Agent was called only once (rest served from cache)\\n", .{});
}

fn cacheExpirationExample(allocator: std.mem.Allocator) !void {
    // Create counter agent
    var counter = try CounterAgent.init(allocator);
    defer counter.agent().deinit();

    // Configure caching with short TTL
    const config = agenkit.middleware.CachingConfig{
        .max_cache_size = 100,
        .default_ttl_ms = 500, // 500ms TTL
    };
    var caching_agent = try agenkit.middleware.CachingDecorator.init(allocator, counter.agent(), config);
    defer caching_agent.agent().deinit();

    var message = try agenkit.Message.withText(allocator, .user, "Test message");
    defer message.deinit();

    // First request - cache miss
    std.debug.print("  Request 1 (cache miss)...\\n", .{});
    {
        const result = try caching_agent.agent().process(message);
        var response = try result.unwrap();
        response.deinit();
    }

    // Second request immediately - cache hit
    std.debug.print("  Request 2 (cache hit)...\\n", .{});
    {
        const result = try caching_agent.agent().process(message);
        var response = try result.unwrap();
        response.deinit();
    }

    // Wait for TTL expiration
    std.debug.print("  Waiting 600ms for cache expiration...\\n", .{});
    std.time.sleep(600 * std.time.ns_per_ms);

    // Third request - cache miss (expired)
    std.debug.print("  Request 3 (cache miss - expired)...\\n", .{});
    {
        const result = try caching_agent.agent().process(message);
        var response = try result.unwrap();
        response.deinit();
    }

    const metrics = caching_agent.metrics();
    std.debug.print("\\n  Metrics:\\n", .{});
    std.debug.print("    Total requests: {d}\\n", .{metrics.total_requests});
    std.debug.print("    Cache hits: {d}\\n", .{metrics.cache_hits});
    std.debug.print("    Cache misses: {d}\\n", .{metrics.cache_misses});
    std.debug.print("    Agent was called twice (once, then after expiration)\\n", .{});
}

fn lruEvictionExample(allocator: std.mem.Allocator) !void {
    // Create counter agent
    var counter = try CounterAgent.init(allocator);
    defer counter.agent().deinit();

    // Configure caching with small size
    const config = agenkit.middleware.CachingConfig{
        .max_cache_size = 3, // Only 3 entries
        .default_ttl_ms = 60000,
    };
    var caching_agent = try agenkit.middleware.CachingDecorator.init(allocator, counter.agent(), config);
    defer caching_agent.agent().deinit();

    std.debug.print("  Sending 5 unique messages (cache size = 3)...\\n", .{});

    // Send 5 different messages
    var i: u32 = 0;
    while (i < 5) : (i += 1) {
        const text = try std.fmt.allocPrint(allocator, "Message {d}", .{i + 1});
        defer allocator.free(text);

        var message = try agenkit.Message.withText(allocator, .user, text);
        defer message.deinit();

        const result = try caching_agent.agent().process(message);
        var response = try result.unwrap();
        response.deinit();

        std.debug.print("    Sent: {s}\\n", .{text});
    }

    const metrics = caching_agent.metrics();
    std.debug.print("\\n  Metrics:\\n", .{});
    std.debug.print("    Total requests: {d}\\n", .{metrics.total_requests});
    std.debug.print("    Cache hits: {d}\\n", .{metrics.cache_hits});
    std.debug.print("    Cache misses: {d}\\n", .{metrics.cache_misses});
    std.debug.print("    Evictions: {d} (LRU)\\n", .{metrics.evictions});
    std.debug.print("    Current size: {d}\\n", .{metrics.current_size});
}

fn metricsExample(allocator: std.mem.Allocator) !void {
    // Create counter agent
    var counter = try CounterAgent.init(allocator);
    defer counter.agent().deinit();

    // Configure caching
    const config = agenkit.middleware.CachingConfig{
        .max_cache_size = 100,
        .default_ttl_ms = 60000,
    };
    var caching_agent = try agenkit.middleware.CachingDecorator.init(allocator, counter.agent(), config);
    defer caching_agent.agent().deinit();

    std.debug.print("  Sending 50 requests (25 unique, each sent twice)...\\n", .{});

    // Send 25 unique messages, each twice (should get 25 misses, 25 hits)
    var i: u32 = 0;
    while (i < 25) : (i += 1) {
        const text = try std.fmt.allocPrint(allocator, "Message {d}", .{i + 1});
        defer allocator.free(text);

        var message = try agenkit.Message.withText(allocator, .user, text);
        defer message.deinit();

        // First request - miss
        {
            const result = try caching_agent.agent().process(message);
            var response = try result.unwrap();
            response.deinit();
        }

        // Second request - hit
        {
            const result = try caching_agent.agent().process(message);
            var response = try result.unwrap();
            response.deinit();
        }
    }

    const metrics = caching_agent.metrics();
    std.debug.print("\\n  Final Metrics:\\n", .{});
    std.debug.print("    Total requests:    {d}\\n", .{metrics.total_requests});
    std.debug.print("    Cache hits:        {d}\\n", .{metrics.cache_hits});
    std.debug.print("    Cache misses:      {d}\\n", .{metrics.cache_misses});
    std.debug.print("    Hit rate:          {d:.1}%\\n", .{metrics.hitRate().?});
    std.debug.print("    Miss rate:         {d:.1}%\\n", .{metrics.missRate().?});
    std.debug.print("    Evictions:         {d}\\n", .{metrics.evictions});
    std.debug.print("    Current size:      {d}\\n", .{metrics.current_size});
    std.debug.print("\\n    Agent called only 25 times (50%% cache hit rate)\\n", .{});
}

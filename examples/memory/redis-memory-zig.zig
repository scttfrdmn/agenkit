/// Redis Memory Example - Zig
///
/// Demonstrates Redis-backed persistent memory for production deployments.
///
/// Prerequisites:
///   docker run -d -p 6379:6379 redis:7-alpine
///
/// Features:
/// - Persistent storage (survives restarts)
/// - TTL support (automatic expiry)
/// - Multi-instance agents (shared memory)
/// - Filtering (time, importance, tags)
/// - Utilities (session management, stats)
///
/// Note: This is a stub implementation showing the API design.
/// Full implementation requires hiredis C library integration.
const std = @import("std");
const RedisMemory = @import("../../agenkit-zig/src/infrastructure/memory/redis_memory.zig").RedisMemory;

fn printDivider(title: []const u8) void {
    std.debug.print("{s}\n", .{"=" ** 60});
    if (title.len > 0) {
        std.debug.print("{s}\n", .{title});
        std.debug.print("{s}\n", .{"=" ** 60});
    }
}

fn basicUsage(allocator: std.mem.Allocator) !void {
    printDivider("Basic Redis Memory Usage");

    // Create Redis memory with 24-hour TTL
    var memory = try RedisMemory.init(
        allocator,
        "localhost",
        6379,
        86400, // 24 hours
        "agenkit:demo",
    );
    defer memory.deinit();

    const session_id = "demo-session-1";

    // Store messages with metadata
    std.debug.print("\n📝 Storing messages...\n", .{});

    var metadata1 = std.StringHashMap(std.json.Value).init(allocator);
    defer metadata1.deinit();
    try metadata1.put("importance", std.json.Value{ .float = 0.8 });

    memory.store(session_id, "user", "What is Redis?", metadata1) catch |err| {
        std.debug.print("Store not implemented: {s}\n", .{@errorName(err)});
        return;
    };

    // In full implementation:
    // memory.store(session_id, "assistant", "Redis is...", metadata2) catch {};
    // memory.store(session_id, "user", "Thanks!", metadata3) catch {};

    // Retrieve recent messages
    std.debug.print("\n📤 Retrieving recent messages...\n", .{});
    const messages = memory.retrieve(session_id, 3, null, null, null) catch |err| {
        std.debug.print("Retrieve not implemented: {s}\n", .{@errorName(err)});
        return;
    };
    defer {
        for (messages) |*msg| {
            msg.deinit();
        }
        allocator.free(messages);
    }

    for (messages) |msg| {
        std.debug.print("[{s}] {s}\n", .{ msg.role, msg.content });
    }

    // Get session count
    const count = memory.getSessionCount(session_id) catch |err| {
        std.debug.print("GetSessionCount not implemented: {s}\n", .{@errorName(err)});
        return;
    };
    std.debug.print("\n📊 Session has {d} messages\n", .{count});
}

fn filteringExample(allocator: std.mem.Allocator) !void {
    printDivider("\nFiltering Example");

    var memory = try RedisMemory.init(
        allocator,
        "localhost",
        6379,
        86400,
        "agenkit:filter",
    );
    defer memory.deinit();

    const session_id = "filter-demo";

    // Store messages with different importance and tags
    std.debug.print("\n📝 Storing messages with metadata...\n", .{});

    const messages = [_]struct { content: []const u8, importance: f64, tags: []const []const u8 }{
        .{ .content = "Hello", .importance = 0.3, .tags = &[_][]const u8{"greeting"} },
        .{ .content = "Can you help with Redis?", .importance = 0.8, .tags = &[_][]const u8{ "question", "redis" } },
        .{ .content = "How do I scale it?", .importance = 0.9, .tags = &[_][]const u8{ "question", "scaling" } },
        .{ .content = "Thanks!", .importance = 0.2, .tags = &[_][]const u8{"gratitude"} },
    };

    for (messages) |msg| {
        var metadata = std.StringHashMap(std.json.Value).init(allocator);
        defer metadata.deinit();

        try metadata.put("importance", std.json.Value{ .float = msg.importance });
        // In full implementation, add tags array

        memory.store(session_id, "user", msg.content, metadata) catch {
            continue;
        };
    }

    std.debug.print("\nNote: Filtering requires full Redis implementation\n", .{});
}

fn multiSessionExample(allocator: std.mem.Allocator) !void {
    printDivider("\nMulti-Session Example");

    var memory = try RedisMemory.init(
        allocator,
        "localhost",
        6379,
        86400,
        "agenkit:multi",
    );
    defer memory.deinit();

    // Simulate multiple user sessions
    std.debug.print("\n👥 Creating multiple sessions...\n", .{});

    var empty_metadata = std.StringHashMap(std.json.Value).init(allocator);
    defer empty_metadata.deinit();

    memory.store("user-alice", "user", "Hello from Alice", empty_metadata) catch {};
    memory.store("user-bob", "user", "Hello from Bob", empty_metadata) catch {};
    memory.store("user-charlie", "user", "Hello from Charlie", empty_metadata) catch {};

    std.debug.print("\nNote: Session management requires full Redis implementation\n", .{});
}

fn productionExample(allocator: std.mem.Allocator) !void {
    printDivider("\nProduction Deployment Example");

    // Production configuration
    const redis_host = std.os.getenv("REDIS_HOST") orelse "localhost";

    var memory = try RedisMemory.init(
        allocator,
        redis_host,
        6379,
        7 * 24 * 3600, // 7 days
        "prod:agenkit:memory",
    );
    defer memory.deinit();

    std.debug.print("\n✅ Production features:\n", .{});
    std.debug.print("  • Persistent storage (survives restarts)\n", .{});
    std.debug.print("  • 7-day TTL (automatic cleanup)\n", .{});
    std.debug.print("  • Multi-instance support (shared memory)\n", .{});
    std.debug.print("  • Filtering (time, importance, tags)\n", .{});
    std.debug.print("  • Session management utilities\n", .{});

    const capabilities = RedisMemory.capabilities();
    std.debug.print("\n🎯 Capabilities:\n", .{});
    for (capabilities) |capability| {
        std.debug.print("  • {s}\n", .{capability});
    }

    std.debug.print("\n💡 Use cases:\n", .{});
    std.debug.print("  • Long-running agents (persist across restarts)\n", .{});
    std.debug.print("  • Multi-instance deployments (shared state)\n", .{});
    std.debug.print("  • Session recovery (restore after failure)\n", .{});
    std.debug.print("  • Conversation history (queryable archive)\n", .{});

    std.debug.print("\n⚠️  Note: This is a stub showing API design.\n", .{});
    std.debug.print("Full implementation requires hiredis C library:\n", .{});
    std.debug.print("1. Add hiredis dependency to build.zig\n", .{});
    std.debug.print("2. Use @cImport(@cInclude(\"hiredis/hiredis.h\"))\n", .{});
    std.debug.print("3. Implement Redis protocol commands\n", .{});
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    basicUsage(allocator) catch |err| {
        std.debug.print("Error in basic_usage: {s}\n", .{@errorName(err)});
    };

    filteringExample(allocator) catch |err| {
        std.debug.print("Error in filtering_example: {s}\n", .{@errorName(err)});
    };

    multiSessionExample(allocator) catch |err| {
        std.debug.print("Error in multi_session_example: {s}\n", .{@errorName(err)});
    };

    productionExample(allocator) catch |err| {
        std.debug.print("Error in production_example: {s}\n", .{@errorName(err)});
    };

    printDivider("\n✅ All examples completed!");
    std.debug.print("Note: This demonstrates the API. Full Redis integration pending.\n", .{});
}

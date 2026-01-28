///! Example of using WebSocket transport for real-time agent communication in Zig.
///!
///! This example demonstrates how to use the WebSocketAgent to communicate with
///! a remote agent server over WebSocket protocol for real-time bidirectional
///! communication.
///!
///! Prerequisites:
///! 1. Install WebSocket library (or use std.http in Zig 0.11+)
///! 2. Start a WebSocket agent server (see server examples in other languages)
///! 3. Run this example
///!
///! Build:
///! ```
///! zig build-exe examples/transports/websocket-transport-zig.zig \
///!     -I agenkit-zig/src
///! ```

const std = @import("std");
const ws = @import("../../agenkit-zig/src/transports/websocket.zig");
const Message = @import("../../agenkit-zig/src/message.zig").Message;

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    try stdout.print("Agenkit Zig - WebSocket Transport Example\n", .{});
    try stdout.print("==========================================\n\n", .{});

    // Basic WebSocket example
    try basicWebSocketExample(allocator, stdout);

    // Secure WebSocket example
    try secureWebSocketExample(allocator, stdout);

    // Custom headers example
    try customHeadersExample(allocator, stdout);

    // Reconnection example
    try reconnectionExample(allocator, stdout);

    // Real-time conversation example
    try realtimeConversationExample(allocator, stdout);

    // Setup instructions
    try stdout.print("\n=== Setup Instructions ===\n", .{});
    try stdout.print("1. WebSocket in Zig:\n", .{});
    try stdout.print("   Option A: Use std.http.Client (Zig 0.11+)\n", .{});
    try stdout.print("   Option B: Use zig-websocket library\n", .{});
    try stdout.print("   Option C: Bind to C WebSocket library\n", .{});
    try stdout.print("\n2. Start a WebSocket server (Python example):\n", .{});
    try stdout.print("   cd agenkit\n", .{});
    try stdout.print("   python examples/websocket_server_example.py\n", .{});
    try stdout.print("\n3. Run this example:\n", .{});
    try stdout.print("   zig build-exe examples/transports/websocket-transport-zig.zig\n", .{});
}

fn basicWebSocketExample(allocator: std.mem.Allocator, writer: anytype) !void {
    try writer.print("\n=== Basic WebSocket Example ===\n", .{});

    // Check if WebSocket support is available
    if (!ws.WebSocketAgent.isAvailable()) {
        try writer.print("WebSocket transport not available (stub implementation).\n", .{});
        try writer.print("Full implementation requires WebSocket library.\n", .{});
        return;
    }

    var config = ws.WebSocketConfig.init(allocator, "ws://localhost:8080");

    var agent = try ws.WebSocketAgent.init(allocator, config);
    defer agent.deinit();

    try writer.print("Connected to WebSocket server at {s}\n", .{config.url});
    try writer.print("Connected: {}\n", .{agent.isConnected()});

    // Create a message
    var messages = std.ArrayList(Message).init(allocator);
    defer messages.deinit();

    const msg = Message.init(allocator, "user", "Hello via WebSocket!");
    try messages.append(msg);

    // Send message (would work in full implementation)
    try writer.print("Sending message: {s}\n", .{msg.content});

    // This will return NotImplemented in stub
    const response = agent.process(messages.items) catch |err| {
        try writer.print("Error (expected for stub): {}\n", .{err});
        return;
    };
    defer response.deinit();

    try writer.print("Response from agent: {s}\n", .{response.content});

    // Show capabilities
    try writer.print("\nAgent capabilities:\n", .{});
    for (agent.capabilities()) |cap| {
        try writer.print("  - {s}\n", .{cap});
    }

    // Test ping
    try writer.print("\nTesting keep-alive ping...\n", .{});
    agent.ping() catch |err| {
        try writer.print("Ping error (expected for stub): {}\n", .{err});
    };
}

fn secureWebSocketExample(allocator: std.mem.Allocator, writer: anytype) !void {
    try writer.print("\n=== Secure WebSocket (wss://) Example ===\n", .{});

    if (!ws.WebSocketAgent.isAvailable()) {
        try writer.print("WebSocket transport not available (stub implementation).\n", .{});
        return;
    }

    var config = ws.WebSocketConfig.init(allocator, "wss://api.example.com");
    config.max_retries = 10;
    config.ping_interval_secs = 60;
    config.request_timeout_secs = 60;

    var agent = try ws.WebSocketAgent.init(allocator, config);
    defer agent.deinit();

    try writer.print("Connected to secure WebSocket server at {s}\n", .{config.url});

    var messages = std.ArrayList(Message).init(allocator);
    defer messages.deinit();

    const msg = Message.init(allocator, "user", "Secure message via WebSocket");
    try messages.append(msg);

    const response = agent.process(messages.items) catch |err| {
        try writer.print("Error (expected for stub): {}\n", .{err});
        return;
    };
    defer response.deinit();

    try writer.print("Response: {s}\n", .{response.content});
}

fn customHeadersExample(allocator: std.mem.Allocator, writer: anytype) !void {
    try writer.print("\n=== WebSocket with Custom Headers Example ===\n", .{});

    if (!ws.WebSocketAgent.isAvailable()) {
        try writer.print("WebSocket transport not available (stub implementation).\n", .{});
        return;
    }

    var config = ws.WebSocketConfig.init(allocator, "ws://localhost:8080");

    // Add custom headers
    try config.headers.put("Authorization", "Bearer your-token-here");
    try config.headers.put("X-Client-Version", "1.0.0");
    try config.headers.put("X-Custom-Header", "custom-value");

    var agent = try ws.WebSocketAgent.init(allocator, config);
    defer agent.deinit();

    try writer.print("Connected with custom headers\n", .{});

    var messages = std.ArrayList(Message).init(allocator);
    defer messages.deinit();

    const msg = Message.init(allocator, "user", "Authenticated request");
    try messages.append(msg);

    const response = agent.process(messages.items) catch |err| {
        try writer.print("Error (expected for stub): {}\n", .{err});
        return;
    };
    defer response.deinit();

    try writer.print("Response: {s}\n", .{response.content});
}

fn reconnectionExample(allocator: std.mem.Allocator, writer: anytype) !void {
    try writer.print("\n=== Automatic Reconnection Example ===\n", .{});

    if (!ws.WebSocketAgent.isAvailable()) {
        try writer.print("WebSocket transport not available (stub implementation).\n", .{});
        return;
    }

    var config = ws.WebSocketConfig.init(allocator, "ws://localhost:8080");
    config.max_retries = 5;
    config.initial_retry_delay_ms = 1000;
    config.max_retry_delay_ms = 30000;

    var agent = try ws.WebSocketAgent.init(allocator, config);
    defer agent.deinit();

    try writer.print("Initial connection status: {}\n", .{agent.isConnected()});

    // Simulate connection loss and reconnection
    try writer.print("\nSimulating connection loss...\n", .{});
    try writer.print("Attempting manual reconnection...\n", .{});

    agent.reconnect() catch |err| {
        try writer.print("Reconnection error (expected for stub): {}\n", .{err});
        return;
    };

    try writer.print("Reconnection successful\n", .{});

    // Try sending a message after reconnection
    var messages = std.ArrayList(Message).init(allocator);
    defer messages.deinit();

    const msg = Message.init(allocator, "user", "Message after reconnection");
    try messages.append(msg);

    const response = agent.process(messages.items) catch |err| {
        try writer.print("Error: {}\n", .{err});
        return;
    };
    defer response.deinit();

    try writer.print("Response: {s}\n", .{response.content});
}

fn realtimeConversationExample(allocator: std.mem.Allocator, writer: anytype) !void {
    try writer.print("\n=== Real-time Conversation Example ===\n", .{});

    if (!ws.WebSocketAgent.isAvailable()) {
        try writer.print("WebSocket transport not available (stub implementation).\n", .{});
        return;
    }

    var config = ws.WebSocketConfig.init(allocator, "ws://localhost:8080");

    var agent = try ws.WebSocketAgent.init(allocator, config);
    defer agent.deinit();

    const conversation = [_][]const u8{
        "Hello!",
        "How are you?",
        "Tell me a joke",
        "Thanks, that was funny!",
        "Goodbye!",
    };

    for (conversation) |user_msg| {
        try writer.print("\nUser: {s}\n", .{user_msg});

        var messages = std.ArrayList(Message).init(allocator);
        defer messages.deinit();

        const msg = Message.init(allocator, "user", user_msg);
        try messages.append(msg);

        const response = agent.process(messages.items) catch |err| {
            try writer.print("Error: {}\n", .{err});
            break;
        };
        defer response.deinit();

        try writer.print("Agent: {s}\n", .{response.content});

        // Small delay between messages for more natural conversation
        std.time.sleep(500 * std.time.ns_per_ms);
    }
}

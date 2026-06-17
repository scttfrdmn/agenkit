///! WebSocket transport for agent communication.
///!
///! Implements the Agent interface for WebSocket-based communication,
///! providing real-time bidirectional communication with automatic reconnection.
///!
///! Features:
///! - Real-time bidirectional communication
///! - Automatic reconnection with exponential backoff
///! - Ping/pong keep-alive
///! - Request/response correlation
///! - Binary and text frames
///! - TLS support (wss://)
///!
///! Example:
///! ```zig
///! const config = WebSocketConfig{
///!     .url = "ws://localhost:8080",
///!     .max_retries = 5,
///!     .initial_retry_delay_ms = 1000,
///!     .ping_interval_secs = 30,
///! };
///! var agent = try WebSocketAgent.init(allocator, config);
///! defer agent.deinit();
///!
///! var messages = std.ArrayList(Message).empty;
///! defer messages.deinit();
///! try messages.append(Message.init("user", "Hello via WebSocket!"));
///!
///! const response = try agent.process(messages.items);
///! defer response.deinit();
///! ```
///!
///! Implementation Notes:
///!
///! This is a stub implementation showing the API design.
///!
///! Full implementation requires:
///! 1. Implement WebSocket client using std.http or zig-websocket
///! 2. Add message framing with request IDs for correlation
///! 3. Implement reconnection logic with exponential backoff
///! 4. Add ping/pong keep-alive mechanism
///! 5. Handle concurrent requests with async
///! 6. Implement TLS support for wss://
///!
///! WebSocket in Zig:
///! - Option 1: Use std.http.Client (Zig 0.11+) with WebSocket upgrade
///! - Option 2: zig-websocket library (community)
///! - Option 3: Call C WebSocket library via @cImport
///! - Option 4: Implement WebSocket protocol from RFC 6455
const std = @import("std");
const Allocator = std.mem.Allocator;
const Message = @import("../message.zig").Message;

/// WebSocket transport configuration
pub const WebSocketConfig = struct {
    /// WebSocket URL (ws:// or wss://)
    url: []const u8,

    /// Maximum reconnection attempts
    max_retries: usize = 5,

    /// Initial retry delay in milliseconds
    initial_retry_delay_ms: u64 = 1000,

    /// Maximum retry delay in milliseconds
    max_retry_delay_ms: u64 = 30000,

    /// Ping interval in milliseconds
    ping_interval_ms: u64 = 30000,

    /// Ping timeout in milliseconds
    ping_timeout_ms: u64 = 10000,

    /// Connection timeout in milliseconds
    connect_timeout_ms: u64 = 10000,

    /// Request timeout in milliseconds
    request_timeout_ms: u64 = 30000,

    /// Custom headers for connection
    headers: std.StringHashMap([]const u8),

    /// Initialize with default headers
    pub fn init(allocator: Allocator, url: []const u8) WebSocketConfig {
        return .{
            .url = url,
            .headers = std.StringHashMap([]const u8).init(allocator),
        };
    }

    /// Clean up headers
    pub fn deinit(self: *WebSocketConfig) void {
        self.headers.deinit();
    }
};

/// WebSocket agent for real-time communication
pub const WebSocketAgent = struct {
    allocator: Allocator,
    config: WebSocketConfig,
    connected: bool,

    // In full implementation:
    // client: *WebSocketClient,
    // pending_requests: std.StringHashMap(*Promise),
    // ping_thread: ?std.Thread,
    // receive_thread: ?std.Thread,
    // should_stop: bool,
    // mutex: agksync.Mutex,

    const Self = @This();

    /// Initialize WebSocket agent
    ///
    /// Full implementation would:
    /// 1. Parse WebSocket URL
    /// 2. Create TLS context if wss://
    /// 3. Connect to WebSocket server
    /// 4. Start ping/pong keep-alive task
    /// 5. Start message receive loop
    ///
    /// Example using std.http:
    /// ```zig
    /// var client = std.http.Client{ .allocator = allocator };
    /// defer client.deinit();
    ///
    /// const uri = try std.Uri.parse(config.url);
    /// var header_buffer: [4096]u8 = undefined;
    ///
    /// var request = try client.open(.GET, uri, .{
    ///     .server_header_buffer = &header_buffer,
    ///     .extra_headers = &[_]std.http.Header{
    ///         .{ .name = "Upgrade", .value = "websocket" },
    ///         .{ .name = "Connection", .value = "Upgrade" },
    ///         .{ .name = "Sec-WebSocket-Key", .value = generateKey() },
    ///         .{ .name = "Sec-WebSocket-Version", .value = "13" },
    ///     },
    /// });
    /// defer request.deinit();
    ///
    /// try request.send();
    /// try request.wait();
    ///
    /// if (request.response.status != .switching_protocols) {
    ///     return error.UpgradeFailed;
    /// }
    ///
    /// // Start ping and receive threads
    /// const ping_thread = try std.Thread.spawn(.{}, pingLoop, .{self});
    /// const receive_thread = try std.Thread.spawn(.{}, receiveLoop, .{self});
    /// ```
    pub fn init(allocator: Allocator, config: WebSocketConfig) !Self {
        // Stub implementation - full version would initialize WebSocket connection
        return Self{
            .allocator = allocator,
            .config = config,
            .connected = false,
        };
    }

    /// Clean up WebSocket resources
    pub fn deinit(self: *Self) void {
        // Full implementation would:
        // - Stop ping and receive threads
        // - Close WebSocket connection
        // - Clean up pending requests
        // - Free allocated resources
        self.config.deinit();
    }

    /// Process message via WebSocket
    ///
    /// Full implementation would:
    /// 1. Generate request ID
    /// 2. Create JSON request with messages
    /// 3. Send WebSocket text frame
    /// 4. Create promise for response
    /// 5. Store in pending_requests map
    /// 6. Wait for response with timeout
    /// 7. Return message
    ///
    /// Example:
    /// ```zig
    /// if (!self.connected) {
    ///     return error.NotConnected;
    /// }
    ///
    /// const request_id = try generateUuid(allocator);
    /// defer allocator.free(request_id);
    ///
    /// const request = try std.json.stringify(.{
    ///     .id = request_id,
    ///     .method = "process",
    ///     .messages = messages,
    /// }, .{}, allocator);
    /// defer allocator.free(request);
    ///
    /// // Create promise for response
    /// var promise = Promise.init(allocator);
    /// errdefer promise.deinit();
    ///
    /// {
    ///     self.mutex.lock();
    ///     defer self.mutex.unlock();
    ///     try self.pending_requests.put(request_id, &promise);
    /// }
    ///
    /// // Send WebSocket frame
    /// try self.client.send(.text, request);
    ///
    /// // Wait for response with timeout
    /// const response = try promise.wait(config.request_timeout_secs * std.time.ns_per_s);
    /// return response;
    /// ```
    pub fn process(self: *Self, messages: []const Message) !Message {
        // Stub implementation - returns error for now
        _ = self;
        _ = messages;
        return error.NotImplemented;
    }

    /// Check if WebSocket is connected
    pub fn isConnected(self: *const Self) bool {
        return self.connected;
    }

    /// Manually reconnect to WebSocket server
    ///
    /// Automatically called on connection failure with exponential backoff.
    ///
    /// Full implementation would:
    /// 1. Close existing connection if any
    /// 2. Attempt reconnection with exponential backoff
    /// 3. Restore ping/pong and receive loops
    ///
    /// Example:
    /// ```zig
    /// var attempt: usize = 0;
    /// while (attempt < self.config.max_retries) : (attempt += 1) {
    ///     const delay = self.config.initial_retry_delay_ms * std.math.pow(u64, 2, attempt);
    ///     const capped_delay = @min(delay, self.config.max_retry_delay_ms);
    ///
    ///     agktime.sleep(capped_delay * std.time.ns_per_ms);
    ///
    ///     if (try self.tryConnect()) {
    ///         self.connected = true;
    ///         return;
    ///     }
    /// }
    /// return error.ReconnectFailed;
    /// ```
    pub fn reconnect(self: *Self) !void {
        _ = self;
        return error.NotImplemented;
    }

    /// Send a ping frame to keep connection alive
    ///
    /// Automatically called by ping task every ping_interval seconds.
    ///
    /// Full implementation would:
    /// 1. Send WebSocket ping frame
    /// 2. Wait for pong response
    /// 3. Trigger reconnect if timeout
    ///
    /// Example:
    /// ```zig
    /// if (!self.connected) {
    ///     return error.NotConnected;
    /// }
    ///
    /// try self.client.send(.ping, &[_]u8{});
    ///
    /// // Wait for pong with timeout
    /// const pong_received = try self.waitForPong(self.config.ping_timeout_secs);
    /// if (!pong_received) {
    ///     self.connected = false;
    ///     try self.reconnect();
    /// }
    /// ```
    pub fn ping(self: *Self) !void {
        _ = self;
        return error.NotImplemented;
    }

    /// Get capabilities
    pub fn capabilities(self: *const Self) []const []const u8 {
        _ = self;
        const caps = [_][]const u8{
            "websocket",
            "bidirectional",
            "realtime",
            "streaming",
        };
        return &caps;
    }

    /// Check if WebSocket support is available
    pub fn isAvailable() bool {
        // In full implementation, check if WebSocket library is available
        return false; // Stub returns false
    }
};

// Tests
test "WebSocketConfig default values" {
    const allocator = std.testing.allocator;
    var config = WebSocketConfig.init(allocator, "ws://localhost:8080");
    defer config.deinit();

    try std.testing.expectEqualStrings("ws://localhost:8080", config.url);
    try std.testing.expectEqual(@as(usize, 5), config.max_retries);
    try std.testing.expectEqual(@as(u64, 1000), config.initial_retry_delay_ms);
    try std.testing.expectEqual(@as(u32, 30), config.ping_interval_secs);
}

test "WebSocketAgent init and deinit" {
    const allocator = std.testing.allocator;
    var config = WebSocketConfig.init(allocator, "ws://localhost:8080");

    var agent = try WebSocketAgent.init(allocator, config);
    defer agent.deinit();

    try std.testing.expectEqualStrings("ws://localhost:8080", agent.config.url);
    try std.testing.expectEqual(false, agent.connected);
}

test "WebSocketAgent isConnected" {
    const allocator = std.testing.allocator;
    var config = WebSocketConfig.init(allocator, "ws://localhost:8080");

    var agent = try WebSocketAgent.init(allocator, config);
    defer agent.deinit();

    try std.testing.expectEqual(false, agent.isConnected());
}

test "WebSocketAgent capabilities" {
    const allocator = std.testing.allocator;
    var config = WebSocketConfig.init(allocator, "ws://localhost:8080");

    var agent = try WebSocketAgent.init(allocator, config);
    defer agent.deinit();

    const caps = agent.capabilities();
    try std.testing.expectEqual(@as(usize, 4), caps.len);
    try std.testing.expectEqualStrings("websocket", caps[0]);
    try std.testing.expectEqualStrings("realtime", caps[2]);
}

test "WebSocketAgent isAvailable" {
    try std.testing.expectEqual(false, WebSocketAgent.isAvailable());
}

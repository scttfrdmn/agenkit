///! gRPC transport for agent communication.
///!
///! Implements the Agent interface for gRPC-based communication,
///! providing efficient binary protocol with built-in streaming support.
///!
///! Features:
///! - Binary protocol with Protocol Buffers
///! - Bidirectional streaming
///! - HTTP/2 multiplexing
///! - TLS support
///! - Automatic reconnection
///! - Load balancing support
///!
///! Example:
///! ```zig
///! const config = GrpcConfig{
///!     .url = "localhost:50051",
///!     .use_tls = false,
///!     .timeout_secs = 30,
///! };
///! var agent = try GrpcAgent.init(allocator, config);
///! defer agent.deinit();
///!
///! var messages = std.ArrayList(Message).init(allocator);
///! defer messages.deinit();
///! try messages.append(Message.init("user", "Hello via gRPC!"));
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
///! 1. Add gRPC Zig library (grpc-zig or custom implementation)
///! 2. Generate Zig code from proto/agent.proto
///! 3. Implement AgentService client
///! 4. Add connection pooling and retry logic
///! 5. Implement TLS configuration
///!
///! Protocol Buffers in Zig:
///! - Option 1: protobuf-zig for code generation
///! - Option 2: Call C protobuf library via @cImport
///! - Option 3: Manual protobuf encoding/decoding
///!
///! gRPC in Zig:
///! - Option 1: Bind to C++ gRPC library via @cImport
///! - Option 2: Implement HTTP/2 client with protobuf encoding
///! - Option 3: Use existing zig-http2 + protobuf-zig

const std = @import("std");
const Allocator = std.mem.Allocator;
const Message = @import("../message.zig").Message;

/// gRPC transport configuration
pub const GrpcConfig = struct {
    /// gRPC server URL (e.g., "localhost:50051")
    url: []const u8,

    /// Enable TLS (grpcs://)
    use_tls: bool = false,

    /// Path to CA certificate for TLS verification
    ca_cert: ?[]const u8 = null,

    /// Client certificate for mTLS
    client_cert: ?[]const u8 = null,

    /// Client key for mTLS
    client_key: ?[]const u8 = null,

    /// Request timeout in milliseconds
    timeout_ms: u64 = 30000,

    /// Connection timeout in milliseconds
    connect_timeout_ms: u64 = 10000,

    /// Keep-alive interval in milliseconds
    keepalive_interval_ms: u64 = 30000,

    /// Maximum message size in bytes
    max_message_size: usize = 4 * 1024 * 1024, // 4MB
};

/// gRPC agent for remote communication
pub const GrpcAgent = struct {
    allocator: Allocator,
    config: GrpcConfig,

    // In full implementation:
    // channel: *Channel,
    // stub: *AgentServiceStub,
    // connected: bool,

    const Self = @This();

    /// Initialize gRPC agent
    ///
    /// Full implementation would:
    /// 1. Parse URL and extract endpoint
    /// 2. Configure TLS if use_tls is true
    /// 3. Create gRPC channel with credentials
    /// 4. Build AgentService stub
    /// 5. Test connection with health check
    ///
    /// Example using @cImport:
    /// ```zig
    /// const c = @cImport({
    ///     @cInclude("grpcpp/grpcpp.h");
    ///     @cInclude("agent.grpc.pb.h");
    /// });
    ///
    /// var creds: *c.ChannelCredentials = undefined;
    /// if (config.use_tls) {
    ///     var ssl_opts = c.SslCredentialsOptions{};
    ///     if (config.ca_cert) |ca| {
    ///         // Read CA cert file
    ///         ssl_opts.pem_root_certs = ca;
    ///     }
    ///     creds = c.grpc_ssl_credentials_create(&ssl_opts);
    /// } else {
    ///     creds = c.grpc_insecure_credentials_create();
    /// }
    ///
    /// var args = c.ChannelArguments{};
    /// args.SetInt(c.GRPC_ARG_KEEPALIVE_TIME_MS, config.keepalive_interval_secs * 1000);
    /// args.SetInt(c.GRPC_ARG_MAX_RECEIVE_MESSAGE_LENGTH, config.max_message_size);
    ///
    /// const channel = c.grpc_channel_create(config.url.ptr, creds, &args);
    /// const stub = c.agent_AgentService_NewStub(channel);
    /// ```
    pub fn init(allocator: Allocator, config: GrpcConfig) !Self {
        // Stub implementation - full version would initialize gRPC connection
        _ = allocator;
        return Self{
            .allocator = allocator,
            .config = config,
        };
    }

    /// Clean up gRPC resources
    pub fn deinit(self: *Self) void {
        // Full implementation would:
        // - Close gRPC channel
        // - Clean up stub
        // - Free any allocated resources
        _ = self;
    }

    /// Process message via gRPC
    ///
    /// Full implementation would:
    /// 1. Convert messages to proto Request
    /// 2. Set request ID, timestamp, metadata
    /// 3. Create gRPC ClientContext with timeout
    /// 4. Call stub.Process(context, request, &response)
    /// 5. Convert proto Response to Message
    /// 6. Handle errors and retries
    ///
    /// Example:
    /// ```zig
    /// var request = agent.Request{
    ///     .version = "1.0",
    ///     .id = generateUuid(),
    ///     .timestamp = getIso8601Timestamp(),
    ///     .method = "process",
    ///     .messages = &proto_messages,
    /// };
    ///
    /// var context = grpc.ClientContext{};
    /// context.set_deadline(std.time.timestamp() + config.timeout_secs);
    ///
    /// var response: agent.Response = undefined;
    /// const status = stub.Process(&context, &request, &response);
    ///
    /// if (!status.ok()) {
    ///     return error.GrpcError;
    /// }
    ///
    /// if (!response.has_message()) {
    ///     return error.MissingMessage;
    /// }
    ///
    /// return Message.fromProto(allocator, response.message());
    /// ```
    pub fn process(self: *Self, messages: []const Message) !Message {
        // Stub implementation - returns error for now
        _ = self;
        _ = messages;
        return error.NotImplemented;
    }

    /// Process streaming request
    ///
    /// Full implementation would call stub.ProcessStream() and return iterator
    pub fn processStream(self: *Self, messages: []const Message) !StreamIterator {
        _ = self;
        _ = messages;
        return error.NotImplemented;
    }

    /// Get capabilities
    pub fn capabilities(self: *const Self) []const []const u8 {
        _ = self;
        const caps = [_][]const u8{
            "grpc",
            "streaming",
            "binary_protocol",
            "http2",
        };
        return &caps;
    }

    /// Check if gRPC support is available
    pub fn isAvailable() bool {
        // In full implementation, check if gRPC library is linked
        return false; // Stub returns false
    }
};

/// Stream iterator for streaming responses
pub const StreamIterator = struct {
    allocator: Allocator,

    // In full implementation:
    // reader: *grpc.ClientReader,
    // context: *grpc.ClientContext,

    const Self = @This();

    pub fn next(self: *Self) !?Message {
        _ = self;
        return error.NotImplemented;
    }

    pub fn deinit(self: *Self) void {
        _ = self;
    }
};

// Tests
test "GrpcConfig default values" {
    const config = GrpcConfig{
        .url = "localhost:50051",
    };

    try std.testing.expectEqual(false, config.use_tls);
    try std.testing.expectEqual(@as(u32, 30), config.timeout_secs);
    try std.testing.expectEqual(@as(u32, 10), config.connect_timeout_secs);
    try std.testing.expectEqual(@as(u32, 30), config.keepalive_interval_secs);
    try std.testing.expectEqual(@as(usize, 4 * 1024 * 1024), config.max_message_size);
}

test "GrpcAgent init and deinit" {
    const allocator = std.testing.allocator;

    const config = GrpcConfig{
        .url = "localhost:50051",
    };

    var agent = try GrpcAgent.init(allocator, config);
    defer agent.deinit();

    try std.testing.expectEqualStrings("localhost:50051", agent.config.url);
}

test "GrpcAgent capabilities" {
    const allocator = std.testing.allocator;

    const config = GrpcConfig{
        .url = "localhost:50051",
    };

    var agent = try GrpcAgent.init(allocator, config);
    defer agent.deinit();

    const caps = agent.capabilities();
    try std.testing.expectEqual(@as(usize, 4), caps.len);
    try std.testing.expectEqualStrings("grpc", caps[0]);
    try std.testing.expectEqualStrings("streaming", caps[1]);
}

test "GrpcAgent isAvailable" {
    try std.testing.expectEqual(false, GrpcAgent.isAvailable());
}

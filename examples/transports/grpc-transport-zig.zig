///! Example of using gRPC transport for remote agent communication in Zig.
///!
///! This example demonstrates how to use the GrpcAgent to communicate with
///! a remote agent server over gRPC protocol.
///!
///! Prerequisites:
///! 1. Install gRPC C++ library (for @cImport binding)
///! 2. Start a gRPC agent server (see server examples in other languages)
///! 3. Run this example
///!
///! Build:
///! ```
///! zig build-exe examples/transports/grpc-transport-zig.zig \
///!     -I agenkit-zig/src \
///!     --library grpc++
///! ```

const std = @import("std");
const grpc = @import("../../agenkit-zig/src/transports/grpc.zig");
const Message = @import("../../agenkit-zig/src/message.zig").Message;

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    try stdout.print("Agenkit Zig - gRPC Transport Example\n", .{});
    try stdout.print("=====================================\n\n", .{});

    // Basic gRPC example
    try basicGrpcExample(allocator, stdout);

    // Secure gRPC example
    try secureGrpcExample(allocator, stdout);

    // Conversation example
    try conversationExample(allocator, stdout);

    // Timeout example
    try timeoutExample(allocator, stdout);

    // Setup instructions
    try stdout.print("\n=== Setup Instructions ===\n", .{});
    try stdout.print("1. Install gRPC C++ library:\n", .{});
    try stdout.print("   # macOS: brew install grpc\n", .{});
    try stdout.print("   # Linux: apt-get install libgrpc++-dev\n", .{});
    try stdout.print("\n2. Generate proto files:\n", .{});
    try stdout.print("   protoc --zig_out=. proto/agent.proto\n", .{});
    try stdout.print("\n3. Start a gRPC server (Python example):\n", .{});
    try stdout.print("   cd agenkit\n", .{});
    try stdout.print("   python examples/grpc_server_example.py\n", .{});
    try stdout.print("\n4. Run this example:\n", .{});
    try stdout.print("   zig build-exe examples/transports/grpc-transport-zig.zig\n", .{});
}

fn basicGrpcExample(allocator: std.mem.Allocator, writer: anytype) !void {
    try writer.print("\n=== Basic gRPC Example ===\n", .{});

    // Check if gRPC support is available
    if (!grpc.GrpcAgent.isAvailable()) {
        try writer.print("gRPC transport not available (stub implementation).\n", .{});
        try writer.print("Full implementation requires gRPC C++ library binding.\n", .{});
        return;
    }

    const config = grpc.GrpcConfig{
        .url = "localhost:50051",
        .use_tls = false,
        .timeout_secs = 30,
    };

    var agent = try grpc.GrpcAgent.init(allocator, config);
    defer agent.deinit();

    try writer.print("Connected to gRPC server at {s}\n", .{config.url});

    // Create a message
    var messages = std.ArrayList(Message).init(allocator);
    defer messages.deinit();

    const msg = Message.init(allocator, "user", "Hello via gRPC!");
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
}

fn secureGrpcExample(allocator: std.mem.Allocator, writer: anytype) !void {
    try writer.print("\n=== Secure gRPC (TLS) Example ===\n", .{});

    if (!grpc.GrpcAgent.isAvailable()) {
        try writer.print("gRPC transport not available (stub implementation).\n", .{});
        return;
    }

    const config = grpc.GrpcConfig{
        .url = "api.example.com:443",
        .use_tls = true,
        .ca_cert = "/path/to/ca.pem",
        .client_cert = "/path/to/client.pem",
        .client_key = "/path/to/client.key",
        .timeout_secs = 60,
    };

    var agent = try grpc.GrpcAgent.init(allocator, config);
    defer agent.deinit();

    try writer.print("Connected to secure gRPC server at {s}\n", .{config.url});

    var messages = std.ArrayList(Message).init(allocator);
    defer messages.deinit();

    const msg = Message.init(allocator, "user", "Secure message via gRPC");
    try messages.append(msg);

    const response = agent.process(messages.items) catch |err| {
        try writer.print("Error (expected for stub): {}\n", .{err});
        return;
    };
    defer response.deinit();

    try writer.print("Response: {s}\n", .{response.content});
}

fn conversationExample(allocator: std.mem.Allocator, writer: anytype) !void {
    try writer.print("\n=== Multi-turn Conversation via gRPC ===\n", .{});

    if (!grpc.GrpcAgent.isAvailable()) {
        try writer.print("gRPC transport not available (stub implementation).\n", .{});
        return;
    }

    const config = grpc.GrpcConfig{
        .url = "localhost:50051",
        .use_tls = false,
        .timeout_secs = 30,
    };

    var agent = try grpc.GrpcAgent.init(allocator, config);
    defer agent.deinit();

    const questions = [_][]const u8{
        "What is 2 + 2?",
        "What about 10 + 5?",
        "Can you explain the previous answer?",
    };

    for (questions) |question| {
        try writer.print("\nUser: {s}\n", .{question});

        var messages = std.ArrayList(Message).init(allocator);
        defer messages.deinit();

        const msg = Message.init(allocator, "user", question);
        try messages.append(msg);

        const response = agent.process(messages.items) catch |err| {
            try writer.print("Error: {}\n", .{err});
            break;
        };
        defer response.deinit();

        try writer.print("Agent: {s}\n", .{response.content});
    }
}

fn timeoutExample(allocator: std.mem.Allocator, writer: anytype) !void {
    try writer.print("\n=== Timeout Configuration Example ===\n", .{});

    if (!grpc.GrpcAgent.isAvailable()) {
        try writer.print("gRPC transport not available (stub implementation).\n", .{});
        return;
    }

    // Short timeout for testing
    const config = grpc.GrpcConfig{
        .url = "localhost:50051",
        .use_tls = false,
        .timeout_secs = 5, // 5 second timeout
        .connect_timeout_secs = 3, // 3 second connect timeout
    };

    var agent = try grpc.GrpcAgent.init(allocator, config);
    defer agent.deinit();

    var messages = std.ArrayList(Message).init(allocator);
    defer messages.deinit();

    const msg = Message.init(allocator, "user", "This might timeout");
    try messages.append(msg);

    const response = agent.process(messages.items) catch |err| {
        try writer.print("Error (expected for timeout test): {}\n", .{err});
        return;
    };
    defer response.deinit();

    try writer.print("Response: {s}\n", .{response.content});
}

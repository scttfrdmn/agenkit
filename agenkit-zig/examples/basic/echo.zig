//! Echo Agent Example
//!
//! This example demonstrates the basics of using AgentKit in Zig:
//! - Creating messages
//! - Using the EchoAgent
//! - Processing messages
//! - Proper memory management with defer
//! - Error handling
//!
//! Run with: zig build run-echo

const std = @import("std");
const agenkit = @import("agenkit");

pub fn main() !void {
    // Initialize allocator
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Print header
    std.debug.print("\n=== AgentKit Echo Agent Example ===\n\n", .{});

    // Create a user message
    std.debug.print("Creating message...\n", .{});
    var message = try agenkit.Message.withText(
        allocator,
        .user,
        "Hello from Zig! This is a test message.",
    );
    defer message.deinit();

    std.debug.print("Message content: {s}\n", .{try message.contentAsText()});
    std.debug.print("Message role: {s}\n\n", .{@tagName(message.role)});

    // Create an echo agent
    std.debug.print("Creating EchoAgent...\n", .{});
    var echo = try agenkit.EchoAgent.init(allocator);
    defer echo.agent().deinit();

    std.debug.print("Agent name: {s}\n\n", .{echo.agent().name()});

    // Process the message
    std.debug.print("Processing message...\n", .{});
    const result = try echo.agent().process(message);
    var response = try result.unwrap();
    defer response.deinit();

    // Display response
    std.debug.print("Response role: {s}\n", .{@tagName(response.role)});
    std.debug.print("Response content: {s}\n\n", .{try response.contentAsText()});

    // Demonstrate with metadata
    std.debug.print("=== Testing with Metadata ===\n\n", .{});

    var message_with_meta = try agenkit.Message.withText(
        allocator,
        .user,
        "Message with metadata",
    );
    defer message_with_meta.deinit();

    // Add metadata using setMetadata
    try message_with_meta.setMetadata("source", .{ .string = "example" });
    try message_with_meta.setMetadata("example_id", .{ .integer = 1 });

    const result2 = try echo.agent().process(message_with_meta);
    var response2 = try result2.unwrap();
    defer response2.deinit();

    std.debug.print("Response with metadata: {s}\n", .{try response2.contentAsText()});
    std.debug.print("Metadata count: {d}\n\n", .{response2.metadata.object.count()});

    std.debug.print("✓ Example completed successfully!\n\n", .{});
}

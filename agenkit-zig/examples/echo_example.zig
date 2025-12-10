/// Simple Echo Agent Example
///
/// This example demonstrates:
/// - Creating messages with the Message API
/// - Initializing an agent (EchoAgent)
/// - Processing messages through the agent
/// - Handling results and cleanup
const std = @import("std");
const agenkit = @import("agenkit");

pub fn main() !void {
    // Setup allocator
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Print header
    std.debug.print("\n=== Agenkit Zig Echo Agent Example ===\n\n", .{});

    // Create a user message
    std.debug.print("Creating user message...\n", .{});
    var user_msg = try agenkit.Message.withText(
        allocator,
        .user,
        "Hello, Agenkit! This is a test message from Zig.",
    );
    defer user_msg.deinit();

    // Add metadata to the message
    try user_msg.setMetadata("session_id", std.json.Value{ .string = "zig-example-001" });
    try user_msg.setMetadata("timestamp", std.json.Value{ .integer = std.time.timestamp() });

    // Create an echo agent
    std.debug.print("Creating echo agent...\n", .{});
    var echo = try agenkit.EchoAgent.init(allocator);
    defer echo.agent().deinit();

    const agent_iface = echo.agent();
    std.debug.print("Agent name: {s}\n", .{agent_iface.name()});

    // Process the message
    std.debug.print("\nProcessing message...\n", .{});
    const result = try agent_iface.process(user_msg);

    // Check if processing succeeded
    if (result.isOk()) {
        std.debug.print("✓ Processing succeeded!\n\n", .{});

        var response = try result.unwrap();
        defer response.deinit();

        // Print the response
        const response_text = try response.contentAsText();
        std.debug.print("Response: {s}\n", .{response_text});

        // Check metadata was preserved
        if (response.getMetadata("session_id")) |session_id| {
            std.debug.print("Session ID: {s}\n", .{session_id.string});
        }
    } else {
        std.debug.print("✗ Processing failed\n", .{});
        const err = result.unwrapErr();
        std.debug.print("Error: {}\n", .{err});
    }

    std.debug.print("\n=== Example completed successfully ===\n\n", .{});
}

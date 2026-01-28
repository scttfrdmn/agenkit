/// Example demonstrating Anthropic Claude streaming support
///
/// This example shows how to stream responses from Claude in real-time,
/// displaying text as it arrives from the API.
///
/// Run:
///   export ANTHROPIC_API_KEY="your-key-here"
///   zig build run-anthropic-streaming

const std = @import("std");
const agenkit = @import("agenkit");
const AnthropicLLM = agenkit.adapter.anthropic.AnthropicLLM;
const Message = agenkit.Message;
const CallOptions = agenkit.adapter.llm.CallOptions;

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Initialize Anthropic adapter
    var llm_impl = try AnthropicLLM.init(
        allocator,
        "", // Will read from ANTHROPIC_API_KEY env var
        "claude-3-5-sonnet-20241022",
    );
    defer llm_impl.deinit();

    const llm = llm_impl.asLLM();

    std.debug.print("=== Anthropic Claude Streaming Example ===\n\n", .{});
    std.debug.print("Asking Claude to count to 10...\n\n", .{});
    std.debug.print("Response (streaming):\n", .{});
    std.debug.print("{s}\n", .{"-" ** 60});

    // Create message
    var user_msg = try Message.withText(allocator, .user, "Count to 10, one number per line.");
    defer user_msg.deinit();

    const messages = [_]*Message{&user_msg};

    // Set up options
    var options = CallOptions.init(allocator);
    defer options.deinit();
    options.withTemperature(1.0);
    options.withMaxTokens(1024);

    // Stream response
    var full_response = std.ArrayList(u8).init(allocator);
    defer full_response.deinit();

    var stream_iter = try llm.stream(allocator, &messages, &options);
    defer stream_iter.deinit();

    while (try stream_iter.next(allocator)) |chunk| {
        defer chunk.deinit();

        const text = switch (chunk.content) {
            .text => |t| t,
            .structured => "",
        };

        std.debug.print("{s}", .{text});
        try full_response.appendSlice(text);
    }

    std.debug.print("\n{s}\n", .{"-" ** 60});
    std.debug.print("\nFull response length: {} characters\n", .{full_response.items.len});

    // Example 2: Story generation
    std.debug.print("\n\n=== Story Generation Example ===\n\n", .{});
    std.debug.print("Asking Claude to write a short story...\n\n", .{});
    std.debug.print("Response (streaming):\n", .{});
    std.debug.print("{s}\n", .{"-" ** 60});

    var story_msg = try Message.withText(
        allocator,
        .user,
        "Write a very short story (3 sentences) about a robot learning to paint.",
    );
    defer story_msg.deinit();

    const story_messages = [_]*Message{&story_msg};

    full_response.clearRetainingCapacity();

    var story_stream = try llm.stream(allocator, &story_messages, &options);
    defer story_stream.deinit();

    while (try story_stream.next(allocator)) |chunk| {
        defer chunk.deinit();

        const text = switch (chunk.content) {
            .text => |t| t,
            .structured => "",
        };

        std.debug.print("{s}", .{text});
        try full_response.appendSlice(text);
    }

    std.debug.print("\n{s}\n", .{"-" ** 60});
    std.debug.print("\nStreaming complete!\n", .{});
    std.debug.print("Total characters received: {}\n", .{full_response.items.len});

    // Example 3: Early termination
    std.debug.print("\n\n=== Early Termination Example ===\n\n", .{});
    std.debug.print("Streaming with early stop after 50 characters...\n\n", .{});
    std.debug.print("Response (streaming):\n", .{});
    std.debug.print("{s}\n", .{"-" ** 60});

    var essay_msg = try Message.withText(
        allocator,
        .user,
        "Write a long essay about the history of computing.",
    );
    defer essay_msg.deinit();

    const essay_messages = [_]*Message{&essay_msg};

    full_response.clearRetainingCapacity();

    var essay_stream = try llm.stream(allocator, &essay_messages, &options);
    defer essay_stream.deinit();

    while (try essay_stream.next(allocator)) |chunk| {
        defer chunk.deinit();

        const text = switch (chunk.content) {
            .text => |t| t,
            .structured => "",
        };

        std.debug.print("{s}", .{text});
        try full_response.appendSlice(text);

        // Stop after 50 characters
        if (full_response.items.len >= 50) {
            std.debug.print("\n[STOPPED EARLY]", .{});
            break;
        }
    }

    std.debug.print("\n{s}\n", .{"-" ** 60});
    std.debug.print("\nStopped after {} characters\n", .{full_response.items.len});

    std.debug.print("\nAll examples complete!\n", .{});
}

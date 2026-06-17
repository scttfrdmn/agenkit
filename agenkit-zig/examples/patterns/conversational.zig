//! Conversational Pattern Example
//!
//! The Conversational pattern maintains message history across multiple turns,
//! enabling context-aware dialogue.
//!
//! This example demonstrates:
//! - Multi-turn conversations with history
//! - System prompts for agent personality
//! - Context window management
//! - History pruning when limit exceeded
//!
//! Run with: zig build run-conversational

const std = @import("std");
const agenkit = @import("agenkit");

pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== AgentKit Conversational Pattern Example ===\n\n", .{});

    // Example 1: Basic conversation with memory
    std.debug.print("--- Example 1: Context Retention ---\n", .{});
    {
        var agent = try agenkit.patterns.ConversationalAgent.init(
            allocator,
            10, // max_history
            "You are a helpful assistant that remembers previous messages.",
        );
        defer agent.deinit();

        // Turn 1
        std.debug.print("User: My favorite color is blue\n", .{});
        var msg1 = try agenkit.Message.withText(allocator, .user, "My favorite color is blue");
        defer msg1.deinit();

        const result1 = try agent.agent().process(msg1);
        var response1 = try result1.unwrap();
        defer response1.deinit();

        std.debug.print("Assistant: {s}\n\n", .{try response1.contentAsText()});

        // Turn 2 - context from turn 1
        std.debug.print("User: What's my favorite color?\n", .{});
        var msg2 = try agenkit.Message.withText(allocator, .user, "What's my favorite color?");
        defer msg2.deinit();

        const result2 = try agent.agent().process(msg2);
        var response2 = try result2.unwrap();
        defer response2.deinit();

        std.debug.print("Assistant: {s}\n", .{try response2.contentAsText()});
        std.debug.print("History size: {d} messages\n", .{agent.history.items.len});
        std.debug.print("✓ Agent maintains conversation context\n\n", .{});
    }

    // Example 2: Multiple turns building context
    std.debug.print("--- Example 2: Multi-Turn Dialogue ---\n", .{});
    {
        var agent = try agenkit.patterns.ConversationalAgent.init(
            allocator,
            20,
            "You are a math tutor.",
        );
        defer agent.deinit();

        const turns = [_][]const u8{
            "Let's talk about addition",
            "What is 2 + 2?",
            "How about 5 + 3?",
            "Thanks for the help!",
        };

        for (turns, 0..) |turn, i| {
            std.debug.print("Turn {d}: {s}\n", .{ i + 1, turn });

            var msg = try agenkit.Message.withText(allocator, .user, turn);
            defer msg.deinit();

            const result = try agent.agent().process(msg);
            var response = try result.unwrap();
            defer response.deinit();

            std.debug.print("Response: {s}\n", .{try response.contentAsText()});
        }

        std.debug.print("Final history size: {d} messages\n", .{agent.history.items.len});
        std.debug.print("✓ Context builds across turns\n\n", .{});
    }

    // Example 3: History pruning
    std.debug.print("--- Example 3: History Pruning (max 3) ---\n", .{});
    {
        var agent = try agenkit.patterns.ConversationalAgent.init(
            allocator,
            3, // Small limit to force pruning
            null, // No system prompt
        );
        defer agent.deinit();

        std.debug.print("Sending 5 messages with max_history=3...\n", .{});

        for (0..5) |i| {
            const text = try std.fmt.allocPrint(allocator, "Message {d}", .{i + 1});
            defer allocator.free(text);

            var msg = try agenkit.Message.withText(allocator, .user, text);
            defer msg.deinit();

            const result = try agent.agent().process(msg);
            var response = try result.unwrap();
            defer response.deinit();

            std.debug.print("  Turn {d}: history size = {d}\n", .{ i + 1, agent.history.items.len });
        }

        std.debug.print("✓ History automatically pruned to limit\n\n", .{});
    }

    // Example 4: With vs without history
    std.debug.print("--- Example 4: Comparison ---\n", .{});
    {
        var conv_agent = try agenkit.patterns.ConversationalAgent.init(
            allocator,
            10,
            null,
        );
        defer conv_agent.deinit();

        var echo_agent = try agenkit.EchoAgent.init(allocator);
        defer echo_agent.agent().deinit();

        const first_msg_text = "My name is Alice";
        const second_msg_text = "What's my name?";

        // Conversational agent
        std.debug.print("Conversational Agent:\n", .{});
        {
            var msg1 = try agenkit.Message.withText(allocator, .user, first_msg_text);
            defer msg1.deinit();
            const r1 = try conv_agent.agent().process(msg1);
            var resp1 = try r1.unwrap();
            defer resp1.deinit();

            var msg2 = try agenkit.Message.withText(allocator, .user, second_msg_text);
            defer msg2.deinit();
            const result = try conv_agent.agent().process(msg2);
            var response = try result.unwrap();
            defer response.deinit();

            std.debug.print("  Response includes history: {s}\n", .{try response.contentAsText()});
        }

        // Echo agent (no history)
        std.debug.print("Echo Agent (no history):\n", .{});
        {
            var msg1 = try agenkit.Message.withText(allocator, .user, first_msg_text);
            defer msg1.deinit();
            const r1 = try echo_agent.agent().process(msg1);
            var resp1 = try r1.unwrap();
            defer resp1.deinit();

            var msg2 = try agenkit.Message.withText(allocator, .user, second_msg_text);
            defer msg2.deinit();
            const result = try echo_agent.agent().process(msg2);
            var response = try result.unwrap();
            defer response.deinit();

            std.debug.print("  Response has no context: {s}\n", .{try response.contentAsText()});
        }

        std.debug.print("✓ History enables context-aware responses\n\n", .{});
    }

    std.debug.print("=== Conversational Pattern Summary ===\n", .{});
    std.debug.print("✓ Maintains message history across turns\n", .{});
    std.debug.print("✓ System prompts for agent personality\n", .{});
    std.debug.print("✓ Automatic pruning when history exceeds limit\n", .{});
    std.debug.print("✓ System messages always preserved\n", .{});
    std.debug.print("✓ Essential for: chatbots, assistants, tutoring\n", .{});
    std.debug.print("\n✓ Conversational pattern example completed successfully!\n\n", .{});
}

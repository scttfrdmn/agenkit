//! Memory Management Example
//!
//! This example demonstrates:
//! - Different allocator types in Zig
//! - GeneralPurposeAllocator for leak detection
//! - ArenaAllocator for bulk cleanup
//! - Proper defer patterns for cleanup
//! - Memory ownership in agent processing
//! - Best practices for allocator usage
//!
//! Run with: zig build run-memory

const std = @import("std");
const agenkit = @import("agenkit");

pub fn main() !void {
    std.debug.print("\n=== AgentKit Memory Management Example ===\n\n", .{});

    // Example 1: GeneralPurposeAllocator with leak detection
    std.debug.print("--- Example 1: GeneralPurposeAllocator with Leak Detection ---\n", .{});
    {
        var gpa = std.heap.GeneralPurposeAllocator(.{}){};
        defer {
            const leaked = gpa.deinit();
            if (leaked == .leak) {
                std.debug.print("⚠️  Memory leak detected!\n", .{});
            } else {
                std.debug.print("✓ No memory leaks\n", .{});
            }
        }
        const allocator = gpa.allocator();

        var message = try agenkit.Message.withText(
            allocator,
            .user,
            "Testing GPA allocator",
        );
        defer message.deinit();

        var echo = try agenkit.EchoAgent.init(allocator);
        defer echo.agent().deinit();

        const result = try echo.agent().process(message);
        var response = try result.unwrap();
        defer response.deinit();

        std.debug.print("Processed with GPA: {s}\n", .{try response.contentAsText()});
    }
    std.debug.print("\n", .{});

    // Example 2: ArenaAllocator for bulk cleanup
    std.debug.print("--- Example 2: ArenaAllocator for Bulk Cleanup ---\n", .{});
    {
        var gpa = std.heap.GeneralPurposeAllocator(.{}){};
        defer _ = gpa.deinit();
        const backing_allocator = gpa.allocator();

        // Create arena - all allocations can be freed at once
        var arena = std.heap.ArenaAllocator.init(backing_allocator);
        defer arena.deinit(); // Frees ALL arena allocations at once
        const allocator = arena.allocator();

        std.debug.print("Creating multiple messages with arena...\n", .{});

        // Create several messages - no individual cleanup needed
        var count: usize = 0;
        for (0..5) |i| {
            _ = try agenkit.Message.withText(
                allocator,
                .user,
                try std.fmt.allocPrint(allocator, "Message {d}", .{i}),
            );
            count += 1;
        }

        std.debug.print("Created {d} messages\n", .{count});
        std.debug.print("All will be freed at once when arena deinits\n", .{});
    }
    std.debug.print("✓ Arena cleanup complete\n\n", .{});

    // Example 3: Memory ownership patterns
    std.debug.print("--- Example 3: Memory Ownership Patterns ---\n", .{});
    {
        var gpa = std.heap.GeneralPurposeAllocator(.{}){};
        defer _ = gpa.deinit();
        const allocator = gpa.allocator();

        // Pattern 1: Caller owns message
        std.debug.print("Pattern 1: Caller retains ownership\n", .{});
        var input_msg = try agenkit.Message.withText(
            allocator,
            .user,
            "Caller owns this",
        );
        defer input_msg.deinit(); // Caller cleans up

        var echo = try agenkit.EchoAgent.init(allocator);
        defer echo.agent().deinit();

        // Agent creates a NEW message - caller must clean it up
        const result = try echo.agent().process(input_msg);
        var output_msg = try result.unwrap();
        defer output_msg.deinit(); // Caller cleans up response too

        std.debug.print("  Input owned by caller: {s}\n", .{try input_msg.contentAsText()});
        std.debug.print("  Output owned by caller: {s}\n", .{try output_msg.contentAsText()});

        // Pattern 2: Clear ownership with defer
        std.debug.print("\nPattern 2: Defer ensures cleanup\n", .{});
        {
            var temp_message = try agenkit.Message.withText(
                allocator,
                .user,
                "Scoped message",
            );
            defer temp_message.deinit(); // Always called when scope exits

            std.debug.print("  Message created in scope: {s}\n", .{try temp_message.contentAsText()});
            // temp_message automatically cleaned up here
        }
        std.debug.print("  ✓ Scoped message cleaned up\n", .{});
    }
    std.debug.print("\n", .{});

    // Example 4: Memory-efficient agent chains
    std.debug.print("--- Example 4: Memory-Efficient Agent Chains ---\n", .{});
    {
        var gpa = std.heap.GeneralPurposeAllocator(.{}){};
        defer _ = gpa.deinit();
        const allocator = gpa.allocator();

        // Create agents
        var agent1 = try agenkit.EchoAgent.init(allocator);
        defer agent1.agent().deinit();

        var agent2 = try agenkit.EchoAgent.init(allocator);
        defer agent2.agent().deinit();

        var agent3 = try agenkit.EchoAgent.init(allocator);
        defer agent3.agent().deinit();

        // Process through chain, cleaning up intermediate results
        var input = try agenkit.Message.withText(
            allocator,
            .user,
            "Pipeline input",
        );
        defer input.deinit();

        std.debug.print("Processing through 3-agent chain...\n", .{});

        // Agent 1
        const result1 = try agent1.agent().process(input);
        var output1 = try result1.unwrap();
        defer output1.deinit(); // Clean up intermediate result

        // Agent 2
        const result2 = try agent2.agent().process(output1);
        var output2 = try result2.unwrap();
        defer output2.deinit(); // Clean up intermediate result

        // Agent 3
        const result3 = try agent3.agent().process(output2);
        var final_output = try result3.unwrap();
        defer final_output.deinit(); // Clean up final result

        std.debug.print("Final output: {s}\n", .{try final_output.contentAsText()});
        std.debug.print("✓ All intermediate results cleaned up\n", .{});
    }
    std.debug.print("\n", .{});

    // Example 5: Detecting memory leaks intentionally
    std.debug.print("--- Example 5: Memory Leak Detection ---\n", .{});
    {
        var gpa = std.heap.GeneralPurposeAllocator(.{}){};
        const allocator = gpa.allocator();

        // Create a message but DON'T clean it up (intentional leak for demo)
        std.debug.print("Creating message without cleanup (intentional leak)...\n", .{});
        _ = try agenkit.Message.withText(
            allocator,
            .user,
            "This will leak!",
        );
        // Note: No defer message.deinit() here!

        const leaked = gpa.deinit();
        if (leaked == .leak) {
            std.debug.print("✓ Leak detected as expected!\n", .{});
            std.debug.print("  (This demonstrates GPA's leak detection)\n", .{});
        }
    }
    std.debug.print("\n", .{});

    std.debug.print("=== Memory Management Best Practices ===\n", .{});
    std.debug.print("1. Always use defer for cleanup\n", .{});
    std.debug.print("2. Use GeneralPurposeAllocator during development\n", .{});
    std.debug.print("3. Consider ArenaAllocator for short-lived operations\n", .{});
    std.debug.print("4. Clear ownership: who allocates, who frees?\n", .{});
    std.debug.print("5. Clean up intermediate results in chains\n", .{});
    std.debug.print("\n✓ Memory management example completed successfully!\n\n", .{});
}

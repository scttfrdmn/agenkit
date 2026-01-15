/// Example: Durable Agent with Automatic Checkpointing
///
/// Demonstrates:
///   - Creating a DurableAgent with automatic checkpointing
///   - Processing messages with state persistence
///   - Checkpoint creation and resumption
///   - Error recovery with checkpoint rollback
///
/// Build: zig build-exe durable_agent.zig -I../../src
/// Run: ./durable_agent

const std = @import("std");
const agenkit = @import("agenkit");

const Agent = agenkit.Agent;
const Message = agenkit.Message;
const DurableAgent = agenkit.infrastructure.checkpointing.DurableAgent;
const InMemoryStorage = agenkit.infrastructure.checkpointing.InMemoryStorage;

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Durable Agent Example ===\n\n", .{});

    // Step 1: Create storage backend
    std.debug.print("1. Creating in-memory storage...\n", .{});
    var storage = InMemoryStorage.init(allocator);
    defer storage.deinit();

    // Step 2: Create base agent (EchoAgent for demo)
    std.debug.print("2. Creating base echo agent...\n", .{});
    const EchoAgent = agenkit.EchoAgent;
    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    // Step 3: Create durable agent with automatic checkpointing every 2 steps
    std.debug.print("3. Creating durable agent (checkpoint every 2 steps)...\n\n", .{});
    var durable = try DurableAgent.init(
        allocator,
        echo.agent(),
        storage.storage(),
        2, // Checkpoint every 2 steps
        true, // Auto-resume on restart
    );
    defer durable.deinit();

    const session_id = "demo-session";

    // Step 4: Process multiple messages (automatic checkpointing)
    std.debug.print("4. Processing messages with automatic checkpointing:\n", .{});

    // Message 1
    var msg1 = try Message.withText(allocator, .user, "Hello, agent!");
    defer msg1.deinit();

    std.debug.print("   Processing: \"{s}\"\n", .{try msg1.contentAsText()});
    const result1 = try durable.processWithSession(msg1, session_id);
    var response1 = try result1.unwrap();
    std.debug.print("   Response: \"{s}\"\n", .{try response1.contentAsText()});
    response1.deinit();

    // Message 2 - this should trigger a checkpoint
    var msg2 = try Message.withText(allocator, .user, "How are you?");
    defer msg2.deinit();

    std.debug.print("   Processing: \"{s}\"\n", .{try msg2.contentAsText()});
    const result2 = try durable.processWithSession(msg2, session_id);
    var response2 = try result2.unwrap();
    std.debug.print("   Response: \"{s}\"\n", .{try response2.contentAsText()});
    std.debug.print("   ✅ Checkpoint created automatically!\n", .{});
    response2.deinit();

    // Message 3
    var msg3 = try Message.withText(allocator, .user, "Tell me more");
    defer msg3.deinit();

    std.debug.print("   Processing: \"{s}\"\n", .{try msg3.contentAsText()});
    const result3 = try durable.processWithSession(msg3, session_id);
    var response3 = try result3.unwrap();
    std.debug.print("   Response: \"{s}\"\n\n", .{try response3.contentAsText()});
    response3.deinit();

    // Step 5: Manual checkpoint
    std.debug.print("5. Creating manual checkpoint...\n", .{});
    const checkpoint_id = try durable.checkpoint(session_id, null);
    defer allocator.free(checkpoint_id);
    std.debug.print("   Checkpoint ID: {s}\n\n", .{checkpoint_id});

    // Step 6: Get session state before reset
    std.debug.print("6. Current session state:\n", .{});
    if (durable.getState(session_id)) |state| {
        std.debug.print("   State keys: ", .{});
        var iter = state.object.iterator();
        while (iter.next()) |entry| {
            std.debug.print("{s} ", .{entry.key_ptr.*});
        }
        std.debug.print("\n\n", .{});
    }

    // Step 7: Simulate failure - reset session
    std.debug.print("7. Simulating failure - resetting session...\n", .{});
    durable.resetSession(session_id);
    std.debug.print("   Session cleared!\n\n", .{});

    // Step 8: Restore from checkpoint
    std.debug.print("8. Restoring from latest checkpoint...\n", .{});
    const restored_state = try durable.resumeFromCheckpoint(session_id, null);
    if (restored_state) |state| {
        std.debug.print("   ✅ State restored successfully!\n", .{});
        std.debug.print("   Restored keys: ", .{});
        var iter = state.object.iterator();
        while (iter.next()) |entry| {
            std.debug.print("{s} ", .{entry.key_ptr.*});
        }
        std.debug.print("\n\n", .{});
    } else {
        std.debug.print("   ⚠️  No checkpoint found\n\n", .{});
    }

    // Step 9: Continue processing after restoration
    std.debug.print("9. Continuing after restoration:\n", .{});
    var msg4 = try Message.withText(allocator, .user, "Are we back?");
    defer msg4.deinit();

    std.debug.print("   Processing: \"{s}\"\n", .{try msg4.contentAsText()});
    const result4 = try durable.processWithSession(msg4, session_id);
    var response4 = try result4.unwrap();
    std.debug.print("   Response: \"{s}\"\n", .{try response4.contentAsText()});
    std.debug.print("   ✅ Processing resumed successfully!\n\n", .{});
    response4.deinit();

    // Step 10: Get statistics
    std.debug.print("10. Session statistics:\n", .{});
    var stats = try durable.getSessionStats(session_id);
    defer stats.object.deinit();

    if (stats.object.get("total_checkpoints")) |total| {
        std.debug.print("   Total checkpoints: {d}\n", .{total.integer});
    }
    if (stats.object.get("current_step")) |step| {
        std.debug.print("   Current step: {d}\n", .{step.integer});
    }
    if (stats.object.get("message_count")) |count| {
        std.debug.print("   Message count: {d}\n", .{count.integer});
    }

    std.debug.print("\n=== Example Complete ===\n\n", .{});
}

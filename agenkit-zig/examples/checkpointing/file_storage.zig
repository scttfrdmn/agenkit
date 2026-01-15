/// Example: File-Based Checkpoint Storage
///
/// Demonstrates:
///   - Using FileStorage for persistent checkpoints
///   - Checkpoints survive program restarts
///   - Managing checkpoint files and directories
///   - Pruning old checkpoints
///
/// Build: zig build-exe file_storage.zig -I../../src
/// Run: ./file_storage

const std = @import("std");
const agenkit = @import("agenkit");

const Agent = agenkit.Agent;
const Message = agenkit.Message;
const DurableAgent = agenkit.infrastructure.checkpointing.DurableAgent;
const FileStorage = agenkit.infrastructure.checkpointing.FileStorage;

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== File Storage Example ===\n\n", .{});

    const checkpoint_dir = "./checkpoints_demo";

    // Step 1: Create file storage
    std.debug.print("1. Creating file storage in: {s}/\n", .{checkpoint_dir});
    var storage = try FileStorage.init(allocator, checkpoint_dir);
    defer storage.deinit();
    std.debug.print("   ✅ Storage directory created\n\n", .{});

    // Step 2: Create base agent
    std.debug.print("2. Creating base echo agent...\n", .{});
    const EchoAgent = agenkit.EchoAgent;
    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    // Step 3: Create durable agent with file storage
    std.debug.print("3. Creating durable agent with file storage...\n\n", .{});
    var durable = try DurableAgent.init(
        allocator,
        echo.agent(),
        storage.storage(),
        3, // Checkpoint every 3 steps
        false, // Manual resumption for this demo
    );
    defer durable.deinit();

    const session_id = "persistent-session";

    // Step 4: Process messages and create checkpoints
    std.debug.print("4. Processing messages and creating checkpoints:\n", .{});

    const messages = [_][]const u8{
        "First message",
        "Second message",
        "Third message",
        "Fourth message - checkpoint triggered",
        "Fifth message",
    };

    for (messages) |text| {
        var msg = try Message.withText(allocator, .user, text);
        defer msg.deinit();

        std.debug.print("   Processing: \"{s}\"\n", .{text});
        const result = try durable.processWithSession(msg, session_id);
        var response = try result.unwrap();
        response.deinit();
    }
    std.debug.print("   ✅ All messages processed\n\n", .{});

    // Step 5: List checkpoint files
    std.debug.print("5. Listing checkpoint files:\n", .{});
    const checkpoints = try durable.listCheckpoints(session_id, 0);
    defer {
        for (checkpoints) |cp| {
            cp.deinit();
            allocator.destroy(cp);
        }
        allocator.free(checkpoints);
    }

    std.debug.print("   Found {d} checkpoints:\n", .{checkpoints.len});
    for (checkpoints, 0..) |checkpoint, i| {
        std.debug.print("   [{d}] ID: {s}\n", .{ i + 1, checkpoint.checkpoint_id });
        std.debug.print("       Step: {d}\n", .{checkpoint.step_number});
        std.debug.print("       Timestamp: {d}\n", .{checkpoint.timestamp});

        // Verify file exists
        const file_path = try std.fmt.allocPrint(
            allocator,
            "{s}/{s}/{s}.json",
            .{ checkpoint_dir, session_id, checkpoint.checkpoint_id },
        );
        defer allocator.free(file_path);

        const file = std.fs.cwd().openFile(file_path, .{}) catch |err| {
            std.debug.print("       ⚠️  File not found: {}\n", .{err});
            continue;
        };
        file.close();
        std.debug.print("       ✅ File exists: {s}\n", .{file_path});
    }
    std.debug.print("\n", .{});

    // Step 6: Get session statistics
    std.debug.print("6. Session statistics:\n", .{});
    var stats = try durable.getSessionStats(session_id);
    defer stats.object.deinit();

    if (stats.object.get("total_checkpoints")) |total| {
        std.debug.print("   Total checkpoints: {d}\n", .{total.integer});
    }
    if (stats.object.get("first_step")) |step| {
        std.debug.print("   First checkpoint step: {d}\n", .{step.integer});
    }
    if (stats.object.get("latest_step")) |step| {
        std.debug.print("   Latest checkpoint step: {d}\n", .{step.integer});
    }
    if (stats.object.get("time_span_seconds")) |span| {
        std.debug.print("   Time span: {d:.2}s\n", .{span.float});
    }
    std.debug.print("\n", .{});

    // Step 7: Demonstrate restoration
    std.debug.print("7. Simulating program restart...\n", .{});
    std.debug.print("   Resetting in-memory session...\n", .{});
    durable.resetSession(session_id);

    std.debug.print("   Restoring from disk checkpoint...\n", .{});
    const restored_state = try durable.resumeFromCheckpoint(session_id, null);

    if (restored_state) |state| {
        std.debug.print("   ✅ Session restored from persistent storage!\n", .{});
        if (state.object.get("message_count")) |count| {
            std.debug.print("   Message count: {d}\n", .{count.integer});
        }
    } else {
        std.debug.print("   ⚠️  No checkpoint found\n", .{});
    }
    std.debug.print("\n", .{});

    // Step 8: Prune old checkpoints (keep only 2 most recent)
    std.debug.print("8. Pruning old checkpoints (keeping 2 most recent):\n", .{});
    const deleted_count = try durable.deleteCheckpoints(session_id);
    std.debug.print("   ✅ Deleted {d} checkpoints\n\n", .{deleted_count});

    // Step 9: Show cleanup instructions
    std.debug.print("9. Cleanup:\n", .{});
    std.debug.print("   Checkpoint files are stored in: {s}/\n", .{checkpoint_dir});
    std.debug.print("   To clean up: rm -rf {s}/\n", .{checkpoint_dir});

    std.debug.print("\n=== Example Complete ===\n\n", .{});
    std.debug.print("Note: Checkpoints persist on disk and will be available after program restart.\n", .{});
    std.debug.print("Run this example again to see restoration from disk!\n\n", .{});
}

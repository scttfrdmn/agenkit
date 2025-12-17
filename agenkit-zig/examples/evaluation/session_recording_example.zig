/// Session Recording Example
///
/// This example demonstrates:
/// - Recording agent interactions
/// - Session trace management
/// - Replaying recorded sessions
/// - Exporting to JSON
///
/// Run with: zig build run-evaluation-recording

const std = @import("std");
const agenkit = @import("agenkit");
const evaluation = agenkit.evaluation;

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n{s}\n", .{"=" ** 70});
    std.debug.print("Session Recording Example\n", .{});
    std.debug.print("{s}\n\n", .{"=" ** 70});

    // ========================================================================
    // Step 1: Create Recorder
    // ========================================================================
    std.debug.print("Step 1: Initializing session recorder...\n", .{});

    const recorder = try evaluation.SessionRecorder.init(allocator);
    defer recorder.deinit();

    std.debug.print("  ✓ Recorder initialized\n\n", .{});

    // ========================================================================
    // Step 2: Record Multiple Sessions
    // ========================================================================
    std.debug.print("Step 2: Recording sessions...\n", .{});

    // Session 1: Math tutor
    try recorder.startRecording("math-tutor-001");
    std.debug.print("  → Started recording: math-tutor-001\n", .{});

    var interaction1 = try evaluation.Interaction.init(
        allocator,
        "What is the derivative of x²?",
        "The derivative of x² is 2x",
        45,
    );
    try interaction1.addMetadata("model", "gpt-4");
    try interaction1.addMetadata("temperature", "0.7");
    try recorder.recordInteraction("math-tutor-001", interaction1);
    interaction1.deinit();

    var interaction2 = try evaluation.Interaction.init(
        allocator,
        "Explain the chain rule",
        "The chain rule states that d/dx[f(g(x))] = f'(g(x)) × g'(x)",
        120,
    );
    try interaction2.addMetadata("model", "gpt-4");
    try recorder.recordInteraction("math-tutor-001", interaction2);
    interaction2.deinit();

    try recorder.stopRecording("math-tutor-001");
    std.debug.print("  ← Stopped recording: math-tutor-001 (2 interactions)\n", .{});

    // Session 2: Code review
    try recorder.startRecording("code-review-001");
    std.debug.print("  → Started recording: code-review-001\n", .{});

    var interaction3 = try evaluation.Interaction.init(
        allocator,
        "Review this function: def add(a, b): return a + b",
        "The function looks good. Simple and correct. Consider adding type hints.",
        85,
    );
    try interaction3.addMetadata("model", "claude-3-sonnet");
    try recorder.recordInteraction("code-review-001", interaction3);
    interaction3.deinit();

    try recorder.stopRecording("code-review-001");
    std.debug.print("  ← Stopped recording: code-review-001 (1 interaction)\n\n", .{});

    // ========================================================================
    // Step 3: Inspect Traces
    // ========================================================================
    std.debug.print("Step 3: Inspecting recorded traces...\n", .{});
    std.debug.print("{s}\n", .{"-" ** 70});

    const trace1 = recorder.getTrace("math-tutor-001").?;
    std.debug.print("Session: {s}\n", .{trace1.session_id});
    std.debug.print("  Interactions: {d}\n", .{trace1.interactionCount()});
    std.debug.print("  Duration: {d:.2}s\n", .{trace1.duration()});
    std.debug.print("  Avg Interaction Time: {d:.1}ms\n", .{trace1.avgInteractionDuration()});

    const trace2 = recorder.getTrace("code-review-001").?;
    std.debug.print("\nSession: {s}\n", .{trace2.session_id});
    std.debug.print("  Interactions: {d}\n", .{trace2.interactionCount()});
    std.debug.print("  Duration: {d:.2}s\n", .{trace2.duration()});
    std.debug.print("  Avg Interaction Time: {d:.1}ms\n", .{trace2.avgInteractionDuration()});

    std.debug.print("{s}\n\n", .{"-" ** 70});

    // ========================================================================
    // Step 4: Replay Session
    // ========================================================================
    std.debug.print("Step 4: Replaying session...\n", .{});

    const replay = try evaluation.SessionReplay.init(allocator, trace1);
    defer replay.deinit();

    var interaction_num: usize = 1;
    while (replay.next()) |interaction| {
        std.debug.print("  [{d}] Input: {s}\n", .{ interaction_num, interaction.input });
        std.debug.print("      Output: {s}\n", .{interaction.output});
        std.debug.print("      Duration: {d}ms\n", .{interaction.duration_ms});
        std.debug.print("      Progress: {d:.0}%\n\n", .{replay.progress() * 100.0});
        interaction_num += 1;
    }

    try std.testing.expect(replay.isComplete());
    std.debug.print("  ✓ Replay complete\n\n", .{});

    // ========================================================================
    // Step 5: Replay Again (Reset)
    // ========================================================================
    std.debug.print("Step 5: Resetting and replaying again...\n", .{});

    replay.reset();
    var count: usize = 0;
    while (replay.next()) |_| {
        count += 1;
    }

    std.debug.print("  ✓ Replayed {d} interactions\n\n", .{count});

    // ========================================================================
    // Step 6: Recorder Statistics
    // ========================================================================
    std.debug.print("Step 6: Recorder statistics...\n", .{});
    std.debug.print("{s}\n", .{"-" ** 70});

    const stats = recorder.getStats();
    std.debug.print("Total Sessions: {d}\n", .{stats.total_sessions});
    std.debug.print("Active Sessions: {d}\n", .{stats.active_sessions});
    std.debug.print("Total Interactions: {d}\n", .{stats.total_interactions});
    std.debug.print("Total Duration: {d:.2}s\n", .{stats.total_duration_seconds});

    std.debug.print("{s}\n\n", .{"-" ** 70});

    // ========================================================================
    // Step 7: Export to JSON
    // ========================================================================
    std.debug.print("Step 7: Exporting to JSON...\n", .{});

    const export_path = "/tmp/agenkit_sessions.json";
    try recorder.saveToFile(export_path);

    std.debug.print("  ✓ Exported to: {s}\n\n", .{export_path});

    // Read and display
    const file = try std.fs.cwd().openFile(export_path, .{});
    defer file.close();

    const content = try file.readToEndAlloc(allocator, 10000);
    defer allocator.free(content);

    std.debug.print("  JSON Content:\n", .{});
    std.debug.print("  {s}\n\n", .{content});

    // Clean up
    try std.fs.cwd().deleteFile(export_path);

    // ========================================================================
    // Summary
    // ========================================================================
    std.debug.print("Summary:\n", .{});
    std.debug.print("  ✓ Session recording (start/stop)\n", .{});
    std.debug.print("  ✓ Interaction capture with metadata\n", .{});
    std.debug.print("  ✓ Trace inspection and analysis\n", .{});
    std.debug.print("  ✓ Session replay\n", .{});
    std.debug.print("  ✓ Reset and replay\n", .{});
    std.debug.print("  ✓ Statistics collection\n", .{});
    std.debug.print("  ✓ JSON export\n", .{});

    std.debug.print("\nUse Cases:\n", .{});
    std.debug.print("  • Debugging agent behavior\n", .{});
    std.debug.print("  • Creating test fixtures from real interactions\n", .{});
    std.debug.print("  • Performance analysis\n", .{});
    std.debug.print("  • A/B testing with replay\n", .{});
    std.debug.print("  • Compliance and audit trails\n", .{});

    std.debug.print("\n{s}\n", .{"=" ** 70});
}

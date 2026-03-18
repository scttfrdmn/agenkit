/// Property-based tests for Message types
///
/// Verifies invariants of Message, Role, Content, and Result types
/// using random inputs. Each property runs 50 times with varied data.
///
/// Run with: zig build test

const std = @import("std");
const testing = std.testing;
const agenkit = @import("agenkit");
const Message = agenkit.Message;
const Role = agenkit.Role;
const Content = agenkit.Content;
const Result = agenkit.Result;
const AgentError = agenkit.AgentError;

const framework = @import("framework.zig");

const ITERATIONS: u32 = 50;
const SEED: u64 = 0xdeadbeef;

// ---------------------------------------------------------------------------
// Property 1: role survives roundtrip
// ---------------------------------------------------------------------------

fn propRoleSurvivesRoundtrip(rng: std.Random, allocator: std.mem.Allocator) !void {
    const role = framework.randomRole(rng);
    var msg = try Message.withText(allocator, role, "hello");
    defer msg.deinit();
    try testing.expectEqual(role, msg.role);
}

test "role_survives_roundtrip" {
    try framework.runProperty(
        "role_survives_roundtrip",
        ITERATIONS,
        SEED,
        testing.allocator,
        propRoleSurvivesRoundtrip,
    );
}

// ---------------------------------------------------------------------------
// Property 2: text content survives creation
// ---------------------------------------------------------------------------

fn propTextContentSurvivesCreation(rng: std.Random, allocator: std.mem.Allocator) !void {
    const text = try framework.randomText(rng, allocator, 256);
    defer allocator.free(text);

    var msg = try Message.withText(allocator, .user, text);
    defer msg.deinit();

    const out = try msg.contentAsText();
    try testing.expectEqualStrings(text, out);
}

test "text_content_survives_creation" {
    try framework.runProperty(
        "text_content_survives_creation",
        ITERATIONS,
        SEED + 1,
        testing.allocator,
        propTextContentSurvivesCreation,
    );
}

// ---------------------------------------------------------------------------
// Property 3: empty text is valid
// ---------------------------------------------------------------------------

fn propEmptyTextIsValid(_: std.Random, allocator: std.mem.Allocator) !void {
    var msg = try Message.withText(allocator, .assistant, "");
    defer msg.deinit();

    const out = try msg.contentAsText();
    try testing.expectEqualStrings("", out);
}

test "empty_text_is_valid" {
    try framework.runProperty(
        "empty_text_is_valid",
        ITERATIONS,
        SEED + 2,
        testing.allocator,
        propEmptyTextIsValid,
    );
}

// ---------------------------------------------------------------------------
// Property 4: unicode text preserved
// ---------------------------------------------------------------------------

fn propUnicodeTextPreserved(_: std.Random, allocator: std.mem.Allocator) !void {
    // Use a fixed unicode string with emoji, CJK, and Cyrillic
    const unicode_text = "Hello 世界 🌍 мир";

    var msg = try Message.withText(allocator, .user, unicode_text);
    defer msg.deinit();

    const out = try msg.contentAsText();
    try testing.expectEqualStrings(unicode_text, out);
}

test "unicode_text_preserved" {
    try framework.runProperty(
        "unicode_text_preserved",
        ITERATIONS,
        SEED + 3,
        testing.allocator,
        propUnicodeTextPreserved,
    );
}

// ---------------------------------------------------------------------------
// Property 5: long text preserved (up to 64KB)
// ---------------------------------------------------------------------------

fn propLongTextPreserved(rng: std.Random, allocator: std.mem.Allocator) !void {
    // Generate text between 1KB and 64KB
    const len = rng.intRangeAtMost(usize, 1024, 64 * 1024);
    const text = try allocator.alloc(u8, len);
    defer allocator.free(text);
    @memset(text, 'a');

    var msg = try Message.withText(allocator, .user, text);
    defer msg.deinit();

    const out = try msg.contentAsText();
    try testing.expectEqual(len, out.len);
    try testing.expectEqualStrings(text, out);
}

test "long_text_preserved" {
    try framework.runProperty(
        "long_text_preserved",
        ITERATIONS,
        SEED + 4,
        testing.allocator,
        propLongTextPreserved,
    );
}

// ---------------------------------------------------------------------------
// Property 6: all Role enum values are valid
// ---------------------------------------------------------------------------

fn propRoleEnumAllValues(_: std.Random, allocator: std.mem.Allocator) !void {
    const roles = [_]Role{ .user, .assistant, .system, .tool, .agent };
    for (roles) |role| {
        var msg = try Message.withText(allocator, role, "test");
        defer msg.deinit();
        try testing.expectEqual(role, msg.role);
    }
}

test "role_enum_all_values" {
    try framework.runProperty(
        "role_enum_all_values",
        ITERATIONS,
        SEED + 5,
        testing.allocator,
        propRoleEnumAllValues,
    );
}

// ---------------------------------------------------------------------------
// Property 7: message deinit is safe
// ---------------------------------------------------------------------------

fn propMessageDeinitIsSafe(rng: std.Random, allocator: std.mem.Allocator) !void {
    const role = framework.randomRole(rng);
    const text = try framework.randomText(rng, allocator, 128);
    defer allocator.free(text);

    var msg = try Message.withText(allocator, role, text);
    // deinit must not panic — no defer, called explicitly
    msg.deinit();
}

test "message_deinit_is_safe" {
    try framework.runProperty(
        "message_deinit_is_safe",
        ITERATIONS,
        SEED + 6,
        testing.allocator,
        propMessageDeinitIsSafe,
    );
}

// ---------------------------------------------------------------------------
// Property 8: multiple messages are independent (no shared memory)
// ---------------------------------------------------------------------------

fn propMultipleMessagesIndependent(rng: std.Random, allocator: std.mem.Allocator) !void {
    const text_a = try framework.randomText(rng, allocator, 64);
    defer allocator.free(text_a);
    const text_b = try framework.randomText(rng, allocator, 64);
    defer allocator.free(text_b);

    var msg_a = try Message.withText(allocator, .user, text_a);
    defer msg_a.deinit();
    var msg_b = try Message.withText(allocator, .assistant, text_b);
    defer msg_b.deinit();

    // Each message should have its own content slice (different pointers)
    const out_a = try msg_a.contentAsText();
    const out_b = try msg_b.contentAsText();

    try testing.expectEqualStrings(text_a, out_a);
    try testing.expectEqualStrings(text_b, out_b);
}

test "multiple_messages_independent" {
    try framework.runProperty(
        "multiple_messages_independent",
        ITERATIONS,
        SEED + 7,
        testing.allocator,
        propMultipleMessagesIndependent,
    );
}

// ---------------------------------------------------------------------------
// Property 9: assistant role roundtrip
// ---------------------------------------------------------------------------

fn propAssistantRoleRoundtrip(_: std.Random, allocator: std.mem.Allocator) !void {
    var msg = try Message.withText(allocator, .assistant, "response text");
    defer msg.deinit();
    try testing.expectEqual(Role.assistant, msg.role);
}

test "assistant_role_roundtrip" {
    try framework.runProperty(
        "assistant_role_roundtrip",
        ITERATIONS,
        SEED + 8,
        testing.allocator,
        propAssistantRoleRoundtrip,
    );
}

// ---------------------------------------------------------------------------
// Property 10: content type discriminant preserved
// ---------------------------------------------------------------------------

fn propContentTypeDiscriminantPreserved(rng: std.Random, allocator: std.mem.Allocator) !void {
    const text = try framework.randomText(rng, allocator, 32);
    defer allocator.free(text);

    var msg = try Message.withText(allocator, .user, text);
    defer msg.deinit();

    // Text content should have .text discriminant, not .structured
    try testing.expect(msg.content == .text);
    try testing.expect(msg.content != .structured);
}

test "content_type_discriminant_preserved" {
    try framework.runProperty(
        "content_type_discriminant_preserved",
        ITERATIONS,
        SEED + 9,
        testing.allocator,
        propContentTypeDiscriminantPreserved,
    );
}

// ---------------------------------------------------------------------------
// Property 11: agent Result.ok wraps message
// ---------------------------------------------------------------------------

fn propAgentResultOkWrapsMessage(rng: std.Random, allocator: std.mem.Allocator) !void {
    const role = framework.randomRole(rng);
    const text = try framework.randomText(rng, allocator, 64);
    defer allocator.free(text);

    const inner_msg = try Message.withText(allocator, role, text);
    const result = Result{ .ok = inner_msg };

    // Verify the Result is ok
    try testing.expect(result.isOk());
    try testing.expect(!result.isErr());

    // unwrap should give back the message with same role and content
    var unwrapped = try result.unwrap();
    defer unwrapped.deinit();

    try testing.expectEqual(role, unwrapped.role);
    const out = try unwrapped.contentAsText();
    try testing.expectEqualStrings(text, out);
}

test "agent_result_ok_wraps_message" {
    try framework.runProperty(
        "agent_result_ok_wraps_message",
        ITERATIONS,
        SEED + 10,
        testing.allocator,
        propAgentResultOkWrapsMessage,
    );
}

// ---------------------------------------------------------------------------
// Property 12: agent Result.err wraps error
// ---------------------------------------------------------------------------

fn propAgentResultErrWrapsError(rng: std.Random, allocator: std.mem.Allocator) !void {
    _ = allocator;

    // Pick a random AgentError
    const errors = [_]AgentError{
        AgentError.ProcessingFailed,
        AgentError.InvalidInput,
        AgentError.Timeout,
        AgentError.Cancelled,
        AgentError.NotImplemented,
    };
    const idx = rng.intRangeAtMost(usize, 0, errors.len - 1);
    const err = errors[idx];

    const result = Result{ .err = err };

    try testing.expect(!result.isOk());
    try testing.expect(result.isErr());
    try testing.expectEqual(err, result.unwrapErr());
}

test "agent_result_err_wraps_error" {
    try framework.runProperty(
        "agent_result_err_wraps_error",
        ITERATIONS,
        SEED + 11,
        testing.allocator,
        propAgentResultErrWrapsError,
    );
}

//! Typed token usage for LLM adapter responses.
//!
//! Adapters record token counts in `Message.metadata["usage"]` as a
//! `std.json.Value` object, but key names differ between the
//! prompt_tokens/completion_tokens convention and the Anthropic
//! input_tokens/output_tokens convention. `usageFromMessage` normalizes both
//! into one struct so cost-metering and budgeting layers consume a single shape.
//!
//! Mirrors the Go reference (agenkit-go/adapter/llm/usage.go).

const std = @import("std");
const Message = @import("../message.zig").Message;

/// Normalized, typed token usage.
///
/// Fields are 0 when the provider does not report them. The cache fields are
/// provider-dependent (e.g. Anthropic prompt caching, including via Bedrock) and
/// are 0 when caching is inactive.
pub const Usage = struct {
    prompt_tokens: i64 = 0,
    completion_tokens: i64 = 0,
    total_tokens: i64 = 0,
    /// Prompt tokens served from a provider cache (billed at a reduced rate).
    cache_read_tokens: i64 = 0,
    /// Prompt tokens written to a provider cache on this request.
    cache_creation_tokens: i64 = 0,
};

/// Coerce a json.Value number to i64; 0 for non-numbers.
fn toI64(value: std.json.Value) i64 {
    return switch (value) {
        .integer => |n| n,
        .float => |f| @intFromFloat(f),
        else => 0,
    };
}

/// Return the first present integer-valued key in `obj`, or 0.
fn pick(obj: std.json.ObjectMap, keys: []const []const u8) i64 {
    for (keys) |key| {
        if (obj.get(key)) |value| {
            const n = toI64(value);
            if (n != 0) return n;
        }
    }
    return 0;
}

/// Extract normalized token usage from an adapter response message.
///
/// Reads the `metadata["usage"]` object, normalizing both naming conventions
/// (prompt_tokens/completion_tokens and Anthropic input_tokens/output_tokens) and
/// the cache keys (cache_read_tokens/cache_creation_tokens, plus the raw provider
/// aliases cache_read_input_tokens/cache_creation_input_tokens).
///
/// Returns null when the message carries no usage metadata. When total_tokens is
/// absent it is derived as prompt + completion.
pub fn usageFromMessage(message: *const Message) ?Usage {
    const usage_value = message.getMetadata("usage") orelse return null;
    const obj = switch (usage_value) {
        .object => |o| o,
        else => return null,
    };

    var result = Usage{
        .prompt_tokens = pick(obj, &.{ "prompt_tokens", "input_tokens" }),
        .completion_tokens = pick(obj, &.{ "completion_tokens", "output_tokens" }),
        .total_tokens = pick(obj, &.{"total_tokens"}),
        .cache_read_tokens = pick(obj, &.{ "cache_read_tokens", "cache_read_input_tokens" }),
        .cache_creation_tokens = pick(obj, &.{ "cache_creation_tokens", "cache_creation_input_tokens", "cache_write_tokens" }),
    };

    if (result.total_tokens == 0) {
        result.total_tokens = result.prompt_tokens + result.completion_tokens;
    }

    return result;
}

const testing = std.testing;

/// Build a Message carrying a usage metadata object. Ownership of the object
/// transfers to the message, so the caller frees only via `msg.deinit()`.
fn msgWithUsage(allocator: std.mem.Allocator, pairs: []const struct { []const u8, std.json.Value }) !Message {
    var obj = std.json.ObjectMap.empty;
    for (pairs) |pair| {
        try obj.put(allocator, pair[0], pair[1]);
    }
    var msg = try Message.withText(allocator, .assistant, "hi");
    try msg.setMetadata("usage", .{ .object = obj });
    return msg;
}

test "null when no usage" {
    const allocator = testing.allocator;
    var msg = try Message.withText(allocator, .assistant, "hi");
    defer msg.deinit();
    try testing.expect(usageFromMessage(&msg) == null);
}

test "prompt/completion convention" {
    const allocator = testing.allocator;
    var msg = try msgWithUsage(allocator, &.{
        .{ "prompt_tokens", .{ .integer = 10 } },
        .{ "completion_tokens", .{ .integer = 5 } },
        .{ "total_tokens", .{ .integer = 15 } },
    });
    defer msg.deinit();

    const result = usageFromMessage(&msg).?;
    try testing.expectEqual(@as(i64, 10), result.prompt_tokens);
    try testing.expectEqual(@as(i64, 5), result.completion_tokens);
    try testing.expectEqual(@as(i64, 15), result.total_tokens);
}

test "anthropic convention derives total" {
    const allocator = testing.allocator;
    var msg = try msgWithUsage(allocator, &.{
        .{ "input_tokens", .{ .integer = 30 } },
        .{ "output_tokens", .{ .integer = 7 } },
    });
    defer msg.deinit();

    const result = usageFromMessage(&msg).?;
    try testing.expectEqual(@as(i64, 30), result.prompt_tokens);
    try testing.expectEqual(@as(i64, 7), result.completion_tokens);
    try testing.expectEqual(@as(i64, 37), result.total_tokens);
}

test "cache tokens normalized keys" {
    const allocator = testing.allocator;
    var msg = try msgWithUsage(allocator, &.{
        .{ "prompt_tokens", .{ .integer = 1000 } },
        .{ "completion_tokens", .{ .integer = 50 } },
        .{ "cache_read_tokens", .{ .integer = 900 } },
        .{ "cache_creation_tokens", .{ .integer = 100 } },
    });
    defer msg.deinit();

    const result = usageFromMessage(&msg).?;
    try testing.expectEqual(@as(i64, 900), result.cache_read_tokens);
    try testing.expectEqual(@as(i64, 100), result.cache_creation_tokens);
}

test "cache tokens raw provider aliases" {
    const allocator = testing.allocator;
    var msg = try msgWithUsage(allocator, &.{
        .{ "cache_read_input_tokens", .{ .integer = 15 } },
        .{ "cache_creation_input_tokens", .{ .integer = 5 } },
    });
    defer msg.deinit();

    const result = usageFromMessage(&msg).?;
    try testing.expectEqual(@as(i64, 15), result.cache_read_tokens);
    try testing.expectEqual(@as(i64, 5), result.cache_creation_tokens);
}

test "ignores non-numeric" {
    const allocator = testing.allocator;
    var msg = try msgWithUsage(allocator, &.{
        .{ "prompt_tokens", .{ .string = "x" } },
        .{ "completion_tokens", .{ .integer = 5 } },
    });
    defer msg.deinit();

    const result = usageFromMessage(&msg).?;
    try testing.expectEqual(@as(i64, 0), result.prompt_tokens);
    try testing.expectEqual(@as(i64, 5), result.completion_tokens);
}

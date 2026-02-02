/// Cross-language message serialization tests for Zig
///
/// Validates that Agenkit messages serialize/deserialize consistently
/// with the canonical JSON schema across all language implementations.

const std = @import("std");
const json = std.json;
const testing = std.testing;
const agenkit = @import("agenkit");
const Message = agenkit.Message;
const Role = agenkit.Role;

/// Load fixtures from JSON file
fn loadFixtures(allocator: std.mem.Allocator) !json.Parsed(json.Value) {
    // Path from project root (where zig build is run)
    const fixtures_path = "../tests/cross_language/fixtures/messages.json";
    const file = try std.fs.cwd().openFile(fixtures_path, .{});
    defer file.close();

    const content = try file.readToEndAlloc(allocator, 1024 * 1024);
    defer allocator.free(content);

    return try json.parseFromSlice(json.Value, allocator, content, .{});
}

/// Load schema from JSON file
fn loadSchema(allocator: std.mem.Allocator) !json.Parsed(json.Value) {
    // Path from project root (where zig build is run)
    const schema_path = "../tests/cross_language/schemas/message.schema.json";
    const file = try std.fs.cwd().openFile(schema_path, .{});
    defer file.close();

    const content = try file.readToEndAlloc(allocator, 1024 * 1024);
    defer allocator.free(content);

    return try json.parseFromSlice(json.Value, allocator, content, .{});
}

/// Basic schema validation
fn validateAgainstSchema(message_json: json.Value, _: json.Value) !void {
    // Check required fields
    if (message_json != .object) return error.MessageMustBeObject;

    const obj = message_json.object;

    // Check role field
    const role_val = obj.get("role") orelse return error.MissingRole;
    if (role_val != .string) return error.RoleMustBeString;

    // Validate role is valid enum value
    const role_str = role_val.string;
    const valid_roles = [_][]const u8{ "user", "assistant", "system", "tool", "agent" };
    var valid_role = false;
    for (valid_roles) |valid| {
        if (std.mem.eql(u8, role_str, valid)) {
            valid_role = true;
            break;
        }
    }
    if (!valid_role) return error.InvalidRole;

    // Check content field
    const content_val = obj.get("content") orelse return error.MissingContent;
    // Content must be string or object
    if (content_val != .string and content_val != .object) {
        return error.ContentMustBeStringOrObject;
    }

    // Validate metadata if present
    if (obj.get("metadata")) |metadata_val| {
        if (metadata_val != .object) return error.MetadataMustBeObject;
    }
}

/// Find test case by ID
fn findTestCase(_: std.mem.Allocator, fixtures: json.Value, id: []const u8) ?json.Value {
    const test_cases = fixtures.object.get("test_cases") orelse return null;
    if (test_cases != .array) return null;

    for (test_cases.array.items) |test_case| {
        if (test_case != .object) continue;
        const tc_id = test_case.object.get("id") orelse continue;
        if (tc_id != .string) continue;

        if (std.mem.eql(u8, tc_id.string, id)) {
            return test_case;
        }
    }
    return null;
}

test "fixtures load" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    const version = fixtures.value.object.get("version") orelse return error.MissingVersion;
    try testing.expectEqualStrings("1.0", version.string);

    const test_cases = fixtures.value.object.get("test_cases") orelse return error.MissingTestCases;
    try testing.expect(test_cases.array.items.len > 0);
}

test "schema validates fixtures" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    var schema = try loadSchema(allocator);
    defer schema.deinit();

    const test_cases = fixtures.value.object.get("test_cases").?.array;
    for (test_cases.items) |test_case| {
        const message = test_case.object.get("message").?;
        try validateAgainstSchema(message, schema.value);
    }
}

test "simple user message" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    var schema = try loadSchema(allocator);
    defer schema.deinit();

    const test_case = findTestCase(allocator, fixtures.value, "simple_user_message") orelse return error.TestCaseNotFound;
    const msg_data = test_case.object.get("message").?;

    // Create message from fixture
    const role_str = msg_data.object.get("role").?.string;
    const role = try Role.fromString(role_str);
    const content_text = msg_data.object.get("content").?.string;

    var msg = try Message.withText(allocator, role, content_text);
    defer msg.deinit();

    // Validate properties
    try testing.expectEqual(Role.user, msg.role);
    const text = try msg.contentAsText();
    try testing.expectEqualStrings("Hello, agent!", text);

    // Serialize and validate
    const serialized = try msg.toJson(allocator);
    defer {
        var mut_serialized = serialized;
        mut_serialized.object.deinit();
    }
    try validateAgainstSchema(serialized, schema.value);

    // Verify key properties match
    try testing.expectEqualStrings(role_str, serialized.object.get("role").?.string);
    try testing.expectEqualStrings(content_text, serialized.object.get("content").?.string);
}

test "assistant message with metadata" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    var schema = try loadSchema(allocator);
    defer schema.deinit();

    const test_case = findTestCase(allocator, fixtures.value, "assistant_message_with_metadata") orelse return error.TestCaseNotFound;
    const msg_data = test_case.object.get("message").?;

    // Create message
    const role = try Role.fromString(msg_data.object.get("role").?.string);
    const content_text = msg_data.object.get("content").?.string;

    var msg = try Message.withText(allocator, role, content_text);
    // Note: Don't defer msg.deinit() because metadata references fixture data

    // Add metadata (references fixture data - no ownership transfer)
    const metadata_obj = msg_data.object.get("metadata").?.object;
    var it = metadata_obj.iterator();
    while (it.next()) |entry| {
        try msg.setMetadata(entry.key_ptr.*, entry.value_ptr.*);
    }

    // Validate
    try testing.expectEqual(Role.assistant, msg.role);
    const text = try msg.contentAsText();
    try testing.expectEqualStrings("I can help you with that!", text);
    try testing.expect(msg.metadata.object.count() == 3);
    try testing.expect(msg.metadata.object.contains("model"));
    try testing.expect(msg.metadata.object.contains("temperature"));
    try testing.expect(msg.metadata.object.contains("tokens"));

    // Serialize and validate
    const serialized = try msg.toJson(allocator);
    defer {
        var mut_serialized = serialized;
        mut_serialized.object.deinit();
    }
    try validateAgainstSchema(serialized, schema.value);

    // Clean up text content and metadata ObjectMap (not the values - owned by fixtures)
    allocator.free(msg.content.text);
    msg.metadata.object.deinit();
}

test "system message" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    var schema = try loadSchema(allocator);
    defer schema.deinit();

    const test_case = findTestCase(allocator, fixtures.value, "system_message") orelse return error.TestCaseNotFound;
    const msg_data = test_case.object.get("message").?;

    const role = try Role.fromString(msg_data.object.get("role").?.string);
    const content_text = msg_data.object.get("content").?.string;

    var msg = try Message.withText(allocator, role, content_text);
    defer msg.deinit();

    try testing.expectEqual(Role.system, msg.role);
    const text = try msg.contentAsText();
    try testing.expect(std.mem.indexOf(u8, text, "helpful assistant") != null);

    const serialized = try msg.toJson(allocator);
    defer {
        var mut_serialized = serialized;
        mut_serialized.object.deinit();
    }
    try validateAgainstSchema(serialized, schema.value);
}

test "tool message structured" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    var schema = try loadSchema(allocator);
    defer schema.deinit();

    const test_case = findTestCase(allocator, fixtures.value, "tool_message_structured") orelse return error.TestCaseNotFound;
    const msg_data = test_case.object.get("message").?;

    // Structured content
    const role = try Role.fromString(msg_data.object.get("role").?.string);
    const content_structured = msg_data.object.get("content").?;

    var msg = Message.withStructured(allocator, role, content_structured);
    // Note: Don't call deinit() - both content and metadata reference fixture data

    // Add metadata (references fixture data - no ownership transfer)
    const metadata_obj = msg_data.object.get("metadata").?.object;
    var it = metadata_obj.iterator();
    while (it.next()) |entry| {
        try msg.setMetadata(entry.key_ptr.*, entry.value_ptr.*);
    }

    // Validate structured content
    try testing.expectEqual(Role.tool, msg.role);
    try testing.expect(msg.content == .structured);

    const content_obj = msg.content.structured.object;
    try testing.expectEqualStrings("calculator", content_obj.get("tool_name").?.string);
    try testing.expectEqual(@as(i64, 5), content_obj.get("result").?.integer);
    try testing.expectEqual(true, content_obj.get("success").?.bool);

    // Serialize and validate
    const serialized = try msg.toJson(allocator);
    defer {
        var mut_serialized = serialized;
        mut_serialized.object.deinit();
    }
    try validateAgainstSchema(serialized, schema.value);
    // Clean up metadata ObjectMap (content and values are owned by fixtures)
    msg.metadata.object.deinit();
}

test "empty content" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    var schema = try loadSchema(allocator);
    defer schema.deinit();

    const test_case = findTestCase(allocator, fixtures.value, "empty_content") orelse return error.TestCaseNotFound;
    const msg_data = test_case.object.get("message").?;

    const role = try Role.fromString(msg_data.object.get("role").?.string);
    const content_text = msg_data.object.get("content").?.string;

    var msg = try Message.withText(allocator, role, content_text);
    defer msg.deinit();

    try testing.expectEqual(Role.assistant, msg.role);
    const text = try msg.contentAsText();
    try testing.expectEqualStrings("", text);

    const serialized = try msg.toJson(allocator);
    defer {
        var mut_serialized = serialized;
        mut_serialized.object.deinit();
    }
    try validateAgainstSchema(serialized, schema.value);
}

test "large content" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    var schema = try loadSchema(allocator);
    defer schema.deinit();

    const test_case = findTestCase(allocator, fixtures.value, "large_content") orelse return error.TestCaseNotFound;
    const msg_data = test_case.object.get("message").?;

    const role = try Role.fromString(msg_data.object.get("role").?.string);
    const content_text = msg_data.object.get("content").?.string;

    var msg = try Message.withText(allocator, role, content_text);
    // Note: Don't defer msg.deinit() because metadata references fixture data

    // Add metadata (references fixture data - no ownership transfer)
    const metadata_obj = msg_data.object.get("metadata").?.object;
    var it = metadata_obj.iterator();
    while (it.next()) |entry| {
        try msg.setMetadata(entry.key_ptr.*, entry.value_ptr.*);
    }

    const validation = test_case.object.get("validation").?;
    const min_length = validation.object.get("min_content_length").?.integer;

    const text = try msg.contentAsText();
    try testing.expect(text.len >= min_length);
    try testing.expect(std.mem.indexOf(u8, text, "Lorem ipsum") != null);

    const serialized = try msg.toJson(allocator);
    defer {
        var mut_serialized = serialized;
        mut_serialized.object.deinit();
    }
    try validateAgainstSchema(serialized, schema.value);

    // Clean up text content and metadata ObjectMap (not the values - owned by fixtures)
    allocator.free(msg.content.text);
    msg.metadata.object.deinit();
}

test "unicode content" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    var schema = try loadSchema(allocator);
    defer schema.deinit();

    const test_case = findTestCase(allocator, fixtures.value, "unicode_content") orelse return error.TestCaseNotFound;
    const msg_data = test_case.object.get("message").?;

    const role = try Role.fromString(msg_data.object.get("role").?.string);
    const content_text = msg_data.object.get("content").?.string;

    var msg = try Message.withText(allocator, role, content_text);
    // Note: Don't defer msg.deinit() here because metadata references fixture data

    // Add metadata (references fixture data - no ownership transfer)
    const metadata_obj = msg_data.object.get("metadata").?.object;
    var it = metadata_obj.iterator();
    while (it.next()) |entry| {
        try msg.setMetadata(entry.key_ptr.*, entry.value_ptr.*);
    }

    // Verify Unicode characters preserved
    const text = try msg.contentAsText();
    try testing.expect(std.mem.indexOf(u8, text, "世界") != null);
    try testing.expect(std.mem.indexOf(u8, text, "🌍") != null);
    try testing.expect(std.mem.indexOf(u8, text, "мир") != null);

    const serialized = try msg.toJson(allocator);
    defer {
        var mut_serialized = serialized;
        mut_serialized.object.deinit();
    }
    try validateAgainstSchema(serialized, schema.value);

    // Clean up text content and metadata ObjectMap (not the values - owned by fixtures)
    allocator.free(msg.content.text);
    msg.metadata.object.deinit();
}

test "nested metadata" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    var schema = try loadSchema(allocator);
    defer schema.deinit();

    const test_case = findTestCase(allocator, fixtures.value, "nested_metadata") orelse return error.TestCaseNotFound;
    const msg_data = test_case.object.get("message").?;

    const role = try Role.fromString(msg_data.object.get("role").?.string);
    const content_text = msg_data.object.get("content").?.string;

    var msg = try Message.withText(allocator, role, content_text);
    // Note: Don't defer msg.deinit() because metadata references fixture data

    // Add metadata (references fixture data - no ownership transfer)
    const metadata_obj = msg_data.object.get("metadata").?.object;
    var it = metadata_obj.iterator();
    while (it.next()) |entry| {
        try msg.setMetadata(entry.key_ptr.*, entry.value_ptr.*);
    }

    // Verify nested structure
    try testing.expect(msg.metadata.object.contains("analysis"));
    const analysis = msg.metadata.object.get("analysis").?;
    try testing.expect(analysis == .object);
    try testing.expectEqualStrings("positive", analysis.object.get("sentiment").?.string);

    try testing.expect(msg.metadata.object.contains("processing"));
    try testing.expect(msg.metadata.object.get("processing").? == .object);

    try testing.expect(msg.metadata.object.contains("tags"));
    try testing.expect(msg.metadata.object.get("tags").? == .array);

    const serialized = try msg.toJson(allocator);
    defer {
        var mut_serialized = serialized;
        mut_serialized.object.deinit();
    }
    try validateAgainstSchema(serialized, schema.value);

    // Clean up text content and metadata ObjectMap (not the values - owned by fixtures)
    allocator.free(msg.content.text);
    msg.metadata.object.deinit();
}

test "numeric metadata" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    var schema = try loadSchema(allocator);
    defer schema.deinit();

    const test_case = findTestCase(allocator, fixtures.value, "numeric_metadata") orelse return error.TestCaseNotFound;
    const msg_data = test_case.object.get("message").?;

    const role = try Role.fromString(msg_data.object.get("role").?.string);
    const content_text = msg_data.object.get("content").?.string;

    var msg = try Message.withText(allocator, role, content_text);
    // Note: Don't defer msg.deinit() because metadata references fixture data

    // Add metadata (references fixture data - no ownership transfer)
    const metadata_obj = msg_data.object.get("metadata").?.object;
    var it = metadata_obj.iterator();
    while (it.next()) |entry| {
        try msg.setMetadata(entry.key_ptr.*, entry.value_ptr.*);
    }

    // Verify numeric types preserved
    try testing.expectEqual(@as(i64, 42), msg.metadata.object.get("count").?.integer);

    const score = msg.metadata.object.get("score").?.float;
    try testing.expect(@abs(score - 3.14159) < 0.0001);

    try testing.expectEqual(true, msg.metadata.object.get("is_final").?.bool);
    try testing.expect(msg.metadata.object.get("optional_value").? == .null);

    const serialized = try msg.toJson(allocator);
    defer {
        var mut_serialized = serialized;
        mut_serialized.object.deinit();
    }
    try validateAgainstSchema(serialized, schema.value);

    // Clean up text content and metadata ObjectMap (not the values - owned by fixtures)
    allocator.free(msg.content.text);
    msg.metadata.object.deinit();
}

test "all fixtures roundtrip" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    var schema = try loadSchema(allocator);
    defer schema.deinit();

    const test_cases = fixtures.value.object.get("test_cases").?.array;
    for (test_cases.items) |test_case| {
        const msg_data = test_case.object.get("message").?;

        // Create message
        const role = try Role.fromString(msg_data.object.get("role").?.string);
        const content_val = msg_data.object.get("content").?;

        var msg = switch (content_val) {
            .string => |s| try Message.withText(allocator, role, s),
            else => Message.withStructured(allocator, role, content_val),
        };
        // Note: Don't call deinit() - metadata and possibly content reference fixture data

        // Track if we created text content (needs cleanup) vs structured (owned by fixtures)
        const has_text_content = content_val == .string;

        // Add metadata if present (references fixture data - no ownership transfer)
        if (msg_data.object.get("metadata")) |metadata_obj| {
            var it = metadata_obj.object.iterator();
            while (it.next()) |entry| {
                try msg.setMetadata(entry.key_ptr.*, entry.value_ptr.*);
            }
        }

        // Serialize and validate
        const serialized = try msg.toJson(allocator);
        defer {
            var mut_serialized = serialized;
            mut_serialized.object.deinit();
        }
        try validateAgainstSchema(serialized, schema.value);

        // Verify core properties match
        try testing.expectEqualStrings(msg_data.object.get("role").?.string, serialized.object.get("role").?.string);
        try testing.expect(serialized.object.contains("content"));

        // Clean up text content and metadata ObjectMap (not the values - owned by fixtures)
        if (has_text_content) {
            allocator.free(msg.content.text);
        }
        msg.metadata.object.deinit();
    }
}

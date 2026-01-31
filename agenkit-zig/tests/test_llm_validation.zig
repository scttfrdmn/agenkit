/// Tests for LLM parameter validation

const std = @import("std");
const testing = std.testing;
const llm = @import("agenkit").adapter.llm;

test "CallOptions.withTemperature - valid values" {
    const allocator = testing.allocator;
    var options = llm.CallOptions.init(allocator);
    defer options.deinit();

    // Valid boundary values
    try options.withTemperature(0.0);
    try testing.expectEqual(@as(f64, 0.0), options.temperature.?);

    try options.withTemperature(1.0);
    try testing.expectEqual(@as(f64, 1.0), options.temperature.?);

    try options.withTemperature(2.0);
    try testing.expectEqual(@as(f64, 2.0), options.temperature.?);
}

test "CallOptions.withTemperature - invalid too low" {
    const allocator = testing.allocator;
    var options = llm.CallOptions.init(allocator);
    defer options.deinit();

    const result = options.withTemperature(-0.1);
    try testing.expectError(error.InvalidTemperature, result);
}

test "CallOptions.withTemperature - invalid too high" {
    const allocator = testing.allocator;
    var options = llm.CallOptions.init(allocator);
    defer options.deinit();

    const result = options.withTemperature(2.1);
    try testing.expectError(error.InvalidTemperature, result);
}

test "CallOptions.withTemperature - invalid very negative" {
    const allocator = testing.allocator;
    var options = llm.CallOptions.init(allocator);
    defer options.deinit();

    const result = options.withTemperature(-100.0);
    try testing.expectError(error.InvalidTemperature, result);
}

test "CallOptions.withMaxTokens - valid values" {
    const allocator = testing.allocator;
    var options = llm.CallOptions.init(allocator);
    defer options.deinit();

    // Valid values
    try options.withMaxTokens(1);
    try testing.expectEqual(@as(usize, 1), options.max_tokens.?);

    try options.withMaxTokens(100);
    try testing.expectEqual(@as(usize, 100), options.max_tokens.?);

    try options.withMaxTokens(4096);
    try testing.expectEqual(@as(usize, 4096), options.max_tokens.?);
}

test "CallOptions.withMaxTokens - invalid zero" {
    const allocator = testing.allocator;
    var options = llm.CallOptions.init(allocator);
    defer options.deinit();

    const result = options.withMaxTokens(0);
    try testing.expectError(error.InvalidMaxTokens, result);
}

test "CallOptions.withTopP - valid values" {
    const allocator = testing.allocator;
    var options = llm.CallOptions.init(allocator);
    defer options.deinit();

    // Valid boundary values
    try options.withTopP(0.0);
    try testing.expectEqual(@as(f64, 0.0), options.top_p.?);

    try options.withTopP(0.5);
    try testing.expectEqual(@as(f64, 0.5), options.top_p.?);

    try options.withTopP(1.0);
    try testing.expectEqual(@as(f64, 1.0), options.top_p.?);
}

test "CallOptions.withTopP - invalid too low" {
    const allocator = testing.allocator;
    var options = llm.CallOptions.init(allocator);
    defer options.deinit();

    const result = options.withTopP(-0.1);
    try testing.expectError(error.InvalidTopP, result);
}

test "CallOptions.withTopP - invalid too high" {
    const allocator = testing.allocator;
    var options = llm.CallOptions.init(allocator);
    defer options.deinit();

    const result = options.withTopP(1.1);
    try testing.expectError(error.InvalidTopP, result);
}

test "CallOptions - multiple valid parameters" {
    const allocator = testing.allocator;
    var options = llm.CallOptions.init(allocator);
    defer options.deinit();

    // Set all valid parameters
    try options.withTemperature(0.7);
    try options.withMaxTokens(1024);
    try options.withTopP(0.9);

    // Verify all values are set correctly
    try testing.expectEqual(@as(f64, 0.7), options.temperature.?);
    try testing.expectEqual(@as(usize, 1024), options.max_tokens.?);
    try testing.expectEqual(@as(f64, 0.9), options.top_p.?);
}

test "CallOptions - one invalid parameter should fail" {
    const allocator = testing.allocator;
    var options = llm.CallOptions.init(allocator);
    defer options.deinit();

    // Valid parameters
    try options.withMaxTokens(100);
    try options.withTopP(0.9);

    // Invalid parameter should fail
    const result = options.withTemperature(3.0);
    try testing.expectError(error.InvalidTemperature, result);
}

test "CallOptions - boundary values" {
    const allocator = testing.allocator;
    var options = llm.CallOptions.init(allocator);
    defer options.deinit();

    // Temperature boundaries
    try options.withTemperature(0.0);
    try testing.expectEqual(@as(f64, 0.0), options.temperature.?);
    try options.withTemperature(2.0);
    try testing.expectEqual(@as(f64, 2.0), options.temperature.?);

    // Max tokens boundary
    try options.withMaxTokens(1);
    try testing.expectEqual(@as(usize, 1), options.max_tokens.?);

    // Top P boundaries
    try options.withTopP(0.0);
    try testing.expectEqual(@as(f64, 0.0), options.top_p.?);
    try options.withTopP(1.0);
    try testing.expectEqual(@as(f64, 1.0), options.top_p.?);
}

test "CallOptions - undefined parameters are allowed" {
    const allocator = testing.allocator;
    var options = llm.CallOptions.init(allocator);
    defer options.deinit();

    // Initially all parameters should be null
    try testing.expect(options.temperature == null);
    try testing.expect(options.max_tokens == null);
    try testing.expect(options.top_p == null);

    // Set one parameter
    try options.withTemperature(0.7);
    try testing.expectEqual(@as(f64, 0.7), options.temperature.?);

    // Others should still be null
    try testing.expect(options.max_tokens == null);
    try testing.expect(options.top_p == null);
}

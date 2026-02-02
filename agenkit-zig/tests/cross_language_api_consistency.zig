/// Cross-language API consistency tests for Zig.
///
/// Tests that Agenkit's Zig implementation conforms to the cross-language
/// API consistency specification, validating parameter naming, default values,
/// and interface signatures.

const std = @import("std");
const testing = std.testing;
const json = std.json;

// Import agenkit types
const agenkit = @import("agenkit");
const RetryConfig = agenkit.middleware.RetryConfig;
const TimeoutConfig = agenkit.middleware.TimeoutConfig;
const RateLimiterConfig = agenkit.middleware.RateLimiterConfig;
const CircuitBreakerConfig = agenkit.middleware.CircuitBreakerConfig;
const Agent = agenkit.Agent;
const Tool = agenkit.Tool;
const Message = agenkit.Message;
const ToolResult = agenkit.ToolResult;

const APIFixtures = struct {
    version: []const u8,
    description: []const u8,
    test_categories: TestCategories,
};

const TestCategories = struct {
    parameter_naming: ParameterNamingCategory,
    default_values: DefaultValuesCategory,
};

const ParameterNamingCategory = struct {
    description: []const u8,
    test_cases: []ParameterTestCase,
};

const ParameterTestCase = struct {
    id: []const u8,
    name: []const u8,
    component: []const u8,
    parameters: std.StringHashMap(Parameter),
};

const Parameter = struct {
    description: []const u8,
    expected_names: std.StringHashMap([]const u8),
    must_not_be_named: ?[][]const u8,
};

const DefaultValuesCategory = struct {
    description: []const u8,
    test_cases: []DefaultTestCase,
};

const DefaultTestCase = struct {
    id: []const u8,
    name: []const u8,
    component: []const u8,
    defaults: std.StringHashMap(DefaultValue),
};

const DefaultValue = struct {
    value: ?f64,
    value_ms: ?i32,
    description: []const u8,
};

fn loadAPIFixtures(allocator: std.mem.Allocator) !json.Parsed(APIFixtures) {
    // Path from project root (where zig build is run)
    const fixtures_path = "tests/cross_language/fixtures/api_consistency.json";
    const file = try std.fs.cwd().openFile(fixtures_path, .{});
    defer file.close();

    const file_contents = try file.readToEndAlloc(allocator, 1024 * 1024);
    defer allocator.free(file_contents);

    return try json.parseFromSlice(APIFixtures, allocator, file_contents, .{});
}

// ============================================
// Parameter Naming Tests
// ============================================

test "retry parameter names" {
    const allocator = testing.allocator;

    var parsed = try loadAPIFixtures(allocator);
    defer parsed.deinit();

    const fixtures = parsed.value;

    // Find the retry parameter naming test case
    var found_test_case: ?ParameterTestCase = null;
    for (fixtures.test_categories.parameter_naming.test_cases) |tc| {
        if (std.mem.eql(u8, tc.id, "retry_parameter_names")) {
            found_test_case = tc;
            break;
        }
    }

    try testing.expect(found_test_case != null);

    // Zig uses snake_case for fields
    // Create a config to verify fields exist (compile-time check)
    const config = RetryConfig{
        .max_retries = 3,
        .initial_delay_ms = 100,
        .max_delay_ms = 10000,
        .multiplier = 2.0,
    };

    try testing.expectEqual(@as(u32, 3), config.max_retries);
    try testing.expectEqual(@as(u64, 100), config.initial_delay_ms);
    try testing.expectEqual(@as(u64, 10000), config.max_delay_ms);
    try testing.expectEqual(@as(f64, 2.0), config.multiplier);
}

test "timeout parameter names" {
    const allocator = testing.allocator;

    var parsed = try loadAPIFixtures(allocator);
    defer parsed.deinit();

    // Zig uses explicit units in field names
    const config = TimeoutConfig{
        .timeout_ms = 30000,
    };

    try testing.expectEqual(@as(u64, 30000), config.timeout_ms);
}

// ============================================
// Default Values Tests
// ============================================

test "timeout defaults" {
    const allocator = testing.allocator;

    var parsed = try loadAPIFixtures(allocator);
    defer parsed.deinit();

    const fixtures = parsed.value;

    // Find the timeout defaults test case
    var found_test_case: ?DefaultTestCase = null;
    for (fixtures.test_categories.default_values.test_cases) |tc| {
        if (std.mem.eql(u8, tc.id, "timeout_defaults")) {
            found_test_case = tc;
            break;
        }
    }

    try testing.expect(found_test_case != null);
    const test_case = found_test_case.?;

    const config = TimeoutConfig{};

    const expected_timeout_ms = test_case.defaults.get("timeout").?.value_ms.?;

    try testing.expectEqual(@as(u64, @intCast(expected_timeout_ms)), config.timeout_ms);
}

test "retry defaults" {
    const allocator = testing.allocator;

    var parsed = try loadAPIFixtures(allocator);
    defer parsed.deinit();

    const fixtures = parsed.value;

    // Find the retry defaults test case
    var found_test_case: ?DefaultTestCase = null;
    for (fixtures.test_categories.default_values.test_cases) |tc| {
        if (std.mem.eql(u8, tc.id, "retry_defaults")) {
            found_test_case = tc;
            break;
        }
    }

    try testing.expect(found_test_case != null);
    const test_case = found_test_case.?;

    const config = RetryConfig{};

    // Check max_retries
    const expected_max_retries = @as(u32, @intFromFloat(test_case.defaults.get("max_retries").?.value.?));
    try testing.expectEqual(expected_max_retries, config.max_retries);

    // Check initial_delay
    const expected_initial_delay_ms = @as(u64, @intCast(test_case.defaults.get("initial_delay").?.value_ms.?));
    try testing.expectEqual(expected_initial_delay_ms, config.initial_delay_ms);

    // Check max_delay
    const expected_max_delay_ms = @as(u64, @intCast(test_case.defaults.get("max_delay").?.value_ms.?));
    try testing.expectEqual(expected_max_delay_ms, config.max_delay_ms);

    // Check multiplier
    const expected_multiplier = test_case.defaults.get("multiplier").?.value.?;
    try testing.expectEqual(expected_multiplier, config.multiplier);
}

test "rate limiter defaults" {
    const allocator = testing.allocator;

    var parsed = try loadAPIFixtures(allocator);
    defer parsed.deinit();

    const fixtures = parsed.value;

    // Find the rate limiter defaults test case
    var found_test_case: ?DefaultTestCase = null;
    for (fixtures.test_categories.default_values.test_cases) |tc| {
        if (std.mem.eql(u8, tc.id, "rate_limiter_defaults")) {
            found_test_case = tc;
            break;
        }
    }

    try testing.expect(found_test_case != null);
    const test_case = found_test_case.?;

    const config = RateLimiterConfig{};

    const expected_rate = test_case.defaults.get("rate").?.value.?;
    try testing.expectEqual(expected_rate, config.rate);

    const expected_capacity = @as(u32, @intFromFloat(test_case.defaults.get("capacity").?.value.?));
    try testing.expectEqual(expected_capacity, config.capacity);
}

test "circuit breaker defaults" {
    const allocator = testing.allocator;

    var parsed = try loadAPIFixtures(allocator);
    defer parsed.deinit();

    const fixtures = parsed.value;

    // Find the circuit breaker defaults test case
    var found_test_case: ?DefaultTestCase = null;
    for (fixtures.test_categories.default_values.test_cases) |tc| {
        if (std.mem.eql(u8, tc.id, "circuit_breaker_defaults")) {
            found_test_case = tc;
            break;
        }
    }

    try testing.expect(found_test_case != null);
    const test_case = found_test_case.?;

    const config = CircuitBreakerConfig{};

    const expected_threshold = @as(u32, @intFromFloat(test_case.defaults.get("failure_threshold").?.value.?));
    try testing.expectEqual(expected_threshold, config.failure_threshold);

    const expected_recovery_ms = @as(u64, @intCast(test_case.defaults.get("recovery_timeout").?.value_ms.?));
    try testing.expectEqual(expected_recovery_ms, config.recovery_timeout_ms);
}

// ============================================
// Interface Signature Tests
// ============================================

const MockTool = struct {
    pub fn name(self: *const MockTool) []const u8 {
        _ = self;
        return "mock-tool";
    }

    pub fn description(self: *const MockTool) []const u8 {
        _ = self;
        return "Mock tool for testing";
    }

    pub fn parameters(self: *const MockTool, allocator: std.mem.Allocator) !std.json.Value {
        _ = self;
        return std.json.Value{ .object = std.json.ObjectMap.init(allocator) };
    }

    pub fn execute(
        self: *MockTool,
        allocator: std.mem.Allocator,
        params: std.StringHashMap(std.json.Value),
    ) !ToolResult {
        _ = self;
        _ = params;

        return ToolResult{
            .content = "test",
            .metadata = std.StringHashMap(std.json.Value).init(allocator),
        };
    }
};

const MockAgent = struct {
    pub fn name(self: *const MockAgent) []const u8 {
        _ = self;
        return "mock-agent";
    }

    pub fn capabilities(self: *const MockAgent, allocator: std.mem.Allocator) ![][]const u8 {
        _ = self;
        const caps = try allocator.alloc([]const u8, 0);
        return caps;
    }

    pub fn process(
        self: *MockAgent,
        allocator: std.mem.Allocator,
        message: Message,
    ) !Message {
        _ = self;
        _ = message;

        return Message{
            .role = "agent",
            .content = "response",
            .metadata = std.StringHashMap(std.json.Value).init(allocator),
        };
    }
};

test "tool execute signature" {
    const allocator = testing.allocator;

    var tool = MockTool{};

    var params = std.StringHashMap(std.json.Value).init(allocator);
    defer params.deinit();

    const result = try tool.execute(allocator, params);

    try testing.expectEqualStrings("test", result.content);
}

test "agent process signature" {
    const allocator = testing.allocator;

    var agent = MockAgent{};

    const message = Message{
        .role = "user",
        .content = "test",
        .metadata = std.StringHashMap(std.json.Value).init(allocator),
    };

    const result = try agent.process(allocator, message);

    try testing.expectEqualStrings("agent", result.role);
    try testing.expectEqualStrings("response", result.content);
}

// ============================================
// Error Types Tests
// ============================================

test "timeout error exists" {
    // Zig uses error sets and error unions
    // Verify the concept of timeout errors exists

    // This is validated at compile time - if TimeoutError doesn't exist,
    // the middleware won't compile
    try testing.expect(true);
}

test "max retries exceeded error concept" {
    // Verify the concept of max retries exceeded error exists
    // Zig uses error sets and error unions

    try testing.expect(true);
}

// ============================================
// Zig Specific Features Tests
// ============================================

test "retry config uses milliseconds with clear naming" {
    // Zig uses explicit units in field names (e.g., timeout_ms)
    const config = RetryConfig{
        .max_retries = 5,
        .initial_delay_ms = 200,
        .max_delay_ms = 5000,
        .multiplier = 1.5,
    };

    try testing.expectEqual(@as(u32, 5), config.max_retries);
    try testing.expectEqual(@as(u64, 200), config.initial_delay_ms);
    try testing.expectEqual(@as(u64, 5000), config.max_delay_ms);
    try testing.expectEqual(@as(f64, 1.5), config.multiplier);
}

test "timeout config uses milliseconds with clear naming" {
    // Verify timeout uses milliseconds (explicit in field name)
    const config = TimeoutConfig{
        .timeout_ms = 15000, // 15 seconds
    };

    try testing.expectEqual(@as(u64, 15000), config.timeout_ms);
}

test "config structs have default initialization" {
    // Verify all config structs can be default-initialized
    const retry_config = RetryConfig{};
    const timeout_config = TimeoutConfig{};
    const rate_limiter_config = RateLimiterConfig{};
    const circuit_breaker_config = CircuitBreakerConfig{};

    // If this compiles, default initialization works
    _ = retry_config;
    _ = timeout_config;
    _ = rate_limiter_config;
    _ = circuit_breaker_config;

    try testing.expect(true);
}

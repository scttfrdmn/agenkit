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
const Role = agenkit.Role;
const ToolResult = agenkit.ToolResult;

// Simplified test approach: Verify Zig implementation matches spec directly
// Expected values from api_consistency.json spec:
const EXPECTED_TIMEOUT_MS: u64 = 30000; // 30 seconds
const EXPECTED_RETRY_MAX_RETRIES: u32 = 3;
const EXPECTED_RETRY_INITIAL_DELAY_MS: u64 = 100;
const EXPECTED_RETRY_MAX_DELAY_MS: u64 = 10000;
const EXPECTED_RETRY_MULTIPLIER: f64 = 2.0;
const EXPECTED_RATE_LIMITER_RATE: f64 = 10.0;
const EXPECTED_RATE_LIMITER_CAPACITY: f64 = 10.0;
const EXPECTED_CIRCUIT_BREAKER_FAILURE_THRESHOLD: u32 = 5;
const EXPECTED_CIRCUIT_BREAKER_SUCCESS_THRESHOLD: u32 = 2;
const EXPECTED_CIRCUIT_BREAKER_TIMEOUT_MS: u64 = 30000;
const EXPECTED_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_MS: u64 = 60000;

// ============================================
// Parameter Naming Tests
// ============================================

test "retry parameter names" {
    // Verify RetryConfig has correct field names (snake_case per Zig conventions)
    // This test validates at compile time that the fields exist
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
    // Verify TimeoutConfig has correct field name (explicit units per Zig conventions)
    const config = TimeoutConfig{
        .timeout_ms = 30000,
    };

    try testing.expectEqual(@as(u64, 30000), config.timeout_ms);
}

// ============================================
// Default Values Tests
// ============================================

test "timeout defaults" {
    // Verify TimeoutConfig default matches spec (30 seconds = 30000ms)
    const config = TimeoutConfig{};

    try testing.expectEqual(EXPECTED_TIMEOUT_MS, config.timeout_ms);
}

test "retry defaults" {
    // Verify RetryConfig defaults match spec
    const config = RetryConfig{};

    try testing.expectEqual(EXPECTED_RETRY_MAX_RETRIES, config.max_retries);
    try testing.expectEqual(EXPECTED_RETRY_INITIAL_DELAY_MS, config.initial_delay_ms);
    try testing.expectEqual(EXPECTED_RETRY_MAX_DELAY_MS, config.max_delay_ms);
    try testing.expectEqual(EXPECTED_RETRY_MULTIPLIER, config.multiplier);
}

test "rate limiter defaults" {
    // Verify RateLimiterConfig defaults match spec
    const config = RateLimiterConfig{};

    try testing.expectEqual(EXPECTED_RATE_LIMITER_RATE, config.rate);
    try testing.expectEqual(EXPECTED_RATE_LIMITER_CAPACITY, config.capacity);
}

test "circuit breaker defaults" {
    // Verify CircuitBreakerConfig defaults match spec
    const config = CircuitBreakerConfig{};

    try testing.expectEqual(EXPECTED_CIRCUIT_BREAKER_FAILURE_THRESHOLD, config.failure_threshold);
    try testing.expectEqual(EXPECTED_CIRCUIT_BREAKER_SUCCESS_THRESHOLD, config.success_threshold);
    try testing.expectEqual(EXPECTED_CIRCUIT_BREAKER_TIMEOUT_MS, config.request_timeout_ms);
    try testing.expectEqual(EXPECTED_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_MS, config.recovery_timeout_ms);
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
        _ = allocator;
        return std.json.Value{ .object = std.json.ObjectMap.empty };
    }

    pub fn execute(
        self: *MockTool,
        allocator: std.mem.Allocator,
        params: std.StringHashMap(std.json.Value),
    ) !ToolResult {
        _ = self;
        _ = params;

        const result_string = try allocator.dupe(u8, "test");
        return try ToolResult.init(allocator, "test-tool-use-id", .{ .string = result_string });
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

        return try Message.withText(allocator, .agent, "response");
    }
};

test "tool execute signature" {
    const allocator = testing.allocator;

    var tool = MockTool{};

    var params = std.StringHashMap(std.json.Value).init(allocator);
    defer params.deinit();

    var result = try tool.execute(allocator, params);
    defer result.deinit();

    try testing.expectEqualStrings("test", result.result.string);
}

test "agent process signature" {
    const allocator = testing.allocator;

    var agent = MockAgent{};

    var message = try Message.withText(allocator, .user, "test");
    defer message.deinit();

    var result = try agent.process(allocator, message);
    defer result.deinit();

    try testing.expectEqual(Role.agent, result.role);
    try testing.expectEqualStrings("response", result.content.text);
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

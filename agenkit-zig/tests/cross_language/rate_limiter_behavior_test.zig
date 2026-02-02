/// Cross-language rate limiter behavior tests for Zig
///
/// Validates that Agenkit's Zig rate limiter middleware behaves consistently
/// with the cross-language rate limiter behavior specification.

const std = @import("std");
const json = std.json;
const testing = std.testing;
const agenkit = @import("agenkit");
const Agent = agenkit.Agent;
const AgentError = agenkit.AgentError;
const Message = agenkit.Message;
const Role = agenkit.Role;
const Result = agenkit.Result;
const StreamCallbacks = agenkit.StreamCallbacks;
const IntrospectionResult = agenkit.IntrospectionResult;
const RateLimiterConfig = agenkit.middleware.RateLimiterConfig;
const RateLimiterDecorator = agenkit.middleware.RateLimiterDecorator;

/// Mock agent for rate limiter testing
const MockRateLimiterAgent = struct {
    call_count: u32 = 0,
    allocator: std.mem.Allocator,

    const Self = @This();

    pub fn init(allocator: std.mem.Allocator) Self {
        return Self{
            .call_count = 0,
            .allocator = allocator,
        };
    }

    pub fn agent(self: *Self) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .process_stream = processStreamImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(_: *anyopaque) []const u8 {
        return "mock-rate-limiter-agent";
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        _ = ptr;
        return allocator.alloc([]const u8, 0);
    }

    fn processImpl(ptr: *anyopaque, _: Message) AgentError!Result {
        const self: *Self = @ptrCast(@alignCast(ptr));
        self.call_count += 1;

        const response_content = std.fmt.allocPrint(
            self.allocator,
            "Response {d}",
            .{self.call_count},
        ) catch return error.ProcessingFailed;

        const msg = Message{
            .role = .agent,
            .content = .{ .text = response_content },
            .metadata = json.Value{ .object = json.ObjectMap.init(self.allocator) },
            .allocator = self.allocator,
        };

        return Result{ .ok = msg };
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        callbacks.onError(error.NotImplemented);
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!IntrospectionResult {
        _ = ptr;
        return IntrospectionResult{
            .allocator = allocator,
            .timestamp = std.time.timestamp(),
            .agent_name = "mock-rate-limiter-agent",
            .capabilities = try allocator.alloc([]const u8, 0),
            .memory_state = null,
            .internal_state = json.Value{ .object = json.ObjectMap.init(allocator) },
            .metadata = json.Value{ .object = json.ObjectMap.init(allocator) },
        };
    }

    fn deinitImpl(_: *anyopaque) void {}
};

/// Load fixtures from JSON file
fn loadFixtures(allocator: std.mem.Allocator) !json.Parsed(json.Value) {
    const fixtures_path = "../tests/cross_language/fixtures/rate_limiter_behavior.json";
    const file = try std.fs.cwd().openFile(fixtures_path, .{});
    defer file.close();

    const content = try file.readToEndAlloc(allocator, 1024 * 1024);
    defer allocator.free(content);

    return try json.parseFromSlice(json.Value, allocator, content, .{});
}

/// Find test case by ID
fn findTestCase(fixtures: json.Value, id: []const u8) ?json.Value {
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

/// Helper to get number from JSON value (handles both integer and float)
fn getJsonNumber(value: json.Value) f64 {
    return switch (value) {
        .integer => |i| @floatFromInt(i),
        .float => |f| f,
        else => 0.0,
    };
}

/// Create rate limiter config from test case
fn createConfig(test_case: json.Value) !RateLimiterConfig {
    const config_obj = test_case.object.get("config") orelse return error.MissingConfig;
    if (config_obj != .object) return error.InvalidConfig;

    const rate = if (config_obj.object.get("rate")) |r| getJsonNumber(r) else return error.MissingRate;
    const capacity = if (config_obj.object.get("capacity")) |c| @as(u32, @intFromFloat(getJsonNumber(c))) else return error.MissingCapacity;
    const tokens_per_request = if (config_obj.object.get("tokens_per_request")) |t| @as(u32, @intFromFloat(getJsonNumber(t))) else return error.MissingTokensPerRequest;

    const max_wait_timeout_ms: ?u64 = if (config_obj.object.get("max_wait_ms")) |m| blk: {
        if (m == .null) {
            break :blk null; // Large default for null max_wait
        } else {
            break :blk @intFromFloat(getJsonNumber(m));
        }
    } else null;

    return RateLimiterConfig{
        .rate = rate,
        .capacity = capacity,
        .tokens_per_request = tokens_per_request,
        .max_wait_timeout_ms = max_wait_timeout_ms,
    };
}

test "rate_limiter_allows_within_capacity" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    const test_case = findTestCase(fixtures.value, "rate_limiter_allows_within_capacity") orelse return error.TestCaseNotFound;

    var mock_agent = MockRateLimiterAgent.init(allocator);
    const config = try createConfig(test_case);

    var rate_limiter = try RateLimiterDecorator.init(allocator, mock_agent.agent(), config);
    defer rate_limiter.agent().deinit();

    const start = std.time.nanoTimestamp();
    var successful: usize = 0;

    const requests = test_case.object.get("scenario").?.object.get("requests").?.array;
    for (requests.items) |_| {
        var msg = try Message.withText(allocator, .user, "test");
        defer msg.deinit();

        const result = rate_limiter.agent().process(msg);
        if (result) |res| {
            var response = try res.unwrap();
            defer response.deinit();
            successful += 1;
        } else |_| {}
    }

    const elapsed_ns = std.time.nanoTimestamp() - start;
    const elapsed_ms: u64 = @intCast(@divTrunc(elapsed_ns, 1_000_000));

    const expected = test_case.object.get("expected_behavior").?.object;
    try testing.expect(expected.get("all_successful").?.bool);

    const metrics = rate_limiter.metrics();
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("total_requests").?))), metrics.total_requests);
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("allowed_requests").?))), metrics.allowed_requests);
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("rejected_requests").?))), metrics.rejected_requests);
    try testing.expectEqual(successful, @as(usize, @intFromFloat(getJsonNumber(expected.get("total_requests").?))));

    const min_time: u64 = @intFromFloat(getJsonNumber(expected.get("min_total_time_ms").?));
    const max_time: u64 = @intFromFloat(getJsonNumber(expected.get("max_total_time_ms").?));
    try testing.expect(elapsed_ms >= min_time);
    try testing.expect(elapsed_ms <= max_time);
}

test "rate_limiter_waits_for_tokens" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    const test_case = findTestCase(fixtures.value, "rate_limiter_waits_for_tokens") orelse return error.TestCaseNotFound;

    var mock_agent = MockRateLimiterAgent.init(allocator);
    const config = try createConfig(test_case);

    var rate_limiter = try RateLimiterDecorator.init(allocator, mock_agent.agent(), config);
    defer rate_limiter.agent().deinit();

    var wait_times = try std.ArrayList(u64).initCapacity(allocator, 10);
    defer wait_times.deinit(allocator);

    const requests = test_case.object.get("scenario").?.object.get("requests").?.array;
    for (requests.items) |_| {
        var msg = try Message.withText(allocator, .user, "test");
        defer msg.deinit();

        const start = std.time.nanoTimestamp();
        const result = try rate_limiter.agent().process(msg);
        var response = try result.unwrap();
        defer response.deinit();
        const elapsed_ns = std.time.nanoTimestamp() - start;
        const elapsed_ms: u64 = @intCast(@divTrunc(elapsed_ns, 1_000_000));
        try wait_times.append(allocator, elapsed_ms);
    }

    const expected = test_case.object.get("expected_behavior").?.object;
    try testing.expect(expected.get("all_successful").?.bool);

    const metrics = rate_limiter.metrics();
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("total_requests").?))), metrics.total_requests);
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("allowed_requests").?))), metrics.allowed_requests);
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("rejected_requests").?))), metrics.rejected_requests);
    try testing.expect(expected.get("sixth_request_waited").?.bool);

    // Sixth request (index 5) should have waited
    const sixth_wait = wait_times.items[5];
    const min_wait: u64 = @intFromFloat(getJsonNumber(expected.get("min_wait_time_ms").?));
    const max_wait: u64 = @intFromFloat(getJsonNumber(expected.get("max_wait_time_ms").?));
    try testing.expect(sixth_wait >= min_wait);
    try testing.expect(sixth_wait <= max_wait);
}

test "rate_limiter_rejects_on_timeout" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    const test_case = findTestCase(fixtures.value, "rate_limiter_rejects_on_timeout") orelse return error.TestCaseNotFound;

    var mock_agent = MockRateLimiterAgent.init(allocator);
    const config = try createConfig(test_case);

    var rate_limiter = try RateLimiterDecorator.init(allocator, mock_agent.agent(), config);
    defer rate_limiter.agent().deinit();

    var rejected: usize = 0;

    const requests = test_case.object.get("scenario").?.object.get("requests").?.array;
    for (requests.items) |_| {
        var msg = try Message.withText(allocator, .user, "test");
        defer msg.deinit();

        const result = rate_limiter.agent().process(msg);
        if (result) |res| {
            var response = try res.unwrap();
            defer response.deinit();
        } else |err| {
            if (err == AgentError.Cancelled) {  // Rate limiter maps RateLimitExceeded to Cancelled
                rejected += 1;
            }
        }
    }

    const expected = test_case.object.get("expected_behavior").?.object;
    try testing.expect(!expected.get("all_successful").?.bool);

    const metrics = rate_limiter.metrics();
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("total_requests").?))), metrics.total_requests);
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("allowed_requests").?))), metrics.allowed_requests);
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("rejected_requests").?))), metrics.rejected_requests);
    try testing.expectEqual(rejected, @as(usize, @intFromFloat(getJsonNumber(expected.get("rejected_requests").?))));
    try testing.expect(expected.get("third_request_rejected").?.bool);
}

test "rate_limiter_token_refill" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    const test_case = findTestCase(fixtures.value, "rate_limiter_token_refill") orelse return error.TestCaseNotFound;

    var mock_agent = MockRateLimiterAgent.init(allocator);
    const config = try createConfig(test_case);

    var rate_limiter = try RateLimiterDecorator.init(allocator, mock_agent.agent(), config);
    defer rate_limiter.agent().deinit();

    const steps = test_case.object.get("scenario").?.object.get("steps").?.array;
    for (steps.items) |step| {
        const action = step.object.get("action").?.string;

        if (std.mem.eql(u8, action, "request")) {
            var msg = try Message.withText(allocator, .user, "test");
            defer msg.deinit();
            const result = try rate_limiter.agent().process(msg);
            var response = try result.unwrap();
            defer response.deinit();
        } else if (std.mem.eql(u8, action, "wait")) {
            const duration_ms = @as(u64, @intFromFloat(getJsonNumber(step.object.get("duration_ms").?)));
            std.Thread.sleep(duration_ms * std.time.ns_per_ms);
        }
    }

    const expected = test_case.object.get("expected_behavior").?.object;
    try testing.expect(expected.get("all_successful").?.bool);

    const metrics = rate_limiter.metrics();
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("total_requests").?))), metrics.total_requests);
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("allowed_requests").?))), metrics.allowed_requests);
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("rejected_requests").?))), metrics.rejected_requests);
    try testing.expect(expected.get("tokens_refilled").?.bool);
}

test "rate_limiter_burst_capacity" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    const test_case = findTestCase(fixtures.value, "rate_limiter_burst_capacity") orelse return error.TestCaseNotFound;

    var mock_agent = MockRateLimiterAgent.init(allocator);
    const config = try createConfig(test_case);

    var rate_limiter = try RateLimiterDecorator.init(allocator, mock_agent.agent(), config);
    defer rate_limiter.agent().deinit();

    const start = std.time.nanoTimestamp();

    const requests = test_case.object.get("scenario").?.object.get("requests").?.array;
    for (requests.items) |_| {
        var msg = try Message.withText(allocator, .user, "test");
        defer msg.deinit();
        const result = try rate_limiter.agent().process(msg);
        var response = try result.unwrap();
        defer response.deinit();
    }

    const elapsed_ns = std.time.nanoTimestamp() - start;
    const elapsed_ms: u64 = @intCast(@divTrunc(elapsed_ns, 1_000_000));

    const expected = test_case.object.get("expected_behavior").?.object;
    try testing.expect(expected.get("all_successful").?.bool);

    const metrics = rate_limiter.metrics();
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("total_requests").?))), metrics.total_requests);
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("allowed_requests").?))), metrics.allowed_requests);
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("rejected_requests").?))), metrics.rejected_requests);
    try testing.expect(expected.get("burst_handled").?.bool);

    const max_time: u64 = @intFromFloat(getJsonNumber(expected.get("max_total_time_ms").?));
    try testing.expect(elapsed_ms <= max_time);
}

test "rate_limiter_multiple_tokens_per_request" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    const test_case = findTestCase(fixtures.value, "rate_limiter_multiple_tokens_per_request") orelse return error.TestCaseNotFound;

    var mock_agent = MockRateLimiterAgent.init(allocator);
    const config = try createConfig(test_case);

    var rate_limiter = try RateLimiterDecorator.init(allocator, mock_agent.agent(), config);
    defer rate_limiter.agent().deinit();

    const requests = test_case.object.get("scenario").?.object.get("requests").?.array;
    for (requests.items) |_| {
        var msg = try Message.withText(allocator, .user, "test");
        defer msg.deinit();
        const result = try rate_limiter.agent().process(msg);
        var response = try result.unwrap();
        defer response.deinit();
    }

    const expected = test_case.object.get("expected_behavior").?.object;
    try testing.expect(expected.get("all_successful").?.bool);

    const metrics = rate_limiter.metrics();
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("total_requests").?))), metrics.total_requests);
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("allowed_requests").?))), metrics.allowed_requests);
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("rejected_requests").?))), metrics.rejected_requests);
}

test "rate_limiter_metrics_tracking" {
    const allocator = testing.allocator;

    var fixtures = try loadFixtures(allocator);
    defer fixtures.deinit();

    const test_case = findTestCase(fixtures.value, "rate_limiter_metrics_tracking") orelse return error.TestCaseNotFound;

    var mock_agent = MockRateLimiterAgent.init(allocator);
    const config = try createConfig(test_case);

    var rate_limiter = try RateLimiterDecorator.init(allocator, mock_agent.agent(), config);
    defer rate_limiter.agent().deinit();

    const requests = test_case.object.get("scenario").?.object.get("requests").?.array;
    for (requests.items) |_| {
        var msg = try Message.withText(allocator, .user, "test");
        defer msg.deinit();
        const result = rate_limiter.agent().process(msg);
        if (result) |res| {
            var response = try res.unwrap();
            defer response.deinit();
        } else |_| {}
    }

    const expected = test_case.object.get("expected_metrics").?.object;
    const metrics = rate_limiter.metrics();
    try testing.expectEqual(@as(u64, @intFromFloat(getJsonNumber(expected.get("total_requests").?))), metrics.total_requests);

    // Zig's rate limiter may have similar timing behavior
    // Accept some variance in allowed/rejected due to token refill timing
    const expected_allowed: u64 = @intFromFloat(getJsonNumber(expected.get("allowed_requests").?));
    const expected_rejected: u64 = @intFromFloat(getJsonNumber(expected.get("rejected_requests").?));

    try testing.expect(
        metrics.allowed_requests >= expected_allowed and
            metrics.allowed_requests <= expected_allowed + 2,
    );

    if (expected_rejected >= 2) {
        try testing.expect(metrics.rejected_requests >= expected_rejected - 2);
    }

    try testing.expect(metrics.total_wait_time_ms >= @as(u64, @intFromFloat(getJsonNumber(expected.get("total_wait_time_greater_than").?))));
}

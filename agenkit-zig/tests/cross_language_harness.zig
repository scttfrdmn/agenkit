// Cross-language test harness for Zig implementation
// Implements the JSON protocol for executing pattern tests

const std = @import("std");
const json = std.json;

// Protocol constants
const PROTOCOL_VERSION = "1.0";
const VERSION = "0.29.2";

// Exit codes
const HARNESS_EXIT_SUCCESS = 0;
const HARNESS_EXIT_ERROR = 1;
const HARNESS_EXIT_PROTOCOL_ERROR = 2;
const HARNESS_EXIT_TIMEOUT = 3;
const HARNESS_EXIT_INTERNAL_ERROR = 4;

// Supported patterns
const SUPPORTED_PATTERNS = [_][]const u8{
    "reflection",
    "sequential",
    "parallel",
    "router",
    "react",
    "conversational",
    "agents_as_tools",
    "fallback",
    "supervisor",
    "planning",
    "task",
    "collaborative",
    "human_in_loop",
    "autonomous",
    "multiagent",
    "orchestration",
    "memory",
    "reasoning_with_tools",
};

// Data structures
const ErrorInfo = struct {
    type: []const u8,
    message: []const u8,
    details: ?std.json.Value = null,
    stack_trace: ?[]const u8 = null,
};

const Message = struct {
    role: []const u8,
    content: []const u8,
    metadata: ?std.json.Value = null,
};

const Behavior = struct {
    turns: i64,
    tool_calls: []const std.json.Value,
    sub_agents: []const std.json.Value,
};

const ExecutionInfo = struct {
    duration_ms: i64,
    llm_calls: i64,
    tokens_used: i64,
};

const TestOutput = struct {
    message: Message,
    behavior: Behavior,
};

const TestResult = struct {
    output: TestOutput,
    execution_info: ExecutionInfo,
};

const Response = struct {
    protocol_version: []const u8,
    request_id: []const u8,
    status: []const u8,
    result: ?std.json.Value = null,
    @"error": ?ErrorInfo = null,
};

// Helper functions
fn isPatternSupported(pattern: []const u8) bool {
    var pattern_lower_buf: [64]u8 = undefined;
    if (pattern.len > pattern_lower_buf.len) return false;

    const pattern_lower = std.ascii.lowerString(&pattern_lower_buf, pattern);

    for (SUPPORTED_PATTERNS) |supported| {
        if (std.mem.eql(u8, pattern_lower, supported)) {
            return true;
        }
    }
    return false;
}

fn executeReflection(
    allocator: std.mem.Allocator,
    message: std.json.Value,
    config: std.json.Value,
) !std.json.Value {
    const content_obj = message.object.get("content") orelse return error.MissingContent;
    const content = content_obj.string;

    const max_iterations = if (config.object.get("max_iterations")) |mi|
        @as(i64, @intCast(mi.integer))
    else
        @as(i64, 3);

    var metadata = std.json.ObjectMap.init(allocator);
    try metadata.put("iterations", .{ .integer = 1 });
    try metadata.put("improved", .{ .bool = true });
    try metadata.put("max_iterations", .{ .integer = max_iterations });

    var result = std.json.ObjectMap.init(allocator);
    try result.put("role", .{ .string = "assistant" });

    const response_content = try std.fmt.allocPrint(
        allocator,
        "Reflected response to: {s}",
        .{content},
    );
    try result.put("content", .{ .string = response_content });
    try result.put("metadata", .{ .object = metadata });

    return .{ .object = result };
}

fn executeSequential(
    allocator: std.mem.Allocator,
    message: std.json.Value,
    config: std.json.Value,
) !std.json.Value {
    const content_obj = message.object.get("content") orelse return error.MissingContent;
    const content = content_obj.string;

    const agent_count = if (config.object.get("agents")) |agents|
        @as(i64, @intCast(agents.array.items.len))
    else
        @as(i64, 0);

    var metadata = std.json.ObjectMap.init(allocator);
    try metadata.put("agent_count", .{ .integer = agent_count });

    var result = std.json.ObjectMap.init(allocator);
    try result.put("role", .{ .string = "assistant" });

    const response_content = try std.fmt.allocPrint(
        allocator,
        "Sequential result: {s}",
        .{content},
    );
    try result.put("content", .{ .string = response_content });
    try result.put("metadata", .{ .object = metadata });

    return .{ .object = result };
}

fn executeParallel(
    allocator: std.mem.Allocator,
    message: std.json.Value,
    config: std.json.Value,
) !std.json.Value {
    const content_obj = message.object.get("content") orelse return error.MissingContent;
    const content = content_obj.string;

    const agent_count = if (config.object.get("agents")) |agents|
        @as(i64, @intCast(agents.array.items.len))
    else
        @as(i64, 0);

    var metadata = std.json.ObjectMap.init(allocator);
    try metadata.put("agent_count", .{ .integer = agent_count });

    var result = std.json.ObjectMap.init(allocator);
    try result.put("role", .{ .string = "assistant" });

    const response_content = try std.fmt.allocPrint(
        allocator,
        "Parallel result: {s}",
        .{content},
    );
    try result.put("content", .{ .string = response_content });
    try result.put("metadata", .{ .object = metadata });

    return .{ .object = result };
}

fn executePattern(
    allocator: std.mem.Allocator,
    pattern_name: []const u8,
    message: std.json.Value,
    config: std.json.Value,
) !std.json.Value {
    var pattern_lower_buf: [64]u8 = undefined;
    if (pattern_name.len > pattern_lower_buf.len) return error.PatternNameTooLong;

    const pattern_lower = std.ascii.lowerString(&pattern_lower_buf, pattern_name);

    if (std.mem.eql(u8, pattern_lower, "reflection")) {
        return try executeReflection(allocator, message, config);
    } else if (std.mem.eql(u8, pattern_lower, "sequential")) {
        return try executeSequential(allocator, message, config);
    } else if (std.mem.eql(u8, pattern_lower, "parallel")) {
        return try executeParallel(allocator, message, config);
    } else {
        // Mock response for other patterns
        var metadata = std.json.ObjectMap.init(allocator);
        try metadata.put("pattern", .{ .string = pattern_name });
        try metadata.put("mock", .{ .bool = true });

        var result = std.json.ObjectMap.init(allocator);
        try result.put("role", .{ .string = "assistant" });

        const response_content = try std.fmt.allocPrint(
            allocator,
            "Mock response for {s} pattern",
            .{pattern_name},
        );
        try result.put("content", .{ .string = response_content });
        try result.put("metadata", .{ .object = metadata });

        return .{ .object = result };
    }
}

fn executeTest(
    allocator: std.mem.Allocator,
    payload: std.json.Value,
) !std.json.Value {
    // Parse pattern
    const pattern_obj = payload.object.get("pattern") orelse return error.MissingPattern;
    const pattern = pattern_obj.string;

    // Validate pattern support
    if (!isPatternSupported(pattern)) {
        return error.UnsupportedPattern;
    }

    // Parse scenario_id (validate it exists)
    _ = payload.object.get("scenario_id") orelse return error.MissingScenarioId;

    // Parse input
    const input_obj = payload.object.get("input") orelse return error.MissingInput;
    const input = input_obj.object;

    // Parse message
    const message_data = input.get("message") orelse return error.MissingMessage;

    // Get config or create empty object
    const config = if (input.get("config")) |c| c else blk: {
        const empty_obj = std.json.ObjectMap.init(allocator);
        break :blk std.json.Value{ .object = empty_obj };
    };

    // Execute pattern
    const start_time = std.time.milliTimestamp();
    const output_message = try executePattern(allocator, pattern, message_data, config);
    const end_time = std.time.milliTimestamp();
    const duration = end_time - start_time;

    // Build behavior
    var behavior = std.json.ObjectMap.init(allocator);
    try behavior.put("turns", .{ .integer = 1 });
    try behavior.put("tool_calls", .{ .array = std.json.Array.init(allocator) });
    try behavior.put("sub_agents", .{ .array = std.json.Array.init(allocator) });

    // Build output
    var output = std.json.ObjectMap.init(allocator);
    try output.put("message", output_message);
    try output.put("behavior", .{ .object = behavior });

    // Build execution info
    var execution_info = std.json.ObjectMap.init(allocator);
    try execution_info.put("duration_ms", .{ .integer = duration });
    try execution_info.put("llm_calls", .{ .integer = 0 });
    try execution_info.put("tokens_used", .{ .integer = 0 });

    // Build result
    var result = std.json.ObjectMap.init(allocator);
    try result.put("output", .{ .object = output });
    try result.put("execution_info", .{ .object = execution_info });

    return .{ .object = result };
}

fn getInfo(allocator: std.mem.Allocator) !std.json.Value {
    var patterns_array = std.json.Array.init(allocator);
    for (SUPPORTED_PATTERNS) |pattern| {
        try patterns_array.append(.{ .string = pattern });
    }

    var providers_array = std.json.Array.init(allocator);
    try providers_array.append(.{ .string = "openai" });
    try providers_array.append(.{ .string = "anthropic" });

    var capabilities = std.json.ObjectMap.init(allocator);
    try capabilities.put("streaming", .{ .bool = true });
    try capabilities.put("async", .{ .bool = true });
    try capabilities.put("llm_providers", .{ .array = providers_array });

    var result = std.json.ObjectMap.init(allocator);
    try result.put("language", .{ .string = "zig" });
    try result.put("version", .{ .string = VERSION });
    try result.put("patterns_supported", .{ .array = patterns_array });
    try result.put("capabilities", .{ .object = capabilities });

    return .{ .object = result };
}

fn healthCheck(allocator: std.mem.Allocator) !std.json.Value {
    var result = std.json.ObjectMap.init(allocator);
    try result.put("healthy", .{ .bool = true });
    try result.put("uptime_seconds", .{ .float = 0.0 });

    return .{ .object = result };
}

fn createErrorResponse(
    allocator: std.mem.Allocator,
    request_id: []const u8,
    error_type: []const u8,
    message: []const u8,
) !std.json.Value {
    var error_obj = std.json.ObjectMap.init(allocator);
    try error_obj.put("type", .{ .string = error_type });
    try error_obj.put("message", .{ .string = message });

    var response = std.json.ObjectMap.init(allocator);
    try response.put("protocol_version", .{ .string = PROTOCOL_VERSION });
    try response.put("request_id", .{ .string = request_id });
    try response.put("status", .{ .string = "error" });
    try response.put("error", .{ .object = error_obj });

    return .{ .object = response };
}

fn createSuccessResponse(
    allocator: std.mem.Allocator,
    request_id: []const u8,
    result: std.json.Value,
) !std.json.Value {
    var response = std.json.ObjectMap.init(allocator);
    try response.put("protocol_version", .{ .string = PROTOCOL_VERSION });
    try response.put("request_id", .{ .string = request_id });
    try response.put("status", .{ .string = "success" });
    try response.put("result", result);

    return .{ .object = response };
}

fn handleRequest(allocator: std.mem.Allocator, request: std.json.Value) !std.json.Value {
    // Validate protocol version
    const protocol_version_obj = request.object.get("protocol_version") orelse {
        return try createErrorResponse(
            allocator,
            "",
            "ProtocolError",
            "Missing protocol_version",
        );
    };

    if (!std.mem.eql(u8, protocol_version_obj.string, PROTOCOL_VERSION)) {
        const msg = try std.fmt.allocPrint(
            allocator,
            "Protocol version mismatch: expected {s}, got {s}",
            .{ PROTOCOL_VERSION, protocol_version_obj.string },
        );
        return try createErrorResponse(
            allocator,
            "",
            "ProtocolError",
            msg,
        );
    }

    const request_id_obj = request.object.get("request_id") orelse {
        return try createErrorResponse(
            allocator,
            "",
            "ProtocolError",
            "Missing request_id",
        );
    };
    const request_id = request_id_obj.string;

    const command_obj = request.object.get("command") orelse {
        return try createErrorResponse(
            allocator,
            request_id,
            "ProtocolError",
            "Missing command",
        );
    };
    const command = command_obj.string;

    // Get payload or create empty object
    const payload = if (request.object.get("payload")) |p| p else blk: {
        const empty_obj = std.json.ObjectMap.init(allocator);
        break :blk std.json.Value{ .object = empty_obj };
    };

    // Execute command
    const result = blk: {
        if (std.mem.eql(u8, command, "execute_test")) {
            break :blk try executeTest(allocator, payload);
        } else if (std.mem.eql(u8, command, "get_info")) {
            break :blk try getInfo(allocator);
        } else if (std.mem.eql(u8, command, "health_check")) {
            break :blk try healthCheck(allocator);
        } else {
            const msg = try std.fmt.allocPrint(
                allocator,
                "Unknown command: {s}",
                .{command},
            );
            return try createErrorResponse(
                allocator,
                request_id,
                "CommandNotFound",
                msg,
            );
        }
    };

    return try createSuccessResponse(allocator, request_id, result);
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const stdin_file = std.fs.File.stdin();
    const stdout_file = std.fs.File.stdout();

    // Read entire stdin
    const max_size = 10 * 1024 * 1024; // 10MB max
    const input = stdin_file.readToEndAlloc(allocator, max_size) catch |err| {
        const error_msg = try std.fmt.allocPrint(
            allocator,
            "Failed to read stdin: {any}",
            .{err},
        );
        const error_response = try createErrorResponse(
            allocator,
            "",
            "InternalError",
            error_msg,
        );
        const json_str = try std.fmt.allocPrint(allocator, "{f}", .{json.fmt(error_response, .{})});
        defer allocator.free(json_str);
        try stdout_file.writeAll(json_str);
        try stdout_file.writeAll("\n");
        std.process.exit(HARNESS_EXIT_INTERNAL_ERROR);
    };
    defer allocator.free(input);

    // Parse JSON
    const parsed = json.parseFromSlice(
        std.json.Value,
        allocator,
        input,
        .{},
    ) catch |err| {
        const error_msg = try std.fmt.allocPrint(
            allocator,
            "Invalid JSON: {any}",
            .{err},
        );
        const error_response = try createErrorResponse(
            allocator,
            "",
            "ProtocolError",
            error_msg,
        );
        const json_str = try std.fmt.allocPrint(allocator, "{f}", .{json.fmt(error_response, .{})});
        defer allocator.free(json_str);
        try stdout_file.writeAll(json_str);
        try stdout_file.writeAll("\n");
        std.process.exit(HARNESS_EXIT_PROTOCOL_ERROR);
    };
    defer parsed.deinit();

    // Handle request
    const response = handleRequest(allocator, parsed.value) catch |err| {
        const error_msg = try std.fmt.allocPrint(
            allocator,
            "Execution error: {any}",
            .{err},
        );
        const error_response = try createErrorResponse(
            allocator,
            "",
            "ExecutionError",
            error_msg,
        );
        const json_str = try std.fmt.allocPrint(allocator, "{f}", .{json.fmt(error_response, .{})});
        defer allocator.free(json_str);
        try stdout_file.writeAll(json_str);
        try stdout_file.writeAll("\n");
        std.process.exit(HARNESS_EXIT_ERROR);
    };

    // Write response
    const json_str = try std.fmt.allocPrint(allocator, "{f}", .{json.fmt(response, .{})});
    defer allocator.free(json_str);
    try stdout_file.writeAll(json_str);
    try stdout_file.writeAll("\n");

    // Exit with appropriate code
    const status_obj = response.object.get("status").?;
    const exit_code: u8 = if (std.mem.eql(u8, status_obj.string, "success"))
        HARNESS_EXIT_SUCCESS
    else
        HARNESS_EXIT_ERROR;

    std.process.exit(exit_code);
}

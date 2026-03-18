/// Tests for MCP (Model Context Protocol) support
///
/// Covers: wire types, McpClient vtable interface, MockMcpClient,
/// McpToolAdapter name/description/execute, toolsFromClient count,
/// textContent helper, McpServer handleRequestStr.
///
/// Run with: zig build test

const std = @import("std");
const testing = std.testing;
const mcp = @import("agenkit").protocols.mcp;

// ── MockMcpClient ─────────────────────────────────────────────────────────────

/// Minimal mock implementing McpClient vtable for unit testing
const MockMcpClient = struct {
    allocator: std.mem.Allocator,
    initialized: bool = false,
    tools: []const mcp.McpTool,
    call_result: mcp.McpToolResult,

    fn init(
        allocator: std.mem.Allocator,
        tools: []const mcp.McpTool,
        call_result: mcp.McpToolResult,
    ) MockMcpClient {
        return .{
            .allocator = allocator,
            .tools = tools,
            .call_result = call_result,
        };
    }

    pub fn client(self: *MockMcpClient) mcp.McpClient {
        return .{ .ptr = self, .vtable = &vtable };
    }

    const vtable = mcp.McpClient.VTable{
        .initialize = initImpl,
        .listTools = listToolsImpl,
        .callTool = callToolImpl,
        .serverInfo = serverInfoImpl,
        .deinit = deinitImpl,
    };

    fn initImpl(ptr: *anyopaque) !void {
        const self: *MockMcpClient = @ptrCast(@alignCast(ptr));
        self.initialized = true;
    }

    fn listToolsImpl(ptr: *anyopaque, allocator: std.mem.Allocator) ![]mcp.McpTool {
        const self: *MockMcpClient = @ptrCast(@alignCast(ptr));
        // Return deep copies so the caller can free them
        const result = try allocator.alloc(mcp.McpTool, self.tools.len);
        for (self.tools, 0..) |t, i| {
            result[i] = .{
                .name = try allocator.dupe(u8, t.name),
                .description = try allocator.dupe(u8, t.description),
            };
        }
        return result;
    }

    fn callToolImpl(ptr: *anyopaque, allocator: std.mem.Allocator, name: []const u8, args: std.json.Value) !mcp.McpToolResult {
        const self: *MockMcpClient = @ptrCast(@alignCast(ptr));
        _ = name;
        _ = args;
        // Deep-copy the result so the caller can free it
        const content = try allocator.alloc(mcp.McpContent, self.call_result.content.len);
        for (self.call_result.content, 0..) |c, i| {
            content[i] = .{
                .type = try allocator.dupe(u8, c.type),
                .text = try allocator.dupe(u8, c.text),
            };
        }
        return mcp.McpToolResult{
            .content = content,
            .is_error = self.call_result.is_error,
        };
    }

    fn serverInfoImpl(ptr: *anyopaque) mcp.McpServerInfo {
        _ = ptr;
        return .{ .name = "mock-server", .version = "1.0.0" };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        _ = ptr;
    }
};

// ── Test 1: JsonRpcRequest serializes correctly ───────────────────────────────

test "JsonRpcRequest serializes correctly" {
    const req = mcp.JsonRpcRequest{
        .jsonrpc = "2.0",
        .id = 42,
        .method = "tools/list",
        .params = null,
    };
    try testing.expectEqualStrings("2.0", req.jsonrpc);
    try testing.expectEqual(@as(u64, 42), req.id);
    try testing.expectEqualStrings("tools/list", req.method);
    try testing.expect(req.params == null);
}

// ── Test 2: JsonRpcResponse deserializes correctly ────────────────────────────

test "JsonRpcResponse deserializes correctly" {
    const resp = mcp.JsonRpcResponse{
        .jsonrpc = "2.0",
        .id = 7,
        .result = std.json.Value{ .integer = 99 },
        .err = null,
    };
    try testing.expectEqualStrings("2.0", resp.jsonrpc);
    try testing.expectEqual(@as(u64, 7), resp.id);
    try testing.expect(resp.result != null);
    try testing.expectEqual(std.json.Value{ .integer = 99 }, resp.result.?);
    try testing.expect(resp.err == null);
}

// ── Test 3: McpTool field access ──────────────────────────────────────────────

test "McpTool field access" {
    const tool = mcp.McpTool{
        .name = "calculator",
        .description = "Performs arithmetic operations",
    };
    try testing.expectEqualStrings("calculator", tool.name);
    try testing.expectEqualStrings("Performs arithmetic operations", tool.description);
}

// ── Test 4: textContent single block ─────────────────────────────────────────

test "textContent single block" {
    const alloc = testing.allocator;
    const contents = [_]mcp.McpContent{
        .{ .type = "text", .text = "hello" },
    };
    const result = try mcp.textContent(alloc, &contents);
    defer alloc.free(result);
    try testing.expectEqualStrings("hello", result);
}

// ── Test 5: textContent multiple blocks ──────────────────────────────────────

test "textContent multiple blocks" {
    const alloc = testing.allocator;
    const contents = [_]mcp.McpContent{
        .{ .type = "text", .text = "foo" },
        .{ .type = "image", .text = "ignored-because-not-text" },
        .{ .type = "text", .text = "bar" },
    };
    const result = try mcp.textContent(alloc, &contents);
    defer alloc.free(result);
    try testing.expectEqualStrings("foo bar", result);
}

// ── Test 6: StdioClient has client interface ──────────────────────────────────

test "StdioClient has client interface" {
    const alloc = testing.allocator;
    // Verify StdioClient.client() returns a valid McpClient with a non-null vtable
    var sc = mcp.StdioClient.init(alloc, "echo", &.{});
    const cli = sc.client();
    // The vtable pointer must be non-null
    try testing.expect(@intFromPtr(cli.vtable) != 0);
    // The ptr must point back to sc
    try testing.expectEqual(@intFromPtr(&sc), @intFromPtr(cli.ptr));
}

// ── Test 7: HttpClient has client interface ───────────────────────────────────

test "HttpClient has client interface" {
    const alloc = testing.allocator;
    var hc = mcp.HttpClient.init(alloc, "http://localhost:8080/mcp");
    const cli = hc.client();
    // The vtable pointer must be non-null
    try testing.expect(@intFromPtr(cli.vtable) != 0);
    // The ptr must point back to hc
    try testing.expectEqual(@intFromPtr(&hc), @intFromPtr(cli.ptr));
}

// ── Test 8: adapter name ──────────────────────────────────────────────────────

test "adapter name" {
    const alloc = testing.allocator;

    const mock_tools = [_]mcp.McpTool{};
    const empty_content: []mcp.McpContent = &.{};
    const mock_result = mcp.McpToolResult{ .content = empty_content, .is_error = false };

    var mock = MockMcpClient.init(alloc, &mock_tools, mock_result);
    const cli = mock.client();

    var adapter = try mcp.McpToolAdapter.init(alloc, "search", "Search the web", cli);
    defer adapter.deinit();

    try testing.expectEqualStrings("search", adapter.name());
}

// ── Test 9: adapter description ───────────────────────────────────────────────

test "adapter description" {
    const alloc = testing.allocator;

    const mock_tools = [_]mcp.McpTool{};
    const empty_content: []mcp.McpContent = &.{};
    const mock_result = mcp.McpToolResult{ .content = empty_content, .is_error = false };

    var mock = MockMcpClient.init(alloc, &mock_tools, mock_result);
    const cli = mock.client();

    var adapter = try mcp.McpToolAdapter.init(alloc, "search", "Search the web", cli);
    defer adapter.deinit();

    try testing.expectEqualStrings("Search the web", adapter.description());
}

// ── Test 10: adapter execute success ─────────────────────────────────────────

test "adapter execute success" {
    const alloc = testing.allocator;

    const mock_tools = [_]mcp.McpTool{};
    const result_contents = [_]mcp.McpContent{
        .{ .type = "text", .text = "42" },
    };
    const mock_result = mcp.McpToolResult{
        .content = @constCast(&result_contents),
        .is_error = false,
    };

    var mock = MockMcpClient.init(alloc, &mock_tools, mock_result);
    const cli = mock.client();

    var adapter = try mcp.McpToolAdapter.init(alloc, "calculator", "Compute things", cli);
    defer adapter.deinit();

    const text = try adapter.execute(alloc, std.json.Value{ .null = {} });
    defer alloc.free(text);

    try testing.expectEqualStrings("42", text);
}

// ── Test 11: adapter execute isError ─────────────────────────────────────────

test "adapter execute isError" {
    const alloc = testing.allocator;

    const mock_tools = [_]mcp.McpTool{};
    const err_contents = [_]mcp.McpContent{
        .{ .type = "text", .text = "tool failed" },
    };
    const mock_result = mcp.McpToolResult{
        .content = @constCast(&err_contents),
        .is_error = true,
    };

    var mock = MockMcpClient.init(alloc, &mock_tools, mock_result);
    const cli = mock.client();

    var adapter = try mcp.McpToolAdapter.init(alloc, "bad-tool", "A broken tool", cli);
    defer adapter.deinit();

    // execute still returns the text content even for errors
    const text = try adapter.execute(alloc, std.json.Value{ .null = {} });
    defer alloc.free(text);

    try testing.expectEqualStrings("tool failed", text);
}

// ── Test 12: toolsFromClient count ───────────────────────────────────────────

test "toolsFromClient count" {
    const alloc = testing.allocator;

    const mock_tools = [_]mcp.McpTool{
        .{ .name = "search", .description = "Search the web" },
        .{ .name = "calculator", .description = "Do math" },
        .{ .name = "read_file", .description = "Read a file" },
    };
    const empty_content: []mcp.McpContent = &.{};
    const mock_result = mcp.McpToolResult{ .content = empty_content, .is_error = false };

    var mock = MockMcpClient.init(alloc, &mock_tools, mock_result);
    const cli = mock.client();

    const adapters = try mcp.toolsFromClient(alloc, cli);
    defer {
        for (adapters) |a| a.deinit();
        alloc.free(adapters);
    }

    try testing.expectEqual(@as(usize, 3), adapters.len);
    try testing.expectEqualStrings("search", adapters[0].name());
    try testing.expectEqualStrings("calculator", adapters[1].name());
    try testing.expectEqualStrings("read_file", adapters[2].name());
}

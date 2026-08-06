/// MCP (Model Context Protocol) support for Agenkit Zig
///
/// Implements the Model Context Protocol for tool discovery and invocation.
/// Provides StdioClient, HttpClient, McpServer, and a Tool adapter.
///
/// Protocol version: 2024-11-05
///
/// ## Overview
///
/// The MCP protocol uses JSON-RPC 2.0 over either stdio (subprocess) or HTTP.
/// This module provides:
/// - `StdioClient`: connects to an MCP server via subprocess stdin/stdout
/// - `HttpClient`: connects to an MCP server via HTTP POST
/// - `McpServer`: serves MCP protocol over stdio
/// - `toolsFromClient`: creates McpToolAdapter for each discovered tool
///
/// ## Example (StdioClient)
///
/// ```zig
/// var sc = StdioClient.init(allocator, "my-mcp-server", &.{"--arg"});
/// var cli = sc.client();
/// defer cli.deinit();
/// try cli.initialize();
/// const tools = try cli.listTools(allocator);
/// defer allocator.free(tools);
/// ```
const std = @import("std");
const ioc = @import("../io_compat.zig");
const agksync = @import("../sync_compat.zig");
const Allocator = std.mem.Allocator;

// ── Protocol constants ────────────────────────────────────────────────────────

pub const PROTOCOL_VERSION = "2024-11-05";
pub const CLIENT_VERSION = "0.89.0";

// ── Wire types ────────────────────────────────────────────────────────────────

/// JSON-RPC 2.0 request
pub const JsonRpcRequest = struct {
    jsonrpc: []const u8,
    id: u64,
    method: []const u8,
    params: ?std.json.Value = null,
};

/// JSON-RPC 2.0 response
pub const JsonRpcResponse = struct {
    jsonrpc: []const u8 = "2.0",
    id: u64 = 0,
    result: ?std.json.Value = null,
    err: ?JsonRpcError = null,
};

/// JSON-RPC 2.0 error object
pub const JsonRpcError = struct {
    code: i32,
    message: []const u8,
};

// ── Domain types ──────────────────────────────────────────────────────────────

/// A tool advertised by an MCP server
pub const McpTool = struct {
    name: []const u8,
    description: []const u8,
};

/// A single content block returned by a tool call
pub const McpContent = struct {
    type: []const u8,
    text: []const u8,
};

/// The result of calling a tool on an MCP server
pub const McpToolResult = struct {
    content: []McpContent,
    is_error: bool,
};

/// Identity information reported by an MCP server
pub const McpServerInfo = struct {
    name: []const u8 = "",
    version: []const u8 = "",
};

/// Concatenate all text-type content blocks, separated by spaces.
/// Caller owns the returned slice.
pub fn textContent(allocator: Allocator, contents: []const McpContent) ![]u8 {
    var parts = std.ArrayList(u8).empty;
    defer parts.deinit(allocator);
    for (contents) |c| {
        if (std.mem.eql(u8, c.type, "text") and c.text.len > 0) {
            if (parts.items.len > 0) try parts.append(allocator, ' ');
            try parts.appendSlice(allocator, c.text);
        }
    }
    return parts.toOwnedSlice(allocator);
}

// ── McpClient vtable interface ────────────────────────────────────────────────

/// Vtable-based interface for MCP clients.
/// Both `StdioClient` and `HttpClient` implement this interface.
pub const McpClient = struct {
    ptr: *anyopaque,
    vtable: *const VTable,

    pub const VTable = struct {
        initialize: *const fn (ptr: *anyopaque) anyerror!void,
        listTools: *const fn (ptr: *anyopaque, allocator: Allocator) anyerror![]McpTool,
        callTool: *const fn (ptr: *anyopaque, allocator: Allocator, name: []const u8, args: std.json.Value) anyerror!McpToolResult,
        serverInfo: *const fn (ptr: *anyopaque) McpServerInfo,
        deinit: *const fn (ptr: *anyopaque) void,
    };

    /// Send initialize handshake to the server.
    pub fn initialize(self: McpClient) !void {
        return self.vtable.initialize(self.ptr);
    }

    /// List tools available on the server.
    /// Caller owns the returned slice (and its string fields).
    pub fn listTools(self: McpClient, allocator: Allocator) ![]McpTool {
        return self.vtable.listTools(self.ptr, allocator);
    }

    /// Call a named tool with the given JSON arguments.
    pub fn callTool(self: McpClient, allocator: Allocator, name: []const u8, args: std.json.Value) !McpToolResult {
        return self.vtable.callTool(self.ptr, allocator, name, args);
    }

    /// Return the server identity reported during initialization.
    pub fn serverInfo(self: McpClient) McpServerInfo {
        return self.vtable.serverInfo(self.ptr);
    }

    /// Release all resources held by this client.
    pub fn deinit(self: McpClient) void {
        self.vtable.deinit(self.ptr);
    }
};

// ── StdioClient ───────────────────────────────────────────────────────────────

/// MCP client that communicates with a subprocess via stdin/stdout.
///
/// The subprocess must implement the MCP protocol (JSON-RPC over newline-delimited JSON).
pub const StdioClient = struct {
    allocator: Allocator,
    command: []const u8,
    args: []const []const u8,
    child: ?std.process.Child = null,
    next_id: u64 = 1,
    mutex: agksync.Mutex = .{},
    server_info_data: McpServerInfo = .{},

    pub fn init(allocator: Allocator, command: []const u8, args: []const []const u8) StdioClient {
        return .{
            .allocator = allocator,
            .command = command,
            .args = args,
        };
    }

    /// Return an `McpClient` interface backed by this StdioClient.
    pub fn client(self: *StdioClient) McpClient {
        return .{ .ptr = self, .vtable = &vtable };
    }

    const vtable = McpClient.VTable{
        .initialize = initializeImpl,
        .listTools = listToolsImpl,
        .callTool = callToolImpl,
        .serverInfo = serverInfoImpl,
        .deinit = deinitImpl,
    };

    fn initializeImpl(ptr: *anyopaque) !void {
        const self: *StdioClient = @ptrCast(@alignCast(ptr));

        // Build argv: [command, args...]
        const argv = try self.allocator.alloc([]const u8, 1 + self.args.len);
        defer self.allocator.free(argv);
        argv[0] = self.command;
        for (self.args, 0..) |a, i| argv[i + 1] = a;

        const child = try std.process.spawn(ioc.io(), .{
            .argv = argv,
            .stdin = .pipe,
            .stdout = .pipe,
            .stderr = .ignore,
        });
        self.child = child;

        // Build initialize params
        var params_str = std.ArrayList(u8).empty;
        defer params_str.deinit(self.allocator);
        try params_str.appendSlice(self.allocator, "{\"protocolVersion\":\"");
        try params_str.appendSlice(self.allocator, PROTOCOL_VERSION);
        try params_str.appendSlice(self.allocator, "\",\"clientVersion\":\"");
        try params_str.appendSlice(self.allocator, CLIENT_VERSION);
        try params_str.appendSlice(self.allocator, "\"}");

        // Build params as json.Value
        const parsed_params = try std.json.parseFromSlice(std.json.Value, self.allocator, params_str.items, .{});
        defer parsed_params.deinit();

        const result = try self.sendRequestRaw("initialize", parsed_params.value);
        defer freeJsonValue(self.allocator, result);

        // Extract server info if present
        if (result == .object) {
            const obj = result.object;
            if (obj.get("serverInfo")) |si| {
                if (si == .object) {
                    if (si.object.get("name")) |n| {
                        if (n == .string) {
                            self.server_info_data.name = try self.allocator.dupe(u8, n.string);
                        }
                    }
                    if (si.object.get("version")) |v| {
                        if (v == .string) {
                            self.server_info_data.version = try self.allocator.dupe(u8, v.string);
                        }
                    }
                }
            }
        }

        // Send initialized notification (fire and forget, no response)
        try self.sendNotification("notifications/initialized");
    }

    fn listToolsImpl(ptr: *anyopaque, allocator: Allocator) ![]McpTool {
        const self: *StdioClient = @ptrCast(@alignCast(ptr));
        const result = try self.sendRequestRaw("tools/list", null);
        defer freeJsonValue(self.allocator, result);
        return parseToolList(allocator, result);
    }

    fn callToolImpl(ptr: *anyopaque, allocator: Allocator, name: []const u8, args: std.json.Value) !McpToolResult {
        const self: *StdioClient = @ptrCast(@alignCast(ptr));

        // Build {"name":"<name>","arguments":<args>}
        const args_str = try std.json.Stringify.valueAlloc(self.allocator, args, .{});
        defer self.allocator.free(args_str);

        var params_json = std.ArrayList(u8).empty;
        defer params_json.deinit(self.allocator);
        try params_json.appendSlice(self.allocator, "{\"name\":\"");
        try params_json.appendSlice(self.allocator, name);
        try params_json.appendSlice(self.allocator, "\",\"arguments\":");
        try params_json.appendSlice(self.allocator, args_str);
        try params_json.append(self.allocator, '}');

        const parsed_params = try std.json.parseFromSlice(std.json.Value, self.allocator, params_json.items, .{});
        defer parsed_params.deinit();

        const result = try self.sendRequestRaw("tools/call", parsed_params.value);
        defer freeJsonValue(self.allocator, result);

        return parseToolResult(allocator, result);
    }

    fn serverInfoImpl(ptr: *anyopaque) McpServerInfo {
        const self: *StdioClient = @ptrCast(@alignCast(ptr));
        return self.server_info_data;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *StdioClient = @ptrCast(@alignCast(ptr));
        if (self.child) |*child| {
            if (child.stdin) |stdin| stdin.close(ioc.io());
            child.stdin = null;
            _ = child.wait(ioc.io()) catch {};
        }
        if (self.server_info_data.name.len > 0) self.allocator.free(self.server_info_data.name);
        if (self.server_info_data.version.len > 0) self.allocator.free(self.server_info_data.version);
    }

    /// Send a JSON-RPC request and return the parsed result value.
    /// `params` may be null (omitted from the wire message) or any json.Value.
    /// Caller must free the returned json.Value with freeJsonValue.
    fn sendRequestRaw(self: *StdioClient, method: []const u8, params: ?std.json.Value) !std.json.Value {
        self.mutex.lock();
        defer self.mutex.unlock();

        const child = &(self.child orelse return error.NotInitialized);
        const stdin_file = child.stdin orelse return error.NotInitialized;
        const stdout_file = child.stdout orelse return error.NotInitialized;

        const id = self.next_id;
        self.next_id += 1;

        // Build request line into a buffer
        var line = std.ArrayList(u8).empty;
        defer line.deinit(self.allocator);

        // "{\"jsonrpc\":\"2.0\",\"id\":<id>,\"method\":\"<method>\""
        try line.appendSlice(self.allocator, "{\"jsonrpc\":\"2.0\",\"id\":");
        var id_buf: [24]u8 = undefined;
        const id_str = std.fmt.bufPrint(&id_buf, "{d}", .{id}) catch unreachable;
        try line.appendSlice(self.allocator, id_str);
        try line.appendSlice(self.allocator, ",\"method\":\"");
        try line.appendSlice(self.allocator, method);
        try line.append(self.allocator, '"');

        if (params) |p| {
            const params_str = try std.json.Stringify.valueAlloc(self.allocator, p, .{});
            defer self.allocator.free(params_str);
            try line.appendSlice(self.allocator, ",\"params\":");
            try line.appendSlice(self.allocator, params_str);
        }

        try line.append(self.allocator, '}');
        try line.append(self.allocator, '\n');

        try stdin_file.writeStreamingAll(ioc.io(), line.items);

        // Read response line
        var read_buf: [65536]u8 = undefined;
        var file_reader = stdout_file.reader(ioc.io(), &read_buf);
        const resp_line = try file_reader.interface.takeDelimiterExclusive('\n');
        const resp_owned = try self.allocator.dupe(u8, resp_line);
        defer self.allocator.free(resp_owned);

        return parseRpcResponse(self.allocator, resp_owned);
    }

    /// Send a JSON-RPC notification (no id, no response expected).
    fn sendNotification(self: *StdioClient, method: []const u8) !void {
        const child = &(self.child orelse return error.NotInitialized);
        const stdin_file = child.stdin orelse return error.NotInitialized;

        var line = std.ArrayList(u8).empty;
        defer line.deinit(self.allocator);
        try line.appendSlice(self.allocator, "{\"jsonrpc\":\"2.0\",\"method\":\"");
        try line.appendSlice(self.allocator, method);
        try line.appendSlice(self.allocator, "\"}\n");
        try stdin_file.writeStreamingAll(ioc.io(), line.items);
    }
};

// ── HttpClient ────────────────────────────────────────────────────────────────

/// MCP client that communicates with a server via HTTP POST.
///
/// Uses the Streamable HTTP transport: all requests are POSTed to `base_url`.
pub const HttpClient = struct {
    allocator: Allocator,
    base_url: []const u8,
    next_id: u64 = 1,
    server_info_data: McpServerInfo = .{},

    pub fn init(allocator: Allocator, base_url: []const u8) HttpClient {
        return .{
            .allocator = allocator,
            .base_url = base_url,
        };
    }

    /// Return an `McpClient` interface backed by this HttpClient.
    pub fn client(self: *HttpClient) McpClient {
        return .{ .ptr = self, .vtable = &vtable };
    }

    const vtable = McpClient.VTable{
        .initialize = initializeImpl,
        .listTools = listToolsImpl,
        .callTool = callToolImpl,
        .serverInfo = serverInfoImpl,
        .deinit = deinitImpl,
    };

    fn initializeImpl(ptr: *anyopaque) !void {
        const self: *HttpClient = @ptrCast(@alignCast(ptr));

        var params_str = std.ArrayList(u8).empty;
        defer params_str.deinit(self.allocator);
        try params_str.appendSlice(self.allocator, "{\"protocolVersion\":\"");
        try params_str.appendSlice(self.allocator, PROTOCOL_VERSION);
        try params_str.appendSlice(self.allocator, "\",\"clientVersion\":\"");
        try params_str.appendSlice(self.allocator, CLIENT_VERSION);
        try params_str.appendSlice(self.allocator, "\"}");

        const parsed = try std.json.parseFromSlice(std.json.Value, self.allocator, params_str.items, .{});
        defer parsed.deinit();

        const result = try self.sendRequestRaw("initialize", parsed.value);
        defer freeJsonValue(self.allocator, result);

        if (result == .object) {
            const obj = result.object;
            if (obj.get("serverInfo")) |si| {
                if (si == .object) {
                    if (si.object.get("name")) |n| {
                        if (n == .string) self.server_info_data.name = try self.allocator.dupe(u8, n.string);
                    }
                    if (si.object.get("version")) |v| {
                        if (v == .string) self.server_info_data.version = try self.allocator.dupe(u8, v.string);
                    }
                }
            }
        }
    }

    fn listToolsImpl(ptr: *anyopaque, allocator: Allocator) ![]McpTool {
        const self: *HttpClient = @ptrCast(@alignCast(ptr));
        const result = try self.sendRequestRaw("tools/list", null);
        defer freeJsonValue(self.allocator, result);
        return parseToolList(allocator, result);
    }

    fn callToolImpl(ptr: *anyopaque, allocator: Allocator, name: []const u8, args: std.json.Value) !McpToolResult {
        const self: *HttpClient = @ptrCast(@alignCast(ptr));

        const args_str = try std.json.Stringify.valueAlloc(self.allocator, args, .{});
        defer self.allocator.free(args_str);

        var params_json = std.ArrayList(u8).empty;
        defer params_json.deinit(self.allocator);
        try params_json.appendSlice(self.allocator, "{\"name\":\"");
        try params_json.appendSlice(self.allocator, name);
        try params_json.appendSlice(self.allocator, "\",\"arguments\":");
        try params_json.appendSlice(self.allocator, args_str);
        try params_json.append(self.allocator, '}');

        const parsed = try std.json.parseFromSlice(std.json.Value, self.allocator, params_json.items, .{});
        defer parsed.deinit();

        const result = try self.sendRequestRaw("tools/call", parsed.value);
        defer freeJsonValue(self.allocator, result);

        return parseToolResult(allocator, result);
    }

    fn serverInfoImpl(ptr: *anyopaque) McpServerInfo {
        const self: *HttpClient = @ptrCast(@alignCast(ptr));
        return self.server_info_data;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *HttpClient = @ptrCast(@alignCast(ptr));
        if (self.server_info_data.name.len > 0) self.allocator.free(self.server_info_data.name);
        if (self.server_info_data.version.len > 0) self.allocator.free(self.server_info_data.version);
    }

    /// Send a JSON-RPC request via HTTP POST and return the parsed result.
    /// Caller must free the returned json.Value with freeJsonValue.
    fn sendRequestRaw(self: *HttpClient, method: []const u8, params: ?std.json.Value) !std.json.Value {
        const id = self.next_id;
        self.next_id += 1;

        // Build request body
        var body = std.ArrayList(u8).empty;
        defer body.deinit(self.allocator);

        try body.appendSlice(self.allocator, "{\"jsonrpc\":\"2.0\",\"id\":");
        var id_buf: [24]u8 = undefined;
        const id_str = std.fmt.bufPrint(&id_buf, "{d}", .{id}) catch unreachable;
        try body.appendSlice(self.allocator, id_str);
        try body.appendSlice(self.allocator, ",\"method\":\"");
        try body.appendSlice(self.allocator, method);
        try body.append(self.allocator, '"');

        if (params) |p| {
            const params_str = try std.json.Stringify.valueAlloc(self.allocator, p, .{});
            defer self.allocator.free(params_str);
            try body.appendSlice(self.allocator, ",\"params\":");
            try body.appendSlice(self.allocator, params_str);
        }

        try body.append(self.allocator, '}');

        // Make HTTP request
        var http_client = std.http.Client{ .allocator = self.allocator, .io = ioc.io() };
        defer http_client.deinit();

        const headers = [_]std.http.Header{
            .{ .name = "Content-Type", .value = "application/json" },
        };

        var response_body: std.Io.Writer.Allocating = .init(self.allocator);
        defer response_body.deinit();

        const result = try http_client.fetch(.{
            .location = .{ .url = self.base_url },
            .method = .POST,
            .payload = body.items,
            .extra_headers = &headers,
            .response_writer = &response_body.writer,
        });

        if (result.status != .ok) return error.HttpError;

        const response_data = try response_body.toOwnedSlice();
        defer self.allocator.free(response_data);

        return parseRpcResponse(self.allocator, response_data);
    }
};

// ── McpServer ─────────────────────────────────────────────────────────────────

/// A single tool entry registered with an McpServer.
pub const ServerToolEntry = struct {
    name: []const u8,
    description: []const u8,
    handler: *const fn (allocator: Allocator, args: std.json.Value) anyerror!McpToolResult,
};

/// MCP server that serves the protocol over stdio.
///
/// Call `serveStdio()` to start processing requests from stdin.
pub const McpServer = struct {
    allocator: Allocator,
    name: []const u8,
    version: []const u8,
    tools: []const ServerToolEntry,

    pub fn init(
        allocator: Allocator,
        name: []const u8,
        version: []const u8,
        tools: []const ServerToolEntry,
    ) McpServer {
        return .{
            .allocator = allocator,
            .name = name,
            .version = version,
            .tools = tools,
        };
    }

    /// Process a single JSON-RPC request string, returning the JSON response string.
    /// Caller owns the returned slice.
    /// Returns empty string for notifications (no response needed).
    pub fn handleRequestStr(self: *McpServer, request_json: []const u8) ![]u8 {
        const parsed = std.json.parseFromSlice(
            std.json.Value,
            self.allocator,
            request_json,
            .{},
        ) catch {
            return self.errorResponse(0, -32700, "Parse error");
        };
        defer parsed.deinit();

        if (parsed.value != .object) return self.errorResponse(0, -32600, "Invalid request");

        const obj = parsed.value.object;

        const id_val = obj.get("id") orelse std.json.Value{ .integer = 0 };
        const id: u64 = switch (id_val) {
            .integer => |n| @intCast(if (n >= 0) n else 0),
            .float => |f| @intFromFloat(if (f >= 0.0) f else 0.0),
            else => 0,
        };

        const method_val = obj.get("method") orelse return self.errorResponse(id, -32600, "Missing method");
        const method = switch (method_val) {
            .string => |s| s,
            else => return self.errorResponse(id, -32600, "Invalid method"),
        };

        const params = obj.get("params");
        return self.dispatch(id, method, params);
    }

    /// Serve MCP protocol over stdin/stdout until EOF.
    pub fn serveStdio(self: *McpServer) !void {
        const stdin_file = std.Io.File.stdin();
        const stdout_file = std.Io.File.stdout();

        var read_buf: [65536]u8 = undefined;
        var file_reader = stdin_file.reader(ioc.io(), &read_buf);

        while (true) {
            const line = file_reader.interface.takeDelimiterExclusive('\n') catch |err| switch (err) {
                error.EndOfStream => break,
                else => return err,
            };
            if (line.len == 0) continue;

            const line_owned = try self.allocator.dupe(u8, line);
            defer self.allocator.free(line_owned);

            const response = try self.handleRequestStr(line_owned);
            defer self.allocator.free(response);

            // Skip empty responses (notifications)
            if (response.len == 0) continue;

            var write_buf: [4096]u8 = undefined;
            var file_writer = stdout_file.writer(ioc.io(), &write_buf);
            try file_writer.interface.writeAll(response);
            try file_writer.interface.writeByte('\n');
            try file_writer.interface.flush();
        }
    }

    fn dispatch(self: *McpServer, id: u64, method: []const u8, params: ?std.json.Value) ![]u8 {
        if (std.mem.eql(u8, method, "initialize")) {
            return self.handleInitialize(id);
        } else if (std.mem.eql(u8, method, "tools/list")) {
            return self.handleToolsList(id);
        } else if (std.mem.eql(u8, method, "tools/call")) {
            return self.handleToolsCall(id, params);
        } else if (std.mem.startsWith(u8, method, "notifications/")) {
            // Notifications need no response
            return try self.allocator.dupe(u8, "");
        } else {
            return self.errorResponse(id, -32601, "Method not found");
        }
    }

    fn handleInitialize(self: *McpServer, id: u64) ![]u8 {
        var buf = std.ArrayList(u8).empty;
        defer buf.deinit(self.allocator);
        var id_buf: [24]u8 = undefined;
        const id_str = std.fmt.bufPrint(&id_buf, "{d}", .{id}) catch unreachable;
        try buf.appendSlice(self.allocator, "{\"jsonrpc\":\"2.0\",\"id\":");
        try buf.appendSlice(self.allocator, id_str);
        try buf.appendSlice(self.allocator, ",\"result\":{\"protocolVersion\":\"");
        try buf.appendSlice(self.allocator, PROTOCOL_VERSION);
        try buf.appendSlice(self.allocator, "\",\"serverInfo\":{\"name\":\"");
        try buf.appendSlice(self.allocator, self.name);
        try buf.appendSlice(self.allocator, "\",\"version\":\"");
        try buf.appendSlice(self.allocator, self.version);
        try buf.appendSlice(self.allocator, "\"}}}");
        return buf.toOwnedSlice(self.allocator);
    }

    fn handleToolsList(self: *McpServer, id: u64) ![]u8 {
        var buf = std.ArrayList(u8).empty;
        defer buf.deinit(self.allocator);
        var id_buf: [24]u8 = undefined;
        const id_str = std.fmt.bufPrint(&id_buf, "{d}", .{id}) catch unreachable;
        try buf.appendSlice(self.allocator, "{\"jsonrpc\":\"2.0\",\"id\":");
        try buf.appendSlice(self.allocator, id_str);
        try buf.appendSlice(self.allocator, ",\"result\":{\"tools\":[");
        for (self.tools, 0..) |tool, i| {
            if (i > 0) try buf.append(self.allocator, ',');
            try buf.appendSlice(self.allocator, "{\"name\":\"");
            try buf.appendSlice(self.allocator, tool.name);
            try buf.appendSlice(self.allocator, "\",\"description\":\"");
            try buf.appendSlice(self.allocator, tool.description);
            try buf.appendSlice(self.allocator, "\"}");
        }
        try buf.appendSlice(self.allocator, "]}}");
        return buf.toOwnedSlice(self.allocator);
    }

    fn handleToolsCall(self: *McpServer, id: u64, params: ?std.json.Value) ![]u8 {
        const p = params orelse return self.errorResponse(id, -32602, "Missing params");
        if (p != .object) return self.errorResponse(id, -32602, "Invalid params");

        const name_val = p.object.get("name") orelse return self.errorResponse(id, -32602, "Missing name");
        const name = switch (name_val) {
            .string => |s| s,
            else => return self.errorResponse(id, -32602, "Invalid name"),
        };
        const args = p.object.get("arguments") orelse std.json.Value{ .null = {} };

        for (self.tools) |tool| {
            if (!std.mem.eql(u8, tool.name, name)) continue;

            const tool_result = tool.handler(self.allocator, args) catch {
                return self.errorResponse(id, -32603, "Tool execution failed");
            };

            var buf = std.ArrayList(u8).empty;
            defer buf.deinit(self.allocator);
            var id_buf: [24]u8 = undefined;
            const id_str = std.fmt.bufPrint(&id_buf, "{d}", .{id}) catch unreachable;
            try buf.appendSlice(self.allocator, "{\"jsonrpc\":\"2.0\",\"id\":");
            try buf.appendSlice(self.allocator, id_str);
            try buf.appendSlice(self.allocator, ",\"result\":{\"isError\":");
            try buf.appendSlice(self.allocator, if (tool_result.is_error) "true" else "false");
            try buf.appendSlice(self.allocator, ",\"content\":[");
            for (tool_result.content, 0..) |c, i| {
                if (i > 0) try buf.append(self.allocator, ',');
                try buf.appendSlice(self.allocator, "{\"type\":\"");
                try buf.appendSlice(self.allocator, c.type);
                try buf.appendSlice(self.allocator, "\",\"text\":\"");
                try buf.appendSlice(self.allocator, c.text);
                try buf.appendSlice(self.allocator, "\"}");
            }
            try buf.appendSlice(self.allocator, "]}}");
            return buf.toOwnedSlice(self.allocator);
        }

        return self.errorResponse(id, -32602, "Tool not found");
    }

    fn errorResponse(self: *McpServer, id: u64, code: i32, message: []const u8) ![]u8 {
        var buf = std.ArrayList(u8).empty;
        defer buf.deinit(self.allocator);
        var id_buf: [24]u8 = undefined;
        const id_str = std.fmt.bufPrint(&id_buf, "{d}", .{id}) catch unreachable;
        var code_buf: [12]u8 = undefined;
        const code_str = std.fmt.bufPrint(&code_buf, "{d}", .{code}) catch unreachable;
        try buf.appendSlice(self.allocator, "{\"jsonrpc\":\"2.0\",\"id\":");
        try buf.appendSlice(self.allocator, id_str);
        try buf.appendSlice(self.allocator, ",\"error\":{\"code\":");
        try buf.appendSlice(self.allocator, code_str);
        try buf.appendSlice(self.allocator, ",\"message\":\"");
        try buf.appendSlice(self.allocator, message);
        try buf.appendSlice(self.allocator, "\"}}");
        return buf.toOwnedSlice(self.allocator);
    }
};

// ── McpToolAdapter ────────────────────────────────────────────────────────────

/// Wraps a named MCP tool + McpClient, providing name/description/execute methods.
///
/// Allows MCP tools to be used anywhere the agenkit Tool vtable pattern is expected.
/// The adapter holds copies of name and description strings.
pub const McpToolAdapter = struct {
    allocator: Allocator,
    tool_name: []const u8,
    tool_description: []const u8,
    mcp_client: McpClient,

    pub fn init(
        allocator: Allocator,
        tool_name: []const u8,
        tool_description: []const u8,
        mcp_client: McpClient,
    ) !*McpToolAdapter {
        const self = try allocator.create(McpToolAdapter);
        self.* = .{
            .allocator = allocator,
            .tool_name = try allocator.dupe(u8, tool_name),
            .tool_description = try allocator.dupe(u8, tool_description),
            .mcp_client = mcp_client,
        };
        return self;
    }

    pub fn deinit(self: *McpToolAdapter) void {
        self.allocator.free(self.tool_name);
        self.allocator.free(self.tool_description);
        self.allocator.destroy(self);
    }

    pub fn name(self: *const McpToolAdapter) []const u8 {
        return self.tool_name;
    }

    pub fn description(self: *const McpToolAdapter) []const u8 {
        return self.tool_description;
    }

    /// Call the MCP tool and return the concatenated text content.
    /// Caller owns the returned slice.
    pub fn execute(self: *McpToolAdapter, allocator: Allocator, args: std.json.Value) ![]u8 {
        const tool_result = try self.mcp_client.callTool(allocator, self.tool_name, args);
        defer {
            for (tool_result.content) |c| {
                allocator.free(c.type);
                allocator.free(c.text);
            }
            allocator.free(tool_result.content);
        }
        return textContent(allocator, tool_result.content);
    }
};

// ── toolsFromClient ───────────────────────────────────────────────────────────

/// Discover all tools on an MCP client and return an array of McpToolAdapter pointers.
/// The client must already be initialized.
/// Caller owns the returned slice and must deinit each adapter.
pub fn toolsFromClient(allocator: Allocator, mcp_client: McpClient) ![](*McpToolAdapter) {
    const tools = try mcp_client.listTools(allocator);
    defer {
        for (tools) |t| {
            allocator.free(t.name);
            allocator.free(t.description);
        }
        allocator.free(tools);
    }

    const adapters = try allocator.alloc(*McpToolAdapter, tools.len);
    errdefer allocator.free(adapters);

    var i: usize = 0;
    errdefer {
        for (adapters[0..i]) |a| a.deinit();
    }

    for (tools) |t| {
        adapters[i] = try McpToolAdapter.init(allocator, t.name, t.description, mcp_client);
        i += 1;
    }

    return adapters;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/// Parse a JSON-RPC response, returning the `result` field or error.
/// Caller must free the returned json.Value with freeJsonValue.
fn parseRpcResponse(allocator: Allocator, json_str: []const u8) !std.json.Value {
    const parsed = try std.json.parseFromSlice(std.json.Value, allocator, json_str, .{});
    defer parsed.deinit();

    if (parsed.value != .object) return std.json.Value{ .null = {} };
    const obj = parsed.value.object;
    if (obj.get("error") != null) return error.RpcError;
    if (obj.get("result")) |res_val| return deepCloneJsonValue(allocator, res_val);
    return std.json.Value{ .null = {} };
}

/// Parse a tools/list result into a slice of McpTool.
/// String fields in each McpTool are allocated from `allocator`.
fn parseToolList(allocator: Allocator, result: std.json.Value) ![]McpTool {
    if (result != .object) return try allocator.alloc(McpTool, 0);

    const tools_val = result.object.get("tools") orelse return try allocator.alloc(McpTool, 0);
    if (tools_val != .array) return try allocator.alloc(McpTool, 0);

    const items = tools_val.array.items;
    const tools = try allocator.alloc(McpTool, items.len);
    errdefer allocator.free(tools);

    for (items, 0..) |item, i| {
        if (item != .object) {
            tools[i] = .{ .name = try allocator.dupe(u8, ""), .description = try allocator.dupe(u8, "") };
            continue;
        }
        const obj = item.object;
        const tool_name = if (obj.get("name")) |n| switch (n) {
            .string => |s| try allocator.dupe(u8, s),
            else => try allocator.dupe(u8, ""),
        } else try allocator.dupe(u8, "");

        const tool_desc = if (obj.get("description")) |d| switch (d) {
            .string => |s| try allocator.dupe(u8, s),
            else => try allocator.dupe(u8, ""),
        } else try allocator.dupe(u8, "");

        tools[i] = .{ .name = tool_name, .description = tool_desc };
    }

    return tools;
}

/// Parse a tools/call result into an McpToolResult.
/// All strings in the result are allocated from `allocator`.
fn parseToolResult(allocator: Allocator, result: std.json.Value) !McpToolResult {
    if (result != .object) {
        return McpToolResult{ .content = try allocator.alloc(McpContent, 0), .is_error = false };
    }

    const obj = result.object;
    const is_error: bool = if (obj.get("isError")) |ie| switch (ie) {
        .bool => |b| b,
        else => false,
    } else false;

    const content_val = obj.get("content") orelse {
        return McpToolResult{ .content = try allocator.alloc(McpContent, 0), .is_error = is_error };
    };

    if (content_val != .array) {
        return McpToolResult{ .content = try allocator.alloc(McpContent, 0), .is_error = is_error };
    }

    const items = content_val.array.items;
    const content = try allocator.alloc(McpContent, items.len);
    errdefer allocator.free(content);

    for (items, 0..) |item, i| {
        if (item != .object) {
            content[i] = .{
                .type = try allocator.dupe(u8, "text"),
                .text = try allocator.dupe(u8, ""),
            };
            continue;
        }
        const cobj = item.object;
        const ctype = if (cobj.get("type")) |t| switch (t) {
            .string => |s| try allocator.dupe(u8, s),
            else => try allocator.dupe(u8, "text"),
        } else try allocator.dupe(u8, "text");

        const ctext = if (cobj.get("text")) |t| switch (t) {
            .string => |s| try allocator.dupe(u8, s),
            else => try allocator.dupe(u8, ""),
        } else try allocator.dupe(u8, "");

        content[i] = .{ .type = ctype, .text = ctext };
    }

    return McpToolResult{ .content = content, .is_error = is_error };
}

/// Deep-clone a json.Value using the given allocator.
fn deepCloneJsonValue(allocator: Allocator, value: std.json.Value) !std.json.Value {
    switch (value) {
        .null => return std.json.Value{ .null = {} },
        .bool => |b| return std.json.Value{ .bool = b },
        .integer => |n| return std.json.Value{ .integer = n },
        .float => |f| return std.json.Value{ .float = f },
        .number_string => |s| return std.json.Value{ .number_string = try allocator.dupe(u8, s) },
        .string => |s| return std.json.Value{ .string = try allocator.dupe(u8, s) },
        .array => |arr| {
            var new_arr = std.json.Array.init(allocator);
            errdefer new_arr.deinit();
            for (arr.items) |item| {
                const cloned = try deepCloneJsonValue(allocator, item);
                try new_arr.append(cloned);
            }
            return std.json.Value{ .array = new_arr };
        },
        .object => |obj| {
            var new_obj = std.json.ObjectMap.empty;
            errdefer new_obj.deinit(allocator);
            var it = obj.iterator();
            while (it.next()) |entry| {
                const key = try allocator.dupe(u8, entry.key_ptr.*);
                errdefer allocator.free(key);
                const val = try deepCloneJsonValue(allocator, entry.value_ptr.*);
                try new_obj.put(allocator, key, val);
            }
            return std.json.Value{ .object = new_obj };
        },
    }
}

/// Free a json.Value and all its nested allocations.
fn freeJsonValue(allocator: Allocator, value: std.json.Value) void {
    switch (value) {
        .string => |s| allocator.free(s),
        .number_string => |s| allocator.free(s),
        .array => |arr| {
            for (arr.items) |item| freeJsonValue(allocator, item);
            var mut_arr = arr;
            mut_arr.deinit();
        },
        .object => |obj| {
            var it = obj.iterator();
            while (it.next()) |entry| {
                freeJsonValue(allocator, entry.value_ptr.*);
            }
            var mut_obj = obj;
            mut_obj.deinit(allocator);
        },
        else => {},
    }
}

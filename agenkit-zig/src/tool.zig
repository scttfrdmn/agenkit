/// Tool interface for executable tools
///
/// Tools are executable functions that agents can call to interact with external
/// systems, APIs, or perform computations. Each tool has a name, description, and
/// optional JSON schema describing its parameters.
///
/// Design principles:
/// - VTable-based polymorphism (idiomatic Zig)
/// - Explicit error handling with error union types
/// - Explicit memory management with allocators
/// - Optional JSON schema for parameter validation
///
/// Example:
/// ```zig
/// const SearchTool = struct {
///     allocator: Allocator,
///
///     pub fn init(allocator: Allocator) !*SearchTool {
///         const self = try allocator.create(SearchTool);
///         self.* = SearchTool{ .allocator = allocator };
///         return self;
///     }
///
///     pub fn tool(self: *SearchTool) Tool {
///         return Tool{
///             .ptr = self,
///             .vtable = &.{
///                 .name = nameImpl,
///                 .description = descriptionImpl,
///                 .parameters_schema = parametersSchemaImpl,
///                 .execute = executeImpl,
///                 .deinit = deinitImpl,
///             },
///         };
///     }
///
///     fn nameImpl(ptr: *anyopaque) []const u8 {
///         _ = ptr;
///         return "search";
///     }
///
///     fn descriptionImpl(ptr: *anyopaque) []const u8 {
///         _ = ptr;
///         return "Search the web for information";
///     }
///
///     fn parametersSchemaImpl(ptr: *anyopaque, allocator: Allocator) ?json.Value {
///         _ = ptr;
///         _ = allocator;
///         // Return JSON schema describing parameters
///         return null;
///     }
///
///     fn executeImpl(ptr: *anyopaque, params: json.Value, allocator: Allocator) ToolError!ToolResult {
///         const self: *SearchTool = @ptrCast(@alignCast(ptr));
///         const query = params.object.get("query") orelse return error.MissingParameter;
///
///         // Perform search...
///         var result_data = json.ObjectMap.empty;
///         try result_data.put("results", json.Value{ .string = "Search results..." });
///
///         return ToolResult{
///             .id = "tool_use_id",
///             .result = json.Value{ .object = result_data },
///             .allocator = allocator,
///         };
///     }
///
///     fn deinitImpl(ptr: *anyopaque) void {
///         const self: *SearchTool = @ptrCast(@alignCast(ptr));
///         self.allocator.destroy(self);
///     }
/// };
/// ```
const std = @import("std");
const json = std.json;
const Allocator = std.mem.Allocator;

/// Error types for tool operations
pub const ToolError = error{
    ExecutionFailed,
    InvalidParameters,
    MissingParameter,
    Timeout,
    NotImplemented,
    OutOfMemory,
};

/// Result of tool execution
pub const ToolResult = struct {
    /// Unique identifier for this tool use
    id: []const u8,

    /// Result data (typically JSON object)
    result: json.Value,

    /// Allocator used for memory management
    allocator: Allocator,

    /// Create a new tool result
    pub fn init(allocator: Allocator, id: []const u8, result: json.Value) !ToolResult {
        const owned_id = try allocator.dupe(u8, id);
        return ToolResult{
            .id = owned_id,
            .result = result,
            .allocator = allocator,
        };
    }

    /// Free all resources associated with this result
    pub fn deinit(self: *ToolResult) void {
        self.allocator.free(self.id);
        freeJsonValue(self.allocator, self.result);
    }

    /// Free JSON value recursively
    fn freeJsonValue(allocator: Allocator, value: json.Value) void {
        switch (value) {
            .string => |s| allocator.free(s),
            .number_string => |s| allocator.free(s),
            .array => |arr| {
                for (arr.items) |item| {
                    freeJsonValue(allocator, item);
                }
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

    /// Get result as JSON string
    pub fn asJson(self: *const ToolResult, allocator: Allocator) ![]const u8 {
        var obj = json.ObjectMap.empty;
        defer obj.deinit(allocator);

        try obj.put(allocator, "id", json.Value{ .string = self.id });
        try obj.put(allocator, "result", self.result);

        return std.json.Stringify.valueAlloc(allocator, json.Value{ .object = obj }, .{});
    }
};

/// Tool interface - all tools must implement these methods via VTable
pub const Tool = struct {
    ptr: *anyopaque,
    vtable: *const VTable,

    pub const VTable = struct {
        /// Get tool identifier (must be unique within a tool set)
        name: *const fn (ptr: *anyopaque) []const u8,

        /// Get human-readable description of tool functionality
        description: *const fn (ptr: *anyopaque) []const u8,

        /// Get optional JSON schema for parameters (JSON Schema draft-07)
        parameters_schema: *const fn (ptr: *anyopaque, allocator: Allocator) ?json.Value,

        /// Execute the tool with given parameters
        execute: *const fn (ptr: *anyopaque, params: json.Value, allocator: Allocator) ToolError!ToolResult,

        /// Clean up resources
        deinit: *const fn (ptr: *anyopaque) void,
    };

    /// Get tool identifier
    ///
    /// Must be unique within a tool set. Used by LLMs to identify which tool to call.
    ///
    /// Returns: Unique tool name (e.g., "search", "calculator")
    pub fn name(self: Tool) []const u8 {
        return self.vtable.name(self.ptr);
    }

    /// Get tool description
    ///
    /// What this tool does. Used by LLMs to decide when to call it.
    /// Should be clear and concise, describing the tool's purpose and capabilities.
    ///
    /// Returns: Human-readable description of tool functionality
    pub fn description(self: Tool) []const u8 {
        return self.vtable.description(self.ptr);
    }

    /// Get JSON schema for tool parameters
    ///
    /// Optional schema describing the expected parameters. Used by LLMs to understand
    /// how to call the tool with correct parameters. Should follow JSON Schema draft-07.
    ///
    /// Returns: Optional JSON schema object, or null if no schema provided
    pub fn parametersSchema(self: Tool, allocator: Allocator) ?json.Value {
        return self.vtable.parameters_schema(self.ptr, allocator);
    }

    /// Execute the tool with given parameters
    ///
    /// Executes the tool with the provided parameters. Parameters are passed as a
    /// JSON value for flexibility. The tool should validate parameters against its
    /// schema if provided.
    ///
    /// Params:
    ///   - params: Tool parameters as JSON value
    ///   - allocator: Allocator for result memory
    ///
    /// Returns: ToolResult on success or ToolError on failure
    ///
    /// Example:
    /// ```zig
    /// var params = json.ObjectMap.empty;
    /// try params.put("query", json.Value{ .string = "What is the weather?" });
    ///
    /// var result = try tool.execute(json.Value{ .object = params }, allocator);
    /// defer result.deinit();
    ///
    /// std.debug.print("Result: {s}\n", .{try result.asJson(allocator)});
    /// ```
    pub fn execute(self: Tool, params: json.Value, allocator: Allocator) !ToolResult {
        return self.vtable.execute(self.ptr, params, allocator);
    }

    /// Clean up resources
    pub fn deinit(self: Tool) void {
        self.vtable.deinit(self.ptr);
    }
};

/// Example tool that echoes back its parameters (useful for testing)
pub const EchoTool = struct {
    allocator: Allocator,

    pub fn init(allocator: Allocator) !*EchoTool {
        const self = try allocator.create(EchoTool);
        self.* = EchoTool{ .allocator = allocator };
        return self;
    }

    pub fn tool(self: *EchoTool) Tool {
        return Tool{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .description = descriptionImpl,
                .parameters_schema = parametersSchemaImpl,
                .execute = executeImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "echo";
    }

    fn descriptionImpl(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "Echo back the provided parameters";
    }

    fn parametersSchemaImpl(ptr: *anyopaque, allocator: Allocator) ?json.Value {
        _ = ptr;
        _ = allocator;
        // Could return a schema describing expected parameters
        return null;
    }

    fn executeImpl(ptr: *anyopaque, params: json.Value, allocator: Allocator) ToolError!ToolResult {
        const self: *EchoTool = @ptrCast(@alignCast(ptr));
        _ = self;

        // Echo back the parameters as the result
        // ToolResult takes ownership of params and will free it on deinit
        return ToolResult.init(allocator, "echo_result", params) catch {
            return ToolError.ExecutionFailed;
        };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *EchoTool = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};

test "EchoTool basic functionality" {
    const allocator = std.testing.allocator;

    var echo = try EchoTool.init(allocator);
    defer echo.tool().deinit();

    const tool_iface = echo.tool();
    try std.testing.expectEqualStrings("echo", tool_iface.name());
    try std.testing.expectEqualStrings("Echo back the provided parameters", tool_iface.description());

    // Create test parameters
    var params = json.ObjectMap.empty;
    const test_str = try allocator.dupe(u8, "value");
    try params.put(allocator, "test", json.Value{ .string = test_str });

    // Execute tool (ToolResult takes ownership of params and its contents)
    var result = try tool_iface.execute(json.Value{ .object = params }, allocator);
    defer result.deinit();

    // Verify result contains our parameters
    try std.testing.expectEqualStrings("echo_result", result.id);
    const test_value = result.result.object.get("test");
    try std.testing.expect(test_value != null);
    try std.testing.expectEqualStrings("value", test_value.?.string);
}

test "ToolResult creation and cleanup" {
    const allocator = std.testing.allocator;

    var result_data = json.ObjectMap.empty;
    const status_str = try allocator.dupe(u8, "success");
    try result_data.put(allocator, "status", json.Value{ .string = status_str });

    var result = try ToolResult.init(allocator, "test_id", json.Value{ .object = result_data });
    defer result.deinit();

    try std.testing.expectEqualStrings("test_id", result.id);
    const status = result.result.object.get("status");
    try std.testing.expect(status != null);
    try std.testing.expectEqualStrings("success", status.?.string);
}

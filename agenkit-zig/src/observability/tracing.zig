/// OpenTelemetry tracing support for Agenkit
///
/// This module provides distributed tracing capabilities using OpenTelemetry
/// standards, including W3C Trace Context propagation.
///
/// Key components:
/// - SpanContext: Trace context (trace_id, span_id, trace_flags)
/// - Span: Unit of work with timing and attributes
/// - TracingMiddleware: Agent wrapper that adds tracing
/// - W3C Trace Context: traceparent/tracestate header support
///
/// Example:
/// ```zig
/// // Wrap an agent with tracing
/// var base_agent = try EchoAgent.init(allocator);
/// var traced_agent = try TracingMiddleware.init(allocator, base_agent.agent(), "echo-service");
/// defer traced_agent.deinit();
///
/// // Process with trace context
/// var msg = try Message.withText(allocator, .user, "Hello");
/// try msg.setMetadata("traceparent", traceparent_value);
///
/// const result = try traced_agent.agent().process(msg);
/// // Response will include trace context in metadata
/// ```

const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const StreamCallbacks = @import("../agent.zig").StreamCallbacks;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const Allocator = std.mem.Allocator;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;

/// Span context containing trace identifiers
pub const SpanContext = struct {
    trace_id: [16]u8, // 128-bit trace ID
    span_id: [8]u8, // 64-bit span ID
    trace_flags: u8, // 8-bit trace flags (sampled, etc.)

    /// Create a new root span context
    pub fn root(allocator: Allocator) !SpanContext {
        _ = allocator;
        var ctx = SpanContext{
            .trace_id = undefined,
            .span_id = undefined,
            .trace_flags = 0x01, // Sampled by default
        };

        // Generate random trace_id and span_id
        var prng = std.Random.DefaultPrng.init(@intCast(std.time.timestamp()));
        const random = prng.random();
        random.bytes(&ctx.trace_id);
        random.bytes(&ctx.span_id);

        return ctx;
    }

    /// Create a child span context
    pub fn child(self: *const SpanContext, allocator: Allocator) !SpanContext {
        _ = allocator;
        var ctx = SpanContext{
            .trace_id = self.trace_id,
            .span_id = undefined,
            .trace_flags = self.trace_flags,
        };

        // Generate new span_id
        var prng = std.Random.DefaultPrng.init(@intCast(std.time.timestamp()));
        const random = prng.random();
        random.bytes(&ctx.span_id);

        return ctx;
    }

    /// Parse from W3C traceparent header
    /// Format: "00-{trace_id}-{span_id}-{flags}"
    pub fn fromTraceparent(traceparent: []const u8) !SpanContext {
        if (traceparent.len != 55) return error.InvalidTraceparent;
        if (traceparent[0] != '0' or traceparent[1] != '0') return error.UnsupportedVersion;
        if (traceparent[2] != '-') return error.InvalidFormat;
        if (traceparent[35] != '-') return error.InvalidFormat;
        if (traceparent[52] != '-') return error.InvalidFormat;

        var ctx = SpanContext{
            .trace_id = undefined,
            .span_id = undefined,
            .trace_flags = undefined,
        };

        // Parse trace_id (32 hex chars = 16 bytes)
        const trace_id_hex = traceparent[3..35];
        for (0..16) |i| {
            ctx.trace_id[i] = try std.fmt.parseInt(u8, trace_id_hex[i * 2 .. i * 2 + 2], 16);
        }

        // Parse span_id (16 hex chars = 8 bytes)
        const span_id_hex = traceparent[36..52];
        for (0..8) |i| {
            ctx.span_id[i] = try std.fmt.parseInt(u8, span_id_hex[i * 2 .. i * 2 + 2], 16);
        }

        // Parse flags (2 hex chars = 1 byte)
        ctx.trace_flags = try std.fmt.parseInt(u8, traceparent[53..55], 16);

        return ctx;
    }

    /// Format as W3C traceparent header
    pub fn toTraceparent(self: *const SpanContext, allocator: Allocator) ![]const u8 {
        var buf = std.ArrayList(u8){};
        defer buf.deinit(allocator);

        try buf.appendSlice(allocator, "00-");

        // trace_id (16 bytes = 32 hex chars)
        for (self.trace_id) |byte| {
            const hex = try std.fmt.allocPrint(allocator, "{x:0>2}", .{byte});
            defer allocator.free(hex);
            try buf.appendSlice(allocator, hex);
        }

        try buf.append(allocator, '-');

        // span_id (8 bytes = 16 hex chars)
        for (self.span_id) |byte| {
            const hex = try std.fmt.allocPrint(allocator, "{x:0>2}", .{byte});
            defer allocator.free(hex);
            try buf.appendSlice(allocator, hex);
        }

        try buf.append(allocator, '-');

        // flags (1 byte = 2 hex chars)
        const flags_hex = try std.fmt.allocPrint(allocator, "{x:0>2}", .{self.trace_flags});
        defer allocator.free(flags_hex);
        try buf.appendSlice(allocator, flags_hex);

        return try buf.toOwnedSlice(allocator);
    }

    /// Check if trace is sampled
    pub fn isSampled(self: *const SpanContext) bool {
        return (self.trace_flags & 0x01) != 0;
    }
};

/// Span representing a unit of work
pub const Span = struct {
    context: SpanContext,
    name: []const u8,
    start_time: i128, // Unix timestamp in nanoseconds
    end_time: ?i128,
    attributes: std.StringHashMap([]const u8),
    allocator: Allocator,

    /// Create a new span
    pub fn init(allocator: Allocator, context: SpanContext, name: []const u8) !*Span {
        const self = try allocator.create(Span);
        self.* = Span{
            .context = context,
            .name = try allocator.dupe(u8, name),
            .start_time = std.time.nanoTimestamp(),
            .end_time = null,
            .attributes = std.StringHashMap([]const u8).init(allocator),
            .allocator = allocator,
        };
        return self;
    }

    /// End the span
    pub fn end(self: *Span) void {
        self.end_time = std.time.nanoTimestamp();
    }

    /// Set an attribute
    pub fn setAttribute(self: *Span, key: []const u8, value: []const u8) !void {
        const key_owned = try self.allocator.dupe(u8, key);
        const value_owned = try self.allocator.dupe(u8, value);
        try self.attributes.put(key_owned, value_owned);
    }

    /// Get duration in milliseconds
    pub fn durationMs(self: *const Span) ?f64 {
        if (self.end_time) |end_time_val| {
            const duration_ns = end_time_val - self.start_time;
            return @as(f64, @floatFromInt(duration_ns)) / 1_000_000.0;
        }
        return null;
    }

    /// Clean up
    pub fn deinit(self: *Span) void {
        self.allocator.free(self.name);
        var it = self.attributes.iterator();
        while (it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            self.allocator.free(entry.value_ptr.*);
        }
        self.attributes.deinit();
        self.allocator.destroy(self);
    }
};

/// Tracing middleware that wraps agents
pub const TracingMiddleware = struct {
    allocator: Allocator,
    inner: Agent,
    service_name: []const u8,

    /// Initialize tracing middleware
    pub fn init(
        allocator: Allocator,
        inner: Agent,
        service_name: []const u8,
    ) !*TracingMiddleware {
        const self = try allocator.create(TracingMiddleware);
        self.* = TracingMiddleware{
            .allocator = allocator,
            .inner = inner,
            .service_name = try allocator.dupe(u8, service_name),
        };
        return self;
    }

    /// Convert to Agent interface

    fn processStream(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        callbacks.onError(AgentError.NotImplemented);
    }

    pub fn agent(self: *TracingMiddleware) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = name,
                .capabilities = capabilities,
                .process = process,
                .process_stream = processStream,
                .introspect = introspect,
                .deinit = deinitVTable,
            },
        };
    }

    /// Name implementation
    fn name(ptr: *anyopaque) []const u8 {
        const self: *TracingMiddleware = @ptrCast(@alignCast(ptr));
        return self.service_name;
    }

    /// Capabilities implementation
    fn capabilities(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *TracingMiddleware = @ptrCast(@alignCast(ptr));
        return self.inner.capabilities(allocator);
    }

    /// Process implementation with tracing
    fn process(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *TracingMiddleware = @ptrCast(@alignCast(ptr));

        // Extract or create span context
        const span_context = blk: {
            if (message.getMetadata("traceparent")) |traceparent_value| {
                if (traceparent_value == .string) {
                    if (SpanContext.fromTraceparent(traceparent_value.string)) |ctx| {
                        // Create child span
                        break :blk try ctx.child(self.allocator);
                    } else |_| {
                        // Invalid traceparent, create new root
                        break :blk try SpanContext.root(self.allocator);
                    }
                }
            }
            // No traceparent, create new root
            break :blk try SpanContext.root(self.allocator);
        };

        // Create span
        var span = Span.init(
            self.allocator,
            span_context,
            self.service_name,
        ) catch {
            return AgentError.ProcessingFailed;
        };
        defer span.deinit();

        // Set attributes (ignore errors for non-critical operations)
        span.setAttribute("service.name", self.service_name) catch {};
        span.setAttribute("message.role", @tagName(message.role)) catch {};

        // Process with inner agent
        const result = self.inner.process(message) catch |err| {
            span.end();
            span.setAttribute("error", "true") catch {};
            span.setAttribute("error.type", @errorName(err)) catch {};
            return err;
        };

        // End span
        span.end();

        // Inject trace context into response
        var response = result.unwrap() catch {
            return AgentError.ProcessingFailed;
        };
        const traceparent = span.context.toTraceparent(self.allocator) catch {
            return Result{ .ok = response };
        };
        errdefer self.allocator.free(traceparent);

        const traceparent_value = std.json.Value{ .string = traceparent };
        response.setMetadata("traceparent", traceparent_value) catch {};

        // Add span duration
        if (span.durationMs()) |duration| {
            const duration_value = std.json.Value{ .float = duration };
            response.setMetadata("span_duration_ms", duration_value) catch {};
        }

        return Result{ .ok = response };
    }

    /// Introspect implementation
    fn introspect(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *TracingMiddleware = @ptrCast(@alignCast(ptr));
        const caps = try capabilities(ptr, allocator);
        defer allocator.free(caps);
        return createDefaultIntrospectionResult(allocator, self.service_name, caps);
    }

    /// Deinit implementation for VTable
    fn deinitVTable(ptr: *anyopaque) void {
        const self: *TracingMiddleware = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    /// Public deinit
    pub fn deinit(self: *TracingMiddleware) void {
        self.inner.deinit();
        self.allocator.free(self.service_name);
        self.allocator.destroy(self);
    }
};

// Tests
test "SpanContext root generation" {
    const allocator = std.testing.allocator;

    const ctx = try SpanContext.root(allocator);
    try std.testing.expect(ctx.isSampled());
}

test "SpanContext child generation" {
    const allocator = std.testing.allocator;

    const parent = try SpanContext.root(allocator);
    const child = try parent.child(allocator);

    // Child should have same trace_id
    try std.testing.expectEqualSlices(u8, &parent.trace_id, &child.trace_id);
    // But different span_id
    try std.testing.expect(!std.mem.eql(u8, &parent.span_id, &child.span_id));
}

test "SpanContext traceparent parsing" {
    const traceparent = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01";
    const ctx = try SpanContext.fromTraceparent(traceparent);

    try std.testing.expect(ctx.isSampled());
    try std.testing.expectEqual(@as(u8, 0x01), ctx.trace_flags);
}

test "SpanContext traceparent generation" {
    const allocator = std.testing.allocator;

    const ctx = try SpanContext.root(allocator);
    const traceparent = try ctx.toTraceparent(allocator);
    defer allocator.free(traceparent);

    try std.testing.expect(traceparent.len == 55);
    try std.testing.expect(std.mem.startsWith(u8, traceparent, "00-"));

    // Should be able to parse it back
    const parsed = try SpanContext.fromTraceparent(traceparent);
    try std.testing.expectEqualSlices(u8, &ctx.trace_id, &parsed.trace_id);
    try std.testing.expectEqualSlices(u8, &ctx.span_id, &parsed.span_id);
    try std.testing.expectEqual(ctx.trace_flags, parsed.trace_flags);
}

test "Span creation and attributes" {
    const allocator = std.testing.allocator;

    const ctx = try SpanContext.root(allocator);
    var span = try Span.init(allocator, ctx, "test-span");
    defer span.deinit();

    try span.setAttribute("key1", "value1");
    try span.setAttribute("key2", "value2");

    span.end();

    const duration = span.durationMs();
    try std.testing.expect(duration != null);
    try std.testing.expect(duration.? >= 0);
}

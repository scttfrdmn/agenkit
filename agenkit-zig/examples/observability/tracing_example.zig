/// OpenTelemetry Tracing Example
///
/// This example demonstrates distributed tracing capabilities using OpenTelemetry
/// standards with W3C Trace Context propagation.
///
/// Features demonstrated:
/// 1. Wrapping agents with TracingMiddleware
/// 2. Automatic span creation and propagation
/// 3. W3C Trace Context (traceparent) headers
/// 4. Parent-child span relationships
/// 5. Span attributes and timing
///
/// Usage:
///   zig build run-tracing-example

const std = @import("std");
const agenkit = @import("agenkit");
const EchoAgent = agenkit.EchoAgent;
const Message = agenkit.Message;
const TracingMiddleware = agenkit.observability.TracingMiddleware;
const SpanContext = agenkit.observability.SpanContext;

pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== OpenTelemetry Tracing Example ===\n\n", .{});

    // Example 1: Basic tracing
    std.debug.print("--- Example 1: Basic Agent Tracing ---\n", .{});
    try basicTracing(allocator);

    // Example 2: Trace context propagation
    std.debug.print("\n--- Example 2: Trace Context Propagation ---\n", .{});
    try traceContextPropagation(allocator);

    // Example 3: Multi-agent tracing chain
    std.debug.print("\n--- Example 3: Multi-Agent Trace Chain ---\n", .{});
    try multiAgentTracing(allocator);

    // Example 4: W3C Trace Context parsing
    std.debug.print("\n--- Example 4: W3C Trace Context ---\n", .{});
    try w3cTraceContext(allocator);

    std.debug.print("\n=== All Examples Complete ===\n", .{});
}

/// Example 1: Basic agent tracing
fn basicTracing(allocator: std.mem.Allocator) !void {
    // Create a base agent
    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    // Wrap with tracing middleware
    var traced = try TracingMiddleware.init(allocator, echo.agent(), "echo-service");
    defer traced.deinit();

    // Process a message
    var msg = try Message.withText(allocator, .user, "Hello, tracing!");
    defer msg.deinit();

    const result = try traced.agent().process(msg);
    var response = try result.unwrap();
    defer {
        // Free traceparent string before deiniting response
        if (response.getMetadata("traceparent")) |tp| {
            if (tp == .string) {
                allocator.free(tp.string);
            }
        }
        response.deinit();
    }

    std.debug.print("Input: {s}\n", .{msg.content.text});
    std.debug.print("Output: {s}\n", .{response.content.text});

    // Extract trace metadata
    if (response.getMetadata("traceparent")) |traceparent| {
        std.debug.print("Traceparent: {s}\n", .{traceparent.string});
    }

    if (response.getMetadata("span_duration_ms")) |duration| {
        std.debug.print("Duration: {d:.2}ms\n", .{duration.float});
    }

    std.debug.print("✅ Trace context automatically added to response!\n", .{});
}

/// Example 2: Trace context propagation
fn traceContextPropagation(allocator: std.mem.Allocator) !void {
    // Create root span context
    const root_ctx = try SpanContext.root(allocator);
    const root_traceparent = try root_ctx.toTraceparent(allocator);
    defer allocator.free(root_traceparent);

    std.debug.print("Root Traceparent: {s}\n", .{root_traceparent});
    std.debug.print("Sampled: {}\n\n", .{root_ctx.isSampled()});

    // Setup traced agent
    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();
    var traced = try TracingMiddleware.init(allocator, echo.agent(), "child-service");
    defer traced.deinit();

    // Create message with parent trace context
    var msg = try Message.withText(allocator, .user, "Child span message");
    defer msg.deinit();

    // Inject parent trace context
    const traceparent_value = std.json.Value{ .string = root_traceparent };
    try msg.setMetadata("traceparent", traceparent_value);

    // Process - will create child span
    const result = try traced.agent().process(msg);
    var response = try result.unwrap();
    defer {
        // Free traceparent string before deiniting response
        if (response.getMetadata("traceparent")) |tp| {
            if (tp == .string) {
                allocator.free(tp.string);
            }
        }
        response.deinit();
    }

    // Extract child trace context
    if (response.getMetadata("traceparent")) |child_traceparent| {
        std.debug.print("Child Traceparent: {s}\n", .{child_traceparent.string});

        // Parse both to show relationship
        const parent_parsed = try SpanContext.fromTraceparent(root_traceparent);
        const child_parsed = try SpanContext.fromTraceparent(child_traceparent.string);

        // Verify same trace_id
        const same_trace = std.mem.eql(u8, &parent_parsed.trace_id, &child_parsed.trace_id);
        std.debug.print("Same Trace ID: {}\n", .{same_trace});

        // Verify different span_id
        const diff_span = !std.mem.eql(u8, &parent_parsed.span_id, &child_parsed.span_id);
        std.debug.print("Different Span ID: {}\n", .{diff_span});

        std.debug.print("✅ Parent-child relationship established!\n", .{});
    }
}

/// Example 3: Multi-agent tracing chain
fn multiAgentTracing(allocator: std.mem.Allocator) !void {
    // Create a chain of traced agents
    var echo1 = try EchoAgent.init(allocator);
    defer echo1.agent().deinit();
    var traced1 = try TracingMiddleware.init(allocator, echo1.agent(), "service-1");
    defer traced1.deinit();

    var echo2 = try EchoAgent.init(allocator);
    defer echo2.agent().deinit();
    var traced2 = try TracingMiddleware.init(allocator, echo2.agent(), "service-2");
    defer traced2.deinit();

    var echo3 = try EchoAgent.init(allocator);
    defer echo3.agent().deinit();
    var traced3 = try TracingMiddleware.init(allocator, echo3.agent(), "service-3");
    defer traced3.deinit();

    // Process through chain
    var msg = try Message.withText(allocator, .user, "Chain message");
    defer msg.deinit();

    std.debug.print("Processing through service chain...\n\n", .{});

    // Service 1
    const result1 = try traced1.agent().process(msg);
    var response1 = try result1.unwrap();
    defer {
        if (response1.getMetadata("traceparent")) |tp| {
            if (tp == .string) allocator.free(tp.string);
        }
        response1.deinit();
    }

    if (response1.getMetadata("traceparent")) |tp1| {
        std.debug.print("Service 1 Traceparent: {s}\n", .{tp1.string});
    }
    if (response1.getMetadata("span_duration_ms")) |d1| {
        std.debug.print("Service 1 Duration: {d:.2}ms\n\n", .{d1.float});
    }

    // Service 2 (receives trace context from service 1)
    const result2 = try traced2.agent().process(response1);
    var response2 = try result2.unwrap();
    defer {
        if (response2.getMetadata("traceparent")) |tp| {
            if (tp == .string) allocator.free(tp.string);
        }
        response2.deinit();
    }

    if (response2.getMetadata("traceparent")) |tp2| {
        std.debug.print("Service 2 Traceparent: {s}\n", .{tp2.string});
    }
    if (response2.getMetadata("span_duration_ms")) |d2| {
        std.debug.print("Service 2 Duration: {d:.2}ms\n\n", .{d2.float});
    }

    // Service 3 (receives trace context from service 2)
    const result3 = try traced3.agent().process(response2);
    var response3 = try result3.unwrap();
    defer {
        if (response3.getMetadata("traceparent")) |tp| {
            if (tp == .string) allocator.free(tp.string);
        }
        response3.deinit();
    }

    if (response3.getMetadata("traceparent")) |tp3| {
        std.debug.print("Service 3 Traceparent: {s}\n", .{tp3.string});
    }
    if (response3.getMetadata("span_duration_ms")) |d3| {
        std.debug.print("Service 3 Duration: {d:.2}ms\n\n", .{d3.float});
    }

    std.debug.print("✅ Trace propagated through entire chain!\n", .{});
}

/// Example 4: W3C Trace Context parsing and generation
fn w3cTraceContext(allocator: std.mem.Allocator) !void {
    // Example traceparent from external system
    const external_traceparent = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01";

    std.debug.print("External Traceparent: {s}\n\n", .{external_traceparent});

    // Parse it
    const ctx = try SpanContext.fromTraceparent(external_traceparent);

    std.debug.print("Parsed Trace Context:\n", .{});
    std.debug.print("- Version: 00\n", .{});
    std.debug.print("- Trace ID: ", .{});
    for (ctx.trace_id) |byte| {
        std.debug.print("{x:0>2}", .{byte});
    }
    std.debug.print("\n", .{});

    std.debug.print("- Span ID: ", .{});
    for (ctx.span_id) |byte| {
        std.debug.print("{x:0>2}", .{byte});
    }
    std.debug.print("\n", .{});

    std.debug.print("- Flags: {x:0>2}\n", .{ctx.trace_flags});
    std.debug.print("- Sampled: {}\n\n", .{ctx.isSampled()});

    // Create child context
    const child = try ctx.child(allocator);
    const child_traceparent = try child.toTraceparent(allocator);
    defer allocator.free(child_traceparent);

    std.debug.print("Child Traceparent: {s}\n", .{child_traceparent});
    std.debug.print("✅ W3C Trace Context fully supported!\n", .{});

    // Demonstrate cross-language compatibility
    std.debug.print("\nCross-Language Compatibility:\n", .{});
    std.debug.print("This traceparent header works with:\n", .{});
    std.debug.print("- Python OpenTelemetry\n", .{});
    std.debug.print("- Go OpenTelemetry\n", .{});
    std.debug.print("- TypeScript OpenTelemetry\n", .{});
    std.debug.print("- C++ OpenTelemetry\n", .{});
    std.debug.print("- Rust OpenTelemetry\n", .{});
    std.debug.print("- Any W3C Trace Context compliant system!\n", .{});
}

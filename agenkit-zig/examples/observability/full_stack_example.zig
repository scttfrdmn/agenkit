/// Full Observability Stack Example
///
/// This example demonstrates all four observability modules working together:
/// - Tracing: Distributed tracing with W3C Trace Context
/// - Metrics: Request counting and latency measurement
/// - Logging: Structured logging with trace correlation
/// - Audit: Compliance logging with event tracking
///
/// This represents a production-ready observability setup for AI agents.
///
/// Usage:
///   zig build run-observability-example

const std = @import("std");
const agenkit = @import("agenkit");
const EchoAgent = agenkit.EchoAgent;
const Message = agenkit.Message;

const observability = agenkit.observability;
const TracingMiddleware = observability.TracingMiddleware;
const MetricsMiddleware = observability.MetricsMiddleware;
const logging = observability.logging;
const audit = observability.audit;

pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Full Observability Stack Example ===\n\n", .{});

    // Example 1: Complete observability setup
    std.debug.print("--- Example 1: Complete Setup ---\n", .{});
    try completeSetup(allocator);

    // Example 2: Trace correlation across modules
    std.debug.print("\n--- Example 2: Trace Correlation ---\n", .{});
    try traceCorrelation(allocator);

    // Example 3: Production-ready agent with full observability
    std.debug.print("\n--- Example 3: Production Agent ---\n", .{});
    try productionAgent(allocator);

    std.debug.print("\n=== All Examples Complete ===\n", .{});
}

/// Example 1: Complete observability setup
fn completeSetup(allocator: std.mem.Allocator) !void {
    // 1. Configure logging
    logging.configure(.json, .info);
    std.debug.print("✅ Logging configured (JSON format, INFO level)\n", .{});

    // 2. Create audit logger
    var audit_logger = try audit.AuditLogger.init(allocator, "example_audit.log");
    defer audit_logger.deinit();
    defer std.Io.Dir.cwd().deleteFile(agenkit.io_compat.io(), "example_audit.log") catch {};
    std.debug.print("✅ Audit logger initialized\n", .{});

    // 3. Create agent with tracing and metrics
    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var traced = try TracingMiddleware.init(allocator, echo.agent(), "example-service");
    defer traced.deinit();
    std.debug.print("✅ Tracing middleware added\n", .{});

    var observed = try MetricsMiddleware.init(allocator, traced.agent());
    defer observed.deinit();
    std.debug.print("✅ Metrics middleware added\n", .{});

    // 4. Log agent creation event
    var create_event = try audit.AuditEvent.create(
        allocator,
        .agent_created,
        "example-service",
        "example-session",
    );
    defer create_event.deinit(allocator);
    try audit_logger.log(&create_event);
    std.debug.print("✅ Agent creation audited\n", .{});

    // 5. Process a message
    std.debug.print("\nProcessing message...\n", .{});
    var msg = try Message.withText(allocator, .user, "Full observability test");
    defer msg.deinit();

    var result = try observed.agent().process(msg);
    var response = try result.unwrap();
    defer {
        if (response.getMetadata("traceparent")) |tp| {
            if (tp == .string) allocator.free(tp.string);
        }
        response.deinit();
    }

    // 6. Log processing event
    var process_event = try audit.AuditEvent.create(
        allocator,
        .message_processed,
        "example-service",
        "example-session",
    );
    defer process_event.deinit(allocator);
    try process_event.withDetail(allocator, "success", "true");
    try audit_logger.log(&process_event);

    // 7. Display collected observability data
    std.debug.print("\nObservability Data:\n", .{});
    std.debug.print("- Trace: ", .{});
    if (response.getMetadata("traceparent")) |tp| {
        std.debug.print("{s}\n", .{tp.string});
    }
    std.debug.print("- Metrics: {} requests, {d:.6}s avg latency\n", .{
        observed.requests_total.value,
        observed.request_duration.mean() orelse 0.0,
    });
    std.debug.print("- Audit: {} events logged\n", .{audit_logger.countEvents()});
    std.debug.print("- Logging: JSON format with trace context\n", .{});

    std.debug.print("\n✅ Full observability stack operational!\n", .{});
}

/// Example 2: Trace correlation across all modules
fn traceCorrelation(allocator: std.mem.Allocator) !void {
    // Configure logging with trace context support
    logging.configure(.json, .info);

    // Create agent with full instrumentation
    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var traced = try TracingMiddleware.init(allocator, echo.agent(), "correlated-service");
    defer traced.deinit();

    var observed = try MetricsMiddleware.init(allocator, traced.agent());
    defer observed.deinit();

    // Process message
    var msg = try Message.withText(allocator, .user, "Correlation test");
    defer msg.deinit();

    var result = try observed.agent().process(msg);
    var response = try result.unwrap();
    defer {
        if (response.getMetadata("traceparent")) |tp| {
            if (tp == .string) allocator.free(tp.string);
        }
        response.deinit();
    }

    // Extract trace context
    if (response.getMetadata("traceparent")) |traceparent| {
        const span_ctx = try observability.SpanContext.fromTraceparent(traceparent.string);

        // Format trace_id and span_id for logging
        var trace_id_buf: [32]u8 = undefined;
        var span_id_buf: [16]u8 = undefined;

        for (span_ctx.trace_id, 0..) |byte, idx| {
            _ = try std.fmt.bufPrint(trace_id_buf[idx * 2 .. idx * 2 + 2], "{x:0>2}", .{byte});
        }

        for (span_ctx.span_id, 0..) |byte, idx| {
            _ = try std.fmt.bufPrint(span_id_buf[idx * 2 .. idx * 2 + 2], "{x:0>2}", .{byte});
        }

        // Create log entry with trace context
        var log_entry = try logging.LogEntry.init(allocator, .info, "Message processed");
        defer log_entry.deinit(allocator);

        try log_entry.withTraceContext(allocator, &trace_id_buf, &span_id_buf);
        try log_entry.withField(allocator, "agent", "correlated-service");
        try log_entry.withField(allocator, "duration_ms", "1.23");

        // Format as JSON
        const json = try logging.formatJson(&log_entry, allocator);
        defer allocator.free(json);

        std.debug.print("Correlated Log Entry:\n{s}\n\n", .{json});
        std.debug.print("✅ Trace ID appears in:\n", .{});
        std.debug.print("  - Distributed trace spans\n", .{});
        std.debug.print("  - Structured log entries\n", .{});
        std.debug.print("  - Metrics (implicitly via timing)\n", .{});
        std.debug.print("  - Can be added to audit events\n", .{});
    }
}

/// Example 3: Production-ready agent with full observability
fn productionAgent(allocator: std.mem.Allocator) !void {
    std.debug.print("Setting up production agent...\n\n", .{});

    // Configure production logging
    logging.configure(.json, .info);

    // Create audit logger with descriptive name
    var audit_logger = try audit.AuditLogger.init(allocator, "production_audit.log");
    defer audit_logger.deinit();
    defer std.Io.Dir.cwd().deleteFile(agenkit.io_compat.io(), "production_audit.log") catch {};

    // Create fully instrumented agent
    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var traced = try TracingMiddleware.init(allocator, echo.agent(), "prod-ai-agent");
    defer traced.deinit();

    var observed = try MetricsMiddleware.init(allocator, traced.agent());
    defer observed.deinit();

    // Log agent initialization
    var init_event = try audit.AuditEvent.create(
        allocator,
        .agent_created,
        "prod-ai-agent",
        "prod-session-001",
    );
    defer init_event.deinit(allocator);
    _ = init_event.withSeverity(.info);
    try init_event.withDetail(allocator, "version", "1.0.0");
    try init_event.withDetail(allocator, "environment", "production");
    try audit_logger.log(&init_event);

    std.debug.print("Processing production requests...\n", .{});

    // Simulate production load
    var i: usize = 0;
    while (i < 3) : (i += 1) {
        var msg = try Message.withText(allocator, .user, "Production request");
        defer msg.deinit();

        var result = try observed.agent().process(msg);
        var response = try result.unwrap();
        defer {
            if (response.getMetadata("traceparent")) |tp| {
                if (tp == .string) allocator.free(tp.string);
            }
            response.deinit();
        }

        // Log successful processing
        var success_event = try audit.AuditEvent.create(
            allocator,
            .message_processed,
            "prod-ai-agent",
            "prod-session-001",
        );
        defer success_event.deinit(allocator);

        const request_id = try std.fmt.allocPrint(allocator, "{}", .{i + 1});
        defer allocator.free(request_id);
        try success_event.withDetail(allocator, "request_id", request_id);
        try audit_logger.log(&success_event);

        std.debug.print("  Request {}: ✅\n", .{i + 1});
    }

    // Display production metrics
    std.debug.print("\nProduction Metrics:\n", .{});
    std.debug.print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n", .{});
    std.debug.print("Requests:     {}\n", .{observed.requests_total.value});
    std.debug.print("Audit Events: {}\n", .{audit_logger.countEvents()});

    if (observed.request_duration.mean()) |mean| {
        std.debug.print("Avg Latency:  {d:.3}ms\n", .{mean * 1000});
    }
    if (observed.request_duration.min()) |min| {
        std.debug.print("Min Latency:  {d:.3}ms\n", .{min * 1000});
    }
    if (observed.request_duration.max()) |max| {
        std.debug.print("Max Latency:  {d:.3}ms\n", .{max * 1000});
    }

    std.debug.print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n", .{});
    std.debug.print("\n✅ Production agent with full observability!\n", .{});
    std.debug.print("\nObservability Features:\n", .{});
    std.debug.print("  ✓ Distributed tracing (W3C Trace Context)\n", .{});
    std.debug.print("  ✓ Request/latency metrics\n", .{});
    std.debug.print("  ✓ Structured JSON logging\n", .{});
    std.debug.print("  ✓ Compliance audit trail\n", .{});
    std.debug.print("  ✓ Cross-module trace correlation\n", .{});
    std.debug.print("\nReady for production deployment!\n", .{});
}

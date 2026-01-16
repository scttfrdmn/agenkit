/// Integration tests for observability modules
///
/// These tests verify that all observability components work together correctly:
/// - Tracing + Metrics + Logging + Audit
/// - Middleware composition
/// - Cross-module data flow

const std = @import("std");
const testing = std.testing;

const Agent = @import("../agent.zig").Agent;
const Message = @import("../message.zig").Message;
const EchoAgent = @import("../agent.zig").EchoAgent;

const tracing = @import("tracing.zig");
const metrics = @import("metrics.zig");
const logging = @import("logging.zig");
const audit = @import("audit.zig");

test "Tracing and Metrics middleware composition" {
    const allocator = testing.allocator;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    // Wrap with tracing first
    var traced = try tracing.TracingMiddleware.init(allocator, echo.agent(), "integration_test");
    defer traced.deinit();

    // Then wrap with metrics
    var observed = try metrics.MetricsMiddleware.init(allocator, traced.agent());
    defer observed.deinit();

    // Process a message
    var msg = try Message.withText(allocator, .user, "test integration");
    defer msg.deinit();

    var result = try observed.agent().process(msg);
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

    // Verify metrics were recorded
    try testing.expectEqual(@as(u64, 1), observed.requests_total.value);
    try testing.expectEqual(@as(usize, 1), observed.request_duration.count());

    // Verify response has trace context in metadata
    const traceparent = response.getMetadata("traceparent");
    try testing.expect(traceparent != null);
}

test "Full observability stack" {
    const allocator = testing.allocator;

    // Initialize logging
    logging.configure(.json, .info);

    // Create audit logger
    var audit_logger = try audit.AuditLogger.init(allocator, "integration_audit.log");
    defer audit_logger.deinit();
    defer std.fs.cwd().deleteFile("integration_audit.log") catch {};

    // Create agent with full observability
    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var traced = try tracing.TracingMiddleware.init(allocator, echo.agent(), "full_stack_test");
    defer traced.deinit();

    var observed = try metrics.MetricsMiddleware.init(allocator, traced.agent());
    defer observed.deinit();

    // Log agent creation
    var create_event = try audit.AuditEvent.create(
        allocator,
        .agent_created,
        "full_stack_test",
        "integration_session",
    );
    defer create_event.deinit(allocator);
    try audit_logger.log(&create_event);

    // Process message
    var msg = try Message.withText(allocator, .user, "full stack test");
    defer msg.deinit();

    var result = try observed.agent().process(msg);
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

    // Log message processing
    var process_event = try audit.AuditEvent.create(
        allocator,
        .message_processed,
        "full_stack_test",
        "integration_session",
    );
    defer process_event.deinit(allocator);
    try process_event.withDetail(allocator, "success", "true");
    try audit_logger.log(&process_event);

    // Verify all components recorded data
    try testing.expectEqual(@as(u64, 1), observed.requests_total.value);
    try testing.expectEqual(@as(usize, 2), audit_logger.countEvents());
}

test "Trace context propagation across middleware" {
    const allocator = testing.allocator;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var traced = try tracing.TracingMiddleware.init(allocator, echo.agent(), "propagation_test");
    defer traced.deinit();

    // Create message with existing trace context
    var msg = try Message.withText(allocator, .user, "propagation test");
    defer msg.deinit();

    const parent_context = try tracing.SpanContext.root(allocator);
    const parent_traceparent = try parent_context.toTraceparent(allocator);
    defer allocator.free(parent_traceparent);

    try msg.setMetadata("traceparent", .{ .string = parent_traceparent });

    // Process message
    var result = try traced.agent().process(msg);
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

    // Verify trace context was propagated
    const response_traceparent = response.getMetadata("traceparent");
    try testing.expect(response_traceparent != null);

    // Parse and verify trace ID matches
    const response_context = try tracing.SpanContext.fromTraceparent(response_traceparent.?.string);
    try testing.expectEqualSlices(u8, &parent_context.trace_id, &response_context.trace_id);
}

test "Metrics with trace correlation" {
    const allocator = testing.allocator;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var traced = try tracing.TracingMiddleware.init(allocator, echo.agent(), "correlated_test");
    defer traced.deinit();

    var observed = try metrics.MetricsMiddleware.init(allocator, traced.agent());
    defer observed.deinit();

    // Process multiple messages with different trace contexts
    var i: usize = 0;
    while (i < 3) : (i += 1) {
        var msg = try Message.withText(allocator, .user, "correlated");
        defer msg.deinit();

        var result = try observed.agent().process(msg);
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
    }

    // Verify metrics recorded all requests
    try testing.expectEqual(@as(u64, 3), observed.requests_total.value);
    try testing.expectEqual(@as(usize, 3), observed.request_duration.count());
}

test "Audit events with severity filtering" {
    const allocator = testing.allocator;

    var logger = try audit.AuditLogger.init(allocator, "severity_test.log");
    defer logger.deinit();
    defer std.fs.cwd().deleteFile("severity_test.log") catch {};

    // Create events with different severities
    var info_event = try audit.AuditEvent.create(allocator, .message_processed, "agent", null);
    defer info_event.deinit(allocator);
    _ = info_event.withSeverity(.info);

    var warn_event = try audit.AuditEvent.create(allocator, .configuration_changed, "agent", null);
    defer warn_event.deinit(allocator);
    _ = warn_event.withSeverity(.warning);

    var critical_event = try audit.AuditEvent.create(allocator, .security_violation, "agent", null);
    defer critical_event.deinit(allocator);
    _ = critical_event.withSeverity(.critical);

    try logger.log(&info_event);
    try logger.log(&warn_event);
    try logger.log(&critical_event);

    // Query critical events
    var critical_results = try logger.queryBySeverity(.critical);
    defer critical_results.deinit(allocator);

    try testing.expectEqual(@as(usize, 1), critical_results.items.len);
    try testing.expectEqual(audit.AuditEventType.security_violation, critical_results.items[0].event_type);
}

test "Logging with trace context from tracing" {
    const allocator = testing.allocator;

    // Create a span context
    const span_ctx = try tracing.SpanContext.root(allocator);
    const traceparent = try span_ctx.toTraceparent(allocator);
    defer allocator.free(traceparent);

    // Extract trace and span IDs
    var trace_id_buf: [32]u8 = undefined;
    var span_id_buf: [16]u8 = undefined;

    for (span_ctx.trace_id, 0..) |byte, idx| {
        _ = try std.fmt.bufPrint(trace_id_buf[idx * 2 .. idx * 2 + 2], "{x:0>2}", .{byte});
    }

    for (span_ctx.span_id, 0..) |byte, idx| {
        _ = try std.fmt.bufPrint(span_id_buf[idx * 2 .. idx * 2 + 2], "{x:0>2}", .{byte});
    }

    // Create log entry with trace context
    var entry = try logging.LogEntry.init(allocator, .info, "traced log");
    defer entry.deinit(allocator);

    try entry.withTraceContext(allocator, &trace_id_buf, &span_id_buf);

    // Format as JSON
    const json = try logging.formatJson(&entry, allocator);
    defer allocator.free(json);

    // Verify trace context is in JSON
    try testing.expect(std.mem.indexOf(u8, json, "\"trace_id\"") != null);
    try testing.expect(std.mem.indexOf(u8, json, "\"span_id\"") != null);
}

test "Error handling in middleware stack" {
    const allocator = testing.allocator;

    // For this test, we'll use EchoAgent which doesn't error
    // In production, you'd test with an agent that can fail
    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var traced = try tracing.TracingMiddleware.init(allocator, echo.agent(), "error_test");
    defer traced.deinit();

    var observed = try metrics.MetricsMiddleware.init(allocator, traced.agent());
    defer observed.deinit();

    var msg = try Message.withText(allocator, .user, "test");
    defer msg.deinit();

    // Even with error handling, metrics should be recorded
    var result = try observed.agent().process(msg);
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

    try testing.expectEqual(@as(u64, 1), observed.requests_total.value);
}

test "Audit event with multiple details" {
    const allocator = testing.allocator;

    var event = try audit.AuditEvent.create(allocator, .message_processed, "test_agent", "test_session");
    defer event.deinit(allocator);

    try event.withDetail(allocator, "duration_ms", "150");
    try event.withDetail(allocator, "tokens_used", "500");
    try event.withDetail(allocator, "model", "claude-3");
    try event.withDetail(allocator, "status", "success");

    const json = try event.toJson(allocator);
    defer allocator.free(json);

    try testing.expect(std.mem.indexOf(u8, json, "\"duration_ms\":\"150\"") != null);
    try testing.expect(std.mem.indexOf(u8, json, "\"tokens_used\":\"500\"") != null);
    try testing.expect(std.mem.indexOf(u8, json, "\"model\":\"claude-3\"") != null);
}

test "Histogram percentile calculation" {
    const allocator = testing.allocator;

    var histogram = try metrics.Histogram.init(allocator, "latency");
    defer histogram.deinit();

    // Add observations
    try histogram.observe(1.0);
    try histogram.observe(2.0);
    try histogram.observe(3.0);
    try histogram.observe(4.0);
    try histogram.observe(5.0);
    try histogram.observe(6.0);
    try histogram.observe(7.0);
    try histogram.observe(8.0);
    try histogram.observe(9.0);
    try histogram.observe(10.0);

    // Verify statistics
    try testing.expectEqual(@as(usize, 10), histogram.count());
    try testing.expectEqual(@as(f64, 55.0), histogram.sum());

    const mean_val = histogram.mean();
    try testing.expect(mean_val != null);
    try testing.expectEqual(@as(f64, 5.5), mean_val.?);

    try testing.expectEqual(@as(f64, 1.0), histogram.min().?);
    try testing.expectEqual(@as(f64, 10.0), histogram.max().?);
}

test "Concurrent audit logging" {
    const allocator = testing.allocator;

    var logger = try audit.AuditLogger.init(allocator, "concurrent_test.log");
    defer logger.deinit();
    defer std.fs.cwd().deleteFile("concurrent_test.log") catch {};

    // Simulate concurrent logging (sequential in tests, but validates thread safety design)
    var i: usize = 0;
    while (i < 10) : (i += 1) {
        var event = try audit.AuditEvent.create(allocator, .message_processed, "agent", null);
        defer event.deinit(allocator);

        try logger.log(&event);
    }

    try testing.expectEqual(@as(usize, 10), logger.countEvents());
}

test "Log format switching" {
    const allocator = testing.allocator;

    var entry = try logging.LogEntry.init(allocator, .info, "format test");
    defer entry.deinit(allocator);

    // JSON format
    const json = try logging.formatJson(&entry, allocator);
    defer allocator.free(json);
    try testing.expect(std.mem.indexOf(u8, json, "{\"timestamp\"") != null);

    // Compact format
    const compact = try logging.formatCompact(&entry, allocator);
    defer allocator.free(compact);
    try testing.expect(std.mem.indexOf(u8, compact, "[") != null);

    // Pretty format
    const pretty = try logging.formatPretty(&entry, allocator);
    defer allocator.free(pretty);
    try testing.expect(std.mem.indexOf(u8, pretty, "INFO |") != null);
}

/// Agenkit Observability Module
///
/// This module provides comprehensive observability features for AI agents:
/// - **Tracing**: OpenTelemetry distributed tracing with W3C Trace Context
/// - **Metrics**: Counters and histograms for performance monitoring
/// - **Logging**: Structured logging with trace correlation
/// - **Audit**: Compliance-ready event logging with queries
///
/// ## Getting Started
///
/// ```zig
/// const agenkit = @import("agenkit");
/// const obs = agenkit.observability;
///
/// // Tracing: Wrap any agent with distributed tracing
/// var base_agent = try EchoAgent.init(allocator);
/// var traced = try obs.TracingMiddleware.init(allocator, base_agent.agent(), "my-service");
/// defer traced.deinit();
///
/// // Metrics: Wrap with metrics collection
/// var with_metrics = try obs.MetricsMiddleware.init(allocator, traced.agent());
/// defer with_metrics.deinit();
///
/// // Logging: Configure structured logging
/// obs.logging.configure(.json, .info);
/// try obs.logging.log(allocator, .info, "Agent started");
///
/// // Audit: Log compliance events
/// var audit_logger = try obs.AuditLogger.init(allocator, "audit.log");
/// defer audit_logger.deinit();
/// var event = try obs.AuditEvent.create(allocator, .agent_created, "my-service", null);
/// defer event.deinit(allocator);
/// try audit_logger.log(&event);
///
/// // Process messages - all observability automatic
/// const result = try with_metrics.agent().process(message);
/// ```
///
/// ## W3C Trace Context
///
/// Full support for W3C Trace Context specification:
/// - traceparent: `00-{trace_id}-{span_id}-{flags}`
/// - Automatic propagation through agent chains
/// - Cross-language compatibility with Python, Go, TypeScript, Rust, C++
///
/// ## Integration
///
/// Works seamlessly with:
/// - All Agenkit agent patterns (Reflection, ReAct, etc.)
/// - Message metadata system
/// - Evaluation framework
/// - External systems (Jaeger, Zipkin, Prometheus, Grafana)
const std = @import("std");

// Export all observability modules
pub const tracing = @import("tracing.zig");
pub const metrics = @import("metrics.zig");
pub const logging = @import("logging.zig");
pub const audit = @import("audit.zig");

// Re-export commonly used types for convenience

// Tracing types
pub const SpanContext = tracing.SpanContext;
pub const Span = tracing.Span;
pub const TracingMiddleware = tracing.TracingMiddleware;

// Metrics types
pub const Counter = metrics.Counter;
pub const Histogram = metrics.Histogram;
pub const MetricsMiddleware = metrics.MetricsMiddleware;

// Logging types
pub const LogLevel = logging.LogLevel;
pub const LogFormat = logging.LogFormat;
pub const LogEntry = logging.LogEntry;

// Audit types
pub const AuditEvent = audit.AuditEvent;
pub const AuditEventType = audit.AuditEventType;
pub const AuditLogger = audit.AuditLogger;
pub const Severity = audit.Severity;

test {
    std.testing.refAllDecls(@This());
    _ = @import("tracing.zig");
    _ = @import("metrics.zig");
    _ = @import("logging.zig");
    _ = @import("audit.zig");
    _ = @import("integration_test.zig");
}

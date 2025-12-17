/// Agenkit Observability Module
///
/// This module provides observability features for AI agents:
/// - OpenTelemetry distributed tracing
/// - W3C Trace Context propagation
/// - Span creation and management
/// - TracingMiddleware for agent instrumentation
///
/// ## Getting Started
///
/// ```zig
/// const agenkit = @import("agenkit");
/// const TracingMiddleware = agenkit.observability.TracingMiddleware;
///
/// // Wrap any agent with tracing
/// var base_agent = try EchoAgent.init(allocator);
/// var traced = try TracingMiddleware.init(allocator, base_agent.agent(), "my-service");
/// defer traced.deinit();
///
/// // Process messages - trace context automatically propagated
/// const result = try traced.agent().process(message);
/// ```
///
/// ## W3C Trace Context
///
/// The module fully supports W3C Trace Context specification:
/// - traceparent: `00-{trace_id}-{span_id}-{flags}`
/// - Automatic propagation through agent chains
/// - Cross-language compatibility
///
/// ## Integration
///
/// Works seamlessly with:
/// - All Agenkit agent patterns
/// - Message metadata system
/// - Evaluation framework
/// - External tracing systems (Jaeger, Zipkin, etc.)

const std = @import("std");

// Export tracing types
pub const tracing = @import("tracing.zig");
pub const SpanContext = tracing.SpanContext;
pub const Span = tracing.Span;
pub const TracingMiddleware = tracing.TracingMiddleware;

test {
    std.testing.refAllDecls(@This());
    _ = @import("tracing.zig");
}

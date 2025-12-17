"use strict";
/**
 * OpenTelemetry distributed tracing for Agenkit agents.
 *
 * Provides automatic span creation, W3C Trace Context propagation,
 * and middleware for instrumenting agent processing.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.TracingMiddleware = void 0;
exports.initTracing = initTracing;
exports.shutdownTracing = shutdownTracing;
exports.getTracer = getTracer;
exports.injectTraceContext = injectTraceContext;
exports.extractTraceContext = extractTraceContext;
exports.createTracedAgent = createTracedAgent;
const api_1 = require("@opentelemetry/api");
const sdk_trace_node_1 = require("@opentelemetry/sdk-trace-node");
const resources_1 = require("@opentelemetry/resources");
const semantic_conventions_1 = require("@opentelemetry/semantic-conventions");
const sdk_trace_base_1 = require("@opentelemetry/sdk-trace-base");
const exporter_trace_otlp_http_1 = require("@opentelemetry/exporter-trace-otlp-http");
const base_1 = require("../middleware/base");
let tracerProvider = null;
let tracer = null;
/**
 * Initialize OpenTelemetry tracing.
 *
 * Must be called once at application startup before creating traced agents.
 *
 * @param config - Tracing configuration
 * @returns TracerProvider instance
 *
 * @example
 * ```typescript
 * import { initTracing } from '@agenkit/core/observability';
 *
 * // Development: console export
 * initTracing({
 *   serviceName: 'my-agent-service',
 *   consoleExport: true
 * });
 *
 * // Production: OTLP export to Jaeger/Tempo
 * initTracing({
 *   serviceName: 'my-agent-service',
 *   otlpEndpoint: 'http://localhost:4318/v1/traces'
 * });
 * ```
 */
function initTracing(config) {
    // Create resource with service name
    const resource = resources_1.Resource.default().merge(new resources_1.Resource({
        [semantic_conventions_1.ATTR_SERVICE_NAME]: config.serviceName,
    }));
    // Create tracer provider
    tracerProvider = new sdk_trace_node_1.NodeTracerProvider({
        resource,
    });
    // Add exporters
    if (config.consoleExport) {
        tracerProvider.addSpanProcessor(new sdk_trace_base_1.SimpleSpanProcessor(new sdk_trace_base_1.ConsoleSpanExporter()));
    }
    if (config.otlpEndpoint) {
        const otlpExporter = new exporter_trace_otlp_http_1.OTLPTraceExporter({
            url: config.otlpEndpoint,
        });
        tracerProvider.addSpanProcessor(new sdk_trace_base_1.BatchSpanProcessor(otlpExporter));
    }
    // Register as global provider
    tracerProvider.register();
    // Get tracer
    tracer = api_1.trace.getTracer('@agenkit/core', '0.2.0');
    return tracerProvider;
}
/**
 * Shutdown tracing and flush pending spans.
 *
 * Should be called on application shutdown.
 *
 * @example
 * ```typescript
 * process.on('SIGTERM', async () => {
 *   await shutdownTracing();
 *   process.exit(0);
 * });
 * ```
 */
async function shutdownTracing() {
    if (tracerProvider) {
        await tracerProvider.shutdown();
        tracerProvider = null;
        tracer = null;
    }
}
/**
 * Get the current tracer instance.
 *
 * @returns Tracer instance or null if not initialized
 */
function getTracer() {
    return tracer;
}
/**
 * Inject trace context into message metadata.
 *
 * Extracts current span context and creates W3C Trace Context headers.
 *
 * @param metadata - Message metadata to inject into
 * @returns Metadata with trace context
 *
 * @example
 * ```typescript
 * const message: Message = {
 *   role: 'user',
 *   content: 'Hello',
 *   metadata: injectTraceContext({})
 * };
 * ```
 */
function injectTraceContext(metadata = {}) {
    const span = api_1.trace.getActiveSpan();
    if (!span) {
        return metadata;
    }
    const spanContext = span.spanContext();
    if (!spanContext) {
        return metadata;
    }
    // Create W3C Trace Context traceparent header
    // Format: version-trace_id-span_id-flags
    const traceparent = `00-${spanContext.traceId}-${spanContext.spanId}-${spanContext.traceFlags.toString(16).padStart(2, '0')}`;
    return {
        ...metadata,
        trace_context: {
            traceparent,
            ...(spanContext.traceState && { tracestate: spanContext.traceState.serialize() }),
        },
    };
}
/**
 * Extract trace context from message metadata.
 *
 * Parses W3C Trace Context headers. For now, returns active context.
 * Full W3C Trace Context propagation would require setting up a propagator.
 *
 * @param metadata - Message metadata
 * @returns Active context
 */
function extractTraceContext(_metadata) {
    // Note: Full W3C Trace Context propagation would require setting up
    // a propagator. For now, we just return the active context.
    return api_1.context.active();
}
/**
 * Middleware that adds distributed tracing to agent processing.
 *
 * Creates spans for each agent.process() call with automatic:
 * - Span creation and timing
 * - Trace context propagation
 * - Error recording
 * - Span attributes (agent name, message role, content length)
 *
 * @example
 * ```typescript
 * import { TracingMiddleware } from '@agenkit/core/observability';
 *
 * const agent = new MyAgent();
 * const tracedAgent = new TracingMiddleware(agent);
 *
 * // Or with custom span name
 * const tracedAgent = new TracingMiddleware(agent, 'custom.operation');
 *
 * // Process messages - tracing happens automatically
 * const response = await tracedAgent.process(message);
 * ```
 */
class TracingMiddleware extends base_1.BaseMiddleware {
    /**
     * Create a new tracing middleware.
     *
     * @param agent - Agent to wrap
     * @param spanName - Custom span name (optional, defaults to "agent.{name}.process")
     */
    constructor(agent, spanName) {
        super(agent);
        this.spanName = spanName || `agent.${agent.name}.process`;
    }
    /**
     * Process a message with distributed tracing.
     *
     * @param message - Input message
     * @returns Output message with trace context
     */
    async process(message) {
        const currentTracer = getTracer();
        if (!currentTracer) {
            // Tracing not initialized, pass through
            return this.agent.process(message);
        }
        // Extract parent trace context from message metadata
        const parentContext = extractTraceContext(message.metadata);
        // Start a new span
        return api_1.context.with(parentContext, async () => {
            const contentLength = typeof message.content === 'string' ? message.content.length : 0;
            const metadataKeys = message.metadata ? Object.keys(message.metadata).join(',') : '';
            const agentCapabilities = this.agent.capabilities || [];
            const span = currentTracer.startSpan(this.spanName, {
                attributes: {
                    'agent.name': this.agent.name,
                    'agent.capabilities': agentCapabilities.join(','),
                    'message.role': message.role,
                    'message.content_length': contentLength,
                    ...(metadataKeys && { 'message.metadata_keys': metadataKeys }),
                },
            });
            try {
                // Process message in span context
                const response = await api_1.context.with(api_1.trace.setSpan(parentContext, span), async () => {
                    return this.agent.process(message);
                });
                // Inject trace context into response
                const responseWithTrace = {
                    ...response,
                    metadata: injectTraceContext(response.metadata || {}),
                };
                // Mark span as successful
                span.setStatus({ code: api_1.SpanStatusCode.OK });
                return responseWithTrace;
            }
            catch (error) {
                // Record error in span
                span.recordException(error);
                span.setStatus({
                    code: api_1.SpanStatusCode.ERROR,
                    message: error instanceof Error ? error.message : String(error),
                });
                throw error;
            }
            finally {
                // Always end the span
                span.end();
            }
        });
    }
}
exports.TracingMiddleware = TracingMiddleware;
/**
 * Create a traced agent by wrapping with TracingMiddleware.
 *
 * Convenience function for wrapping agents with tracing.
 *
 * @param agent - Agent to wrap
 * @param spanName - Custom span name (optional)
 * @returns Traced agent
 *
 * @example
 * ```typescript
 * import { createTracedAgent } from '@agenkit/core/observability';
 *
 * const agent = new MyAgent();
 * const tracedAgent = createTracedAgent(agent);
 * ```
 */
function createTracedAgent(agent, spanName) {
    return new TracingMiddleware(agent, spanName);
}

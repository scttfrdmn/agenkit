/**
 * OpenTelemetry distributed tracing for Agenkit agents.
 *
 * Provides automatic span creation, W3C Trace Context propagation,
 * and middleware for instrumenting agent processing.
 */

import { trace, context, Span, SpanStatusCode, Tracer } from '@opentelemetry/api';
import { NodeTracerProvider } from '@opentelemetry/sdk-trace-node';
import { defaultResource, resourceFromAttributes } from '@opentelemetry/resources';
import { ATTR_SERVICE_NAME } from '@opentelemetry/semantic-conventions';
import {
  ConsoleSpanExporter,
  SimpleSpanProcessor as BaseSimpleSpanProcessor,
  BatchSpanProcessor as BaseBatchSpanProcessor,
  type SpanProcessor,
} from '@opentelemetry/sdk-trace-base';
import { TraceIdRatioBasedSampler, ParentBasedSampler } from '@opentelemetry/sdk-trace-base';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { Agent, Message } from '../core/interfaces';
import { BaseMiddleware } from '../middleware/base';

/**
 * Configuration for tracing initialization.
 */
export interface TracingConfig {
  /** Service name for traces */
  serviceName: string;
  /** OTLP endpoint URL (optional) */
  otlpEndpoint?: string;
  /** Enable console export for development (default: false) */
  consoleExport?: boolean;
  /** Sampling rate (0.0 to 1.0). Default 1.0 (100%). For production, use lower rates (e.g., 0.01 = 1%) */
  sampleRate?: number;
}

/**
 * Trace context metadata format for W3C Trace Context propagation.
 */
export interface TraceContext {
  traceparent: string;
  tracestate?: string;
}

let tracerProvider: NodeTracerProvider | null = null;
let tracer: Tracer | null = null;

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
 * // Development: console export, 100% sampling
 * initTracing({
 *   serviceName: 'my-agent-service',
 *   consoleExport: true
 * });
 *
 * // Production: OTLP export to Jaeger/Tempo, 1% sampling
 * initTracing({
 *   serviceName: 'my-agent-service',
 *   otlpEndpoint: 'http://localhost:4318/v1/traces',
 *   sampleRate: 0.01
 * });
 * ```
 */
export function initTracing(config: TracingConfig): NodeTracerProvider {
  // Create resource with service name
  const resource = defaultResource().merge(
    resourceFromAttributes({
      [ATTR_SERVICE_NAME]: config.serviceName,
    })
  );

  // Configure sampling
  // ParentBased: if parent span is sampled, always sample child spans
  // Otherwise, use TraceIdRatioBasedSampler for root spans
  const sampleRate = config.sampleRate ?? 1.0;
  const sampler = new ParentBasedSampler({
    root: new TraceIdRatioBasedSampler(sampleRate),
  });

  // Build span processors up-front: modern otel-js takes them via the
  // constructor (`addSpanProcessor` was removed).
  const spanProcessors: SpanProcessor[] = [];
  if (config.consoleExport) {
    spanProcessors.push(new BaseSimpleSpanProcessor(new ConsoleSpanExporter()));
  }
  if (config.otlpEndpoint) {
    const otlpExporter = new OTLPTraceExporter({
      url: config.otlpEndpoint,
    });
    spanProcessors.push(new BaseBatchSpanProcessor(otlpExporter));
  }

  // Create tracer provider with sampler + processors
  tracerProvider = new NodeTracerProvider({
    resource,
    sampler,
    spanProcessors,
  });

  // Register as global provider
  tracerProvider.register();

  // Get tracer
  tracer = trace.getTracer('@agenkit/core', '0.2.0');

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
export async function shutdownTracing(): Promise<void> {
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
export function getTracer(): Tracer | null {
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
export function injectTraceContext(metadata: Record<string, any> = {}): Record<string, any> {
  const span = trace.getActiveSpan();
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
export function extractTraceContext(_metadata?: Record<string, any>): ReturnType<typeof context.active> {
  // Note: Full W3C Trace Context propagation would require setting up
  // a propagator. For now, we just return the active context.
  return context.active();
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
export class TracingMiddleware extends BaseMiddleware {
  private readonly spanName: string;

  /**
   * Create a new tracing middleware.
   *
   * @param agent - Agent to wrap
   * @param spanName - Custom span name (optional, defaults to "agent.{name}.process")
   */
  constructor(agent: Agent, spanName?: string) {
    super(agent);
    this.spanName = spanName || `agent.${agent.name}.process`;
  }

  /**
   * Process a message with distributed tracing.
   *
   * @param message - Input message
   * @returns Output message with trace context
   */
  async process(message: Message): Promise<Message> {
    const currentTracer = getTracer();
    if (!currentTracer) {
      // Tracing not initialized, pass through
      return this.agent.process(message);
    }

    // Extract parent trace context from message metadata
    const parentContext = extractTraceContext(message.metadata);

    // Start a new span
    return context.with(parentContext, async () => {
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
        // Process message in span context and inject trace context
        const response = await context.with(trace.setSpan(parentContext, span), async () => {
          const result = await this.agent.process(message);
          // Inject trace context while span is active
          return {
            ...result,
            metadata: injectTraceContext(result.metadata || {}),
          };
        });

        // Mark span as successful
        span.setStatus({ code: SpanStatusCode.OK });

        return response;
      } catch (error) {
        // Record error in span
        span.recordException(error as Error);
        span.setStatus({
          code: SpanStatusCode.ERROR,
          message: error instanceof Error ? error.message : String(error),
        });

        throw error;
      } finally {
        // Always end the span
        span.end();
      }
    });
  }
}

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
export function createTracedAgent(agent: Agent, spanName?: string): Agent {
  return new TracingMiddleware(agent, spanName);
}

/**
 * Tests for initTracing's global registration.
 *
 * otel-js 3.0 removed NodeTracerProvider.register(), so initTracing now wires
 * up the context manager and propagator itself. These pin the two behaviours
 * register() used to provide by default; neither was covered before.
 */

import { context, propagation, trace } from '@opentelemetry/api';
import { initTracing, injectTraceContext, shutdownTracing } from '../observability/tracing';

describe('initTracing global registration', () => {
  beforeAll(() => {
    initTracing({ serviceName: 'tracing-init-test', sampleRate: 1.0 });
  });

  afterAll(async () => {
    await shutdownTracing();
    trace.disable();
    context.disable();
    propagation.disable();
  });

  it('keeps the parent span active across an await (context manager)', async () => {
    const tracer = trace.getTracer('tracing-init-test');

    await tracer.startActiveSpan('parent', async (parent) => {
      await new Promise((resolve) => setTimeout(resolve, 1));

      const active = trace.getActiveSpan();
      expect(active?.spanContext().spanId).toBe(parent.spanContext().spanId);

      const metadata = injectTraceContext();
      expect(metadata.trace_context.traceparent).toBe(
        `00-${parent.spanContext().traceId}-${parent.spanContext().spanId}-01`
      );
      parent.end();
    });
  });

  it('injects a W3C traceparent header (global propagator)', () => {
    const tracer = trace.getTracer('tracing-init-test');
    const span = tracer.startSpan('outbound');
    const carrier: Record<string, string> = {};

    propagation.inject(trace.setSpan(context.active(), span), carrier);

    expect(carrier.traceparent).toBe(
      `00-${span.spanContext().traceId}-${span.spanContext().spanId}-01`
    );
    span.end();
  });
});

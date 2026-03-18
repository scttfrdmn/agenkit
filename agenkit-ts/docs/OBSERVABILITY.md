# Observability Guide — Agenkit TypeScript

This guide covers distributed tracing, metrics, structured logging, and audit trails for production Agenkit TypeScript deployments.

## Table of Contents

- [Overview](#overview)
- [OpenTelemetry Setup](#opentelemetry-setup)
- [TracingAgent](#tracingagent)
- [Metrics Collection](#metrics-collection)
- [Structured Logging](#structured-logging)
- [Audit Middleware](#audit-middleware)
- [Distributed Tracing with Async Context](#distributed-tracing-with-async-context)
- [Exporting to Backends](#exporting-to-backends)
- [Production Patterns](#production-patterns)
- [Quick Reference](#quick-reference)

---

## Overview

Agenkit TypeScript provides three observability layers that can be used independently or together:

| Layer | What It Measures | Primary Use |
|-------|-----------------|-------------|
| **Tracing** | Request flow across services | Debugging, latency analysis |
| **Metrics** | Aggregated statistics | Dashboards, alerts |
| **Logging** | Discrete events with context | Debugging, audit trails |

All three integrate with the OpenTelemetry standard, enabling export to Jaeger, Zipkin, Prometheus, Grafana, Datadog, and more.

---

## OpenTelemetry Setup

### Install Dependencies

```bash
npm install \
  @opentelemetry/sdk-node \
  @opentelemetry/api \
  @opentelemetry/auto-instrumentations-node \
  @opentelemetry/exporter-jaeger \
  @opentelemetry/exporter-prometheus \
  @opentelemetry/sdk-metrics
```

### Basic Configuration

Create `src/telemetry.ts` and import it **before** any other module:

```typescript
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { JaegerExporter } from '@opentelemetry/exporter-jaeger';
import { PrometheusExporter } from '@opentelemetry/exporter-prometheus';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';

const sdk = new NodeSDK({
  resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: 'my-agent-service',
    [SemanticResourceAttributes.SERVICE_VERSION]: '1.0.0',
    [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: process.env.NODE_ENV ?? 'development',
  }),
  traceExporter: new JaegerExporter({
    endpoint: process.env.JAEGER_ENDPOINT ?? 'http://localhost:14268/api/traces',
  }),
  metricReader: new PrometheusExporter({
    port: 9464, // Prometheus scrapes /metrics on this port
  }),
  instrumentations: [
    getNodeAutoInstrumentations({
      '@opentelemetry/instrumentation-http': { enabled: true },
      '@opentelemetry/instrumentation-grpc': { enabled: true },
    }),
  ],
});

sdk.start();

process.on('SIGTERM', () => {
  sdk.shutdown().then(() => process.exit(0));
});
```

### Minimal Configuration (Development)

For development without backend infrastructure:

```typescript
import { configureObservability } from '@agenkit/core/observability';

configureObservability({
  serviceName: 'my-agent-dev',
  exporterType: 'console', // prints spans to stdout
});
```

---

## TracingAgent

`TracingAgent` wraps any agent and automatically creates OpenTelemetry spans for every `process()` call.

### Basic Usage

```typescript
import { TracingAgent, LocalAgent, createMessage } from '@agenkit/core';
import { trace } from '@opentelemetry/api';

// Create a tracer for your service
const tracer = trace.getTracer('my-agent-service', '1.0.0');

// Wrap any agent with tracing
const base = new LocalAgent({
  name: 'worker',
  process: async (msg) => ({
    role: 'assistant',
    content: `Processed: ${msg.content}`,
  }),
});

const traced = new TracingAgent(base, {
  tracer,
  serviceName: 'my-agent-service',
  additionalAttributes: {
    'agent.version': '1.0.0',
    environment: 'production',
  },
});

// Every process() call creates a span automatically
const response = await traced.process(createMessage('user', 'Hello'));
// Span: { name: 'agent.process', attributes: { agent.name: 'worker', ... } }
```

### What Gets Traced

Each span includes:
- `agent.name` — the wrapped agent's name
- `message.role` — input message role
- `message.content_length` — input content length in bytes
- `response.role` — output message role
- `response.content_length` — output content length
- `duration_ms` — processing latency
- `error` — set to `true` if an exception was thrown
- `error.message` — exception message
- Any `additionalAttributes` you configure

### Tracing Middleware Stack

```typescript
import {
  TracingAgent,
  RetryMiddleware,
  TimeoutMiddleware,
  CachingMiddleware,
} from '@agenkit/core';

// Build middleware stack, with tracing as the outermost layer
let agent: Agent = llmAgent;
agent = new RetryMiddleware(agent, { maxRetries: 3, initialDelayMs: 1000 });
agent = new TimeoutMiddleware(agent, { timeoutMs: 30000 });
agent = new CachingMiddleware(agent, { ttlMs: 60000, maxSize: 100 });

// Tracing is outermost — captures all middleware latency
agent = new TracingAgent(agent, { tracer, serviceName: 'llm-service' });

const response = await agent.process(message);
```

### Custom Span Attributes

```typescript
import { TracingAgent, createMessage } from '@agenkit/core';
import { trace, context } from '@opentelemetry/api';

const tracer = trace.getTracer('agent-service');

// Manually add attributes to the current span from within agent code
class InstrumentedAgent implements Agent {
  readonly name = 'instrumented';

  async process(message: Message): Promise<Message> {
    const span = trace.getActiveSpan();
    span?.setAttribute('session.id', message.metadata?.session_id as string ?? '');
    span?.setAttribute('user.id', message.metadata?.user_id as string ?? '');

    const start = Date.now();
    const response = await this.doWork(message);

    span?.setAttribute('work.duration_ms', Date.now() - start);
    return response;
  }

  private async doWork(message: Message): Promise<Message> {
    return { role: 'assistant', content: `Done: ${message.content}` };
  }
}
```

---

## Metrics Collection

### MetricsCollector

`MetricsCollector` tracks request counts, latencies, and error rates per agent.

```typescript
import { MetricsCollector } from '@agenkit/core/observability';

const collector = new MetricsCollector({
  buckets: [5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000],
});

async function processWithMetrics(
  agent: Agent,
  message: Message
): Promise<Message> {
  const start = Date.now();
  let success = false;

  try {
    const response = await agent.process(message);
    success = true;
    return response;
  } finally {
    collector.record(agent.name, Date.now() - start, success);
  }
}

// Get a snapshot of all metrics
const snapshot = collector.getSnapshot();
console.log(JSON.stringify(snapshot, null, 2));

// Export as Prometheus text format
const prometheusText = collector.getPrometheusText();
// Serve this at /metrics for Prometheus to scrape
```

### MetricsMiddleware

Use `MetricsMiddleware` to automatically collect metrics without changing calling code:

```typescript
import { MetricsMiddleware } from '@agenkit/core/middleware';

const agent = new MetricsMiddleware(baseAgent, {
  histogramBuckets: [10, 50, 100, 500, 1000, 5000],
});

// Process messages normally
const response = await agent.process(message);

// Retrieve metrics at any time
const metrics = agent.getMetrics();
console.log(`
  Total requests:    ${metrics.totalRequests}
  Successful:        ${metrics.successfulRequests}
  Failed:            ${metrics.failedRequests}
  Average latency:   ${metrics.averageLatencyMs.toFixed(2)}ms
  P95 latency:       ${metrics.p95LatencyMs.toFixed(2)}ms
  P99 latency:       ${metrics.p99LatencyMs.toFixed(2)}ms
`);
```

### OpenTelemetry Metrics

For production metrics with Prometheus/Grafana:

```typescript
import { metrics } from '@opentelemetry/api';

const meter = metrics.getMeter('agent-service', '1.0.0');

// Create instruments
const requestCounter = meter.createCounter('agent.requests.total', {
  description: 'Total number of agent requests',
});

const latencyHistogram = meter.createHistogram('agent.request.duration_ms', {
  description: 'Agent request latency in milliseconds',
  unit: 'ms',
});

const activeRequestsGauge = meter.createUpDownCounter('agent.requests.active', {
  description: 'Number of in-flight agent requests',
});

// Use in your agent wrapper
class MeteredAgent implements Agent {
  constructor(private readonly inner: Agent) {}

  readonly name = this.inner.name;

  async process(message: Message): Promise<Message> {
    const labels = { agent: this.inner.name, role: message.role };

    activeRequestsGauge.add(1, labels);
    requestCounter.add(1, labels);

    const start = performance.now();
    try {
      const response = await this.inner.process(message);

      latencyHistogram.record(performance.now() - start, {
        ...labels,
        success: 'true',
      });

      return response;
    } catch (error) {
      latencyHistogram.record(performance.now() - start, {
        ...labels,
        success: 'false',
      });
      throw error;
    } finally {
      activeRequestsGauge.add(-1, labels);
    }
  }
}
```

---

## Structured Logging

### Using the Agenkit Logger

```typescript
import { createLogger } from '@agenkit/core/observability';

const logger = createLogger({
  name: 'my-agent-service',
  level: process.env.LOG_LEVEL ?? 'info',
  format: 'json', // 'json' for production, 'pretty' for development
});

// Log with structured context
logger.info('agent started', { agentName: 'greeter', version: '1.0.0' });
logger.debug('processing message', { role: message.role, contentLength: JSON.stringify(message.content).length });
logger.error('agent failed', { agentName: 'greeter', error: error.message, stack: error.stack });
```

### Correlation IDs

Attach a correlation ID to every log message for a request:

```typescript
import { AsyncLocalStorage } from 'node:async_hooks';
import { randomUUID } from 'node:crypto';

// Store correlation context across async boundaries
const correlationStorage = new AsyncLocalStorage<{ correlationId: string }>();

function withCorrelationId<T>(fn: () => Promise<T>): Promise<T> {
  const correlationId = randomUUID();
  return correlationStorage.run({ correlationId }, fn);
}

class CorrelatedAgent implements Agent {
  constructor(
    private readonly inner: Agent,
    private readonly logger: Logger
  ) {}

  readonly name = this.inner.name;

  async process(message: Message): Promise<Message> {
    const ctx = correlationStorage.getStore();
    const correlationId = ctx?.correlationId ?? randomUUID();

    this.logger.info('request started', {
      agentName: this.name,
      correlationId,
      messageRole: message.role,
    });

    try {
      const response = await this.inner.process(message);

      this.logger.info('request completed', {
        agentName: this.name,
        correlationId,
        responseRole: response.role,
      });

      return response;
    } catch (error) {
      this.logger.error('request failed', {
        agentName: this.name,
        correlationId,
        error: error instanceof Error ? error.message : String(error),
      });
      throw error;
    }
  }
}

// Usage
await withCorrelationId(async () => {
  const response = await correlatedAgent.process(message);
  // All logs within this block share the same correlationId
});
```

### Log Levels

| Level | When to Use |
|-------|-------------|
| `error` | Errors that affect functionality |
| `warn` | Unexpected conditions that are recoverable |
| `info` | Key business events (request start/end, config) |
| `debug` | Detailed diagnostic information |
| `trace` | Very verbose, internal state |

---

## Audit Middleware

`AuditMiddleware` logs every request and response for compliance and debugging.

```typescript
import { AuditMiddleware } from '@agenkit/core/observability';

const agent = new AuditMiddleware(baseAgent, {
  logger: auditLogger,
  includeContent: false,   // set true only in development (may log PII)
  includeMetadata: true,
  onAuditRecord: (record) => {
    // Custom audit sink — write to database, queue, etc.
    auditDatabase.insert({
      timestamp: record.timestamp,
      agentName: record.agentName,
      durationMs: record.durationMs,
      success: record.success,
      requestRole: record.request.role,
      responseRole: record.response?.role,
      error: record.error,
    });
  },
});

const response = await agent.process(message);
```

### Audit Record Structure

```typescript
interface AuditRecord {
  timestamp: string;          // ISO 8601
  agentName: string;
  durationMs: number;
  success: boolean;
  request: {
    role: string;
    contentLength: number;
    metadata?: Record<string, unknown>;
  };
  response?: {
    role: string;
    contentLength: number;
    metadata?: Record<string, unknown>;
  };
  error?: string;
  traceId?: string;           // OpenTelemetry trace ID if available
  spanId?: string;            // OpenTelemetry span ID if available
}
```

---

## Distributed Tracing with Async Context

### Propagating Trace Context

When agents call other services, propagate the W3C Trace Context:

```typescript
import { context, propagation, trace } from '@opentelemetry/api';
import { W3CTraceContextPropagator } from '@opentelemetry/core';

// Inject trace context into HTTP headers
async function callDownstreamAgent(
  url: string,
  message: Message
): Promise<Message> {
  const carrier: Record<string, string> = {};
  propagation.inject(context.active(), carrier);

  const response = await fetch(`${url}/process`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...carrier, // W3C traceparent + tracestate headers
    },
    body: JSON.stringify(message),
  });

  return response.json() as Promise<Message>;
}

// Extract trace context from incoming HTTP request
function extractTraceContext(headers: Record<string, string>): void {
  const ctx = propagation.extract(context.active(), headers);
  context.with(ctx, () => {
    // All spans created here will be children of the incoming trace
  });
}
```

### AsyncLocalStorage for Request Context

```typescript
import { AsyncLocalStorage } from 'node:async_hooks';
import { context, trace } from '@opentelemetry/api';

interface RequestContext {
  traceId: string;
  spanId: string;
  userId?: string;
  sessionId?: string;
}

const requestContextStorage = new AsyncLocalStorage<RequestContext>();

// Middleware to set request context (e.g., in Express/Fastify)
function attachRequestContext(
  req: Request,
  _res: Response,
  next: () => void
): void {
  const span = trace.getActiveSpan();
  const spanContext = span?.spanContext();

  const ctx: RequestContext = {
    traceId: spanContext?.traceId ?? 'unknown',
    spanId: spanContext?.spanId ?? 'unknown',
    userId: req.headers['x-user-id'] as string | undefined,
    sessionId: req.headers['x-session-id'] as string | undefined,
  };

  requestContextStorage.run(ctx, next);
}

// Access in any downstream code
function getCurrentContext(): RequestContext | undefined {
  return requestContextStorage.getStore();
}

class ContextAwareAgent implements Agent {
  readonly name = 'context-aware';

  async process(message: Message): Promise<Message> {
    const ctx = getCurrentContext();

    return {
      role: 'assistant',
      content: `Processed for user ${ctx?.userId ?? 'anonymous'}`,
      metadata: {
        traceId: ctx?.traceId,
        sessionId: ctx?.sessionId,
      },
    };
  }
}
```

---

## Exporting to Backends

### Jaeger

```bash
# Start Jaeger with Docker
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 14268:14268 \
  jaegertracing/all-in-one:latest
```

```typescript
import { JaegerExporter } from '@opentelemetry/exporter-jaeger';

const traceExporter = new JaegerExporter({
  endpoint: 'http://localhost:14268/api/traces',
});
```

Open the Jaeger UI at: `http://localhost:16686`

### Zipkin

```bash
docker run -d --name zipkin -p 9411:9411 openzipkin/zipkin
```

```typescript
import { ZipkinExporter } from '@opentelemetry/exporter-zipkin';

const traceExporter = new ZipkinExporter({
  url: 'http://localhost:9411/api/v2/spans',
});
```

### Prometheus + Grafana

```typescript
import { PrometheusExporter } from '@opentelemetry/exporter-prometheus';

// Prometheus scrapes /metrics at this port
const metricReader = new PrometheusExporter({ port: 9464 });
```

Then configure Prometheus to scrape:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'agenkit'
    static_configs:
      - targets: ['localhost:9464']
```

### OTLP (OpenTelemetry Collector)

```bash
npm install @opentelemetry/exporter-otlp-http
```

```typescript
import { OTLPTraceExporter } from '@opentelemetry/exporter-otlp-http';
import { OTLPMetricExporter } from '@opentelemetry/exporter-otlp-http';

const traceExporter = new OTLPTraceExporter({
  url: 'http://otel-collector:4318/v1/traces',
});

const metricExporter = new OTLPMetricExporter({
  url: 'http://otel-collector:4318/v1/metrics',
});
```

---

## Production Patterns

### Full Observability Stack

```typescript
import {
  TracingAgent,
  MetricsMiddleware,
  RetryMiddleware,
  TimeoutMiddleware,
  CircuitBreakerMiddleware,
} from '@agenkit/core';
import { AuditMiddleware } from '@agenkit/core/observability';
import { trace } from '@opentelemetry/api';

const tracer = trace.getTracer('agent-service', '1.0.0');

function buildProductionAgent(base: Agent): Agent {
  let agent: Agent = base;

  // Resilience (innermost — measured by tracing)
  agent = new RetryMiddleware(agent, { maxRetries: 3, initialDelayMs: 1000 });
  agent = new TimeoutMiddleware(agent, { timeoutMs: 30000 });
  agent = new CircuitBreakerMiddleware(agent, {
    failureThreshold: 5,
    recoveryTimeoutMs: 60000,
  });

  // Observability (outermost — captures all latency)
  agent = new MetricsMiddleware(agent);
  agent = new AuditMiddleware(agent, {
    logger: auditLogger,
    includeContent: false,
  });
  agent = new TracingAgent(agent, {
    tracer,
    serviceName: 'agent-service',
  });

  return agent;
}

const productionAgent = buildProductionAgent(llmAgent);
```

### Health Check Endpoint

```typescript
import { MetricsMiddleware, CircuitBreakerMiddleware } from '@agenkit/core';

// Expose health and metrics via HTTP
function createHealthEndpoint(agents: Map<string, Agent>): RequestHandler {
  return (_req, res) => {
    const health: Record<string, unknown> = {};

    for (const [name, agent] of agents) {
      if (agent instanceof CircuitBreakerMiddleware) {
        health[name] = {
          status: agent.getState() === 'open' ? 'unhealthy' : 'healthy',
          circuit: agent.getState(),
          ...agent.getMetrics(),
        };
      } else if (agent instanceof MetricsMiddleware) {
        health[name] = {
          status: 'healthy',
          ...agent.getMetrics(),
        };
      } else {
        health[name] = { status: 'healthy' };
      }
    }

    const isHealthy = Object.values(health).every(
      (h) => (h as { status: string }).status === 'healthy'
    );

    res.status(isHealthy ? 200 : 503).json({
      status: isHealthy ? 'healthy' : 'degraded',
      agents: health,
      timestamp: new Date().toISOString(),
    });
  };
}
```

---

## Quick Reference

### Installation

```bash
# Core observability
npm install @opentelemetry/sdk-node @opentelemetry/api

# Jaeger exporter
npm install @opentelemetry/exporter-jaeger

# Prometheus exporter
npm install @opentelemetry/exporter-prometheus

# OTLP exporter
npm install @opentelemetry/exporter-otlp-http

# Auto-instrumentations
npm install @opentelemetry/auto-instrumentations-node
```

### Common Patterns

```typescript
// Tracing
import { TracingAgent } from '@agenkit/core';
import { trace } from '@opentelemetry/api';

const tracer = trace.getTracer('service-name', '1.0.0');
const traced = new TracingAgent(agent, { tracer });

// Metrics
import { MetricsMiddleware } from '@agenkit/core/middleware';
const metered = new MetricsMiddleware(agent);
const metrics = metered.getMetrics();

// Logging
import { createLogger } from '@agenkit/core/observability';
const logger = createLogger({ name: 'service', level: 'info', format: 'json' });
logger.info('event', { key: 'value' });

// Audit
import { AuditMiddleware } from '@agenkit/core/observability';
const audited = new AuditMiddleware(agent, { logger });
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OTEL_SERVICE_NAME` | Service name for telemetry | `'unknown'` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector endpoint | `'http://localhost:4318'` |
| `JAEGER_ENDPOINT` | Jaeger Thrift HTTP endpoint | `'http://localhost:14268/api/traces'` |
| `LOG_LEVEL` | Logging level | `'info'` |
| `NODE_ENV` | Environment tag | `'development'` |

### See Also

- [API.md](API.md) — TracingAgent and MetricsCollector API reference
- [TESTING_FRAMEWORK.md](TESTING_FRAMEWORK.md) — Testing with mock tracing
- [GETTING_STARTED.md](GETTING_STARTED.md) — Basic setup guide

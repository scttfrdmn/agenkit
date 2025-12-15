# TypeScript Observability API Reference

Complete API reference for Agenkit's TypeScript observability module.

## Package: `@agenkit/core/observability`

### Functions

#### `initTracing()`

Initialize OpenTelemetry distributed tracing.

```typescript
function initTracing(config: TracingConfig): NodeTracerProvider
```

**Parameters:**
- `config` (TracingConfig): Tracing configuration object.
  - `serviceName` (string): Name to identify this service in traces.
  - `otlpEndpoint` (string, optional): OTLP collector endpoint (e.g., `"http://localhost:4318/v1/traces"`). If not specified, OTLP export is disabled.
  - `consoleExport` (boolean, optional): Whether to export traces to console for debugging. Default: `false`.

**Returns:**
- `NodeTracerProvider`: The configured OpenTelemetry tracer provider.

**Example:**
```typescript
import { initTracing } from '@agenkit/core/observability';

// Development: console export
const provider = initTracing({
  serviceName: 'my-agent-service',
  consoleExport: true,
});

// Production: OTLP export to Jaeger/Tempo
const provider = initTracing({
  serviceName: 'my-agent-service',
  otlpEndpoint: 'http://localhost:4318/v1/traces',
});
```

---

#### `shutdownTracing()`

Shutdown tracing and flush pending spans.

```typescript
async function shutdownTracing(): Promise<void>
```

**Returns:**
- `Promise<void>`: Promise that resolves when shutdown is complete.

**Example:**
```typescript
import { shutdownTracing } from '@agenkit/core/observability';

// On application shutdown
process.on('SIGTERM', async () => {
  await shutdownTracing();
  process.exit(0);
});
```

---

#### `initMetrics()`

Initialize OpenTelemetry metrics with Prometheus export.

```typescript
async function initMetrics(config: MetricsConfig): Promise<MeterProvider>
```

**Parameters:**
- `config` (MetricsConfig): Metrics configuration object.
  - `serviceName` (string): Name to identify this service in metrics.
  - `port` (number): Port for Prometheus metrics HTTP endpoint.
  - `host` (string, optional): Hostname for metrics server. Default: `"0.0.0.0"`.

**Returns:**
- `Promise<MeterProvider>`: Promise resolving to the configured OpenTelemetry meter provider.

**Example:**
```typescript
import { initMetrics } from '@agenkit/core/observability';

const provider = await initMetrics({
  serviceName: 'my-agent-service',
  port: 8003,
});

// Metrics available at http://localhost:8003/metrics
```

---

#### `shutdownMetrics()`

Shutdown metrics and close Prometheus endpoint.

```typescript
async function shutdownMetrics(): Promise<void>
```

**Returns:**
- `Promise<void>`: Promise that resolves when shutdown is complete.

**Example:**
```typescript
import { shutdownMetrics } from '@agenkit/core/observability';

process.on('SIGTERM', async () => {
  await shutdownMetrics();
  process.exit(0);
});
```

---

#### `configureLogging()`

Configure structured logging with optional trace correlation.

```typescript
function configureLogging(config: Partial<LoggingConfig>): void
```

**Parameters:**
- `config` (Partial<LoggingConfig>): Logging configuration object.
  - `level` (LogLevel): Log level enum value. Default: `LogLevel.INFO`.
  - `structured` (boolean): Whether to use JSON structured logging format. Default: `false`.
  - `includeTraceContext` (boolean): Whether to include trace_id and span_id in logs. Default: `false`.

**Example:**
```typescript
import { configureLogging, LogLevel } from '@agenkit/core/observability';

// JSON logs with trace correlation
configureLogging({
  level: LogLevel.INFO,
  structured: true,
  includeTraceContext: true,
});

// Plain text logs without trace correlation
configureLogging({
  level: LogLevel.DEBUG,
  structured: false,
  includeTraceContext: false,
});
```

---

#### `getLoggerWithTrace()`

Get a logger instance that includes trace context in log records.

```typescript
function getLoggerWithTrace(name: string): Logger
```

**Parameters:**
- `name` (string): Logger name, typically module or component name.

**Returns:**
- `Logger`: Logger instance with trace context support.

**Example:**
```typescript
import { getLoggerWithTrace } from '@agenkit/core/observability';

const logger = getLoggerWithTrace('MyAgent');

// Logs will automatically include trace_id and span_id when in a span
logger.info('Processing message', { user_id: '123' });
```

---

#### `getTracer()`

Get the current tracer instance.

```typescript
function getTracer(): Tracer | null
```

**Returns:**
- `Tracer | null`: OpenTelemetry tracer instance, or null if tracing not initialized.

**Example:**
```typescript
import { getTracer } from '@agenkit/core/observability';
import { trace } from '@opentelemetry/api';

const tracer = getTracer();
if (tracer) {
  const span = tracer.startSpan('custom-operation');
  span.setAttribute('key', 'value');
  // Do work...
  span.end();
}
```

---

#### `getMetricsUrl()`

Get the Prometheus metrics endpoint URL.

```typescript
function getMetricsUrl(): string | null
```

**Returns:**
- `string | null`: Metrics URL (e.g., `"http://localhost:8003/metrics"`), or null if metrics not initialized.

**Example:**
```typescript
import { getMetricsUrl } from '@agenkit/core/observability';

const url = getMetricsUrl();
if (url) {
  console.log(`Metrics available at: ${url}`);
}
```

---

#### `getLoggingConfig()`

Get current logging configuration.

```typescript
function getLoggingConfig(): LoggingConfig
```

**Returns:**
- `LoggingConfig`: Current logging configuration object.

**Example:**
```typescript
import { getLoggingConfig } from '@agenkit/core/observability';

const config = getLoggingConfig();
console.log(`Current log level: ${config.level}`);
```

---

### Classes

#### `TracingMiddleware`

Middleware that adds distributed tracing to agent processing.

```typescript
class TracingMiddleware extends BaseMiddleware {
  constructor(agent: Agent, spanName?: string)
}
```

**Constructor Parameters:**
- `agent` (Agent): The agent to wrap with tracing.
- `spanName` (string, optional): Custom span name. If not specified, uses `"agent.{agent.name}.process"`.

**Properties:**
- `name` (string): Returns the wrapped agent's name.
- `capabilities` (string[]): Returns the wrapped agent's capabilities.

**Methods:**

##### `process()`

Process a message with distributed tracing.

```typescript
async process(message: Message): Promise<Message>
```

**Parameters:**
- `message` (Message): Input message to process.

**Returns:**
- `Promise<Message>`: Response message with trace context injected into metadata.

**Throws:**
- Any exception raised by the wrapped agent.

**Behavior:**
- Extracts parent trace context from `message.metadata.trace_context`
- Creates a new span as a child of parent context
- Records span attributes (agent name, capabilities, message role, content length, metadata keys)
- Calls wrapped agent's `process()` method
- Records success status or error
- Injects trace context into response metadata

**Example:**
```typescript
import { TracingMiddleware } from '@agenkit/core/observability';

const baseAgent = new MyAgent();
const tracedAgent = new TracingMiddleware(baseAgent);

// Process message - span is created automatically
const response = await tracedAgent.process(message);

// Response includes trace context for propagation
console.log(response.metadata?.trace_context);
// { traceparent: '00-...', ... }
```

---

#### `MetricsMiddleware`

Middleware that adds metrics collection to agent processing.

```typescript
class MetricsMiddleware extends BaseMiddleware {
  constructor(agent: Agent)
}
```

**Constructor Parameters:**
- `agent` (Agent): The agent to wrap with metrics collection.

**Properties:**
- `name` (string): Returns the wrapped agent's name.
- `capabilities` (string[]): Returns the wrapped agent's capabilities.

**Methods:**

##### `process()`

Process a message with metrics collection.

```typescript
async process(message: Message): Promise<Message>
```

**Parameters:**
- `message` (Message): Input message to process.

**Returns:**
- `Promise<Message>`: Response message from wrapped agent.

**Throws:**
- Any exception raised by the wrapped agent.

**Metrics Recorded:**
- `agenkit.agent.requests`: Counter of total requests
- `agenkit.agent.errors`: Counter of errors (only on failure)
- `agenkit.agent.latency`: Histogram of processing latency in milliseconds
- `agenkit.agent.message_size`: Histogram of message content size in bytes

**Attributes (Labels):**
- `agent.name`: Name of the agent
- `message.role`: Role of the message
- `status`: "success" or "error"
- `error.type`: Type of exception (only on error)

**Example:**
```typescript
import { MetricsMiddleware } from '@agenkit/core/observability';

const baseAgent = new MyAgent();
const monitoredAgent = new MetricsMiddleware(baseAgent);

// Process message - metrics are recorded automatically
const response = await monitoredAgent.process(message);
```

---

#### `Logger`

Logger class with trace context support.

```typescript
class Logger {
  constructor(name: string)
}
```

**Constructor Parameters:**
- `name` (string): Logger name, typically module or component name.

**Methods:**

##### `debug()`

Log a debug message.

```typescript
debug(message: string, metadata?: Record<string, any>): void
```

**Parameters:**
- `message` (string): Log message.
- `metadata` (Record<string, any>, optional): Additional metadata to include in log entry.

**Example:**
```typescript
logger.debug('Cache miss', { key: 'user:123' });
```

---

##### `info()`

Log an info message.

```typescript
info(message: string, metadata?: Record<string, any>): void
```

**Parameters:**
- `message` (string): Log message.
- `metadata` (Record<string, any>, optional): Additional metadata to include in log entry.

**Example:**
```typescript
logger.info('Processing request', { user_id: '123' });
```

---

##### `warn()`

Log a warning message.

```typescript
warn(message: string, metadata?: Record<string, any>): void
```

**Parameters:**
- `message` (string): Log message.
- `metadata` (Record<string, any>, optional): Additional metadata to include in log entry.

**Example:**
```typescript
logger.warn('Rate limit approaching', { current: 950, limit: 1000 });
```

---

##### `error()`

Log an error message.

```typescript
error(message: string, error?: Error, metadata?: Record<string, any>): void
```

**Parameters:**
- `message` (string): Log message.
- `error` (Error, optional): Error object to log.
- `metadata` (Record<string, any>, optional): Additional metadata to include in log entry.

**Example:**
```typescript
try {
  await riskyOperation();
} catch (err) {
  logger.error('Operation failed', err as Error, { operation: 'riskyOperation' });
}
```

---

### Helper Functions

#### `injectTraceContext()`

Inject current trace context into metadata dictionary.

```typescript
function injectTraceContext(metadata?: Record<string, any>): Record<string, any>
```

**Parameters:**
- `metadata` (Record<string, any>, optional): Existing metadata dictionary or undefined.

**Returns:**
- `Record<string, any>`: Metadata with trace context added under `"trace_context"` key.

**Example:**
```typescript
import { injectTraceContext } from '@agenkit/core/observability';

const metadata = { key: 'value' };
const withTrace = injectTraceContext(metadata);
// { key: 'value', trace_context: { traceparent: '00-...' } }
```

---

#### `extractTraceContext()`

Extract trace context from message metadata.

```typescript
function extractTraceContext(metadata?: Record<string, any>): Context
```

**Parameters:**
- `metadata` (Record<string, any>, optional): Message metadata.

**Returns:**
- `Context`: OpenTelemetry context (currently returns active context).

**Note:** Full W3C Trace Context propagation would require setting up a propagator. For now, this returns the active context.

**Example:**
```typescript
import { extractTraceContext } from '@agenkit/core/observability';

const ctx = extractTraceContext(message.metadata);
```

---

#### `createTracedAgent()`

Create a traced agent by wrapping with TracingMiddleware.

```typescript
function createTracedAgent(agent: Agent, spanName?: string): Agent
```

**Parameters:**
- `agent` (Agent): Agent to wrap.
- `spanName` (string, optional): Custom span name.

**Returns:**
- `Agent`: Traced agent.

**Example:**
```typescript
import { createTracedAgent } from '@agenkit/core/observability';

const agent = new MyAgent();
const tracedAgent = createTracedAgent(agent);
```

---

#### `createMonitoredAgent()`

Create a monitored agent by wrapping with MetricsMiddleware.

```typescript
function createMonitoredAgent(agent: Agent): Agent
```

**Parameters:**
- `agent` (Agent): Agent to wrap.

**Returns:**
- `Agent`: Monitored agent.

**Example:**
```typescript
import { createMonitoredAgent } from '@agenkit/core/observability';

const agent = new MyAgent();
const monitoredAgent = createMonitoredAgent(agent);
```

---

### Type Definitions

#### `TracingConfig`

Configuration for tracing initialization.

```typescript
interface TracingConfig {
  serviceName: string;
  otlpEndpoint?: string;
  consoleExport?: boolean;
}
```

**Fields:**
- `serviceName` (string): Service name for traces.
- `otlpEndpoint` (string, optional): OTLP endpoint URL.
- `consoleExport` (boolean, optional): Enable console export for development.

---

#### `MetricsConfig`

Configuration for metrics initialization.

```typescript
interface MetricsConfig {
  serviceName: string;
  port: number;
  host?: string;
}
```

**Fields:**
- `serviceName` (string): Service name for metrics.
- `port` (number): Port for Prometheus scrape endpoint.
- `host` (string, optional): Hostname for metrics server.

---

#### `LoggingConfig`

Configuration for structured logging.

```typescript
interface LoggingConfig {
  level: LogLevel;
  structured: boolean;
  includeTraceContext: boolean;
}
```

**Fields:**
- `level` (LogLevel): Minimum log level.
- `structured` (boolean): Use JSON format.
- `includeTraceContext` (boolean): Include trace_id and span_id.

---

#### `LogLevel`

Log level enumeration.

```typescript
enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARN = 'WARN',
  ERROR = 'ERROR',
}
```

**Values:**
- `DEBUG`: Debug level logging.
- `INFO`: Informational logging.
- `WARN`: Warning logging.
- `ERROR`: Error logging.

---

#### `LogEntry`

Structured log entry format.

```typescript
interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  trace_id?: string;
  span_id?: string;
  [key: string]: any;
}
```

**Fields:**
- `timestamp` (string): ISO 8601 timestamp.
- `level` (LogLevel): Log level.
- `message` (string): Log message.
- `trace_id` (string, optional): Trace ID from active span.
- `span_id` (string, optional): Span ID from active span.
- Additional fields from metadata.

---

#### `TraceContext`

W3C Trace Context format.

```typescript
interface TraceContext {
  traceparent: string;
  tracestate?: string;
}
```

**Fields:**
- `traceparent` (string): W3C traceparent header (format: `00-{trace_id}-{span_id}-{flags}`).
- `tracestate` (string, optional): W3C tracestate header.

---

#### `Message`

Agent message type (from `@agenkit/core`):

```typescript
interface Message {
  role: string;
  content: string | object;
  metadata?: Record<string, any>;
  timestamp?: Date;
}
```

**Fields:**
- `role` (string): Message role (e.g., "user", "assistant").
- `content` (string | object): Message content.
- `metadata` (Record<string, any>, optional): Optional metadata, used for trace context propagation.
- `timestamp` (Date, optional): Message timestamp.

---

#### `Agent`

Agent interface (from `@agenkit/core`):

```typescript
interface Agent {
  readonly name: string;
  readonly capabilities: string[];
  process(message: Message): Promise<Message>;
}
```

**Properties:**
- `name` (string): Agent name.
- `capabilities` (string[]): Agent capabilities.

**Methods:**
- `process(message: Message): Promise<Message>`: Process a message.

---

## Usage Patterns

### Complete Setup

```typescript
import {
  initTracing,
  initMetrics,
  configureLogging,
  LogLevel,
  TracingMiddleware,
  MetricsMiddleware,
  getLoggerWithTrace,
  shutdownTracing,
  shutdownMetrics,
} from '@agenkit/core/observability';

async function main() {
  // Initialize observability
  initTracing({
    serviceName: 'my-agent-service',
    consoleExport: true,
  });

  await initMetrics({
    serviceName: 'my-agent-service',
    port: 8003,
  });

  configureLogging({
    level: LogLevel.INFO,
    structured: true,
    includeTraceContext: true,
  });

  // Get logger
  const logger = getLoggerWithTrace('main');

  // Wrap agent with middleware
  const baseAgent = new MyAgent();
  const tracedAgent = new TracingMiddleware(baseAgent);
  const monitoredAgent = new MetricsMiddleware(tracedAgent);

  // Use agent
  logger.info('Starting request');
  const response = await monitoredAgent.process(message);
  logger.info('Request complete');

  // Cleanup
  await shutdownTracing();
  await shutdownMetrics();
}
```

### Custom Instrumentation

```typescript
import { getTracer } from '@agenkit/core/observability';
import { trace, metrics } from '@opentelemetry/api';

// Manual tracing
const tracer = getTracer();
if (tracer) {
  const span = tracer.startSpan('database-query');
  span.setAttribute('query', 'SELECT * FROM users');

  try {
    const result = await db.query(...);
    span.setAttribute('rows', result.length);
  } finally {
    span.end();
  }
}

// Manual metrics
const meter = metrics.getMeter('@agenkit/core');
const counter = meter.createCounter('cache.hits', {
  description: 'Cache hit counter',
});
counter.add(1, { cache_name: 'user-cache' });
```

### Error Handling

```typescript
const logger = getLoggerWithTrace('MyAgent');

try {
  const response = await agent.process(message);
  return response;
} catch (error) {
  // Errors are automatically recorded in spans and metrics
  logger.error('Processing failed', error as Error, {
    agent: agent.name,
    message_role: message.role,
  });
  throw error;
}
```

### Middleware Chaining

```typescript
import {
  TracingMiddleware,
  MetricsMiddleware,
  createTracedAgent,
  createMonitoredAgent,
} from '@agenkit/core/observability';

// Option 1: Explicit chaining
const baseAgent = new MyAgent();
const tracedAgent = new TracingMiddleware(baseAgent);
const monitoredAgent = new MetricsMiddleware(tracedAgent);

// Option 2: Helper functions
const baseAgent2 = new MyAgent();
const observableAgent = createMonitoredAgent(
  createTracedAgent(baseAgent2)
);
```

### Integration with Web Frameworks

#### Express.js

```typescript
import express from 'express';
import {
  initTracing,
  initMetrics,
  configureLogging,
  LogLevel,
} from '@agenkit/core/observability';

const app = express();

// Initialize observability at startup
initTracing({ serviceName: 'my-api', consoleExport: false });
await initMetrics({ serviceName: 'my-api', port: 8003 });
configureLogging({
  level: LogLevel.INFO,
  structured: true,
  includeTraceContext: true,
});

// Use traced agents in routes
app.post('/process', async (req, res) => {
  const message = { role: 'user', content: req.body.content };
  const response = await monitoredAgent.process(message);
  res.json(response);
});

app.listen(3000);
```

#### NestJS

```typescript
import { Injectable, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import {
  initTracing,
  initMetrics,
  shutdownTracing,
  shutdownMetrics,
} from '@agenkit/core/observability';

@Injectable()
export class ObservabilityService implements OnModuleInit, OnModuleDestroy {
  async onModuleInit() {
    initTracing({ serviceName: 'my-nest-service' });
    await initMetrics({ serviceName: 'my-nest-service', port: 8003 });
  }

  async onModuleDestroy() {
    await shutdownTracing();
    await shutdownMetrics();
  }
}
```

---

## Best Practices

### 1. Initialize Early

Always initialize observability at application startup, before creating agents:

```typescript
// ✅ Good
await initTracing({ serviceName: 'my-service' });
await initMetrics({ serviceName: 'my-service', port: 8003 });
configureLogging({ level: LogLevel.INFO, structured: true });

const agent = new MyAgent();
```

```typescript
// ❌ Bad
const agent = new MyAgent();
await initTracing({ serviceName: 'my-service' });  // Too late!
```

### 2. Layer Middleware Correctly

Apply middleware in this order:

```typescript
// ✅ Correct order
const baseAgent = new MyAgent();
const tracedAgent = new TracingMiddleware(baseAgent);     // Tracing first
const monitoredAgent = new MetricsMiddleware(tracedAgent); // Metrics second
```

### 3. Use Meaningful Service Names

```typescript
// ✅ Good
initTracing({ serviceName: 'recommendation-agent' });
initTracing({ serviceName: 'search-agent' });

// ❌ Bad
initTracing({ serviceName: 'service' });
initTracing({ serviceName: 'agent1' });
```

### 4. Include Context in Logs

```typescript
// ✅ Good
logger.info('Processing request', {
  user_id: userId,
  request_id: requestId,
  agent: agent.name,
});

// ❌ Bad
logger.info(`Processing request for ${userId}`);
```

### 5. Handle Shutdown Gracefully

```typescript
// Flush pending traces/metrics on shutdown
process.on('SIGTERM', async () => {
  await shutdownTracing();
  await shutdownMetrics();
  process.exit(0);
});

process.on('SIGINT', async () => {
  await shutdownTracing();
  await shutdownMetrics();
  process.exit(0);
});
```

### 6. Don't Log Sensitive Data

```typescript
// ✅ Good
logger.info('User authenticated', { user_id: user.id });

// ❌ Bad
logger.info('User authenticated', { password: password });
```

---

## See Also

- [Observability Guide](./observability.md) - Comprehensive usage guide
- [Python API Reference](./observability-python-api.md) - Python observability API
- [Go API Reference](./observability-go-api.md) - Go observability API
- [Examples](../agenkit-ts/examples/observability-example.ts) - Working example

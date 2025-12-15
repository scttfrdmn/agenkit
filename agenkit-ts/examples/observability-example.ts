/**
 * OpenTelemetry Observability Example
 *
 * Demonstrates distributed tracing, metrics collection, and structured logging
 * across multiple agents with trace correlation.
 *
 * Usage:
 *   npx ts-node examples/observability-example.ts
 *
 * View metrics at: http://localhost:8003/metrics
 */

import {
  Agent,
  Message,
  initTracing,
  initMetrics,
  configureLogging,
  LogLevel,
  TracingMiddleware,
  MetricsMiddleware,
  getLoggerWithTrace,
  shutdownTracing,
  shutdownMetrics,
} from '../src';

/**
 * Simple echo agent for demonstration.
 */
class EchoAgent implements Agent {
  public readonly name: string;
  public readonly capabilities: string[];
  private readonly logger;

  constructor(name: string) {
    this.name = name;
    this.capabilities = ['echo'];
    this.logger = getLoggerWithTrace(`EchoAgent.${name}`);
  }

  async process(message: Message): Promise<Message> {
    this.logger.info('Processing message', {
      message_role: message.role,
      message_length: message.content?.length || 0,
    });

    // Simulate some processing time
    await new Promise((resolve) => setTimeout(resolve, 100));

    const response: Message = {
      role: 'assistant',
      content: `Echo from ${this.name}: ${message.content}`,
      metadata: {
        processed_by: this.name,
        original_message: message.content,
      },
    };

    this.logger.info('Message processed successfully', {
      response_length: response.content?.length || 0,
    });

    return response;
  }
}

/**
 * Main example function.
 */
async function main() {
  console.log('=== Agenkit TypeScript Observability Example ===\n');

  // 1. Initialize observability
  console.log('1. Initializing OpenTelemetry...');

  initTracing({
    serviceName: 'agenkit-ts-example',
    consoleExport: true, // Export traces to console for demo
  });

  await initMetrics({
    serviceName: 'agenkit-ts-example',
    port: 8003, // Prometheus metrics on port 8003
  });

  configureLogging({
    level: LogLevel.INFO,
    structured: true, // JSON structured logging
    includeTraceContext: true, // Include trace_id and span_id
  });

  console.log('✓ Tracing, metrics, and logging initialized\n');
  console.log('  Traces: Console export enabled');
  console.log('  Metrics: http://localhost:8003/metrics');
  console.log('  Logs: Structured JSON with trace context\n');

  // 2. Create agents with observability
  console.log('2. Creating agents with observability middleware...');

  const agent1 = new EchoAgent('agent-1');
  const agent2 = new EchoAgent('agent-2');

  // Wrap with tracing
  const tracedAgent1 = new TracingMiddleware(agent1);
  const tracedAgent2 = new TracingMiddleware(agent2);

  // Wrap with metrics
  const monitoredAgent1 = new MetricsMiddleware(tracedAgent1);
  const monitoredAgent2 = new MetricsMiddleware(tracedAgent2);

  console.log('✓ Agents wrapped with observability middleware\n');

  // 3. Process messages through agent chain
  console.log('3. Processing messages through agents...');

  const message: Message = {
    role: 'user',
    content: 'Hello from the TypeScript observability example!',
  };

  // Process through agent1
  console.log(`   → Sending to ${agent1.name}...`);
  const response1 = await monitoredAgent1.process(message);

  // Process through agent2 with propagated trace context
  console.log(`   → Sending to ${agent2.name}...`);
  const response2 = await monitoredAgent2.process(response1);

  console.log(`\n   ✓ Final response: ${response2.content}\n`);

  // 4. Demonstrate error handling
  console.log('4. Demonstrating error handling and metrics...');

  class FailingAgent implements Agent {
    public readonly name = 'failing-agent';
    public readonly capabilities = ['fail'];
    private readonly logger;

    constructor() {
      this.logger = getLoggerWithTrace('FailingAgent');
    }

    async process(_message: Message): Promise<Message> {
      this.logger.error('Agent intentionally failing for demo');
      throw new Error('Intentional failure for observability demo');
    }
  }

  const failingAgent = new FailingAgent();
  const monitoredFailingAgent = new MetricsMiddleware(new TracingMiddleware(failingAgent));

  try {
    await monitoredFailingAgent.process(message);
  } catch (error) {
    console.log(`   ✓ Error handled and recorded in metrics/traces\n`);
  }

  // 5. Show observability features
  console.log('5. Observability Features:');
  console.log('   • Distributed traces: Check console output above');
  console.log('   • Trace context propagated across agents');
  console.log('   • Structured logs include trace_id and span_id');
  console.log('   • Metrics collected for requests, errors, and latency');
  console.log('   • Prometheus metrics available at http://localhost:8003/metrics\n');

  console.log('6. Metrics Available:');
  console.log('   • agenkit_agent_requests_total - Total requests by agent/status');
  console.log('   • agenkit_agent_errors_total - Total errors by agent/type');
  console.log('   • agenkit_agent_latency - Processing latency histogram');
  console.log('   • agenkit_agent_message_size - Message size histogram\n');

  console.log('7. View Metrics:');
  console.log('   curl http://localhost:8003/metrics\n');

  console.log('=== Example Complete ===\n');

  // Wait a moment for exporters to flush
  await new Promise((resolve) => setTimeout(resolve, 2000));

  // Cleanup
  await shutdownTracing();
  await shutdownMetrics();

  console.log('Observability shutdown complete');
}

// Run example
main().catch((error) => {
  console.error('Example failed:', error);
  process.exit(1);
});

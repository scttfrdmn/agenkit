/**
 * Basic Observability Example
 *
 * Simple introduction to Agenkit observability with:
 * - Console tracing
 * - Basic metrics
 * - Simple logging
 *
 * Usage:
 *   npx ts-node examples/observability-basic.ts
 *
 * View metrics at: http://localhost:8001/metrics
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
class SimpleAgent implements Agent {
  public readonly name = 'simple-agent';
  public readonly capabilities = ['echo'];
  private readonly logger;

  constructor() {
    this.logger = getLoggerWithTrace('SimpleAgent');
  }

  async process(message: Message): Promise<Message> {
    this.logger.info('Processing message', {
      role: message.role,
      content: message.content,
    });

    // Simulate some work
    await new Promise((resolve) => setTimeout(resolve, 100));

    const response: Message = {
      role: 'assistant',
      content: `Echo: ${message.content}`,
    };

    this.logger.info('Message processed');

    return response;
  }
}

/**
 * Main basic example function.
 */
async function main() {
  console.log('=== Agenkit TypeScript Basic Observability Example ===\n');

  // 1. Initialize observability
  console.log('1. Initializing observability...');

  // Initialize tracing with console export
  initTracing({
    serviceName: 'agenkit-basic',
    consoleExport: true,
  });

  // Initialize metrics
  await initMetrics({
    serviceName: 'agenkit-basic',
    port: 8001,
  });

  // Configure logging
  configureLogging({
    level: LogLevel.INFO,
    structured: false, // Human-readable format
    includeTraceContext: true,
  });

  console.log('✓ Observability initialized');
  console.log('  • Tracing: Console export enabled');
  console.log('  • Metrics: http://localhost:8001/metrics');
  console.log('  • Logging: Human-readable format\n');

  // 2. Create agent with observability
  console.log('2. Creating agent with observability...');

  const agent = new SimpleAgent();

  // Wrap with tracing and metrics middleware
  const observableAgent = new MetricsMiddleware(new TracingMiddleware(agent));

  console.log('✓ Agent wrapped with observability middleware\n');

  // 3. Process a message
  console.log('3. Processing message...');

  const message: Message = {
    role: 'user',
    content: 'Hello, observability!',
  };

  const response = await observableAgent.process(message);

  console.log(`✓ Response: "${response.content}"\n`);

  // 4. Show what was captured
  console.log('4. Observability Captured:');
  console.log('   • Trace: Check console output above for span details');
  console.log('   • Logs: Structured logs with trace context');
  console.log('   • Metrics: Request count, latency, and more\n');

  console.log('5. View Metrics:');
  console.log('   curl http://localhost:8001/metrics\n');

  console.log('   You should see:');
  console.log('   • agenkit_agent_requests_total - Total requests');
  console.log('   • agenkit_agent_latency - Processing time\n');

  console.log('=== Example Complete ===\n');

  // Wait for exporters to flush
  await new Promise((resolve) => setTimeout(resolve, 1000));

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

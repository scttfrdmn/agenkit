/**
 * Metrics Query Demo - shows Prometheus metrics output
 */

import { initMetrics, MetricsMiddleware, shutdownMetrics } from '../src/observability/metrics';
import { Agent, Message } from '../src';

class DemoAgent implements Agent {
  public readonly name = 'demo-agent';
  public readonly capabilities = ['test'];

  async process(message: Message): Promise<Message> {
    await new Promise(resolve => setTimeout(resolve, 100));
    return {
      role: 'assistant',
      content: `Processed: ${message.content}`
    };
  }
}

class FailingAgent implements Agent {
  public readonly name = 'failing-agent';
  public readonly capabilities = ['fail'];

  async process(_message: Message): Promise<Message> {
    throw new Error('Intentional failure for metrics demo');
  }
}

async function main() {
  console.log('=== Metrics Demo ===\n');
  console.log('Initializing metrics on port 8007...\n');

  await initMetrics({
    serviceName: 'agenkit-metrics-demo',
    port: 8007
  });

  const agent = new DemoAgent();
  const monitored = new MetricsMiddleware(agent);

  console.log('Processing 5 successful requests...');
  for (let i = 0; i < 5; i++) {
    await monitored.process({
      role: 'user',
      content: `Test message ${i}`
    });
  }
  console.log('✓ 5 requests completed\n');

  console.log('Processing 2 failed requests...');
  const failAgent = new FailingAgent();
  const monitoredFailAgent = new MetricsMiddleware(failAgent);

  for (let i = 0; i < 2; i++) {
    try {
      await monitoredFailAgent.process({
        role: 'user',
        content: 'This will fail'
      });
    } catch (error) {
      // Expected
    }
  }
  console.log('✓ 2 errors captured\n');

  console.log('Fetching Prometheus metrics...\n');
  console.log('='.repeat(80));
  console.log('\n');

  // Query metrics
  const response = await fetch('http://localhost:8007/metrics');
  const text = await response.text();
  console.log(text);

  console.log('='.repeat(80));

  await shutdownMetrics();
  console.log('\nMetrics demo complete!');
}

main().catch(console.error);

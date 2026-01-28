/**
 * Production-ready agent with load balancing, health checks, and enhanced retry.
 *
 * This example demonstrates how to build a production agent system with:
 * - Load balancing across multiple backend agents
 * - Health monitoring with Kubernetes-style probes
 * - Enhanced retry with jitter and backpressure detection
 * - Prometheus metrics export
 *
 * Perfect for 30-hour autonomous agent deployments.
 */

import { Agent, Message } from '../../../agenkit-ts/src/core';
import {
  LoadBalancer,
  LoadBalancerConfig,
  LoadBalancingStrategy,
  HealthChecker,
  HealthCheckConfig,
  EnhancedRetryDecorator,
  EnhancedRetryConfig,
  JitterType,
} from '../../../agenkit-ts/src/infrastructure';

/**
 * Simulated agent for testing production infrastructure.
 */
class SimulatedAgent implements Agent {
  private requestCount = 0;

  constructor(
    private readonly agentName: string,
    private readonly failureRate: number = 0.0
  ) {}

  name(): string {
    return this.agentName;
  }

  capabilities(): string[] {
    return ['text_generation', 'reasoning'];
  }

  async process(message: Message): Promise<Message> {
    this.requestCount++;

    // Simulate processing time
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Simulate occasional failures for testing retry
    if (Math.random() < this.failureRate) {
      throw new Error(`${this.agentName}: Simulated transient error`);
    }

    return {
      role: 'agent',
      content: `${this.agentName} processed: ${message.content}`,
      metadata: {
        agent: this.agentName,
        request_count: this.requestCount,
        timestamp: new Date().toISOString(),
      },
    };
  }
}

/**
 * Run production agent system demonstration.
 */
async function main(): Promise<void> {
  console.log('Starting production agent system...');

  // 1. Create backend agents with varying failure rates
  const backend1 = new SimulatedAgent('agent-1', 0.1);
  const backend2 = new SimulatedAgent('agent-2', 0.05);
  const backend3 = new SimulatedAgent('agent-3', 0.15);

  // 2. Wrap each backend with enhanced retry
  const retryConfig: EnhancedRetryConfig = {
    maxAttempts: 3,
    initialBackoffMs: 100,
    maxBackoffMs: 5000,
    backoffMultiplier: 2.0,
    jitterType: JitterType.Full,
    enableBackpressure: true,
    backpressureThreshold: 0.3,
    backpressureWindow: 10,
    errorStrategies: new Map(),
  };

  const retryBackend1 = new EnhancedRetryDecorator(backend1, retryConfig);
  const retryBackend2 = new EnhancedRetryDecorator(backend2, retryConfig);
  const retryBackend3 = new EnhancedRetryDecorator(backend3, retryConfig);

  // 3. Create load balancer with health checking
  const lbConfig: LoadBalancerConfig = {
    strategy: LoadBalancingStrategy.LeastConnections,
    healthCheckEnabled: true,
    healthCheckIntervalMs: 5000,
    healthCheckTimeoutMs: 2000,
    maxRetriesPerBackend: 2,
  };

  const loadBalancer = new LoadBalancer(
    [retryBackend1, retryBackend2, retryBackend3],
    lbConfig
  );

  // 4. Set up health checker for the load balancer
  const healthConfig: HealthCheckConfig = {
    livenessEnabled: true,
    livenessIntervalMs: 10000,
    livenessFailureThreshold: 3,
    readinessEnabled: true,
    readinessIntervalMs: 5000,
    readinessFailureThreshold: 2,
    startupEnabled: true,
    startupTimeoutMs: 30000,
    startupFailureThreshold: 5,
  };

  const healthChecker = new HealthChecker(loadBalancer, healthConfig);
  healthChecker.start();

  // Wait for startup to complete
  console.log('Waiting for startup checks...');
  await new Promise((resolve) => setTimeout(resolve, 2000));

  if (!healthChecker.isHealthy()) {
    console.error('System failed startup checks');
    return;
  }

  console.log('System is healthy and ready!');

  // 5. Process requests through the production system
  const requests: Message[] = Array.from({ length: 20 }, (_, i) => ({
    role: 'user',
    content: `Request ${i}`,
  }));

  let successful = 0;
  let failed = 0;

  for (let i = 0; i < requests.length; i++) {
    try {
      const response = await loadBalancer.process(requests[i]);
      console.log(`Request ${i}: SUCCESS - ${response.content}`);
      successful++;
    } catch (error) {
      console.error(`Request ${i}: FAILED - ${(error as Error).message}`);
      failed++;
    }

    // Brief pause between requests
    await new Promise((resolve) => setTimeout(resolve, 200));
  }

  // 6. Export metrics
  console.log('\n' + '='.repeat(60));
  console.log('FINAL METRICS');
  console.log('='.repeat(60));

  // Load balancer metrics
  const lbMetrics = loadBalancer.getMetrics();
  console.log('\nLoad Balancer:');
  console.log(`  Total requests: ${lbMetrics.totalRequests}`);
  console.log(`  Successful: ${lbMetrics.successfulRequests}`);
  console.log(`  Failed: ${lbMetrics.failedRequests}`);
  const successRate =
    lbMetrics.totalRequests > 0
      ? (lbMetrics.successfulRequests / lbMetrics.totalRequests) * 100
      : 0;
  console.log(`  Success rate: ${successRate.toFixed(1)}%`);

  // Backend distribution
  console.log('\nBackend Distribution:');
  for (const [backendId, count] of lbMetrics.backendRequestCounts.entries()) {
    console.log(`  ${backendId}: ${count} requests`);
  }

  // Retry metrics for each backend
  console.log('\nRetry Metrics:');
  const backends = [retryBackend1, retryBackend2, retryBackend3];
  for (let i = 0; i < backends.length; i++) {
    const metrics = backends[i].getMetrics();
    console.log(`  Agent ${i + 1}:`);
    console.log(`    Total attempts: ${metrics.totalAttempts}`);
    console.log(`    Successful on first: ${metrics.successfulFirstAttempt}`);
    console.log(`    Successful on retry: ${metrics.successfulOnRetry}`);
    console.log(`    Failed after retries: ${metrics.failedAfterRetries}`);
    console.log(`    Total retries: ${metrics.totalRetries}`);
    if (metrics.backpressureDetected > 0) {
      console.log(
        `    Backpressure detected: ${metrics.backpressureDetected} times`
      );
    }
  }

  // Health metrics
  const healthMetrics = healthChecker.getMetrics();
  console.log('\nHealth Checks:');
  for (const [probeType, count] of healthMetrics.totalChecks.entries()) {
    const success = healthMetrics.successfulChecks.get(probeType) || 0;
    const failedCount = healthMetrics.failedChecks.get(probeType) || 0;
    console.log(
      `  ${probeType}: ${success}/${count} passed (${failedCount} failed)`
    );
  }

  // Export Prometheus metrics
  console.log('\nPrometheus Metrics:');
  console.log('='.repeat(60));
  const prometheusMetrics = healthChecker.exportPrometheusMetrics();
  console.log(prometheusMetrics);

  // Stop health checker
  healthChecker.stop();
  console.log('\nProduction agent system stopped.');
}

// Run the example
main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});

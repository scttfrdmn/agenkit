/**
 * Production Monitoring Example
 *
 * Shows how to integrate the evaluation framework into production systems
 * for continuous monitoring of agent performance.
 *
 * This example demonstrates:
 * - Real-time metrics collection from live traffic
 * - Session recording for debugging
 * - Regression detection for quality gates
 * - Performance statistics and alerting
 *
 * Run with: npx tsx examples/evaluation/production-monitoring.ts
 */

import {
  MetricsCollector,
  SessionResult,
  SessionRecorder,
  FileRecordingStorage,
  RegressionDetector,
  SessionStatus,
  MetricType,
  createMetricMeasurement,
} from '../../src/evaluation';
import { EvaluationResult } from '../../src/evaluation/core';
import { Agent, Message } from '../../src/core/interfaces';

/**
 * Production agent for demonstration.
 */
class ProductionAgent implements Agent {
  getName(): string {
    return 'production-agent';
  }

  getCapabilities(): string[] {
    return ['chat'];
  }

  async process(message: Message, sessionId?: string): Promise<Message> {
    // Simulate processing
    await new Promise(resolve =>
      setTimeout(resolve, 50 + Math.random() * 200)
    );

    return {
      role: 'assistant',
      content: `Response to: ${message.content}`,
      metadata: {},
    };
  }
}

/**
 * Helper functions for creating metrics.
 */
function createQualityMetric(
  name: string,
  score: number,
  maxScore: number,
  metadata?: Record<string, unknown>
) {
  return createMetricMeasurement(
    name,
    score / maxScore,
    MetricType.QualityScore,
    metadata
  );
}

function createDurationMetric(
  durationSeconds: number,
  metadata?: Record<string, unknown>
) {
  return createMetricMeasurement(
    'duration',
    durationSeconds,
    MetricType.Duration,
    metadata
  );
}

function createCostMetric(
  cost: number,
  currency: string,
  metadata?: Record<string, unknown>
) {
  return createMetricMeasurement('total_cost', cost, MetricType.Cost, {
    currency,
    ...metadata,
  });
}

async function main() {
  console.log('Production Monitoring Example');
  console.log('=============================\n');

  // Step 1: Initialize monitoring infrastructure
  console.log('Step 1: Initializing Monitoring Infrastructure');
  console.log('-----------------------------------------------');

  // Create metrics collector (safe for concurrent access in async context)
  const collector = new MetricsCollector();

  // Create session recorder with file storage
  const recorder = new SessionRecorder(
    new FileRecordingStorage('./production_recordings')
  );

  // Create regression detector with baseline
  const baseline = new EvaluationResult('baseline', 'production-agent', new Date());
  baseline.accuracy = 0.95;
  baseline.qualityScore = 0.9;
  baseline.avgLatencyMs = 150.0;

  const detector = new RegressionDetector();
  detector.setBaseline(baseline);

  console.log('✓ MetricsCollector initialized');
  console.log('✓ SessionRecorder configured with file storage');
  console.log('✓ RegressionDetector configured with baseline\n');

  // Step 2: Wrap agent for automatic monitoring
  console.log('Step 2: Wrapping Agent for Monitoring');
  console.log('--------------------------------------');
  const agent = new ProductionAgent();
  const monitoredAgent = recorder.wrap(agent);

  console.log('✓ Agent wrapped - all interactions will be recorded\n');

  // Step 3: Simulate production traffic
  console.log('Step 3: Simulating Production Traffic');
  console.log('--------------------------------------');
  console.log('Processing 50 user requests...\n');

  for (let i = 0; i < 50; i++) {
    const sessionId = `prod-session-${String(i + 1).padStart(3, '0')}`;

    // Create session result
    const result = new SessionResult(sessionId, agent.getName());

    // Process message
    const message: Message = {
      role: 'user',
      content: `User query ${i + 1}`,
      metadata: {
        session_id: sessionId,
      },
    };

    const start = Date.now();
    try {
      await monitoredAgent.process(message, sessionId);
      const duration = (Date.now() - start) / 1000;

      result.setStatus(SessionStatus.Completed);

      // Add quality metric
      const qualityScore = 0.85 + Math.random() * 0.15;
      result.addMetricMeasurement(
        createQualityMetric('response_quality', qualityScore * 10, 10.0, {})
      );

      // Add duration metric
      result.addMetricMeasurement(createDurationMetric(duration, {}));

      // Add cost metric (simulate token usage)
      const tokens = 100 + Math.floor(Math.random() * 300);
      const cost = tokens * 0.00001;
      result.addMetricMeasurement(
        createCostMetric(cost, 'USD', {
          tokens,
        })
      );
    } catch (error) {
      result.setStatus(SessionStatus.Failed);
      result.addError({
        type: 'processing_error',
        message: error instanceof Error ? error.message : String(error),
        details: {},
        timestamp: new Date(),
      });
    }

    collector.addSession(result);

    // Print progress every 10 requests
    if ((i + 1) % 10 === 0) {
      console.log(`  Processed ${i + 1} requests`);
    }
  }

  console.log('\n✓ Processing complete\n');

  // Step 4: Real-time statistics
  console.log('Step 4: Real-time Performance Statistics');
  console.log('-----------------------------------------');

  const sessionCount = collector.getSessionCount();
  const successRate = collector.getSuccessRate();
  const avgDuration = collector.getAverageDuration();
  const totalErrors = collector.getTotalErrorCount();

  console.log('Session Statistics:');
  console.log(`  Total Sessions: ${sessionCount}`);
  console.log(`  Success Rate: ${(successRate * 100).toFixed(1)}%`);
  console.log(`  Avg Duration: ${avgDuration.toFixed(3)}s`);
  console.log(`  Total Errors: ${totalErrors}\n`);

  const aggregated = collector.getAggregatedMetrics();

  const qualityStats = aggregated.get('response_quality');
  if (qualityStats && qualityStats.count > 0) {
    console.log('Quality Metrics:');
    console.log(`  Mean Quality: ${qualityStats.mean.toFixed(3)}`);
    console.log(`  Min Quality: ${qualityStats.min.toFixed(3)}`);
    console.log(`  Max Quality: ${qualityStats.max.toFixed(3)}\n`);
  }

  const costStats = aggregated.get('total_cost');
  if (costStats && costStats.count > 0) {
    const totalCost = costStats.mean * costStats.count;
    console.log('Cost Metrics:');
    console.log(`  Total Cost: $${totalCost.toFixed(4)}`);
    console.log(`  Avg Cost/Request: $${costStats.mean.toFixed(4)}\n`);
  }

  // Step 5: Check for regressions
  console.log('Step 5: Regression Detection');
  console.log('-----------------------------');

  const currentEvaluation = new EvaluationResult('current', 'production-agent', new Date());
  currentEvaluation.accuracy = successRate;
  currentEvaluation.qualityScore = qualityStats?.mean || 0;
  currentEvaluation.avgLatencyMs = avgDuration * 1000; // convert to ms

  const regressions = detector.detect(currentEvaluation);

  if (regressions.length === 0) {
    console.log('✓ No regressions detected - performance is stable\n');
  } else {
    console.log(`⚠ ${regressions.length} regressions detected:\n`);
    regressions.forEach(reg => {
      console.log(`  ${reg.metricName}:`);
      console.log(`    Baseline: ${reg.baselineValue.toFixed(3)}`);
      console.log(`    Current: ${reg.currentValue.toFixed(3)}`);
      console.log(`    Degradation: ${reg.degradationPercent.toFixed(1)}%`);
      console.log(`    Severity: ${reg.severity}\n`);
    });
  }

  // Summary
  console.log('='.repeat(70));
  console.log('Summary: Production Monitoring');
  console.log('='.repeat(70));

  console.log('\nMonitoring Components:');
  console.log('1. MetricsCollector: Aggregate statistics across sessions');
  console.log('2. SessionRecorder: Capture interactions for debugging');
  console.log('3. RegressionDetector: Alert on performance degradation');

  console.log('\nRecommended Architecture:');
  console.log('┌─────────────┐');
  console.log('│   Request   │');
  console.log('└──────┬──────┘');
  console.log('       │');
  console.log('       ▼');
  console.log('┌─────────────────────┐');
  console.log('│  Monitoring Wrapper │ (Recorder)');
  console.log('└──────┬──────────────┘');
  console.log('       │');
  console.log('       ▼');
  console.log('┌─────────────────┐');
  console.log('│  Agent Process  │');
  console.log('└──────┬──────────┘');
  console.log('       │');
  console.log('       ▼');
  console.log('┌────────────────────┐');
  console.log('│  Metrics Collector │');
  console.log('└────────────────────┘');

  console.log('\nBest Practices:');
  console.log('1. Record all production interactions (storage is cheap)');
  console.log('2. Compute statistics in real-time (streaming metrics)');
  console.log('3. Run regression detection hourly or per-deployment');
  console.log('4. Export metrics to monitoring systems (Prometheus, DataDog)');
  console.log('5. Set up alerts for critical regressions');
  console.log('6. Review failed sessions daily for patterns');

  console.log('\nPerformance Considerations:');
  console.log('- Recording overhead: <1ms per request');
  console.log('- Memory usage: ~1KB per session result');
  console.log('- File I/O: Async operations for high throughput');
  console.log('- Async-safe: No race conditions in single-threaded runtime');

  console.log('\nIntegration Examples:');
  console.log('\n1. Express.js Middleware:');
  console.log('```typescript');
  console.log('app.use(async (req, res, next) => {');
  console.log('  const sessionId = req.sessionID;');
  console.log('  const result = new SessionResult(sessionId, "api-agent");');
  console.log('  res.on("finish", () => {');
  console.log('    collector.addSession(result);');
  console.log('  });');
  console.log('  next();');
  console.log('});');
  console.log('```');

  console.log('\n2. Real-time Alerting:');
  console.log('```typescript');
  console.log('setInterval(() => {');
  console.log('  const currentMetrics = collector.getAggregatedMetrics();');
  console.log('  const regressions = detector.detect(toEvaluationResult(currentMetrics));');
  console.log('  if (regressions.some(r => r.severity === "critical")) {');
  console.log('    sendAlert("Critical regression detected!");');
  console.log('  }');
  console.log('}, 60000); // Every minute');
  console.log('```');

  console.log('\n3. Dashboard Export:');
  console.log('```typescript');
  console.log('app.get("/metrics", (req, res) => {');
  console.log('  const stats = collector.getAggregatedMetrics();');
  console.log('  res.json({');
  console.log('    success_rate: collector.getSuccessRate(),');
  console.log('    avg_duration: collector.getAverageDuration(),');
  console.log('    quality: stats.get("response_quality"),');
  console.log('  });');
  console.log('});');
  console.log('```');
}

main().catch(console.error);

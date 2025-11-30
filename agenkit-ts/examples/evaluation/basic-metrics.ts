/**
 * Basic Metrics Collection Example
 *
 * This example demonstrates how to use the evaluation framework to:
 * - Create SessionResult instances to track agent sessions
 * - Add metric measurements (quality, cost, duration)
 * - Collect multiple session results
 * - Compute aggregate statistics across sessions
 *
 * This is the foundation for monitoring agent performance over time,
 * tracking success rates, detecting issues, and measuring improvements.
 *
 * Run with: npx tsx examples/evaluation/basic-metrics.ts
 */

import {
  SessionResult,
  MetricsCollector,
  SessionStatus,
  MetricType,
  createMetricMeasurement,
  createErrorRecord,
} from '../../src/evaluation';

/**
 * Helper functions for creating common metrics.
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

/**
 * Simulate running an agent session and collecting metrics.
 */
async function simulateAgentSession(
  sessionId: string,
  agentName: string
): Promise<SessionResult> {
  const result = new SessionResult(sessionId, agentName);

  // Simulate some processing time
  await new Promise(resolve => setTimeout(resolve, 10 + Math.random() * 50));

  // Add quality metrics
  const qualityScore = 0.7 + Math.random() * 0.3; // 0.7-1.0
  result.addMetricMeasurement(
    createQualityMetric('response_quality', qualityScore * 10, 10.0, {
      evaluator: 'rule_based',
    })
  );

  // Add cost metrics
  const tokensUsed = 100 + Math.floor(Math.random() * 400);
  const costPerToken = 0.00001;
  const totalCost = tokensUsed * costPerToken;
  result.addMetricMeasurement(
    createCostMetric(totalCost, 'USD', {
      tokens: tokensUsed,
    })
  );

  // Add duration metrics
  const durationSeconds = 0.5 + Math.random() * 2.0; // 0.5-2.5 seconds
  result.addMetricMeasurement(createDurationMetric(durationSeconds, {}));

  // Add custom success rate metric
  const success = Math.random() > 0.2; // 80% success rate
  const successValue = success ? 1.0 : 0.0;

  if (success) {
    result.setStatus(SessionStatus.Completed);
  } else {
    result.setStatus(SessionStatus.Failed);
    result.addError(
      createErrorRecord('processing_error', 'Failed to complete task', {
        reason: 'timeout',
      })
    );
  }

  result.addMetricMeasurement(
    createMetricMeasurement('success', successValue, MetricType.SuccessRate, {})
  );

  return result;
}

async function main() {
  console.log('Basic Metrics Collection Example');
  console.log('=================================\n');

  // Step 1: Create metrics collector
  console.log('Step 1: Creating Metrics Collector');
  console.log('-----------------------------------');
  const collector = new MetricsCollector();
  console.log('✓ Metrics collector created\n');

  // Step 2: Simulate multiple agent sessions
  console.log('Step 2: Simulating Agent Sessions');
  console.log('----------------------------------');
  const numSessions = 20;
  console.log(`Running ${numSessions} simulated agent sessions...\n`);

  for (let i = 0; i < numSessions; i++) {
    const sessionId = `session-${String(i + 1).padStart(3, '0')}`;
    const agentName = 'example-agent';

    const result = await simulateAgentSession(sessionId, agentName);
    collector.addSession(result);

    // Print progress
    const status = result.status === SessionStatus.Completed ? '✓' : '✗';
    console.log(`  ${status} Session ${i + 1}: ${result.status}`);
  }
  console.log();

  // Step 3: Compute aggregate statistics
  console.log('Step 3: Computing Aggregate Statistics');
  console.log('---------------------------------------');

  const sessionCount = collector.getSessionCount();
  const completedCount = collector.getSessionsByStatus(SessionStatus.Completed).length;
  const failedCount = collector.getSessionsByStatus(SessionStatus.Failed).length;
  const successRate = collector.getSuccessRate();
  const avgDuration = collector.getAverageDuration();
  const totalErrors = collector.getTotalErrorCount();
  const avgErrorsPerSession = sessionCount > 0 ? totalErrors / sessionCount : 0;

  console.log(`Total Sessions: ${sessionCount}`);
  console.log(`Completed: ${completedCount}`);
  console.log(`Failed: ${failedCount}`);
  console.log(`Success Rate: ${(successRate * 100).toFixed(1)}%`);
  console.log(`Average Duration: ${avgDuration.toFixed(2)}s`);
  console.log(`Total Errors: ${totalErrors}`);
  console.log(`Avg Errors/Session: ${avgErrorsPerSession.toFixed(2)}\n`);

  // Step 4: Analyze specific metrics
  console.log('Step 4: Analyzing Specific Metrics');
  console.log('-----------------------------------');

  const aggregated = collector.getAggregatedMetrics();

  // Quality metrics
  const qualityStats = aggregated.get('response_quality');
  if (qualityStats && qualityStats.count > 0) {
    console.log('\nQuality Metrics:');
    console.log(`  Count: ${qualityStats.count}`);
    console.log(`  Mean: ${qualityStats.mean.toFixed(3)}`);
    console.log(`  Min: ${qualityStats.min.toFixed(3)}`);
    console.log(`  Max: ${qualityStats.max.toFixed(3)}`);
  }

  // Cost metrics
  const costStats = aggregated.get('total_cost');
  if (costStats && costStats.count > 0) {
    const totalCost = costStats.mean * costStats.count;
    console.log('\nCost Metrics:');
    console.log(`  Count: ${costStats.count}`);
    console.log(`  Total Cost: $${totalCost.toFixed(4)}`);
    console.log(`  Average Cost/Session: $${costStats.mean.toFixed(4)}`);
    console.log(`  Min Cost: $${costStats.min.toFixed(4)}`);
    console.log(`  Max Cost: $${costStats.max.toFixed(4)}`);
  }

  // Duration metrics
  const durationStats = aggregated.get('duration');
  if (durationStats && durationStats.count > 0) {
    const totalDuration = durationStats.mean * durationStats.count;
    console.log('\nDuration Metrics:');
    console.log(`  Count: ${durationStats.count}`);
    console.log(`  Total Duration: ${totalDuration.toFixed(2)}s`);
    console.log(`  Average Duration: ${durationStats.mean.toFixed(2)}s`);
    console.log(`  Min Duration: ${durationStats.min.toFixed(2)}s`);
    console.log(`  Max Duration: ${durationStats.max.toFixed(2)}s`);
  }

  // Success rate metrics
  const successStats = aggregated.get('success');
  if (successStats && successStats.count > 0) {
    console.log('\nSuccess Rate Metrics:');
    console.log(`  Count: ${successStats.count}`);
    console.log(`  Success Rate: ${(successStats.mean * 100).toFixed(1)}%`);
  }

  // Step 5: Examine individual session results
  console.log('\n\nStep 5: Examining Individual Sessions');
  console.log('--------------------------------------');
  const results = collector.getAllSessions();

  console.log('\nTop 3 Highest Quality Sessions:');
  console.log('-'.repeat(70));

  // Sort by quality
  const sessionsWithQuality = results
    .map(result => {
      const qualityMeasurement = result.getMeasurementsByName('response_quality')[0];
      return {
        result,
        quality: qualityMeasurement ? qualityMeasurement.value : 0,
      };
    })
    .sort((a, b) => b.quality - a.quality)
    .slice(0, 3);

  sessionsWithQuality.forEach((sw, i) => {
    const costMeasurement = sw.result.getMeasurementsByName('total_cost')[0];
    const durationMeasurement = sw.result.getMeasurementsByName('duration')[0];

    console.log(`${i + 1}. Session: ${sw.result.sessionId}`);
    console.log(`   Quality: ${sw.quality.toFixed(3)}`);
    if (costMeasurement) {
      console.log(`   Cost: $${costMeasurement.value.toFixed(4)}`);
    }
    if (durationMeasurement) {
      console.log(`   Duration: ${durationMeasurement.value.toFixed(2)}s`);
    }
    console.log(`   Status: ${sw.result.status}\n`);
  });

  // Step 6: Summary and best practices
  console.log('='.repeat(70));
  console.log('Summary: Basic Metrics Collection');
  console.log('='.repeat(70));

  console.log('\nKey Capabilities:');
  console.log('1. SessionResult: Track individual agent session metrics');
  console.log('2. MetricsCollector: Aggregate metrics across multiple sessions');
  console.log('3. Metric Types: Quality, cost, duration, success rate, custom');
  console.log('4. Statistics: Success rate, averages, min/max, error rates');

  console.log('\nMetric Types Available:');
  console.log('- MetricType.SuccessRate: Binary success/failure tracking');
  console.log('- MetricType.QualityScore: Normalized quality scores (0.0-1.0)');
  console.log('- MetricType.Cost: Token costs and API expenses');
  console.log('- MetricType.Duration: Execution time tracking');
  console.log('- MetricType.ErrorRate: Error frequency analysis');
  console.log('- MetricType.TaskCompletion: Task completion tracking');
  console.log('- MetricType.Custom: Domain-specific metrics');

  console.log('\nBest Practices:');
  console.log('1. Create one SessionResult per agent invocation');
  console.log('2. Add measurements as they occur (streaming metrics)');
  console.log('3. Set final status (completed/failed) when session ends');
  console.log('4. Use helper functions for common metric types');
  console.log('5. Collect across many sessions for statistical significance');
  console.log('6. Export to JSON for long-term storage and analysis');

  console.log('\nReal-World Applications:');
  console.log('- Monitor agent success rates over time');
  console.log('- Track API costs and token usage');
  console.log('- Identify slow or expensive sessions');
  console.log('- Detect quality degradation');
  console.log('- A/B test different agent configurations');
  console.log('- Generate performance reports and dashboards');
}

main().catch(console.error);

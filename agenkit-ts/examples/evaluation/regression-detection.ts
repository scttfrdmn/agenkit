/**
 * Regression Detection Example
 *
 * Regression detection compares current agent performance to a baseline,
 * alerting when quality degrades beyond acceptable thresholds.
 *
 * This is essential for:
 * - Continuous quality monitoring in production
 * - Catching regressions before deployment
 * - Tracking performance trends over time
 * - Automated quality gates in CI/CD
 *
 * Run with: npx tsx examples/evaluation/regression-detection.ts
 */

import {
  RegressionDetector,
  Severity,
  type Regression,
} from '../../src/evaluation';
import { EvaluationResult } from '../../src/evaluation/core';

/**
 * Create an evaluation result for testing.
 */
function createEvaluationResult(
  id: string,
  accuracy: number,
  quality: number,
  latency: number
): EvaluationResult {
  const result = new EvaluationResult(id, 'production-agent', new Date());
  result.totalTests = 100;
  result.passedTests = Math.floor(accuracy * 100);
  result.failedTests = Math.floor((1 - accuracy) * 100);
  result.accuracy = accuracy;
  result.qualityScore = quality;
  result.avgLatencyMs = latency;
  return result;
}

async function main() {
  console.log('Regression Detection Example');
  console.log('============================\n');

  // Step 1: Establish baseline
  console.log('Step 1: Establishing Baseline Performance');
  console.log('------------------------------------------');
  const baseline = createEvaluationResult('baseline-001', 0.95, 0.92, 150.0);

  console.log('Baseline Metrics:');
  console.log(`  Accuracy: ${(baseline.accuracy! * 100).toFixed(1)}%`);
  console.log(`  Quality: ${baseline.qualityScore!.toFixed(3)}`);
  console.log(`  Latency: ${baseline.avgLatencyMs!.toFixed(0)}ms\n`);

  // Step 2: Create detector
  console.log('Step 2: Creating Regression Detector');
  console.log('-------------------------------------');
  const detector = new RegressionDetector();
  detector.setBaseline(baseline);

  console.log('✓ Detector created with default thresholds:');
  console.log('  Accuracy: 10% degradation');
  console.log('  Quality: 10% degradation');
  console.log('  Latency: 20% increase\n');

  // Step 3: Simulate good performance (no regression)
  console.log('Step 3: Testing Good Performance (No Regression)');
  console.log('------------------------------------------------');
  const goodResult = createEvaluationResult('eval-002', 0.94, 0.91, 155.0);
  let regressions = detector.detect(goodResult);

  console.log('Current Performance:');
  console.log(`  Accuracy: ${(goodResult.accuracy! * 100).toFixed(1)}%`);
  console.log(`  Quality: ${goodResult.qualityScore!.toFixed(3)}`);
  console.log(`  Latency: ${goodResult.avgLatencyMs!.toFixed(0)}ms`);
  console.log(`\nRegressions Detected: ${regressions.length}`);

  if (regressions.length === 0) {
    console.log('✓ Performance within acceptable range\n');
  }

  // Step 4: Simulate moderate regression
  console.log('Step 4: Testing Moderate Degradation');
  console.log('-------------------------------------');
  const moderateResult = createEvaluationResult('eval-003', 0.83, 0.81, 190.0);
  regressions = detector.detect(moderateResult);

  console.log('Current Performance:');
  console.log(`  Accuracy: ${(moderateResult.accuracy! * 100).toFixed(1)}%`);
  console.log(`  Quality: ${moderateResult.qualityScore!.toFixed(3)}`);
  console.log(`  Latency: ${moderateResult.avgLatencyMs!.toFixed(0)}ms`);
  console.log(`\n⚠ Regressions Detected: ${regressions.length}\n`);

  regressions.forEach(reg => {
    console.log(`Regression: ${reg.metricName}`);
    console.log(`  Baseline: ${reg.baselineValue.toFixed(3)}`);
    console.log(`  Current: ${reg.currentValue.toFixed(3)}`);
    console.log(`  Degradation: ${reg.degradationPercent.toFixed(1)}%`);
    console.log(`  Severity: ${reg.severity}\n`);
  });

  // Step 5: Simulate critical regression
  console.log('Step 5: Testing Critical Degradation');
  console.log('-------------------------------------');
  const criticalResult = createEvaluationResult('eval-004', 0.45, 0.42, 350.0);
  regressions = detector.detect(criticalResult);

  console.log('Current Performance:');
  console.log(`  Accuracy: ${(criticalResult.accuracy! * 100).toFixed(1)}%`);
  console.log(`  Quality: ${criticalResult.qualityScore!.toFixed(3)}`);
  console.log(`  Latency: ${criticalResult.avgLatencyMs!.toFixed(0)}ms`);
  console.log(`\n✗ CRITICAL Regressions Detected: ${regressions.length}\n`);

  regressions.forEach(reg => {
    console.log(`Regression: ${reg.metricName}`);
    console.log(`  Baseline: ${reg.baselineValue.toFixed(3)}`);
    console.log(`  Current: ${reg.currentValue.toFixed(3)}`);
    console.log(`  Degradation: ${reg.degradationPercent.toFixed(1)}%`);
    console.log(`  Severity: ${reg.severity}\n`);
  });

  // Step 6: Trend analysis
  console.log('Step 6: Analyzing Performance Trends');
  console.log('-------------------------------------');

  // Add more historical data
  for (let i = 0; i < 10; i++) {
    const accuracy = 0.95 - i * 0.03; // Declining trend
    const quality = 0.92 - i * 0.025;
    const latency = 150.0 + i * 15.0;

    const result = createEvaluationResult(
      `eval-${String(i + 5).padStart(3, '0')}`,
      accuracy,
      quality,
      latency
    );
    detector.detect(result);
  }

  const trend = detector.getTrend('accuracy', 10);
  if (trend) {
    console.log('Accuracy Trend (last 10 evaluations):');
    console.log(`  Direction: ${trend.direction}`);
    console.log(`  Slope: ${trend.slope.toFixed(6)}`);
    console.log(`  Current: ${trend.current.toFixed(3)}`);
    console.log(`  Mean: ${trend.mean.toFixed(3)}`);
    console.log(`  Variance: ${trend.variance.toFixed(6)}\n`);

    if (trend.direction === 'degrading') {
      console.log('⚠ Warning: Accuracy is trending downward');
    }
  }

  // Summary
  console.log('\n' + '='.repeat(70));
  console.log('Summary: Regression Detection');
  console.log('='.repeat(70));

  console.log('\nSeverity Levels:');
  console.log('- None: <10% degradation (within normal variance)');
  console.log('- Minor: 10-20% degradation (monitor closely)');
  console.log('- Moderate: 20-50% degradation (investigate)');
  console.log('- Critical: >50% degradation (immediate action)');

  console.log('\nDetectable Metrics:');
  console.log('- Accuracy: Overall correctness rate');
  console.log('- Quality Score: Multi-dimensional quality assessment');
  console.log('- Latency: Response time (lower is better)');
  console.log('- Error Rate: Frequency of errors');
  console.log('- Custom Metrics: Any numeric metric can be tracked');

  console.log('\nBest Practices:');
  console.log('1. Establish baseline from production data, not test data');
  console.log('2. Set thresholds based on business requirements');
  console.log('3. Run detection after every deployment');
  console.log('4. Track trends over time, not just point-in-time');
  console.log('5. Alert on-call engineers for critical regressions');
  console.log('6. Update baseline periodically as agent improves');

  console.log('\nIntegration with CI/CD:');
  console.log('```typescript');
  console.log('const regressions = detector.detect(result);');
  console.log('for (const reg of regressions) {');
  console.log('  if (reg.severity === Severity.CRITICAL) {');
  console.log('    throw new Error("Critical regression detected, blocking deployment");');
  console.log('  }');
  console.log('}');
  console.log('```');

  console.log('\nCustom Thresholds:');
  console.log('```typescript');
  console.log('const detector = new RegressionDetector({');
  console.log('  accuracy: 0.05,    // 5% degradation threshold');
  console.log('  qualityScore: 0.08, // 8% degradation threshold');
  console.log('  avgLatencyMs: 0.15, // 15% increase threshold');
  console.log('});');
  console.log('```');

  console.log('\nReal-World Applications:');
  console.log('- Pre-deployment Quality Gates: Block releases with regressions');
  console.log('- Production Monitoring: Alert when live performance degrades');
  console.log('- A/B Testing: Ensure new variant doesn\'t regress');
  console.log('- Model Updates: Validate new LLM versions maintain quality');
  console.log('- Prompt Changes: Detect negative impact of prompt modifications');
  console.log('- Infrastructure Changes: Monitor performance after scaling');
}

main().catch(console.error);

/**
 * Tests for regression detection.
 */

import { EvaluationResult } from '../evaluation/core';
import {
  RegressionDetector,
  Severity,
  isRegression,
  regressionToDict,
  Regression,
} from '../evaluation/regression';

// Helper to create test evaluation result
function createResult(overrides: Partial<EvaluationResult>): EvaluationResult {
  return {
    evaluationId: 'test-eval',
    agentName: 'test-agent',
    timestamp: new Date(),
    metrics: {},
    aggregatedMetrics: {},
    totalTests: 10,
    passedTests: 8,
    failedTests: 2,
    metadata: {},
    ...overrides,
  };
}

describe('RegressionDetector', () => {
  let detector: RegressionDetector;

  beforeEach(() => {
    detector = new RegressionDetector();
  });

  test('constructor creates detector', () => {
    expect(detector).toBeDefined();
    expect(detector.getSummary().hasBaseline).toBe(false);
  });

  test('constructor with baseline', () => {
    const baseline = createResult({ accuracy: 0.9 });
    const detector2 = new RegressionDetector({ baseline });

    expect(detector2.getSummary().hasBaseline).toBe(true);
    expect(detector2.getBaseline()).toBe(baseline);
  });

  test('constructor with custom thresholds', () => {
    const detector2 = new RegressionDetector({
      thresholds: { accuracy: 0.05, latency: 0.15 },
    });

    const summary = detector2.getSummary();
    expect(summary.thresholds).toEqual({ accuracy: 0.05, latency: 0.15 });
  });

  test('setBaseline sets baseline', () => {
    const baseline = createResult({ accuracy: 0.9 });
    detector.setBaseline(baseline);

    expect(detector.getSummary().hasBaseline).toBe(true);
    expect(detector.getBaseline()).toBe(baseline);
  });

  test('detect returns empty array without baseline', () => {
    const current = createResult({ accuracy: 0.5 });
    const regressions = detector.detect(current);

    expect(regressions).toHaveLength(0);
  });

  test('detect finds accuracy regression', () => {
    const baseline = createResult({ accuracy: 0.9 });
    const current = createResult({ accuracy: 0.7 }); // 22% drop

    detector.setBaseline(baseline);
    const regressions = detector.detect(current);

    expect(regressions).toHaveLength(1);
    expect(regressions[0].metricName).toBe('accuracy');
    expect(regressions[0].baselineValue).toBe(0.9);
    expect(regressions[0].currentValue).toBe(0.7);
    expect(regressions[0].degradationPercent).toBeCloseTo(22.22, 1);
    expect(regressions[0].severity).toBe(Severity.MODERATE);
  });

  test('detect finds quality regression', () => {
    const baseline = createResult({ qualityScore: 0.8 });
    const current = createResult({ qualityScore: 0.6 }); // 25% drop

    detector.setBaseline(baseline);
    const regressions = detector.detect(current);

    expect(regressions).toHaveLength(1);
    expect(regressions[0].metricName).toBe('quality');
    expect(regressions[0].degradationPercent).toBeCloseTo(25.0, 1);
  });

  test('detect finds latency regression', () => {
    const baseline = createResult({ avgLatencyMs: 100 });
    const current = createResult({ avgLatencyMs: 150 }); // 50% slower

    detector.setBaseline(baseline);
    const regressions = detector.detect(current);

    expect(regressions).toHaveLength(1);
    expect(regressions[0].metricName).toBe('latency');
    expect(regressions[0].degradationPercent).toBe(50.0);
    expect(regressions[0].severity).toBe(Severity.CRITICAL);
  });

  test('detect finds context length regression', () => {
    const baseline = createResult({ contextLength: 1000 });
    const current = createResult({ contextLength: 1500 }); // 50% larger

    detector.setBaseline(baseline);
    const regressions = detector.detect(current);

    expect(regressions).toHaveLength(1);
    expect(regressions[0].metricName).toBe('context_length');
    expect(regressions[0].degradationPercent).toBe(50.0);
  });

  test('detect finds compression ratio regression', () => {
    const baseline = createResult({ compressionRatio: 5.0 });
    const current = createResult({ compressionRatio: 3.0 }); // 40% worse

    detector.setBaseline(baseline);
    const regressions = detector.detect(current);

    expect(regressions).toHaveLength(1);
    expect(regressions[0].metricName).toBe('compression_ratio');
    expect(regressions[0].degradationPercent).toBe(40.0);
  });

  test('detect finds multiple regressions', () => {
    const baseline = createResult({
      accuracy: 0.9,
      qualityScore: 0.8,
      avgLatencyMs: 100,
    });
    const current = createResult({
      accuracy: 0.7, // 22% drop
      qualityScore: 0.6, // 25% drop
      avgLatencyMs: 150, // 50% slower
    });

    detector.setBaseline(baseline);
    const regressions = detector.detect(current);

    expect(regressions).toHaveLength(3);
    expect(regressions.map(r => r.metricName)).toEqual(['accuracy', 'quality', 'latency']);
  });

  test('detect ignores improvements', () => {
    const baseline = createResult({ accuracy: 0.8 });
    const current = createResult({ accuracy: 0.9 }); // Better

    detector.setBaseline(baseline);
    const regressions = detector.detect(current);

    expect(regressions).toHaveLength(0);
  });

  test('detect respects custom thresholds', () => {
    const detector2 = new RegressionDetector({
      thresholds: { accuracy: 0.5 }, // 50% threshold
    });

    const baseline = createResult({ accuracy: 0.9 });
    const current = createResult({ accuracy: 0.7 }); // 22% drop (below threshold)

    detector2.setBaseline(baseline);
    const regressions = detector2.detect(current);

    expect(regressions).toHaveLength(0);
  });

  test('detect stores history', () => {
    const baseline = createResult({ accuracy: 0.9 });
    const current = createResult({ accuracy: 0.8 });

    detector.setBaseline(baseline);
    detector.detect(current, true);

    expect(detector.getHistory()).toHaveLength(1);
    expect(detector.getHistory()[0]).toBe(current);
  });

  test('detect skips history storage when requested', () => {
    const baseline = createResult({ accuracy: 0.9 });
    const current = createResult({ accuracy: 0.8 });

    detector.setBaseline(baseline);
    detector.detect(current, false);

    expect(detector.getHistory()).toHaveLength(0);
  });

  test('severity calculation', () => {
    const baseline = createResult({ accuracy: 1.0 });

    detector.setBaseline(baseline);

    // Minor: 5% drop
    let regressions = detector.detect(createResult({ accuracy: 0.95 }));
    expect(regressions).toHaveLength(0); // Below 10% threshold

    // Minor: 15% drop
    regressions = detector.detect(createResult({ accuracy: 0.85 }));
    expect(regressions[0].severity).toBe(Severity.MINOR);

    // Moderate: 35% drop
    regressions = detector.detect(createResult({ accuracy: 0.65 }));
    expect(regressions[0].severity).toBe(Severity.MODERATE);

    // Critical: 60% drop
    regressions = detector.detect(createResult({ accuracy: 0.40 }));
    expect(regressions[0].severity).toBe(Severity.CRITICAL);
  });

  test('regression context includes metadata', () => {
    const baseline = createResult({ accuracy: 0.9 });
    const current = createResult({ accuracy: 0.7 });

    detector.setBaseline(baseline);
    const regressions = detector.detect(current);

    expect(regressions[0].context.thresholdPercent).toBe(10);
    expect(regressions[0].context.higherIsBetter).toBe(true);
  });

  test('regression has timestamp', () => {
    const baseline = createResult({ accuracy: 0.9 });
    const current = createResult({ accuracy: 0.7 });

    detector.setBaseline(baseline);
    const regressions = detector.detect(current);

    expect(regressions[0].timestamp).toBeInstanceOf(Date);
  });
});

describe('RegressionDetector.getTrend', () => {
  let detector: RegressionDetector;

  beforeEach(() => {
    detector = new RegressionDetector();
  });

  test('returns null with insufficient history', () => {
    const trend = detector.getTrend('accuracy');
    expect(trend).toBeNull();

    detector.detect(createResult({ accuracy: 0.9 }), true);
    const trend2 = detector.getTrend('accuracy');
    expect(trend2).toBeNull(); // Need at least 2 points
  });

  test('calculates improving trend', () => {
    const baseline = createResult({ accuracy: 0.9 });
    detector.setBaseline(baseline);

    // Improving trend: 0.8 -> 0.85 -> 0.9
    detector.detect(createResult({ accuracy: 0.8 }), true);
    detector.detect(createResult({ accuracy: 0.85 }), true);
    detector.detect(createResult({ accuracy: 0.9 }), true);

    const trend = detector.getTrend('accuracy');

    expect(trend).toBeDefined();
    expect(trend!.metric).toBe('accuracy');
    expect(trend!.direction).toBe('improving');
    expect(trend!.slope).toBeGreaterThan(0);
    expect(trend!.current).toBe(0.9);
    expect(trend!.windowSize).toBe(3);
  });

  test('calculates degrading trend', () => {
    const baseline = createResult({ accuracy: 0.9 });
    detector.setBaseline(baseline);

    // Degrading trend: 0.9 -> 0.85 -> 0.8
    detector.detect(createResult({ accuracy: 0.9 }), true);
    detector.detect(createResult({ accuracy: 0.85 }), true);
    detector.detect(createResult({ accuracy: 0.8 }), true);

    const trend = detector.getTrend('accuracy');

    expect(trend).toBeDefined();
    expect(trend!.direction).toBe('degrading');
    expect(trend!.slope).toBeLessThan(0);
  });

  test('calculates stable trend', () => {
    const baseline = createResult({ accuracy: 0.9 });
    detector.setBaseline(baseline);

    // Stable trend: 0.9 -> 0.9 -> 0.9
    detector.detect(createResult({ accuracy: 0.9 }), true);
    detector.detect(createResult({ accuracy: 0.9 }), true);
    detector.detect(createResult({ accuracy: 0.9 }), true);

    const trend = detector.getTrend('accuracy');

    expect(trend).toBeDefined();
    expect(trend!.direction).toBe('stable');
    expect(trend!.slope).toBe(0);
    expect(trend!.variance).toBe(0);
  });

  test('respects window parameter', () => {
    const baseline = createResult({ accuracy: 0.9 });
    detector.setBaseline(baseline);

    // Add 10 results
    for (let i = 0; i < 10; i++) {
      detector.detect(createResult({ accuracy: 0.8 + i * 0.01 }), true);
    }

    const trend = detector.getTrend('accuracy', 5);

    expect(trend).toBeDefined();
    expect(trend!.windowSize).toBe(5);
  });

  test('calculates variance correctly', () => {
    const baseline = createResult({ accuracy: 0.9 });
    detector.setBaseline(baseline);

    detector.detect(createResult({ accuracy: 0.8 }), true);
    detector.detect(createResult({ accuracy: 0.9 }), true);
    detector.detect(createResult({ accuracy: 0.7 }), true);

    const trend = detector.getTrend('accuracy');

    expect(trend).toBeDefined();
    expect(trend!.variance).toBeGreaterThan(0);
  });

  test('works with different metrics', () => {
    const baseline = createResult({ qualityScore: 0.9 });
    detector.setBaseline(baseline);

    detector.detect(createResult({ qualityScore: 0.8 }), true);
    detector.detect(createResult({ qualityScore: 0.85 }), true);

    const trend = detector.getTrend('quality');

    expect(trend).toBeDefined();
    expect(trend!.metric).toBe('quality');
  });

  test('returns null for metric with no values', () => {
    const baseline = createResult({ accuracy: 0.9 });
    detector.setBaseline(baseline);

    detector.detect(createResult({ accuracy: 0.8 }), true);
    detector.detect(createResult({ accuracy: 0.85 }), true);

    // Request trend for latency (no data)
    const trend = detector.getTrend('latency');

    expect(trend).toBeNull();
  });
});

describe('RegressionDetector.compareResults', () => {
  let detector: RegressionDetector;

  beforeEach(() => {
    detector = new RegressionDetector();
  });

  test('compares accuracy', () => {
    const resultA = createResult({ accuracy: 0.9 });
    const resultB = createResult({ accuracy: 0.8 });

    const comparison = detector.compareResults(resultA, resultB);

    expect(comparison.accuracy).toBeDefined();
    expect(comparison.accuracy.baseline).toBe(0.9);
    expect(comparison.accuracy.current).toBe(0.8);
    expect(comparison.accuracy.change).toBeCloseTo(-0.1, 2);
    expect(comparison.accuracy.changePercent).toBeCloseTo(-11.11, 1);
  });

  test('compares quality', () => {
    const resultA = createResult({ qualityScore: 0.8 });
    const resultB = createResult({ qualityScore: 0.9 });

    const comparison = detector.compareResults(resultA, resultB);

    expect(comparison.quality).toBeDefined();
    expect(comparison.quality.change).toBeCloseTo(0.1, 2);
    expect(comparison.quality.changePercent).toBeCloseTo(12.5, 1);
  });

  test('compares latency', () => {
    const resultA = createResult({ avgLatencyMs: 100 });
    const resultB = createResult({ avgLatencyMs: 150 });

    const comparison = detector.compareResults(resultA, resultB);

    expect(comparison.latency).toBeDefined();
    expect(comparison.latency.change).toBe(50);
    expect(comparison.latency.changePercent).toBe(50);
  });

  test('compares multiple metrics', () => {
    const resultA = createResult({
      accuracy: 0.9,
      qualityScore: 0.8,
      avgLatencyMs: 100,
    });
    const resultB = createResult({
      accuracy: 0.85,
      qualityScore: 0.75,
      avgLatencyMs: 120,
    });

    const comparison = detector.compareResults(resultA, resultB);

    expect(Object.keys(comparison)).toHaveLength(3);
    expect(comparison.accuracy).toBeDefined();
    expect(comparison.quality).toBeDefined();
    expect(comparison.latency).toBeDefined();
  });

  test('handles zero baseline gracefully', () => {
    const resultA = createResult({ accuracy: 0 });
    const resultB = createResult({ accuracy: 0.5 });

    const comparison = detector.compareResults(resultA, resultB);

    expect(comparison.accuracy.changePercent).toBe(0);
  });

  test('skips undefined metrics', () => {
    const resultA = createResult({ accuracy: 0.9 });
    const resultB = createResult({}); // No accuracy

    const comparison = detector.compareResults(resultA, resultB);

    expect(comparison.accuracy).toBeUndefined();
  });
});

describe('RegressionDetector.clearHistory', () => {
  test('clears history', () => {
    const detector = new RegressionDetector();
    const baseline = createResult({ accuracy: 0.9 });

    detector.setBaseline(baseline);
    detector.detect(createResult({ accuracy: 0.8 }), true);
    detector.detect(createResult({ accuracy: 0.85 }), true);

    expect(detector.getHistory()).toHaveLength(2);

    detector.clearHistory();

    expect(detector.getHistory()).toHaveLength(0);
  });
});

describe('RegressionDetector.getSummary', () => {
  test('returns summary without baseline', () => {
    const detector = new RegressionDetector();
    const summary = detector.getSummary();

    expect(summary.hasBaseline).toBe(false);
    expect(summary.baselineId).toBeNull();
    expect(summary.historyCount).toBe(0);
    expect(summary.thresholds).toBeDefined();
  });

  test('returns summary with baseline', () => {
    const detector = new RegressionDetector();
    const baseline = createResult({ evaluationId: 'baseline-123', accuracy: 0.9 });

    detector.setBaseline(baseline);
    detector.detect(createResult({ accuracy: 0.8 }), true);

    const summary = detector.getSummary();

    expect(summary.hasBaseline).toBe(true);
    expect(summary.baselineId).toBe('baseline-123');
    expect(summary.historyCount).toBe(1);
  });
});

describe('Helper functions', () => {
  test('isRegression checks degradation', () => {
    const regression: Regression = {
      metricName: 'accuracy',
      baselineValue: 0.9,
      currentValue: 0.7,
      degradationPercent: 22.22,
      severity: Severity.MODERATE,
      timestamp: new Date(),
      context: {},
    };

    expect(isRegression(regression)).toBe(true);

    const improvement: Regression = {
      ...regression,
      degradationPercent: -10, // Negative = improvement
    };

    expect(isRegression(improvement)).toBe(false);
  });

  test('regressionToDict converts to plain object', () => {
    const regression: Regression = {
      metricName: 'accuracy',
      baselineValue: 0.9,
      currentValue: 0.7,
      degradationPercent: 22.22,
      severity: Severity.MODERATE,
      timestamp: new Date('2025-01-01T00:00:00Z'),
      context: { foo: 'bar' },
    };

    const dict = regressionToDict(regression);

    expect(dict.metric_name).toBe('accuracy');
    expect(dict.baseline_value).toBe(0.9);
    expect(dict.current_value).toBe(0.7);
    expect(dict.degradation_percent).toBe(22.22);
    expect(dict.severity).toBe('moderate');
    expect(dict.timestamp).toBe('2025-01-01T00:00:00.000Z');
    expect(dict.context).toEqual({ foo: 'bar' });
  });
});

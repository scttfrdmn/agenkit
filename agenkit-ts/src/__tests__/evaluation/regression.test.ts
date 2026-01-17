/**
 * Tests for regression detection.
 *
 * Tests RegressionDetector, Regression, and Severity tracking.
 */

import { describe, it, expect } from 'vitest';
import {
  RegressionDetector,
  Regression,
  Severity,
  DetectionConfig,
} from '../../evaluation/regression';
import type { EvaluationResult } from '../../evaluation/core';

// Helper to create evaluation result
function createEvalResult(
  score: number,
  timestamp: Date = new Date()
): EvaluationResult {
  return {
    evaluationId: 'test',
    agentName: 'test-agent',
    timestamp: timestamp.toISOString(),
    totalTests: 10,
    passedTests: Math.round(score * 10),
    failedTests: 10 - Math.round(score * 10),
    score,
    metadata: {},
  };
}

// ============================================
// RegressionDetector Basic Tests
// ============================================

describe('RegressionDetector: Basic Detection', () => {
  it('should detect significant regression', () => {
    const detector = new RegressionDetector();

    const baseline = createEvalResult(0.9);
    const current = createEvalResult(0.5);

    const regression = detector.detect(baseline, current);

    expect(regression).not.toBeNull();
    expect(regression?.severity).toBe(Severity.Critical);
  });

  it('should not detect when performance improves', () => {
    const detector = new RegressionDetector();

    const baseline = createEvalResult(0.7);
    const current = createEvalResult(0.9);

    const regression = detector.detect(baseline, current);

    expect(regression).toBeNull();
  });

  it('should not detect minor fluctuations', () => {
    const detector = new RegressionDetector();

    const baseline = createEvalResult(0.8);
    const current = createEvalResult(0.78); // Only 2% drop

    const regression = detector.detect(baseline, current);

    expect(regression).toBeNull(); // Below default 5% threshold
  });

  it('should use custom threshold', () => {
    const config: DetectionConfig = {
      minRegressionThreshold: 0.1, // 10% threshold
    };
    const detector = new RegressionDetector(config);

    const baseline = createEvalResult(0.8);
    const current = createEvalResult(0.72); // 8% drop

    const regression = detector.detect(baseline, current);

    expect(regression).toBeNull(); // Below 10% threshold
  });
});

// ============================================
// Severity Classification Tests
// ============================================

describe('RegressionDetector: Severity', () => {
  it('should classify critical regression', () => {
    const detector = new RegressionDetector();

    const baseline = createEvalResult(0.9);
    const current = createEvalResult(0.4); // 50% drop

    const regression = detector.detect(baseline, current);

    expect(regression?.severity).toBe(Severity.Critical);
  });

  it('should classify major regression', () => {
    const detector = new RegressionDetector();

    const baseline = createEvalResult(0.8);
    const current = createEvalResult(0.6); // 20% drop

    const regression = detector.detect(baseline, current);

    expect(regression?.severity).toBe(Severity.Major);
  });

  it('should classify minor regression', () => {
    const detector = new RegressionDetector();

    const baseline = createEvalResult(0.8);
    const current = createEvalResult(0.73); // 7% drop

    const regression = detector.detect(baseline, current);

    expect(regression?.severity).toBe(Severity.Minor);
  });

  it('should use custom severity thresholds', () => {
    const config: DetectionConfig = {
      minRegressionThreshold: 0.05,
      minorThreshold: 0.15,
      majorThreshold: 0.30,
    };
    const detector = new RegressionDetector(config);

    const baseline = createEvalResult(0.8);
    const current = createEvalResult(0.64); // 16% drop

    const regression = detector.detect(baseline, current);

    expect(regression?.severity).toBe(Severity.Major);
  });
});

// ============================================
// History Tracking Tests
// ============================================

describe('RegressionDetector: History', () => {
  it('should track historical results', () => {
    const detector = new RegressionDetector();

    const result1 = createEvalResult(0.8, new Date('2024-01-01'));
    const result2 = createEvalResult(0.85, new Date('2024-01-02'));
    const result3 = createEvalResult(0.7, new Date('2024-01-03'));

    detector.addResult(result1);
    detector.addResult(result2);
    detector.addResult(result3);

    const history = detector.getHistory();

    expect(history).toHaveLength(3);
    expect(history[0].score).toBe(0.8);
  });

  it('should detect regression from historical trend', () => {
    const detector = new RegressionDetector();

    // Establish upward trend
    detector.addResult(createEvalResult(0.7));
    detector.addResult(createEvalResult(0.75));
    detector.addResult(createEvalResult(0.8));

    // Sudden drop
    const current = createEvalResult(0.6);

    const regressions = detector.detectFromHistory(current);

    expect(regressions.length).toBeGreaterThan(0);
  });

  it('should clear history', () => {
    const detector = new RegressionDetector();

    detector.addResult(createEvalResult(0.8));
    detector.addResult(createEvalResult(0.85));

    expect(detector.getHistory()).toHaveLength(2);

    detector.clearHistory();

    expect(detector.getHistory()).toHaveLength(0);
  });
});

// ============================================
// Regression Object Tests
// ============================================

describe('Regression', () => {
  it('should create regression with details', () => {
    const baseline = createEvalResult(0.9);
    const current = createEvalResult(0.6);

    const regression = new Regression({
      baselineScore: baseline.score,
      currentScore: current.score,
      severity: Severity.Critical,
      timestamp: new Date(),
      details: { metric: 'accuracy' },
    });

    expect(regression.baselineScore).toBe(0.9);
    expect(regression.currentScore).toBe(0.6);
    expect(regression.severity).toBe(Severity.Critical);
  });

  it('should calculate delta', () => {
    const regression = new Regression({
      baselineScore: 0.8,
      currentScore: 0.6,
      severity: Severity.Major,
      timestamp: new Date(),
    });

    expect(regression.delta).toBe(-0.2);
  });

  it('should calculate percent change', () => {
    const regression = new Regression({
      baselineScore: 0.8,
      currentScore: 0.6,
      severity: Severity.Major,
      timestamp: new Date(),
    });

    expect(regression.percentChange).toBeCloseTo(-25, 0);
  });
});

// ============================================
// Advanced Detection Tests
// ============================================

describe('RegressionDetector: Advanced', () => {
  it('should detect sustained regression', () => {
    const detector = new RegressionDetector();

    // Good baseline
    detector.addResult(createEvalResult(0.85));

    // Sustained drop
    detector.addResult(createEvalResult(0.7));
    detector.addResult(createEvalResult(0.68));
    const current = createEvalResult(0.69);

    const regressions = detector.detectFromHistory(current);

    // Should detect regression from baseline
    expect(regressions.length).toBeGreaterThan(0);
  });

  it('should handle noisy data', () => {
    const detector = new RegressionDetector();

    // Noisy but stable trend
    detector.addResult(createEvalResult(0.78));
    detector.addResult(createEvalResult(0.82));
    detector.addResult(createEvalResult(0.79));
    detector.addResult(createEvalResult(0.81));

    const current = createEvalResult(0.80);

    const regressions = detector.detectFromHistory(current);

    // Should not detect regression (within noise)
    expect(regressions).toHaveLength(0);
  });

  it('should support metric-specific detection', () => {
    const config: DetectionConfig = {
      minRegressionThreshold: 0.1,
      metricName: 'accuracy',
    };
    const detector = new RegressionDetector(config);

    const baseline = createEvalResult(0.9);
    const current = createEvalResult(0.75); // 15% drop

    const regression = detector.detect(baseline, current);

    expect(regression).not.toBeNull();
    expect(regression?.details?.metricName).toBe('accuracy');
  });
});

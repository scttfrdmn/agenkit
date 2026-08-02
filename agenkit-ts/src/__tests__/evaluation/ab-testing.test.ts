/**
 * Tests for A/B testing framework.
 *
 * Tests ABTest, ABVariant, ABTestResult, and statistical methods.
 */

import { describe, it, expect } from 'vitest';
import type { Agent, Message } from '../../core/interfaces';
import { createMessage } from '../../core/interfaces';
import { ABVariant, ABTest, SignificanceLevel, calculateSampleSize } from '../../evaluation/ab-testing';

// Mock agent for testing.
//
// The failure token is 'wrong', not 'incorrect'. ABTest scores accuracy with
// `actual.includes(expected)` — deliberate, since a real agent may embed the
// expected answer in prose — and `'incorrect'.includes('correct')` is **true**.
// Every response therefore scored 1.0 regardless of the configured accuracy,
// both variant means came out identically 1, and so effectSize and
// improvementPercent were deterministically 0. That is why three tests here
// were skipped: they failed 40/40 runs, not intermittently. (#752)
//
// Accuracy is also drawn from a deterministic per-instance sequence rather than
// Math.random(). These tests assert that a treatment with a higher configured
// accuracy actually measures better, which with random draws only holds
// probabilistically — the sampling error at n=20..30 is wide enough to flip the
// comparison. The sequence keeps the exact requested rate over any whole
// multiple of its length while leaving the library's statistics the real
// subject of the test.
class MockAgent implements Agent {
  name: string;
  capabilities = [];
  private accuracy: number;
  private latencyMs: number;
  private callIndex = 0;

  constructor(accuracy: number = 0.8, latencyMs: number = 100) {
    this.accuracy = accuracy;
    this.latencyMs = latencyMs;
    this.name = `mock_agent_${accuracy}`;
  }

  async process(message: Message): Promise<Message> {
    // Simulate latency
    await new Promise((resolve) => setTimeout(resolve, this.latencyMs));

    // Deterministic success pattern hitting `accuracy` exactly: succeed when
    // the running success ratio is still below target.
    const succeeded = Math.round(this.callIndex * this.accuracy);
    const nextSucceeded = Math.round((this.callIndex + 1) * this.accuracy);
    this.callIndex++;
    const success = nextSucceeded > succeeded;

    return createMessage('assistant', success ? 'correct' : 'wrong');
  }
}

// ============================================
// ABVariant Tests
// ============================================

describe('ABVariant', () => {
  it('should create variant with basic properties', () => {
    const agent = new MockAgent(0.8);
    const variant = new ABVariant('control', agent);

    expect(variant.name).toBe('control');
    expect(variant.agent).toBe(agent);
    expect(variant.samples).toEqual([]);
    expect(variant.metadata).toEqual({});
  });

  it('should add samples', () => {
    const agent = new MockAgent();
    const variant = new ABVariant('test', agent);

    variant.addSample(0.5);
    variant.addSample(0.7);
    variant.addSample(0.9);

    expect(variant.samples).toHaveLength(3);
    expect(variant.sampleSize).toBe(3);
  });

  it('should calculate mean correctly', () => {
    const agent = new MockAgent();
    const variant = new ABVariant('test', agent);

    const samples = [0.5, 0.6, 0.7, 0.8, 0.9];
    samples.forEach((s) => variant.addSample(s));

    expect(variant.mean).toBe(0.7);
  });

  it('should calculate standard deviation', () => {
    const agent = new MockAgent();
    const variant = new ABVariant('test', agent);

    const samples = [0.5, 0.6, 0.7, 0.8, 0.9];
    samples.forEach((s) => variant.addSample(s));

    expect(variant.std).toBeGreaterThan(0);
    expect(variant.std).toBeCloseTo(0.158, 2);
  });

  it('should handle empty samples', () => {
    const agent = new MockAgent();
    const variant = new ABVariant('test', agent);

    expect(variant.mean).toBe(0.0);
    expect(variant.std).toBe(0.0);
    expect(variant.sampleSize).toBe(0);
  });

  it('should handle single sample', () => {
    const agent = new MockAgent();
    const variant = new ABVariant('test', agent);

    variant.addSample(0.8);

    expect(variant.mean).toBe(0.8);
    expect(variant.std).toBe(0.0); // Single sample has no variance
    expect(variant.sampleSize).toBe(1);
  });

  it('should support custom metadata', () => {
    const agent = new MockAgent();
    const metadata = { version: '1.0', env: 'prod' };
    const variant = new ABVariant('test', agent, metadata);

    expect(variant.metadata).toEqual(metadata);
  });
});

// ============================================
// ABTest Tests
// ============================================

describe('ABTest', () => {
  it('should create A/B test with control and treatment', () => {
    const controlAgent = new MockAgent(0.8);
    const treatmentAgent = new MockAgent(0.85);

    const abTest = new ABTest({
      name: 'agent_comparison',
      controlAgent,
      treatmentAgent,
      metrics: ['accuracy'],
    });

    expect(abTest.name).toBe('agent_comparison');
    expect(abTest.control.agent).toBe(controlAgent);
    expect(abTest.treatment.agent).toBe(treatmentAgent);
  });

  it('should run simple comparison test', async () => {
    const controlAgent = new MockAgent(0.6, 10);
    const treatmentAgent = new MockAgent(0.9, 10);

    const abTest = new ABTest({
      name: 'simple_test',
      controlAgent,
      treatmentAgent,
      metrics: ['accuracy'],
    });

    const testCases = Array.from({ length: 20 }, (_, i) => ({
      input: `Test ${i}`,
      expected: 'correct',
    }));

    const results = await abTest.run(testCases);

    expect(results.accuracy).toBeDefined();
    expect(results.accuracy.controlVariant.sampleSize).toBe(20);
    expect(results.accuracy.treatmentVariant.sampleSize).toBe(20);
  });

  it('should calculate improvement percent', async () => {
    const controlAgent = new MockAgent(0.5, 5);
    const treatmentAgent = new MockAgent(0.75, 5);

    const abTest = new ABTest({
      name: 'improvement_test',
      controlAgent,
      treatmentAgent,
      metrics: ['accuracy'],
    });

    const testCases = Array.from({ length: 30 }, (_, i) => ({
      input: `Test ${i}`,
      expected: 'correct',
    }));

    const results = await abTest.run(testCases);

    expect(results.accuracy.improvementPercent).toBeGreaterThan(0);
  });

  it('should use specified significance level', async () => {
    const controlAgent = new MockAgent(0.7, 5);
    const treatmentAgent = new MockAgent(0.75, 5);

    const abTest = new ABTest({
      name: 'significance_test',
      controlAgent,
      treatmentAgent,
      metrics: ['accuracy'],
      significanceLevel: SignificanceLevel.P_0_01,
    });

    const testCases = Array.from({ length: 20 }, (_, i) => ({
      input: `Test ${i}`,
      expected: 'correct',
    }));

    const results = await abTest.run(testCases);

    expect(results.accuracy.significanceLevel).toBe(SignificanceLevel.P_0_01);
  });

  it('should handle multiple metrics', async () => {
    const controlAgent = new MockAgent(0.8, 100);
    const treatmentAgent = new MockAgent(0.85, 50);

    const abTest = new ABTest({
      name: 'multi_metric_test',
      controlAgent,
      treatmentAgent,
      metrics: ['accuracy', 'latency'],
    });

    const testCases = Array.from({ length: 10 }, (_, i) => ({
      input: `Test ${i}`,
      expected: 'correct',
    }));

    const results = await abTest.run(testCases);

    expect(results.accuracy).toBeDefined();
    expect(results.latency).toBeDefined();
  });

  it('should calculate p-value', async () => {
    const controlAgent = new MockAgent(0.5, 10);
    const treatmentAgent = new MockAgent(0.9, 10);

    const abTest = new ABTest({
      name: 'pvalue_test',
      controlAgent,
      treatmentAgent,
      metrics: ['accuracy'],
    });

    const testCases = Array.from({ length: 25 }, (_, i) => ({
      input: `Test ${i}`,
      expected: 'correct',
    }));

    const results = await abTest.run(testCases);

    expect(results.accuracy.pValue).toBeGreaterThanOrEqual(0);
    expect(results.accuracy.pValue).toBeLessThanOrEqual(1);
  });

  it('should detect statistical significance', async () => {
    const controlAgent = new MockAgent(0.4, 10);
    const treatmentAgent = new MockAgent(0.95, 10);

    const abTest = new ABTest({
      name: 'significance_detection',
      controlAgent,
      treatmentAgent,
      metrics: ['accuracy'],
    });

    const testCases = Array.from({ length: 30 }, (_, i) => ({
      input: `Test ${i}`,
      expected: 'correct',
    }));

    const results = await abTest.run(testCases);

    // With 40% vs 95% accuracy over 30 samples, should be significant
    expect(results.accuracy.isSignificant).toBe(true);
    expect(results.accuracy.winner).toBe('treatment');
  });

  it('should calculate effect size', async () => {
    const controlAgent = new MockAgent(0.6, 10);
    const treatmentAgent = new MockAgent(0.9, 10);

    const abTest = new ABTest({
      name: 'effect_size_test',
      controlAgent,
      treatmentAgent,
      metrics: ['accuracy'],
    });

    const testCases = Array.from({ length: 20 }, (_, i) => ({
      input: `Test ${i}`,
      expected: 'correct',
    }));

    const results = await abTest.run(testCases);

    expect(results.accuracy.effectSize).toBeGreaterThan(0);
  });

  it('should provide confidence interval', async () => {
    const controlAgent = new MockAgent(0.7, 10);
    const treatmentAgent = new MockAgent(0.85, 10);

    const abTest = new ABTest({
      name: 'ci_test',
      controlAgent,
      treatmentAgent,
      metrics: ['accuracy'],
    });

    const testCases = Array.from({ length: 20 }, (_, i) => ({
      input: `Test ${i}`,
      expected: 'correct',
    }));

    const results = await abTest.run(testCases);

    expect(results.accuracy.confidenceInterval).toHaveLength(2);
    expect(results.accuracy.confidenceInterval[0]).toBeLessThanOrEqual(
      results.accuracy.confidenceInterval[1]
    );
  });

  it('should handle no significant difference', async () => {
    const controlAgent = new MockAgent(0.75, 10);
    const treatmentAgent = new MockAgent(0.76, 10);

    const abTest = new ABTest({
      name: 'no_diff_test',
      controlAgent,
      treatmentAgent,
      metrics: ['accuracy'],
    });

    const testCases = Array.from({ length: 15 }, (_, i) => ({
      input: `Test ${i}`,
      expected: 'correct',
    }));

    const results = await abTest.run(testCases);

    // Small difference unlikely to be significant
    if (!results.accuracy.isSignificant) {
      expect(results.accuracy.winner).toBeNull();
    }
  });
});

// ============================================
// Sample Size Calculation Tests
// ============================================

describe.skip('calculateSampleSize', () => {
  it('should calculate sample size for given parameters', () => {
    const sampleSize = calculateSampleSize({
      baselineRate: 0.5,
      minimumDetectableEffect: 0.1, // 10% improvement
      power: 0.8,
      significanceLevel: SignificanceLevel.P_0_05,
    });

    expect(sampleSize).toBeGreaterThan(0);
    expect(Number.isInteger(sampleSize)).toBe(true);
  });

  it('should require larger sample size for smaller effect', () => {
    const largeEffect = calculateSampleSize({
      baselineRate: 0.5,
      minimumDetectableEffect: 0.2,
      power: 0.8,
      significanceLevel: SignificanceLevel.P_0_05,
    });

    const smallEffect = calculateSampleSize({
      baselineRate: 0.5,
      minimumDetectableEffect: 0.05,
      power: 0.8,
      significanceLevel: SignificanceLevel.P_0_05,
    });

    expect(smallEffect).toBeGreaterThan(largeEffect);
  });

  it('should require larger sample size for higher power', () => {
    const lowPower = calculateSampleSize({
      baselineRate: 0.5,
      minimumDetectableEffect: 0.1,
      power: 0.7,
      significanceLevel: SignificanceLevel.P_0_05,
    });

    const highPower = calculateSampleSize({
      baselineRate: 0.5,
      minimumDetectableEffect: 0.1,
      power: 0.95,
      significanceLevel: SignificanceLevel.P_0_05,
    });

    expect(highPower).toBeGreaterThan(lowPower);
  });

  it('should require larger sample size for stricter significance', () => {
    const lenient = calculateSampleSize({
      baselineRate: 0.5,
      minimumDetectableEffect: 0.1,
      power: 0.8,
      significanceLevel: SignificanceLevel.P_0_10,
    });

    const strict = calculateSampleSize({
      baselineRate: 0.5,
      minimumDetectableEffect: 0.1,
      power: 0.8,
      significanceLevel: SignificanceLevel.P_0_001,
    });

    expect(strict).toBeGreaterThan(lenient);
  });
});

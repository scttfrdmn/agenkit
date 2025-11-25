/**
 * Tests for A/B Testing framework.
 */

import {
  ABTest,
  ABVariant,
  SignificanceLevel,
  TestCase,
} from '../evaluation/ab-testing';
import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Mock agent for testing.
 */
class MockAgent implements Agent {
  readonly name: string;
  private response: string;
  private delay: number;

  constructor(name: string, response: string, delay: number = 0) {
    this.name = name;
    this.response = response;
    this.delay = delay;
  }

  async process(message: Message): Promise<Message> {
    if (this.delay > 0) {
      await new Promise(resolve => setTimeout(resolve, this.delay));
    }
    return createMessage('assistant', this.response);
  }
}

describe('ABVariant', () => {
  it('should create variant', () => {
    const agent = new MockAgent('test', 'response');
    const variant = new ABVariant('control', agent);

    expect(variant.name).toBe('control');
    expect(variant.agent).toBe(agent);
    expect(variant.samples).toEqual([]);
  });

  it('should add samples', () => {
    const agent = new MockAgent('test', 'response');
    const variant = new ABVariant('control', agent);

    variant.addSample(0.8);
    variant.addSample(0.9);
    variant.addSample(0.85);

    expect(variant.samples).toEqual([0.8, 0.9, 0.85]);
  });

  it('should calculate statistics', () => {
    const agent = new MockAgent('test', 'response');
    const variant = new ABVariant('control', agent);

    variant.addSample(0.8);
    variant.addSample(0.9);
    variant.addSample(0.85);

    expect(variant.mean).toBeCloseTo(0.85, 5);
    expect(variant.std).toBeGreaterThan(0);
    expect(variant.sampleSize).toBe(3);
  });

  it('should handle empty samples', () => {
    const agent = new MockAgent('test', 'response');
    const variant = new ABVariant('control', agent);

    expect(variant.mean).toBe(0.0);
    expect(variant.std).toBe(0.0);
    expect(variant.sampleSize).toBe(0);
  });

  it('should handle single sample', () => {
    const agent = new MockAgent('test', 'response');
    const variant = new ABVariant('control', agent);

    variant.addSample(0.75);

    expect(variant.mean).toBe(0.75);
    expect(variant.std).toBe(0.0); // STD requires at least 2 samples
    expect(variant.sampleSize).toBe(1);
  });
});

describe('ABTest', () => {
  describe('Configuration', () => {
    it('should create test with defaults', () => {
      const controlAgent = new MockAgent('control', 'baseline');
      const treatmentAgent = new MockAgent('treatment', 'optimized');

      const test = new ABTest({
        name: 'test_experiment',
        controlAgent,
        treatmentAgent,
      });

      expect(test.name).toBe('test_experiment');
      expect(test.metrics).toEqual(['accuracy']);
      expect(test.significanceLevel).toBe(SignificanceLevel.P_0_05);
    });

    it('should use custom configuration', () => {
      const controlAgent = new MockAgent('control', 'baseline');
      const treatmentAgent = new MockAgent('treatment', 'optimized');

      const test = new ABTest({
        name: 'custom_experiment',
        controlAgent,
        treatmentAgent,
        metrics: ['accuracy', 'latency'],
        significanceLevel: SignificanceLevel.P_0_01,
      });

      expect(test.metrics).toEqual(['accuracy', 'latency']);
      expect(test.significanceLevel).toBe(SignificanceLevel.P_0_01);
    });
  });

  describe('Basic Execution', () => {
    it('should run test and return results', async () => {
      const controlAgent = new MockAgent('control', 'correct answer');
      const treatmentAgent = new MockAgent('treatment', 'correct answer');

      const test = new ABTest({
        name: 'basic_test',
        controlAgent,
        treatmentAgent,
      });

      const testCases: TestCase[] = [
        { input: 'question 1', expected: 'correct answer' },
        { input: 'question 2', expected: 'correct answer' },
        { input: 'question 3', expected: 'correct answer' },
      ];

      const results = await test.run(testCases, { shuffle: false });

      expect(results.accuracy).toBeDefined();
      expect(results.accuracy.controlVariant.sampleSize).toBe(3);
      expect(results.accuracy.treatmentVariant.sampleSize).toBe(3);
    });

    it('should calculate accuracy correctly', async () => {
      const controlAgent = new MockAgent('control', 'correct');
      const treatmentAgent = new MockAgent('treatment', 'correct');

      const test = new ABTest({
        name: 'accuracy_test',
        controlAgent,
        treatmentAgent,
      });

      const testCases: TestCase[] = [
        { input: 'q1', expected: 'correct' },
        { input: 'q2', expected: 'correct' },
      ];

      const results = await test.run(testCases, { shuffle: false });

      expect(results.accuracy.controlVariant.mean).toBe(1.0);
      expect(results.accuracy.treatmentVariant.mean).toBe(1.0);
    });

    it('should calculate latency', async () => {
      const fastAgent = new MockAgent('fast', 'answer', 10);
      const slowAgent = new MockAgent('slow', 'answer', 50);

      const test = new ABTest({
        name: 'latency_test',
        controlAgent: fastAgent,
        treatmentAgent: slowAgent,
        metrics: ['latencyMs'],
      });

      const testCases: TestCase[] = [{ input: 'question', expected: 'answer' }];

      const results = await test.run(testCases, { shuffle: false });

      expect(results.latencyMs.controlVariant.mean).toBeLessThan(
        results.latencyMs.treatmentVariant.mean
      );
    });

    it('should handle sample size limit', async () => {
      const controlAgent = new MockAgent('control', 'answer');
      const treatmentAgent = new MockAgent('treatment', 'answer');

      const test = new ABTest({
        name: 'sample_size_test',
        controlAgent,
        treatmentAgent,
      });

      const testCases: TestCase[] = [
        { input: 'q1', expected: 'answer' },
        { input: 'q2', expected: 'answer' },
        { input: 'q3', expected: 'answer' },
        { input: 'q4', expected: 'answer' },
        { input: 'q5', expected: 'answer' },
      ];

      const results = await test.run(testCases, { sampleSize: 3, shuffle: false });

      expect(results.accuracy.controlVariant.sampleSize).toBe(3);
      expect(results.accuracy.treatmentVariant.sampleSize).toBe(3);
    });
  });

  describe('Statistical Analysis', () => {
    it('should detect significant difference', async () => {
      // Control: always wrong, Treatment: always right
      const controlAgent = new MockAgent('control', 'wrong');
      const treatmentAgent = new MockAgent('treatment', 'correct');

      const test = new ABTest({
        name: 'significance_test',
        controlAgent,
        treatmentAgent,
      });

      const testCases: TestCase[] = Array(30)
        .fill(null)
        .map((_, i) => ({
          input: `question ${i}`,
          expected: 'correct',
        }));

      const results = await test.run(testCases, { shuffle: false });

      // With perfect separation (0.0 vs 1.0) over 30 samples, should be highly significant
      expect(results.accuracy.pValue).toBeLessThan(0.05);
      expect(results.accuracy.isSignificant).toBe(true);
      expect(results.accuracy.winner).toBe('treatment');
      expect(results.accuracy.treatmentVariant.mean).toBe(1.0);
      expect(results.accuracy.controlVariant.mean).toBe(0.0);
    });

    it('should not detect significance with same performance', async () => {
      const agent1 = new MockAgent('agent1', 'answer');
      const agent2 = new MockAgent('agent2', 'answer');

      const test = new ABTest({
        name: 'no_difference_test',
        controlAgent: agent1,
        treatmentAgent: agent2,
      });

      const testCases: TestCase[] = Array(10)
        .fill(null)
        .map((_, i) => ({
          input: `question ${i}`,
          expected: 'answer',
        }));

      const results = await test.run(testCases, { shuffle: false });

      // With identical performance, should not be significant
      expect(results.accuracy.pValue).toBeGreaterThan(0.05);
      expect(results.accuracy.isSignificant).toBe(false);
      expect(results.accuracy.winner).toBeNull();
    });

    it('should calculate effect size', async () => {
      const controlAgent = new MockAgent('control', 'wrong');
      const treatmentAgent = new MockAgent('treatment', 'correct');

      const test = new ABTest({
        name: 'effect_size_test',
        controlAgent,
        treatmentAgent,
      });

      const testCases: TestCase[] = Array(10)
        .fill(null)
        .map((_, i) => ({
          input: `question ${i}`,
          expected: 'correct',
        }));

      const results = await test.run(testCases, { shuffle: false });

      expect(results.accuracy.effectSize).toBeDefined();
      expect(typeof results.accuracy.effectSize).toBe('number');
    });

    it('should calculate confidence interval', async () => {
      const controlAgent = new MockAgent('control', 'answer');
      const treatmentAgent = new MockAgent('treatment', 'answer');

      const test = new ABTest({
        name: 'ci_test',
        controlAgent,
        treatmentAgent,
      });

      const testCases: TestCase[] = Array(10)
        .fill(null)
        .map((_, i) => ({
          input: `question ${i}`,
          expected: 'answer',
        }));

      const results = await test.run(testCases, { shuffle: false });

      expect(results.accuracy.confidenceInterval).toBeDefined();
      expect(results.accuracy.confidenceInterval.length).toBe(2);
      expect(results.accuracy.confidenceInterval[0]).toBeLessThanOrEqual(
        results.accuracy.confidenceInterval[1]
      );
    });
  });

  describe('Multiple Metrics', () => {
    it('should evaluate multiple metrics', async () => {
      const controlAgent = new MockAgent('control', 'answer', 10);
      const treatmentAgent = new MockAgent('treatment', 'answer', 20);

      const test = new ABTest({
        name: 'multi_metric_test',
        controlAgent,
        treatmentAgent,
        metrics: ['accuracy', 'latencyMs'],
      });

      const testCases: TestCase[] = [
        { input: 'q1', expected: 'answer' },
        { input: 'q2', expected: 'answer' },
      ];

      const results = await test.run(testCases, { shuffle: false });

      expect(results.accuracy).toBeDefined();
      expect(results.latencyMs).toBeDefined();
      expect(Object.keys(results).length).toBe(2);
    });
  });

  describe('Error Handling', () => {
    it('should handle agent errors gracefully', async () => {
      class ErrorAgent implements Agent {
        readonly name = 'error_agent';
        async process(): Promise<Message> {
          throw new Error('Agent failed');
        }
      }

      const controlAgent = new MockAgent('control', 'answer');
      const treatmentAgent = new ErrorAgent();

      const test = new ABTest({
        name: 'error_test',
        controlAgent,
        treatmentAgent,
      });

      const testCases: TestCase[] = [{ input: 'question', expected: 'answer' }];

      const results = await test.run(testCases, { shuffle: false });

      // Treatment should have 0 accuracy due to errors
      expect(results.accuracy.treatmentVariant.mean).toBe(0.0);
      expect(results.accuracy.controlVariant.mean).toBeGreaterThan(0.0);
    });
  });

  describe('Summary', () => {
    it('should generate summary', async () => {
      const controlAgent = new MockAgent('control', 'answer');
      const treatmentAgent = new MockAgent('treatment', 'answer');

      const test = new ABTest({
        name: 'summary_test',
        controlAgent,
        treatmentAgent,
      });

      const testCases: TestCase[] = [{ input: 'question', expected: 'answer' }];

      await test.run(testCases, { shuffle: false });

      const summary = test.getSummary();

      expect(summary.experimentName).toBe('summary_test');
      expect(summary.variants).toBeDefined();
      expect(summary.metrics).toEqual(['accuracy']);
      expect(summary.results).toBeDefined();
    });
  });

  describe('Significance Levels', () => {
    it('should respect custom significance level', () => {
      const controlAgent = new MockAgent('control', 'answer');
      const treatmentAgent = new MockAgent('treatment', 'answer');

      const test = new ABTest({
        name: 'significance_level_test',
        controlAgent,
        treatmentAgent,
        significanceLevel: SignificanceLevel.P_0_01,
      });

      expect(test.significanceLevel).toBe(SignificanceLevel.P_0_01);
      expect(test.significanceLevel).toBe(0.01);
    });
  });
});

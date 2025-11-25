/**
 * Tests for Quality Metrics module.
 */

import {
  AccuracyMetric,
  QualityMetrics,
  LatencyMetric,
  evaluateAgent,
} from '../evaluation/quality-metrics';
import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Mock agent for testing.
 */
class MockAgent implements Agent {
  readonly name = 'MockAgent';
  private response: string;

  constructor(response: string) {
    this.response = response;
  }

  async process(message: Message): Promise<Message> {
    return createMessage('assistant', this.response);
  }
}

describe('AccuracyMetric', () => {
  describe('Configuration', () => {
    it('should create with default configuration', () => {
      const metric = new AccuracyMetric();

      expect(metric.name).toBe('accuracy');
    });

    it('should create with custom validator', () => {
      const validator = (expected: string, actual: string) => expected === actual;
      const metric = new AccuracyMetric({ validator });

      expect(metric.name).toBe('accuracy');
    });

    it('should create with case-sensitive mode', () => {
      const metric = new AccuracyMetric({ caseSensitive: true });

      expect(metric.name).toBe('accuracy');
    });
  });

  describe('Measurement', () => {
    it('should return 1.0 for correct answer', async () => {
      const metric = new AccuracyMetric();
      const agent = new MockAgent('Paris');
      const input = createMessage('user', 'What is the capital of France?');
      const output = createMessage('assistant', 'The capital is Paris');

      const score = await metric.measure(agent, input, output, { expected: 'Paris' });

      expect(score).toBe(1.0);
    });

    it('should return 0.0 for incorrect answer', async () => {
      const metric = new AccuracyMetric();
      const agent = new MockAgent('London');
      const input = createMessage('user', 'What is the capital of France?');
      const output = createMessage('assistant', 'London');

      const score = await metric.measure(agent, input, output, { expected: 'Paris' });

      expect(score).toBe(0.0);
    });

    it('should be case-insensitive by default', async () => {
      const metric = new AccuracyMetric();
      const agent = new MockAgent('paris');
      const input = createMessage('user', 'Question');
      const output = createMessage('assistant', 'paris');

      const score = await metric.measure(agent, input, output, { expected: 'PARIS' });

      expect(score).toBe(1.0);
    });

    it('should respect case-sensitive mode', async () => {
      const metric = new AccuracyMetric({ caseSensitive: true });
      const agent = new MockAgent('paris');
      const input = createMessage('user', 'Question');
      const output = createMessage('assistant', 'paris');

      const score = await metric.measure(agent, input, output, { expected: 'Paris' });

      expect(score).toBe(0.0);
    });

    it('should return 1.0 when no expected output', async () => {
      const metric = new AccuracyMetric();
      const agent = new MockAgent('anything');
      const input = createMessage('user', 'Question');
      const output = createMessage('assistant', 'anything');

      const score = await metric.measure(agent, input, output);

      expect(score).toBe(1.0);
    });

    it('should use custom validator', async () => {
      const validator = (expected: string, actual: string) => {
        return actual.length >= parseInt(expected);
      };
      const metric = new AccuracyMetric({ validator });
      const agent = new MockAgent('Hello World');
      const input = createMessage('user', 'Question');
      const output = createMessage('assistant', 'Hello World');

      const score = await metric.measure(agent, input, output, { expected: '5' });

      expect(score).toBe(1.0);
    });

    it('should support substring matching', async () => {
      const metric = new AccuracyMetric();
      const agent = new MockAgent('The answer');
      const input = createMessage('user', 'Question');
      const output = createMessage('assistant', 'The answer is 42');

      const score = await metric.measure(agent, input, output, { expected: '42' });

      expect(score).toBe(1.0);
    });
  });

  describe('Aggregation', () => {
    it('should aggregate empty measurements', () => {
      const metric = new AccuracyMetric();
      const result = metric.aggregate([]);

      expect(result.accuracy).toBe(0.0);
      expect(result.total).toBe(0);
      expect(result.correct).toBe(0);
      expect(result.incorrect).toBe(0);
    });

    it('should aggregate perfect accuracy', () => {
      const metric = new AccuracyMetric();
      const result = metric.aggregate([1.0, 1.0, 1.0]);

      expect(result.accuracy).toBe(1.0);
      expect(result.total).toBe(3);
      expect(result.correct).toBe(3);
      expect(result.incorrect).toBe(0);
    });

    it('should aggregate partial accuracy', () => {
      const metric = new AccuracyMetric();
      const result = metric.aggregate([1.0, 0.0, 1.0, 0.0]);

      expect(result.accuracy).toBe(0.5);
      expect(result.total).toBe(4);
      expect(result.correct).toBe(2);
      expect(result.incorrect).toBe(2);
    });
  });
});

describe('QualityMetrics', () => {
  describe('Configuration', () => {
    it('should create with default weights', () => {
      const metric = new QualityMetrics();

      expect(metric.name).toBe('quality');
    });

    it('should create with custom weights', () => {
      const metric = new QualityMetrics({
        weights: {
          relevance: 0.5,
          completeness: 0.5,
        },
      });

      expect(metric.name).toBe('quality');
    });
  });

  describe('Measurement', () => {
    it('should measure quality', async () => {
      const metric = new QualityMetrics();
      const agent = new MockAgent('Paris is the capital');
      const input = createMessage('user', 'What is the capital of France?');
      const output = createMessage('assistant', 'Paris is the capital of France.');

      const score = await metric.measure(agent, input, output);

      expect(score).toBeGreaterThan(0);
      expect(score).toBeLessThanOrEqual(1);
    });

    it('should give higher scores to better responses', async () => {
      const metric = new QualityMetrics();
      const agent = new MockAgent('response');
      const input = createMessage('user', 'What is the capital of France?');

      const goodOutput = createMessage(
        'assistant',
        'The capital of France is Paris. It is the largest city in France.'
      );
      const poorOutput = createMessage('assistant', 'x');

      const goodScore = await metric.measure(agent, input, goodOutput);
      const poorScore = await metric.measure(agent, input, poorOutput);

      expect(goodScore).toBeGreaterThan(poorScore);
    });

    it('should consider expected output if provided', async () => {
      const metric = new QualityMetrics();
      const agent = new MockAgent('response');
      const input = createMessage('user', 'Question');

      const correctOutput = createMessage('assistant', 'The answer is Paris.');
      const wrongOutput = createMessage('assistant', 'The answer is London.');

      const correctScore = await metric.measure(agent, input, correctOutput, {
        expected: 'Paris',
      });
      const wrongScore = await metric.measure(agent, input, wrongOutput, {
        expected: 'Paris',
      });

      expect(correctScore).toBeGreaterThan(wrongScore);
    });
  });

  describe('Aggregation', () => {
    it('should aggregate empty measurements', () => {
      const metric = new QualityMetrics();
      const result = metric.aggregate([]);

      expect(result.mean).toBe(0.0);
      expect(result.total).toBe(0);
    });

    it('should aggregate quality scores', () => {
      const metric = new QualityMetrics();
      const result = metric.aggregate([0.8, 0.9, 0.7]);

      expect(result.mean).toBeCloseTo(0.8, 5);
      expect(result.min).toBe(0.7);
      expect(result.max).toBe(0.9);
      expect(result.total).toBe(3);
    });
  });
});

describe('LatencyMetric', () => {
  describe('Measurement', () => {
    it('should use provided latency from context', async () => {
      const metric = new LatencyMetric();
      const agent = new MockAgent('response');
      const input = createMessage('user', 'Question');
      const output = createMessage('assistant', 'Answer');

      const score = await metric.measure(agent, input, output, { latency: 123.45 });

      expect(score).toBe(123.45);
    });

    it('should measure latency if not provided', async () => {
      const metric = new LatencyMetric();
      const agent = new MockAgent('response');
      const input = createMessage('user', 'Question');
      const output = createMessage('assistant', 'Answer');

      const score = await metric.measure(agent, input, output);

      expect(score).toBeGreaterThan(0);
    });
  });

  describe('Aggregation', () => {
    it('should aggregate empty measurements', () => {
      const metric = new LatencyMetric();
      const result = metric.aggregate([]);

      expect(result.mean).toBe(0.0);
      expect(result.total).toBe(0);
    });

    it('should calculate percentiles', () => {
      const metric = new LatencyMetric();
      const measurements = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
      const result = metric.aggregate(measurements);

      expect(result.mean).toBe(55);
      expect(result.min).toBe(10);
      expect(result.max).toBe(100);
      expect(result.p50).toBeGreaterThanOrEqual(40);
      expect(result.p50).toBeLessThanOrEqual(60);
      expect(result.p95).toBeGreaterThanOrEqual(90);
      expect(result.p99).toBeGreaterThanOrEqual(90);
    });

    it('should handle single measurement', () => {
      const metric = new LatencyMetric();
      const result = metric.aggregate([42]);

      expect(result.mean).toBe(42);
      expect(result.min).toBe(42);
      expect(result.max).toBe(42);
      expect(result.p50).toBe(42);
      expect(result.p95).toBe(42);
      expect(result.p99).toBe(42);
    });
  });
});

describe('evaluateAgent', () => {
  it('should evaluate agent with multiple metrics', async () => {
    const agent = new MockAgent('Paris');
    const testCases = [
      { input: createMessage('user', 'Q1'), expected: 'Paris' },
      { input: createMessage('user', 'Q2'), expected: 'Paris' },
    ];
    const metrics = [new AccuracyMetric(), new QualityMetrics()];

    const result = await evaluateAgent(agent, testCases, metrics);

    expect(result.agentName).toBe('MockAgent');
    expect(result.totalTests).toBe(2);
    expect(result.metrics.accuracy).toBeDefined();
    expect(result.metrics.quality).toBeDefined();
  });

  it('should compute accuracy correctly', async () => {
    const agent = new MockAgent('Paris');
    const testCases = [
      { input: createMessage('user', 'Q1'), expected: 'Paris' },
      { input: createMessage('user', 'Q2'), expected: 'Paris' },
      { input: createMessage('user', 'Q3'), expected: 'Paris' },
    ];
    const metrics = [new AccuracyMetric()];

    const result = await evaluateAgent(agent, testCases, metrics);

    expect(result.metrics.accuracy.accuracy).toBe(1.0);
    expect(result.metrics.accuracy.correct).toBe(3);
    expect(result.metrics.accuracy.incorrect).toBe(0);
  });

  it('should measure latency', async () => {
    const agent = new MockAgent('response');
    const testCases = [{ input: createMessage('user', 'Question') }];
    const metrics = [new LatencyMetric()];

    const result = await evaluateAgent(agent, testCases, metrics);

    expect(result.metrics.latency).toBeDefined();
    expect(result.metrics.latency.mean).toBeGreaterThan(0);
  });

  it('should handle multiple test cases', async () => {
    const agent = new MockAgent('Answer');
    const testCases = Array(10)
      .fill(null)
      .map((_, i) => ({
        input: createMessage('user', `Question ${i}`),
        expected: 'Answer',
      }));
    const metrics = [new AccuracyMetric(), new LatencyMetric()];

    const result = await evaluateAgent(agent, testCases, metrics);

    expect(result.totalTests).toBe(10);
    expect(result.metrics.accuracy.total).toBe(10);
    expect(result.metrics.latency.total).toBe(10);
  });

  it('should handle test cases without expected output', async () => {
    const agent = new MockAgent('Answer');
    const testCases = [{ input: createMessage('user', 'Question') }];
    const metrics = [new AccuracyMetric()];

    const result = await evaluateAgent(agent, testCases, metrics);

    expect(result.metrics.accuracy.accuracy).toBe(1.0);
  });
});

/**
 * Tests for core evaluation framework.
 */

import { Agent, Message, createMessage } from '../core/interfaces';
import {
  Evaluator,
  EvaluationResult,
  TestCase,
  getSuccessRate,
  resultToDict,
  evaluateAgent,
} from '../evaluation/core';
import { Metric } from '../evaluation/quality-metrics';

// Mock agent for testing
class MockAgent implements Agent {
  name = 'mock-agent';
  capabilities = [];

  async process(message: Message): Promise<Message> {
    // Echo back the input with a prefix
    return createMessage('assistant', `Response: ${message.content}`);
  }
}

// Mock metric that always returns 0.8
class MockMetric implements Metric {
  name = 'mock_metric';

  async measure(
    agent: Agent,
    inputMessage: Message,
    outputMessage: Message,
    context?: Record<string, unknown>
  ): Promise<number> {
    return 0.8;
  }

  aggregate(measurements: number[]): Record<string, number> {
    if (measurements.length === 0) {
      return { mean: 0, min: 0, max: 0, count: 0 };
    }

    const sum = measurements.reduce((a, b) => a + b, 0);
    const mean = sum / measurements.length;
    const min = Math.min(...measurements);
    const max = Math.max(...measurements);

    return {
      mean,
      min,
      max,
      count: measurements.length,
    };
  }
}

// Mock accuracy metric
class MockAccuracyMetric implements Metric {
  name = 'accuracy';

  async measure(
    agent: Agent,
    inputMessage: Message,
    outputMessage: Message,
    context?: Record<string, unknown>
  ): Promise<number> {
    if (!context?.expected) {
      return 1.0;
    }

    const expected = String(context.expected).toLowerCase();
    const actual = outputMessage.content.toLowerCase();

    return actual.includes(expected) ? 1.0 : 0.0;
  }

  aggregate(measurements: number[]): Record<string, number> {
    if (measurements.length === 0) {
      return { mean: 0, min: 0, max: 0, count: 0 };
    }

    const sum = measurements.reduce((a, b) => a + b, 0);
    return {
      mean: sum / measurements.length,
      min: Math.min(...measurements),
      max: Math.max(...measurements),
      count: measurements.length,
    };
  }
}

describe('Evaluator', () => {
  let agent: Agent;
  let mockMetric: Metric;

  beforeEach(() => {
    agent = new MockAgent();
    mockMetric = new MockMetric();
  });

  test('constructor creates evaluator', () => {
    const evaluator = new Evaluator(agent, [mockMetric]);

    expect(evaluator).toBeDefined();
    expect(evaluator.getAgent()).toBe(agent);
    expect(evaluator.getMetrics()).toHaveLength(1);
    expect(evaluator.getSessionId()).toMatch(/^eval-/);
  });

  test('constructor with custom session ID', () => {
    const sessionId = 'custom-session-123';
    const evaluator = new Evaluator(agent, [mockMetric], sessionId);

    expect(evaluator.getSessionId()).toBe(sessionId);
  });

  test('evaluate runs test cases', async () => {
    const evaluator = new Evaluator(agent, [mockMetric]);
    const testCases: TestCase[] = [
      { input: 'test 1', expected: 'response' },
      { input: 'test 2', expected: 'response' },
    ];

    const result = await evaluator.evaluate(testCases);

    expect(result).toBeDefined();
    expect(result.evaluationId).toBeDefined();
    expect(result.agentName).toBe('mock-agent');
    expect(result.totalTests).toBe(2);
    expect(result.timestamp).toBeInstanceOf(Date);
  });

  test('evaluate collects metrics', async () => {
    const evaluator = new Evaluator(agent, [mockMetric]);
    const testCases: TestCase[] = [
      { input: 'test 1' },
      { input: 'test 2' },
      { input: 'test 3' },
    ];

    const result = await evaluator.evaluate(testCases);

    expect(result.metrics['mock_metric']).toHaveLength(3);
    expect(result.metrics['mock_metric']).toEqual([0.8, 0.8, 0.8]);
  });

  test('evaluate aggregates metrics', async () => {
    const evaluator = new Evaluator(agent, [mockMetric]);
    const testCases: TestCase[] = [
      { input: 'test 1' },
      { input: 'test 2' },
    ];

    const result = await evaluator.evaluate(testCases);

    expect(result.aggregatedMetrics['mock_metric']).toBeDefined();
    expect(result.aggregatedMetrics['mock_metric'].mean).toBe(0.8);
    expect(result.aggregatedMetrics['mock_metric'].count).toBe(2);
  });

  test('evaluate tracks accuracy', async () => {
    const accuracyMetric = new MockAccuracyMetric();
    const evaluator = new Evaluator(agent, [accuracyMetric]);
    const testCases: TestCase[] = [
      { input: 'test 1', expected: 'response' },
      { input: 'test 2', expected: 'response' },
      { input: 'test 3', expected: 'xyz' }, // Will fail
    ];

    const result = await evaluator.evaluate(testCases);

    expect(result.passedTests).toBe(2);
    expect(result.failedTests).toBe(1);
    expect(result.accuracy).toBeCloseTo(2 / 3, 2);
  });

  test('evaluate tracks latency', async () => {
    const evaluator = new Evaluator(agent, [mockMetric]);
    const testCases: TestCase[] = [
      { input: 'test 1' },
      { input: 'test 2' },
    ];

    const result = await evaluator.evaluate(testCases);

    expect(result.avgLatencyMs).toBeDefined();
    expect(result.avgLatencyMs).toBeGreaterThanOrEqual(0);
    expect(result.p95LatencyMs).toBeDefined();
    expect(result.p95LatencyMs).toBeGreaterThanOrEqual(0);
  });

  test('evaluate handles errors gracefully', async () => {
    // Agent that throws errors
    const errorAgent: Agent = {
      name: 'error-agent',
      capabilities: [],
      async process() {
        throw new Error('Processing failed');
      },
    };

    const evaluator = new Evaluator(errorAgent, [mockMetric]);
    const testCases: TestCase[] = [
      { input: 'test 1' },
      { input: 'test 2' },
    ];

    const result = await evaluator.evaluate(testCases);

    expect(result.failedTests).toBe(2);
    expect(result.passedTests).toBe(0);
  });

  test('evaluateSingle evaluates one test', async () => {
    const evaluator = new Evaluator(agent, [mockMetric]);
    const inputMsg = createMessage('user', 'test input');

    const scores = await evaluator.evaluateSingle(inputMsg, 'expected');

    expect(scores['mock_metric']).toBe(0.8);
  });

  test('evaluate with custom evaluation ID', async () => {
    const evaluator = new Evaluator(agent, [mockMetric]);
    const testCases: TestCase[] = [{ input: 'test' }];
    const customId = 'custom-eval-123';

    const result = await evaluator.evaluate(testCases, customId);

    expect(result.evaluationId).toBe(customId);
  });

  test('evaluate with no metrics uses simple validation', async () => {
    const evaluator = new Evaluator(agent, []);
    const testCases: TestCase[] = [
      { input: 'test 1', expected: 'response' },
      { input: 'test 2', expected: 'xyz' }, // Will fail
    ];

    const result = await evaluator.evaluate(testCases);

    expect(result.passedTests).toBe(1);
    expect(result.failedTests).toBe(1);
  });
});

describe('getSuccessRate', () => {
  test('calculates success rate', () => {
    const result: EvaluationResult = {
      evaluationId: 'test',
      agentName: 'test-agent',
      timestamp: new Date(),
      metrics: {},
      aggregatedMetrics: {},
      totalTests: 10,
      passedTests: 7,
      failedTests: 3,
      metadata: {},
    };

    expect(getSuccessRate(result)).toBe(0.7);
  });

  test('returns 0 for no tests', () => {
    const result: EvaluationResult = {
      evaluationId: 'test',
      agentName: 'test-agent',
      timestamp: new Date(),
      metrics: {},
      aggregatedMetrics: {},
      totalTests: 0,
      passedTests: 0,
      failedTests: 0,
      metadata: {},
    };

    expect(getSuccessRate(result)).toBe(0.0);
  });
});

describe('resultToDict', () => {
  test('converts result to dictionary', () => {
    const result: EvaluationResult = {
      evaluationId: 'test-123',
      agentName: 'test-agent',
      timestamp: new Date('2025-01-01T00:00:00Z'),
      metrics: { accuracy: [0.8, 0.9] },
      aggregatedMetrics: { accuracy: { mean: 0.85 } },
      totalTests: 2,
      passedTests: 2,
      failedTests: 0,
      accuracy: 0.85,
      metadata: { version: '1.0' },
    };

    const dict = resultToDict(result);

    expect(dict.evaluationId).toBe('test-123');
    expect(dict.agentName).toBe('test-agent');
    expect(dict.timestamp).toBe('2025-01-01T00:00:00.000Z');
    expect(dict.totalTests).toBe(2);
    expect(dict.successRate).toBe(1.0);
    expect(dict.accuracy).toBe(0.85);
  });
});

describe('evaluateAgent helper', () => {
  test('evaluates agent with helper function', async () => {
    const agent = new MockAgent();
    const testCases: TestCase[] = [
      { input: 'test 1', expected: 'response' },
      { input: 'test 2', expected: 'response' },
    ];

    const result = await evaluateAgent(agent, testCases, [new MockMetric()]);

    expect(result).toBeDefined();
    expect(result.totalTests).toBe(2);
    expect(result.agentName).toBe('mock-agent');
  });

  test('evaluates agent without metrics', async () => {
    const agent = new MockAgent();
    const testCases: TestCase[] = [{ input: 'test' }];

    const result = await evaluateAgent(agent, testCases);

    expect(result).toBeDefined();
    expect(result.totalTests).toBe(1);
  });
});

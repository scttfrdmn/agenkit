/**
 * Tests for evaluation metrics.
 *
 * Tests AccuracyMetric, QualityMetrics, ContextMetrics, LatencyMetric, etc.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import type { Agent, Message } from '../../core/interfaces';
import { createMessage } from '../../core/interfaces';
import { AccuracyMetric, QualityMetrics, LatencyMetric } from '../../evaluation/quality-metrics';
import { ContextMetrics, CompressionMetrics } from '../../evaluation/context-metrics';

// Mock agent for testing
class MockAgent implements Agent {
  name = 'mock-agent';
  capabilities = [];
  private contextStats: Record<string, unknown>;
  private compressionStats: Record<string, unknown>;

  constructor(contextStats?: Record<string, unknown>, compressionStats?: Record<string, unknown>) {
    this.contextStats = contextStats || {};
    this.compressionStats = compressionStats || {};
  }

  async process(message: Message): Promise<Message> {
    return createMessage('assistant', 'Response');
  }

  async getContextStats(sessionId: string): Promise<Record<string, unknown>> {
    return this.contextStats;
  }

  async getCompressionStats(sessionId: string): Promise<Record<string, unknown>> {
    return this.compressionStats;
  }
}

// ============================================
// AccuracyMetric Tests
// ============================================

describe('AccuracyMetric', () => {
  let agent: MockAgent;
  let metric: AccuracyMetric;

  beforeEach(() => {
    agent = new MockAgent();
    metric = new AccuracyMetric();
  });

  it('should return 1.0 for correct answer', async () => {
    const input = createMessage('user', 'What is 2+2?');
    const output = createMessage('assistant', 'The answer is 4');

    const score = await metric.measure(agent, input, output, { expected: '4' });

    expect(score).toBe(1.0);
  });

  it('should return 0.0 for incorrect answer', async () => {
    const input = createMessage('user', 'What is 2+2?');
    const output = createMessage('assistant', 'The answer is 5');

    const score = await metric.measure(agent, input, output, { expected: '4' });

    expect(score).toBe(0.0);
  });

  it('should be case-insensitive by default', async () => {
    const input = createMessage('user', 'Capital of France?');
    const output = createMessage('assistant', 'PARIS');

    const score = await metric.measure(agent, input, output, { expected: 'paris' });

    expect(score).toBe(1.0);
  });

  it('should support case-sensitive matching', async () => {
    const caseSensitiveMetric = new AccuracyMetric({ caseSensitive: true });
    const input = createMessage('user', 'Test');
    const output = createMessage('assistant', 'PARIS');

    const score = await caseSensitiveMetric.measure(agent, input, output, { expected: 'paris' });

    expect(score).toBe(0.0);
  });

  it('should support custom validator', async () => {
    const validator = (expected: string, actual: string) => actual.length > 10;
    const customMetric = new AccuracyMetric({ validator });

    const input = createMessage('user', 'Test');
    const output = createMessage('assistant', 'This is a long response');

    const score = await customMetric.measure(agent, input, output, { expected: 'ignored' });

    expect(score).toBe(1.0);
  });

  it('should return 1.0 when no expected value provided', async () => {
    const input = createMessage('user', 'Test');
    const output = createMessage('assistant', 'Response');

    const score = await metric.measure(agent, input, output, {});

    expect(score).toBe(1.0);
  });

  it('should aggregate measurements correctly', () => {
    const measurements = [1.0, 1.0, 0.0, 1.0, 0.0];
    const stats = metric.aggregate(measurements);

    expect(stats.accuracy).toBe(0.6);
    expect(stats.total).toBe(5);
    expect(stats.correct).toBe(3);
    expect(stats.incorrect).toBe(2);
  });

  it('should handle empty measurements', () => {
    const stats = metric.aggregate([]);

    expect(stats.accuracy).toBe(0.0);
    expect(stats.total).toBe(0);
  });

  it('should handle single measurement', () => {
    const stats = metric.aggregate([1.0]);

    expect(stats.accuracy).toBe(1.0);
    expect(stats.total).toBe(1);
    expect(stats.correct).toBe(1);
  });
});

// ============================================
// QualityMetrics Tests
// ============================================

describe('QualityMetrics', () => {
  let agent: MockAgent;
  let metric: QualityMetrics;

  beforeEach(() => {
    agent = new MockAgent();
    metric = new QualityMetrics();
  });

  it('should measure response quality', async () => {
    const input = createMessage('user', 'Question');
    const output = createMessage('assistant', 'This is a detailed response');

    const score = await metric.measure(agent, input, output);

    expect(score).toBeGreaterThanOrEqual(0);
    expect(score).toBeLessThanOrEqual(1);
  });

  it('should handle empty response', async () => {
    const input = createMessage('user', 'Question');
    const output = createMessage('assistant', '');

    const score = await metric.measure(agent, input, output);

    expect(score).toBeGreaterThanOrEqual(0);
  });

  it('should aggregate quality scores', () => {
    const measurements = [0.8, 0.9, 0.7, 0.85];
    const stats = metric.aggregate(measurements);

    expect(stats).toBeDefined();
    expect(Object.keys(stats).length).toBeGreaterThan(0);
  });

  it('should handle empty quality measurements', () => {
    const stats = metric.aggregate([]);

    expect(stats).toBeDefined();
  });
});

// ============================================
// LatencyMetric Tests
// ============================================

describe('LatencyMetric', () => {
  let agent: MockAgent;
  let metric: LatencyMetric;

  beforeEach(() => {
    agent = new MockAgent();
    metric = new LatencyMetric();
  });

  it('should measure response latency', async () => {
    const input = createMessage('user', 'Test');
    const output = createMessage('assistant', 'Response');

    const startTime = Date.now();
    await new Promise((resolve) => setTimeout(resolve, 10));
    const score = await metric.measure(agent, input, output, { startTime });

    expect(score).toBeGreaterThanOrEqual(0);
  });

  it('should aggregate latency measurements', () => {
    const measurements = [100, 150, 120, 200];
    const stats = metric.aggregate(measurements);

    expect(stats.mean).toBeDefined();
    expect(stats.min).toBeDefined();
    expect(stats.max).toBeDefined();
  });

  it('should calculate statistics correctly', () => {
    const measurements = Array.from({ length: 100 }, (_, i) => i + 1);
    const stats = metric.aggregate(measurements);

    expect(stats.mean).toBeGreaterThan(0);
    expect(stats.min).toBe(1);
    expect(stats.max).toBe(100);
  });
});

// ============================================
// ContextMetrics Tests
// ============================================

describe('ContextMetrics', () => {
  it('should measure context length', async () => {
    const contextStats = {
      context_length: 500,
    };
    const agent = new MockAgent(contextStats);
    const metric = new ContextMetrics();

    const input = createMessage('user', 'Test');
    const output = createMessage('assistant', 'Response');

    const score = await metric.measure(agent, input, output, { sessionId: 'test-123' });

    expect(score).toBe(500);
  });

  it('should return 0 when no context stats available', async () => {
    const agent = new MockAgent({});
    const metric = new ContextMetrics();

    const input = createMessage('user', 'Test');
    const output = createMessage('assistant', 'Response');

    const score = await metric.measure(agent, input, output, { sessionId: 'test-123' });

    expect(score).toBe(0);
  });

  it('should aggregate context lengths', () => {
    const metric = new ContextMetrics();
    const measurements = [100, 200, 300, 400];
    const stats = metric.aggregate(measurements);

    expect(stats.mean).toBe(250);
    expect(stats.max).toBe(400);
    expect(stats.final).toBe(400);
  });
});

// ============================================
// CompressionMetrics Tests
// ============================================

describe('CompressionMetrics', () => {
  it('should measure compression ratio', async () => {
    const agent = new MockAgent();
    const metric = new CompressionMetrics();

    const input = createMessage('user', 'Test');
    const output = createMessage('assistant', 'Response');

    const score = await metric.measure(agent, input, output, {
      raw_tokens: 1000,
      compressed_tokens: 500,
    });

    expect(score).toBe(2.0); // 1000/500 = 2.0 compression ratio
  });

  it('should return 1.0 when no compression available', async () => {
    const agent = new MockAgent();
    const metric = new CompressionMetrics();

    const input = createMessage('user', 'Test');
    const output = createMessage('assistant', 'Response');

    const score = await metric.measure(agent, input, output, {});

    expect(score).toBe(1.0);
  });

  it('should aggregate compression ratios', () => {
    const metric = new CompressionMetrics();
    const measurements = [2.0, 2.5, 3.0];
    const stats = metric.aggregate(measurements);

    expect(stats.mean).toBeCloseTo(2.5, 2);
    expect(stats.min).toBe(2.0);
    expect(stats.max).toBe(3.0);
  });
});

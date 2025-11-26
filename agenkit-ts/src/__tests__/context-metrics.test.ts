/**
 * Tests for context metrics.
 */

import { Agent, Message, createMessage } from '../core/interfaces';
import {
  ContextMetrics,
  CompressionMetrics,
  AgentWithContextStats,
  createCompressionStats,
  compressionStatsToDict,
} from '../evaluation/context-metrics';

// Mock agent with context stats
class MockAgentWithStats implements AgentWithContextStats {
  name = 'mock-agent-stats';
  capabilities = [];
  private contextLength = 1000;

  async process(message: Message): Promise<Message> {
    return createMessage('assistant', 'Response');
  }

  async getContextStats(sessionId: string): Promise<Record<string, number>> {
    return {
      context_length: this.contextLength,
      session_count: 1,
    };
  }

  setContextLength(length: number): void {
    this.contextLength = length;
  }
}

// Regular mock agent without context stats
class MockAgent implements Agent {
  name = 'mock-agent';
  capabilities = [];

  async process(message: Message): Promise<Message> {
    return createMessage('assistant', 'Response');
  }
}

describe('ContextMetrics', () => {
  let metric: ContextMetrics;

  beforeEach(() => {
    metric = new ContextMetrics();
  });

  test('has correct name', () => {
    expect(metric.name).toBe('context_length');
  });

  test('measures from agent context stats', async () => {
    const agent = new MockAgentWithStats();
    agent.setContextLength(5000);

    const input = createMessage('user', 'test');
    const output = createMessage('assistant', 'response');

    const length = await metric.measure(agent, input, output, {
      sessionId: 'test-session',
    });

    expect(length).toBe(5000);
  });

  test('measures from message metadata', async () => {
    const agent = new MockAgent();
    const input = createMessage('user', 'test');
    input.metadata = { context_length: 2500 };
    const output = createMessage('assistant', 'response');

    const length = await metric.measure(agent, input, output);

    expect(length).toBe(2500);
  });

  test('measures from conversation history', async () => {
    const agent = new MockAgent();
    const input = createMessage('user', 'test');
    const output = createMessage('assistant', 'response');

    const history: Message[] = [
      createMessage('user', 'a'.repeat(400)), // ~100 tokens
      createMessage('assistant', 'b'.repeat(400)), // ~100 tokens
      createMessage('user', 'c'.repeat(800)), // ~200 tokens
    ];

    const length = await metric.measure(agent, input, output, {
      conversationHistory: history,
    });

    expect(length).toBe(400); // 1600 chars / 4
  });

  test('returns 0 for no context', async () => {
    const agent = new MockAgent();
    const input = createMessage('user', 'test');
    const output = createMessage('assistant', 'response');

    const length = await metric.measure(agent, input, output);

    expect(length).toBe(0);
  });

  test('aggregates measurements correctly', () => {
    const measurements = [100, 200, 300, 400, 500];

    const stats = metric.aggregate(measurements);

    expect(stats.mean).toBe(300);
    expect(stats.min).toBe(100);
    expect(stats.max).toBe(500);
    expect(stats.final).toBe(500);
    expect(stats.growth_rate).toBe(80); // (500 - 100) / 5
  });

  test('aggregates empty measurements', () => {
    const stats = metric.aggregate([]);

    expect(stats.mean).toBe(0);
    expect(stats.min).toBe(0);
    expect(stats.max).toBe(0);
    expect(stats.final).toBe(0);
    expect(stats.growth_rate).toBe(0);
  });

  test('aggregates single measurement', () => {
    const stats = metric.aggregate([500]);

    expect(stats.mean).toBe(500);
    expect(stats.min).toBe(500);
    expect(stats.max).toBe(500);
    expect(stats.final).toBe(500);
    expect(stats.growth_rate).toBe(0); // No growth with single measurement
  });

  test('calculates growth rate correctly', () => {
    const measurements = [1000, 1500, 2000];

    const stats = metric.aggregate(measurements);

    expect(stats.growth_rate).toBeCloseTo(333.33, 1); // (2000 - 1000) / 3
  });
});

describe('CompressionMetrics', () => {
  let metric: CompressionMetrics;

  beforeEach(() => {
    metric = new CompressionMetrics();
  });

  test('has correct name', () => {
    expect(metric.name).toBe('compression_ratio');
  });

  test('measures from message metadata', async () => {
    const agent = new MockAgent();
    const input = createMessage('user', 'test');
    input.metadata = {
      raw_tokens: 1000,
      compressed_tokens: 200,
    };
    const output = createMessage('assistant', 'response');

    const ratio = await metric.measure(agent, input, output);

    expect(ratio).toBe(5.0); // 1000 / 200
  });

  test('measures from context', async () => {
    const agent = new MockAgent();
    const input = createMessage('user', 'test');
    const output = createMessage('assistant', 'response');

    const ratio = await metric.measure(agent, input, output, {
      raw_tokens: 5000,
      compressed_tokens: 1000,
    });

    expect(ratio).toBe(5.0);
  });

  test('returns 1.0 for no compression', async () => {
    const agent = new MockAgent();
    const input = createMessage('user', 'test');
    const output = createMessage('assistant', 'response');

    const ratio = await metric.measure(agent, input, output);

    expect(ratio).toBe(1.0);
  });

  test('handles zero compressed tokens', async () => {
    const agent = new MockAgent();
    const input = createMessage('user', 'test');
    input.metadata = {
      raw_tokens: 1000,
      compressed_tokens: 0,
    };
    const output = createMessage('assistant', 'response');

    const ratio = await metric.measure(agent, input, output);

    expect(ratio).toBe(1.0); // Fallback to 1.0 to avoid division by zero
  });

  test('aggregates compression ratios', () => {
    const measurements = [2.0, 3.0, 4.0, 5.0];

    const stats = metric.aggregate(measurements);

    expect(stats.mean).toBe(3.5);
    expect(stats.min).toBe(2.0);
    expect(stats.max).toBe(5.0);
    expect(stats.count).toBe(4);
  });

  test('aggregates empty measurements', () => {
    const stats = metric.aggregate([]);

    expect(stats.mean).toBe(1.0);
    expect(stats.min).toBe(1.0);
    expect(stats.max).toBe(1.0);
    expect(stats.count).toBe(0);
  });
});

describe('createCompressionStats', () => {
  test('creates compression stats', () => {
    const stats = createCompressionStats(10000, 2000, 0.95, 5000);

    expect(stats.rawTokens).toBe(10000);
    expect(stats.compressedTokens).toBe(2000);
    expect(stats.compressionRatio).toBe(5.0);
    expect(stats.retrievalAccuracy).toBe(0.95);
    expect(stats.contextLengthTested).toBe(5000);
    expect(stats.timestamp).toBeInstanceOf(Date);
  });
});

describe('compressionStatsToDict', () => {
  test('converts stats to dictionary', () => {
    const stats = createCompressionStats(10000, 2000, 0.95, 5000);
    const dict = compressionStatsToDict(stats);

    expect(dict.raw_tokens).toBe(10000);
    expect(dict.compressed_tokens).toBe(2000);
    expect(dict.compression_ratio).toBe(5.0);
    expect(dict.retrieval_accuracy).toBe(0.95);
    expect(dict.context_length_tested).toBe(5000);
    expect(typeof dict.timestamp).toBe('string');
  });
});

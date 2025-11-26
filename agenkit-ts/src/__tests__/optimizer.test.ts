/**
 * Tests for optimization framework.
 */

import { Agent, Message, createMessage } from '../core/interfaces';
import { TestCase } from '../evaluation/core';
import {
  SearchSpace,
  RandomSearchOptimizer,
  getOptimizationDuration,
  getOptimizationImprovement,
  optimizationResultToDict,
  OptimizationResult,
} from '../evaluation/optimizer';

// Mock agent for testing
class MockAgent implements Agent {
  name = 'mock-agent';
  capabilities = [];
  private config: Record<string, unknown>;

  constructor(config: Record<string, unknown>) {
    this.config = config;
  }

  async process(message: Message): Promise<Message> {
    // Simulate accuracy based on temperature (lower = better)
    const temperature = (this.config.temperature as number) || 0.5;
    const accuracy = 1.0 - temperature * 0.5; // Higher temp = lower accuracy

    return createMessage('assistant', `Response with accuracy ${accuracy}`);
  }

  getConfig(): Record<string, unknown> {
    return this.config;
  }
}

describe('SearchSpace', () => {
  let space: SearchSpace;

  beforeEach(() => {
    space = new SearchSpace();
  });

  test('addContinuous adds continuous parameter', () => {
    space.addContinuous('temperature', 0.0, 1.0);

    const param = space.getParameter('temperature');
    expect(param).toBeDefined();
    expect(param!.type).toBe('continuous');
    expect(param!.low).toBe(0.0);
    expect(param!.high).toBe(1.0);
  });

  test('addDiscrete adds discrete parameter', () => {
    space.addDiscrete('max_tokens', [128, 256, 512]);

    const param = space.getParameter('max_tokens');
    expect(param).toBeDefined();
    expect(param!.type).toBe('discrete');
    expect(param!.values).toEqual([128, 256, 512]);
  });

  test('addInteger adds integer parameter', () => {
    space.addInteger('n_samples', 10, 100);

    const param = space.getParameter('n_samples');
    expect(param).toBeDefined();
    expect(param!.type).toBe('integer');
    expect(param!.low).toBe(10);
    expect(param!.high).toBe(100);
  });

  test('addCategorical adds categorical parameter', () => {
    space.addCategorical('model', ['gpt-4', 'claude-3']);

    const param = space.getParameter('model');
    expect(param).toBeDefined();
    expect(param!.type).toBe('categorical');
    expect(param!.values).toEqual(['gpt-4', 'claude-3']);
  });

  test('sample generates valid configuration', () => {
    space.addContinuous('temperature', 0.0, 1.0);
    space.addDiscrete('max_tokens', [128, 256, 512]);
    space.addInteger('n_samples', 10, 100);
    space.addCategorical('model', ['gpt-4', 'claude-3']);

    const config = space.sample();

    expect(config.temperature).toBeGreaterThanOrEqual(0.0);
    expect(config.temperature).toBeLessThanOrEqual(1.0);
    expect([128, 256, 512]).toContain(config.max_tokens);
    expect(config.n_samples).toBeGreaterThanOrEqual(10);
    expect(config.n_samples).toBeLessThanOrEqual(100);
    expect(['gpt-4', 'claude-3']).toContain(config.model);
  });

  test('sample generates different configurations', () => {
    space.addContinuous('temperature', 0.0, 1.0);

    const config1 = space.sample();
    const config2 = space.sample();

    // Should be different (with very high probability)
    // Run multiple times to be sure
    let allSame = true;
    for (let i = 0; i < 10; i++) {
      const c1 = space.sample();
      const c2 = space.sample();
      if (c1.temperature !== c2.temperature) {
        allSame = false;
        break;
      }
    }

    expect(allSame).toBe(false);
  });

  test('validate accepts valid configuration', () => {
    space.addContinuous('temperature', 0.0, 1.0);
    space.addDiscrete('max_tokens', [128, 256, 512]);

    const config = {
      temperature: 0.5,
      max_tokens: 256,
    };

    expect(space.validate(config)).toBe(true);
  });

  test('validate rejects out-of-range continuous value', () => {
    space.addContinuous('temperature', 0.0, 1.0);

    const config = { temperature: 1.5 };

    expect(space.validate(config)).toBe(false);
  });

  test('validate rejects invalid discrete value', () => {
    space.addDiscrete('max_tokens', [128, 256, 512]);

    const config = { max_tokens: 999 };

    expect(space.validate(config)).toBe(false);
  });

  test('validate rejects non-integer for integer parameter', () => {
    space.addInteger('n_samples', 10, 100);

    const config = { n_samples: 50.5 };

    expect(space.validate(config)).toBe(false);
  });

  test('validate rejects invalid categorical value', () => {
    space.addCategorical('model', ['gpt-4', 'claude-3']);

    const config = { model: 'invalid-model' };

    expect(space.validate(config)).toBe(false);
  });

  test('validate rejects unknown parameter', () => {
    space.addContinuous('temperature', 0.0, 1.0);

    const config = { unknown_param: 0.5 };

    expect(space.validate(config)).toBe(false);
  });

  test('getParameterNames returns all parameter names', () => {
    space.addContinuous('temperature', 0.0, 1.0);
    space.addDiscrete('max_tokens', [128, 256, 512]);

    const names = space.getParameterNames();

    expect(names).toHaveLength(2);
    expect(names).toContain('temperature');
    expect(names).toContain('max_tokens');
  });

  test('size returns number of parameters', () => {
    expect(space.size()).toBe(0);

    space.addContinuous('temperature', 0.0, 1.0);
    expect(space.size()).toBe(1);

    space.addDiscrete('max_tokens', [128, 256, 512]);
    expect(space.size()).toBe(2);
  });

  test('getParameter returns undefined for non-existent parameter', () => {
    const param = space.getParameter('nonexistent');
    expect(param).toBeUndefined();
  });
});

describe('RandomSearchOptimizer', () => {
  let optimizer: RandomSearchOptimizer;
  let searchSpace: SearchSpace;
  let testCases: TestCase[];

  beforeEach(() => {
    searchSpace = new SearchSpace();
    searchSpace.addContinuous('temperature', 0.0, 1.0);

    optimizer = new RandomSearchOptimizer(
      (config) => new MockAgent(config),
      searchSpace,
      'accuracy'
    );

    testCases = [
      { input: 'test 1', expected: 'response' },
      { input: 'test 2', expected: 'response' },
      { input: 'test 3', expected: 'response' },
    ];
  });

  test('optimize runs specified iterations', async () => {
    const result = await optimizer.optimize(testCases, 5);

    expect(result.nIterations).toBe(5);
    expect(result.history).toHaveLength(5);
  });

  test('optimize finds best configuration', async () => {
    const result = await optimizer.optimize(testCases, 10);

    expect(result.bestConfig).toBeDefined();
    expect(result.bestScore).toBeDefined();
    expect(result.bestConfig.temperature).toBeGreaterThanOrEqual(0.0);
    expect(result.bestConfig.temperature).toBeLessThanOrEqual(1.0);
  });

  test('optimize tracks history', async () => {
    const result = await optimizer.optimize(testCases, 5);

    expect(result.history).toHaveLength(5);
    for (const [config, score] of result.history) {
      expect(config.temperature).toBeDefined();
      expect(typeof score).toBe('number');
    }
  });

  test('optimize selects best score from history', async () => {
    const result = await optimizer.optimize(testCases, 10);

    // Best score should be >= all other scores
    for (const [, score] of result.history) {
      expect(result.bestScore).toBeGreaterThanOrEqual(score);
    }
  });

  test('optimize includes timestamps', async () => {
    const result = await optimizer.optimize(testCases, 3);

    expect(result.startTime).toBeInstanceOf(Date);
    expect(result.endTime).toBeInstanceOf(Date);
    expect(result.endTime.getTime()).toBeGreaterThanOrEqual(result.startTime.getTime());
  });

  test('optimize includes metadata', async () => {
    const result = await optimizer.optimize(testCases, 3);

    expect(result.metadata).toBeDefined();
    expect(result.metadata.algorithm).toBe('random_search');
  });

  test('optimize with multiple parameters', async () => {
    const space2 = new SearchSpace();
    space2.addContinuous('temperature', 0.0, 1.0);
    space2.addDiscrete('max_tokens', [128, 256, 512]);

    const optimizer2 = new RandomSearchOptimizer(
      (config) => new MockAgent(config),
      space2,
      'accuracy'
    );

    const result = await optimizer2.optimize(testCases, 5);

    expect(result.bestConfig.temperature).toBeDefined();
    expect(result.bestConfig.max_tokens).toBeDefined();
  });

  test('optimize with minimize objective', async () => {
    const optimizer2 = new RandomSearchOptimizer(
      (config) => new MockAgent(config),
      searchSpace,
      'accuracy',
      false // minimize
    );

    const result = await optimizer2.optimize(testCases, 5);

    expect(result.bestConfig).toBeDefined();
    expect(result.bestScore).toBeDefined();
  });

  test('getHistory returns optimization history', async () => {
    await optimizer.optimize(testCases, 5);

    const history = optimizer.getHistory();

    expect(history).toHaveLength(5);
    expect(history).toEqual(optimizer.getHistory()); // Should be a copy
  });

  test('optimize handles empty test cases', async () => {
    const result = await optimizer.optimize([], 3);

    expect(result.nIterations).toBe(3);
    expect(result.history).toHaveLength(3);
  });
});

describe('Helper functions', () => {
  test('getOptimizationDuration calculates duration', () => {
    const result: OptimizationResult = {
      bestConfig: {},
      bestScore: 0.8,
      history: [],
      nIterations: 10,
      startTime: new Date('2025-01-01T00:00:00Z'),
      endTime: new Date('2025-01-01T00:01:00Z'),
      metadata: {},
    };

    const duration = getOptimizationDuration(result);
    expect(duration).toBe(60); // 60 seconds
  });

  test('getOptimizationImprovement calculates improvement', () => {
    const result: OptimizationResult = {
      bestConfig: {},
      bestScore: 0.9,
      history: [
        [{}, 0.6],
        [{}, 0.7],
        [{}, 0.9],
      ],
      nIterations: 3,
      startTime: new Date(),
      endTime: new Date(),
      metadata: {},
    };

    const improvement = getOptimizationImprovement(result);
    expect(improvement).toBeCloseTo(50, 1); // 50% improvement from 0.6 to 0.9
  });

  test('getOptimizationImprovement handles empty history', () => {
    const result: OptimizationResult = {
      bestConfig: {},
      bestScore: 0.9,
      history: [],
      nIterations: 0,
      startTime: new Date(),
      endTime: new Date(),
      metadata: {},
    };

    const improvement = getOptimizationImprovement(result);
    expect(improvement).toBe(0);
  });

  test('getOptimizationImprovement handles zero initial score', () => {
    const result: OptimizationResult = {
      bestConfig: {},
      bestScore: 0.9,
      history: [[{}, 0]],
      nIterations: 1,
      startTime: new Date(),
      endTime: new Date(),
      metadata: {},
    };

    const improvement = getOptimizationImprovement(result);
    expect(improvement).toBe(0);
  });

  test('optimizationResultToDict converts to plain object', () => {
    const result: OptimizationResult = {
      bestConfig: { temperature: 0.5 },
      bestScore: 0.8,
      history: [[{ temperature: 0.5 }, 0.8]],
      nIterations: 1,
      startTime: new Date('2025-01-01T00:00:00Z'),
      endTime: new Date('2025-01-01T00:01:00Z'),
      metadata: { algorithm: 'random_search' },
    };

    const dict = optimizationResultToDict(result);

    expect(dict.best_config).toEqual({ temperature: 0.5 });
    expect(dict.best_score).toBe(0.8);
    expect(dict.n_iterations).toBe(1);
    expect(dict.duration_seconds).toBe(60);
    expect(dict.start_time).toBe('2025-01-01T00:00:00.000Z');
    expect(dict.end_time).toBe('2025-01-01T00:01:00.000Z');
    expect(dict.metadata).toEqual({ algorithm: 'random_search' });
    expect(dict.improvement_percent).toBeDefined();
  });
});

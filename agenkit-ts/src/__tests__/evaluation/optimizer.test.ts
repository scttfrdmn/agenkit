/**
 * Tests for hyperparameter optimization.
 *
 * Tests SearchSpace, OptimizationResult, and RandomSearchOptimizer.
 */

import { describe, it, expect } from 'vitest';
import {
  SearchSpace,
  OptimizationResult,
  RandomSearchOptimizer,
  ParameterType,
} from '../../evaluation/optimizer';
import type { Agent, Message } from '../../core/interfaces';
import { createMessage } from '../../core/interfaces';

// Mock agent factory for testing
function createMockAgentFactory(
  scoreFn: (params: Record<string, unknown>) => number
): (params: Record<string, unknown>) => Agent {
  return (params: Record<string, unknown>) => {
    return {
      name: 'mock-agent',
      capabilities: [],
      async process(message: Message): Promise<Message> {
        const score = scoreFn(params);
        return createMessage('assistant', `Score: ${score}`);
      },
    };
  };
}

// ============================================
// SearchSpace Tests
// ============================================

describe('SearchSpace', () => {
  it('should create search space with parameters', () => {
    const space = new SearchSpace({
      temperature: { type: ParameterType.Continuous, min: 0, max: 1 },
      topK: { type: ParameterType.Discrete, values: [1, 5, 10, 20] },
    });

    expect(space.parameters).toHaveProperty('temperature');
    expect(space.parameters).toHaveProperty('topK');
  });

  it('should sample continuous parameters', () => {
    const space = new SearchSpace({
      temperature: { type: ParameterType.Continuous, min: 0, max: 1 },
    });

    const sample = space.sample();

    expect(sample.temperature).toBeGreaterThanOrEqual(0);
    expect(sample.temperature).toBeLessThanOrEqual(1);
  });

  it('should sample discrete parameters', () => {
    const space = new SearchSpace({
      topK: { type: ParameterType.Discrete, values: [1, 5, 10] },
    });

    const sample = space.sample();

    expect([1, 5, 10]).toContain(sample.topK);
  });

  it('should sample categorical parameters', () => {
    const space = new SearchSpace({
      model: { type: ParameterType.Categorical, values: ['gpt-4', 'claude-3'] },
    });

    const sample = space.sample();

    expect(['gpt-4', 'claude-3']).toContain(sample.model);
  });

  it('should sample multiple parameters', () => {
    const space = new SearchSpace({
      temperature: { type: ParameterType.Continuous, min: 0, max: 1 },
      topK: { type: ParameterType.Discrete, values: [1, 5, 10] },
      model: { type: ParameterType.Categorical, values: ['gpt-4', 'claude'] },
    });

    const sample = space.sample();

    expect(sample).toHaveProperty('temperature');
    expect(sample).toHaveProperty('topK');
    expect(sample).toHaveProperty('model');
  });
});

// ============================================
// OptimizationResult Tests
// ============================================

describe('OptimizationResult', () => {
  it('should create optimization result', () => {
    const result = new OptimizationResult({
      bestParams: { temperature: 0.7 },
      bestScore: 0.95,
      allTrials: [],
      iterations: 10,
    });

    expect(result.bestParams).toEqual({ temperature: 0.7 });
    expect(result.bestScore).toBe(0.95);
    expect(result.iterations).toBe(10);
  });

  it('should track trial history', () => {
    const trials = [
      { params: { temp: 0.5 }, score: 0.8 },
      { params: { temp: 0.7 }, score: 0.9 },
    ];

    const result = new OptimizationResult({
      bestParams: { temp: 0.7 },
      bestScore: 0.9,
      allTrials: trials,
      iterations: 2,
    });

    expect(result.allTrials).toHaveLength(2);
    expect(result.allTrials[1].score).toBe(0.9);
  });
});

// ============================================
// RandomSearchOptimizer Tests
// ============================================

describe('RandomSearchOptimizer', () => {
  it('should create optimizer with search space', () => {
    const space = new SearchSpace({
      temperature: { type: ParameterType.Continuous, min: 0, max: 1 },
    });

    const optimizer = new RandomSearchOptimizer(space);

    expect(optimizer.searchSpace).toBe(space);
  });

  it('should optimize and find best parameters', async () => {
    const space = new SearchSpace({
      value: { type: ParameterType.Continuous, min: 0, max: 10 },
    });

    // Factory that scores based on how close value is to 7
    const factory = createMockAgentFactory((params) => {
      const value = params.value as number;
      return 1.0 - Math.abs(value - 7) / 10;
    });

    const optimizer = new RandomSearchOptimizer(space);

    const result = await optimizer.optimize({
      agentFactory: factory,
      testCases: [{ input: 'test', expected: 'test' }],
      iterations: 20,
    });

    expect(result.bestScore).toBeGreaterThan(0);
    expect(result.iterations).toBe(20);
    expect(result.bestParams.value).toBeGreaterThanOrEqual(0);
    expect(result.bestParams.value).toBeLessThanOrEqual(10);
  });

  it('should track improvement over iterations', async () => {
    const space = new SearchSpace({
      value: { type: ParameterType.Discrete, values: [1, 5, 9] },
    });

    const factory = createMockAgentFactory((params) => {
      return (params.value as number) / 10; // Higher value = higher score
    });

    const optimizer = new RandomSearchOptimizer(space);

    const result = await optimizer.optimize({
      agentFactory: factory,
      testCases: [{ input: 'test', expected: 'test' }],
      iterations: 15,
    });

    expect(result.allTrials.length).toBe(15);
    expect(result.bestParams.value).toBe(9); // Should find highest value
  });

  it('should handle multiple parameters', async () => {
    const space = new SearchSpace({
      temperature: { type: ParameterType.Continuous, min: 0, max: 1 },
      topK: { type: ParameterType.Discrete, values: [1, 5, 10] },
    });

    const factory = createMockAgentFactory((params) => {
      const temp = params.temperature as number;
      const topK = params.topK as number;
      return temp * 0.5 + (topK / 10) * 0.5; // Combine both parameters
    });

    const optimizer = new RandomSearchOptimizer(space);

    const result = await optimizer.optimize({
      agentFactory: factory,
      testCases: [{ input: 'test', expected: 'test' }],
      iterations: 10,
    });

    expect(result.bestParams).toHaveProperty('temperature');
    expect(result.bestParams).toHaveProperty('topK');
  });

  it('should respect iteration limit', async () => {
    const space = new SearchSpace({
      value: { type: ParameterType.Continuous, min: 0, max: 1 },
    });

    const factory = createMockAgentFactory(() => 0.5);

    const optimizer = new RandomSearchOptimizer(space);

    const result = await optimizer.optimize({
      agentFactory: factory,
      testCases: [{ input: 'test', expected: 'test' }],
      iterations: 5,
    });

    expect(result.iterations).toBe(5);
    expect(result.allTrials).toHaveLength(5);
  });
});

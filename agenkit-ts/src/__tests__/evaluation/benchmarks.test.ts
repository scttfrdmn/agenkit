/**
 * Tests for benchmark suites.
 *
 * Tests SimpleQABenchmark, NeedleInHaystackBenchmark, ExtremeScaleBenchmark,
 * InformationRetentionBenchmark, and BenchmarkSuite.
 */

import { describe, it, expect } from 'vitest';
import {
  SimpleQABenchmark,
  ReasoningBenchmark,
  NeedleInHaystackBenchmark,
  ExtremeScaleBenchmark,
  InformationRetentionBenchmark,
  BenchmarkSuite,
} from '../../evaluation/benchmarks';

// ============================================
// SimpleQABenchmark Tests
// ============================================

describe('SimpleQABenchmark', () => {
  it('should create benchmark with correct name and description', () => {
    const benchmark = new SimpleQABenchmark();

    expect(benchmark.name).toBe('simple_qa');
    expect(benchmark.description).toContain('question');
  });

  it('should generate test cases', async () => {
    const benchmark = new SimpleQABenchmark();
    const testCases = await benchmark.generateTestCases();

    expect(testCases.length).toBeGreaterThan(0);
    expect(testCases.every((tc) => tc.input)).toBe(true);
    expect(testCases.every((tc) => tc.expected)).toBe(true);
    expect(testCases.every((tc) => tc.tags)).toBe(true);
  });

  it('should include math questions', async () => {
    const benchmark = new SimpleQABenchmark();
    const testCases = await benchmark.generateTestCases();

    const mathCases = testCases.filter((tc) => tc.tags?.includes('math'));
    expect(mathCases.length).toBeGreaterThan(0);
  });

  it('should include knowledge questions', async () => {
    const benchmark = new SimpleQABenchmark();
    const testCases = await benchmark.generateTestCases();

    const knowledgeCases = testCases.filter((tc) => tc.tags?.includes('knowledge'));
    expect(knowledgeCases.length).toBeGreaterThan(0);
  });
});

// ============================================
// ReasoningBenchmark Tests
// ============================================

describe('ReasoningBenchmark', () => {
  it('should create reasoning benchmark', () => {
    const benchmark = new ReasoningBenchmark();

    expect(benchmark.name).toBe('reasoning');
    expect(benchmark.description).toContain('reasoning');
  });

  it('should generate multi-step problems', async () => {
    const benchmark = new ReasoningBenchmark();
    const testCases = await benchmark.generateTestCases();

    expect(testCases.length).toBeGreaterThan(0);
    expect(testCases.every((tc) => tc.tags?.includes('reasoning'))).toBe(true);
  });
});

// ============================================
// NeedleInHaystackBenchmark Tests
// ============================================

describe('NeedleInHaystackBenchmark', () => {
  it('should create needle-in-haystack benchmark', () => {
    const benchmark = new NeedleInHaystackBenchmark({ contextLength: 1000, needleCount: 3 });

    expect(benchmark.name).toContain('needle_in_haystack');
    expect(benchmark.description).toContain('1000');
  });

  it('should generate correct number of test cases', async () => {
    const benchmark = new NeedleInHaystackBenchmark({ contextLength: 1000, needleCount: 3 });
    const testCases = await benchmark.generateTestCases();

    expect(testCases).toHaveLength(3); // One test per needle
  });

  it('should embed needles in haystack', async () => {
    const benchmark = new NeedleInHaystackBenchmark({ contextLength: 1000, needleCount: 2 });
    const testCases = await benchmark.generateTestCases();

    // Check that expected value appears in input
    for (const tc of testCases) {
      expect(tc.input).toContain(tc.expected as string);
    }
  });

  it('should tag cases with retrieval and context', async () => {
    const benchmark = new NeedleInHaystackBenchmark({ contextLength: 1000, needleCount: 2 });
    const testCases = await benchmark.generateTestCases();

    expect(testCases.every((tc) => tc.tags?.includes('retrieval'))).toBe(true);
    expect(testCases.every((tc) => tc.tags?.includes('context'))).toBe(true);
  });

  it('should generate haystack of specified length', async () => {
    const contextLength = 500;
    const benchmark = new NeedleInHaystackBenchmark({ contextLength, needleCount: 1 });
    const testCases = await benchmark.generateTestCases();

    // Input should be approximately the context length (within 20%)
    const input = testCases[0].input;
    expect(input.length).toBeGreaterThan(contextLength * 0.8);
  });
});

// ============================================
// ExtremeScaleBenchmark Tests
// ============================================

describe('ExtremeScaleBenchmark', () => {
  it('should create extreme-scale benchmark', () => {
    const benchmark = new ExtremeScaleBenchmark([10000, 100000], 2);

    expect(benchmark.name).toBe('extreme_scale');
    expect(benchmark.description).toContain('retrieval');
  });

  it('should generate test cases for each length', async () => {
    const benchmark = new ExtremeScaleBenchmark([10000, 100000], 2);
    const testCases = await benchmark.generateTestCases();

    // 2 lengths * 2 needles = 4 test cases
    expect(testCases).toHaveLength(4);
  });

  it('should tag cases with extreme_scale', async () => {
    const benchmark = new ExtremeScaleBenchmark([10000], 1);
    const testCases = await benchmark.generateTestCases();

    expect(testCases.every((tc) => tc.tags?.includes('extreme_scale'))).toBe(true);
  });

  it('should support single length', async () => {
    const benchmark = new ExtremeScaleBenchmark([50000], 3);
    const testCases = await benchmark.generateTestCases();

    expect(testCases).toHaveLength(3);
  });
});

// ============================================
// InformationRetentionBenchmark Tests
// ============================================

describe('InformationRetentionBenchmark', () => {
  it('should create information retention benchmark', () => {
    const benchmark = new InformationRetentionBenchmark(100, [25, 50, 75]);

    expect(benchmark.name).toBe('information_retention');
    expect(benchmark.description).toContain('recall');
  });

  it('should generate plant and recall test cases', async () => {
    const benchmark = new InformationRetentionBenchmark(100, [25, 50, 75]);
    const testCases = await benchmark.generateTestCases();

    expect(testCases.length).toBeGreaterThan(0);

    const plantCases = testCases.filter((tc) => tc.metadata?.type === 'fact_plant');
    const recallCases = testCases.filter((tc) => tc.metadata?.type === 'recall_test');

    expect(plantCases.length).toBeGreaterThan(0);
    expect(recallCases.length).toBeGreaterThan(0);
  });

  it('should create recall points at specified intervals', async () => {
    const recallPoints = [20, 40, 60];
    const benchmark = new InformationRetentionBenchmark(80, recallPoints);
    const testCases = await benchmark.generateTestCases();

    const recallCases = testCases.filter((tc) => tc.metadata?.type === 'recall_test');

    // Should have recall tests at each recall point
    expect(recallCases.length).toBeGreaterThanOrEqual(recallPoints.length);
  });

  it('should tag retention test cases', async () => {
    const benchmark = new InformationRetentionBenchmark(50, [25]);
    const testCases = await benchmark.generateTestCases();

    const retentionCases = testCases.filter((tc) => tc.tags?.includes('retention'));
    expect(retentionCases.length).toBeGreaterThan(0);
  });
});

// ============================================
// BenchmarkSuite Tests
// ============================================

describe('BenchmarkSuite', () => {
  it('should create suite with multiple benchmarks', () => {
    const benchmarks = [new SimpleQABenchmark(), new ReasoningBenchmark()];
    const suite = new BenchmarkSuite('comprehensive', benchmarks);

    expect(suite.name).toBe('comprehensive');
    expect(suite.benchmarks).toHaveLength(2);
  });

  it('should generate test cases from all benchmarks', async () => {
    const benchmarks = [new SimpleQABenchmark(), new ReasoningBenchmark()];
    const suite = new BenchmarkSuite('combined', benchmarks);

    const testCases = await suite.generateTestCases();

    expect(testCases.length).toBeGreaterThan(0);
  });

  it('should run all benchmarks', async () => {
    const benchmarks = [new SimpleQABenchmark()];
    const suite = new BenchmarkSuite('test_suite', benchmarks);

    const results = await suite.run(async (testCase) => {
      // Mock evaluation - always returns 1.0
      return {
        input: testCase.input,
        expected: testCase.expected as string,
        actual: testCase.expected as string,
        score: 1.0,
      };
    });

    expect(results).toBeDefined();
    expect(results.benchmarks).toHaveLength(1);
    expect(results.overallScore).toBeGreaterThan(0);
  });

  it('should aggregate scores across benchmarks', async () => {
    const benchmarks = [new SimpleQABenchmark(), new ReasoningBenchmark()];
    const suite = new BenchmarkSuite('aggregate_test', benchmarks);

    const results = await suite.run(async (testCase) => {
      return {
        input: testCase.input,
        expected: testCase.expected as string,
        actual: testCase.expected as string,
        score: 0.8,
      };
    });

    expect(results.overallScore).toBeCloseTo(0.8, 1);
  });

  it('should handle empty suite', async () => {
    const suite = new BenchmarkSuite('empty', []);
    const testCases = await suite.generateTestCases();

    expect(testCases).toHaveLength(0);
  });
});

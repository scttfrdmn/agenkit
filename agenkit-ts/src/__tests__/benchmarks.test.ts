/**
 * Tests for Benchmarks module.
 */

import {
  SimpleQABenchmark,
  ReasoningBenchmark,
  NeedleInHaystackBenchmark,
  CodeGenerationBenchmark,
  getAllBenchmarks,
  getBenchmarkByName,
  runBenchmark,
  TestCase,
} from '../evaluation/benchmarks';

describe('SimpleQABenchmark', () => {
  it('should have correct metadata', () => {
    const benchmark = new SimpleQABenchmark();

    expect(benchmark.name).toBe('simple_qa');
    expect(benchmark.description).toBe('Basic question-answering tasks');
  });

  it('should generate test cases', async () => {
    const benchmark = new SimpleQABenchmark();
    const testCases = await benchmark.generateTestCases();

    expect(testCases.length).toBeGreaterThan(0);
    expect(testCases[0]).toHaveProperty('input');
    expect(testCases[0]).toHaveProperty('expected');
    expect(testCases[0]).toHaveProperty('tags');
  });

  it('should have valid test case structure', async () => {
    const benchmark = new SimpleQABenchmark();
    const testCases = await benchmark.generateTestCases();

    for (const testCase of testCases) {
      expect(typeof testCase.input).toBe('string');
      expect(typeof testCase.expected).toBe('string');
      expect(Array.isArray(testCase.tags)).toBe(true);
    }
  });

  it('should include expected answers', async () => {
    const benchmark = new SimpleQABenchmark();
    const testCases = await benchmark.generateTestCases();

    const mathQuestion = testCases.find(tc => tc.input.includes('2+2'));
    expect(mathQuestion).toBeDefined();
    expect(mathQuestion?.expected).toBe('4');
  });
});

describe('ReasoningBenchmark', () => {
  it('should have correct metadata', () => {
    const benchmark = new ReasoningBenchmark();

    expect(benchmark.name).toBe('reasoning');
    expect(benchmark.description).toBe('Multi-step reasoning and logic problems');
  });

  it('should generate test cases', async () => {
    const benchmark = new ReasoningBenchmark();
    const testCases = await benchmark.generateTestCases();

    expect(testCases.length).toBeGreaterThan(0);
    expect(testCases.length).toBeGreaterThanOrEqual(5);
  });

  it('should include logic problems', async () => {
    const benchmark = new ReasoningBenchmark();
    const testCases = await benchmark.generateTestCases();

    const logicProblem = testCases.find(tc => tc.input.includes('roses'));
    expect(logicProblem).toBeDefined();
    expect(logicProblem?.tags).toContain('logic');
  });

  it('should tag test cases appropriately', async () => {
    const benchmark = new ReasoningBenchmark();
    const testCases = await benchmark.generateTestCases();

    const hasMath = testCases.some(tc => tc.tags?.includes('math'));
    const hasLogic = testCases.some(tc => tc.tags?.includes('logic'));

    expect(hasMath || hasLogic).toBe(true);
  });
});

describe('NeedleInHaystackBenchmark', () => {
  it('should have correct default configuration', () => {
    const benchmark = new NeedleInHaystackBenchmark();

    // 10000/5 matches Python, Go, Rust and C++ (#790).
    expect(benchmark.contextLength).toBe(10_000);
    expect(benchmark.needleCount).toBe(5);
    expect(benchmark.name).toBe('needle_in_haystack_10000');
  });

  it('should accept custom configuration', () => {
    const benchmark = new NeedleInHaystackBenchmark({
      contextLength: 5000,
      needleCount: 5,
    });

    expect(benchmark.contextLength).toBe(5000);
    expect(benchmark.needleCount).toBe(5);
    expect(benchmark.name).toBe('needle_in_haystack_5000');
  });

  it('should generate test cases with needles', async () => {
    const benchmark = new NeedleInHaystackBenchmark({
      contextLength: 500,
      needleCount: 2,
    });
    const testCases = await benchmark.generateTestCases();

    expect(testCases.length).toBe(2);
  });

  it('should embed needles in haystack', async () => {
    const benchmark = new NeedleInHaystackBenchmark({
      contextLength: 500,
      needleCount: 2,
    });
    const testCases = await benchmark.generateTestCases();

    for (const testCase of testCases) {
      expect(testCase.input).toContain('Context:');
      expect(testCase.input).toContain('Question:');
      expect(testCase.input).toContain('ALPHA-');
      expect(testCase.input).toContain('-OMEGA');
    }
  });

  it('should include metadata', async () => {
    const benchmark = new NeedleInHaystackBenchmark();
    const testCases = await benchmark.generateTestCases();

    for (const testCase of testCases) {
      expect(testCase.metadata).toBeDefined();
      expect(testCase.metadata?.needlePosition).toBeDefined();
      expect(testCase.metadata?.totalNeedles).toBe(5);
    }
  });

  it('should generate different codes for each needle', async () => {
    const benchmark = new NeedleInHaystackBenchmark({ needleCount: 3 });
    const testCases = await benchmark.generateTestCases();

    const codes = testCases.map(tc => tc.expected);
    const uniqueCodes = new Set(codes);

    expect(uniqueCodes.size).toBe(codes.length);
  });
});

describe('CodeGenerationBenchmark', () => {
  it('should have correct metadata', () => {
    const benchmark = new CodeGenerationBenchmark();

    expect(benchmark.name).toBe('code_generation');
    expect(benchmark.description).toBe('Generate simple code snippets');
  });

  it('should generate test cases', async () => {
    const benchmark = new CodeGenerationBenchmark();
    const testCases = await benchmark.generateTestCases();

    expect(testCases.length).toBeGreaterThan(0);
  });

  it('should use validation functions for expected', async () => {
    const benchmark = new CodeGenerationBenchmark();
    const testCases = await benchmark.generateTestCases();

    for (const testCase of testCases) {
      expect(typeof testCase.expected).toBe('function');
    }
  });

  it('should validate code snippets correctly', async () => {
    const benchmark = new CodeGenerationBenchmark();
    const testCases = await benchmark.generateTestCases();

    const sumTestCase = testCases.find(tc => tc.input.includes('sum'));
    expect(sumTestCase).toBeDefined();

    if (typeof sumTestCase!.expected === 'function') {
      const validCode = 'function sum(a, b) { return a + b; }';
      const invalidCode = 'just some random text';

      expect(sumTestCase!.expected(validCode)).toBe(true);
      expect(sumTestCase!.expected(invalidCode)).toBe(false);
    }
  });
});

describe('Benchmark Utilities', () => {
  describe('getAllBenchmarks', () => {
    it('should return all benchmarks', () => {
      const benchmarks = getAllBenchmarks();

      expect(benchmarks.length).toBeGreaterThan(0);
      expect(benchmarks.every(b => b.name && b.description)).toBe(true);
    });

    it('should include standard benchmarks', () => {
      const benchmarks = getAllBenchmarks();
      const names = benchmarks.map(b => b.name);

      expect(names).toContain('simple_qa');
      expect(names).toContain('reasoning');
      expect(names).toContain('code_generation');
    });
  });

  describe('getBenchmarkByName', () => {
    it('should find benchmark by name', () => {
      const benchmark = getBenchmarkByName('simple_qa');

      expect(benchmark).toBeDefined();
      expect(benchmark?.name).toBe('simple_qa');
    });

    it('should return undefined for unknown benchmark', () => {
      const benchmark = getBenchmarkByName('nonexistent');

      expect(benchmark).toBeUndefined();
    });
  });

  describe('runBenchmark', () => {
    it('should run benchmark and return results', async () => {
      const benchmark = new SimpleQABenchmark();

      // Mock evaluate function that passes all tests
      const evaluateFn = async (testCase: TestCase) => {
        return testCase.input.includes('2+2');
      };

      const result = await runBenchmark(benchmark, evaluateFn);

      expect(result.benchmarkName).toBe('simple_qa');
      expect(result.totalTests).toBeGreaterThan(0);
      expect(result.passed + result.failed).toBe(result.totalTests);
      expect(result.results.length).toBe(result.totalTests);
    });

    it('should calculate accuracy correctly', async () => {
      const benchmark = new SimpleQABenchmark();

      // Always pass
      const result = await runBenchmark(benchmark, async () => true);

      expect(result.accuracy).toBe(100);
      expect(result.passed).toBe(result.totalTests);
      expect(result.failed).toBe(0);
    });

    it('should handle failures', async () => {
      const benchmark = new SimpleQABenchmark();

      // Always fail
      const result = await runBenchmark(benchmark, async () => false);

      expect(result.accuracy).toBe(0);
      expect(result.passed).toBe(0);
      expect(result.failed).toBe(result.totalTests);
    });

    it('should measure duration', async () => {
      const benchmark = new SimpleQABenchmark();

      const result = await runBenchmark(benchmark, async () => {
        await new Promise(resolve => setTimeout(resolve, 10));
        return true;
      });

      expect(result.totalDuration).toBeGreaterThan(0);
      expect(result.averageDuration).toBeGreaterThan(0);
    });

    it('should handle errors gracefully', async () => {
      const benchmark = new SimpleQABenchmark();

      const result = await runBenchmark(benchmark, async () => {
        throw new Error('Test error');
      });

      expect(result.failed).toBe(result.totalTests);
      expect(result.results.every(r => r.error !== undefined)).toBe(true);
    });

    it('should include test case details in results', async () => {
      const benchmark = new SimpleQABenchmark();

      const result = await runBenchmark(benchmark, async () => true);

      for (const testResult of result.results) {
        expect(testResult.input).toBeDefined();
        expect(testResult.expected).toBeDefined();
        expect(testResult.passed).toBeDefined();
        expect(testResult.duration).toBeDefined();
        expect(testResult.tags).toBeDefined();
      }
    });
  });
});

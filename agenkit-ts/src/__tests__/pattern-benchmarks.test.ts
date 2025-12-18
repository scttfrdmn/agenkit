/**
 * Tests for Pattern Benchmarks module.
 */

import * as fs from 'fs';
import * as path from 'path';
import {
  PatternBenchmark,
  YAMLBenchmarkLoader,
  PatternBenchmarkSuite,
} from '../evaluation/pattern-benchmarks';
import { Agent, Message } from '../interfaces';

// Mock agent for testing
class MockAgent implements Agent {
  constructor(private config: Record<string, unknown> = {}) {}

  get name(): string {
    return 'mock_agent';
  }

  async process(message: Message): Promise<Message> {
    return {
      role: 'assistant',
      content: `Processed: ${message.content}`,
      metadata: {
        pattern: this.config.pattern || 'test',
        processed: true,
      },
    };
  }
}

describe('PatternBenchmark', () => {
  it('should create benchmark with correct properties', () => {
    const testCases = [
      {
        input: 'test input',
        expected: 'test output',
        tags: ['test'],
      },
    ];

    const benchmark = new PatternBenchmark('test_pattern', 'Test description', testCases);

    expect(benchmark.name).toBe('test_pattern_benchmark');
    expect(benchmark.description).toBe('Test description');
    expect(benchmark.patternName).toBe('test_pattern');
  });

  it('should generate test cases', async () => {
    const testCases = [
      {
        input: 'test input 1',
        expected: 'test output 1',
        tags: ['test'],
      },
      {
        input: 'test input 2',
        expected: 'test output 2',
        tags: ['test'],
      },
    ];

    const benchmark = new PatternBenchmark('test_pattern', 'Test description', testCases);
    const generated = await benchmark.generateTestCases();

    expect(generated).toHaveLength(2);
    expect(generated[0].input).toBe('test input 1');
    expect(generated[1].input).toBe('test input 2');
  });
});

describe('YAMLBenchmarkLoader', () => {
  const specsDir = path.resolve(__dirname, '../../../../tests/cross_language/specs');

  it('should create loader with valid directory', () => {
    // Skip if specs directory doesn't exist
    if (!fs.existsSync(specsDir)) {
      console.warn(`Skipping test: specs directory not found at ${specsDir}`);
      return;
    }

    const loader = new YAMLBenchmarkLoader(specsDir);
    expect(loader).toBeDefined();
  });

  it('should throw error for invalid directory', () => {
    expect(() => {
      new YAMLBenchmarkLoader('/non/existent/path');
    }).toThrow('Specs directory not found');
  });

  it('should load reflection pattern benchmark', () => {
    // Skip if specs directory doesn't exist
    if (!fs.existsSync(specsDir)) {
      console.warn(`Skipping test: specs directory not found at ${specsDir}`);
      return;
    }

    const loader = new YAMLBenchmarkLoader(specsDir);
    const benchmark = loader.loadPatternBenchmark('reflection');

    expect(benchmark).toBeDefined();
    expect(benchmark.patternName).toBe('reflection');
    expect(benchmark.name).toContain('reflection');
  });

  it('should generate test cases from YAML', async () => {
    // Skip if specs directory doesn't exist
    if (!fs.existsSync(specsDir)) {
      console.warn(`Skipping test: specs directory not found at ${specsDir}`);
      return;
    }

    const loader = new YAMLBenchmarkLoader(specsDir);
    const benchmark = loader.loadPatternBenchmark('reflection');
    const testCases = await benchmark.generateTestCases();

    expect(testCases.length).toBeGreaterThan(0);
    expect(testCases[0]).toHaveProperty('input');
    expect(testCases[0]).toHaveProperty('expected');
    expect(testCases[0]).toHaveProperty('tags');
  });

  it('should include proper metadata in test cases', async () => {
    // Skip if specs directory doesn't exist
    if (!fs.existsSync(specsDir)) {
      console.warn(`Skipping test: specs directory not found at ${specsDir}`);
      return;
    }

    const loader = new YAMLBenchmarkLoader(specsDir);
    const benchmark = loader.loadPatternBenchmark('reflection');
    const testCases = await benchmark.generateTestCases();

    for (const testCase of testCases) {
      expect(testCase.metadata).toBeDefined();
      expect(testCase.metadata?.pattern).toBe('reflection');
      expect(testCase.metadata?.scenario_id).toBeDefined();
      expect(testCase.metadata?.config).toBeDefined();
    }
  });

  it('should include yaml_generated tag', async () => {
    // Skip if specs directory doesn't exist
    if (!fs.existsSync(specsDir)) {
      console.warn(`Skipping test: specs directory not found at ${specsDir}`);
      return;
    }

    const loader = new YAMLBenchmarkLoader(specsDir);
    const benchmark = loader.loadPatternBenchmark('reflection');
    const testCases = await benchmark.generateTestCases();

    for (const testCase of testCases) {
      expect(testCase.tags).toContain('yaml_generated');
      expect(testCase.tags).toContain('reflection');
    }
  });

  it('should load all pattern benchmarks', () => {
    // Skip if specs directory doesn't exist
    if (!fs.existsSync(specsDir)) {
      console.warn(`Skipping test: specs directory not found at ${specsDir}`);
      return;
    }

    const loader = new YAMLBenchmarkLoader(specsDir);
    const benchmarks = loader.loadAllPatternBenchmarks();

    expect(benchmarks.length).toBeGreaterThan(0);
    expect(benchmarks.length).toBeGreaterThanOrEqual(10); // At least 10 patterns
  });

  it('should create validators from expected output', async () => {
    // Skip if specs directory doesn't exist
    if (!fs.existsSync(specsDir)) {
      console.warn(`Skipping test: specs directory not found at ${specsDir}`);
      return;
    }

    const loader = new YAMLBenchmarkLoader(specsDir);
    const benchmark = loader.loadPatternBenchmark('reflection');
    const testCases = await benchmark.generateTestCases();

    // Test that expected is a function (validator)
    const testCase = testCases[0];
    expect(typeof testCase.expected).toBe('function');

    // Test validator with mock message
    const mockMessage: Message = {
      role: 'assistant',
      content: 'test response',
      metadata: {},
    };

    const validator = testCase.expected as (msg: Message) => boolean;
    const result = validator(mockMessage);
    expect(typeof result).toBe('boolean');
  });
});

describe('PatternBenchmarkSuite', () => {
  const specsDir = path.resolve(__dirname, '../../../../tests/cross_language/specs');

  it('should create empty suite', () => {
    const suite = new PatternBenchmarkSuite();
    expect(suite.getAllBenchmarks()).toHaveLength(0);
  });

  it('should create suite with benchmarks', () => {
    const testCases = [
      {
        input: 'test',
        expected: 'output',
        tags: ['test'],
      },
    ];
    const benchmark = new PatternBenchmark('test', 'Test', testCases);
    const suite = new PatternBenchmarkSuite([benchmark]);

    expect(suite.getAllBenchmarks()).toHaveLength(1);
  });

  it('should load from YAML specs', () => {
    // Skip if specs directory doesn't exist
    if (!fs.existsSync(specsDir)) {
      console.warn(`Skipping test: specs directory not found at ${specsDir}`);
      return;
    }

    const suite = PatternBenchmarkSuite.fromYamlSpecs(specsDir);
    expect(suite.getAllBenchmarks().length).toBeGreaterThan(0);
  });

  it('should get benchmark by name', () => {
    // Skip if specs directory doesn't exist
    if (!fs.existsSync(specsDir)) {
      console.warn(`Skipping test: specs directory not found at ${specsDir}`);
      return;
    }

    const suite = PatternBenchmarkSuite.fromYamlSpecs(specsDir);
    const reflection = suite.getBenchmark('reflection');

    expect(reflection).toBeDefined();
    expect(reflection?.patternName).toBe('reflection');
  });

  it('should return undefined for non-existent benchmark', () => {
    const suite = new PatternBenchmarkSuite();
    const result = suite.getBenchmark('non_existent');

    expect(result).toBeUndefined();
  });

  it('should filter benchmarks by tag', () => {
    // Skip if specs directory doesn't exist
    if (!fs.existsSync(specsDir)) {
      console.warn(`Skipping test: specs directory not found at ${specsDir}`);
      return;
    }

    const suite = PatternBenchmarkSuite.fromYamlSpecs(specsDir);
    const yamlBenchmarks = suite.getBenchmarksByTag('yaml_generated');

    expect(yamlBenchmarks.length).toBeGreaterThan(0);
  });

  it('should run individual benchmark', async () => {
    // Skip if specs directory doesn't exist
    if (!fs.existsSync(specsDir)) {
      console.warn(`Skipping test: specs directory not found at ${specsDir}`);
      return;
    }

    const suite = PatternBenchmarkSuite.fromYamlSpecs(specsDir);
    const benchmark = suite.getBenchmark('reflection');

    if (!benchmark) {
      throw new Error('Reflection benchmark not found');
    }

    const agentFactory = (config: Record<string, unknown>) => new MockAgent(config);

    const results = await suite.runBenchmark(benchmark, agentFactory);

    expect(results.pattern).toBe('reflection');
    expect(results.summary.total).toBeGreaterThan(0);
    expect(results.summary.total).toBe(
      results.summary.passed + results.summary.failed
    );
    expect(results.test_cases.length).toBe(results.summary.total);
  });

  it('should track timing in benchmark results', async () => {
    // Skip if specs directory doesn't exist
    if (!fs.existsSync(specsDir)) {
      console.warn(`Skipping test: specs directory not found at ${specsDir}`);
      return;
    }

    const suite = PatternBenchmarkSuite.fromYamlSpecs(specsDir);
    const benchmark = suite.getBenchmark('reflection');

    if (!benchmark) {
      throw new Error('Reflection benchmark not found');
    }

    const agentFactory = (config: Record<string, unknown>) => new MockAgent(config);

    const results = await suite.runBenchmark(benchmark, agentFactory);

    expect(results.summary.total_time_ms).toBeGreaterThanOrEqual(0);
    for (const testResult of results.test_cases) {
      expect(testResult.time_ms).toBeGreaterThanOrEqual(0);
    }
  });

  it('should handle agent errors gracefully', async () => {
    // Skip if specs directory doesn't exist
    if (!fs.existsSync(specsDir)) {
      console.warn(`Skipping test: specs directory not found at ${specsDir}`);
      return;
    }

    // Create agent that always throws
    class FailingAgent implements Agent {
      get name(): string {
        return 'failing_agent';
      }

      async process(_message: Message): Promise<Message> {
        throw new Error('Intentional test error');
      }
    }

    const suite = PatternBenchmarkSuite.fromYamlSpecs(specsDir);
    const benchmark = suite.getBenchmark('reflection');

    if (!benchmark) {
      throw new Error('Reflection benchmark not found');
    }

    const agentFactory = () => new FailingAgent();

    const results = await suite.runBenchmark(benchmark, agentFactory);

    // All tests should have failed due to errors
    expect(results.summary.failed).toBe(results.summary.total);
    expect(results.summary.passed).toBe(0);

    // Check that errors were recorded
    for (const testResult of results.test_cases) {
      expect(testResult.passed).toBe(false);
      expect(testResult.error).toBeDefined();
    }
  });

  it('should convert suite to dict', () => {
    // Skip if specs directory doesn't exist
    if (!fs.existsSync(specsDir)) {
      console.warn(`Skipping test: specs directory not found at ${specsDir}`);
      return;
    }

    const suite = PatternBenchmarkSuite.fromYamlSpecs(specsDir);
    const dict = suite.toDict();

    expect(dict.total_benchmarks).toBeGreaterThan(0);
    expect(Array.isArray(dict.patterns)).toBe(true);
    expect(dict.descriptions).toBeDefined();
  });

  it('should load from standard patterns location', () => {
    const suite = PatternBenchmarkSuite.standardPatterns();
    // May be empty if specs directory doesn't exist, but should not throw
    expect(suite).toBeDefined();
    expect(suite.getAllBenchmarks()).toBeDefined();
  });
});

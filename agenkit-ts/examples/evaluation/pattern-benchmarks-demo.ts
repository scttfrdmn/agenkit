#!/usr/bin/env ts-node
/**
 * Pattern Benchmarks Demo
 *
 * Demonstrates how to use the pattern benchmark suite to evaluate agent patterns
 * using standardized test scenarios loaded from YAML specifications.
 *
 * This example shows:
 * 1. Loading pattern benchmarks from YAML specs
 * 2. Creating an agent factory for testing
 * 3. Running individual pattern benchmarks
 * 4. Running the full benchmark suite
 * 5. Analyzing results
 *
 * Usage:
 *     ts-node examples/evaluation/pattern-benchmarks-demo.ts
 *     # or with npm:
 *     npm run build && node dist/examples/evaluation/pattern-benchmarks-demo.js
 */

import * as path from 'path';
import {
  PatternBenchmarkSuite,
  YAMLBenchmarkLoader,
  BenchmarkResult,
} from '../../src/evaluation/pattern-benchmarks';
import { Agent, Message } from '../../src/interfaces';

/**
 * Mock reflection agent for demonstration purposes.
 */
class MockReflectionAgent implements Agent {
  private maxIterations: number;
  private iterationCount: number = 0;

  constructor(config: { max_reflections?: number }) {
    this.maxIterations = config.max_reflections || 3;
  }

  get name(): string {
    return 'mock_reflection';
  }

  async process(message: Message): Promise<Message> {
    this.iterationCount += 1;

    // Simulate reflection by improving response
    const improvedContent = `Improved response (iteration ${this.iterationCount}): ${message.content}`;

    return {
      role: 'assistant',
      content: improvedContent,
      metadata: {
        iterations: this.iterationCount,
        improved: true,
        pattern: 'reflection',
      },
    };
  }
}

/**
 * Demonstrate loading pattern benchmarks from YAML specs.
 */
async function demoLoadingBenchmarks(): Promise<YAMLBenchmarkLoader> {
  console.log('='.repeat(70));
  console.log('Pattern Benchmark Loading Demo');
  console.log('='.repeat(70));

  // Get specs directory
  const specsDir = path.resolve(__dirname, '../../../tests/cross_language/specs');
  console.log(`\n✓ Loading benchmarks from: ${specsDir}`);

  // Create loader
  const loader = new YAMLBenchmarkLoader(specsDir);
  console.log('✓ YAMLBenchmarkLoader created');

  // Load single pattern benchmark
  const reflectionBenchmark = loader.loadPatternBenchmark('reflection');
  console.log(`\n✓ Loaded benchmark: ${reflectionBenchmark.name}`);
  console.log(`  Description: ${reflectionBenchmark.description}`);

  // Generate test cases
  const testCases = await reflectionBenchmark.generateTestCases();
  console.log(`  Test cases: ${testCases.length}`);

  for (let i = 0; i < testCases.length; i++) {
    const testCase = testCases[i];
    console.log(`\n  Test Case ${i + 1}:`);
    console.log(`    Input: ${testCase.input.substring(0, 50)}...`);
    console.log(`    Tags: ${testCase.tags?.join(', ')}`);
    console.log(`    Pattern: ${testCase.metadata?.pattern}`);
  }

  // Load all pattern benchmarks
  const allBenchmarks = loader.loadAllPatternBenchmarks();
  console.log(`\n✓ Loaded ${allBenchmarks.length} total pattern benchmarks`);

  const patternNames = allBenchmarks.map((b) => b.patternName);
  console.log(`\nAvailable patterns: ${patternNames.sort().slice(0, 10).join(', ')}...`);

  return loader;
}

/**
 * Demonstrate running a single pattern benchmark.
 */
async function demoRunningSingleBenchmark(): Promise<BenchmarkResult> {
  console.log('\n' + '='.repeat(70));
  console.log('Single Pattern Benchmark Demo');
  console.log('='.repeat(70));

  // Create suite and get reflection benchmark
  const specsDir = path.resolve(__dirname, '../../../tests/cross_language/specs');
  const suite = PatternBenchmarkSuite.fromYamlSpecs(specsDir);
  const benchmark = suite.getBenchmark('reflection');

  if (!benchmark) {
    throw new Error('Reflection benchmark not found');
  }

  console.log(`\n✓ Running benchmark: ${benchmark.name}`);

  // Create agent factory
  const agentFactory = (config: Record<string, unknown>): Agent => {
    return new MockReflectionAgent(config as { max_reflections?: number });
  };

  // Run benchmark using suite
  const results = await suite.runBenchmark(benchmark, agentFactory);

  // Display results
  console.log(`\n✓ Benchmark Results for '${results.pattern}':`);
  console.log(`  Total test cases: ${results.summary.total}`);
  console.log(`  Passed: ${results.summary.passed}`);
  console.log(`  Failed: ${results.summary.failed}`);
  console.log(`  Total time: ${results.summary.total_time_ms.toFixed(2)}ms`);

  if (results.summary.total > 0) {
    const passRate = (results.summary.passed / results.summary.total) * 100;
    const avgTime = results.summary.total_time_ms / results.summary.total;
    console.log(`  Pass rate: ${passRate.toFixed(1)}%`);
    console.log(`  Avg time per test: ${avgTime.toFixed(2)}ms`);
  }

  // Show individual test case results
  console.log('\n  Test Case Details:');
  for (let i = 0; i < Math.min(3, results.test_cases.length); i++) {
    const testResult = results.test_cases[i];
    const status = testResult.passed ? '✓ PASS' : '✗ FAIL';
    console.log(
      `    ${i + 1}. ${testResult.scenario_id}: ${status} (${testResult.time_ms.toFixed(2)}ms)`
    );
  }

  if (results.test_cases.length > 3) {
    console.log(`    ... and ${results.test_cases.length - 3} more test cases`);
  }

  return results;
}

/**
 * Demonstrate using the pattern benchmark suite.
 */
async function demoBenchmarkSuite(): Promise<PatternBenchmarkSuite> {
  console.log('\n' + '='.repeat(70));
  console.log('Pattern Benchmark Suite Demo');
  console.log('='.repeat(70));

  // Create suite from YAML specs
  const specsDir = path.resolve(__dirname, '../../../tests/cross_language/specs');
  const suite = PatternBenchmarkSuite.fromYamlSpecs(specsDir);

  console.log(`\n✓ Created benchmark suite with ${suite.getAllBenchmarks().length} patterns`);

  // Get specific benchmark
  const reflection = suite.getBenchmark('reflection');
  if (reflection) {
    console.log(`✓ Found reflection benchmark: ${reflection.name}`);
  }

  // Filter benchmarks by tag
  const yamlBenchmarks = suite.getBenchmarksByTag('yaml_generated');
  console.log(`✓ Found ${yamlBenchmarks.length} benchmarks with 'yaml_generated' tag`);

  // Show suite summary
  const suiteDict = suite.toDict();
  console.log('\n✓ Suite Summary:');
  console.log(`  Total patterns: ${suiteDict.total_benchmarks}`);
  console.log(
    `  Patterns: ${(suiteDict.patterns as string[]).sort().slice(0, 8).join(', ')}...`
  );

  return suite;
}

/**
 * Demonstrate comparing different pattern implementations.
 */
async function demoComparingPatterns(): Promise<void> {
  console.log('\n' + '='.repeat(70));
  console.log('Pattern Comparison Demo');
  console.log('='.repeat(70));

  const specsDir = path.resolve(__dirname, '../../../tests/cross_language/specs');
  const loader = new YAMLBenchmarkLoader(specsDir);

  // Load multiple pattern benchmarks
  const patternsToTest = ['reflection', 'sequential', 'parallel'];
  const resultsComparison: Array<{
    pattern: string;
    test_cases: number;
    description: string;
  }> = [];

  console.log('\n✓ Comparing patterns:\n');

  for (const patternName of patternsToTest) {
    try {
      const benchmark = loader.loadPatternBenchmark(patternName);
      const testCases = await benchmark.generateTestCases();

      resultsComparison.push({
        pattern: patternName,
        test_cases: testCases.length,
        description: benchmark.description.substring(0, 60) + '...',
      });

      console.log(`  ${patternName}:`);
      console.log(`    Test cases: ${testCases.length}`);
      console.log(`    Description: ${benchmark.description.substring(0, 50)}...`);
    } catch (error) {
      console.log(`  ${patternName}: Failed to load (${error})`);
    }
  }

  // Summary table
  console.log('\n✓ Pattern Comparison Summary:');
  console.log(`  ${'Pattern'.padEnd(15)} | ${'Test Cases'.padEnd(12)} | Description`);
  console.log('  ' + '-'.repeat(70));

  for (const result of resultsComparison) {
    console.log(
      `  ${result.pattern.padEnd(15)} | ${String(result.test_cases).padEnd(12)} | ${result.description}`
    );
  }
}

/**
 * Demonstrate comprehensive benchmark suite execution.
 */
async function demoComprehensiveBenchmarking(): Promise<void> {
  console.log('\n' + '='.repeat(70));
  console.log('Comprehensive Benchmarking Demo');
  console.log('='.repeat(70));

  const specsDir = path.resolve(__dirname, '../../../tests/cross_language/specs');
  const suite = PatternBenchmarkSuite.fromYamlSpecs(specsDir);

  console.log('\n✓ Running comprehensive benchmark suite...');
  console.log('  Note: This would test all patterns with real agents\n');

  // Show what would be tested
  const allBenchmarks = suite.getAllBenchmarks();
  console.log(`  Patterns to test: ${allBenchmarks.length}`);

  let totalTestCases = 0;
  for (const benchmark of allBenchmarks) {
    const testCases = await benchmark.generateTestCases();
    totalTestCases += testCases.length;
  }

  console.log(`  Total test cases: ${totalTestCases}`);
  console.log(`  Estimated time: ~${(totalTestCases * 0.1).toFixed(1)}s (with mock agents)`);

  console.log('\n  To run the full suite, implement agent factories for all patterns:');
  console.log('  ```typescript');
  console.log('  const results = await suite.runAllBenchmarks((patternName, config) => {');
  console.log('    return createAgentForPattern(patternName, config);');
  console.log('  });');
  console.log('  ```');
}

/**
 * Main demo runner.
 */
async function main(): Promise<void> {
  console.log('\n╔' + '═'.repeat(68) + '╗');
  console.log('║' + ' Pattern Benchmarks Demo - TypeScript '.padStart(48).padEnd(68) + '║');
  console.log('╚' + '═'.repeat(68) + '╝\n');

  try {
    // Run all demo functions
    await demoLoadingBenchmarks();
    await demoRunningSingleBenchmark();
    await demoBenchmarkSuite();
    await demoComparingPatterns();
    await demoComprehensiveBenchmarking();

    console.log('\n' + '='.repeat(70));
    console.log('All Demos Complete!');
    console.log('='.repeat(70));
    console.log('\n✓ Pattern benchmarking framework is ready to use');
    console.log('✓ Load benchmarks from YAML specs');
    console.log('✓ Run individual or suite-wide benchmarks');
    console.log('✓ Compare pattern implementations');
    console.log('✓ Track performance metrics\n');
  } catch (error) {
    console.error('\n✗ Demo failed:', error);
    process.exit(1);
  }
}

// Run if executed directly
if (require.main === module) {
  main().catch((error) => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

export { main };

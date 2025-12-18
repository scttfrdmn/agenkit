#!/usr/bin/env ts-node
/**
 * TypeScript Pattern Performance Benchmarks
 *
 * Measures framework overhead for all 18 agent patterns using mock agents.
 * This matches the C++, Go, and Python benchmark methodology - measuring pattern overhead,
 * not LLM performance.
 */

import * as path from 'path';
import {
  PatternBenchmarkSuite,
  type PatternTestCase,
} from '../src/evaluation/pattern-benchmarks';
import type { Agent, Message } from '../src/index';

/**
 * Minimal mock agent for performance testing.
 */
class MockAgent implements Agent {
  private config: Record<string, unknown>;
  private _name: string;

  constructor(config: Record<string, unknown> = {}) {
    this.config = config;
    this._name = (config.name as string) || 'mock_agent';
  }

  get name(): string {
    return this._name;
  }

  async process(message: Message): Promise<Message> {
    return {
      role: 'assistant',
      content: `Response to: ${message.content}`,
      metadata: {
        processed: true,
      },
    };
  }
}

interface BenchmarkResult {
  pattern: string;
  iterations: number;
  totalTimeMs: number;
  avgTimeUs: number;
  opsPerSec: number;
}

/**
 * Benchmark a single pattern.
 */
async function benchmarkPattern(
  patternName: string,
  suite: PatternBenchmarkSuite,
  iterations: number = 1000
): Promise<BenchmarkResult | { pattern: string; error: string }> {
  const benchmark = suite.getBenchmark(patternName);
  if (!benchmark) {
    return { pattern: patternName, error: 'Benchmark not found' };
  }

  const testCases = await benchmark.generateTestCases();
  if (testCases.length === 0) {
    return { pattern: patternName, error: 'No test cases' };
  }

  // Use first test case for benchmarking
  const testCase = testCases[0];
  const config = (testCase.metadata?.config as Record<string, unknown>) || {};

  // Create agent
  const agent = new MockAgent(config);

  // Warmup
  for (let i = 0; i < 10; i++) {
    await agent.process({
      role: 'user',
      content: testCase.input,
      metadata: {},
    });
  }

  // Benchmark
  const startTime = performance.now();
  for (let i = 0; i < iterations; i++) {
    await agent.process({
      role: 'user',
      content: testCase.input,
      metadata: {},
    });
  }
  const elapsedMs = performance.now() - startTime;

  // Calculate metrics
  const avgTimeUs = (elapsedMs / iterations) * 1000;
  const opsPerSec = iterations / (elapsedMs / 1000);

  return {
    pattern: patternName,
    iterations,
    totalTimeMs: elapsedMs,
    avgTimeUs,
    opsPerSec,
  };
}

/**
 * Run all pattern benchmarks.
 */
async function main(): Promise<void> {
  console.log('='.repeat(80));
  console.log('TypeScript Pattern Performance Benchmarks');
  console.log('='.repeat(80));
  console.log();

  // Load benchmarks
  const specsDir = path.resolve(__dirname, '../../tests/cross_language/specs');
  console.log(`Loading benchmarks from: ${specsDir}`);

  const suite = PatternBenchmarkSuite.fromYamlSpecs(specsDir);
  const benchmarks = suite.getAllBenchmarks();

  console.log(`Found ${benchmarks.length} pattern benchmarks`);
  console.log();

  // Pattern order (matching C++/Go/Python benchmarks)
  const patternOrder = [
    'reflection',
    'react',
    'agents_as_tools',
    'reasoning_with_tools',
    'conversational',
    'task',
    'multiagent',
    'planning',
    'autonomous',
    'sequential',
    'parallel',
    'router',
    'fallback',
    'collaborative',
    'human_in_loop',
    'supervisor',
    'orchestration',
  ];

  const results: BenchmarkResult[] = [];

  console.log('Running benchmarks...');
  console.log(
    `${'Pattern'.padEnd(25)} ${'Avg Time (μs)'.padEnd(15)} ${'Ops/sec'.padEnd(15)}`
  );
  console.log('-'.repeat(80));

  for (const patternName of patternOrder) {
    // Find benchmark (handle naming variations)
    let benchmark = suite.getBenchmark(patternName);
    if (!benchmark) {
      // Try with underscores replaced with dashes
      benchmark = suite.getBenchmark(patternName.replace(/_/g, '-'));
    }

    if (benchmark) {
      const result = await benchmarkPattern(benchmark.patternName, suite, 1000);
      if ('error' in result) {
        console.log(`${patternName.padEnd(25)} SKIP (${result.error})`);
      } else {
        results.push(result);
        console.log(
          `${result.pattern.padEnd(25)} ${result.avgTimeUs.toFixed(2).padEnd(15)} ${Math.round(result.opsPerSec).toString().padEnd(15)}`
        );
      }
    } else {
      console.log(`${patternName.padEnd(25)} SKIP (not found)`);
    }
  }

  console.log();
  console.log('='.repeat(80));
  console.log('Summary');
  console.log('='.repeat(80));
  console.log(`Benchmarks run: ${results.length}`);

  if (results.length > 0) {
    const avgTime =
      results.reduce((sum, r) => sum + r.avgTimeUs, 0) / results.length;
    const fastest = results.reduce((min, r) =>
      r.avgTimeUs < min.avgTimeUs ? r : min
    );
    const slowest = results.reduce((max, r) =>
      r.avgTimeUs > max.avgTimeUs ? r : max
    );

    console.log(`Average time: ${avgTime.toFixed(2)} μs`);
    console.log(`Fastest: ${fastest.pattern} (${fastest.avgTimeUs.toFixed(2)} μs)`);
    console.log(`Slowest: ${slowest.pattern} (${slowest.avgTimeUs.toFixed(2)} μs)`);
  }

  console.log();
  console.log('Results by pattern:');
  const sortedResults = [...results].sort((a, b) => a.avgTimeUs - b.avgTimeUs);
  for (const result of sortedResults) {
    console.log(`  ${result.pattern.padEnd(25)} ${result.avgTimeUs.toFixed(2).padStart(10)} μs`);
  }
}

// Run if executed directly
if (require.main === module) {
  main().catch((error) => {
    console.error('Error running benchmarks:', error);
    process.exit(1);
  });
}

export { main, benchmarkPattern, MockAgent };

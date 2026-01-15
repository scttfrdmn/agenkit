#!/usr/bin/env ts-node
/**
 * Pattern Benchmarks Runner - Simple performance measurement
 *
 * Measures the overhead of pattern implementations using mock agents.
 * Similar to Python, Go, Rust, C++, and Zig benchmark suites.
 */

import {
  ReflectionAgent,
  SequentialPattern,
  ParallelPattern,
  RouterPattern,
  Agent,
  Message,
} from '../src/index';

class MockAgent implements Agent {
  constructor(public agentName: string = 'mock') {}

  get name(): string {
    return this.agentName;
  }

  async process(message: Message): Promise<Message> {
    return {
      role: 'assistant',
      content: `Mock response`,
      metadata: {},
    };
  }
}

interface BenchmarkResult {
  pattern: string;
  iterations: number;
  avgTimeUs: number;
  opsPerSec: number;
}

async function benchmarkPattern(
  name: string,
  fn: () => Promise<void>,
  iterations: number = 1000
): Promise<BenchmarkResult> {
  // Warmup
  for (let i = 0; i < 10; i++) {
    await fn();
  }

  // Measure
  const start = performance.now();
  for (let i = 0; i < iterations; i++) {
    await fn();
  }
  const end = performance.now();

  const totalTimeMs = end - start;
  const avgTimeUs = (totalTimeMs * 1000) / iterations;
  const opsPerSec = Math.floor((iterations / totalTimeMs) * 1000);

  return {
    pattern: name,
    iterations,
    avgTimeUs,
    opsPerSec,
  };
}

async function main() {
  console.log('=== Agenkit Pattern Benchmarks (TypeScript) ===\n');
  console.log('Pattern                              Time        Throughput');
  console.log('------------------------------------------------------------');

  const results: BenchmarkResult[] = [];

  // Reflection
  const reflection = new ReflectionAgent({
    generator: new MockAgent('generator'),
    critic: new MockAgent('critic'),
    maxIterations: 2,
  });
  results.push(
    await benchmarkPattern('Reflection', async () => {
      await reflection.process({ role: 'user', content: 'test' });
    })
  );

  // Sequential
  const sequential = new SequentialPattern([
    new MockAgent('agent1'),
    new MockAgent('agent2'),
    new MockAgent('agent3'),
  ]);
  results.push(
    await benchmarkPattern('Sequential', async () => {
      await sequential.process({ role: 'user', content: 'test' });
    })
  );

  // Parallel
  const parallel = new ParallelPattern([
    new MockAgent('agent1'),
    new MockAgent('agent2'),
    new MockAgent('agent3'),
  ]);
  results.push(
    await benchmarkPattern('Parallel', async () => {
      await parallel.process({ role: 'user', content: 'test' });
    })
  );

  // Router
  const routes = {
    route1: new MockAgent('route1'),
    route2: new MockAgent('route2'),
  };
  const routerFn: any = (msg: Message) => 'route1';  // Simple router function
  const router = new RouterPattern(routerFn, routes);
  results.push(
    await benchmarkPattern('Router', async () => {
      await router.process({ role: 'user', content: 'test' });
    })
  );

  // Display results
  for (const result of results) {
    const timeStr =
      result.avgTimeUs < 1
        ? `${(result.avgTimeUs * 1000).toFixed(0)} ns/op`
        : result.avgTimeUs < 1000
        ? `${result.avgTimeUs.toFixed(0)} μs/op`
        : `${(result.avgTimeUs / 1000).toFixed(0)} ms/op`;

    console.log(
      `${result.pattern.padEnd(36)} ${timeStr.padStart(11)} ${result.opsPerSec.toString().padStart(10)} ops/s`
    );
  }

  console.log('\n=== Benchmark Complete ===');
}

// Run if executed directly
if (require.main === module) {
  main().catch((error) => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}


#!/usr/bin/env ts-node
/**
 * TypeScript Pattern Performance Benchmarks
 *
 * Measures ACTUAL pattern overhead using mock agents for all patterns.
 * This matches the Go, C++, and Python benchmark methodology - measuring pattern logic,
 * not LLM performance.
 *
 * IMPORTANT: This tests the actual pattern implementations (ReflectionAgent,
 * ReActAgent, etc.), not just simple mock agent echo. The previous version
 * incorrectly measured only mock echo latency, not pattern overhead.
 */

import type { Agent, Message, Tool } from '../src/index';
import {
  ReflectionAgent,
  ReActAgent,
  AgentTool,
  ReasoningWithToolsAgent,
  ConversationalAgent,
  SequentialAgent,
  ParallelAgent,
  RouterAgent,
  FallbackAgent,
  SupervisorAgent,
} from '../src/patterns';

/**
 * Minimal mock agent for performance testing.
 */
class MockAgent implements Agent {
  private _name: string;

  constructor(name: string = 'mock') {
    this._name = name;
  }

  get name(): string {
    return this._name;
  }

  get capabilities(): string[] {
    return ['mock'];
  }

  async process(message: Message): Promise<Message> {
    return {
      role: 'assistant',
      content: `Processed: ${message.content.toString().substring(0, 20)}...`,
      metadata: { mock: true },
    };
  }
}

/**
 * Mock tool for ReAct/Reasoning benchmarks.
 */
class MockTool implements Tool {
  name: string;
  description: string;

  constructor(name: string = 'test_tool') {
    this.name = name;
    this.description = 'A test tool';
  }

  async execute(..._args: unknown[]): Promise<Record<string, unknown>> {
    return { result: 'tool executed' };
  }
}

/**
 * Mock LLM client for Conversational pattern.
 */
class MockLLMClient {
  async chat(_messages: Message[]): Promise<Message> {
    return { role: 'assistant', content: 'LLM response', metadata: {} };
  }
}

/**
 * Mock classifier for Router pattern.
 */
class MockClassifier {
  async classify(_message: Message): Promise<string> {
    return 'agent1';
  }
}

/**
 * Mock planner for Supervisor pattern.
 */
class MockPlanner {
  async plan(_message: Message): Promise<Array<{ agent: string; task: string }>> {
    return [
      { agent: 'agent1', task: 'subtask1' },
      { agent: 'agent2', task: 'subtask2' },
    ];
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
 * Benchmark Reflection pattern (2 iterations).
 */
async function benchmarkReflection(iterations: number = 1000): Promise<BenchmarkResult> {
  const generator = new MockAgent('generator');
  const critic = new MockAgent('critic');

  const agent = new ReflectionAgent({
    generator,
    critic,
    maxIterations: 2,
  });

  const msg: Message = { role: 'user', content: 'test input', metadata: {} };

  // Warmup
  for (let i = 0; i < 10; i++) {
    await agent.process(msg);
  }

  // Benchmark
  const startTime = performance.now();
  for (let i = 0; i < iterations; i++) {
    await agent.process(msg);
  }
  const elapsedMs = performance.now() - startTime;

  return {
    pattern: 'reflection',
    iterations,
    totalTimeMs: elapsedMs,
    avgTimeUs: (elapsedMs / iterations) * 1000,
    opsPerSec: iterations / (elapsedMs / 1000),
  };
}

/**
 * Benchmark ReAct pattern (3 steps).
 */
async function benchmarkReAct(iterations: number = 1000): Promise<BenchmarkResult> {
  const agent = new MockAgent();
  const tool = new MockTool();

  const reactAgent = new ReActAgent({
    agent,
    tools: [tool],
    maxSteps: 3,
  });

  const msg: Message = { role: 'user', content: 'test input', metadata: {} };

  // Warmup
  for (let i = 0; i < 10; i++) {
    await reactAgent.process(msg);
  }

  // Benchmark
  const startTime = performance.now();
  for (let i = 0; i < iterations; i++) {
    await reactAgent.process(msg);
  }
  const elapsedMs = performance.now() - startTime;

  return {
    pattern: 'react',
    iterations,
    totalTimeMs: elapsedMs,
    avgTimeUs: (elapsedMs / iterations) * 1000,
    opsPerSec: iterations / (elapsedMs / 1000),
  };
}

/**
 * Benchmark Agents-as-Tools pattern.
 */
async function benchmarkAgentsAsTools(iterations: number = 1000): Promise<BenchmarkResult> {
  const agent = new MockAgent();

  const tool = new AgentTool({
    agent,
    name: 'test_tool',
    description: 'Test tool',
  });

  // Warmup
  for (let i = 0; i < 10; i++) {
    await tool.execute({ input: 'test' });
  }

  // Benchmark
  const startTime = performance.now();
  for (let i = 0; i < iterations; i++) {
    await tool.execute({ input: 'test' });
  }
  const elapsedMs = performance.now() - startTime;

  return {
    pattern: 'agents_as_tools',
    iterations,
    totalTimeMs: elapsedMs,
    avgTimeUs: (elapsedMs / iterations) * 1000,
    opsPerSec: iterations / (elapsedMs / 1000),
  };
}

/**
 * Benchmark Reasoning with Tools pattern (5 steps).
 */
async function benchmarkReasoningWithTools(
  iterations: number = 1000
): Promise<BenchmarkResult> {
  const agent = new MockAgent();
  const tool = new MockTool();

  const reasoningAgent = new ReasoningWithToolsAgent({
    agent,
    tools: [tool],
    maxReasoningSteps: 5,
  });

  const msg: Message = { role: 'user', content: 'test input', metadata: {} };

  // Warmup
  for (let i = 0; i < 10; i++) {
    await reasoningAgent.process(msg);
  }

  // Benchmark
  const startTime = performance.now();
  for (let i = 0; i < iterations; i++) {
    await reasoningAgent.process(msg);
  }
  const elapsedMs = performance.now() - startTime;

  return {
    pattern: 'reasoning_with_tools',
    iterations,
    totalTimeMs: elapsedMs,
    avgTimeUs: (elapsedMs / iterations) * 1000,
    opsPerSec: iterations / (elapsedMs / 1000),
  };
}

/**
 * Benchmark Conversational pattern (10 history limit).
 */
async function benchmarkConversational(iterations: number = 1000): Promise<BenchmarkResult> {
  const llmClient = new MockLLMClient();

  const agent = new ConversationalAgent({
    llmClient: llmClient as any,
    maxHistory: 10,
  });

  const msg: Message = { role: 'user', content: 'test input', metadata: {} };

  // Warmup
  for (let i = 0; i < 10; i++) {
    await agent.process(msg);
  }

  // Benchmark
  const startTime = performance.now();
  for (let i = 0; i < iterations; i++) {
    await agent.process(msg);
  }
  const elapsedMs = performance.now() - startTime;

  return {
    pattern: 'conversational',
    iterations,
    totalTimeMs: elapsedMs,
    avgTimeUs: (elapsedMs / iterations) * 1000,
    opsPerSec: iterations / (elapsedMs / 1000),
  };
}

/**
 * Benchmark Sequential pattern (3 agents).
 */
async function benchmarkSequential(iterations: number = 1000): Promise<BenchmarkResult> {
  const agents = [new MockAgent('agent0'), new MockAgent('agent1'), new MockAgent('agent2')];

  const seqAgent = new SequentialAgent({ agents });

  const msg: Message = { role: 'user', content: 'test input', metadata: {} };

  // Warmup
  for (let i = 0; i < 10; i++) {
    await seqAgent.process(msg);
  }

  // Benchmark
  const startTime = performance.now();
  for (let i = 0; i < iterations; i++) {
    await seqAgent.process(msg);
  }
  const elapsedMs = performance.now() - startTime;

  return {
    pattern: 'sequential',
    iterations,
    totalTimeMs: elapsedMs,
    avgTimeUs: (elapsedMs / iterations) * 1000,
    opsPerSec: iterations / (elapsedMs / 1000),
  };
}

/**
 * Benchmark Parallel pattern (3 agents).
 */
async function benchmarkParallel(iterations: number = 1000): Promise<BenchmarkResult> {
  const agents = [new MockAgent('agent0'), new MockAgent('agent1'), new MockAgent('agent2')];

  const parAgent = new ParallelAgent({ agents });

  const msg: Message = { role: 'user', content: 'test input', metadata: {} };

  // Warmup
  for (let i = 0; i < 10; i++) {
    await parAgent.process(msg);
  }

  // Benchmark
  const startTime = performance.now();
  for (let i = 0; i < iterations; i++) {
    await parAgent.process(msg);
  }
  const elapsedMs = performance.now() - startTime;

  return {
    pattern: 'parallel',
    iterations,
    totalTimeMs: elapsedMs,
    avgTimeUs: (elapsedMs / iterations) * 1000,
    opsPerSec: iterations / (elapsedMs / 1000),
  };
}

/**
 * Benchmark Router pattern (2 agents).
 */
async function benchmarkRouter(iterations: number = 1000): Promise<BenchmarkResult> {
  const agents = { agent1: new MockAgent('agent1'), agent2: new MockAgent('agent2') };
  const classifier = new MockClassifier();

  const routerAgent = new RouterAgent({ agents, classifier: classifier as any });

  const msg: Message = { role: 'user', content: 'test input', metadata: {} };

  // Warmup
  for (let i = 0; i < 10; i++) {
    await routerAgent.process(msg);
  }

  // Benchmark
  const startTime = performance.now();
  for (let i = 0; i < iterations; i++) {
    await routerAgent.process(msg);
  }
  const elapsedMs = performance.now() - startTime;

  return {
    pattern: 'router',
    iterations,
    totalTimeMs: elapsedMs,
    avgTimeUs: (elapsedMs / iterations) * 1000,
    opsPerSec: iterations / (elapsedMs / 1000),
  };
}

/**
 * Benchmark Fallback pattern (3 agents).
 */
async function benchmarkFallback(iterations: number = 1000): Promise<BenchmarkResult> {
  const agents = [new MockAgent('agent0'), new MockAgent('agent1'), new MockAgent('agent2')];

  const fallbackAgent = new FallbackAgent({ agents });

  const msg: Message = { role: 'user', content: 'test input', metadata: {} };

  // Warmup
  for (let i = 0; i < 10; i++) {
    await fallbackAgent.process(msg);
  }

  // Benchmark
  const startTime = performance.now();
  for (let i = 0; i < iterations; i++) {
    await fallbackAgent.process(msg);
  }
  const elapsedMs = performance.now() - startTime;

  return {
    pattern: 'fallback',
    iterations,
    totalTimeMs: elapsedMs,
    avgTimeUs: (elapsedMs / iterations) * 1000,
    opsPerSec: iterations / (elapsedMs / 1000),
  };
}

/**
 * Benchmark Supervisor pattern (2 agents).
 */
async function benchmarkSupervisor(iterations: number = 1000): Promise<BenchmarkResult> {
  const agents = { agent1: new MockAgent('agent1'), agent2: new MockAgent('agent2') };
  const planner = new MockPlanner();

  const supervisorAgent = new SupervisorAgent({ agents, planner: planner as any });

  const msg: Message = { role: 'user', content: 'test input', metadata: {} };

  // Warmup
  for (let i = 0; i < 10; i++) {
    await supervisorAgent.process(msg);
  }

  // Benchmark
  const startTime = performance.now();
  for (let i = 0; i < iterations; i++) {
    await supervisorAgent.process(msg);
  }
  const elapsedMs = performance.now() - startTime;

  return {
    pattern: 'supervisor',
    iterations,
    totalTimeMs: elapsedMs,
    avgTimeUs: (elapsedMs / iterations) * 1000,
    opsPerSec: iterations / (elapsedMs / 1000),
  };
}

/**
 * Run all pattern benchmarks.
 */
async function main(): Promise<void> {
  console.log('='.repeat(80));
  console.log('TypeScript Pattern Performance Benchmarks - CORRECTED');
  console.log('Testing ACTUAL patterns (not just mock echo)');
  console.log('='.repeat(80));
  console.log();

  // Pattern benchmarks in order
  const benchmarks: [string, () => Promise<BenchmarkResult>][] = [
    ['reflection', benchmarkReflection],
    ['react', benchmarkReAct],
    ['agents_as_tools', benchmarkAgentsAsTools],
    ['reasoning_with_tools', benchmarkReasoningWithTools],
    ['conversational', benchmarkConversational],
    ['sequential', benchmarkSequential],
    ['parallel', benchmarkParallel],
    ['router', benchmarkRouter],
    ['fallback', benchmarkFallback],
    ['supervisor', benchmarkSupervisor],
  ];

  const results: BenchmarkResult[] = [];

  console.log('Running benchmarks...');
  console.log(
    `${'Pattern'.padEnd(25)} ${'Avg Time (μs)'.padEnd(15)} ${'Ops/sec'.padEnd(15)}`
  );
  console.log('-'.repeat(80));

  for (const [patternName, benchmarkFunc] of benchmarks) {
    try {
      const result = await benchmarkFunc(1000);
      results.push(result);
      console.log(
        `${result.pattern.padEnd(25)} ${result.avgTimeUs.toFixed(2).padEnd(15)} ${Math.round(result.opsPerSec).toString().padEnd(15)}`
      );
    } catch (error) {
      console.log(`${patternName.padEnd(25)} ERROR: ${error}`);
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
  console.log('Results by pattern (sorted):');
  const sortedResults = [...results].sort((a, b) => a.avgTimeUs - b.avgTimeUs);
  for (const result of sortedResults) {
    console.log(`  ${result.pattern.padEnd(25)} ${result.avgTimeUs.toFixed(2).padStart(10)} μs`);
  }

  console.log();
  console.log('Note: These results measure ACTUAL pattern overhead, not mock echo.');
  console.log('Previous results only measured MockAgent.process() latency.');
}

// Run if executed directly
if (require.main === module) {
  main().catch((error) => {
    console.error('Error running benchmarks:', error);
    process.exit(1);
  });
}

export { main, MockAgent };

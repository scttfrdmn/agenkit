/**
 * Chaos Agent Infrastructure
 *
 * Provides base classes and utilities for injecting chaos into agent behavior.
 * These agents wrap normal agents and inject various failure modes for testing.
 */

import type { Agent, Message } from '../../core/interfaces';

export enum ChaosMode {
  NONE = 'none',
  TIMEOUT = 'timeout',
  CONNECTION_REFUSED = 'connection_refused',
  CONNECTION_DROP = 'connection_drop',
  SLOW_RESPONSE = 'slow_response',
  INTERMITTENT = 'intermittent',
  RANDOM_ERROR = 'random_error',
  MEMORY_PRESSURE = 'memory_pressure',
  CRASH = 'crash',
}

export interface ChaosStats {
  requestCount: number;
  failureCount: number;
  failureRate: number;
}

/**
 * Agent that injects chaos for testing resilience.
 *
 * Supports various failure modes:
 * - Timeouts: Delays exceeding configured timeout
 * - Connection failures: Simulates network issues
 * - Random errors: Probabilistic failures
 * - Slow responses: Gradual performance degradation
 */
export class ChaosAgent implements Agent {
  private requestCount = 0;
  private failureCount = 0;
  private crashAfter: number | null = null;

  constructor(
    private readonly agent: Agent,
    private readonly failureRate: number = 0.0,
    private readonly delayMs: number = 0.0,
    private readonly chaosMode: ChaosMode = ChaosMode.NONE,
    private readonly agentName?: string
  ) {}

  get name(): string {
    return this.agentName || `chaos-${this.agent.name}`;
  }

  get capabilities(): string[] {
    return this.agent.capabilities ?? [];
  }

  setCrashAfter(count: number): void {
    this.crashAfter = count;
  }

  getStats(): ChaosStats {
    return {
      requestCount: this.requestCount,
      failureCount: this.failureCount,
      failureRate: this.failureCount / Math.max(1, this.requestCount),
    };
  }

  async process(message: Message): Promise<Message> {
    this.requestCount++;

    // Check for crash condition
    if (this.crashAfter !== null && this.requestCount > this.crashAfter) {
      throw new Error('Agent crashed (simulated)');
    }

    // Inject chaos based on mode
    switch (this.chaosMode) {
      case ChaosMode.TIMEOUT:
        // Simulate timeout by waiting forever
        await new Promise(() => {}); // Never resolves
        break;

      case ChaosMode.CONNECTION_REFUSED:
        this.failureCount++;
        throw new Error('ECONNREFUSED: Connection refused (simulated)');

      case ChaosMode.CONNECTION_DROP:
        this.failureCount++;
        throw new Error('ECONNRESET: Connection dropped (simulated)');

      case ChaosMode.RANDOM_ERROR:
        if (Math.random() < this.failureRate) {
          this.failureCount++;
          throw new Error(`Random failure (rate=${this.failureRate})`);
        }
        break;

      case ChaosMode.SLOW_RESPONSE:
        // Inject delay
        await new Promise((resolve) => setTimeout(resolve, this.delayMs));
        break;

      case ChaosMode.INTERMITTENT:
        // Randomly fail or succeed
        if (Math.random() < this.failureRate) {
          this.failureCount++;
          throw new Error('ECONNRESET: Intermittent failure (simulated)');
        }
        break;

      case ChaosMode.MEMORY_PRESSURE:
        // Simulate memory pressure with large response
        return {
          role: 'agent',
          content: 'x'.repeat(10 * 1024 * 1024), // 10MB
          metadata: { chaos: 'memory_pressure' },
        };

      case ChaosMode.CRASH:
        this.failureCount++;
        throw new Error('Agent crashed (simulated)');
    }

    // If no chaos or chaos passed, delegate to wrapped agent
    return await this.agent.process(message);
  }
}

/**
 * Agent with configurable flakiness patterns.
 *
 * Useful for testing retry and circuit breaker behavior with realistic
 * failure patterns (e.g., fail-fail-succeed, gradual degradation).
 */
export class FlakeyAgent implements Agent {
  private requestIndex = 0;

  constructor(
    private readonly agent: Agent,
    private readonly failurePattern: boolean[],
    private readonly agentName?: string
  ) {}

  get name(): string {
    return this.agentName || `flakey-${this.agent.name}`;
  }

  get capabilities(): string[] {
    return this.agent.capabilities ?? [];
  }

  reset(): void {
    this.requestIndex = 0;
  }

  async process(message: Message): Promise<Message> {
    // Get current position in pattern (cycle if exceeded)
    const shouldSucceed = this.failurePattern[this.requestIndex % this.failurePattern.length];
    this.requestIndex++;

    if (!shouldSucceed) {
      throw new Error(`Flakey failure at request ${this.requestIndex}`);
    }

    return await this.agent.process(message);
  }
}

/**
 * Agent that simulates overload conditions.
 *
 * Starts responding normally, then degrades as request count increases.
 * Useful for testing circuit breaker and rate limiter behavior.
 */
export class OverloadedAgent implements Agent {
  private requestCount = 0;
  private startTime = Date.now();

  constructor(
    private readonly agent: Agent,
    private readonly overloadThreshold: number = 10,
    private readonly overloadFailureRate: number = 0.8,
    private readonly agentName?: string
  ) {}

  get name(): string {
    return this.agentName || `overloaded-${this.agent.name}`;
  }

  get capabilities(): string[] {
    return this.agent.capabilities ?? [];
  }

  isOverloaded(): boolean {
    return this.requestCount > this.overloadThreshold;
  }

  reset(): void {
    this.requestCount = 0;
    this.startTime = Date.now();
  }

  async process(message: Message): Promise<Message> {
    this.requestCount++;

    // If overloaded, fail probabilistically
    if (this.isOverloaded() && Math.random() < this.overloadFailureRate) {
      throw new Error(
        `Service overloaded (requests=${this.requestCount}, threshold=${this.overloadThreshold})`
      );
    }

    return await this.agent.process(message);
  }
}

/**
 * Simple test agent for chaos testing.
 */
export class SimpleAgent implements Agent {
  constructor(private readonly agentName: string = 'simple-agent') {}

  get name(): string {
    return this.agentName;
  }

  get capabilities(): string[] {
    return ['test'];
  }

  async process(message: Message): Promise<Message> {
    return {
      role: 'agent',
      content: `Processed: ${message.content}`,
      metadata: { agent: this.name },
    };
  }
}

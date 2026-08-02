/**
 * Cross-language retry behavior tests for TypeScript
 *
 * Validates that Agenkit's TypeScript retry middleware behaves consistently
 * with the cross-language retry behavior specification.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';
import { RetryMiddleware, RetryConfig } from '../../src/middleware/retry.js';
import type { Agent, Message } from '../../src/core/interfaces.js';
import { atLeastMs } from '../../src/__tests__/support/timing.js';

interface RetryBehaviorFixtures {
  version: string;
  description: string;
  test_cases: RetryBehaviorTestCase[];
}

interface RetryBehaviorTestCase {
  id: string;
  name: string;
  config: {
    max_retries: number;
    initial_backoff_ms: number;
    max_backoff_ms: number;
    backoff_multiplier: number;
  };
  scenario: {
    agent_responses: Array<{
      success: boolean;
      content?: string;
      error?: string;
    }>;
  };
  expected_behavior?: {
    total_attempts: number;
    successful: boolean;
    final_response?: string;
    min_total_delay_ms?: number;
    max_total_delay_ms?: number;
    error_type?: string;
    should_not_retry?: boolean;
    delays_capped?: boolean;
    expected_delays_ms?: number[];
    total_delay_ms?: number;
  };
  expected_metrics?: {
    total_attempts: number;
    successful_first_attempt: number;
    successful_on_retry: number;
    total_failures: number;
    retry_distribution: Record<string, number>;
  };
}

/**
 * Mock agent that simulates responses from fixture scenarios
 */
class MockRetryAgent implements Agent {
  private responses: Array<{ success: boolean; content?: string; error?: string }>;
  public callCount: number = 0;

  constructor(responses: Array<{ success: boolean; content?: string; error?: string }>) {
    this.responses = responses;
  }

  get name(): string {
    return 'mock-retry-agent';
  }

  get capabilities(): string[] {
    return [];
  }

  async process(_message: Message): Promise<Message> {
    if (this.callCount >= this.responses.length) {
      throw new Error('No more responses available');
    }

    const response = this.responses[this.callCount];
    this.callCount++;

    if (response.success) {
      return {
        role: 'agent',
        content: response.content!,
        metadata: {},
        timestamp: Date.now(),
      };
    } else {
      throw new Error(response.error!);
    }
  }
}

describe('Cross-Language Retry Behavior', () => {
  let fixtures: RetryBehaviorFixtures;

  beforeAll(() => {
    // Load fixtures
    const fixturesPath = join(__dirname, '../../../tests/cross_language/fixtures/retry_behavior.json');
    fixtures = JSON.parse(readFileSync(fixturesPath, 'utf-8'));
  });

  it('success on first attempt (no retries)', async () => {
    const testCase = fixtures.test_cases.find((tc) => tc.id === 'retry_success_first_attempt')!;

    // Create mock agent
    const agent = new MockRetryAgent(testCase.scenario.agent_responses);

    // Create retry decorator
    const config: RetryConfig = {
      maxRetries: testCase.config.max_retries,
      initialDelayMs: testCase.config.initial_backoff_ms,
      maxDelayMs: testCase.config.max_backoff_ms,
      backoffMultiplier: testCase.config.backoff_multiplier,
      shouldRetry: () => true, // Always retry for tests
    };
    const retry = new RetryMiddleware(agent, config);

    // Execute
    const message: Message = { role: 'user', content: 'test', metadata: {}, timestamp: Date.now() };
    const response = await retry.process(message);

    // Verify expected behavior
    expect(agent.callCount).toBe(testCase.expected_behavior!.total_attempts);
    expect(response.content).toBe(testCase.expected_behavior!.final_response);
  });

  it('success after retry', async () => {
    const testCase = fixtures.test_cases.find((tc) => tc.id === 'retry_success_second_attempt')!;

    const agent = new MockRetryAgent(testCase.scenario.agent_responses);
    const config: RetryConfig = {
      maxRetries: testCase.config.max_retries,
      initialDelayMs: testCase.config.initial_backoff_ms,
      maxDelayMs: testCase.config.max_backoff_ms,
      backoffMultiplier: testCase.config.backoff_multiplier,
      shouldRetry: () => true, // Always retry for tests
    };
    const retry = new RetryMiddleware(agent, config);

    // Measure time
    const start = Date.now();
    const message: Message = { role: 'user', content: 'test', metadata: {}, timestamp: Date.now() };
    const response = await retry.process(message);
    const elapsed = Date.now() - start;

    // Verify expected behavior
    expect(agent.callCount).toBe(testCase.expected_behavior!.total_attempts);
    expect(response.content).toBe(testCase.expected_behavior!.final_response);

    // Verify delay within expected range. The lower bound is NOT exact: it was
    // previously asserted as such, on the reasoning that "backoff sleeps can
    // only push elapsed higher, never lower". They can push it lower — Node
    // fires a setTimeout up to ~1ms before its deadline (see atLeastMs), which
    // made this fail on `expected 99 to be >= 100` about 1 run in 10. The upper
    // bound uses a generous multiplier rather than a fixed +50ms: a
    // loaded/parallel CI runner can add hundreds of ms of scheduling latency,
    // so a tight cap was flaky. This still catches gross regressions (e.g.
    // config ignored → 10x the configured delay).
    const minDelay = testCase.expected_behavior!.min_total_delay_ms!;
    const maxDelay = testCase.expected_behavior!.max_total_delay_ms!;
    expect(elapsed).toBeGreaterThanOrEqual(atLeastMs(minDelay));
    expect(elapsed).toBeLessThanOrEqual(maxDelay * 3 + 500);
  });

  it('retries exhausted', async () => {
    const testCase = fixtures.test_cases.find((tc) => tc.id === 'retry_exhausted')!;

    const agent = new MockRetryAgent(testCase.scenario.agent_responses);
    const config: RetryConfig = {
      maxRetries: testCase.config.max_retries,
      initialDelayMs: testCase.config.initial_backoff_ms,
      maxDelayMs: testCase.config.max_backoff_ms,
      backoffMultiplier: testCase.config.backoff_multiplier,
      shouldRetry: () => true, // Always retry for tests
    };
    const retry = new RetryMiddleware(agent, config);

    // Should fail after exhausting retries
    const message: Message = { role: 'user', content: 'test', metadata: {}, timestamp: Date.now() };
    await expect(retry.process(message)).rejects.toThrow();

    // Verify expected behavior
    expect(agent.callCount).toBe(testCase.expected_behavior!.total_attempts);
    expect(testCase.expected_behavior!.successful).toBe(false);
  });

  it('exponential backoff timing', async () => {
    const testCase = fixtures.test_cases.find((tc) => tc.id === 'retry_exponential_backoff')!;

    const agent = new MockRetryAgent(testCase.scenario.agent_responses);
    const config: RetryConfig = {
      maxRetries: testCase.config.max_retries,
      initialDelayMs: testCase.config.initial_backoff_ms,
      maxDelayMs: testCase.config.max_backoff_ms,
      backoffMultiplier: testCase.config.backoff_multiplier,
      shouldRetry: () => true, // Always retry for tests
    };
    const retry = new RetryMiddleware(agent, config);

    // Measure time
    const start = Date.now();
    const message: Message = { role: 'user', content: 'test', metadata: {}, timestamp: Date.now() };
    await retry.process(message);
    const elapsed = Date.now() - start;

    // Verify expected behavior
    expect(agent.callCount).toBe(testCase.expected_behavior!.total_attempts);
    expect(testCase.expected_behavior!.successful).toBe(true);

    // Verify exponential backoff timing: 100ms + 200ms + 400ms = 700ms
    const minDelay = testCase.expected_behavior!.min_total_delay_ms!;
    const maxDelay = testCase.expected_behavior!.max_total_delay_ms!;
    expect(elapsed).toBeGreaterThanOrEqual(atLeastMs(minDelay));
    expect(elapsed).toBeLessThanOrEqual(maxDelay * 3 + 500); // generous: CI scheduling latency
  });

  it('max backoff cap', async () => {
    const testCase = fixtures.test_cases.find((tc) => tc.id === 'retry_max_backoff_capped')!;

    const agent = new MockRetryAgent(testCase.scenario.agent_responses);
    const config: RetryConfig = {
      maxRetries: testCase.config.max_retries,
      initialDelayMs: testCase.config.initial_backoff_ms,
      maxDelayMs: testCase.config.max_backoff_ms,
      backoffMultiplier: testCase.config.backoff_multiplier,
      shouldRetry: () => true, // Always retry for tests
    };
    const retry = new RetryMiddleware(agent, config);

    // Measure time
    const start = Date.now();
    const message: Message = { role: 'user', content: 'test', metadata: {}, timestamp: Date.now() };
    const response = await retry.process(message);
    const elapsed = Date.now() - start;

    // Verify expected behavior
    expect(agent.callCount).toBe(testCase.expected_behavior!.total_attempts);
    expect(testCase.expected_behavior!.successful).toBe(true);
    expect(testCase.expected_behavior!.delays_capped).toBe(true);

    // Verify capped backoff
    const minDelay = testCase.expected_behavior!.min_total_delay_ms!;
    const maxDelay = testCase.expected_behavior!.max_total_delay_ms!;
    expect(elapsed).toBeGreaterThanOrEqual(atLeastMs(minDelay));
    expect(elapsed).toBeLessThanOrEqual(maxDelay * 3 + 500); // generous: CI scheduling latency
    expect(response.content).toBe('Success');
  });

  it('non-retryable error', async () => {
    const testCase = fixtures.test_cases.find((tc) => tc.id === 'retry_non_retryable_error')!;

    const agent = new MockRetryAgent(testCase.scenario.agent_responses);

    // Define should retry predicate
    const shouldRetry = (error: Error) => !error.message.includes('InvalidInput');

    const config: RetryConfig = {
      maxRetries: testCase.config.max_retries,
      initialDelayMs: testCase.config.initial_backoff_ms,
      maxDelayMs: testCase.config.max_backoff_ms,
      backoffMultiplier: testCase.config.backoff_multiplier,
      shouldRetry, // Don't retry InvalidInput errors
    };
    const retry = new RetryMiddleware(agent, config);

    // Should fail immediately without retrying
    const message: Message = { role: 'user', content: 'test', metadata: {}, timestamp: Date.now() };
    await expect(retry.process(message)).rejects.toThrow();

    // Verify expected behavior
    expect(agent.callCount).toBe(testCase.expected_behavior!.total_attempts);
    expect(testCase.expected_behavior!.successful).toBe(false);
    expect(testCase.expected_behavior!.should_not_retry).toBe(true);
  });

  it('metrics tracking', async () => {
    const testCase = fixtures.test_cases.find((tc) => tc.id === 'retry_metrics_tracking')!;

    const agent = new MockRetryAgent(testCase.scenario.agent_responses);
    const config: RetryConfig = {
      maxRetries: testCase.config.max_retries,
      initialDelayMs: testCase.config.initial_backoff_ms,
      maxDelayMs: testCase.config.max_backoff_ms,
      backoffMultiplier: testCase.config.backoff_multiplier,
      shouldRetry: () => true, // Always retry for tests
    };
    const retry = new RetryMiddleware(agent, config);

    // Execute request (fails once, then succeeds)
    const message: Message = { role: 'user', content: 'test', metadata: {}, timestamp: Date.now() };
    const response = await retry.process(message);

    // Verify success
    expect(response.content).toBe('Success');

    // Verify metrics
    const expected = testCase.expected_metrics!;
    const metrics = retry.metrics;

    expect(metrics.totalAttempts).toBe(expected.total_attempts);
    expect(metrics.successfulFirstAttempt).toBe(expected.successful_first_attempt);
    expect(metrics.successfulOnRetry).toBe(expected.successful_on_retry);
  });
});

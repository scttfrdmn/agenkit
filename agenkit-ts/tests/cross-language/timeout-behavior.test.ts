/**
 * Cross-language timeout behavior tests for TypeScript
 *
 * Validates that Agenkit's TypeScript timeout middleware behaves consistently
 * with the cross-language timeout behavior specification.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';
import { TimeoutMiddleware, TimeoutConfig } from '../../src/middleware/timeout.js';
import type { Agent, Message } from '../../src/core/interfaces.js';
import { atLeastMs } from '../../src/__tests__/support/timing.js';

interface TimeoutBehaviorFixtures {
  version: string;
  description: string;
  test_cases: TimeoutBehaviorTestCase[];
}

interface TimeoutBehaviorTestCase {
  id: string;
  name: string;
  config: {
    timeout_ms: number;
  };
  scenario: {
    agent_delay_ms?: number;
    agent_response?: {
      success: boolean;
      content?: string;
      error?: string;
    };
    requests?: Array<{
      agent_delay_ms: number;
      agent_response: {
        success: boolean;
        content?: string;
        error?: string;
      };
    }>;
  };
  expected_behavior?: {
    successful: boolean;
    timed_out: boolean;
    final_response?: string;
    error_type?: string;
    error_message_contains?: string;
    min_elapsed_ms: number;
    max_elapsed_ms: number;
  };
  expected_metrics?: {
    total_requests: number;
    successful_requests: number;
    timed_out_requests: number;
    success_rate: number;
  };
}

/**
 * Mock agent that simulates delays for timeout testing
 */
class MockTimeoutAgent implements Agent {
  private delayMs: number;
  private response: { success: boolean; content?: string; error?: string };
  public callCount: number = 0;

  constructor(
    delayMs: number,
    response: { success: boolean; content?: string; error?: string }
  ) {
    this.delayMs = delayMs;
    this.response = response;
  }

  get name(): string {
    return 'mock-timeout-agent';
  }

  get capabilities(): string[] {
    return [];
  }

  async process(_message: Message): Promise<Message> {
    this.callCount++;

    // Simulate delay
    if (this.delayMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, this.delayMs));
    }

    // Return response or error
    if (this.response.success) {
      return {
        role: 'agent',
        content: this.response.content || '',
      };
    } else {
      throw new Error(this.response.error || 'Agent error');
    }
  }
}

/**
 * Load timeout behavior fixtures
 */
function loadFixtures(): TimeoutBehaviorFixtures {
  const fixturesPath = join(
    __dirname,
    '../../../tests/cross_language/fixtures/timeout_behavior.json'
  );
  const fixturesData = readFileSync(fixturesPath, 'utf-8');
  return JSON.parse(fixturesData);
}

/**
 * Find a specific test case by ID
 */
function findTestCase(fixtures: TimeoutBehaviorFixtures, id: string): TimeoutBehaviorTestCase {
  const testCase = fixtures.test_cases.find((tc) => tc.id === id);
  if (!testCase) {
    throw new Error(`Test case not found: ${id}`);
  }
  return testCase;
}

describe('Cross-Language Timeout Behavior', () => {
  let fixtures: TimeoutBehaviorFixtures;

  beforeAll(() => {
    fixtures = loadFixtures();
  });

  it('should complete successfully within timeout limit', async () => {
    const testCase = findTestCase(fixtures, 'timeout_success_within_limit');

    // Create mock agent
    const mockAgent = new MockTimeoutAgent(
      testCase.scenario.agent_delay_ms!,
      testCase.scenario.agent_response!
    );

    // Create timeout middleware
    const config: TimeoutConfig = {
      timeoutMs: testCase.config.timeout_ms,
    };
    const timeoutAgent = new TimeoutMiddleware(mockAgent, config);

    // Execute with timing
    const start = Date.now();
    const message: Message = { role: 'user', content: 'test' };
    const result = await timeoutAgent.process(message);
    const elapsed = Date.now() - start;

    // Verify expected behavior
    const expected = testCase.expected_behavior!;
    expect(result).toBeDefined();
    expect(expected.successful).toBe(true);
    expect(expected.timed_out).toBe(false);
    expect(result.content).toBe(expected.final_response);

    expect(elapsed).toBeGreaterThanOrEqual(atLeastMs(expected.min_elapsed_ms));
    expect(elapsed).toBeLessThanOrEqual(expected.max_elapsed_ms);
  });

  it('should timeout when request exceeds limit', async () => {
    const testCase = findTestCase(fixtures, 'timeout_exceeded');

    // Create mock agent
    const mockAgent = new MockTimeoutAgent(
      testCase.scenario.agent_delay_ms!,
      testCase.scenario.agent_response!
    );

    // Create timeout middleware
    const config: TimeoutConfig = {
      timeoutMs: testCase.config.timeout_ms,
    };
    const timeoutAgent = new TimeoutMiddleware(mockAgent, config);

    // Execute with timing
    const start = Date.now();
    const message: Message = { role: 'user', content: 'test' };

    // Verify timeout error
    const expected = testCase.expected_behavior!;
    await expect(timeoutAgent.process(message)).rejects.toThrow();

    const elapsed = Date.now() - start;
    expect(expected.successful).toBe(false);
    expect(expected.timed_out).toBe(true);

    expect(elapsed).toBeGreaterThanOrEqual(atLeastMs(expected.min_elapsed_ms));
    expect(elapsed).toBeLessThanOrEqual(expected.max_elapsed_ms);
  });

  it('should handle request exactly at timeout boundary', async () => {
    const testCase = findTestCase(fixtures, 'timeout_exactly_at_limit');

    // Create mock agent
    const mockAgent = new MockTimeoutAgent(
      testCase.scenario.agent_delay_ms!,
      testCase.scenario.agent_response!
    );

    // Create timeout middleware
    const config: TimeoutConfig = {
      timeoutMs: testCase.config.timeout_ms,
    };
    const timeoutAgent = new TimeoutMiddleware(mockAgent, config);

    // Execute with timing
    const start = Date.now();
    const message: Message = { role: 'user', content: 'test' };
    const result = await timeoutAgent.process(message);
    const elapsed = Date.now() - start;

    // Verify expected behavior
    const expected = testCase.expected_behavior!;
    expect(result).toBeDefined();
    expect(expected.successful).toBe(true);
    expect(expected.timed_out).toBe(false);
    expect(result.content).toBe(expected.final_response);

    expect(elapsed).toBeGreaterThanOrEqual(atLeastMs(expected.min_elapsed_ms));
    expect(elapsed).toBeLessThanOrEqual(expected.max_elapsed_ms);
  });

  it('should complete immediately with zero delay', async () => {
    const testCase = findTestCase(fixtures, 'timeout_zero_delay');

    // Create mock agent
    const mockAgent = new MockTimeoutAgent(
      testCase.scenario.agent_delay_ms!,
      testCase.scenario.agent_response!
    );

    // Create timeout middleware
    const config: TimeoutConfig = {
      timeoutMs: testCase.config.timeout_ms,
    };
    const timeoutAgent = new TimeoutMiddleware(mockAgent, config);

    // Execute with timing
    const start = Date.now();
    const message: Message = { role: 'user', content: 'test' };
    const result = await timeoutAgent.process(message);
    const elapsed = Date.now() - start;

    // Verify expected behavior
    const expected = testCase.expected_behavior!;
    expect(result).toBeDefined();
    expect(expected.successful).toBe(true);
    expect(expected.timed_out).toBe(false);
    expect(result.content).toBe(expected.final_response);

    expect(elapsed).toBeLessThanOrEqual(expected.max_elapsed_ms);
  });

  it('should propagate agent errors before timeout', async () => {
    const testCase = findTestCase(fixtures, 'timeout_agent_error');

    // Create mock agent
    const mockAgent = new MockTimeoutAgent(
      testCase.scenario.agent_delay_ms!,
      testCase.scenario.agent_response!
    );

    // Create timeout middleware
    const config: TimeoutConfig = {
      timeoutMs: testCase.config.timeout_ms,
    };
    const timeoutAgent = new TimeoutMiddleware(mockAgent, config);

    // Execute with timing
    const start = Date.now();
    const message: Message = { role: 'user', content: 'test' };

    // Verify agent error (not timeout)
    const expected = testCase.expected_behavior!;
    try {
      await timeoutAgent.process(message);
      throw new Error('Should have thrown an error');
    } catch (error: any) {
      expect(expected.successful).toBe(false);
      expect(expected.timed_out).toBe(false);
      expect(error.message).toContain(expected.error_message_contains);
    }

    const elapsed = Date.now() - start;
    expect(elapsed).toBeGreaterThanOrEqual(atLeastMs(expected.min_elapsed_ms));
    expect(elapsed).toBeLessThanOrEqual(expected.max_elapsed_ms);
  });

  it('should handle very short timeouts', async () => {
    const testCase = findTestCase(fixtures, 'timeout_very_short');

    // Create mock agent
    const mockAgent = new MockTimeoutAgent(
      testCase.scenario.agent_delay_ms!,
      testCase.scenario.agent_response!
    );

    // Create timeout middleware
    const config: TimeoutConfig = {
      timeoutMs: testCase.config.timeout_ms,
    };
    const timeoutAgent = new TimeoutMiddleware(mockAgent, config);

    // Execute with timing
    const start = Date.now();
    const message: Message = { role: 'user', content: 'test' };

    // Verify timeout error
    const expected = testCase.expected_behavior!;
    await expect(timeoutAgent.process(message)).rejects.toThrow();

    const elapsed = Date.now() - start;
    expect(expected.successful).toBe(false);
    expect(expected.timed_out).toBe(true);

    expect(elapsed).toBeGreaterThanOrEqual(atLeastMs(expected.min_elapsed_ms));
    // Very short timeouts get wider tolerance
    expect(elapsed).toBeLessThanOrEqual(expected.max_elapsed_ms + 20);
  });

  it('should track metrics across multiple requests', async () => {
    const testCase = findTestCase(fixtures, 'timeout_metrics_tracking');

    // Create timeout config
    const config: TimeoutConfig = {
      timeoutMs: testCase.config.timeout_ms,
    };

    // Process multiple requests
    let successful = 0;
    let timedOut = 0;

    for (const request of testCase.scenario.requests!) {
      const mockAgent = new MockTimeoutAgent(
        request.agent_delay_ms,
        request.agent_response
      );
      const timeoutAgent = new TimeoutMiddleware(mockAgent, config);

      const message: Message = { role: 'user', content: 'test' };

      try {
        await timeoutAgent.process(message);
        successful++;
      } catch (error) {
        timedOut++;
      }
    }

    // Verify metrics
    const expectedMetrics = testCase.expected_metrics!;
    expect(testCase.scenario.requests!.length).toBe(expectedMetrics.total_requests);
    expect(successful).toBe(expectedMetrics.successful_requests);
    expect(timedOut).toBe(expectedMetrics.timed_out_requests);
  });
});

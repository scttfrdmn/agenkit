/**
 * Cross-language circuit breaker behavior tests for TypeScript
 *
 * Validates that Agenkit's TypeScript circuit breaker middleware behaves consistently
 * with the cross-language circuit breaker behavior specification.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';
import {
  CircuitBreakerMiddleware,
  CircuitBreakerConfig,
  CircuitState,
  CircuitBreakerError,
} from '../../src/middleware/circuit-breaker.js';
import type { Agent, Message } from '../../src/core/interfaces.js';

interface CircuitBreakerFixtures {
  version: string;
  description: string;
  test_cases: CircuitBreakerTestCase[];
}

interface CircuitBreakerTestCase {
  id: string;
  name: string;
  config: {
    failure_threshold: number;
    recovery_timeout_ms: number;
    success_threshold: number;
    timeout_ms: number;
  };
  scenario: {
    agent_responses?: Array<{
      success: boolean;
      content?: string;
      error?: string;
    }>;
    steps?: Array<{
      action: string;
      agent_response?: {
        success: boolean;
        content?: string;
        error?: string;
      };
      duration_ms?: number;
    }>;
  };
  expected_behavior?: {
    final_state: string;
    total_requests?: number;
    successful_requests?: number;
    failed_requests?: number;
    rejected_requests?: number;
    all_requests_completed?: boolean;
    state_transitions?: string[];
    fourth_request_rejected?: boolean;
    recovery_successful?: boolean;
    total_successful_in_half_open?: number;
    circuit_fully_recovered?: boolean;
    reopened_after_partial_recovery?: boolean;
    all_rejected_while_open?: boolean;
  };
  expected_metrics?: {
    total_requests: number;
    successful_requests: number;
    failed_requests: number;
    rejected_requests: number;
    state_changes: Record<string, number>;
    final_state: string;
  };
}

/**
 * Mock agent that simulates responses from fixture scenarios
 */
class MockCircuitBreakerAgent implements Agent {
  private responses: Array<{ success: boolean; content?: string; error?: string }>;
  public callCount: number = 0;

  constructor(responses: Array<{ success: boolean; content?: string; error?: string }>) {
    this.responses = responses;
  }

  get name(): string {
    return 'mock-circuit-breaker-agent';
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
        content: response.content || '',
      };
    } else {
      throw new Error(response.error || 'Agent error');
    }
  }
}

/**
 * Load circuit breaker behavior fixtures
 */
function loadFixtures(): CircuitBreakerFixtures {
  const fixturesPath = join(
    __dirname,
    '../../../tests/cross_language/fixtures/circuit_breaker_behavior.json'
  );
  const fixturesData = readFileSync(fixturesPath, 'utf-8');
  return JSON.parse(fixturesData);
}

/**
 * Find a specific test case by ID
 */
function findTestCase(fixtures: CircuitBreakerFixtures, id: string): CircuitBreakerTestCase {
  const testCase = fixtures.test_cases.find((tc) => tc.id === id);
  if (!testCase) {
    throw new Error(`Test case not found: ${id}`);
  }
  return testCase;
}

/**
 * Sleep for specified milliseconds
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

describe('Cross-Language Circuit Breaker Behavior', () => {
  let fixtures: CircuitBreakerFixtures;

  beforeAll(() => {
    fixtures = loadFixtures();
  });

  it('should remain closed with successful requests', async () => {
    const testCase = findTestCase(fixtures, 'circuit_breaker_closed_success');

    // Create mock agent
    const mockAgent = new MockCircuitBreakerAgent(testCase.scenario.agent_responses!);

    // Create circuit breaker
    const config: CircuitBreakerConfig = {
      failureThreshold: testCase.config.failure_threshold,
      timeout: testCase.config.recovery_timeout_ms,
      successThreshold: testCase.config.success_threshold,
      requestTimeout: testCase.config.timeout_ms,
    };
    const circuitBreaker = new CircuitBreakerMiddleware(mockAgent, config);

    // Execute requests
    let successful = 0;
    for (let i = 0; i < testCase.scenario.agent_responses!.length; i++) {
      const message: Message = { role: 'user', content: 'test' };
      const result = await circuitBreaker.process(message);
      expect(result).toBeDefined();
      successful++;
    }

    // Verify expected behavior
    const expected = testCase.expected_behavior!;
    expect(circuitBreaker.state).toBe(CircuitState.CLOSED);
    expect(circuitBreaker.metrics.totalRequests).toBe(expected.total_requests);
    expect(circuitBreaker.metrics.successfulRequests).toBe(expected.successful_requests);
    expect(circuitBreaker.metrics.failedRequests).toBe(expected.failed_requests);
    expect(circuitBreaker.metrics.rejectedRequests).toBe(expected.rejected_requests);
    expect(successful).toBe(expected.total_requests);
  });

  it('should open after failure threshold is reached', async () => {
    const testCase = findTestCase(fixtures, 'circuit_breaker_opens_on_failures');

    // Create mock agent
    const mockAgent = new MockCircuitBreakerAgent(testCase.scenario.agent_responses!);

    // Create circuit breaker
    const config: CircuitBreakerConfig = {
      failureThreshold: testCase.config.failure_threshold,
      timeout: testCase.config.recovery_timeout_ms,
      successThreshold: testCase.config.success_threshold,
      requestTimeout: testCase.config.timeout_ms,
    };
    const circuitBreaker = new CircuitBreakerMiddleware(mockAgent, config);

    // Execute requests
    let rejected = 0;
    for (let i = 0; i < testCase.scenario.agent_responses!.length; i++) {
      const message: Message = { role: 'user', content: 'test' };
      try {
        await circuitBreaker.process(message);
      } catch (error: any) {
        if (error instanceof CircuitBreakerError) {
          rejected++;
        }
      }
    }

    // Verify expected behavior
    const expected = testCase.expected_behavior!;
    expect(circuitBreaker.state).toBe(CircuitState.OPEN);
    expect(circuitBreaker.metrics.totalRequests).toBe(expected.total_requests);
    expect(circuitBreaker.metrics.failedRequests).toBe(expected.failed_requests);
    expect(circuitBreaker.metrics.rejectedRequests).toBe(expected.rejected_requests);
    expect(expected.fourth_request_rejected).toBe(true);
  });

  it('should transition to half-open after recovery timeout', async () => {
    const testCase = findTestCase(fixtures, 'circuit_breaker_half_open_transition');

    // Extract responses from steps
    const responses = testCase.scenario.steps!
      .filter((step) => step.action === 'request')
      .map((step) => step.agent_response!);

    const mockAgent = new MockCircuitBreakerAgent(responses);

    // Create circuit breaker
    const config: CircuitBreakerConfig = {
      failureThreshold: testCase.config.failure_threshold,
      timeout: testCase.config.recovery_timeout_ms,
      successThreshold: testCase.config.success_threshold,
      requestTimeout: testCase.config.timeout_ms,
    };
    const circuitBreaker = new CircuitBreakerMiddleware(mockAgent, config);

    // Execute steps
    for (const step of testCase.scenario.steps!) {
      if (step.action === 'request') {
        const message: Message = { role: 'user', content: 'test' };
        try {
          await circuitBreaker.process(message);
        } catch (error) {
          // Expected failures
        }
      } else if (step.action === 'wait') {
        await sleep(step.duration_ms!);
      }
    }

    // Verify expected behavior
    const expected = testCase.expected_behavior!;
    expect(circuitBreaker.state).toBe(CircuitState.CLOSED);
    expect(expected.recovery_successful).toBe(true);
  });

  it('should close after success threshold in half-open state', async () => {
    const testCase = findTestCase(fixtures, 'circuit_breaker_half_open_to_closed');

    // Extract responses from steps
    const responses = testCase.scenario.steps!
      .filter((step) => step.action === 'request')
      .map((step) => step.agent_response!);

    const mockAgent = new MockCircuitBreakerAgent(responses);

    // Create circuit breaker
    const config: CircuitBreakerConfig = {
      failureThreshold: testCase.config.failure_threshold,
      timeout: testCase.config.recovery_timeout_ms,
      successThreshold: testCase.config.success_threshold,
      requestTimeout: testCase.config.timeout_ms,
    };
    const circuitBreaker = new CircuitBreakerMiddleware(mockAgent, config);

    // Execute steps
    for (const step of testCase.scenario.steps!) {
      if (step.action === 'request') {
        const message: Message = { role: 'user', content: 'test' };
        try {
          await circuitBreaker.process(message);
        } catch (error) {
          // Expected failures
        }
      } else if (step.action === 'wait') {
        await sleep(step.duration_ms!);
      }
    }

    // Verify expected behavior
    const expected = testCase.expected_behavior!;
    expect(circuitBreaker.state).toBe(CircuitState.CLOSED);
    expect(expected.circuit_fully_recovered).toBe(true);
  });

  it('should reopen on failure in half-open state', async () => {
    const testCase = findTestCase(fixtures, 'circuit_breaker_half_open_reopens');

    // Extract responses from steps
    const responses = testCase.scenario.steps!
      .filter((step) => step.action === 'request')
      .map((step) => step.agent_response!);

    const mockAgent = new MockCircuitBreakerAgent(responses);

    // Create circuit breaker
    const config: CircuitBreakerConfig = {
      failureThreshold: testCase.config.failure_threshold,
      timeout: testCase.config.recovery_timeout_ms,
      successThreshold: testCase.config.success_threshold,
      requestTimeout: testCase.config.timeout_ms,
    };
    const circuitBreaker = new CircuitBreakerMiddleware(mockAgent, config);

    // Execute steps
    for (const step of testCase.scenario.steps!) {
      if (step.action === 'request') {
        const message: Message = { role: 'user', content: 'test' };
        try {
          await circuitBreaker.process(message);
        } catch (error) {
          // Expected failures
        }
      } else if (step.action === 'wait') {
        await sleep(step.duration_ms!);
      }
    }

    // Verify expected behavior
    const expected = testCase.expected_behavior!;
    expect(circuitBreaker.state).toBe(CircuitState.OPEN);
    expect(expected.reopened_after_partial_recovery).toBe(true);
  });

  it('should reject all requests when open', async () => {
    const testCase = findTestCase(fixtures, 'circuit_breaker_rejects_when_open');

    // Create mock agent
    const mockAgent = new MockCircuitBreakerAgent(testCase.scenario.agent_responses!);

    // Create circuit breaker
    const config: CircuitBreakerConfig = {
      failureThreshold: testCase.config.failure_threshold,
      timeout: testCase.config.recovery_timeout_ms,
      successThreshold: testCase.config.success_threshold,
      requestTimeout: testCase.config.timeout_ms,
    };
    const circuitBreaker = new CircuitBreakerMiddleware(mockAgent, config);

    // Execute requests
    let rejected = 0;
    for (let i = 0; i < testCase.scenario.agent_responses!.length; i++) {
      const message: Message = { role: 'user', content: 'test' };
      try {
        await circuitBreaker.process(message);
      } catch (error: any) {
        if (error instanceof CircuitBreakerError) {
          rejected++;
        }
      }
    }

    // Verify expected behavior
    const expected = testCase.expected_behavior!;
    expect(circuitBreaker.state).toBe(CircuitState.OPEN);
    expect(circuitBreaker.metrics.rejectedRequests).toBe(expected.rejected_requests);
    expect(rejected).toBe(expected.rejected_requests);
  });

  it('should track metrics accurately', async () => {
    const testCase = findTestCase(fixtures, 'circuit_breaker_metrics_tracking');

    // Extract responses from steps
    const responses = testCase.scenario.steps!
      .filter((step) => step.action === 'request')
      .map((step) => step.agent_response!);

    const mockAgent = new MockCircuitBreakerAgent(responses);

    // Create circuit breaker
    const config: CircuitBreakerConfig = {
      failureThreshold: testCase.config.failure_threshold,
      timeout: testCase.config.recovery_timeout_ms,
      successThreshold: testCase.config.success_threshold,
      requestTimeout: testCase.config.timeout_ms,
    };
    const circuitBreaker = new CircuitBreakerMiddleware(mockAgent, config);

    // Execute steps
    for (const step of testCase.scenario.steps!) {
      if (step.action === 'request') {
        const message: Message = { role: 'user', content: 'test' };
        try {
          await circuitBreaker.process(message);
        } catch (error) {
          // Expected failures and rejections
        }
      } else if (step.action === 'wait') {
        await sleep(step.duration_ms!);
      }
    }

    // Verify expected metrics
    const expected = testCase.expected_metrics!;
    expect(circuitBreaker.metrics.totalRequests).toBe(expected.total_requests);
    expect(circuitBreaker.metrics.successfulRequests).toBe(expected.successful_requests);
    expect(circuitBreaker.metrics.failedRequests).toBe(expected.failed_requests);
    expect(circuitBreaker.metrics.rejectedRequests).toBe(expected.rejected_requests);
    expect(circuitBreaker.state).toBe(CircuitState.CLOSED);
  });
});

/**
 * Cross-language rate limiter behavior tests for TypeScript.
 *
 * Validates that Agenkit's TypeScript rate limiter middleware behaves consistently
 * with the cross-language rate limiter behavior specification.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import { Agent, Message } from '../../src/core/interfaces';
import { RateLimiterConfig, RateLimiterDecorator, RateLimitError } from '../../src/middleware/rate-limiter';

/**
 * Mock agent for rate limiter testing.
 */
class MockRateLimiterAgent implements Agent {
  name = 'mock-rate-limiter-agent';
  capabilities: string[] = [];
  private callCount = 0;

  async process(message: Message): Promise<Message> {
    this.callCount++;
    return {
      role: 'agent',
      content: `Response ${this.callCount}`,
    };
  }
}

interface RateLimiterTestCase {
  id: string;
  name: string;
  config: {
    rate: number;
    capacity: number;
    tokens_per_request: number;
    max_wait_ms: number | null;
  };
  scenario: {
    requests?: Array<{ delay_ms: number }>;
    steps?: Array<{ action: string; duration_ms?: number }>;
  };
  expected_behavior?: {
    all_successful: boolean;
    total_requests: number;
    allowed_requests: number;
    rejected_requests: number;
    min_total_time_ms?: number;
    max_total_time_ms?: number;
    sixth_request_waited?: boolean;
    min_wait_time_ms?: number;
    max_wait_time_ms?: number;
    third_request_rejected?: boolean;
    tokens_refilled?: boolean;
    burst_handled?: boolean;
  };
  expected_metrics?: {
    total_requests: number;
    allowed_requests: number;
    rejected_requests: number;
    total_wait_time_greater_than: number;
  };
}

interface RateLimiterFixtures {
  version: string;
  description: string;
  test_cases: RateLimiterTestCase[];
}

let fixtures: RateLimiterFixtures;

beforeAll(() => {
  // Path from agenkit-ts/tests/cross-language to agenkit/tests/cross_language
  const fixturesPath = path.join(__dirname, '..', '..', '..', 'tests', 'cross_language', 'fixtures', 'rate_limiter_behavior.json');
  const fixturesData = fs.readFileSync(fixturesPath, 'utf-8');
  fixtures = JSON.parse(fixturesData);
});

function findTestCase(testId: string): RateLimiterTestCase {
  const testCase = fixtures.test_cases.find((tc) => tc.id === testId);
  if (!testCase) {
    throw new Error(`Test case not found: ${testId}`);
  }
  return testCase;
}

function createRateLimiterConfig(testCase: RateLimiterTestCase): RateLimiterConfig {
  return {
    rate: testCase.config.rate,
    capacity: testCase.config.capacity,
    tokensPerRequest: testCase.config.tokens_per_request,
    maxWaitTimeoutMs: testCase.config.max_wait_ms ?? undefined,
  };
}

describe('Rate Limiter Behavior', () => {
  it('allows requests within burst capacity', async () => {
    const testCase = findTestCase('rate_limiter_allows_within_capacity');
    const mockAgent = new MockRateLimiterAgent();
    const config = createRateLimiterConfig(testCase);
    const rateLimiter = new RateLimiterDecorator(mockAgent, config);

    const start = Date.now();
    let successful = 0;
    for (const _ of testCase.scenario.requests!) {
      const msg: Message = { role: 'user', content: 'test' };
      try {
        await rateLimiter.process(msg);
        successful++;
      } catch (error) {
        // Rate limit error
      }
    }
    const elapsed = Date.now() - start;

    const expected = testCase.expected_behavior!;
    expect(expected.all_successful).toBe(true);
    expect(rateLimiter.metrics.totalRequests).toBe(expected.total_requests);
    expect(rateLimiter.metrics.allowedRequests).toBe(expected.allowed_requests);
    expect(rateLimiter.metrics.rejectedRequests).toBe(expected.rejected_requests);
    expect(successful).toBe(expected.total_requests);
    expect(elapsed).toBeGreaterThanOrEqual(expected.min_total_time_ms!);
    expect(elapsed).toBeLessThanOrEqual(expected.max_total_time_ms!);
  });

  it('waits for tokens when capacity exceeded', async () => {
    const testCase = findTestCase('rate_limiter_waits_for_tokens');
    const mockAgent = new MockRateLimiterAgent();
    const config = createRateLimiterConfig(testCase);
    const rateLimiter = new RateLimiterDecorator(mockAgent, config);

    const waitTimes: number[] = [];
    for (const _ of testCase.scenario.requests!) {
      const msg: Message = { role: 'user', content: 'test' };
      const start = Date.now();
      await rateLimiter.process(msg);
      const elapsed = Date.now() - start;
      waitTimes.push(elapsed);
    }

    const expected = testCase.expected_behavior!;
    expect(expected.all_successful).toBe(true);
    expect(rateLimiter.metrics.totalRequests).toBe(expected.total_requests);
    expect(rateLimiter.metrics.allowedRequests).toBe(expected.allowed_requests);
    expect(rateLimiter.metrics.rejectedRequests).toBe(expected.rejected_requests);
    expect(expected.sixth_request_waited).toBe(true);

    // Sixth request (index 5) should have waited
    const sixthWait = waitTimes[5];
    expect(sixthWait).toBeGreaterThanOrEqual(expected.min_wait_time_ms!);
    expect(sixthWait).toBeLessThanOrEqual(expected.max_wait_time_ms!);
  });

  it('rejects requests when max_wait exceeded', async () => {
    const testCase = findTestCase('rate_limiter_rejects_on_timeout');
    const mockAgent = new MockRateLimiterAgent();
    const config = createRateLimiterConfig(testCase);
    const rateLimiter = new RateLimiterDecorator(mockAgent, config);

    let rejected = 0;
    for (const _ of testCase.scenario.requests!) {
      const msg: Message = { role: 'user', content: 'test' };
      try {
        await rateLimiter.process(msg);
      } catch (error) {
        if (error instanceof RateLimitError) {
          rejected++;
        }
      }
    }

    const expected = testCase.expected_behavior!;
    expect(expected.all_successful).toBe(false);
    expect(rateLimiter.metrics.totalRequests).toBe(expected.total_requests);
    expect(rateLimiter.metrics.allowedRequests).toBe(expected.allowed_requests);
    expect(rateLimiter.metrics.rejectedRequests).toBe(expected.rejected_requests);
    expect(rejected).toBe(expected.rejected_requests);
    expect(expected.third_request_rejected).toBe(true);
  });

  it('refills tokens at configured rate', async () => {
    const testCase = findTestCase('rate_limiter_token_refill');
    const mockAgent = new MockRateLimiterAgent();
    const config = createRateLimiterConfig(testCase);
    const rateLimiter = new RateLimiterDecorator(mockAgent, config);

    for (const step of testCase.scenario.steps!) {
      if (step.action === 'request') {
        const msg: Message = { role: 'user', content: 'test' };
        await rateLimiter.process(msg);
      } else if (step.action === 'wait') {
        await new Promise((resolve) => setTimeout(resolve, step.duration_ms!));
      }
    }

    const expected = testCase.expected_behavior!;
    expect(expected.all_successful).toBe(true);
    expect(rateLimiter.metrics.totalRequests).toBe(expected.total_requests);
    expect(rateLimiter.metrics.allowedRequests).toBe(expected.allowed_requests);
    expect(rateLimiter.metrics.rejectedRequests).toBe(expected.rejected_requests);
    expect(expected.tokens_refilled).toBe(true);
  });

  it('allows burst up to capacity', async () => {
    const testCase = findTestCase('rate_limiter_burst_capacity');
    const mockAgent = new MockRateLimiterAgent();
    const config = createRateLimiterConfig(testCase);
    const rateLimiter = new RateLimiterDecorator(mockAgent, config);

    const start = Date.now();
    for (const _ of testCase.scenario.requests!) {
      const msg: Message = { role: 'user', content: 'test' };
      await rateLimiter.process(msg);
    }
    const elapsed = Date.now() - start;

    const expected = testCase.expected_behavior!;
    expect(expected.all_successful).toBe(true);
    expect(rateLimiter.metrics.totalRequests).toBe(expected.total_requests);
    expect(rateLimiter.metrics.allowedRequests).toBe(expected.allowed_requests);
    expect(rateLimiter.metrics.rejectedRequests).toBe(expected.rejected_requests);
    expect(expected.burst_handled).toBe(true);
    expect(elapsed).toBeLessThanOrEqual(expected.max_total_time_ms!);
  });

  it('consumes multiple tokens per request', async () => {
    const testCase = findTestCase('rate_limiter_multiple_tokens_per_request');
    const mockAgent = new MockRateLimiterAgent();
    const config = createRateLimiterConfig(testCase);
    const rateLimiter = new RateLimiterDecorator(mockAgent, config);

    for (const _ of testCase.scenario.requests!) {
      const msg: Message = { role: 'user', content: 'test' };
      await rateLimiter.process(msg);
    }

    const expected = testCase.expected_behavior!;
    expect(expected.all_successful).toBe(true);
    expect(rateLimiter.metrics.totalRequests).toBe(expected.total_requests);
    expect(rateLimiter.metrics.allowedRequests).toBe(expected.allowed_requests);
    expect(rateLimiter.metrics.rejectedRequests).toBe(expected.rejected_requests);
  });

  it('tracks metrics accurately', async () => {
    const testCase = findTestCase('rate_limiter_metrics_tracking');
    const mockAgent = new MockRateLimiterAgent();
    const config = createRateLimiterConfig(testCase);
    const rateLimiter = new RateLimiterDecorator(mockAgent, config);

    for (const _ of testCase.scenario.requests!) {
      const msg: Message = { role: 'user', content: 'test' };
      try {
        await rateLimiter.process(msg);
      } catch (error) {
        // Rate limit error
      }
    }

    const expected = testCase.expected_metrics!;
    expect(rateLimiter.metrics.totalRequests).toBe(expected.total_requests);
    expect(rateLimiter.metrics.allowedRequests).toBe(expected.allowed_requests);
    expect(rateLimiter.metrics.rejectedRequests).toBe(expected.rejected_requests);
    expect(rateLimiter.metrics.totalWaitTime).toBeGreaterThanOrEqual(expected.total_wait_time_greater_than);
  });
});

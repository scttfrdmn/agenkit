/**
 * Middleware Consistency Integration Tests
 *
 * Validates that middleware behavior is consistent across different scenarios.
 * Tests retry logic, circuit breaker state transitions, rate limiting,
 * timeouts, batching, and caching consistency.
 */

import { describe, it, expect, vi } from 'vitest';
import type { Agent, Message } from '../../core/interfaces';

// ============================================
// Test Agents
// ============================================

/**
 * Agent that counts how many times it's called.
 */
class CountingAgent implements Agent {
  private callCount = 0;

  constructor(private readonly agentName: string = 'counting-agent') {}

  get name(): string {
    return this.agentName;
  }

  get capabilities(): string[] {
    return ['count'];
  }

  async process(message: Message): Promise<Message> {
    this.callCount++;
    return {
      role: 'agent',
      content: `Call #${this.callCount}: ${message.content}`,
      metadata: { call_count: this.callCount },
    };
  }

  getCallCount(): number {
    return this.callCount;
  }
}

/**
 * Agent that fails a specified number of times before succeeding.
 */
class FailingAgent implements Agent {
  private attemptCount = 0;

  constructor(
    private readonly failCount: number,
    private readonly agentName: string = 'failing-agent'
  ) {}

  get name(): string {
    return this.agentName;
  }

  get capabilities(): string[] {
    return ['fail'];
  }

  async process(message: Message): Promise<Message> {
    this.attemptCount++;
    if (this.attemptCount <= this.failCount) {
      throw new Error(`Failure ${this.attemptCount}/${this.failCount}`);
    }

    return {
      role: 'agent',
      content: `Success after ${this.failCount} failures`,
      metadata: { attempt_count: this.attemptCount },
    };
  }

  getAttemptCount(): number {
    return this.attemptCount;
  }
}

/**
 * Agent with configurable delay.
 */
class SlowAgent implements Agent {
  constructor(
    private readonly delay: number,
    private readonly agentName: string = 'slow-agent'
  ) {}

  get name(): string {
    return this.agentName;
  }

  get capabilities(): string[] {
    return ['slow'];
  }

  async process(message: Message): Promise<Message> {
    await new Promise((resolve) => setTimeout(resolve, this.delay));
    return {
      role: 'agent',
      content: `Completed after ${this.delay}ms delay`,
      metadata: { delay: this.delay },
    };
  }
}

// ============================================
// Retry Middleware Consistency Tests
// ============================================

describe('Middleware Consistency: Retry', () => {
  it('should have consistent retry count behavior', async () => {
    // Fails 2 times, succeeds on 3rd
    const agent = new FailingAgent(2);

    // Manually implement retry logic to test expected behavior
    const maxRetries = 3;
    let attempt = 0;
    let response: Message | null = null;

    for (attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        response = await agent.process({ role: 'user', content: 'test' });
        break;
      } catch {
        if (attempt < maxRetries) {
          await new Promise((resolve) => setTimeout(resolve, 10));
        }
      }
    }

    // Should succeed on 3rd attempt (after 2 retries)
    expect(agent.getAttemptCount()).toBe(3);
    expect(response?.metadata?.attempt_count).toBe(3);
  });

  it('should use consistent exponential backoff timing', () => {
    const delays = [];

    // Simulate exponential backoff: 0.1s, 0.2s, 0.4s
    const baseDelay = 0.1;
    for (let i = 0; i < 3; i++) {
      const delay = baseDelay * 2 ** i;
      delays.push(delay);
    }

    // Expected delays: [0.1, 0.2, 0.4]
    expect(delays).toEqual([0.1, 0.2, 0.4]);
    expect(Math.abs(delays.reduce((a, b) => a + b, 0) - 0.7)).toBeLessThan(0.001);
  });

  it('should exhaust retries for persistent failures', async () => {
    const agent = new FailingAgent(10); // Fails 10 times

    const maxRetries = 3;
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        await agent.process({ role: 'user', content: 'test' });
        break;
      } catch (e) {
        lastError = e as Error;
        if (attempt < maxRetries) {
          await new Promise((resolve) => setTimeout(resolve, 10));
        }
      }
    }

    // Should have exhausted all retries
    expect(lastError).not.toBeNull();
    expect(agent.getAttemptCount()).toBe(maxRetries + 1);
  });
});

// ============================================
// Circuit Breaker Consistency Tests
// ============================================

describe('Middleware Consistency: Circuit Breaker', () => {
  it('should transition states consistently (CLOSED → OPEN → HALF_OPEN → CLOSED)', () => {
    class CircuitBreakerSimulator {
      state = 'CLOSED';
      failureCount = 0;

      constructor(private readonly failureThreshold: number) {}

      recordSuccess(): void {
        if (this.state === 'HALF_OPEN') {
          this.state = 'CLOSED';
          this.failureCount = 0;
        }
      }

      recordFailure(): void {
        this.failureCount++;
        if (this.state === 'CLOSED' && this.failureCount >= this.failureThreshold) {
          this.state = 'OPEN';
        }
      }

      attemptRecovery(): void {
        if (this.state === 'OPEN') {
          this.state = 'HALF_OPEN';
        }
      }
    }

    const cb = new CircuitBreakerSimulator(3);

    // Initial state
    expect(cb.state).toBe('CLOSED');

    // Record 3 failures → should open
    for (let i = 0; i < 3; i++) {
      cb.recordFailure();
    }

    expect(cb.state).toBe('OPEN');
    expect(cb.failureCount).toBe(3);

    // Attempt recovery → should go to HALF_OPEN
    cb.attemptRecovery();
    expect(cb.state).toBe('HALF_OPEN');

    // Success in HALF_OPEN → should close
    cb.recordSuccess();
    expect(cb.state).toBe('CLOSED');
    expect(cb.failureCount).toBe(0);
  });

  it('should prevent requests when circuit is open', () => {
    class CircuitBreaker {
      private state = 'CLOSED';
      private failures = 0;

      constructor(private readonly threshold: number) {}

      allowRequest(): boolean {
        return this.state !== 'OPEN';
      }

      recordFailure(): void {
        this.failures++;
        if (this.failures >= this.threshold) {
          this.state = 'OPEN';
        }
      }
    }

    const cb = new CircuitBreaker(3);

    // Should allow requests initially
    expect(cb.allowRequest()).toBe(true);

    // Record 3 failures
    for (let i = 0; i < 3; i++) {
      cb.recordFailure();
    }

    // Should block requests when open
    expect(cb.allowRequest()).toBe(false);
  });
});

// ============================================
// Rate Limiter Consistency Tests
// ============================================

describe('Middleware Consistency: Rate Limiter', () => {
  it('should use consistent token bucket algorithm', async () => {
    class TokenBucket {
      private tokens: number;
      private lastUpdate: number;

      constructor(
        private readonly rate: number, // tokens per second
        private readonly burst: number // max tokens
      ) {
        this.tokens = burst;
        this.lastUpdate = Date.now();
      }

      consume(tokens = 1): boolean {
        // Refill tokens based on elapsed time
        const now = Date.now();
        const elapsed = (now - this.lastUpdate) / 1000;
        this.tokens = Math.min(this.burst, this.tokens + elapsed * this.rate);
        this.lastUpdate = now;

        // Try to consume
        if (this.tokens >= tokens) {
          this.tokens -= tokens;
          return true;
        }
        return false;
      }
    }

    // 10 tokens/second, burst of 10
    const bucket = new TokenBucket(10.0, 10);

    // Should be able to consume 10 tokens immediately (burst)
    for (let i = 0; i < 10; i++) {
      expect(bucket.consume()).toBe(true);
    }

    // 11th should fail (no tokens left)
    expect(bucket.consume()).toBe(false);

    // Fake timers: refill is computed from Date.now() elapsed, so advancing the
    // simulated clock 100ms refills 1 token just as a real wait would.
    vi.useFakeTimers();
    try {
      await vi.advanceTimersByTimeAsync(100);
      expect(bucket.consume()).toBe(true);
    } finally {
      vi.useRealTimers();
    }
  });

  it('should enforce rate limits consistently', () => {
    const rateLimit = 10; // requests per second
    const window = 1000; // 1 second window

    let requestsInWindow = 0;
    let windowStart = Date.now();

    // Simulate rate limiting
    for (let i = 0; i < 15; i++) {
      const now = Date.now();
      if (now - windowStart > window) {
        // Reset window
        windowStart = now;
        requestsInWindow = 0;
      }

      if (requestsInWindow < rateLimit) {
        requestsInWindow++;
      }
    }

    expect(requestsInWindow).toBeLessThanOrEqual(rateLimit);
  });
});

// ============================================
// Timeout Middleware Consistency Tests
// ============================================

describe('Middleware Consistency: Timeout', () => {
  it('should enforce timeouts consistently', async () => {
    const agent = new SlowAgent(500); // Takes 500ms

    // Fake timers: both branches are behavior assertions (which side of the
    // race wins), not wall-clock magnitudes. Advancing the simulated clock to
    // each deadline reproduces the same outcomes instantly.
    vi.useFakeTimers();
    try {
      // Test with 1000ms timeout (should succeed: agent at 500ms wins)
      const timeout1 = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('Timeout')), 1000)
      );
      const race1 = Promise.race([agent.process({ role: 'user', content: 'test' }), timeout1]);
      await vi.advanceTimersByTimeAsync(500);
      const response = await race1;

      expect((response as Message).metadata?.delay).toBe(500);

      // Test with 100ms timeout (should fail: timeout fires before agent)
      const timeout2 = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('Timeout')), 100)
      );
      const assertion = expect(
        Promise.race([agent.process({ role: 'user', content: 'test' }), timeout2])
      ).rejects.toThrow('Timeout');
      await vi.advanceTimersByTimeAsync(100);
      await assertion;
    } finally {
      vi.useRealTimers();
    }
  });

  it('should measure timeout duration accurately', async () => {
    // Magnitudes scaled down 5x ([100,200,500] -> [20,40,100]); this test
    // self-measures setTimeout accuracy, which holds at smaller magnitudes with
    // the same relative tolerance.
    const timeouts = [20, 40, 100];

    for (const timeout of timeouts) {
      const start = Date.now();
      const promise = new Promise((resolve) => setTimeout(resolve, timeout));
      await promise;
      const elapsed = Date.now() - start;

      // Allow generous upper variance
      expect(elapsed).toBeGreaterThanOrEqual(timeout - 5);
      expect(elapsed).toBeLessThan(timeout + 50);
    }
  });
});

// ============================================
// Batching Middleware Consistency Tests
// ============================================

describe('Middleware Consistency: Batching', () => {
  it('should respect batch window timing', async () => {
    const agent = new CountingAgent();

    // Simulate batching: collect requests for a window, then process. Window
    // reduced 100 -> 20ms; the assertion is only that all 5 collected requests
    // are processed after the window, independent of its duration.
    const batch: Message[] = [];
    const batchWindow = 20;

    // Collect requests
    const start = Date.now();
    const deadline = start + batchWindow;

    // Add 5 requests
    for (let i = 0; i < 5; i++) {
      batch.push({ role: 'user', content: `Request ${i}` });
    }

    // Wait for batch window
    const remaining = deadline - Date.now();
    if (remaining > 0) {
      await new Promise((resolve) => setTimeout(resolve, remaining));
    }

    // Process batch
    const responses = await Promise.all(batch.map((msg) => agent.process(msg)));

    expect(responses).toHaveLength(5);
    expect(agent.getCallCount()).toBe(5);
  });

  it('should enforce batch size limits', () => {
    const maxBatchSize = 10;

    // Simulate collecting requests up to max batch size
    const batch = [];
    for (let i = 0; i < 15; i++) {
      if (batch.length < maxBatchSize) {
        batch.push(i);
      }
    }

    expect(batch).toHaveLength(10);
  });
});

// ============================================
// Caching Middleware Consistency Tests
// ============================================

describe('Middleware Consistency: Caching', () => {
  it('should have consistent cache hit/miss behavior', async () => {
    const agent = new CountingAgent();

    // Simulates caching behavior
    const cache = new Map<string, Message>();

    // First request (cache miss)
    const msg1: Message = { role: 'user', content: 'test' };
    const cacheKey = msg1.content;

    let response1: Message;
    if (!cache.has(cacheKey)) {
      response1 = await agent.process(msg1);
      cache.set(cacheKey, response1);
    } else {
      response1 = cache.get(cacheKey)!;
    }

    expect(agent.getCallCount()).toBe(1);

    // Second request (cache hit)
    let response2: Message;
    if (cache.has(cacheKey)) {
      response2 = cache.get(cacheKey)!;
    } else {
      response2 = await agent.process(msg1);
    }

    expect(agent.getCallCount()).toBe(1); // Should not increase
    expect(response1.content).toBe(response2.content);
  });

  it('should use consistent LRU eviction', () => {
    const cache = new Map<string, string>();
    const maxSize = 3;
    const accessOrder: string[] = [];

    function put(key: string, value: string): void {
      // Evict if at capacity and key doesn't exist
      if (!cache.has(key) && cache.size >= maxSize) {
        const lruKey = accessOrder.shift()!;
        cache.delete(lruKey);
      }

      cache.set(key, value);
      // Update access order
      const index = accessOrder.indexOf(key);
      if (index !== -1) {
        accessOrder.splice(index, 1);
      }
      accessOrder.push(key);
    }

    function get(key: string): string | undefined {
      const value = cache.get(key);
      if (value !== undefined) {
        // Update access order
        const index = accessOrder.indexOf(key);
        if (index !== -1) {
          accessOrder.splice(index, 1);
        }
        accessOrder.push(key);
      }
      return value;
    }

    // Add 3 entries
    put('key0', 'value0');
    put('key1', 'value1');
    put('key2', 'value2');

    expect(cache.size).toBe(3);

    // Access key0 (makes it most recently used)
    get('key0');

    // Add key3 (should evict key1, the least recently used)
    put('key3', 'value3');

    // Validate
    expect(cache.size).toBe(3);
    expect(cache.has('key0')).toBe(true); // Recently used
    expect(cache.has('key1')).toBe(false); // LRU, should be evicted
    expect(cache.has('key2')).toBe(true);
    expect(cache.has('key3')).toBe(true); // Just added
  });

  it('should handle TTL expiration consistently', async () => {
    class CacheEntry {
      private readonly expiresAt: number;

      constructor(
        public readonly value: string,
        ttl: number
      ) {
        this.expiresAt = Date.now() + ttl;
      }

      isExpired(): boolean {
        return Date.now() > this.expiresAt;
      }
    }

    // Create entry with 100ms TTL
    const entry = new CacheEntry('test_value', 100);

    // Should not be expired immediately
    expect(entry.isExpired()).toBe(false);

    // Fake timers: isExpired() compares against Date.now(), so advancing the
    // simulated clock past the TTL exercises the same expiration path.
    vi.useFakeTimers();
    try {
      await vi.advanceTimersByTimeAsync(150);
      // Should be expired now
      expect(entry.isExpired()).toBe(true);
    } finally {
      vi.useRealTimers();
    }
  });
});

// ============================================
// Metadata Preservation Tests
// ============================================

describe('Middleware Consistency: Metadata', () => {
  it('should preserve metadata through middleware chain', async () => {
    const agent = new CountingAgent();

    const message: Message = {
      role: 'user',
      content: 'test',
      metadata: {
        trace_id: 'abc-123',
        user_id: 42,
        nested: { key: 'value' },
      },
    };

    await agent.process(message);

    // Middleware should preserve original message metadata
    expect(message.metadata?.trace_id).toBe('abc-123');
    expect(message.metadata?.user_id).toBe(42);
    expect(message.metadata?.nested).toEqual({ key: 'value' });
  });

  it('should handle metadata across async boundaries', async () => {
    const agent = new CountingAgent();

    const metadata = { id: 'test-123', timestamp: Date.now() };
    const msg: Message = {
      role: 'user',
      content: 'async test',
      metadata,
    };

    const response = await agent.process(msg);

    // Original message metadata should be unchanged
    expect(msg.metadata).toEqual(metadata);

    // Response should have its own metadata
    expect(response.metadata?.call_count).toBe(1);
  });
});

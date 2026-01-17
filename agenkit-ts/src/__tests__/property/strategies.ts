/**
 * Fast-Check Strategies for Property-Based Testing
 *
 * Defines reusable arbitraries for generating test data.
 */

import * as fc from 'fast-check';
import type { Message } from '../../core/interfaces';

// Basic data strategies
export const contentArbitrary = fc.string({ maxLength: 1000 });
export const shortContentArbitrary = fc.string({ minLength: 1, maxLength: 100 });
export const roleArbitrary = fc.constantFrom('user', 'agent', 'system');

// Numeric strategies
export const positiveIntArbitrary = fc.integer({ min: 1, max: 1000 });
export const smallPositiveIntArbitrary = fc.integer({ min: 1, max: 10 });
export const probabilityArbitrary = fc.float({ min: 0.0, max: 1.0, noNaN: true });
export const durationMsArbitrary = fc.integer({ min: 1, max: 5000 });
export const ttlArbitrary = fc.integer({ min: 1, max: 3600 }); // 1s to 1 hour

// Metadata strategies
export const metadataValueArbitrary = fc.oneof(
  fc.constant(null),
  fc.boolean(),
  fc.integer({ min: -1000, max: 1000 }),
  fc.float({ min: -1000.0, max: 1000.0, noNaN: true, noDefaultInfinity: true }),
  fc.string({ maxLength: 100 })
);

export const metadataArbitrary = fc.dictionary(
  fc.string({ minLength: 1, maxLength: 20 }),
  metadataValueArbitrary,
  { maxKeys: 10 }
);

// Message strategy
export const messageArbitrary = fc.record({
  role: roleArbitrary,
  content: contentArbitrary,
  metadata: fc.option(metadataArbitrary, { nil: undefined }),
}) as fc.Arbitrary<Message>;

// List of messages strategy
export const messagesArbitrary = fc.array(messageArbitrary, { minLength: 1, maxLength: 100 });
export const smallMessagesArbitrary = fc.array(messageArbitrary, { minLength: 1, maxLength: 10 });

// Cache configuration strategies
export const cacheConfigArbitrary = fc.record({
  maxCacheSize: positiveIntArbitrary,
  defaultTtl: ttlArbitrary,
});

// Circuit breaker configuration strategies
export const circuitBreakerConfigArbitrary = fc.record({
  failureThreshold: fc.integer({ min: 1, max: 10 }),
  successThreshold: fc.integer({ min: 1, max: 10 }),
  recoveryTimeout: fc.float({ min: Math.fround(0.1), max: Math.fround(5.0), noNaN: true }),
});

// Retry configuration strategies
export const retryConfigArbitrary = fc.record({
  maxRetries: fc.integer({ min: 1, max: 10 }),
  backoffBase: fc.float({ min: Math.fround(0.01), max: Math.fround(1.0), noNaN: true }),
  maxDelay: fc.float({ min: Math.fround(1.0), max: Math.fround(10.0), noNaN: true }),
});

// Rate limiter configuration strategies
export const rateLimiterConfigArbitrary = fc.record({
  rate: fc.float({ min: Math.fround(1.0), max: Math.fround(100.0), noNaN: true }), // requests per second
  burstCapacity: fc.integer({ min: 1, max: 100 }),
});

// Batching configuration strategies
export const batchingConfigArbitrary = fc.record({
  maxBatchSize: fc.integer({ min: 1, max: 100 }),
  maxWaitTime: fc.float({ min: Math.fround(0.01), max: Math.fround(1.0), noNaN: true }),
});

// Timeout configuration strategies
export const timeoutConfigArbitrary = fc.record({
  timeout: fc.float({ min: Math.fround(0.1), max: Math.fround(5.0), noNaN: true }),
});

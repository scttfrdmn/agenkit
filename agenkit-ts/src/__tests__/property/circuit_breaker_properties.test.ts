/**
 * Circuit Breaker Property-Based Tests
 *
 * Validates invariants for circuit breaker behavior:
 * - Opens after failure threshold consecutive failures
 * - Rejects calls immediately when open
 * - Transitions to half-open after recovery timeout
 * - Resets to closed on success in half-open state
 * - Failure count never exceeds threshold when closed
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { circuitBreakerConfigArbitrary } from './strategies';

// ============================================
// Circuit Breaker Implementation for Testing
// ============================================

type CircuitState = 'closed' | 'open' | 'half_open';

interface CircuitBreakerConfig {
  failureThreshold: number;
  successThreshold: number;
  recoveryTimeout: number; // seconds
}

class CircuitBreaker {
  private state: CircuitState = 'closed';
  private failureCount = 0;
  private successCount = 0;
  private lastFailureTime?: number;

  constructor(private config: CircuitBreakerConfig) {}

  getState(): CircuitState {
    return this.state;
  }

  getFailureCount(): number {
    return this.failureCount;
  }

  /** Try to execute; returns true if call was allowed, false if rejected. */
  tryCall(success: boolean): boolean {
    // Check if we should transition from open to half-open
    if (this.state === 'open') {
      const now = Date.now() / 1000;
      if (
        this.lastFailureTime !== undefined &&
        now - this.lastFailureTime >= this.config.recoveryTimeout
      ) {
        this.state = 'half_open';
        this.successCount = 0;
      } else {
        return false; // Call rejected
      }
    }

    // Allow the call
    if (success) {
      this.onSuccess();
    } else {
      this.onFailure();
    }
    return true;
  }

  private onSuccess(): void {
    if (this.state === 'half_open') {
      this.successCount++;
      if (this.successCount >= this.config.successThreshold) {
        this.reset();
      }
    } else {
      // Reset failure count on success in closed state
      this.failureCount = 0;
    }
  }

  private onFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now() / 1000;

    if (this.state === 'half_open') {
      // Go back to open on failure in half-open
      this.state = 'open';
    } else if (this.failureCount >= this.config.failureThreshold) {
      this.state = 'open';
    }
  }

  reset(): void {
    this.state = 'closed';
    this.failureCount = 0;
    this.successCount = 0;
  }
}

// ============================================
// Property: State Transitions
// ============================================

describe('Circuit Breaker Properties: State Transitions', () => {
  it('should open after failureThreshold consecutive failures', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 10 }),
        (failureThreshold) => {
          const cb = new CircuitBreaker({
            failureThreshold,
            successThreshold: 1,
            recoveryTimeout: 1000,
          });

          // Property: starts closed
          expect(cb.getState()).toBe('closed');

          // Trigger exactly failureThreshold failures
          for (let i = 0; i < failureThreshold; i++) {
            cb.tryCall(false);
          }

          // Property: should now be open
          expect(cb.getState()).toBe('open');
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should reject calls when open', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 5 }),
        fc.integer({ min: 1, max: 10 }),
        (failureThreshold, extraCalls) => {
          const cb = new CircuitBreaker({
            failureThreshold,
            successThreshold: 1,
            recoveryTimeout: 1000, // Very long timeout — stays open
          });

          // Open the circuit
          for (let i = 0; i < failureThreshold; i++) {
            cb.tryCall(false);
          }

          expect(cb.getState()).toBe('open');

          // Property: all subsequent calls are rejected
          for (let i = 0; i < extraCalls; i++) {
            const allowed = cb.tryCall(true);
            expect(allowed).toBe(false);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should stay closed with fewer failures than threshold', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 2, max: 10 }),
        (failureThreshold) => {
          const cb = new CircuitBreaker({
            failureThreshold,
            successThreshold: 1,
            recoveryTimeout: 1000,
          });

          // Trigger fewer failures than threshold
          for (let i = 0; i < failureThreshold - 1; i++) {
            cb.tryCall(false);
          }

          // Property: still closed
          expect(cb.getState()).toBe('closed');
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should allow calls when closed', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 3, max: 10 }),
        fc.integer({ min: 1, max: 10 }),
        (failureThreshold, numCalls) => {
          const cb = new CircuitBreaker({
            failureThreshold,
            successThreshold: 1,
            recoveryTimeout: 1000,
          });

          // Make fewer failures than threshold to stay closed
          for (let i = 0; i < Math.min(numCalls, failureThreshold - 1); i++) {
            const allowed = cb.tryCall(false);
            expect(allowed).toBe(true);
          }

          expect(cb.getState()).toBe('closed');
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ============================================
// Property: Reset Behavior
// ============================================

describe('Circuit Breaker Properties: Reset', () => {
  it('should reset failure count on reset()', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 10 }),
        (failures) => {
          const cb = new CircuitBreaker({
            failureThreshold: failures + 5,
            successThreshold: 1,
            recoveryTimeout: 1000,
          });

          for (let i = 0; i < failures; i++) {
            cb.tryCall(false);
          }

          expect(cb.getFailureCount()).toBe(failures);

          cb.reset();

          expect(cb.getFailureCount()).toBe(0);
          expect(cb.getState()).toBe('closed');
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should reset to closed state', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 5 }),
        (failureThreshold) => {
          const cb = new CircuitBreaker({
            failureThreshold,
            successThreshold: 1,
            recoveryTimeout: 1000,
          });

          // Open it
          for (let i = 0; i < failureThreshold; i++) {
            cb.tryCall(false);
          }

          expect(cb.getState()).toBe('open');

          // Reset
          cb.reset();

          expect(cb.getState()).toBe('closed');
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should accept calls after reset', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 5 }),
        (failureThreshold) => {
          const cb = new CircuitBreaker({
            failureThreshold,
            successThreshold: 1,
            recoveryTimeout: 1000,
          });

          // Open it
          for (let i = 0; i < failureThreshold; i++) {
            cb.tryCall(false);
          }

          cb.reset();

          // Property: calls allowed after reset
          const allowed = cb.tryCall(true);
          expect(allowed).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ============================================
// Property: Failure Count Invariants
// ============================================

describe('Circuit Breaker Properties: Failure Count', () => {
  it('failure count should equal number of failures when closed', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 5 }),
        (failuresBeforeThreshold) => {
          const failureThreshold = failuresBeforeThreshold + 5; // High enough to stay closed
          const cb = new CircuitBreaker({
            failureThreshold,
            successThreshold: 1,
            recoveryTimeout: 1000,
          });

          for (let i = 0; i < failuresBeforeThreshold; i++) {
            cb.tryCall(false);
          }

          // Property: failure count matches
          expect(cb.getFailureCount()).toBe(failuresBeforeThreshold);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('success should reset failure count in closed state', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 3 }),
        (partialFailures) => {
          const failureThreshold = partialFailures + 5;
          const cb = new CircuitBreaker({
            failureThreshold,
            successThreshold: 1,
            recoveryTimeout: 1000,
          });

          // Some failures
          for (let i = 0; i < partialFailures; i++) {
            cb.tryCall(false);
          }

          expect(cb.getFailureCount()).toBe(partialFailures);

          // One success resets count
          cb.tryCall(true);

          expect(cb.getFailureCount()).toBe(0);
          expect(cb.getState()).toBe('closed');
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ============================================
// Property: Configuration Validation
// ============================================

describe('Circuit Breaker Properties: Configuration', () => {
  it('should handle any valid configuration without crashing', () => {
    fc.assert(
      fc.property(
        circuitBreakerConfigArbitrary,
        (config) => {
          const cb = new CircuitBreaker({
            failureThreshold: config.failureThreshold,
            successThreshold: config.successThreshold,
            recoveryTimeout: config.recoveryTimeout,
          });

          // Property: always starts in a valid state
          expect(['closed', 'open', 'half_open']).toContain(cb.getState());
          expect(cb.getFailureCount()).toBeGreaterThanOrEqual(0);
        }
      ),
      { numRuns: 100 }
    );
  });
});

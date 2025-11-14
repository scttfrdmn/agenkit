/**
 * Tests for circuit breaker middleware.
 */

import { LocalAgent, createMessage, circuitBreaker, CircuitState, CircuitBreakerError } from '../index';

describe('CircuitBreakerMiddleware', () => {
  it('should start in CLOSED state', () => {
    const agent = new LocalAgent({
      name: 'test',
      process: async (msg) => createMessage('assistant', msg.content),
    });

    const cb = circuitBreaker()(agent);

    expect((cb as any).getState()).toBe(CircuitState.CLOSED);
  });

  it('should open circuit after failure threshold', async () => {
    let callCount = 0;

    const agent = new LocalAgent({
      name: 'failing',
      process: async () => {
        callCount++;
        throw new Error('Service error');
      },
    });

    const cb = circuitBreaker({ failureThreshold: 3 })(agent);

    // Should fail 3 times before opening
    for (let i = 0; i < 3; i++) {
      await expect(cb.process(createMessage('user', 'Test'))).rejects.toThrow('Service error');
    }

    expect((cb as any).getState()).toBe(CircuitState.OPEN);
    expect(callCount).toBe(3);

    // Next call should fail immediately with CircuitBreakerError
    await expect(cb.process(createMessage('user', 'Test'))).rejects.toThrow(CircuitBreakerError);

    // Call count should not increase
    expect(callCount).toBe(3);
  });

  it('should transition to HALF_OPEN after timeout', async () => {
    const agent = new LocalAgent({
      name: 'failing',
      process: async () => {
        throw new Error('Service error');
      },
    });

    const cb = circuitBreaker({ failureThreshold: 2, timeout: 100 })(agent);

    // Open the circuit
    await expect(cb.process(createMessage('user', 'Test'))).rejects.toThrow();
    await expect(cb.process(createMessage('user', 'Test'))).rejects.toThrow();

    expect((cb as any).getState()).toBe(CircuitState.OPEN);

    // Wait for timeout
    await new Promise((resolve) => setTimeout(resolve, 150));

    // Next call should transition to HALF_OPEN and attempt the call
    await expect(cb.process(createMessage('user', 'Test'))).rejects.toThrow('Service error');

    expect((cb as any).getState()).toBe(CircuitState.OPEN); // Fails, goes back to OPEN
  });

  it('should close circuit after success threshold in HALF_OPEN', async () => {
    let callCount = 0;
    let shouldFail = true;

    const agent = new LocalAgent({
      name: 'recovering',
      process: async (msg) => {
        callCount++;

        if (shouldFail) {
          throw new Error('Service error');
        }

        return createMessage('assistant', msg.content);
      },
    });

    const cb = circuitBreaker({
      failureThreshold: 2,
      successThreshold: 2,
      timeout: 100,
    })(agent);

    // Open the circuit
    await expect(cb.process(createMessage('user', 'Test'))).rejects.toThrow();
    await expect(cb.process(createMessage('user', 'Test'))).rejects.toThrow();

    expect((cb as any).getState()).toBe(CircuitState.OPEN);

    // Wait for timeout
    await new Promise((resolve) => setTimeout(resolve, 150));

    // Service recovers
    shouldFail = false;

    // Should transition to HALF_OPEN and succeed twice
    await cb.process(createMessage('user', 'Test1'));
    expect((cb as any).getState()).toBe(CircuitState.HALF_OPEN);

    await cb.process(createMessage('user', 'Test2'));
    expect((cb as any).getState()).toBe(CircuitState.CLOSED);

    // Should continue working
    const response = await cb.process(createMessage('user', 'Test3'));
    expect(response.content).toBe('Test3');
    expect((cb as any).getState()).toBe(CircuitState.CLOSED);
  });

  it('should reset failure count on success in CLOSED state', async () => {
    let callCount = 0;

    const agent = new LocalAgent({
      name: 'intermittent',
      process: async (msg) => {
        callCount++;

        // Fail on attempts 1 and 2, succeed on 3
        if (callCount <= 2) {
          throw new Error('Service error');
        }

        return createMessage('assistant', msg.content);
      },
    });

    const cb = circuitBreaker({ failureThreshold: 5 })(agent);

    // Fail twice
    await expect(cb.process(createMessage('user', 'Test1'))).rejects.toThrow();
    expect((cb as any).getFailureCount()).toBe(1);

    await expect(cb.process(createMessage('user', 'Test2'))).rejects.toThrow();
    expect((cb as any).getFailureCount()).toBe(2);

    // Succeed once - should reset failure count
    await cb.process(createMessage('user', 'Test3'));
    expect((cb as any).getFailureCount()).toBe(0);
    expect((cb as any).getState()).toBe(CircuitState.CLOSED);
  });

  it('should manually reset circuit breaker', async () => {
    const agent = new LocalAgent({
      name: 'failing',
      process: async () => {
        throw new Error('Service error');
      },
    });

    const cb = circuitBreaker({ failureThreshold: 2 })(agent);

    // Open the circuit
    await expect(cb.process(createMessage('user', 'Test'))).rejects.toThrow();
    await expect(cb.process(createMessage('user', 'Test'))).rejects.toThrow();

    expect((cb as any).getState()).toBe(CircuitState.OPEN);

    // Manually reset
    (cb as any).reset();

    expect((cb as any).getState()).toBe(CircuitState.CLOSED);
    expect((cb as any).getFailureCount()).toBe(0);
  });

  it('should provide informative error message', async () => {
    const agent = new LocalAgent({
      name: 'my-service',
      process: async () => {
        throw new Error('Service error');
      },
    });

    const cb = circuitBreaker({ failureThreshold: 1 })(agent);

    // Open circuit
    await expect(cb.process(createMessage('user', 'Test'))).rejects.toThrow();

    // Should get CircuitBreakerError
    try {
      await cb.process(createMessage('user', 'Test'));
      fail('Should have thrown');
    } catch (error) {
      expect(error).toBeInstanceOf(CircuitBreakerError);
      expect((error as Error).message).toContain('my-service');
    }
  });

  it('should handle rapid failures correctly', async () => {
    let callCount = 0;

    const agent = new LocalAgent({
      name: 'rapid-fail',
      process: async () => {
        callCount++;
        throw new Error('Service error');
      },
    });

    const cb = circuitBreaker({ failureThreshold: 5 })(agent);

    // Fire 10 sequential requests
    const results: Error[] = [];
    for (let i = 0; i < 10; i++) {
      try {
        await cb.process(createMessage('user', 'Test'));
      } catch (error) {
        results.push(error as Error);
      }
    }

    // Should have opened circuit after 5 failures
    expect((cb as any).getState()).toBe(CircuitState.OPEN);

    // Count how many were actual service errors vs circuit breaker errors
    const serviceErrors = results.filter((r) => r.message === 'Service error').length;
    const circuitErrors = results.filter((r) => r instanceof CircuitBreakerError).length;

    // Should have made exactly 5 calls before opening
    expect(serviceErrors).toBe(5);
    expect(circuitErrors).toBe(5);
    expect(callCount).toBe(5);
  });
});

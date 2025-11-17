/**
 * Middleware Example - Production Resilience Patterns
 *
 * Demonstrates how to use middleware for building robust agents:
 * - Retry: Automatic retry with exponential backoff
 * - Timeout: Prevent hung requests
 * - Circuit Breaker: Fail fast when service is down
 *
 * Run: npx ts-node examples/middleware-example.ts
 */

import {
  LocalAgent,
  retry,
  timeout,
  circuitBreaker,
  createMessage,
  Message,
} from '../src/index';

// Simulated flaky agent that sometimes fails
let callCount = 0;
const flakyAgent = new LocalAgent(
  async (message: Message) => {
    callCount++;
    console.log(`  📞 Attempt ${callCount}: Processing "${message.content}"`);

    // Fail first 2 attempts, then succeed
    if (callCount < 3) {
      throw new Error('Service temporarily unavailable');
    }

    return createMessage('assistant', `Processed after ${callCount} attempts`);
  },
  { name: 'flaky-service' },
);

// Simulated slow agent
const slowAgent = new LocalAgent(
  async (message: Message) => {
    console.log('  ⏳ Processing (will take 5 seconds)...');
    await new Promise((resolve) => setTimeout(resolve, 5000));
    return createMessage('assistant', 'Finally done!');
  },
  { name: 'slow-service' },
);

async function main() {
  console.log('🎯 Agenkit Middleware Examples\n');

  // ==================================================================
  // Example 1: Retry Middleware
  // ==================================================================
  console.log('📚 Example 1: Retry Middleware');
  console.log('  Automatically retries failed requests with backoff\n');

  callCount = 0; // Reset counter
  const resilientAgent = retry(flakyAgent, {
    maxRetries: 3,
    initialDelay: 100,
    maxDelay: 1000,
    backoffMultiplier: 2,
  });

  try {
    const response = await resilientAgent.process(createMessage('user', 'Hello'));
    console.log(`  ✅ Success: ${response.content}\n`);
  } catch (error: any) {
    console.log(`  ❌ Failed: ${error.message}\n`);
  }

  // ==================================================================
  // Example 2: Timeout Middleware
  // ==================================================================
  console.log('📚 Example 2: Timeout Middleware');
  console.log('  Prevents requests from hanging indefinitely\n');

  const timedAgent = timeout(slowAgent, {
    timeout: 1000, // 1 second timeout
  });

  try {
    console.log('  Sending request with 1s timeout (agent takes 5s)...');
    await timedAgent.process(createMessage('user', 'Process this'));
  } catch (error: any) {
    console.log(`  ✅ Correctly timed out: ${error.message}\n`);
  }

  // ==================================================================
  // Example 3: Circuit Breaker Middleware
  // ==================================================================
  console.log('📚 Example 3: Circuit Breaker Middleware');
  console.log('  Fails fast when service is unhealthy\n');

  // Agent that always fails
  const brokenAgent = new LocalAgent(
    async () => {
      throw new Error('Service is down');
    },
    { name: 'broken-service' },
  );

  const protectedAgent = circuitBreaker(brokenAgent, {
    failureThreshold: 3,
    recoveryTimeout: 5000,
    successThreshold: 2,
  });

  // First 3 requests will fail and open the circuit
  for (let i = 1; i <= 5; i++) {
    try {
      await protectedAgent.process(createMessage('user', `Request ${i}`));
    } catch (error: any) {
      if (error.message.includes('Circuit breaker is OPEN')) {
        console.log(`  ⚡ Request ${i}: Circuit OPEN - Failing fast`);
      } else {
        console.log(`  ❌ Request ${i}: Service error`);
      }
    }
  }
  console.log('');

  // ==================================================================
  // Example 4: Combining Middleware (Layered Protection)
  // ==================================================================
  console.log('📚 Example 4: Combining Middleware');
  console.log('  Layer multiple middleware for defense in depth\n');

  callCount = 0;
  const fullyProtectedAgent = circuitBreaker(
    timeout(
      retry(flakyAgent, {
        maxRetries: 2,
        initialDelay: 50,
      }),
      {
        timeout: 2000,
      },
    ),
    {
      failureThreshold: 5,
      recoveryTimeout: 5000,
    },
  );

  console.log('  Middleware stack: Circuit Breaker → Timeout → Retry → Agent');
  console.log('  Processing request...');

  try {
    const response = await fullyProtectedAgent.process(createMessage('user', 'Protected request'));
    console.log(`  ✅ ${response.content}\n`);
  } catch (error: any) {
    console.log(`  ❌ Failed: ${error.message}\n`);
  }

  // ==================================================================
  // Summary
  // ==================================================================
  console.log('📝 Key Takeaways:');
  console.log('  • Retry: Handles transient failures (network blips, temporary errors)');
  console.log('  • Timeout: Prevents resource exhaustion from slow services');
  console.log('  • Circuit Breaker: Protects system from cascading failures');
  console.log('  • Combine them: Defense in depth for production systems');
  console.log('');
  console.log('✨ Production Tip: Always use middleware in production!');
  console.log('   The small overhead (<1ms) prevents catastrophic failures.');
}

main().catch(console.error);

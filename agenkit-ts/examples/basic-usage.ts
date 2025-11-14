/**
 * Basic usage example for agenkit TypeScript.
 *
 * Demonstrates core functionality:
 * - Creating local agents
 * - Processing messages
 * - Applying middleware
 * - Using HTTP transport
 */

import {
  LocalAgent,
  createMessage,
  applyMiddleware,
  retry,
  timeout,
  HTTPAgent,
} from '../src/index';

async function main() {
  console.log('🚀 Agenkit TypeScript - Basic Usage Examples\n');

  // Example 1: Simple local agent
  console.log('Example 1: Simple Local Agent');
  console.log('=' .repeat(50));

  const echoAgent = new LocalAgent({
    name: 'echo',
    process: async (message) => {
      console.log(`  Received: ${message.content}`);
      return createMessage('assistant', `Echo: ${message.content}`);
    },
  });

  const response1 = await echoAgent.process(createMessage('user', 'Hello, agent!'));
  console.log(`  Response: ${response1.content}\n`);

  // Example 2: Agent with state
  console.log('Example 2: Stateful Agent (Counter)');
  console.log('=' .repeat(50));

  let count = 0;
  const counterAgent = new LocalAgent({
    name: 'counter',
    process: async (message) => {
      count++;
      return createMessage('assistant', `Message #${count}: ${message.content}`, {
        count,
      });
    },
  });

  for (let i = 1; i <= 3; i++) {
    const response = await counterAgent.process(createMessage('user', `Message ${i}`));
    console.log(`  ${response.content}`);
  }
  console.log();

  // Example 3: Middleware - Retry
  console.log('Example 3: Retry Middleware');
  console.log('=' .repeat(50));

  let attempts = 0;
  const flakyAgent = new LocalAgent({
    name: 'flaky',
    process: async (message) => {
      attempts++;
      console.log(`  Attempt ${attempts}`);

      if (attempts < 3) {
        throw new Error('Network error');
      }

      return createMessage('assistant', 'Success!');
    },
  });

  const retriedAgent = applyMiddleware(flakyAgent, [
    retry({ maxAttempts: 3, initialDelay: 100 }),
  ]);

  try {
    const response = await retriedAgent.process(createMessage('user', 'Hello'));
    console.log(`  Final response: ${response.content}\n`);
  } catch (error) {
    console.log(`  Failed: ${(error as Error).message}\n`);
  }

  // Example 4: Middleware - Timeout
  console.log('Example 4: Timeout Middleware');
  console.log('=' .repeat(50));

  const slowAgent = new LocalAgent({
    name: 'slow',
    process: async (message) => {
      console.log('  Processing (will take 2 seconds)...');
      await new Promise((resolve) => setTimeout(resolve, 2000));
      return createMessage('assistant', 'Done!');
    },
  });

  const timedAgent = applyMiddleware(slowAgent, [timeout({ timeout: 1000 })]);

  try {
    await timedAgent.process(createMessage('user', 'Hello'));
  } catch (error) {
    console.log(`  Timeout error (expected): ${(error as Error).message}\n`);
  }

  // Example 5: Combined middleware
  console.log('Example 5: Combined Middleware (Retry + Timeout)');
  console.log('=' .repeat(50));

  attempts = 0;
  const unreliableAgent = new LocalAgent({
    name: 'unreliable',
    process: async (message) => {
      attempts++;
      console.log(`  Attempt ${attempts}`);

      // Simulate network flakiness
      if (attempts === 1) {
        throw new Error('Network timeout');
      }

      await new Promise((resolve) => setTimeout(resolve, 100));
      return createMessage('assistant', 'Success after retry!');
    },
  });

  const robustAgent = applyMiddleware(unreliableAgent, [
    retry({ maxAttempts: 3, initialDelay: 50 }),
    timeout({ timeout: 5000 }),
  ]);

  const response5 = await robustAgent.process(createMessage('user', 'Hello'));
  console.log(`  Final response: ${response5.content}\n`);

  console.log('✅ All examples completed!');
}

// Run examples
main().catch(console.error);

/**
 * Basic OpenAI GPT example
 *
 * Demonstrates:
 * - OpenAI adapter configuration
 * - Single-turn completion
 * - Multi-turn conversation
 * - Streaming responses
 * - Token usage tracking
 *
 * Setup:
 *   export OPENAI_API_KEY=your-key
 *   npm run build
 *   node dist/examples/openai-basic.js
 */

import { OpenAIAdapter } from '../src/adapters/openai';
import { createMessage } from '../src/core/interfaces';

async function main() {
  console.log('='.repeat(60));
  console.log('AgentKit TypeScript - OpenAI Basic Example');
  console.log('='.repeat(60));
  console.log();

  // Check for API key
  if (!process.env.OPENAI_API_KEY) {
    console.error('❌ OPENAI_API_KEY environment variable not set');
    console.error('');
    console.error('Please set your API key:');
    console.error('  export OPENAI_API_KEY=your-key-here');
    console.error('');
    process.exit(1);
  }

  // Create OpenAI adapter
  const adapter = new OpenAIAdapter({
    model: 'gpt-4-turbo',
    temperature: 0.7,
    maxTokens: 1024,
  });

  console.log(`✓ Initialized ${adapter.name()}`);
  console.log(`✓ Capabilities: ${adapter.capabilities().join(', ')}`);
  console.log();

  // Example 1: Simple completion
  console.log('-'.repeat(60));
  console.log('Example 1: Simple Completion');
  console.log('-'.repeat(60));
  console.log();

  const message1 = createMessage({
    role: 'user',
    content: 'What is 2 + 2?',
  });

  console.log(`User: ${message1.content}`);
  console.log();

  const response1 = await adapter.process(message1);
  console.log(`Assistant: ${response1.content}`);
  console.log();
  console.log(`Metadata:`);
  console.log(`  Model: ${response1.metadata?.model}`);
  console.log(`  Tokens: ${JSON.stringify(response1.metadata?.usage)}`);
  console.log(`  Finish reason: ${response1.metadata?.finish_reason}`);
  console.log();

  // Example 2: Multi-turn conversation
  console.log('-'.repeat(60));
  console.log('Example 2: Multi-Turn Conversation');
  console.log('-'.repeat(60));
  console.log();

  const conversation = [
    createMessage({ role: 'system', content: 'You are a helpful math tutor.' }),
    createMessage({ role: 'user', content: 'What is the Pythagorean theorem?' }),
  ];

  console.log('System: You are a helpful math tutor.');
  console.log('User: What is the Pythagorean theorem?');
  console.log();

  const response2 = await adapter.complete(conversation);
  console.log(`Assistant: ${response2.content}`);
  console.log();
  console.log(`Tokens used: ${response2.metadata?.usage?.total_tokens}`);
  console.log();

  // Example 3: Streaming response
  console.log('-'.repeat(60));
  console.log('Example 3: Streaming Response');
  console.log('-'.repeat(60));
  console.log();

  const message3 = createMessage({
    role: 'user',
    content: 'Write a haiku about TypeScript.',
  });

  console.log(`User: ${message3.content}`);
  console.log();
  console.log('Assistant (streaming): ');

  let fullResponse = '';
  for await (const chunk of adapter.processStream(message3)) {
    process.stdout.write(chunk.content as string);
    fullResponse += chunk.content;
  }

  console.log();
  console.log();
  console.log(`Full response length: ${fullResponse.length} characters`);
  console.log();

  // Example 4: Different models
  console.log('-'.repeat(60));
  console.log('Example 4: Using GPT-3.5 Turbo (faster, cheaper)');
  console.log('-'.repeat(60));
  console.log();

  const fastAdapter = new OpenAIAdapter({
    model: 'gpt-3.5-turbo',
    temperature: 0.5,
    maxTokens: 100,
  });

  const message4 = createMessage({
    role: 'user',
    content: 'Explain quantum computing in one sentence.',
  });

  console.log(`User: ${message4.content}`);
  console.log();

  const response4 = await fastAdapter.process(message4);
  console.log(`Assistant (${fastAdapter.name()}): ${response4.content}`);
  console.log();
  console.log(`Cost comparison:`);
  console.log(`  GPT-4 Turbo: ~$0.01 / 1K tokens (input), ~$0.03 / 1K tokens (output)`);
  console.log(`  GPT-3.5 Turbo: ~$0.0005 / 1K tokens (input), ~$0.0015 / 1K tokens (output)`);
  console.log();

  console.log('-'.repeat(60));
  console.log('✓ All examples completed successfully!');
  console.log('-'.repeat(60));
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});

/**
 * Basic Anthropic Claude example
 *
 * Demonstrates:
 * - Anthropic adapter configuration
 * - Single-turn completion with Claude
 * - Multi-turn conversation
 * - Streaming responses
 * - System message handling
 *
 * Setup:
 *   export ANTHROPIC_API_KEY=your-key
 *   npm run build
 *   node dist/examples/anthropic-basic.js
 */

import { AnthropicAdapter } from '../src/adapters/anthropic';
import { createMessage } from '../src/core/interfaces';

async function main() {
  console.log('='.repeat(60));
  console.log('AgentKit TypeScript - Anthropic Claude Example');
  console.log('='.repeat(60));
  console.log();

  // Check for API key
  if (!process.env.ANTHROPIC_API_KEY) {
    console.error('❌ ANTHROPIC_API_KEY environment variable not set');
    console.error('');
    console.error('Please set your API key:');
    console.error('  export ANTHROPIC_API_KEY=your-key-here');
    console.error('');
    process.exit(1);
  }

  // Create Anthropic adapter
  const adapter = new AnthropicAdapter({
    model: 'claude-3-5-sonnet-20241022',
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
    content: 'Explain the concept of recursion in programming.',
  });

  console.log(`User: ${message1.content}`);
  console.log();

  const response1 = await adapter.process(message1);
  console.log(`Claude: ${response1.content}`);
  console.log();
  console.log(`Metadata:`);
  console.log(`  Model: ${response1.metadata?.model}`);
  console.log(`  Tokens: ${JSON.stringify(response1.metadata?.usage)}`);
  console.log(`  Stop reason: ${response1.metadata?.stop_reason}`);
  console.log();

  // Example 2: With system message
  console.log('-'.repeat(60));
  console.log('Example 2: Conversation with System Message');
  console.log('-'.repeat(60));
  console.log();

  const conversation = [
    createMessage({
      role: 'system',
      content: 'You are a creative writing assistant who speaks in haikus.',
    }),
    createMessage({
      role: 'user',
      content: 'Describe a sunset.',
    }),
  ];

  console.log('System: You are a creative writing assistant who speaks in haikus.');
  console.log('User: Describe a sunset.');
  console.log();

  const response2 = await adapter.complete(conversation);
  console.log(`Claude: ${response2.content}`);
  console.log();
  console.log(`Input tokens: ${response2.metadata?.usage?.prompt_tokens}`);
  console.log(`Output tokens: ${response2.metadata?.usage?.completion_tokens}`);
  console.log();

  // Example 3: Streaming response
  console.log('-'.repeat(60));
  console.log('Example 3: Streaming Response');
  console.log('-'.repeat(60));
  console.log();

  const message3 = createMessage({
    role: 'user',
    content: 'Write a short poem about artificial intelligence.',
  });

  console.log(`User: ${message3.content}`);
  console.log();
  console.log('Claude (streaming): ');

  let fullResponse = '';
  for await (const chunk of adapter.processStream(message3)) {
    process.stdout.write(chunk.content as string);
    fullResponse += chunk.content;
  }

  console.log();
  console.log();
  console.log(`Full response length: ${fullResponse.length} characters`);
  console.log();

  // Example 4: Model comparison
  console.log('-'.repeat(60));
  console.log('Example 4: Using Claude 3 Haiku (faster, cheaper)');
  console.log('-'.repeat(60));
  console.log();

  const haikuAdapter = new AnthropicAdapter({
    model: 'claude-3-haiku-20240307',
    temperature: 0.7,
    maxTokens: 200,
  });

  const message4 = createMessage({
    role: 'user',
    content: 'What is machine learning in one paragraph?',
  });

  console.log(`User: ${message4.content}`);
  console.log();

  const response4 = await haikuAdapter.process(message4);
  console.log(`Claude Haiku: ${response4.content}`);
  console.log();
  console.log(`Model comparison:`);
  console.log(`  Claude 3.5 Sonnet: Most capable, balanced performance`);
  console.log(`  Claude 3 Opus: Highest capability, slower`);
  console.log(`  Claude 3 Haiku: Fastest, most cost-effective`);
  console.log();

  // Example 5: Multi-turn dialogue
  console.log('-'.repeat(60));
  console.log('Example 5: Multi-Turn Dialogue');
  console.log('-'.repeat(60));
  console.log();

  const dialogue = [
    createMessage({ role: 'user', content: 'What is TypeScript?' }),
  ];

  console.log('User: What is TypeScript?');

  const turn1 = await adapter.complete(dialogue);
  console.log(`Claude: ${turn1.content}`);
  console.log();

  // Add assistant's response to dialogue
  dialogue.push(createMessage({ role: 'assistant', content: turn1.content as string }));
  dialogue.push(createMessage({ role: 'user', content: 'What are its main benefits?' }));

  console.log('User: What are its main benefits?');

  const turn2 = await adapter.complete(dialogue);
  console.log(`Claude: ${turn2.content}`);
  console.log();

  console.log(`Total tokens in conversation: ${turn2.metadata?.usage?.total_tokens}`);
  console.log();

  console.log('-'.repeat(60));
  console.log('✓ All examples completed successfully!');
  console.log('-'.repeat(60));
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});

/**
 * Basic Google Gemini example
 *
 * Demonstrates:
 * - Gemini adapter configuration
 * - Single-turn completion with Gemini
 * - Multi-turn conversation
 * - Streaming responses
 * - System message handling
 *
 * Setup:
 *   export GEMINI_API_KEY=your-key (or GOOGLE_API_KEY)
 *   npm run build
 *   node dist/examples/gemini-basic.js
 */

import { GeminiAdapter } from '../src/adapters/gemini';
import { createMessage } from '../src/core/interfaces';

async function main() {
  console.log('='.repeat(60));
  console.log('AgentKit TypeScript - Google Gemini Example');
  console.log('='.repeat(60));
  console.log();

  // Check for API key
  if (!process.env.GEMINI_API_KEY && !process.env.GOOGLE_API_KEY) {
    console.error('❌ GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set');
    console.error('');
    console.error('Please set your API key:');
    console.error('  export GEMINI_API_KEY=your-key-here');
    console.error('');
    console.error('Get your API key from: https://makersuite.google.com/app/apikey');
    console.error('');
    process.exit(1);
  }

  // Create Gemini adapter
  const adapter = new GeminiAdapter({
    model: 'gemini-2.0-flash-exp',
    temperature: 0.7,
    maxTokens: 1024,
  });

  console.log(`✓ Initialized ${adapter.name}`);
  console.log(`✓ Capabilities: ${adapter.capabilities.join(', ')}`);
  console.log();

  // Example 1: Simple completion
  console.log('-'.repeat(60));
  console.log('Example 1: Simple Completion');
  console.log('-'.repeat(60));
  console.log();

  const message1 = createMessage({
    role: 'user',
    content: 'Explain the concept of neural networks in one paragraph.',
  });

  console.log(`User: ${message1.content}`);
  console.log();

  const response1 = await adapter.process(message1);
  console.log(`Gemini: ${response1.content}`);
  console.log();
  console.log('Metadata:');
  console.log(`  Model: ${response1.metadata?.model}`);
  console.log(`  Tokens: ${JSON.stringify(response1.metadata?.usage)}`);
  console.log(`  Finish reason: ${response1.metadata?.finish_reason}`);
  console.log();

  // Example 2: With system message
  console.log('-'.repeat(60));
  console.log('Example 2: Conversation with System Message');
  console.log('-'.repeat(60));
  console.log();

  const conversation = [
    createMessage({
      role: 'system',
      content: 'You are a creative storyteller who explains complex topics through analogies.',
    }),
    createMessage({
      role: 'user',
      content: 'How does machine learning work?',
    }),
  ];

  console.log('System: You are a creative storyteller who explains complex topics through analogies.');
  console.log('User: How does machine learning work?');
  console.log();

  const response2 = await adapter.complete(conversation);
  console.log(`Gemini: ${response2.content}`);
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
  console.log('Gemini (streaming): ');

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
  console.log('Example 4: Using Gemini 1.5 Pro (more capable)');
  console.log('-'.repeat(60));
  console.log();

  const proAdapter = new GeminiAdapter({
    model: 'gemini-1.5-pro',
    temperature: 0.7,
    maxTokens: 200,
  });

  const message4 = createMessage({
    role: 'user',
    content: 'What are the key differences between supervised and unsupervised learning?',
  });

  console.log(`User: ${message4.content}`);
  console.log();

  const response4 = await proAdapter.process(message4);
  console.log(`Gemini Pro: ${response4.content}`);
  console.log();
  console.log('Model comparison:');
  console.log('  gemini-2.0-flash-exp: Fastest, experimental features');
  console.log('  gemini-1.5-pro: Most capable, best for complex tasks');
  console.log('  gemini-1.5-flash: Fast and cost-effective');
  console.log();

  // Example 5: Multi-turn dialogue
  console.log('-'.repeat(60));
  console.log('Example 5: Multi-Turn Dialogue');
  console.log('-'.repeat(60));
  console.log();

  const dialogue = [
    createMessage({ role: 'user', content: 'What is deep learning?' }),
  ];

  console.log('User: What is deep learning?');

  const turn1 = await adapter.complete(dialogue);
  console.log(`Gemini: ${turn1.content}`);
  console.log();

  dialogue.push(createMessage({ role: 'assistant', content: turn1.content as string }));
  dialogue.push(createMessage({ role: 'user', content: 'What are some popular deep learning frameworks?' }));

  console.log('User: What are some popular deep learning frameworks?');

  const turn2 = await adapter.complete(dialogue);
  console.log(`Gemini: ${turn2.content}`);
  console.log();

  console.log(`Total tokens in conversation: ${turn2.metadata?.usage?.total_tokens}`);
  console.log();

  // Example 6: Advanced configuration
  console.log('-'.repeat(60));
  console.log('Example 6: Advanced Configuration');
  console.log('-'.repeat(60));
  console.log();

  const advancedAdapter = new GeminiAdapter({
    model: 'gemini-2.0-flash-exp',
    temperature: 0.9,
    maxTokens: 150,
    topP: 0.95,
    topK: 40,
    stopSequences: ['END'],
  });

  const message6 = createMessage({
    role: 'user',
    content: 'Tell me a creative story about robots.',
  });

  console.log(`User: ${message6.content}`);
  console.log();

  const response6 = await advancedAdapter.process(message6);
  console.log(`Gemini (creative): ${response6.content}`);
  console.log();
  console.log('Configuration used:');
  console.log('  Temperature: 0.9 (more creative)');
  console.log('  Top-P: 0.95 (nucleus sampling)');
  console.log('  Top-K: 40 (consider top 40 tokens)');
  console.log();

  console.log('-'.repeat(60));
  console.log('✓ All examples completed successfully!');
  console.log('-'.repeat(60));
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});

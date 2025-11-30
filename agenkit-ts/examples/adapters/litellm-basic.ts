/**
 * Basic LiteLLM example
 *
 * Demonstrates:
 * - LiteLLM adapter configuration
 * - Single-turn completion via LiteLLM proxy
 * - Multi-turn conversation
 * - Streaming responses
 * - Multiple provider support
 *
 * Setup:
 *   1. Install and run LiteLLM proxy:
 *      pip install litellm
 *      litellm --model gpt-3.5-turbo
 *   2. Or use Docker:
 *      docker run -p 4000:4000 ghcr.io/berriai/litellm:latest
 *   3. Run this example:
 *      npm run build
 *      node dist/examples/litellm-basic.js
 */

import { LiteLLMAdapter } from '../src/adapters/litellm';
import { createMessage } from '../src/core/interfaces';

async function main() {
  console.log('='.repeat(60));
  console.log('AgentKit TypeScript - LiteLLM Example');
  console.log('='.repeat(60));
  console.log();

  console.log('Make sure LiteLLM proxy is running:');
  console.log('  litellm --model gpt-3.5-turbo');
  console.log('  or');
  console.log('  docker run -p 4000:4000 ghcr.io/berriai/litellm:latest');
  console.log();

  // Create LiteLLM adapter
  const adapter = new LiteLLMAdapter({
    baseUrl: 'http://localhost:4000',
    model: 'gpt-3.5-turbo',
    temperature: 0.7,
    maxTokens: 1024,
  });

  console.log(`✓ Initialized ${adapter.name}`);
  console.log(`✓ Capabilities: ${adapter.capabilities.join(', ')}`);
  console.log(`✓ Proxy: http://localhost:4000`);
  console.log();

  // Example 1: Simple completion
  console.log('-'.repeat(60));
  console.log('Example 1: Simple Completion');
  console.log('-'.repeat(60));
  console.log();

  const message1 = createMessage({
    role: 'user',
    content: 'Explain the concept of a universal LLM gateway in one paragraph.',
  });

  console.log(`User: ${message1.content}`);
  console.log();

  try {
    const response1 = await adapter.process(message1);
    console.log(`LiteLLM: ${response1.content}`);
    console.log();
    console.log('Metadata:');
    console.log(`  Model: ${response1.metadata?.model}`);
    console.log(`  Tokens: ${JSON.stringify(response1.metadata?.usage)}`);
    console.log(`  Finish reason: ${response1.metadata?.finish_reason}`);
    console.log();
  } catch (error) {
    console.error(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    console.error('Make sure LiteLLM proxy is running on http://localhost:4000');
    process.exit(1);
  }

  // Example 2: With system message
  console.log('-'.repeat(60));
  console.log('Example 2: Conversation with System Message');
  console.log('-'.repeat(60));
  console.log();

  const conversation = [
    createMessage({
      role: 'system',
      content: 'You are a helpful assistant that explains technical concepts clearly.',
    }),
    createMessage({
      role: 'user',
      content: 'What is LiteLLM?',
    }),
  ];

  console.log('System: You are a helpful assistant that explains technical concepts clearly.');
  console.log('User: What is LiteLLM?');
  console.log();

  const response2 = await adapter.complete(conversation);
  console.log(`LiteLLM: ${response2.content}`);
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
    content: 'List the top 5 benefits of using a universal LLM gateway.',
  });

  console.log(`User: ${message3.content}`);
  console.log();
  console.log('LiteLLM (streaming): ');

  let fullResponse = '';
  for await (const chunk of adapter.processStream(message3)) {
    process.stdout.write(chunk.content as string);
    fullResponse += chunk.content;
  }

  console.log();
  console.log();
  console.log(`Full response length: ${fullResponse.length} characters`);
  console.log();

  // Example 4: Different models through LiteLLM
  console.log('-'.repeat(60));
  console.log('Example 4: Using Different Providers');
  console.log('-'.repeat(60));
  console.log();

  console.log('LiteLLM supports 100+ providers:');
  console.log('  OpenAI: gpt-4, gpt-3.5-turbo');
  console.log('  Anthropic: claude-3-5-sonnet-20241022');
  console.log('  AWS Bedrock: bedrock/anthropic.claude-v2');
  console.log('  Google Gemini: gemini/gemini-pro');
  console.log('  Azure OpenAI: azure/gpt-4');
  console.log('  Local Ollama: ollama/llama2');
  console.log();

  // Example with GPT-4 (if available)
  console.log('Switching to GPT-4 (if configured in LiteLLM):');
  const gpt4Adapter = new LiteLLMAdapter({
    baseUrl: 'http://localhost:4000',
    model: 'gpt-4',
    temperature: 0.7,
    maxTokens: 200,
  });

  const message4 = createMessage({
    role: 'user',
    content: 'What are microservices in one sentence?',
  });

  console.log(`User: ${message4.content}`);
  console.log();

  try {
    const response4 = await gpt4Adapter.process(message4);
    console.log(`GPT-4 (via LiteLLM): ${response4.content}`);
    console.log();
  } catch (error) {
    console.log('Note: GPT-4 model not configured in LiteLLM proxy');
    console.log();
  }

  // Example 5: Multi-turn dialogue
  console.log('-'.repeat(60));
  console.log('Example 5: Multi-Turn Dialogue');
  console.log('-'.repeat(60));
  console.log();

  const dialogue = [
    createMessage({ role: 'user', content: 'What is API rate limiting?' }),
  ];

  console.log('User: What is API rate limiting?');

  const turn1 = await adapter.complete(dialogue);
  console.log(`LiteLLM: ${turn1.content}`);
  console.log();

  dialogue.push(createMessage({ role: 'assistant', content: turn1.content as string }));
  dialogue.push(createMessage({ role: 'user', content: 'How does LiteLLM help with rate limiting?' }));

  console.log('User: How does LiteLLM help with rate limiting?');

  const turn2 = await adapter.complete(dialogue);
  console.log(`LiteLLM: ${turn2.content}`);
  console.log();

  console.log(`Total tokens in conversation: ${turn2.metadata?.usage?.total_tokens}`);
  console.log();

  // Example 6: With authentication
  console.log('-'.repeat(60));
  console.log('Example 6: Authenticated LiteLLM Proxy');
  console.log('-'.repeat(60));
  console.log();

  console.log('For production deployments, use API key authentication:');
  console.log();
  console.log('const secureAdapter = new LiteLLMAdapter({');
  console.log('  baseUrl: "https://your-litellm-proxy.com",');
  console.log('  model: "gpt-4",');
  console.log('  apiKey: process.env.LITELLM_API_KEY,');
  console.log('});');
  console.log();

  // Example 7: Error handling
  console.log('-'.repeat(60));
  console.log('Example 7: Error Handling');
  console.log('-'.repeat(60));
  console.log();

  const invalidAdapter = new LiteLLMAdapter({
    baseUrl: 'http://localhost:4000',
    model: 'non-existent-model',
  });

  try {
    await invalidAdapter.process(createMessage({
      role: 'user',
      content: 'Test',
    }));
  } catch (error) {
    console.log('Caught expected error:');
    console.log(`  ${error instanceof Error ? error.message : 'Unknown error'}`);
    console.log();
    console.log('LiteLLM adapter properly handles:');
    console.log('  - Invalid model names');
    console.log('  - Network errors');
    console.log('  - Timeout errors');
    console.log('  - API authentication errors');
    console.log();
  }

  console.log('-'.repeat(60));
  console.log('✓ All examples completed successfully!');
  console.log('-'.repeat(60));
  console.log();
  console.log('Next steps:');
  console.log('  1. Configure LiteLLM with your preferred providers');
  console.log('  2. Set up load balancing across multiple models');
  console.log('  3. Enable caching for cost optimization');
  console.log('  4. Monitor usage with LiteLLM dashboard');
}

main().catch((error) => {
  console.error('Error:', error.message);
  console.error('');
  console.error('Make sure LiteLLM proxy is running:');
  console.error('  pip install litellm');
  console.error('  litellm --model gpt-3.5-turbo');
  console.error('');
  process.exit(1);
});

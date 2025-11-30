/**
 * Basic Amazon Bedrock example
 *
 * Demonstrates:
 * - Bedrock adapter configuration
 * - Single-turn completion with Claude on Bedrock
 * - Multi-turn conversation
 * - Streaming responses
 * - AWS credential handling
 *
 * Setup:
 *   Configure AWS credentials (use IAM role, profile, or environment variables):
 *     export AWS_ACCESS_KEY_ID=your-key
 *     export AWS_SECRET_ACCESS_KEY=your-secret
 *     export AWS_REGION=us-east-1
 *   npm run build
 *   node dist/examples/bedrock-basic.js
 */

import { BedrockAdapter } from '../src/adapters/bedrock';
import { createMessage } from '../src/core/interfaces';

async function main() {
  console.log('='.repeat(60));
  console.log('AgentKit TypeScript - Amazon Bedrock Example');
  console.log('='.repeat(60));
  console.log();

  // Create Bedrock adapter
  const adapter = new BedrockAdapter({
    region: process.env.AWS_REGION || 'us-east-1',
    modelId: 'anthropic.claude-3-5-sonnet-20241022-v2:0',
    temperature: 0.7,
    maxTokens: 1024,
  });

  console.log(`✓ Initialized ${adapter.name}`);
  console.log(`✓ Capabilities: ${adapter.capabilities.join(', ')}`);
  console.log(`✓ Region: ${process.env.AWS_REGION || 'us-east-1'}`);
  console.log();

  // Example 1: Simple completion
  console.log('-'.repeat(60));
  console.log('Example 1: Simple Completion');
  console.log('-'.repeat(60));
  console.log();

  const message1 = createMessage({
    role: 'user',
    content: 'Explain the concept of cloud computing in one paragraph.',
  });

  console.log(`User: ${message1.content}`);
  console.log();

  const response1 = await adapter.process(message1);
  console.log(`Claude (Bedrock): ${response1.content}`);
  console.log();
  console.log('Metadata:');
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
      content: 'You are a helpful AWS expert who explains cloud services clearly.',
    }),
    createMessage({
      role: 'user',
      content: 'What is Amazon Bedrock?',
    }),
  ];

  console.log('System: You are a helpful AWS expert who explains cloud services clearly.');
  console.log('User: What is Amazon Bedrock?');
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
    content: 'List the top 5 benefits of using Amazon Bedrock.',
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

  // Example 4: Different Bedrock models
  console.log('-'.repeat(60));
  console.log('Example 4: Using Claude 3 Haiku (faster, cheaper)');
  console.log('-'.repeat(60));
  console.log();

  const haikuAdapter = new BedrockAdapter({
    region: process.env.AWS_REGION || 'us-east-1',
    modelId: 'anthropic.claude-3-haiku-20240307-v1:0',
    temperature: 0.7,
    maxTokens: 200,
  });

  const message4 = createMessage({
    role: 'user',
    content: 'What is serverless computing in one sentence?',
  });

  console.log(`User: ${message4.content}`);
  console.log();

  const response4 = await haikuAdapter.process(message4);
  console.log(`Claude Haiku: ${response4.content}`);
  console.log();
  console.log('Available Bedrock models:');
  console.log('  anthropic.claude-3-5-sonnet-20241022-v2:0 - Most capable');
  console.log('  anthropic.claude-3-haiku-20240307-v1:0 - Fast and cost-effective');
  console.log('  meta.llama3-70b-instruct-v1:0 - Llama 3 70B');
  console.log('  mistral.mistral-large-2402-v1:0 - Mistral Large');
  console.log('  amazon.titan-text-premier-v1:0 - Amazon Titan');
  console.log();

  // Example 5: Multi-turn dialogue
  console.log('-'.repeat(60));
  console.log('Example 5: Multi-Turn Dialogue');
  console.log('-'.repeat(60));
  console.log();

  const dialogue = [
    createMessage({ role: 'user', content: 'What is Amazon S3?' }),
  ];

  console.log('User: What is Amazon S3?');

  const turn1 = await adapter.complete(dialogue);
  console.log(`Claude: ${turn1.content}`);
  console.log();

  dialogue.push(createMessage({ role: 'assistant', content: turn1.content as string }));
  dialogue.push(createMessage({ role: 'user', content: 'What are some common use cases?' }));

  console.log('User: What are some common use cases?');

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
  console.error('');
  console.error('Make sure you have AWS credentials configured:');
  console.error('  - IAM role (for EC2/ECS/EKS)');
  console.error('  - AWS profile (~/.aws/credentials)');
  console.error('  - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)');
  console.error('');
  process.exit(1);
});

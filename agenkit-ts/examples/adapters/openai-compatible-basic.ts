/**
 * OpenAI-Compatible LLM Adapter Examples
 *
 * This example demonstrates using Agenkit with OpenAI-compatible inference
 * services like vLLM, llama.cpp, SGLang, and TensorRT-LLM.
 *
 * Setup Instructions:
 *
 * 1. vLLM (recommended for production):
 *    docker run --gpus all -p 8000:8000 vllm/vllm-openai \
 *      --model meta-llama/Llama-2-7b-chat-hf
 *
 * 2. llama.cpp (lightweight, CPU-friendly):
 *    git clone https://github.com/ggerganov/llama.cpp
 *    cd llama.cpp && make
 *    ./server -m models/llama-2-7b-chat.gguf -c 2048 --port 8080
 *
 * 3. SGLang (optimized for complex prompts):
 *    pip install sglang
 *    python -m sglang.launch_server \
 *      --model-path meta-llama/Llama-2-7b-chat-hf --port 30000
 *
 * Benefits:
 * - Run LLMs locally (no cloud API costs)
 * - Keep data private (on-premises)
 * - Same code works with all services
 * - Easy migration between providers
 */

import { OpenAICompatibleAgent, createMessage } from '../../src/index.js';

// Helper functions for formatting
function printSeparator(title: string = ''): void {
  console.log('\n' + '='.repeat(80));
  if (title) {
    console.log(title);
    console.log('='.repeat(80));
  }
}

function printSubheading(text: string): void {
  console.log(`\n${text}`);
  console.log('-'.repeat(text.length));
}

/**
 * Example 1: vLLM Local Deployment
 *
 * vLLM is the most popular choice for high-throughput inference.
 */
async function vllmExample(): Promise<void> {
  printSeparator('Example 1: vLLM Local Deployment');

  console.log('\nSetup:');
  console.log('  docker run --gpus all -p 8000:8000 vllm/vllm-openai \\');
  console.log('    --model meta-llama/Llama-2-7b-chat-hf');
  console.log();

  // Create vLLM adapter
  const agent = new OpenAICompatibleAgent({
    baseURL: 'http://localhost:8000/v1',
    model: 'meta-llama/Llama-2-7b-chat-hf',
    provider: 'vllm',
  });

  console.log(`✓ Connected to vLLM service`);
  console.log(`  Provider: ${agent.name}`);
  console.log(`  Capabilities: ${agent.capabilities.join(', ')}`);
  console.log();

  const message = createMessage('user', 'What is machine learning in one sentence?');
  console.log(`📤 User: ${message.content}`);

  try {
    const response = await agent.process(message);
    console.log(`📥 Assistant: ${response.content}`);

    // Print metadata
    if (response.metadata?.provider) {
      console.log('\n📊 Metadata:');
      console.log(`  Provider: ${response.metadata.provider}`);
      console.log(`  Base URL: ${response.metadata.baseURL}`);
      console.log(`  Model: ${response.metadata.model}`);
      if (response.metadata.usage) {
        const usage = response.metadata.usage as Record<string, unknown>;
        console.log(`  Tokens: ${usage.total_tokens}`);
      }
    }
  } catch (error) {
    console.log(`❌ Error (service may not be running): ${error}`);
    console.log('   Make sure vLLM is running on http://localhost:8000');
  }
}

/**
 * Example 2: llama.cpp Server
 *
 * llama.cpp is lightweight and CPU-friendly, perfect for development.
 */
async function llamacppExample(): Promise<void> {
  printSeparator('Example 2: llama.cpp Server');

  console.log('\nSetup:');
  console.log('  ./llama.cpp/server -m models/llama-2-7b-chat.gguf \\');
  console.log('    -c 2048 --port 8080');
  console.log();

  // Create llama.cpp adapter
  const agent = new OpenAICompatibleAgent({
    baseURL: 'http://localhost:8080/v1',
    model: 'llama-2-7b-chat',
    provider: 'llamacpp',
    temperature: 0.7,
    maxTokens: 100,
  });

  console.log(`✓ Connected to llama.cpp server`);
  console.log(`  Provider: ${agent.name}`);
  console.log();

  const message = createMessage('user', 'Write a haiku about coding.');
  console.log(`📤 User: ${message.content}`);

  try {
    const response = await agent.process(message);
    console.log(`📥 Assistant:\n${response.content}`);
  } catch (error) {
    console.log(`❌ Error (service may not be running): ${error}`);
    console.log('   Make sure llama.cpp is running on http://localhost:8080');
  }
}

/**
 * Example 3: Streaming Response
 *
 * Stream responses in real-time for better user experience.
 */
async function streamingExample(): Promise<void> {
  printSeparator('Example 3: Streaming Response');

  console.log('\nThis example streams responses in real-time from vLLM.\n');

  // Create adapter
  const agent = new OpenAICompatibleAgent({
    baseURL: 'http://localhost:8000/v1',
    model: 'meta-llama/Llama-2-7b-chat-hf',
    provider: 'vllm',
  });

  const message = createMessage('user', 'Count from 1 to 10 slowly.');
  console.log(`📤 User: ${message.content}`);
  process.stdout.write('📥 Assistant (streaming): ');

  try {
    for await (const chunk of agent.processStream(message)) {
      process.stdout.write(chunk.content as string);
    }
    console.log();
  } catch (error) {
    console.log(`\n❌ Error (service may not be running): ${error}`);
    console.log('   Make sure vLLM is running on http://localhost:8000');
  }
}

/**
 * Example 4: Multi-Service Comparison
 *
 * Demonstrates how the same code works with different services.
 */
async function multiServiceExample(): Promise<void> {
  printSeparator('Example 4: Multi-Service Comparison');

  console.log('\nThis example shows how the same code works with different services.\n');

  const services = [
    {
      name: 'vLLM',
      baseURL: 'http://localhost:8000/v1',
      model: 'meta-llama/Llama-2-7b-chat-hf',
      provider: 'vllm',
    },
    {
      name: 'llama.cpp',
      baseURL: 'http://localhost:8080/v1',
      model: 'llama-2-7b-chat',
      provider: 'llamacpp',
    },
    {
      name: 'SGLang',
      baseURL: 'http://localhost:30000/v1',
      model: 'meta-llama/Llama-2-7b-chat-hf',
      provider: 'sglang',
    },
  ];

  const message = createMessage('user', 'What is a GPU in one sentence?');

  for (const svc of services) {
    console.log(`Testing ${svc.name}...`);

    const agent = new OpenAICompatibleAgent({
      baseURL: svc.baseURL,
      model: svc.model,
      provider: svc.provider,
      maxTokens: 100,
    });

    try {
      const response = await agent.process(message);
      console.log(`  ✅ ${svc.name} responded:`);
      const content = response.content as string;
      console.log(`     ${content.substring(0, 80)}${content.length > 80 ? '...' : ''}`);
      if (response.metadata?.provider) {
        console.log(`     Provider: ${response.metadata.provider}`);
      }
      console.log();
    } catch (error) {
      console.log(`  ❌ ${svc.name} not available: ${error}\n`);
    }
  }

  console.log('💡 Key Point: The same Agenkit code works with all services!');
}

/**
 * Example 5: Conversation with Context
 *
 * Demonstrates maintaining conversation context across multiple turns.
 */
async function conversationExample(): Promise<void> {
  printSeparator('Example 5: Conversation with Context');

  const agent = new OpenAICompatibleAgent({
    baseURL: 'http://localhost:8000/v1',
    model: 'meta-llama/Llama-2-7b-chat-hf',
    provider: 'vllm',
    temperature: 0.7,
  });

  console.log('\nMulti-turn conversation:\n');

  const turns = [
    'Hi! My name is Alice.',
    'What is my name?',
    'Tell me a short joke about my name.',
  ];

  try {
    for (const userInput of turns) {
      const message = createMessage('user', userInput);
      console.log(`👤 User: ${userInput}`);

      const response = await agent.process(message);
      console.log(`🤖 Assistant: ${response.content}\n`);
    }
  } catch (error) {
    console.log(`❌ Error: ${error}`);
  }
}

/**
 * Print setup instructions
 */
function printSetupInstructions(): void {
  printSeparator('Setup Instructions');

  console.log('\n1️⃣  vLLM:');
  console.log('   docker run --gpus all -p 8000:8000 vllm/vllm-openai \\');
  console.log('       --model meta-llama/Llama-2-7b-chat-hf\n');

  console.log('2️⃣  llama.cpp:');
  console.log('   git clone https://github.com/ggerganov/llama.cpp');
  console.log('   cd llama.cpp && make');
  console.log('   ./server -m models/llama-2-7b-chat.gguf -c 2048 --port 8080\n');

  console.log('3️⃣  SGLang:');
  console.log('   pip install sglang');
  console.log('   python -m sglang.launch_server \\');
  console.log('       --model-path meta-llama/Llama-2-7b-chat-hf \\');
  console.log('       --port 30000\n');

  console.log('4️⃣  TensorRT-LLM:');
  console.log('   docker run --gpus all -p 8001:8001 \\');
  console.log('       nvcr.io/nvidia/tritonserver:23.10-trtllm-python-py3 \\');
  console.log('       tritonserver --model-repository=/models\n');

  console.log('💡 Benefits:');
  console.log('   • Run LLMs locally (no cloud API costs)');
  console.log('   • Keep data private (on-premises)');
  console.log('   • Same code works with all services');
  console.log('   • Easy migration between providers\n');
}

/**
 * Main function
 */
async function main(): Promise<void> {
  console.log('╔' + '='.repeat(78) + '╗');
  console.log('║' + ' '.repeat(15) + 'OpenAI-Compatible LLM Adapter Examples' + ' '.repeat(24) + '║');
  console.log('╚' + '='.repeat(78) + '╝');
  console.log();
  console.log('This example demonstrates using Agenkit with OpenAI-compatible');
  console.log('inference services like vLLM, llama.cpp, SGLang, and TensorRT-LLM.');
  console.log();
  console.log('Note: These examples require a running inference service.');
  console.log('See the examples below for setup instructions.');
  console.log();

  // Run examples
  await vllmExample();
  await llamacppExample();
  await streamingExample();
  await multiServiceExample();
  await conversationExample();

  // Print setup instructions
  printSetupInstructions();

  console.log('✅ Example Complete!');
  console.log();
  console.log('Next steps:');
  console.log('  • Start a local inference service');
  console.log('  • Run: npm run example examples/adapters/openai-compatible-basic.ts');
  console.log('  • Try different services and models');
}

// Run if executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}

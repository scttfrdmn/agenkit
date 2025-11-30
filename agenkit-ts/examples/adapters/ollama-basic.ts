/**
 * Ollama Basic Usage Example
 *
 * Demonstrates:
 * - Local LLM inference with Ollama
 * - Zero-cost development and testing
 * - Privacy-preserving local inference
 * - Multiple model comparison
 * - Streaming responses
 * - Temperature effects
 *
 * Setup:
 *   1. Install Ollama: https://ollama.ai/download
 *   2. Pull a model: ollama pull llama2
 *   3. Verify: ollama list
 *   4. npm run build
 *   5. node dist/examples/adapters/ollama-basic.js
 */

import { OllamaAdapter } from '../../src/adapters/ollama';
import { createMessage } from '../../src/core/interfaces';

function printSeparator(title: string = '') {
  console.log('\n' + '='.repeat(60));
  if (title) {
    console.log(title);
    console.log('='.repeat(60));
  }
  console.log();
}

async function basicCompletion() {
  printSeparator('Example 1: Basic Completion');

  // Initialize Ollama adapter (no API key needed!)
  const ollama = new OllamaAdapter({
    model: 'llama2', // Or: mistral, codellama, phi, gemma
    baseURL: 'http://localhost:11434', // Default Ollama server
    temperature: 0.7,
    maxTokens: 150,
  });

  console.log(`Model: ${ollama.name}`);
  console.log('Server: http://localhost:11434');
  console.log();

  const message = createMessage({
    role: 'user',
    content: 'What is AgentKit and why would I use it?',
  });

  console.log('Sending request to local Ollama server...\n');

  try {
    const response = await ollama.process(message);

    console.log(`Response: ${response.content}\n`);

    // Access metadata
    console.log('Metadata:');
    if (response.metadata) {
      console.log(`  Model: ${response.metadata.model}`);
      if (response.metadata.total_duration_ms) {
        console.log(`  Duration: ${Math.round(response.metadata.total_duration_ms)}ms`);
      }
      if (response.metadata.usage) {
        console.log(`  Prompt tokens: ${response.metadata.usage.prompt_tokens}`);
        console.log(`  Completion tokens: ${response.metadata.usage.completion_tokens}`);
        console.log(`  Total tokens: ${response.metadata.usage.total_tokens}`);
      }
    }
    console.log();
  } catch (error) {
    console.error(`❌ Error: ${error}`);
    console.log('\nTroubleshooting:');
    console.log('  1. Is Ollama running? (ollama serve)');
    console.log('  2. Do you have the model? (ollama pull llama2)');
    console.log('  3. Is the server accessible at http://localhost:11434?');
  }
}

async function streamingExample() {
  printSeparator('Example 2: Streaming Response');

  const ollama = new OllamaAdapter({
    model: 'llama2',
  });

  const message = createMessage({
    role: 'user',
    content: 'Write a haiku about AI agents.',
  });

  console.log('Streaming from local Ollama: ');

  try {
    let fullResponse = '';
    for await (const chunk of ollama.stream(message)) {
      process.stdout.write(chunk.content);
      fullResponse += chunk.content;
    }

    console.log('\n');
    console.log(`✓ Streamed ${fullResponse.length} characters\n`);
  } catch (error) {
    console.error(`\n❌ Streaming error: ${error}`);
  }
}

async function conversationExample() {
  printSeparator('Example 3: Multi-turn Conversation');

  const ollama = new OllamaAdapter({
    model: 'llama2',
    maxTokens: 100,
  });

  // Note: This example sends independent requests.
  // For true conversation history, you would need to maintain context
  // (Ollama adapter currently processes single messages)

  console.log('Turn 1:');
  const message1 = createMessage({
    role: 'user',
    content: 'What is an agent pattern?',
  });

  console.log(`User: ${message1.content}`);

  try {
    const response1 = await ollama.process(message1);
    console.log(`Assistant: ${response1.content}\n`);

    console.log('Turn 2:');
    const message2 = createMessage({
      role: 'user',
      content: 'Can you give me an example?',
    });

    console.log(`User: ${message2.content}`);

    const response2 = await ollama.process(message2);
    console.log(`Assistant: ${response2.content}\n`);

    console.log('✓ Multi-turn conversation completed');
    console.log('Note: For conversation history, wrap in ConversationalAgent pattern\n');
  } catch (error) {
    console.error(`❌ Error: ${error}`);
  }
}

async function modelComparison() {
  printSeparator('Example 4: Model Comparison');

  const prompt = 'Explain what an AI agent is in one sentence.';
  console.log(`Prompt: ${prompt}\n`);

  const models = [
    { name: 'llama2', description: 'Meta\'s Llama 2 (balanced)' },
    { name: 'mistral', description: 'Mistral 7B (fast, capable)' },
    { name: 'phi', description: 'Microsoft\'s efficient model' },
  ];

  for (const model of models) {
    console.log(`Model: ${model.name}`);
    console.log(`  ${model.description}`);

    const ollama = new OllamaAdapter({
      model: model.name,
      maxTokens: 50,
    });

    try {
      const message = createMessage({ role: 'user', content: prompt });
      const response = await ollama.process(message);
      console.log(`  Response: ${response.content}\n`);
    } catch (error) {
      console.error(`  ❌ ${model.name} not available: ${error}`);
      console.log(`     Pull with: ollama pull ${model.name}\n`);
    }
  }
}

async function temperatureComparison() {
  printSeparator('Example 5: Temperature Comparison');

  const ollama = new OllamaAdapter({
    model: 'llama2',
  });

  const prompt = 'List 3 creative uses for AI agents.';
  console.log(`Prompt: ${prompt}\n`);

  const temperatures = [0.0, 0.5, 1.0];

  for (const temp of temperatures) {
    console.log(`Temperature: ${temp}`);
    console.log('  ' + (temp === 0.0 ? '(deterministic, focused)' :
                        temp === 0.5 ? '(balanced)' :
                        '(creative, varied)'));

    const tempOllama = new OllamaAdapter({
      model: 'llama2',
      temperature: temp,
      maxTokens: 100,
    });

    try {
      const message = createMessage({ role: 'user', content: prompt });
      const response = await tempOllama.process(message);
      console.log(`  ${response.content}\n`);
    } catch (error) {
      console.error(`  ❌ Error: ${error}\n`);
    }
  }
}

async function errorHandling() {
  printSeparator('Example 6: Error Handling');

  console.log('Testing with invalid server URL...\n');

  const ollama = new OllamaAdapter({
    model: 'llama2',
    baseURL: 'http://invalid-server:11434',
    timeout: 3000, // 3 second timeout
  });

  try {
    const message = createMessage({ role: 'user', content: 'Test message' });
    await ollama.process(message);
    console.log('Unexpected success!');
  } catch (error) {
    console.log('✓ Error handled correctly:');
    console.log(`  ${error}\n`);
  }
}

async function main() {
  printSeparator('OLLAMA ADAPTER EXAMPLES');
  console.log('Local LLM inference with Ollama\n');

  console.log('Prerequisites:');
  console.log('  ✓ No API key required (runs locally)');
  console.log('  ✓ Install: https://ollama.ai/download');
  console.log('  ✓ Pull model: ollama pull llama2');

  await basicCompletion();
  await streamingExample();
  await conversationExample();
  await modelComparison();
  await temperatureComparison();
  await errorHandling();

  printSeparator('✅ ALL EXAMPLES COMPLETED');

  console.log('💡 Key Advantages of Ollama:\n');
  console.log('  • No API keys or costs');
  console.log('  • Runs entirely locally');
  console.log('  • Fast inference on local hardware');
  console.log('  • Privacy - data never leaves your machine');
  console.log('  • Great for development and testing\n');

  console.log('Popular Ollama models:\n');
  console.log('  • llama2 - Meta\'s Llama 2 (balanced)');
  console.log('  • llama3 - Meta\'s Llama 3 (latest)');
  console.log('  • mistral - Mistral 7B (fast, capable)');
  console.log('  • codellama - Code-focused Llama');
  console.log('  • phi - Microsoft\'s efficient model');
  console.log('  • gemma - Google\'s open model\n');

  console.log('Commands:');
  console.log('  ollama list          - Show installed models');
  console.log('  ollama pull <model>  - Download a model');
  console.log('  ollama serve         - Start Ollama server\n');
}

main().catch(console.error);

/**
 * LLM Integration Example - OpenAI and Anthropic
 *
 * Demonstrates how to integrate real LLM providers:
 * - OpenAI (GPT-4, GPT-3.5)
 * - Anthropic (Claude)
 * - Middleware for production resilience
 *
 * Setup:
 *   export OPENAI_API_KEY="your-key"
 *   export ANTHROPIC_API_KEY="your-key"
 *
 * Run: npx ts-node examples/llm-integration.ts
 */

import {
  OpenAIAgent,
  AnthropicAgent,
  retry,
  timeout,
  circuitBreaker,
  createMessage,
} from '../src/index';

async function main() {
  console.log('🤖 Agenkit LLM Integration Examples\n');

  // ==================================================================
  // Example 1: OpenAI Agent
  // ==================================================================
  console.log('📚 Example 1: OpenAI Integration');
  console.log('  GPT-4 and GPT-3.5 Turbo support\n');

  if (process.env.OPENAI_API_KEY) {
    const openaiAgent = new OpenAIAgent({
      apiKey: process.env.OPENAI_API_KEY,
      model: 'gpt-3.5-turbo', // or 'gpt-4'
      temperature: 0.7,
      maxTokens: 150,
    });

    console.log('  Asking OpenAI: "What is agenkit?"');
    try {
      const response = await openaiAgent.process(
        createMessage('user', 'What is agenkit? Answer in one sentence.'),
      );
      console.log(`  🤖 OpenAI: ${response.content}\n`);
    } catch (error: any) {
      console.log(`  ❌ Error: ${error.message}\n`);
    }
  } else {
    console.log('  ⚠️  OPENAI_API_KEY not set, skipping...\n');
  }

  // ==================================================================
  // Example 2: Anthropic Agent (Claude)
  // ==================================================================
  console.log('📚 Example 2: Anthropic Integration');
  console.log('  Claude 3 (Opus, Sonnet, Haiku) support\n');

  if (process.env.ANTHROPIC_API_KEY) {
    const anthropicAgent = new AnthropicAgent({
      apiKey: process.env.ANTHROPIC_API_KEY,
      model: 'claude-3-sonnet-20240229',
      maxTokens: 150,
    });

    console.log('  Asking Claude: "What makes a good AI agent framework?"');
    try {
      const response = await anthropicAgent.process(
        createMessage('user', 'What makes a good AI agent framework? One sentence.'),
      );
      console.log(`  🤖 Claude: ${response.content}\n`);
    } catch (error: any) {
      console.log(`  ❌ Error: ${error.message}\n`);
    }
  } else {
    console.log('  ⚠️  ANTHROPIC_API_KEY not set, skipping...\n');
  }

  // ==================================================================
  // Example 3: Production-Ready LLM Agent
  // ==================================================================
  console.log('📚 Example 3: Production-Ready LLM with Middleware');
  console.log('  Add resilience: Retry + Timeout + Circuit Breaker\n');

  if (process.env.OPENAI_API_KEY) {
    // Create base agent
    const baseAgent = new OpenAIAgent({
      apiKey: process.env.OPENAI_API_KEY,
      model: 'gpt-3.5-turbo',
      temperature: 0.7,
    });

    // Wrap with production middleware
    const productionAgent = circuitBreaker(
      timeout(
        retry(baseAgent, {
          maxRetries: 3,
          initialDelay: 1000,
          backoffMultiplier: 2,
        }),
        {
          timeout: 30000, // 30 second timeout
        },
      ),
      {
        failureThreshold: 5,
        recoveryTimeout: 60000,
      },
    );

    console.log('  Middleware stack: Circuit Breaker → Timeout → Retry → OpenAI');
    console.log('  Processing request...');

    try {
      const response = await productionAgent.process(
        createMessage('user', 'Explain middleware in one sentence.'),
      );
      console.log(`  ✅ Success: ${response.content}\n`);
    } catch (error: any) {
      console.log(`  ❌ Failed: ${error.message}\n`);
    }
  } else {
    console.log('  ⚠️  OPENAI_API_KEY not set, skipping...\n');
  }

  // ==================================================================
  // Example 4: Streaming Responses
  // ==================================================================
  console.log('📚 Example 4: Streaming LLM Responses');
  console.log('  Real-time token-by-token output\n');

  if (process.env.OPENAI_API_KEY) {
    const streamingAgent = new OpenAIAgent({
      apiKey: process.env.OPENAI_API_KEY,
      model: 'gpt-3.5-turbo',
      stream: true,
    });

    console.log('  Streaming response: "Tell me a haiku about code"');
    console.log('  🤖 ');

    try {
      for await (const chunk of streamingAgent.processStream(
        createMessage('user', 'Tell me a haiku about code.'),
      )) {
        process.stdout.write(chunk.content);
      }
      console.log('\n');
    } catch (error: any) {
      console.log(`\n  ❌ Error: ${error.message}\n`);
    }
  } else {
    console.log('  ⚠️  OPENAI_API_KEY not set, skipping...\n');
  }

  // ==================================================================
  // Configuration Best Practices
  // ==================================================================
  console.log('🎯 LLM Configuration Best Practices\n');

  console.log('  Model Selection:');
  console.log('    • GPT-4: Most capable, slower, $$$');
  console.log('    • GPT-3.5-turbo: Fast, cheap, good for most tasks');
  console.log('    • Claude Opus: Highest capability');
  console.log('    • Claude Sonnet: Balanced performance/cost');
  console.log('    • Claude Haiku: Fastest, cheapest\n');

  console.log('  Temperature Settings:');
  console.log('    • 0.0-0.3: Deterministic, factual (code, facts)');
  console.log('    • 0.4-0.7: Balanced (most applications)');
  console.log('    • 0.8-1.0: Creative (writing, brainstorming)\n');

  console.log('  Production Checklist:');
  console.log('    ✓ Add retry middleware (handle rate limits)');
  console.log('    ✓ Add timeout middleware (prevent hangs)');
  console.log('    ✓ Add circuit breaker (handle outages)');
  console.log('    ✓ Monitor token usage (cost control)');
  console.log('    ✓ Cache responses (reduce API calls)');
  console.log('    ✓ Use streaming for UX (show progress)\n');

  // ==================================================================
  // Cost Optimization Tips
  // ==================================================================
  console.log('💰 Cost Optimization Tips\n');

  console.log('  1. Use appropriate models:');
  console.log('     • Don\'t use GPT-4 for simple tasks');
  console.log('     • Start with GPT-3.5, upgrade if needed\n');

  console.log('  2. Limit max_tokens:');
  console.log('     • Set reasonable limits (e.g., 150 for short answers)');
  console.log('     • Prevents runaway costs\n');

  console.log('  3. Cache responses:');
  console.log('     • Use caching middleware for repeated queries');
  console.log('     • Especially effective for FAQ-style apps\n');

  console.log('  4. Batch requests:');
  console.log('     • Use batching middleware when possible');
  console.log('     • OpenAI Batch API: 50% cheaper!\n');

  console.log('✨ Pro Tip: Monitor your API usage in production!');
  console.log('   Set up alerts for unexpected cost spikes.');
}

main().catch(console.error);

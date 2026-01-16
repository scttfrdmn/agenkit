/**
 * Vector Memory with Semantic Search Example
 *
 * Demonstrates:
 * - Using OpenAI embeddings for semantic search
 * - Storing conversation messages with metadata
 * - Semantic retrieval with similarity scoring
 * - Filtering by importance, tags, and time
 * - RAG (Retrieval-Augmented Generation) pattern
 *
 * Prerequisites:
 * 1. Install OpenAI SDK: npm install openai
 * 2. Set OPENAI_API_KEY environment variable
 *
 * Run: npx ts-node examples/vector-memory-semantic-search.ts
 */

import { OpenAI } from 'openai';
import { VectorMemory, OpenAIEmbeddings } from '../src/memory';
import { Message } from '../src';

async function main() {
  console.log('=== Vector Memory with Semantic Search ===\n');

  // Check for API key
  if (!process.env.OPENAI_API_KEY) {
    console.error('Error: OPENAI_API_KEY environment variable not set');
    console.log('\nTo run this example:');
    console.log('  export OPENAI_API_KEY=your-api-key');
    console.log('  npx ts-node examples/vector-memory-semantic-search.ts');
    process.exit(1);
  }

  // Initialize OpenAI embeddings
  console.log('1. Initializing OpenAI embeddings (text-embedding-3-small)...\n');
  const embeddings = new OpenAIEmbeddings(new OpenAI(), {
    model: 'text-embedding-3-small', // 1536 dimensions, $0.02/1M tokens
  });

  // Create vector memory
  const memory = new VectorMemory(embeddings);
  console.log(`   Embedding dimension: ${embeddings.dimension()}`);
  console.log(`   Capabilities: ${memory.capabilities.join(', ')}\n`);

  // Store conversation messages with metadata
  console.log('2. Storing conversation messages...\n');

  const sessionId = 'demo-session-1';

  const messages: Array<{ message: Message; metadata?: Record<string, unknown> }> = [
    {
      message: {
        role: 'user',
        content: 'What are your pricing plans for the enterprise tier?',
      },
      metadata: { importance: 0.9, tags: ['pricing', 'enterprise'] },
    },
    {
      message: {
        role: 'assistant',
        content:
          'Our enterprise tier starts at $5,000/month and includes dedicated support, ' +
          'custom integrations, and 99.9% SLA. Volume discounts available.',
      },
      metadata: { importance: 0.9, tags: ['pricing', 'enterprise'] },
    },
    {
      message: {
        role: 'user',
        content: 'Can you tell me a joke?',
      },
      metadata: { importance: 0.2, tags: ['casual'] },
    },
    {
      message: {
        role: 'assistant',
        content: 'Why did the AI go to therapy? It had too many deep learning issues!',
      },
      metadata: { importance: 0.2, tags: ['casual'] },
    },
    {
      message: {
        role: 'user',
        content: 'How do I configure the API timeout settings?',
      },
      metadata: { importance: 0.7, tags: ['technical', 'configuration'] },
    },
    {
      message: {
        role: 'assistant',
        content:
          'API timeout can be configured in the config file using the timeout_seconds ' +
          'parameter. Default is 30 seconds. You can set it per-request with the timeout option.',
      },
      metadata: { importance: 0.7, tags: ['technical', 'configuration'] },
    },
    {
      message: {
        role: 'user',
        content: 'What security features do you offer?',
      },
      metadata: { importance: 0.8, tags: ['security', 'enterprise'] },
    },
    {
      message: {
        role: 'assistant',
        content:
          'We offer end-to-end encryption, SOC 2 Type II certification, role-based ' +
          'access control (RBAC), audit logging, and optional on-premise deployment.',
      },
      metadata: { importance: 0.8, tags: ['security', 'enterprise'] },
    },
  ];

  for (const { message, metadata } of messages) {
    await memory.store(sessionId, message, metadata);
    const preview = message.content.substring(0, 60);
    console.log(`   ✓ Stored: ${preview}...`);
  }

  console.log(`\n   Total messages stored: ${messages.length}\n`);

  // Example 1: Semantic search for pricing information
  console.log('3. Semantic Search: "pricing and costs"\n');

  const pricingResults = await memory.retrieve(sessionId, {
    query: 'pricing and costs',
    limit: 2,
  });

  console.log('   Top results:');
  for (const msg of pricingResults) {
    const preview = msg.content.substring(0, 70);
    console.log(`   - [${msg.role}] ${preview}...`);
  }

  // Example 2: Semantic search with similarity scores
  console.log('\n4. Semantic Search with Scores: "security features"\n');

  const securityResults = await memory.retrieveWithScores(sessionId, 'security features', 3);

  console.log('   Results with similarity scores:');
  for (const [msg, score] of securityResults) {
    const preview = msg.content.substring(0, 60);
    console.log(`   - [${msg.role}] (score: ${score.toFixed(3)}) ${preview}...`);
  }

  // Example 3: Filter by importance threshold
  console.log('\n5. Filter by Importance (threshold: 0.7)\n');

  const importantResults = await memory.retrieve(sessionId, {
    importanceThreshold: 0.7,
    limit: 10,
  });

  console.log(`   Found ${importantResults.length} high-importance messages:`);
  for (const msg of importantResults) {
    const preview = msg.content.substring(0, 50);
    console.log(`   - ${preview}...`);
  }

  // Example 4: Filter by tags
  console.log('\n6. Filter by Tags: ["enterprise"]\n');

  const enterpriseResults = await memory.retrieve(sessionId, {
    tags: ['enterprise'],
    limit: 10,
  });

  console.log(`   Found ${enterpriseResults.length} enterprise-related messages:`);
  for (const msg of enterpriseResults) {
    const preview = msg.content.substring(0, 50);
    console.log(`   - ${preview}...`);
  }

  // Example 5: Combined filters with semantic search
  console.log('\n7. Combined: Semantic + Importance + Tags\n');
  console.log('   Query: "enterprise features"');
  console.log('   Filters: importance >= 0.7, tags include "enterprise"\n');

  const combinedResults = await memory.retrieveWithScores(
    sessionId,
    'enterprise features',
    5,
    {
      importanceThreshold: 0.7,
      tags: ['enterprise'],
    },
  );

  console.log(`   Found ${combinedResults.length} matching messages:`);
  for (const [msg, score] of combinedResults) {
    const preview = msg.content.substring(0, 60);
    console.log(`   - (score: ${score.toFixed(3)}) ${preview}...`);
  }

  // Example 6: RAG pattern - retrieve context for answering a question
  console.log('\n8. RAG Pattern: Retrieve context for question\n');

  const question = 'What security and pricing options are available?';
  console.log(`   Question: "${question}"\n`);

  const context = await memory.retrieveWithScores(sessionId, question, 3, {
    importanceThreshold: 0.7,
  });

  console.log('   Retrieved context:');
  for (const [msg, score] of context) {
    const preview = msg.content.substring(0, 70);
    console.log(`   - [${msg.role}] (relevance: ${score.toFixed(3)})`);
    console.log(`     ${preview}...`);
  }

  console.log('\n   → This context would be passed to an LLM to generate an informed answer\n');

  // Example 7: Session summary
  console.log('9. Session Summary\n');

  const summary = await memory.summarize(sessionId);
  console.log(`   ${summary.content}\n`);

  // Example 8: Time-based filtering
  console.log('10. Time-based Filtering (last hour)\n');

  const now = new Date();
  const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);

  const recentMessages = await memory.retrieve(sessionId, {
    timeRange: [oneHourAgo, now],
    limit: 10,
  });

  console.log(`   Found ${recentMessages.length} messages from the last hour\n`);

  // Cleanup
  console.log('11. Cleanup\n');
  await memory.clear(sessionId);
  console.log('   ✓ Session cleared\n');

  console.log('=== Example Complete ===\n');
  console.log('Key Takeaways:');
  console.log('• Semantic search finds relevant messages by meaning, not exact keywords');
  console.log('• Combine semantic search with metadata filtering for precise retrieval');
  console.log('• Use importance scores to prioritize critical information');
  console.log('• Tags enable categorical filtering');
  console.log('• Perfect for RAG: retrieve relevant context before LLM generation');
  console.log('\nCost Analysis:');
  console.log(`• Stored 8 messages (~${messages.reduce((sum, m) => sum + m.message.content.length, 0)} chars)`);
  console.log('• Embeddings: ~$0.0001 for this example (text-embedding-3-small)');
  console.log('• Production: Batch embeddings and cache for cost efficiency\n');
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});

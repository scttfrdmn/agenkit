/**
 * Basic Vector Memory Example (No API Key Required)
 *
 * Demonstrates vector memory with a simple mock embedding provider.
 * Perfect for learning and testing without external dependencies.
 *
 * Run: npx ts-node examples/vector-memory-basic.ts
 */

import { VectorMemory, EmbeddingProvider } from '../src/memory';
import { Message } from '../src';

/**
 * Simple embedding provider for demonstration.
 * Uses character frequencies to create embeddings.
 */
class SimpleEmbeddingProvider implements EmbeddingProvider {
  async embed(text: string): Promise<number[]> {
    // Create 10-dimensional embedding based on character frequencies
    const embedding = new Array(10).fill(0);

    for (let i = 0; i < text.length; i++) {
      const charCode = text.toLowerCase().charCodeAt(i);
      embedding[i % 10] += charCode;
    }

    // Normalize to unit vector
    const magnitude = Math.sqrt(embedding.reduce((sum, val) => sum + val * val, 0));
    return magnitude > 0 ? embedding.map((val) => val / magnitude) : embedding;
  }

  dimension(): number {
    return 10;
  }
}

async function main() {
  console.log('=== Basic Vector Memory Example ===\n');

  // Initialize vector memory with simple embeddings
  console.log('1. Initialize vector memory with simple embeddings\n');
  const embeddings = new SimpleEmbeddingProvider();
  const memory = new VectorMemory(embeddings);

  console.log(`   Embedding dimension: ${embeddings.dimension()}`);
  console.log(`   Capabilities: ${memory.capabilities.join(', ')}\n`);

  // Store some messages
  console.log('2. Store conversation messages\n');

  const sessionId = 'demo-session';

  const messages = [
    { role: 'user' as const, content: 'Hello! How are you today?' },
    { role: 'assistant' as const, content: 'Hello! I am doing well, thank you for asking.' },
    { role: 'user' as const, content: 'What is machine learning?' },
    {
      role: 'assistant' as const,
      content: 'Machine learning is a subset of AI that enables systems to learn from data.',
    },
    { role: 'user' as const, content: 'Tell me about neural networks.' },
    {
      role: 'assistant' as const,
      content: 'Neural networks are computing systems inspired by biological neural networks.',
    },
  ];

  for (const msg of messages) {
    await memory.store(sessionId, msg);
    console.log(`   ✓ ${msg.role}: ${msg.content.substring(0, 50)}...`);
  }

  console.log('\n3. Basic retrieval (most recent)\n');

  const recentMessages = await memory.retrieve(sessionId, { limit: 3 });
  console.log(`   Retrieved ${recentMessages.length} most recent messages:`);
  for (const msg of recentMessages) {
    console.log(`   - [${msg.role}] ${msg.content.substring(0, 60)}`);
  }

  console.log('\n4. Semantic search\n');

  const query = 'artificial intelligence and learning';
  console.log(`   Query: "${query}"\n`);

  const searchResults = await memory.retrieve(sessionId, {
    query,
    limit: 2,
  });

  console.log('   Top results:');
  for (const msg of searchResults) {
    console.log(`   - [${msg.role}] ${msg.content.substring(0, 60)}`);
  }

  console.log('\n5. Retrieve with similarity scores\n');

  const scoredResults = await memory.retrieveWithScores(sessionId, 'neural networks', 3);

  console.log('   Results with scores:');
  for (const [msg, score] of scoredResults) {
    console.log(`   - [${msg.role}] (score: ${score.toFixed(3)}) ${msg.content.substring(0, 50)}`);
  }

  console.log('\n6. Store messages with metadata\n');

  await memory.store(
    sessionId,
    { role: 'user', content: 'Important question about production deployment' },
    { importance: 0.9, tags: ['production', 'critical'] },
  );

  await memory.store(
    sessionId,
    { role: 'user', content: 'Random casual comment' },
    { importance: 0.1, tags: ['casual'] },
  );

  console.log('   ✓ Stored 2 messages with metadata\n');

  console.log('7. Filter by importance\n');

  const importantMessages = await memory.retrieve(sessionId, {
    importanceThreshold: 0.7,
    limit: 10,
  });

  console.log(`   Found ${importantMessages.length} high-importance messages:`);
  for (const msg of importantMessages) {
    console.log(`   - ${msg.content.substring(0, 60)}`);
  }

  console.log('\n8. Filter by tags\n');

  const taggedMessages = await memory.retrieve(sessionId, {
    tags: ['production'],
    limit: 10,
  });

  console.log(`   Found ${taggedMessages.length} messages tagged "production":`);
  for (const msg of taggedMessages) {
    console.log(`   - ${msg.content.substring(0, 60)}`);
  }

  console.log('\n9. Generate session summary\n');

  const summary = await memory.summarize(sessionId);
  console.log(`   ${summary.content}\n`);

  console.log('10. Clear session\n');
  await memory.clear(sessionId);
  console.log('   ✓ Session cleared\n');

  const emptyCheck = await memory.retrieve(sessionId);
  console.log(`   Messages remaining: ${emptyCheck.length}\n`);

  console.log('=== Example Complete ===\n');
}

main().catch((error) => {
  console.error('Error:', error);
  process.exit(1);
});

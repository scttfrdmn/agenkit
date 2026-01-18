/**
 * Production Vector Memory Example
 *
 * Demonstrates production-ready vector memory patterns including:
 * - OpenAI embeddings with real semantic search
 * - Distance metrics (cosine, euclidean, dot product)
 * - Batch operations for efficiency
 * - ChromaDB integration for persistent storage
 * - Performance optimization strategies
 *
 * Prerequisites:
 * 1. Install dependencies: npm install openai chromadb
 * 2. Set OPENAI_API_KEY environment variable
 * 3. Optional: Start ChromaDB server (docker run -p 8000:8000 chromadb/chroma)
 *
 * Run: npx ts-node examples/vector-memory-production.ts
 */

import { OpenAI } from 'openai';
import { VectorMemory, OpenAIEmbeddings, InMemoryVectorStore } from '../src/memory';
import { Message } from '../src';

async function main() {
  console.log('=== Production Vector Memory Example ===\n');

  // Check for API key
  if (!process.env.OPENAI_API_KEY) {
    console.error('Error: OPENAI_API_KEY environment variable not set');
    console.log('\nTo run this example:');
    console.log('  export OPENAI_API_KEY=your-api-key');
    console.log('  npx ts-node examples/vector-memory-production.ts');
    process.exit(1);
  }

  // ====================================================================
  // Part 1: Initialize with OpenAI Embeddings
  // ====================================================================
  console.log('1. Initialize with OpenAI embeddings\n');

  const embeddings = new OpenAIEmbeddings(new OpenAI(), {
    model: 'text-embedding-3-small', // 1536 dimensions, $0.02/1M tokens
  });

  const vectorStore = new InMemoryVectorStore();
  const memory = new VectorMemory(embeddings, vectorStore);

  console.log(`   Embedding model: text-embedding-3-small`);
  console.log(`   Dimension: ${embeddings.dimension()}`);
  console.log(`   Capabilities: ${memory.capabilities.join(', ')}\n`);

  const sessionId = 'production-session';

  // ====================================================================
  // Part 2: Batch Operations for Efficiency
  // ====================================================================
  console.log('2. Batch storage for efficient bulk operations\n');

  const documents: Array<{ message: Message; metadata?: Record<string, unknown> }> = [
    {
      message: {
        role: 'user',
        content: 'What is the capital of France?',
      },
      metadata: { importance: 0.5, tags: ['geography', 'europe'] },
    },
    {
      message: {
        role: 'assistant',
        content: 'The capital of France is Paris.',
      },
      metadata: { importance: 0.5, tags: ['geography', 'europe'] },
    },
    {
      message: {
        role: 'user',
        content: 'How do I implement a binary search tree in Python?',
      },
      metadata: { importance: 0.8, tags: ['programming', 'algorithms'] },
    },
    {
      message: {
        role: 'assistant',
        content:
          'A binary search tree can be implemented using a Node class with left, right, ' +
          'and value attributes. Each node maintains the BST property: left < parent < right.',
      },
      metadata: { importance: 0.8, tags: ['programming', 'algorithms'] },
    },
    {
      message: {
        role: 'user',
        content: 'What are the health benefits of exercise?',
      },
      metadata: { importance: 0.6, tags: ['health', 'fitness'] },
    },
    {
      message: {
        role: 'assistant',
        content:
          'Regular exercise improves cardiovascular health, strengthens muscles, ' +
          'boosts mental health, and helps maintain a healthy weight.',
      },
      metadata: { importance: 0.6, tags: ['health', 'fitness'] },
    },
    {
      message: {
        role: 'user',
        content: 'Explain quantum entanglement.',
      },
      metadata: { importance: 0.9, tags: ['physics', 'quantum'] },
    },
    {
      message: {
        role: 'assistant',
        content:
          'Quantum entanglement is a phenomenon where particles become correlated ' +
          'such that the quantum state of one particle cannot be described independently.',
      },
      metadata: { importance: 0.9, tags: ['physics', 'quantum'] },
    },
  ];

  console.log(`   Storing ${documents.length} messages in batch...`);
  const startBatch = Date.now();

  // Use batch operation - generates embeddings in parallel
  await memory.storeBatch(sessionId, documents);

  const batchTime = Date.now() - startBatch;
  console.log(`   ✓ Batch storage completed in ${batchTime}ms`);
  console.log(`   Average: ${(batchTime / documents.length).toFixed(1)}ms per message\n`);

  // ====================================================================
  // Part 3: Distance Metrics Comparison
  // ====================================================================
  console.log('3. Compare distance metrics for semantic search\n');

  const query = 'computer science data structures';
  console.log(`   Query: "${query}"\n`);

  // Cosine similarity (default - best for text)
  console.log('   a) Cosine Similarity (default):');
  const cosineResults = await memory.retrieveWithScores(sessionId, query, 3, {
    distanceMetric: 'cosine',
  });
  for (const [msg, score] of cosineResults) {
    const preview = msg.content.substring(0, 50);
    console.log(`      - (${score.toFixed(3)}) ${preview}...`);
  }

  // Euclidean distance
  console.log('\n   b) Euclidean Distance:');
  const euclideanResults = await memory.retrieveWithScores(sessionId, query, 3, {
    distanceMetric: 'euclidean',
  });
  for (const [msg, score] of euclideanResults) {
    const preview = msg.content.substring(0, 50);
    console.log(`      - (${score.toFixed(3)}) ${preview}...`);
  }

  // Dot product
  console.log('\n   c) Dot Product:');
  const dotProductResults = await memory.retrieveWithScores(sessionId, query, 3, {
    distanceMetric: 'dot_product',
  });
  for (const [msg, score] of dotProductResults) {
    const preview = msg.content.substring(0, 50);
    console.log(`      - (${score.toFixed(3)}) ${preview}...`);
  }

  console.log('\n   → Cosine similarity typically works best for text embeddings\n');

  // ====================================================================
  // Part 4: Advanced Filtering with Semantic Search
  // ====================================================================
  console.log('4. Advanced filtering: semantic + importance + tags\n');

  const searchQuery = 'scientific concepts and theories';
  console.log(`   Query: "${searchQuery}"`);
  console.log('   Filters: importance >= 0.8, tags include "physics" or "programming"\n');

  const filteredResults = await memory.retrieveWithScores(sessionId, searchQuery, 5, {
    importanceThreshold: 0.8,
    tags: ['physics', 'programming'],
    distanceMetric: 'cosine',
  });

  console.log(`   Found ${filteredResults.length} matching results:`);
  for (const [msg, score] of filteredResults) {
    const preview = msg.content.substring(0, 60);
    console.log(`   - (score: ${score.toFixed(3)}) ${preview}...`);
  }

  // ====================================================================
  // Part 5: Batch Search for Multiple Queries
  // ====================================================================
  console.log('\n5. Batch search: process multiple queries efficiently\n');

  const queries = [
    'programming and algorithms',
    'physics and quantum mechanics',
    'health and wellness',
  ];

  console.log('   Processing queries:');
  for (const q of queries) {
    console.log(`   - "${q}"`);
  }

  // Note: Batch search at vector store level (not VectorMemory level yet)
  // Generate embeddings for all queries in parallel
  const startSearch = Date.now();
  const queryEmbeddings = await Promise.all(queries.map((q) => embeddings.embed(q)));

  // Perform batch search
  const batchResults = await vectorStore.searchBatch(sessionId, queryEmbeddings, 2);
  const searchTime = Date.now() - startSearch;

  console.log(`\n   ✓ Batch search completed in ${searchTime}ms\n`);

  console.log('   Results:');
  for (let i = 0; i < queries.length; i++) {
    console.log(`\n   Query ${i + 1}: "${queries[i]}"`);
    for (const result of batchResults[i]) {
      const preview = result.message.content.substring(0, 50);
      console.log(`   - (${result.score.toFixed(3)}) ${preview}...`);
    }
  }

  // ====================================================================
  // Part 6: Production Best Practices
  // ====================================================================
  console.log('\n6. Production best practices\n');

  console.log('   ✓ Batch operations: Use storeBatch() for bulk inserts');
  console.log('   ✓ Distance metrics: Choose based on your use case');
  console.log('     - Cosine: Text/NLP (most common)');
  console.log('     - Euclidean: Spatial data, images');
  console.log('     - Dot product: Pre-normalized vectors');
  console.log('   ✓ Metadata: Tag messages for efficient filtering');
  console.log('   ✓ Importance: Prioritize critical information');
  console.log('   ✓ Time ranges: Filter by recency for temporal data');
  console.log('   ✓ Persistent storage: Use ChromaDB for production');

  // ====================================================================
  // Part 7: Cost and Performance Analysis
  // ====================================================================
  console.log('\n7. Cost and performance analysis\n');

  const totalChars = documents.reduce((sum, doc) => sum + doc.message.content.length, 0);
  const estimatedTokens = Math.ceil(totalChars / 4); // Rough estimate
  const embeddingCost = (estimatedTokens / 1_000_000) * 0.02; // $0.02 per 1M tokens

  console.log(`   Messages stored: ${documents.length}`);
  console.log(`   Total characters: ${totalChars}`);
  console.log(`   Estimated tokens: ${estimatedTokens}`);
  console.log(`   Embedding cost: $${embeddingCost.toFixed(6)}`);
  console.log(`   Batch storage time: ${batchTime}ms`);
  console.log(`   Batch search time: ${searchTime}ms`);

  console.log('\n   Performance tips:');
  console.log('   • Batch operations reduce API calls and latency');
  console.log('   • Cache embeddings for frequently accessed messages');
  console.log('   • Use appropriate distance metric for your domain');
  console.log('   • Index metadata fields for faster filtering');
  console.log('   • Consider dimensionality reduction for very large datasets');

  // ====================================================================
  // Part 8: ChromaDB Integration (Optional)
  // ====================================================================
  console.log('\n8. ChromaDB integration for persistent storage\n');

  console.log('   To use ChromaDB in production:\n');
  console.log('   import { ChromaClient } from "chromadb";');
  console.log('   import { ChromaDBVectorStore } from "../src/memory";');
  console.log('');
  console.log('   const client = new ChromaClient();');
  console.log('   const vectorStore = new ChromaDBVectorStore(client, {');
  console.log('     collectionName: "my-agent-memory",');
  console.log('     distanceMetric: "cosine"  // or "euclidean", "dot_product"');
  console.log('   });');
  console.log('');
  console.log('   const memory = new VectorMemory(embeddings, vectorStore);');
  console.log('');
  console.log('   Benefits:');
  console.log('   • Persistent storage across restarts');
  console.log('   • Efficient indexing with HNSW algorithm');
  console.log('   • Native distance metric support');
  console.log('   • Horizontal scalability');

  // Cleanup
  console.log('\n9. Cleanup\n');
  await memory.clear(sessionId);
  console.log('   ✓ Session cleared\n');

  console.log('=== Example Complete ===\n');
  console.log('Key Takeaways:');
  console.log('• Use batch operations for better performance and lower costs');
  console.log('• Choose the right distance metric for your domain');
  console.log('• Combine semantic search with metadata filtering');
  console.log('• Use ChromaDB or similar for production persistence');
  console.log('• Monitor costs and optimize batch sizes\n');
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});

# TypeScript Vector Memory Implementation

**Status**: ✅ Complete (19 tests passing)
**Completed**: January 16, 2026
**Issue**: [#463](https://github.com/scttfrdmn/agenkit/issues/463)

---

## Overview

Vector Memory provides semantic retrieval for agent conversations using embeddings and vector similarity. This enables RAG (Retrieval-Augmented Generation) patterns and intelligent context management.

### Key Features

- ✅ **Semantic Search**: Find relevant messages by meaning, not just keywords
- ✅ **Pluggable Embeddings**: Support for OpenAI, custom providers
- ✅ **Pluggable Storage**: In-memory, ChromaDB, and custom vector stores
- ✅ **Rich Filtering**: Time range, importance, tags, similarity threshold
- ✅ **Similarity Scores**: Retrieve messages with cosine similarity scores
- ✅ **Session Isolation**: Independent memory for each session
- ✅ **Production Ready**: Comprehensive tests, proper error handling

---

## Architecture

### Core Interfaces

```typescript
interface EmbeddingProvider {
  embed(text: string): Promise<number[]>;
  dimension(): number;
}

interface VectorStore {
  add(sessionId, messageId, embedding, message, metadata, timestamp): Promise<void>;
  search(sessionId, queryEmbedding, limit, options): Promise<MessageSearchResult[]>;
  getRecent(sessionId, limit, options): Promise<MessageWithMetadata[]>;
  clear(sessionId): Promise<void>;
}

class VectorMemory implements Memory {
  constructor(embeddingProvider: EmbeddingProvider, vectorStore?: VectorStore);
  store(sessionId, message, metadata?): Promise<void>;
  retrieve(sessionId, options?): Promise<Message[]>;
  retrieveWithScores(sessionId, query, limit, options?): Promise<[Message, number][]>;
  summarize(sessionId, options?): Promise<Message>;
  clear(sessionId): Promise<void>;
  get capabilities(): string[];
}
```

### Implementations

| Component | Description | Use Case |
|-----------|-------------|----------|
| `InMemoryVectorStore` | Simple cosine similarity | Testing, small datasets |
| `ChromaDBVectorStore` | ChromaDB integration | Production, RAG applications |
| `OpenAIEmbeddings` | OpenAI embeddings API | High-quality semantic search |
| Custom | Roll your own | Specialized requirements |

---

## Installation

### Required Dependencies

```bash
npm install @agenkit/core
```

### Optional Dependencies

For OpenAI embeddings:
```bash
npm install openai
```

For ChromaDB storage:
```bash
npm install chromadb
```

---

## Quick Start

### Basic Usage (No External Dependencies)

```typescript
import { VectorMemory, EmbeddingProvider } from '@agenkit/core';

// Simple embedding provider
class SimpleEmbeddings implements EmbeddingProvider {
  async embed(text: string): Promise<number[]> {
    // Your embedding logic here
    return [0.1, 0.2, 0.3, ...]; // 10-1536 dimensions
  }

  dimension(): number {
    return 10;
  }
}

const memory = new VectorMemory(new SimpleEmbeddings());

// Store messages
await memory.store('session-1', {
  role: 'user',
  content: 'What are your pricing plans?'
}, { importance: 0.9, tags: ['pricing'] });

// Semantic search
const results = await memory.retrieve('session-1', {
  query: 'costs and pricing',
  limit: 5
});
```

### Production Usage with OpenAI

```typescript
import { OpenAI } from 'openai';
import { VectorMemory, OpenAIEmbeddings } from '@agenkit/core';

const embeddings = new OpenAIEmbeddings(
  new OpenAI({ apiKey: process.env.OPENAI_API_KEY }),
  { model: 'text-embedding-3-small' }
);

const memory = new VectorMemory(embeddings);

// Store conversation
await memory.store('session-1', message, {
  importance: 0.8,
  tags: ['support', 'technical']
});

// Semantic search with scores
const results = await memory.retrieveWithScores(
  'session-1',
  'technical support issues',
  5
);

for (const [message, score] of results) {
  console.log(`Score: ${score.toFixed(3)} - ${message.content}`);
}
```

### Production Usage with ChromaDB

```typescript
import { ChromaClient } from 'chromadb';
import {
  VectorMemory,
  ChromaDBVectorStore,
  OpenAIEmbeddings
} from '@agenkit/core';
import { OpenAI } from 'openai';

// Initialize ChromaDB
const chromaClient = new ChromaClient();
const vectorStore = new ChromaDBVectorStore(chromaClient, {
  collectionName: 'agent-memory'
});

// Initialize embeddings
const embeddings = new OpenAIEmbeddings(new OpenAI());

// Create memory with persistent storage
const memory = new VectorMemory(embeddings, vectorStore);

// Use as normal - data persists in ChromaDB
await memory.store('session-1', message);
```

---

## API Reference

### VectorMemory

#### Constructor

```typescript
constructor(
  embeddingProvider: EmbeddingProvider,
  vectorStore?: VectorStore
)
```

Creates a new vector memory instance.

**Parameters:**
- `embeddingProvider`: Provider for generating embeddings
- `vectorStore`: Storage backend (defaults to `InMemoryVectorStore`)

#### store()

```typescript
async store(
  sessionId: string,
  message: Message,
  metadata?: Record<string, unknown>
): Promise<void>
```

Store a message with optional metadata.

**Parameters:**
- `sessionId`: Session identifier
- `message`: Message to store
- `metadata`: Optional metadata (importance, tags, etc.)

**Example:**
```typescript
await memory.store('session-1', message, {
  importance: 0.9,
  tags: ['critical', 'security'],
  userId: 'user-123'
});
```

#### retrieve()

```typescript
async retrieve(
  sessionId: string,
  options?: {
    query?: string;              // Semantic query
    limit?: number;              // Max results (default: 10)
    timeRange?: [Date, Date];    // Time filter
    importanceThreshold?: number; // Min importance (0-1)
    tags?: string[];             // Tag filter
    minSimilarity?: number;      // Min similarity score (0-1)
  }
): Promise<Message[]>
```

Retrieve messages with optional semantic search and filtering.

**Examples:**
```typescript
// Most recent messages
const recent = await memory.retrieve('session-1', { limit: 10 });

// Semantic search
const relevant = await memory.retrieve('session-1', {
  query: 'security features',
  limit: 5
});

// Filter by importance
const important = await memory.retrieve('session-1', {
  importanceThreshold: 0.7,
  limit: 10
});

// Filter by tags
const tagged = await memory.retrieve('session-1', {
  tags: ['bug', 'critical'],
  limit: 20
});

// Combined filters
const results = await memory.retrieve('session-1', {
  query: 'authentication issues',
  importanceThreshold: 0.6,
  tags: ['security'],
  minSimilarity: 0.5,
  limit: 5
});
```

#### retrieveWithScores()

```typescript
async retrieveWithScores(
  sessionId: string,
  query: string,
  limit?: number,
  options?: {
    timeRange?: [Date, Date];
    importanceThreshold?: number;
    tags?: string[];
    minSimilarity?: number;
  }
): Promise<Array<[Message, number]>>
```

Retrieve messages with similarity scores for ranking and filtering.

**Example:**
```typescript
const results = await memory.retrieveWithScores(
  'session-1',
  'pricing plans',
  5
);

for (const [message, score] of results) {
  console.log(`Relevance: ${(score * 100).toFixed(1)}%`);
  console.log(`Content: ${message.content}\n`);
}
```

#### summarize()

```typescript
async summarize(
  sessionId: string,
  options?: {
    maxLength?: number;
    style?: 'brief' | 'detailed';
  }
): Promise<Message>
```

Generate a summary of the session's conversation history.

**Example:**
```typescript
const summary = await memory.summarize('session-1');
console.log(summary.content);
// "Session summary (25 messages):
//  1. [user] What are your pricing plans?
//  2. [assistant] We offer three tiers: Basic ($10), Pro ($50)..."
```

#### clear()

```typescript
async clear(sessionId: string): Promise<void>
```

Clear all messages for a session.

**Example:**
```typescript
await memory.clear('session-1');
```

#### capabilities

```typescript
get capabilities(): string[]
```

Returns list of supported capabilities.

**Returns:**
```typescript
[
  'basic_retrieval',
  'semantic_search',
  'similarity_retrieval',
  'time_filtering',
  'importance_filtering',
  'tag_filtering'
]
```

---

## Filtering Options

### Time Range Filtering

```typescript
const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
const now = new Date();

const recentMessages = await memory.retrieve('session-1', {
  timeRange: [oneHourAgo, now],
  limit: 10
});
```

### Importance Filtering

```typescript
// Store with importance
await memory.store('session-1', message, { importance: 0.9 });

// Retrieve high-importance messages
const important = await memory.retrieve('session-1', {
  importanceThreshold: 0.7
});
```

### Tag Filtering

```typescript
// Store with tags
await memory.store('session-1', message, {
  tags: ['bug', 'critical', 'security']
});

// Retrieve by tags (matches any tag)
const bugMessages = await memory.retrieve('session-1', {
  tags: ['bug']
});
```

### Similarity Threshold

```typescript
const results = await memory.retrieve('session-1', {
  query: 'authentication',
  minSimilarity: 0.7 // Only return results with >70% similarity
});
```

### Combined Filters

```typescript
const results = await memory.retrieve('session-1', {
  query: 'security issues',
  importanceThreshold: 0.6,
  tags: ['security', 'urgent'],
  minSimilarity: 0.5,
  timeRange: [lastWeek, now],
  limit: 10
});
```

---

## RAG Pattern

Vector memory is perfect for RAG (Retrieval-Augmented Generation):

```typescript
import { OpenAI } from 'openai';
import { VectorMemory, OpenAIEmbeddings } from '@agenkit/core';

const client = new OpenAI();
const memory = new VectorMemory(new OpenAIEmbeddings(client));

// Store knowledge base
await memory.store('kb', { role: 'system', content: 'Product pricing: $50/mo' });
await memory.store('kb', { role: 'system', content: 'Support available 24/7' });

// User question
const question = 'How much does your product cost?';

// Retrieve relevant context
const context = await memory.retrieveWithScores('kb', question, 3);

// Build prompt with context
const contextStr = context
  .map(([msg, score]) => `[Relevance: ${score.toFixed(2)}] ${msg.content}`)
  .join('\n');

const response = await client.chat.completions.create({
  model: 'gpt-4',
  messages: [
    { role: 'system', content: `Context:\n${contextStr}` },
    { role: 'user', content: question }
  ]
});

console.log(response.choices[0].message.content);
```

---

## Embedding Providers

### OpenAI Embeddings

```typescript
import { OpenAI } from 'openai';
import { OpenAIEmbeddings } from '@agenkit/core';

const embeddings = new OpenAIEmbeddings(
  new OpenAI({ apiKey: process.env.OPENAI_API_KEY }),
  {
    model: 'text-embedding-3-small', // or 'text-embedding-3-large'
    dimension: 1536 // Optional, defaults based on model
  }
);

console.log(`Dimension: ${embeddings.dimension()}`);
```

**Models:**
- `text-embedding-3-small`: 1536 dimensions, $0.02/1M tokens
- `text-embedding-3-large`: 3072 dimensions, $0.13/1M tokens
- `text-embedding-ada-002`: 1536 dimensions (legacy)

### Custom Embedding Provider

```typescript
import { EmbeddingProvider } from '@agenkit/core';

class CustomEmbeddings implements EmbeddingProvider {
  async embed(text: string): Promise<number[]> {
    // Call your embedding service
    const response = await fetch('https://your-embedding-api.com/embed', {
      method: 'POST',
      body: JSON.stringify({ text })
    });

    const data = await response.json();
    return data.embedding;
  }

  dimension(): number {
    return 768; // Your model's dimension
  }
}

const memory = new VectorMemory(new CustomEmbeddings());
```

---

## Vector Stores

### InMemoryVectorStore (Default)

Simple in-memory storage with cosine similarity. Good for testing and small datasets.

```typescript
import { VectorMemory, InMemoryVectorStore } from '@agenkit/core';

const vectorStore = new InMemoryVectorStore();
const memory = new VectorMemory(embeddings, vectorStore);
```

**Characteristics:**
- ✅ No external dependencies
- ✅ Fast for small datasets (<10k messages)
- ✅ Perfect for testing
- ❌ Not persistent
- ❌ Not scalable

### ChromaDBVectorStore

Production-ready vector database integration.

```typescript
import { ChromaClient } from 'chromadb';
import { ChromaDBVectorStore } from '@agenkit/core';

const client = new ChromaClient();
const vectorStore = new ChromaDBVectorStore(client, {
  collectionName: 'agent-memory'
});

const memory = new VectorMemory(embeddings, vectorStore);
```

**Characteristics:**
- ✅ Persistent storage
- ✅ Scalable to millions of vectors
- ✅ Fast approximate nearest neighbor search
- ✅ Metadata filtering
- ✅ Production-ready

### Custom Vector Store

```typescript
import { VectorStore, MessageSearchResult } from '@agenkit/core';

class CustomVectorStore implements VectorStore {
  async add(
    sessionId: string,
    messageId: string,
    embedding: number[],
    message: Message,
    metadata: Record<string, unknown>,
    timestamp: number
  ): Promise<void> {
    // Store in your database
  }

  async search(
    sessionId: string,
    queryEmbedding: number[],
    limit: number,
    options?: any
  ): Promise<MessageSearchResult[]> {
    // Perform similarity search
    return [];
  }

  async getRecent(
    sessionId: string,
    limit: number,
    options?: any
  ): Promise<MessageWithMetadata[]> {
    // Return recent messages
    return [];
  }

  async clear(sessionId: string): Promise<void> {
    // Clear session
  }
}

const memory = new VectorMemory(embeddings, new CustomVectorStore());
```

---

## Testing

### Run Tests

```bash
cd agenkit-ts
npm test -- src/memory/__tests__/vector-memory.test.ts
```

### Test Coverage

✅ **19 tests passing (100% success rate)**

**Test Categories:**
1. Basic Operations (4 tests)
   - Store and retrieve
   - Multiple messages
   - Session isolation
   - Clear session

2. Semantic Search (3 tests)
   - Semantic query
   - Retrieve with scores
   - Most recent (no query)

3. Metadata Filtering (4 tests)
   - Importance threshold
   - Tag filtering
   - Time range filtering
   - Combined filters

4. InMemoryVectorStore (3 tests)
   - Cosine similarity calculation
   - Zero-magnitude vectors
   - Similarity threshold

5. Other (5 tests)
   - Capabilities
   - Summarization
   - Empty session
   - Limit parameter

---

## Examples

### Example 1: Basic Usage (No API Key)

```bash
npx ts-node examples/vector-memory-basic.ts
```

Demonstrates:
- Simple embedding provider
- Store/retrieve operations
- Semantic search basics
- Metadata filtering
- Session management

### Example 2: Semantic Search with OpenAI

```bash
export OPENAI_API_KEY=your-api-key
npx ts-node examples/vector-memory-semantic-search.ts
```

Demonstrates:
- OpenAI embeddings integration
- Production-ready semantic search
- RAG pattern
- Advanced filtering
- Similarity scoring
- Cost analysis

---

## Performance Characteristics

### InMemoryVectorStore

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Store | O(1) | Append to array |
| Search | O(n) | Linear scan with cosine similarity |
| getRecent | O(n log n) | Sort by timestamp |
| Clear | O(1) | Delete map entry |

**Recommendations:**
- Use for <10k messages per session
- Good for testing and development
- Not suitable for large-scale production

### ChromaDBVectorStore

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Store | O(log n) | Indexed insert |
| Search | O(log n) | ANN (approximate nearest neighbor) |
| getRecent | O(n log n) | Secondary index sort |
| Clear | O(n) | Batch delete |

**Recommendations:**
- Use for production deployments
- Scales to millions of vectors
- Supports distributed deployment

---

## Cost Analysis

### Embedding Costs (OpenAI)

| Model | Dimension | Cost/1M tokens | Use Case |
|-------|-----------|---------------|----------|
| text-embedding-3-small | 1536 | $0.02 | General purpose |
| text-embedding-3-large | 3072 | $0.13 | High precision |
| text-embedding-ada-002 | 1536 | $0.10 | Legacy |

**Example:**
- 1,000 messages (avg 100 tokens each) = 100k tokens
- Cost with text-embedding-3-small: $0.002
- Cost with text-embedding-3-large: $0.013

**Cost Optimization:**
- ✅ Batch embed multiple messages
- ✅ Cache embeddings
- ✅ Use smaller models when possible
- ✅ Consider local embedding models for high volume

---

## Comparison with Python/Go

### Feature Parity

| Feature | Python | Go | TypeScript |
|---------|--------|----|-----------
| EmbeddingProvider | ✅ | ✅ | ✅ |
| VectorStore interface | ✅ | ✅ | ✅ |
| InMemoryVectorStore | ✅ | ✅ | ✅ |
| Cosine similarity | ✅ | ✅ | ✅ |
| Semantic search | ✅ | ✅ | ✅ |
| Retrieve with scores | ✅ | ✅ | ✅ |
| Importance filtering | ✅ | ✅ | ✅ |
| Tag filtering | ✅ | ✅ | ✅ |
| Time filtering | ✅ | ✅ | ✅ |
| Similarity threshold | ✅ | ✅ | ✅ |
| Session isolation | ✅ | ✅ | ✅ |
| Summarization | ✅ | ✅ | ✅ |
| ChromaDB integration | ❌ | ❌ | ✅ |
| OpenAI integration | ❌ | ❌ | ✅ |

### Test Coverage

| Language | Tests | Status |
|----------|-------|--------|
| Python | 25 | ✅ Complete |
| Go | 28 | ✅ Complete |
| TypeScript | **19** | ✅ **Complete** |

---

## Best Practices

### 1. Choose the Right Embedding Model

```typescript
// For general purpose (cost-effective)
const embeddings = new OpenAIEmbeddings(client, {
  model: 'text-embedding-3-small'
});

// For high precision (more expensive)
const embeddings = new OpenAIEmbeddings(client, {
  model: 'text-embedding-3-large'
});
```

### 2. Use Metadata Effectively

```typescript
await memory.store('session-1', message, {
  importance: calculateImportance(message), // 0.0-1.0
  tags: extractTags(message), // ['bug', 'feature', 'security']
  userId: session.userId,
  timestamp: Date.now(),
  // Custom metadata
  department: 'engineering',
  priority: 'high'
});
```

### 3. Combine Filters for Precision

```typescript
// Find recent, important, security-related messages
const results = await memory.retrieve('session-1', {
  query: 'authentication issues',
  importanceThreshold: 0.7,
  tags: ['security'],
  timeRange: [lastWeek, now],
  minSimilarity: 0.6,
  limit: 10
});
```

### 4. Use Similarity Scores for Ranking

```typescript
const results = await memory.retrieveWithScores(
  'session-1',
  query,
  20 // Fetch more than needed
);

// Filter by score and re-rank
const filtered = results
  .filter(([msg, score]) => score > 0.5)
  .sort(([_a, scoreA], [_b, scoreB]) => scoreB - scoreA)
  .slice(0, 5);
```

### 5. Cache Embeddings for Repeated Queries

```typescript
const embeddingCache = new Map<string, number[]>();

class CachedEmbeddings implements EmbeddingProvider {
  constructor(private provider: EmbeddingProvider) {}

  async embed(text: string): Promise<number[]> {
    if (embeddingCache.has(text)) {
      return embeddingCache.get(text)!;
    }

    const embedding = await this.provider.embed(text);
    embeddingCache.set(text, embedding);
    return embedding;
  }

  dimension(): number {
    return this.provider.dimension();
  }
}

const memory = new VectorMemory(new CachedEmbeddings(embeddings));
```

---

## Troubleshooting

### Issue: Slow Search Performance

**Solution:** Use a production vector database like ChromaDB:

```typescript
import { ChromaClient } from 'chromadb';
import { ChromaDBVectorStore } from '@agenkit/core';

const vectorStore = new ChromaDBVectorStore(new ChromaClient());
const memory = new VectorMemory(embeddings, vectorStore);
```

### Issue: High Embedding Costs

**Solutions:**
1. Use smaller model: `text-embedding-3-small` instead of `large`
2. Batch embeddings
3. Cache embeddings for repeated queries
4. Consider local embedding models (e.g., sentence-transformers)

### Issue: Poor Semantic Search Results

**Solutions:**
1. Use higher quality embeddings (`text-embedding-3-large`)
2. Increase `minSimilarity` threshold
3. Combine with importance/tag filtering
4. Store more context in messages
5. Use more specific queries

### Issue: Memory Usage Growing

**Solution:** Implement TTL or periodic cleanup:

```typescript
// Clear old sessions periodically
setInterval(async () => {
  const oldSessions = await getSessionsOlderThan(30 * 24 * 60 * 60 * 1000); // 30 days
  for (const sessionId of oldSessions) {
    await memory.clear(sessionId);
  }
}, 24 * 60 * 60 * 1000); // Daily cleanup
```

---

## Future Enhancements

Potential future additions (not in current scope):

- [ ] Pinecone integration
- [ ] Weaviate integration
- [ ] Qdrant integration
- [ ] Batch embedding operations
- [ ] Automatic importance calculation
- [ ] Automatic tag extraction
- [ ] TTL/expiration support
- [ ] Multi-vector search (hybrid search)
- [ ] Compression for large embeddings

---

## References

- **Issue**: [#463 - TypeScript Vector Memory](https://github.com/scttfrdmn/agenkit/issues/463)
- **Python Implementation**: `agenkit/memory/vector_memory.py`
- **Go Implementation**: `agenkit-go/memory/vector_memory.go`
- **Tests**: `src/memory/__tests__/vector-memory.test.ts`
- **Examples**: `examples/vector-memory-*.ts`

---

**Last Updated**: January 16, 2026
**Status**: Production Ready ✅
**Test Coverage**: 19/19 tests passing (100%)

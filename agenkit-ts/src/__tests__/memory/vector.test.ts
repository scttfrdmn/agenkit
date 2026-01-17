/**
 * Tests for VectorMemory and InMemoryVectorStore.
 *
 * Tests semantic search, similarity scoring, embeddings,
 * and vector store operations.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  VectorMemory,
  InMemoryVectorStore,
  type EmbeddingProvider,
  type VectorStore,
} from '../../memory/vector-memory';
import { createMessage, type Message } from '../../core/interfaces';

// Mock embedding provider for testing
class MockEmbeddingProvider implements EmbeddingProvider {
  private dim: number;

  constructor(dimension: number = 10) {
    this.dim = dimension;
  }

  async embed(text: string): Promise<number[]> {
    // Character-frequency based deterministic embeddings
    const embedding = new Array(this.dim).fill(0);

    for (let i = 0; i < text.length; i++) {
      const charCode = text.charCodeAt(i);
      embedding[i % this.dim] += charCode / 1000;
    }

    return embedding;
  }

  dimension(): number {
    return this.dim;
  }
}

describe('VectorMemory', () => {
  let memory: VectorMemory;
  let embeddings: MockEmbeddingProvider;
  let vectorStore: VectorStore;

  beforeEach(() => {
    embeddings = new MockEmbeddingProvider(10);
    vectorStore = new InMemoryVectorStore();
    memory = new VectorMemory(embeddings, vectorStore);
  });

  // ============================================
  // Basic Operations Tests
  // ============================================

  describe('Basic Operations', () => {
    it('should store and retrieve single message', async () => {
      const sessionId = 'session-1';
      const message = createMessage('user', 'Hello world');

      await memory.store(sessionId, message);
      const retrieved = await memory.retrieve(sessionId);

      expect(retrieved).toHaveLength(1);
      expect(retrieved[0].content).toBe('Hello world');
    });

    it('should retrieve multiple messages', async () => {
      const sessionId = 'session-1';

      await memory.store(sessionId, createMessage('user', 'First message'));
      await memory.store(sessionId, createMessage('assistant', 'Second message'));
      await memory.store(sessionId, createMessage('user', 'Third message'));

      const retrieved = await memory.retrieve(sessionId);

      expect(retrieved).toHaveLength(3);
    });

    it('should handle empty session', async () => {
      const retrieved = await memory.retrieve('nonexistent-session');

      expect(retrieved).toHaveLength(0);
    });

    it('should clear session', async () => {
      const sessionId = 'session-1';

      await memory.store(sessionId, createMessage('user', 'Test'));
      expect(await memory.retrieve(sessionId)).toHaveLength(1);

      await memory.clear(sessionId);
      expect(await memory.retrieve(sessionId)).toHaveLength(0);
    });
  });

  // ============================================
  // Semantic Search Tests
  // ============================================

  describe('Semantic Search', () => {
    beforeEach(async () => {
      const sessionId = 'session-1';

      await memory.store(sessionId, createMessage('user', 'How do I reset my password?'));
      await memory.store(sessionId, createMessage('user', 'What is the weather today?'));
      await memory.store(sessionId, createMessage('user', 'Help me recover my account password'));
      await memory.store(sessionId, createMessage('user', 'Show me the forecast'));
    });

    it('should perform semantic search with query', async () => {
      const results = await memory.retrieve('session-1', {
        query: 'password recovery',
      });

      expect(results.length).toBeGreaterThan(0);
      // Should find password-related messages
      const contents = results.map((m) => m.content.toLowerCase());
      const hasPasswordContent = contents.some((c) => c.includes('password'));
      expect(hasPasswordContent).toBe(true);
    });

    it('should return similarity scores with retrieveWithScores', async () => {
      const results = await memory.retrieveWithScores('session-1', 'password', 5);

      expect(results.length).toBeGreaterThan(0);

      // Check structure: array of [Message, score] tuples
      results.forEach(([message, score]) => {
        expect(message).toHaveProperty('content');
        expect(message).toHaveProperty('role');
        expect(typeof score).toBe('number');
        expect(score).toBeGreaterThanOrEqual(-1);
        expect(score).toBeLessThanOrEqual(1);
      });
    });

    it('should order results by similarity', async () => {
      const results = await memory.retrieveWithScores('session-1', 'password reset', 10);

      // Scores should be in descending order (most similar first)
      for (let i = 1; i < results.length; i++) {
        expect(results[i - 1][1]).toBeGreaterThanOrEqual(results[i][1]);
      }
    });

    it('should return most recent when no query provided', async () => {
      const results = await memory.retrieve('session-1');

      expect(results).toHaveLength(4);
      // Should be in reverse chronological order
      expect(results[0].content).toBe('Show me the forecast'); // Most recent
    });
  });

  // ============================================
  // Filtering Tests
  // ============================================

  describe('Filtering', () => {
    beforeEach(async () => {
      const sessionId = 'session-1';

      await memory.store(sessionId, createMessage('user', 'Low priority task'), {
        importance: 0.3,
        tags: ['low'],
      });
      await memory.store(sessionId, createMessage('user', 'Medium priority task'), {
        importance: 0.5,
        tags: ['medium'],
      });
      await memory.store(sessionId, createMessage('user', 'High priority task'), {
        importance: 0.9,
        tags: ['high', 'urgent'],
      });
    });

    it('should filter by importance threshold', async () => {
      const results = await memory.retrieve('session-1', {
        importanceThreshold: 0.6,
      });

      expect(results).toHaveLength(1);
      expect(results[0].metadata?.importance).toBeGreaterThanOrEqual(0.6);
    });

    it('should filter by tags', async () => {
      const results = await memory.retrieve('session-1', {
        tags: ['urgent'],
      });

      expect(results).toHaveLength(1);
      expect(results[0].metadata?.tags).toContain('urgent');
    });

    it('should filter by time range', async () => {
      const sessionId = 'session-2';
      const now = new Date();
      const past = new Date(now.getTime() - 10000);
      const future = new Date(now.getTime() + 10000);

      await memory.store(sessionId, createMessage('user', 'Recent message'));

      const results = await memory.retrieve(sessionId, {
        timeRange: [past, future],
      });

      expect(results).toHaveLength(1);
    });

    it('should filter by minimum similarity', async () => {
      const results = await memory.retrieveWithScores('session-1', 'task', 10, {
        minSimilarity: 0.5,
      });

      results.forEach(([_message, score]) => {
        expect(score).toBeGreaterThanOrEqual(0.5);
      });
    });

    it('should combine semantic search with filters', async () => {
      const results = await memory.retrieve('session-1', {
        query: 'priority',
        importanceThreshold: 0.4,
        tags: ['medium', 'high'],
      });

      expect(results.length).toBeGreaterThanOrEqual(1);
      results.forEach((msg) => {
        expect(msg.metadata?.importance).toBeGreaterThanOrEqual(0.4);
      });
    });
  });

  // ============================================
  // Session Isolation Tests
  // ============================================

  describe('Session Isolation', () => {
    it('should isolate messages between sessions', async () => {
      await memory.store('session-1', createMessage('user', 'Session 1 message'));
      await memory.store('session-2', createMessage('user', 'Session 2 message'));

      const session1 = await memory.retrieve('session-1');
      const session2 = await memory.retrieve('session-2');

      expect(session1).toHaveLength(1);
      expect(session1[0].content).toBe('Session 1 message');

      expect(session2).toHaveLength(1);
      expect(session2[0].content).toBe('Session 2 message');
    });

    it('should search only within session', async () => {
      await memory.store('session-1', createMessage('user', 'password reset help'));
      await memory.store('session-2', createMessage('user', 'weather forecast'));

      const results = await memory.retrieve('session-1', { query: 'password' });

      expect(results).toHaveLength(1);
      expect(results[0].content).toContain('password');
    });
  });

  // ============================================
  // Metadata Tests
  // ============================================

  describe('Metadata', () => {
    it('should preserve metadata', async () => {
      const sessionId = 'session-1';
      const message = createMessage('user', 'Test message');
      const metadata = {
        importance: 0.8,
        tags: ['important', 'urgent'],
        custom: 'value',
      };

      await memory.store(sessionId, message, metadata);
      const retrieved = await memory.retrieve(sessionId);

      expect(retrieved[0].metadata?.importance).toBe(0.8);
      expect(retrieved[0].metadata?.tags).toEqual(['important', 'urgent']);
      expect(retrieved[0].metadata?.custom).toBe('value');
    });

    it('should preserve timestamp', async () => {
      const sessionId = 'session-1';
      const message = createMessage('user', 'Test');
      const now = new Date();

      await memory.store(sessionId, message);
      const retrieved = await memory.retrieve(sessionId);

      const timestamp = new Date(retrieved[0].timestamp!);
      expect(timestamp.getTime()).toBeGreaterThanOrEqual(now.getTime() - 1000);
      expect(timestamp.getTime()).toBeLessThanOrEqual(now.getTime() + 1000);
    });
  });

  // ============================================
  // Limit Parameter Tests
  // ============================================

  describe('Limit Parameter', () => {
    it('should respect limit in retrieve', async () => {
      const sessionId = 'session-1';

      for (let i = 0; i < 20; i++) {
        await memory.store(sessionId, createMessage('user', `Message ${i}`));
      }

      const results = await memory.retrieve(sessionId, { limit: 5 });

      expect(results.length).toBeLessThanOrEqual(5);
    });

    it('should use default limit of 10', async () => {
      const sessionId = 'session-1';

      for (let i = 0; i < 20; i++) {
        await memory.store(sessionId, createMessage('user', `Message ${i}`));
      }

      const results = await memory.retrieve(sessionId);

      expect(results.length).toBeLessThanOrEqual(10);
    });
  });

  // ============================================
  // Summarization Tests
  // ============================================

  describe('Summarization', () => {
    it('should generate summary', async () => {
      const sessionId = 'session-1';

      await memory.store(sessionId, createMessage('user', 'Hello'));
      await memory.store(sessionId, createMessage('assistant', 'Hi there'));

      const summary = await memory.summarize(sessionId);

      expect(summary).toBeDefined();
      expect(summary.role).toBe('system');
      expect(summary.content).toBeDefined();
      expect(summary.content.length).toBeGreaterThan(0);
    });

    it('should handle empty session summarization', async () => {
      const summary = await memory.summarize('empty-session');

      expect(summary).toBeDefined();
      expect(summary.role).toBe('system');
      expect(summary.content).toContain('No messages');
    });
  });

  // ============================================
  // Capabilities Tests
  // ============================================

  describe('Capabilities', () => {
    it('should report vector memory capabilities', () => {
      const capabilities = memory.capabilities;

      expect(capabilities).toContain('basic_retrieval');
      expect(capabilities).toContain('semantic_search');
      expect(capabilities).toContain('similarity_retrieval');
      expect(capabilities).toContain('time_filtering');
      expect(capabilities).toContain('importance_filtering');
      expect(capabilities).toContain('tag_filtering');
    });
  });
});

// ============================================
// InMemoryVectorStore Tests
// ============================================

describe('InMemoryVectorStore', () => {
  let store: InMemoryVectorStore;

  beforeEach(() => {
    store = new InMemoryVectorStore();
  });

  describe('Cosine Similarity', () => {
    it('should calculate similarity for identical vectors', async () => {
      const sessionId = 'session-1';
      const vector = [1, 0, 0, 0, 0];

      await store.add(sessionId, 'msg-1', vector, createMessage('user', 'Test 1'), {}, new Date());
      await store.add(sessionId, 'msg-2', vector, createMessage('user', 'Test 2'), {}, new Date());

      const results = await store.search(sessionId, vector, 2);

      expect(results.length).toBe(2);
      // Identical vectors should have similarity ~1.0
      results.forEach((result) => {
        expect(result.score).toBeCloseTo(1.0, 1);
      });
    });

    it('should calculate similarity for orthogonal vectors', async () => {
      const sessionId = 'session-1';
      const vector1 = [1, 0, 0, 0, 0];
      const vector2 = [0, 1, 0, 0, 0];

      await store.add(
        sessionId,
        'msg-1',
        vector1,
        createMessage('user', 'Test 1'),
        {},
        new Date(),
      );
      await store.add(
        sessionId,
        'msg-2',
        vector2,
        createMessage('user', 'Test 2'),
        {},
        new Date(),
      );

      const results = await store.search(sessionId, vector1, 2);

      // Find the orthogonal vector result by message content
      const orthogonalResult = results.find((r) => r.message.content === 'Test 2');
      expect(orthogonalResult).toBeDefined();
      // Orthogonal vectors should have similarity ~0.0
      expect(Math.abs(orthogonalResult!.score)).toBeLessThan(0.1);
    });

    it('should handle zero-magnitude vectors', async () => {
      const sessionId = 'session-1';
      const zeroVector = [0, 0, 0, 0, 0];
      const normalVector = [1, 0, 0, 0, 0];

      await store.add(
        sessionId,
        'msg-1',
        zeroVector,
        createMessage('user', 'Zero'),
        {},
        new Date(),
      );
      await store.add(
        sessionId,
        'msg-2',
        normalVector,
        createMessage('user', 'Normal'),
        {},
        new Date(),
      );

      const results = await store.search(sessionId, normalVector, 2);

      expect(results).toHaveLength(2);
      // Zero vector should have similarity 0.0
      const zeroResult = results.find((r) => r.message.content === 'Zero');
      expect(zeroResult?.score).toBe(0.0);
    });
  });

  describe('Search Operations', () => {
    it('should return results ordered by similarity', async () => {
      const sessionId = 'session-1';
      const queryVector = [1, 0, 0, 0, 0];
      const similar = [0.9, 0, 0, 0, 0];
      const dissimilar = [0, 1, 0, 0, 0];

      await store.add(
        sessionId,
        'msg-1',
        dissimilar,
        createMessage('user', 'Dissimilar'),
        {},
        new Date(),
      );
      await store.add(
        sessionId,
        'msg-2',
        similar,
        createMessage('user', 'Similar'),
        {},
        new Date(),
      );

      const results = await store.search(sessionId, queryVector, 2);

      expect(results[0].message.content).toBe('Similar'); // Most similar first
      expect(results[0].score).toBeGreaterThan(results[1].score);
    });

    it('should filter by minimum similarity', async () => {
      const sessionId = 'session-1';
      const queryVector = [1, 0, 0, 0, 0];

      await store.add(
        sessionId,
        'msg-1',
        [0.9, 0, 0, 0, 0],
        createMessage('user', 'High similarity'),
        {},
        new Date(),
      );
      await store.add(
        sessionId,
        'msg-2',
        [0, 1, 0, 0, 0],
        createMessage('user', 'Low similarity'),
        {},
        new Date(),
      );

      const results = await store.search(sessionId, queryVector, 10, { minSimilarity: 0.5 });

      expect(results).toHaveLength(1);
      expect(results[0].message.content).toBe('High similarity');
      expect(results[0].score).toBeGreaterThanOrEqual(0.5);
    });
  });

  describe('Recent Messages', () => {
    it('should retrieve recent messages without search', async () => {
      const sessionId = 'session-1';
      const now = Date.now();

      await store.add(
        sessionId,
        'msg-1',
        [1, 0],
        createMessage('user', 'First'),
        {},
        new Date(now - 2000),
      );
      await store.add(
        sessionId,
        'msg-2',
        [0, 1],
        createMessage('user', 'Second'),
        {},
        new Date(now - 1000),
      );
      await store.add(
        sessionId,
        'msg-3',
        [1, 1],
        createMessage('user', 'Third'),
        {},
        new Date(now),
      );

      const results = await store.getRecent(sessionId, 2);

      expect(results).toHaveLength(2);
      // Should be most recent first
      expect(results[0].message.content).toBe('Third');
      expect(results[1].message.content).toBe('Second');
    });
  });
});

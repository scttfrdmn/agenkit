/**
 * Tests for vector memory implementation.
 *
 * Tests cover:
 * - EmbeddingProvider interface
 * - InMemoryVectorStore with cosine similarity
 * - VectorMemory with semantic search
 * - Filtering (time, importance, tags, similarity)
 * - Session isolation
 * - Retrieve with scores
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { Message } from '../../core/interfaces';
import {
  VectorMemory,
  InMemoryVectorStore,
  EmbeddingProvider,
  VectorStore,
} from '../vector-memory';

/**
 * Mock embedding provider for testing.
 *
 * Generates deterministic embeddings based on character frequencies
 * for predictable test behavior.
 */
class MockEmbeddingProvider implements EmbeddingProvider {
  private readonly _dimension: number;

  constructor(dimension: number = 10) {
    this._dimension = dimension;
  }

  async embed(text: string): Promise<number[]> {
    // Simple character-based embedding for testing
    const embedding = new Array(this._dimension).fill(0);

    for (let i = 0; i < text.length; i++) {
      const charCode = text.charCodeAt(i);
      embedding[i % this._dimension] += charCode;
    }

    // Normalize to unit vector
    const magnitude = Math.sqrt(embedding.reduce((sum, val) => sum + val * val, 0));
    return magnitude > 0 ? embedding.map((val) => val / magnitude) : embedding;
  }

  dimension(): number {
    return this._dimension;
  }
}

describe('VectorMemory', () => {
  let embeddings: EmbeddingProvider;
  let vectorMemory: VectorMemory;

  beforeEach(() => {
    embeddings = new MockEmbeddingProvider(10);
    vectorMemory = new VectorMemory(embeddings);
  });

  describe('Basic Operations', () => {
    it('should store and retrieve messages', async () => {
      const message: Message = { role: 'user', content: 'Hello world' };

      await vectorMemory.store('session-1', message);
      const messages = await vectorMemory.retrieve('session-1');

      expect(messages).toHaveLength(1);
      expect(messages[0].content).toBe('Hello world');
      expect(messages[0].role).toBe('user');
    });

    it('should support multiple messages in session', async () => {
      const messages: Message[] = [
        { role: 'user', content: 'First message' },
        { role: 'assistant', content: 'Second message' },
        { role: 'user', content: 'Third message' },
      ];

      for (const msg of messages) {
        await vectorMemory.store('session-1', msg);
      }

      const retrieved = await vectorMemory.retrieve('session-1', { limit: 10 });
      expect(retrieved).toHaveLength(3);
    });

    it('should isolate sessions', async () => {
      await vectorMemory.store('session-1', { role: 'user', content: 'Session 1' });
      await vectorMemory.store('session-2', { role: 'user', content: 'Session 2' });

      const session1 = await vectorMemory.retrieve('session-1');
      const session2 = await vectorMemory.retrieve('session-2');

      expect(session1).toHaveLength(1);
      expect(session2).toHaveLength(1);
      expect(session1[0].content).toBe('Session 1');
      expect(session2[0].content).toBe('Session 2');
    });

    it('should clear session', async () => {
      await vectorMemory.store('session-1', { role: 'user', content: 'Message' });
      await vectorMemory.clear('session-1');

      const messages = await vectorMemory.retrieve('session-1');
      expect(messages).toHaveLength(0);
    });
  });

  describe('Semantic Search', () => {
    beforeEach(async () => {
      // Store test messages
      await vectorMemory.store('session-1', { role: 'user', content: 'The quick brown fox' });
      await vectorMemory.store('session-1', { role: 'assistant', content: 'Tell me about pricing plans' });
      await vectorMemory.store('session-1', { role: 'user', content: 'What are the costs?' });
      await vectorMemory.store('session-1', { role: 'assistant', content: 'The fox jumps over the fence' });
    });

    it('should perform semantic search', async () => {
      const messages = await vectorMemory.retrieve('session-1', {
        query: 'pricing information',
        limit: 2,
      });

      expect(messages).toHaveLength(2);
      // Should find pricing-related messages first
      expect(messages[0].content).toContain('pricing');
    });

    it('should retrieve with similarity scores', async () => {
      const results = await vectorMemory.retrieveWithScores('session-1', 'pricing costs', 2);

      expect(results).toHaveLength(2);
      expect(results[0]).toHaveLength(2); // [message, score] tuple
      expect(typeof results[0][1]).toBe('number');
      expect(results[0][1]).toBeGreaterThanOrEqual(-1);
      expect(results[0][1]).toBeLessThanOrEqual(1);
    });

    it('should return most recent when no query provided', async () => {
      // Add a clear delay to ensure different timestamps
      await new Promise((resolve) => setTimeout(resolve, 10));
      await vectorMemory.store('session-1', { role: 'user', content: 'Most recent message' });

      const messages = await vectorMemory.retrieve('session-1', { limit: 2 });

      expect(messages).toHaveLength(2);
      // Should be most recent first
      expect(messages[0].content).toBe('Most recent message');
    });
  });

  describe('Metadata Filtering', () => {
    beforeEach(async () => {
      const now = Date.now();

      await vectorMemory.store('session-1', { role: 'user', content: 'Low importance' }, { importance: 0.3 });

      await vectorMemory.store('session-1', { role: 'user', content: 'High importance' }, { importance: 0.9 });

      await vectorMemory.store('session-1', { role: 'user', content: 'Tagged message' }, { tags: ['urgent', 'bug'] });

      await vectorMemory.store('session-1', { role: 'user', content: 'Another tag' }, { tags: ['feature'] });
    });

    it('should filter by importance threshold', async () => {
      const messages = await vectorMemory.retrieve('session-1', {
        importanceThreshold: 0.5,
        limit: 10,
      });

      expect(messages.length).toBeGreaterThanOrEqual(1);
      // Should only get high importance message
      expect(messages.some((m) => m.content === 'High importance')).toBe(true);
      expect(messages.some((m) => m.content === 'Low importance')).toBe(false);
    });

    it('should filter by tags', async () => {
      const messages = await vectorMemory.retrieve('session-1', {
        tags: ['urgent'],
        limit: 10,
      });

      expect(messages.length).toBeGreaterThanOrEqual(1);
      expect(messages.some((m) => m.content === 'Tagged message')).toBe(true);
      expect(messages.some((m) => m.content === 'Another tag')).toBe(false);
    });

    it('should filter by time range', async () => {
      const now = new Date();
      const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
      const oneHourLater = new Date(now.getTime() + 60 * 60 * 1000);

      await vectorMemory.store('session-1', { role: 'user', content: 'Recent message' });

      const messages = await vectorMemory.retrieve('session-1', {
        timeRange: [oneHourAgo, oneHourLater],
        limit: 10,
      });

      expect(messages.length).toBeGreaterThan(0);
      expect(messages.some((m) => m.content === 'Recent message')).toBe(true);
    });

    it('should combine multiple filters', async () => {
      await vectorMemory.store(
        'session-1',
        { role: 'user', content: 'Important and tagged' },
        { importance: 0.8, tags: ['critical'] },
      );

      const messages = await vectorMemory.retrieve('session-1', {
        importanceThreshold: 0.7,
        tags: ['critical'],
        limit: 10,
      });

      expect(messages.length).toBeGreaterThanOrEqual(1);
      expect(messages[0].content).toBe('Important and tagged');
    });
  });

  describe('InMemoryVectorStore', () => {
    let vectorStore: VectorStore;

    beforeEach(() => {
      vectorStore = new InMemoryVectorStore();
    });

    it('should calculate cosine similarity correctly', async () => {
      const embedding1 = [1, 0, 0];
      const embedding2 = [0, 1, 0];
      const embedding3 = [1, 0, 0]; // Same as embedding1

      await vectorStore.add(
        'session-1',
        'msg-1',
        embedding1,
        { role: 'user', content: 'Message 1' },
        {},
        Date.now(),
      );

      await vectorStore.add(
        'session-1',
        'msg-2',
        embedding2,
        { role: 'user', content: 'Message 2' },
        {},
        Date.now(),
      );

      await vectorStore.add(
        'session-1',
        'msg-3',
        embedding3,
        { role: 'user', content: 'Message 3' },
        {},
        Date.now(),
      );

      const results = await vectorStore.search('session-1', embedding1, 3);

      expect(results).toHaveLength(3);
      // embedding1 and embedding3 are identical, should have score ~1.0
      expect(results[0].score).toBeCloseTo(1.0, 2);
      // embedding1 and embedding2 are orthogonal, should have score ~0.0
      expect(results[2].score).toBeCloseTo(0.0, 2);
    });

    it('should handle zero-magnitude vectors', async () => {
      const zeroVector = [0, 0, 0];
      const normalVector = [1, 1, 1];

      await vectorStore.add(
        'session-1',
        'msg-1',
        zeroVector,
        { role: 'user', content: 'Zero vector' },
        {},
        Date.now(),
      );

      const results = await vectorStore.search('session-1', normalVector, 1);

      expect(results).toHaveLength(1);
      expect(results[0].score).toBe(0.0); // Zero magnitude should give 0 similarity
    });

    it('should apply minimum similarity threshold', async () => {
      const embedding1 = [1, 0, 0];
      const embedding2 = [0, 1, 0]; // Orthogonal to embedding1

      await vectorStore.add(
        'session-1',
        'msg-1',
        embedding1,
        { role: 'user', content: 'Message 1' },
        {},
        Date.now(),
      );

      await vectorStore.add(
        'session-1',
        'msg-2',
        embedding2,
        { role: 'user', content: 'Message 2' },
        {},
        Date.now(),
      );

      const results = await vectorStore.search('session-1', embedding1, 10, {
        minSimilarity: 0.5,
      });

      // Should only get embedding1 (similarity ~1.0), not embedding2 (similarity ~0.0)
      expect(results).toHaveLength(1);
      expect(results[0].message.content).toBe('Message 1');
    });
  });

  describe('Capabilities', () => {
    it('should report correct capabilities', () => {
      const capabilities = vectorMemory.capabilities;

      expect(capabilities).toContain('basic_retrieval');
      expect(capabilities).toContain('semantic_search');
      expect(capabilities).toContain('similarity_retrieval');
      expect(capabilities).toContain('time_filtering');
      expect(capabilities).toContain('importance_filtering');
      expect(capabilities).toContain('tag_filtering');
    });
  });

  describe('Summarization', () => {
    it('should create summary from messages', async () => {
      for (let i = 1; i <= 5; i++) {
        await vectorMemory.store('session-1', {
          role: 'user',
          content: `Message ${i}: This is some content`,
        });
      }

      const summary = await vectorMemory.summarize('session-1');

      expect(summary.role).toBe('system');
      expect(summary.content).toContain('Session summary');
      expect(summary.content).toContain('5 messages');
    });

    it('should handle empty session', async () => {
      const summary = await vectorMemory.summarize('empty-session');

      expect(summary.role).toBe('system');
      expect(summary.content).toBe('No messages in session.');
    });
  });

  describe('Limit Parameter', () => {
    beforeEach(async () => {
      for (let i = 1; i <= 20; i++) {
        await vectorMemory.store('session-1', {
          role: 'user',
          content: `Message ${i}`,
        });
      }
    });

    it('should respect limit parameter', async () => {
      const messages = await vectorMemory.retrieve('session-1', { limit: 5 });
      expect(messages).toHaveLength(5);
    });

    it('should default to limit of 10', async () => {
      const messages = await vectorMemory.retrieve('session-1');
      expect(messages).toHaveLength(10);
    });
  });
});

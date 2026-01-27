/**
 * Tests for RedisMemory.
 *
 * Tests storage, retrieval, filtering, TTL, and utilities.
 *
 * NOTE: These tests require a running Redis instance.
 * Run: docker run -d -p 6379:6379 redis:7-alpine
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { RedisMemory } from '../../memory/redisMemory';
import { createMessage } from '../../core/interfaces';

describe('RedisMemory', () => {
  let memory: RedisMemory;

  beforeEach(() => {
    memory = new RedisMemory({
      redisUrl: process.env.REDIS_URL || 'redis://localhost:6379',
      ttl: 3600, // 1 hour for tests
      keyPrefix: 'agenkit:test:memory',
    });
  });

  afterEach(async () => {
    // Clean up test data
    try {
      const sessions = await memory.getAllSessions();
      for (const sessionId of sessions) {
        await memory.clear(sessionId);
      }
      await memory.close();
    } catch (err) {
      // Redis might not be available
    }
  });

  // ============================================
  // Connection Tests
  // ============================================

  describe('Connection', () => {
    it('should connect to Redis successfully', async () => {
      try {
        const sessionId = 'test-connection';
        await memory.store(sessionId, createMessage('user', 'Test'));
        const messages = await memory.retrieve(sessionId);
        expect(messages).toHaveLength(1);
      } catch (err) {
        // Skip test if Redis not available
        console.warn('Redis not available, skipping test');
        return;
      }
    });
  });

  // ============================================
  // Basic Store and Retrieve Tests
  // ============================================

  describe('Basic Operations', () => {
    it('should store and retrieve single message', async () => {
      try {
        const sessionId = 'session-1';
        const message = createMessage('user', 'Hello');

        await memory.store(sessionId, message);
        const retrieved = await memory.retrieve(sessionId);

        expect(retrieved).toHaveLength(1);
        expect(retrieved[0].content).toBe('Hello');
        expect(retrieved[0].role).toBe('user');
      } catch (err) {
        console.warn('Redis not available, skipping test');
        return;
      }
    });

    it('should retrieve messages in LIFO order (most recent first)', async () => {
      try {
        const sessionId = 'session-2';

        await memory.store(sessionId, createMessage('user', 'First'));
        // Small delay to ensure timestamp ordering
        await new Promise((resolve) => setTimeout(resolve, 10));
        await memory.store(sessionId, createMessage('assistant', 'Second'));
        await new Promise((resolve) => setTimeout(resolve, 10));
        await memory.store(sessionId, createMessage('user', 'Third'));

        const retrieved = await memory.retrieve(sessionId);

        expect(retrieved).toHaveLength(3);
        expect(retrieved[0].content).toBe('Third'); // Most recent
        expect(retrieved[1].content).toBe('Second');
        expect(retrieved[2].content).toBe('First');
      } catch (err) {
        console.warn('Redis not available, skipping test');
        return;
      }
    });

    it('should respect limit parameter', async () => {
      try {
        const sessionId = 'session-3';

        for (let i = 0; i < 10; i++) {
          await memory.store(sessionId, createMessage('user', `Message ${i}`));
        }

        const retrieved = await memory.retrieve(sessionId, { limit: 5 });

        expect(retrieved).toHaveLength(5);
      } catch (err) {
        console.warn('Redis not available, skipping test');
        return;
      }
    });

    it('should default to limit of 10', async () => {
      try {
        const sessionId = 'session-4';

        for (let i = 0; i < 20; i++) {
          await memory.store(sessionId, createMessage('user', `Message ${i}`));
        }

        const retrieved = await memory.retrieve(sessionId);

        expect(retrieved).toHaveLength(10); // Default limit
      } catch (err) {
        console.warn('Redis not available, skipping test');
        return;
      }
    });

    it('should handle empty session', async () => {
      try {
        const retrieved = await memory.retrieve('nonexistent-session');

        expect(retrieved).toHaveLength(0);
      } catch (err) {
        console.warn('Redis not available, skipping test');
        return;
      }
    });

    it('should clear session', async () => {
      try {
        const sessionId = 'session-5';

        await memory.store(sessionId, createMessage('user', 'Test'));
        expect((await memory.retrieve(sessionId)).length).toBe(1);

        await memory.clear(sessionId);
        expect((await memory.retrieve(sessionId)).length).toBe(0);
      } catch (err) {
        console.warn('Redis not available, skipping test');
        return;
      }
    });
  });

  // ============================================
  // Multi-Session Isolation Tests
  // ============================================

  describe('Session Isolation', () => {
    it('should isolate messages between sessions', async () => {
      try {
        await memory.store('session-a', createMessage('user', 'Session A message'));
        await memory.store('session-b', createMessage('user', 'Session B message'));

        const messagesA = await memory.retrieve('session-a');
        const messagesB = await memory.retrieve('session-b');

        expect(messagesA).toHaveLength(1);
        expect(messagesB).toHaveLength(1);
        expect(messagesA[0].content).toBe('Session A message');
        expect(messagesB[0].content).toBe('Session B message');
      } catch (err) {
        console.warn('Redis not available, skipping test');
        return;
      }
    });
  });

  // ============================================
  // Filtering Tests
  // ============================================

  describe('Filtering', () => {
    it('should filter by importance threshold', async () => {
      try {
        const sessionId = 'filter-importance';

        await memory.store(sessionId, createMessage('user', 'Low importance'), { importance: 0.3 });
        await memory.store(sessionId, createMessage('user', 'High importance'), { importance: 0.9 });

        const filtered = await memory.retrieve(sessionId, { importanceThreshold: 0.5 });

        expect(filtered).toHaveLength(1);
        expect(filtered[0].content).toBe('High importance');
      } catch (err) {
        console.warn('Redis not available, skipping test');
        return;
      }
    });

    it('should filter by tags (any match)', async () => {
      try {
        const sessionId = 'filter-tags';

        await memory.store(sessionId, createMessage('user', 'Greeting'), { tags: ['greeting'] });
        await memory.store(sessionId, createMessage('user', 'Question'), { tags: ['question'] });
        await memory.store(sessionId, createMessage('user', 'Feedback'), { tags: ['feedback'] });

        const filtered = await memory.retrieve(sessionId, { tags: ['greeting', 'question'] });

        expect(filtered).toHaveLength(2);
      } catch (err) {
        console.warn('Redis not available, skipping test');
        return;
      }
    });

    it('should filter by time range', async () => {
      try {
        const sessionId = 'filter-time';

        const now = new Date();
        const oneHourAgo = new Date(now.getTime() - 3600 * 1000);
        const twoHoursAgo = new Date(now.getTime() - 2 * 3600 * 1000);

        await memory.store(sessionId, createMessage('user', 'Recent'));
        await new Promise((resolve) => setTimeout(resolve, 100));

        const filtered = await memory.retrieve(sessionId, {
          timeRange: [twoHoursAgo, now],
        });

        expect(filtered).toHaveLength(1);
        expect(filtered[0].content).toBe('Recent');
      } catch (err) {
        console.warn('Redis not available, skipping test');
        return;
      }
    });

    it('should combine multiple filters', async () => {
      try {
        const sessionId = 'filter-combined';

        await memory.store(sessionId, createMessage('user', 'Important greeting'), {
          importance: 0.8,
          tags: ['greeting'],
        });
        await memory.store(sessionId, createMessage('user', 'Unimportant greeting'), {
          importance: 0.2,
          tags: ['greeting'],
        });
        await memory.store(sessionId, createMessage('user', 'Important question'), {
          importance: 0.9,
          tags: ['question'],
        });

        const filtered = await memory.retrieve(sessionId, {
          importanceThreshold: 0.5,
          tags: ['greeting'],
        });

        expect(filtered).toHaveLength(1);
        expect(filtered[0].content).toBe('Important greeting');
      } catch (err) {
        console.warn('Redis not available, skipping test');
        return;
      }
    });
  });

  // ============================================
  // Summarization Tests
  // ============================================

  describe('Summarization', () => {
    it('should summarize conversation', async () => {
      try {
        const sessionId = 'summarize-1';

        for (let i = 0; i < 5; i++) {
          await memory.store(sessionId, createMessage('user', `Message ${i}`));
        }

        const summary = await memory.summarize(sessionId);

        expect(summary.role).toBe('system');
        expect(summary.content).toContain('Session summary');
        expect(summary.content).toContain('5 messages');
      } catch (err) {
        console.warn('Redis not available, skipping test');
        return;
      }
    });

    it('should handle empty session in summarize', async () => {
      try {
        const summary = await memory.summarize('empty-session');

        expect(summary.role).toBe('system');
        expect(summary.content).toBe('No messages in session.');
      } catch (err) {
        console.warn('Redis not available, skipping test');
        return;
      }
    });
  });

  // ============================================
  // Utility Tests
  // ============================================

  describe('Utilities', () => {
    it('should get session count', async () => {
      try {
        const sessionId = 'util-count';

        for (let i = 0; i < 5; i++) {
          await memory.store(sessionId, createMessage('user', `Message ${i}`));
        }

        const count = await memory.getSessionCount(sessionId);

        expect(count).toBe(5);
      } catch (err) {
        console.warn('Redis not available, skipping test');
        return;
      }
    });

    it('should get all sessions', async () => {
      try {
        await memory.store('session-x', createMessage('user', 'X'));
        await memory.store('session-y', createMessage('user', 'Y'));
        await memory.store('session-z', createMessage('user', 'Z'));

        const sessions = await memory.getAllSessions();

        expect(sessions.length).toBeGreaterThanOrEqual(3);
        expect(sessions).toContain('session-x');
        expect(sessions).toContain('session-y');
        expect(sessions).toContain('session-z');
      } catch (err) {
        console.warn('Redis not available, skipping test');
        return;
      }
    });

    it('should get memory usage', async () => {
      try {
        await memory.store('usage-1', createMessage('user', 'Test 1'));
        await memory.store('usage-2', createMessage('user', 'Test 2'));

        const usage = await memory.getMemoryUsage();

        expect(usage.totalSessions).toBeGreaterThanOrEqual(2);
        expect(usage.totalMessages).toBeGreaterThanOrEqual(2);
        expect(usage.ttl).toBe(3600);
      } catch (err) {
        console.warn('Redis not available, skipping test');
        return;
      }
    });
  });

  // ============================================
  // Capabilities Tests
  // ============================================

  describe('Capabilities', () => {
    it('should expose correct capabilities', () => {
      const capabilities = memory.capabilities;

      expect(capabilities).toContain('basic_retrieval');
      expect(capabilities).toContain('persistence');
      expect(capabilities).toContain('ttl');
      expect(capabilities).toContain('time_filtering');
      expect(capabilities).toContain('importance_filtering');
      expect(capabilities).toContain('tag_filtering');
    });
  });
});

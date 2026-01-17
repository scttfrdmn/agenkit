/**
 * Tests for InMemoryMemory.
 *
 * Tests basic storage, retrieval, filtering, LRU eviction, and utilities.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { InMemoryMemory } from '../../memory/in-memory';
import { createMessage } from '../../core/interfaces';

describe('InMemoryMemory', () => {
  let memory: InMemoryMemory;

  beforeEach(() => {
    memory = new InMemoryMemory({ maxSize: 100 });
  });

  // ============================================
  // Basic Store and Retrieve Tests
  // ============================================

  describe('Basic Operations', () => {
    it('should store and retrieve single message', async () => {
      const sessionId = 'session-1';
      const message = createMessage('user', 'Hello');

      await memory.store(sessionId, message);
      const retrieved = await memory.retrieve(sessionId);

      expect(retrieved).toHaveLength(1);
      expect(retrieved[0].content).toBe('Hello');
      expect(retrieved[0].role).toBe('user');
    });

    it('should retrieve messages in LIFO order (most recent first)', async () => {
      const sessionId = 'session-1';

      await memory.store(sessionId, createMessage('user', 'First'));
      await memory.store(sessionId, createMessage('assistant', 'Second'));
      await memory.store(sessionId, createMessage('user', 'Third'));

      const retrieved = await memory.retrieve(sessionId);

      expect(retrieved).toHaveLength(3);
      expect(retrieved[0].content).toBe('Third'); // Most recent
      expect(retrieved[1].content).toBe('Second');
      expect(retrieved[2].content).toBe('First');
    });

    it('should respect limit parameter', async () => {
      const sessionId = 'session-1';

      for (let i = 0; i < 10; i++) {
        await memory.store(sessionId, createMessage('user', `Message ${i}`));
      }

      const retrieved = await memory.retrieve(sessionId, { limit: 5 });

      expect(retrieved).toHaveLength(5);
      expect(retrieved[0].content).toBe('Message 9'); // Most recent
    });

    it('should default to limit of 10', async () => {
      const sessionId = 'session-1';

      for (let i = 0; i < 20; i++) {
        await memory.store(sessionId, createMessage('user', `Message ${i}`));
      }

      const retrieved = await memory.retrieve(sessionId);

      expect(retrieved).toHaveLength(10); // Default limit
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
  // Multi-Session Isolation Tests
  // ============================================

  describe('Session Isolation', () => {
    it('should isolate messages between sessions', async () => {
      await memory.store('session-1', createMessage('user', 'Session 1 message'));
      await memory.store('session-2', createMessage('user', 'Session 2 message'));

      const session1Messages = await memory.retrieve('session-1');
      const session2Messages = await memory.retrieve('session-2');

      expect(session1Messages).toHaveLength(1);
      expect(session1Messages[0].content).toBe('Session 1 message');

      expect(session2Messages).toHaveLength(1);
      expect(session2Messages[0].content).toBe('Session 2 message');
    });

    it('should track multiple sessions independently', async () => {
      for (let i = 1; i <= 3; i++) {
        for (let j = 0; j < i; j++) {
          await memory.store(`session-${i}`, createMessage('user', `Msg ${j}`));
        }
      }

      expect(await memory.retrieve('session-1')).toHaveLength(1);
      expect(await memory.retrieve('session-2')).toHaveLength(2);
      expect(await memory.retrieve('session-3')).toHaveLength(3);
    });
  });

  // ============================================
  // LRU Eviction Tests
  // ============================================

  describe('LRU Eviction', () => {
    it('should evict oldest message when maxSize exceeded', async () => {
      const smallMemory = new InMemoryMemory({ maxSize: 3 });
      const sessionId = 'session-1';

      await smallMemory.store(sessionId, createMessage('user', 'Message 1'));
      await smallMemory.store(sessionId, createMessage('user', 'Message 2'));
      await smallMemory.store(sessionId, createMessage('user', 'Message 3'));

      expect(await smallMemory.retrieve(sessionId)).toHaveLength(3);

      // This should evict Message 1
      await smallMemory.store(sessionId, createMessage('user', 'Message 4'));

      const retrieved = await smallMemory.retrieve(sessionId);
      expect(retrieved).toHaveLength(3);
      expect(retrieved[2].content).toBe('Message 2'); // Message 1 evicted
      expect(retrieved[0].content).toBe('Message 4'); // Most recent
    });

    it('should handle maxSize of 1', async () => {
      const tinyMemory = new InMemoryMemory({ maxSize: 1 });
      const sessionId = 'session-1';

      await tinyMemory.store(sessionId, createMessage('user', 'First'));
      await tinyMemory.store(sessionId, createMessage('user', 'Second'));

      const retrieved = await tinyMemory.retrieve(sessionId);
      expect(retrieved).toHaveLength(1);
      expect(retrieved[0].content).toBe('Second');
    });
  });

  // ============================================
  // Metadata Tests
  // ============================================

  describe('Metadata', () => {
    it('should store and retrieve metadata', async () => {
      const sessionId = 'session-1';
      const message = createMessage('user', 'Test');
      const metadata = { importance: 0.8, tags: ['important', 'urgent'] };

      await memory.store(sessionId, message, metadata);
      const retrieved = await memory.retrieve(sessionId);

      expect(retrieved[0].metadata?.importance).toBe(0.8);
      expect(retrieved[0].metadata?.tags).toEqual(['important', 'urgent']);
    });

    it('should preserve message timestamp', async () => {
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
  // Filtering Tests
  // ============================================

  describe('Filtering', () => {
    beforeEach(async () => {
      const sessionId = 'session-1';

      await memory.store(
        sessionId,
        createMessage('user', 'Low importance'),
        { importance: 0.3, tags: ['low'] },
      );
      await memory.store(
        sessionId,
        createMessage('user', 'Medium importance'),
        { importance: 0.5, tags: ['medium'] },
      );
      await memory.store(
        sessionId,
        createMessage('user', 'High importance'),
        { importance: 0.9, tags: ['high', 'urgent'] },
      );
    });

    it('should filter by importance threshold', async () => {
      const retrieved = await memory.retrieve('session-1', { importanceThreshold: 0.6 });

      expect(retrieved).toHaveLength(1);
      expect(retrieved[0].content).toBe('High importance');
    });

    it('should filter by tags (any match)', async () => {
      const retrieved = await memory.retrieve('session-1', { tags: ['urgent'] });

      expect(retrieved).toHaveLength(1);
      expect(retrieved[0].content).toBe('High importance');
    });

    it('should filter by multiple tags (any match)', async () => {
      const retrieved = await memory.retrieve('session-1', { tags: ['low', 'medium'] });

      expect(retrieved).toHaveLength(2);
      expect(retrieved[0].metadata?.tags).toContain('medium');
      expect(retrieved[1].metadata?.tags).toContain('low');
    });

    it('should filter by time range', async () => {
      const sessionId = 'session-2';
      const now = new Date();
      const past = new Date(now.getTime() - 10000); // 10 seconds ago
      const future = new Date(now.getTime() + 10000); // 10 seconds from now

      await memory.store(sessionId, createMessage('user', 'Recent message'));

      // Should retrieve message within time range
      const retrieved = await memory.retrieve(sessionId, {
        timeRange: [past, future],
      });

      expect(retrieved).toHaveLength(1);

      // Should not retrieve message outside time range
      const futureRange = await memory.retrieve(sessionId, {
        timeRange: [future, new Date(future.getTime() + 10000)],
      });

      expect(futureRange).toHaveLength(0);
    });

    it('should combine multiple filters', async () => {
      const retrieved = await memory.retrieve('session-1', {
        importanceThreshold: 0.4,
        tags: ['medium', 'high'],
      });

      expect(retrieved).toHaveLength(2);
      expect(retrieved[0].metadata?.importance).toBeGreaterThanOrEqual(0.4);
      expect(
        retrieved[0].metadata?.tags?.some((tag: string) => ['medium', 'high'].includes(tag)),
      ).toBe(true);
    });
  });

  // ============================================
  // Summarization Tests
  // ============================================

  describe('Summarization', () => {
    it('should generate basic summary', async () => {
      const sessionId = 'session-1';

      await memory.store(sessionId, createMessage('user', 'Hello'));
      await memory.store(sessionId, createMessage('assistant', 'Hi there'));
      await memory.store(sessionId, createMessage('user', 'How are you?'));

      const summary = await memory.summarize(sessionId);

      expect(summary).toBeDefined();
      expect(summary.length).toBeGreaterThan(0);
      expect(summary).toContain('3 messages');
    });

    it('should handle empty session summarization', async () => {
      const summary = await memory.summarize('empty-session');

      expect(summary).toBeDefined();
      expect(summary).toContain('No messages');
    });
  });

  // ============================================
  // Utility Methods Tests
  // ============================================

  describe('Utilities', () => {
    it('should return session count', async () => {
      const sessionId = 'session-1';

      expect(memory.getSessionCount(sessionId)).toBe(0);

      await memory.store(sessionId, createMessage('user', 'Message 1'));
      await memory.store(sessionId, createMessage('user', 'Message 2'));

      expect(memory.getSessionCount(sessionId)).toBe(2);
    });

    it('should return all session IDs', async () => {
      expect(memory.getAllSessions()).toEqual([]);

      await memory.store('session-1', createMessage('user', 'Test 1'));
      await memory.store('session-2', createMessage('user', 'Test 2'));
      await memory.store('session-3', createMessage('user', 'Test 3'));

      const sessions = memory.getAllSessions();
      expect(sessions).toHaveLength(3);
      expect(sessions).toContain('session-1');
      expect(sessions).toContain('session-2');
      expect(sessions).toContain('session-3');
    });

    it('should return memory usage statistics', async () => {
      await memory.store('session-1', createMessage('user', 'Test 1'));
      await memory.store('session-1', createMessage('user', 'Test 2'));
      await memory.store('session-2', createMessage('user', 'Test 3'));

      const usage = memory.getMemoryUsage();

      expect(usage.totalSessions).toBe(2);
      expect(usage.totalMessages).toBe(3);
      expect(usage.maxSizePerSession).toBe(100);
    });
  });

  // ============================================
  // Capabilities Tests
  // ============================================

  describe('Capabilities', () => {
    it('should report correct capabilities', () => {
      const capabilities = memory.capabilities;

      expect(capabilities).toContain('basic_retrieval');
      expect(capabilities).toContain('time_filtering');
      expect(capabilities).toContain('importance_filtering');
      expect(capabilities).toContain('tag_filtering');
    });
  });

  // ============================================
  // Concurrent Access Tests
  // ============================================

  describe('Concurrent Access', () => {
    it('should handle concurrent stores', async () => {
      const sessionId = 'session-1';
      const promises = [];

      for (let i = 0; i < 10; i++) {
        promises.push(memory.store(sessionId, createMessage('user', `Message ${i}`)));
      }

      await Promise.all(promises);

      const retrieved = await memory.retrieve(sessionId);
      expect(retrieved.length).toBe(10);
    });

    it('should handle concurrent retrieves', async () => {
      const sessionId = 'session-1';

      await memory.store(sessionId, createMessage('user', 'Test'));

      const promises = Array.from({ length: 10 }, () => memory.retrieve(sessionId));
      const results = await Promise.all(promises);

      results.forEach((result) => {
        expect(result).toHaveLength(1);
        expect(result[0].content).toBe('Test');
      });
    });
  });
});

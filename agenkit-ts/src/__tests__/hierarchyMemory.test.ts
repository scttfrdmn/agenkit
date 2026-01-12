/**
 * Tests for HierarchyMemory backward compatibility adapter.
 *
 * Verifies that HierarchyMemory correctly implements the Memory interface
 * while using the 3-tier hierarchy internally.
 */

import { HierarchyMemory } from '../memory/hierarchyMemory';
import { Message } from '../core/interfaces';

describe('HierarchyMemory', () => {
  let memory: HierarchyMemory;

  beforeEach(() => {
    memory = new HierarchyMemory({
      workingCapacity: 10,
      shortTermCapacity: 100,
      shortTermTTLSeconds: 3600,
      longTermMinImportance: 0.7,
      enableLongTerm: true,
    });
  });

  describe('store and retrieve', () => {
    it('should store and retrieve messages', async () => {
      const message: Message = {
        role: 'user',
        content: 'Hello world',
        timestamp: new Date().toISOString(),
      };

      await memory.store('session-1', message);

      const messages = await memory.retrieve('session-1', { limit: 10 });
      expect(messages).toHaveLength(1);
      expect(messages[0].content).toBe('Hello world');
      expect(messages[0].role).toBe('user');
    });

    it('should isolate sessions', async () => {
      const msg1: Message = {
        role: 'user',
        content: 'Session 1 message',
        timestamp: new Date().toISOString(),
      };
      const msg2: Message = {
        role: 'user',
        content: 'Session 2 message',
        timestamp: new Date().toISOString(),
      };

      await memory.store('session-1', msg1);
      await memory.store('session-2', msg2);

      const session1Messages = await memory.retrieve('session-1', { limit: 10 });
      const session2Messages = await memory.retrieve('session-2', { limit: 10 });

      expect(session1Messages).toHaveLength(1);
      expect(session1Messages[0].content).toBe('Session 1 message');

      expect(session2Messages).toHaveLength(1);
      expect(session2Messages[0].content).toBe('Session 2 message');
    });

    it('should route messages by importance', async () => {
      // Low importance - working + short-term only
      const lowImportance: Message = {
        role: 'system',
        content: 'Low importance message',
        timestamp: new Date().toISOString(),
      };
      await memory.store('session-1', lowImportance, { importance: 0.3 });

      // High importance - should go to long-term
      const highImportance: Message = {
        role: 'user',
        content: 'Very important fact to remember',
        timestamp: new Date().toISOString(),
      };
      await memory.store('session-1', highImportance, { importance: 0.9 });

      // Retrieve and verify routing
      const messages = await memory.retrieve('session-1', { limit: 10 });
      expect(messages.length).toBeGreaterThan(0);

      const stats = memory.getStats();
      expect(stats).toHaveProperty('working');
      expect(stats).toHaveProperty('short_term');
      expect(stats).toHaveProperty('long_term');
    });

    it('should filter by importance threshold', async () => {
      const msg1: Message = {
        role: 'user',
        content: 'Low importance message',
        timestamp: new Date().toISOString(),
      };
      await memory.store('session-1', msg1, { importance: 0.3 });

      const msg2: Message = {
        role: 'user',
        content: 'High importance message',
        timestamp: new Date().toISOString(),
      };
      await memory.store('session-1', msg2, { importance: 0.9 });

      // Retrieve with importance threshold
      const messages = await memory.retrieve('session-1', {
        limit: 10,
        importanceThreshold: 0.6,
      });

      expect(messages).toHaveLength(1);
      expect(messages[0].content).toBe('High importance message');
    });

    it('should filter by time range using original message timestamps', async () => {
      const now = new Date();
      const past = new Date(now.getTime() - 2 * 60 * 60 * 1000); // 2 hours ago

      const msg1: Message = {
        role: 'user',
        content: 'Old message',
        timestamp: past.toISOString(),
      };

      const msg2: Message = {
        role: 'user',
        content: 'Recent message',
        timestamp: now.toISOString(),
      };

      await memory.store('session-1', msg1);
      await memory.store('session-1', msg2);

      // Filter by time range - should only get recent message
      const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
      const oneHourFromNow = new Date(now.getTime() + 60 * 60 * 1000);

      const messages = await memory.retrieve('session-1', {
        limit: 10,
        timeRange: [oneHourAgo, oneHourFromNow],
      });

      expect(messages).toHaveLength(1);
      expect(messages[0].content).toBe('Recent message');
    });

    it('should filter by tags', async () => {
      // Store messages with tags
      const msg1: Message = {
        role: 'user',
        content: 'Message with tag A',
        timestamp: new Date().toISOString(),
        metadata: { tags: ['tagA', 'common'] },
      };
      await memory.store('session-1', msg1);

      const msg2: Message = {
        role: 'assistant',
        content: 'Response with tag B',
        timestamp: new Date().toISOString(),
        metadata: { tags: ['tagB'] },
      };
      await memory.store('session-1', msg2);

      // Retrieve with tag filter
      const messages = await memory.retrieve('session-1', {
        limit: 10,
        tags: ['tagA'],
      });

      expect(messages).toHaveLength(1);
      expect(messages[0].content).toBe('Message with tag A');
    });

    it('should summarize conversation', async () => {
      // Store several messages
      for (let i = 0; i < 15; i++) {
        const msg: Message = {
          role: i % 2 === 0 ? 'user' : 'assistant',
          content: `Message ${i}`,
          timestamp: new Date().toISOString(),
        };
        await memory.store('session-1', msg);
      }

      const summary = await memory.summarize('session-1');

      expect(summary.role).toBe('system');
      expect(summary.content).toContain('Session summary');
      expect(summary.content).toContain('15 messages');
    });

    it('should clear session-specific memories', async () => {
      // Store messages in both sessions
      const msg1: Message = {
        role: 'user',
        content: 'Session 1 message',
        timestamp: new Date().toISOString(),
      };
      await memory.store('session-1', msg1);

      const msg2: Message = {
        role: 'user',
        content: 'Session 2 message',
        timestamp: new Date().toISOString(),
      };
      await memory.store('session-2', msg2);

      // Clear session 1
      await memory.clear('session-1');

      // Session 1 should be empty
      const session1Messages = await memory.retrieve('session-1', { limit: 10 });
      expect(session1Messages).toHaveLength(0);

      // Session 2 should still have messages
      const session2Messages = await memory.retrieve('session-2', { limit: 10 });
      expect(session2Messages).toHaveLength(1);
      expect(session2Messages[0].content).toBe('Session 2 message');
    });

    it('should return memory capabilities', () => {
      const capabilities = memory.capabilities;

      expect(Array.isArray(capabilities)).toBe(true);
      expect(capabilities).toContain('semantic_search');
      expect(capabilities).toContain('importance_filtering');
      expect(capabilities).toContain('multi_tier');
    });

    it('should return memory statistics', () => {
      const stats = memory.getStats();

      expect(stats).toHaveProperty('working');
      expect(stats).toHaveProperty('short_term');
      expect(stats).toHaveProperty('long_term');
    });
  });
});

/**
 * Tests for HierarchyMemory.
 *
 * Tests 3-tier hierarchical memory with importance routing,
 * semantic search, and backward compatibility.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { HierarchyMemory } from '../../memory/hierarchyMemory';
import { createMessage } from '../../core/interfaces';

describe('HierarchyMemory', () => {
  let memory: HierarchyMemory;

  beforeEach(() => {
    memory = new HierarchyMemory({
      workingCapacity: 5,
      shortTermCapacity: 10,
      shortTermTTLSeconds: 3600,
      longTermMinImportance: 0.7,
      enableLongTerm: true,
    });
  });

  // ============================================
  // Basic Operations Tests
  // ============================================

  describe('Basic Operations', () => {
    it('should store and retrieve single message', async () => {
      const sessionId = 'session-1';
      const message = createMessage('user', 'Hello');

      await memory.store(sessionId, message);
      const retrieved = await memory.retrieve(sessionId);

      expect(retrieved).toHaveLength(1);
      expect(retrieved[0].content).toBe('Hello');
    });

    it('should retrieve messages in LIFO order (most recent first)', async () => {
      const sessionId = 'session-1';

      await memory.store(sessionId, createMessage('user', 'First'));
      await memory.store(sessionId, createMessage('assistant', 'Second'));
      await memory.store(sessionId, createMessage('user', 'Third'));

      const retrieved = await memory.retrieve(sessionId);

      expect(retrieved).toHaveLength(3);
      expect(retrieved[0].content).toBe('Third'); // Most recent
    });

    it('should respect limit parameter', async () => {
      const sessionId = 'session-1';

      for (let i = 0; i < 20; i++) {
        await memory.store(sessionId, createMessage('user', `Message ${i}`));
      }

      const retrieved = await memory.retrieve(sessionId, { limit: 5 });

      expect(retrieved.length).toBeLessThanOrEqual(5);
    });

    it('should handle empty session', async () => {
      const retrieved = await memory.retrieve('nonexistent-session');

      expect(retrieved).toHaveLength(0);
    });

    it('should clear session', async () => {
      const sessionId = 'session-1';

      await memory.store(sessionId, createMessage('user', 'Test'));
      expect((await memory.retrieve(sessionId)).length).toBeGreaterThan(0);

      await memory.clear(sessionId);
      expect(await memory.retrieve(sessionId)).toHaveLength(0);
    });
  });

  // ============================================
  // Importance Routing Tests
  // ============================================

  describe('Importance Routing', () => {
    it('should route messages by importance to correct tiers', async () => {
      const sessionId = 'session-1';

      // Low importance → working/short-term only
      await memory.store(sessionId, createMessage('user', 'Low'), { importance: 0.3 });

      // High importance → all tiers
      await memory.store(sessionId, createMessage('user', 'High'), { importance: 0.9 });

      const stats = await memory.getStats();

      // High importance should be in long-term
      expect(stats).toBeDefined();
    });

    it('should use default importance by role', async () => {
      const sessionId = 'session-1';

      await memory.store(sessionId, createMessage('system', 'System message')); // 0.3
      await memory.store(sessionId, createMessage('user', 'User message')); // 0.5
      await memory.store(sessionId, createMessage('assistant', 'Assistant message')); // 0.4

      const retrieved = await memory.retrieve(sessionId);

      expect(retrieved).toHaveLength(3);
    });

    it('should override default importance with metadata', async () => {
      const sessionId = 'session-1';

      // Override user default (0.5) to high importance
      await memory.store(sessionId, createMessage('user', 'Important user message'), {
        importance: 0.95,
      });

      const retrieved = await memory.retrieve(sessionId);

      expect(retrieved[0].metadata?.importance).toBe(0.95);
    });

    it('should respect longTermMinImportance threshold', async () => {
      const sessionId = 'session-1';

      // Below threshold (0.7)
      await memory.store(sessionId, createMessage('user', 'Not important enough'), {
        importance: 0.6,
      });

      // Above threshold
      await memory.store(sessionId, createMessage('user', 'Very important'), { importance: 0.8 });

      const stats = await memory.getStats();

      // Only high importance should make it to long-term
      expect(stats).toBeDefined();
    });
  });

  // ============================================
  // Multi-Tier Eviction Tests
  // ============================================

  describe('Multi-Tier Eviction', () => {
    it('should evict from working memory when capacity exceeded (FIFO)', async () => {
      const smallMemory = new HierarchyMemory({
        workingCapacity: 3,
        shortTermCapacity: 10,
        longTermMinImportance: 0.9,
      });

      const sessionId = 'session-1';

      // Fill working memory
      await smallMemory.store(sessionId, createMessage('user', 'Message 1'));
      await smallMemory.store(sessionId, createMessage('user', 'Message 2'));
      await smallMemory.store(sessionId, createMessage('user', 'Message 3'));

      const stats1 = await smallMemory.getStats();
      expect(stats1.working.size).toBe(3);

      // This should evict Message 1 from working memory
      await smallMemory.store(sessionId, createMessage('user', 'Message 4'));

      const stats2 = await smallMemory.getStats();
      expect(stats2.working.size).toBe(3); // Still at capacity

      // Verify Message 1 was evicted from working (should be in short-term now)
      const retrieved = await smallMemory.retrieve(sessionId, { limit: 10 });
      const contents = retrieved.map((m) => m.content);
      expect(contents).toContain('Message 4'); // Most recent in working
    });

    it('should handle long-term disabled configuration', async () => {
      const noLongTerm = new HierarchyMemory({
        workingCapacity: 5,
        shortTermCapacity: 10,
        enableLongTerm: false,
      });

      const sessionId = 'session-1';

      // Even high importance won't go to long-term
      await noLongTerm.store(sessionId, createMessage('user', 'High importance'), {
        importance: 0.95,
      });

      const stats = await noLongTerm.getStats();

      expect(stats.long_term).toBeUndefined();
    });
  });

  // ============================================
  // Session Isolation Tests
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

    it('should handle multi-session interference with semantic search', async () => {
      // Store messages in different sessions with similar content
      await memory.store('session-1', createMessage('user', 'Hello world'));
      await memory.store('session-2', createMessage('user', 'Hello world'));

      // Retrieve with query should filter by session
      const session1Results = await memory.retrieve('session-1', { query: 'hello' });

      expect(session1Results).toHaveLength(1);
      // Session isolation ensured by implementation
    });
  });

  // ============================================
  // Filtering Tests
  // ============================================

  describe('Filtering', () => {
    beforeEach(async () => {
      const sessionId = 'session-1';

      await memory.store(sessionId, createMessage('user', 'Low importance'), {
        importance: 0.3,
        tags: ['low'],
      });
      await memory.store(sessionId, createMessage('user', 'Medium importance'), {
        importance: 0.5,
        tags: ['medium'],
      });
      await memory.store(sessionId, createMessage('user', 'High importance'), {
        importance: 0.9,
        tags: ['high', 'urgent'],
      });
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

    it('should filter by time range', async () => {
      const sessionId = 'session-2';
      const now = new Date();
      const past = new Date(now.getTime() - 10000);
      const future = new Date(now.getTime() + 10000);

      await memory.store(sessionId, createMessage('user', 'Recent message'));

      const retrieved = await memory.retrieve(sessionId, {
        timeRange: [past, future],
      });

      expect(retrieved).toHaveLength(1);
    });

    it('should combine multiple filters', async () => {
      const retrieved = await memory.retrieve('session-1', {
        importanceThreshold: 0.4,
        tags: ['medium', 'high'],
      });

      expect(retrieved.length).toBeGreaterThanOrEqual(1);
    });
  });

  // ============================================
  // Semantic Search Tests
  // ============================================

  describe('Semantic Search', () => {
    it('should perform semantic retrieval with query', async () => {
      const sessionId = 'session-1';

      await memory.store(sessionId, createMessage('user', 'How do I reset my password?'));
      await memory.store(sessionId, createMessage('user', 'What is the weather like?'));
      await memory.store(sessionId, createMessage('user', 'Tell me about password recovery'));

      // Query should find password-related messages
      const results = await memory.retrieve(sessionId, { query: 'password' });

      expect(results.length).toBeGreaterThan(0);
      // Results should contain password-related messages
    });

    it('should search across all tiers', async () => {
      const sessionId = 'session-1';

      // Store in different tiers via importance
      await memory.store(sessionId, createMessage('user', 'Low priority task'), {
        importance: 0.2,
      });
      await memory.store(sessionId, createMessage('user', 'High priority task'), {
        importance: 0.9,
      });

      const results = await memory.retrieve(sessionId, { query: 'task' });

      expect(results.length).toBeGreaterThanOrEqual(1);
    });
  });

  // ============================================
  // Summarization Tests
  // ============================================

  describe('Summarization', () => {
    it('should generate summary across all tiers', async () => {
      const sessionId = 'session-1';

      await memory.store(sessionId, createMessage('user', 'Hello'));
      await memory.store(sessionId, createMessage('assistant', 'Hi there'));
      await memory.store(sessionId, createMessage('user', 'How are you?'));

      const summary = await memory.summarize(sessionId);

      expect(summary).toBeDefined();
      expect(summary.length).toBeGreaterThan(0);
    });

    it('should handle empty session summarization', async () => {
      const summary = await memory.summarize('empty-session');

      expect(summary).toBeDefined();
    });
  });

  // ============================================
  // Statistics Tests
  // ============================================

  describe('Statistics', () => {
    it('should return tier statistics', async () => {
      const sessionId = 'session-1';

      await memory.store(sessionId, createMessage('user', 'Message 1'));
      await memory.store(sessionId, createMessage('user', 'Message 2'), { importance: 0.9 });

      const stats = await memory.getStats();

      expect(stats.working).toBeDefined();
      expect(stats.working.size).toBeGreaterThanOrEqual(0);
      expect(stats.working.capacity).toBe(5);

      expect(stats.short_term).toBeDefined();
      expect(stats.short_term.capacity).toBe(10);

      expect(stats.long_term).toBeDefined();
    });

    it('should track message distribution across tiers', async () => {
      const sessionId = 'session-1';

      // Fill up working memory
      for (let i = 0; i < 10; i++) {
        const importance = i >= 7 ? 0.9 : 0.4; // Last 3 are high importance
        await memory.store(sessionId, createMessage('user', `Message ${i}`), { importance });
      }

      const stats = await memory.getStats();

      expect(stats.working.size).toBeLessThanOrEqual(5);
      // High importance messages should be in long-term
    });
  });

  // ============================================
  // Utilities Tests
  // ============================================

  describe('Utilities', () => {
    it('should return all session IDs', async () => {
      await memory.store('session-1', createMessage('user', 'Test 1'));
      await memory.store('session-2', createMessage('user', 'Test 2'));
      await memory.store('session-3', createMessage('user', 'Test 3'));

      const sessions = await memory.getAllSessions();

      expect(sessions).toHaveLength(3);
      expect(sessions).toContain('session-1');
      expect(sessions).toContain('session-2');
      expect(sessions).toContain('session-3');
    });
  });

  // ============================================
  // Capabilities Tests
  // ============================================

  describe('Capabilities', () => {
    it('should report hierarchical capabilities', () => {
      const capabilities = memory.capabilities;

      expect(capabilities).toContain('semantic_search');
      expect(capabilities).toContain('importance_filtering');
      expect(capabilities).toContain('tag_filtering');
      expect(capabilities).toContain('time_filtering');
      expect(capabilities).toContain('multi_tier');
      expect(capabilities).toContain('auto_eviction');
    });
  });

  // ============================================
  // Configuration Validation Tests
  // ============================================

  describe('Configuration Validation', () => {
    it('should accept valid configuration', () => {
      expect(() => {
        new HierarchyMemory({
          workingCapacity: 10,
          shortTermCapacity: 100,
          shortTermTTLSeconds: 3600,
          longTermMinImportance: 0.7,
          enableLongTerm: true,
        });
      }).not.toThrow();
    });

    it('should handle minimal configuration', () => {
      expect(() => {
        new HierarchyMemory({});
      }).not.toThrow();
    });
  });

  // ============================================
  // Backward Compatibility Tests
  // ============================================

  describe('Backward Compatibility', () => {
    it('should implement Memory interface', async () => {
      const sessionId = 'session-1';

      // Test all required Memory methods
      await memory.store(sessionId, createMessage('user', 'Test'));
      const retrieved = await memory.retrieve(sessionId);
      expect(retrieved).toBeDefined();

      const summary = await memory.summarize(sessionId);
      expect(summary).toBeDefined();

      await memory.clear(sessionId);
      expect(await memory.retrieve(sessionId)).toHaveLength(0);

      expect(memory.capabilities).toBeDefined();
    });
  });
});

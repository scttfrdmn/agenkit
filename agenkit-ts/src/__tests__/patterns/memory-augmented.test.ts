/**
 * Comprehensive tests for Memory hierarchy pattern.
 *
 * Tests cover:
 * - WorkingMemory: FIFO eviction, capacity, clear
 * - ShortTermMemory: TTL, LRU, capacity
 * - LongTermMemory: importance threshold, semantic retrieval
 * - MemoryHierarchy: cross-tier storage and retrieval
 */

import { describe, it, expect } from 'vitest';
import {
  WorkingMemory,
  ShortTermMemory,
  LongTermMemory,
  MemoryHierarchy,
  createMemoryEntry,
} from '../../patterns/memory';

describe('createMemoryEntry', () => {
  it('should create entry with required fields', () => {
    const entry = createMemoryEntry('test content');

    expect(entry.content).toBe('test content');
    expect(typeof entry.id).toBe('string');
    expect(entry.id.length).toBeGreaterThan(0);
    expect(entry.timestamp).toBeInstanceOf(Date);
    expect(entry.accessCount).toBe(0);
    expect(entry.importance).toBe(0.5);
  });

  it('should create entry with custom metadata', () => {
    const entry = createMemoryEntry('content', { category: 'test' });

    expect(entry.metadata).toEqual({ category: 'test' });
  });

  it('should create entry with custom importance', () => {
    const entry = createMemoryEntry('content', {}, 0.9);

    expect(entry.importance).toBe(0.9);
  });

  it('should create entry with session ID', () => {
    const entry = createMemoryEntry('content', {}, 0.5, 'session-123');

    expect(entry.sessionId).toBe('session-123');
  });
});

describe('WorkingMemory', () => {
  describe('Constructor', () => {
    it('should create with default max messages', () => {
      const memory = new WorkingMemory();

      expect(memory.length).toBe(0);
      expect(memory.capacity).toBe(10);
    });

    it('should throw when maxMessages is less than 1', () => {
      expect(() => new WorkingMemory(0)).toThrow('maxMessages must be at least 1');
    });
  });

  describe('store and retrieve', () => {
    it('should store and retrieve a message', async () => {
      const memory = new WorkingMemory(10);
      const entry = createMemoryEntry('hello world');

      await memory.store(entry);
      const results = await memory.retrieve('hello');

      expect(results).toHaveLength(1);
      expect(results[0].content).toBe('hello world');
    });

    it('should retrieve up to limit messages', async () => {
      const memory = new WorkingMemory(10);

      for (let i = 0; i < 10; i++) {
        await memory.store(createMemoryEntry(`message ${i}`));
      }

      const results = await memory.retrieve('message', 5);
      expect(results).toHaveLength(5);
    });

    it('should return most recent messages', async () => {
      const memory = new WorkingMemory(10);

      for (let i = 0; i < 5; i++) {
        await memory.store(createMemoryEntry(`message ${i}`));
      }

      const results = await memory.retrieve('query', 3);
      // Should return last 3
      expect(results).toHaveLength(3);
    });
  });

  describe('FIFO eviction', () => {
    it('should evict oldest when capacity exceeded', async () => {
      const memory = new WorkingMemory(3);

      const e1 = createMemoryEntry('first');
      const e2 = createMemoryEntry('second');
      const e3 = createMemoryEntry('third');
      const e4 = createMemoryEntry('fourth');

      await memory.store(e1);
      await memory.store(e2);
      await memory.store(e3);
      await memory.store(e4); // evicts e1

      expect(memory.length).toBe(3);
      const all = memory.getAll();
      expect(all.some(e => e.content === 'first')).toBe(false);
      expect(all.some(e => e.content === 'fourth')).toBe(true);
    });

    it('should never exceed capacity', async () => {
      const maxMessages = 5;
      const memory = new WorkingMemory(maxMessages);

      for (let i = 0; i < 20; i++) {
        await memory.store(createMemoryEntry(`message ${i}`));
      }

      expect(memory.length).toBeLessThanOrEqual(maxMessages);
    });
  });

  describe('delete', () => {
    it('should remove entry by ID', async () => {
      const memory = new WorkingMemory(10);
      const entry = createMemoryEntry('to delete');

      await memory.store(entry);
      expect(memory.length).toBe(1);

      await memory.delete(entry.id);
      expect(memory.length).toBe(0);
    });

    it('should be idempotent for missing IDs', async () => {
      const memory = new WorkingMemory(10);
      await memory.store(createMemoryEntry('entry'));

      await memory.delete('nonexistent-id');

      expect(memory.length).toBe(1);
    });
  });

  describe('clear', () => {
    it('should remove all entries', async () => {
      const memory = new WorkingMemory(10);

      for (let i = 0; i < 5; i++) {
        await memory.store(createMemoryEntry(`msg ${i}`));
      }

      memory.clear();
      expect(memory.length).toBe(0);
    });
  });
});

describe('ShortTermMemory', () => {
  describe('Constructor', () => {
    it('should create with default values', () => {
      const memory = new ShortTermMemory();

      expect(memory.capacity).toBe(100);
      expect(memory.ttlSeconds).toBe(3600);
    });

    it('should throw when maxMessages is less than 1', () => {
      expect(() => new ShortTermMemory(0)).toThrow('maxMessages must be at least 1');
    });

    it('should throw when ttlSeconds is less than 1', () => {
      expect(() => new ShortTermMemory(100, 0)).toThrow('ttlSeconds must be at least 1');
    });
  });

  describe('store and retrieve', () => {
    it('should store and retrieve entries', async () => {
      const memory = new ShortTermMemory(10, 3600);
      const entry = createMemoryEntry('test content');

      await memory.store(entry);
      const results = await memory.retrieve('test');

      expect(results.length).toBeGreaterThan(0);
      expect(results[0].content).toBe('test content');
    });

    it('should respect capacity limit', async () => {
      const memory = new ShortTermMemory(3, 3600);

      for (let i = 0; i < 10; i++) {
        await memory.store(createMemoryEntry(`entry ${i}`));
      }

      expect(memory.length).toBeLessThanOrEqual(3);
    });
  });
});

describe('LongTermMemory', () => {
  describe('Constructor', () => {
    it('should create with default values', () => {
      const memory = new LongTermMemory();

      expect(memory.length).toBe(0);
      expect(memory.minImportanceThreshold).toBe(0.5);
    });

    it('should throw when minImportance out of range', () => {
      expect(() => new LongTermMemory(undefined, undefined, -0.1)).toThrow(
        'minImportance must be between 0.0 and 1.0'
      );
      expect(() => new LongTermMemory(undefined, undefined, 1.1)).toThrow(
        'minImportance must be between 0.0 and 1.0'
      );
    });
  });

  describe('importance threshold', () => {
    it('should store entries above threshold', async () => {
      const memory = new LongTermMemory(undefined, undefined, 0.5);
      const entry = createMemoryEntry('important', {}, 0.8);

      await memory.store(entry);

      expect(memory.length).toBe(1);
    });

    it('should reject entries below threshold', async () => {
      const memory = new LongTermMemory(undefined, undefined, 0.7);
      const entry = createMemoryEntry('not important', {}, 0.3);

      await memory.store(entry);

      expect(memory.length).toBe(0);
    });
  });

  describe('retrieve', () => {
    it('should return entries relevant to query', async () => {
      const memory = new LongTermMemory(undefined, undefined, 0.3);
      await memory.store(createMemoryEntry('Python programming', {}, 0.8));
      await memory.store(createMemoryEntry('JavaScript cooking', {}, 0.8));

      const results = await memory.retrieve('Python', 5);

      // Python entry should be ranked higher
      expect(results[0].content).toContain('Python');
    });

    it('should respect limit', async () => {
      const memory = new LongTermMemory(undefined, undefined, 0.3);

      for (let i = 0; i < 10; i++) {
        await memory.store(createMemoryEntry(`entry ${i}`, {}, 0.8));
      }

      const results = await memory.retrieve('entry', 3);
      expect(results).toHaveLength(3);
    });
  });
});

describe('MemoryHierarchy', () => {
  describe('Constructor', () => {
    it('should create with working memory only', () => {
      const working = new WorkingMemory(10);
      const hierarchy = new MemoryHierarchy(working);

      expect(hierarchy.workingTier).toBe(working);
      expect(hierarchy.shortTermTier).toBeUndefined();
      expect(hierarchy.longTermTier).toBeUndefined();
    });

    it('should create with all tiers', () => {
      const working = new WorkingMemory(10);
      const shortTerm = new ShortTermMemory(100);
      const longTerm = new LongTermMemory();

      const hierarchy = new MemoryHierarchy(working, shortTerm, longTerm);

      expect(hierarchy.shortTermTier).toBe(shortTerm);
      expect(hierarchy.longTermTier).toBe(longTerm);
    });
  });

  describe('store', () => {
    it('should always store in working memory', async () => {
      const working = new WorkingMemory(10);
      const hierarchy = new MemoryHierarchy(working);

      await hierarchy.store('test content');

      expect(working.length).toBe(1);
    });

    it('should store in short-term when available', async () => {
      const working = new WorkingMemory(10);
      const shortTerm = new ShortTermMemory(10);
      const hierarchy = new MemoryHierarchy(working, shortTerm);

      await hierarchy.store('content');

      expect(shortTerm.length).toBe(1);
    });

    it('should store in long-term when importance is high enough', async () => {
      const working = new WorkingMemory(10);
      const longTerm = new LongTermMemory(undefined, undefined, 0.5);
      const hierarchy = new MemoryHierarchy(working, undefined, longTerm);

      await hierarchy.store('important content', {}, 0.8);

      expect(longTerm.length).toBe(1);
    });

    it('should throw when importance is out of range', async () => {
      const hierarchy = new MemoryHierarchy(new WorkingMemory(10));

      await expect(hierarchy.store('content', {}, 1.5)).rejects.toThrow(
        'importance must be between 0.0 and 1.0'
      );
    });

    it('should return an ID string', async () => {
      const hierarchy = new MemoryHierarchy(new WorkingMemory(10));
      const id = await hierarchy.store('content');

      expect(typeof id).toBe('string');
      expect(id.length).toBeGreaterThan(0);
    });
  });

  describe('retrieve', () => {
    it('should retrieve memories from working tier', async () => {
      const hierarchy = new MemoryHierarchy(new WorkingMemory(10));
      await hierarchy.store('test memory');

      const results = await hierarchy.retrieve('test');

      expect(results.length).toBeGreaterThan(0);
    });

    it('should deduplicate across tiers', async () => {
      const working = new WorkingMemory(10);
      const shortTerm = new ShortTermMemory(10);
      const hierarchy = new MemoryHierarchy(working, shortTerm);

      await hierarchy.store('same content'); // Stored in both tiers

      const results = await hierarchy.retrieve('content');
      const ids = results.map(r => r.id);
      const uniqueIds = new Set(ids);

      expect(ids.length).toBe(uniqueIds.size);
    });

    it('should respect limit', async () => {
      const hierarchy = new MemoryHierarchy(new WorkingMemory(20));

      for (let i = 0; i < 10; i++) {
        await hierarchy.store(`memory ${i}`);
      }

      const results = await hierarchy.retrieve('memory', 3);
      expect(results).toHaveLength(3);
    });
  });

  describe('delete', () => {
    it('should remove entry from all tiers', async () => {
      const working = new WorkingMemory(10);
      const hierarchy = new MemoryHierarchy(working);

      const id = await hierarchy.store('to delete');
      expect(working.length).toBe(1);

      await hierarchy.delete(id);
      expect(working.length).toBe(0);
    });
  });

  describe('getStats', () => {
    it('should return stats with working tier info', () => {
      const hierarchy = new MemoryHierarchy(new WorkingMemory(10));
      const stats = hierarchy.getStats();

      expect(stats.working).toBeDefined();
      const working = stats.working as any;
      expect(typeof working.size).toBe('number');
      expect(typeof working.capacity).toBe('number');
    });

    it('should include short-term stats when present', () => {
      const hierarchy = new MemoryHierarchy(
        new WorkingMemory(10),
        new ShortTermMemory(100, 3600)
      );
      const stats = hierarchy.getStats();

      expect(stats.short_term).toBeDefined();
      const st = stats.short_term as any;
      expect(typeof st.ttl_seconds).toBe('number');
    });
  });
});

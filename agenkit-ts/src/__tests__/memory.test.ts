/**
 * Tests for Memory Hierarchy pattern.
 */

import {
  MemoryEntry,
  createMemoryEntry,
  WorkingMemory,
  ShortTermMemory,
  LongTermMemory,
  MemoryHierarchy,
} from '../patterns/memory';

describe('MemoryEntry', () => {
  it('should create a memory entry', () => {
    const entry = createMemoryEntry('Test content', { key: 'value' }, 0.7, 'session-1');

    expect(entry.content).toBe('Test content');
    expect(entry.metadata).toEqual({ key: 'value' });
    expect(entry.importance).toBe(0.7);
    expect(entry.sessionId).toBe('session-1');
    expect(entry.accessCount).toBe(0);
    expect(entry.timestamp).toBeInstanceOf(Date);
    expect(entry.id).toBeTruthy();
  });

  it('should create entry with default values', () => {
    const entry = createMemoryEntry('Content');

    expect(entry.content).toBe('Content');
    expect(entry.metadata).toEqual({});
    expect(entry.importance).toBe(0.5);
    expect(entry.sessionId).toBeUndefined();
  });
});

describe('WorkingMemory', () => {
  describe('Configuration', () => {
    it('should create with default capacity', () => {
      const memory = new WorkingMemory();

      expect(memory.length).toBe(0);
    });

    it('should create with custom capacity', () => {
      const memory = new WorkingMemory(20);

      expect(memory.length).toBe(0);
    });

    it('should throw if maxMessages < 1', () => {
      expect(() => new WorkingMemory(0)).toThrow('maxMessages must be at least 1');
    });
  });

  describe('Storage', () => {
    it('should store entries', async () => {
      const memory = new WorkingMemory(10);
      const entry = createMemoryEntry('Test');

      await memory.store(entry);

      expect(memory.length).toBe(1);
    });

    it('should evict oldest when at capacity', async () => {
      const memory = new WorkingMemory(3);

      const entry1 = createMemoryEntry('Entry 1');
      const entry2 = createMemoryEntry('Entry 2');
      const entry3 = createMemoryEntry('Entry 3');
      const entry4 = createMemoryEntry('Entry 4');

      await memory.store(entry1);
      await memory.store(entry2);
      await memory.store(entry3);
      await memory.store(entry4);

      expect(memory.length).toBe(3);

      const all = memory.getAll();
      expect(all[0].content).toBe('Entry 2'); // Entry 1 evicted
      expect(all[2].content).toBe('Entry 4');
    });
  });

  describe('Retrieval', () => {
    it('should retrieve recent entries', async () => {
      const memory = new WorkingMemory(10);

      await memory.store(createMemoryEntry('Entry 1'));
      await memory.store(createMemoryEntry('Entry 2'));
      await memory.store(createMemoryEntry('Entry 3'));

      const results = await memory.retrieve('', 2);

      expect(results.length).toBe(2);
      expect(results[1].content).toBe('Entry 3');
    });

    it('should return all if limit exceeds size', async () => {
      const memory = new WorkingMemory(10);

      await memory.store(createMemoryEntry('Entry 1'));
      await memory.store(createMemoryEntry('Entry 2'));

      const results = await memory.retrieve('', 10);

      expect(results.length).toBe(2);
    });
  });

  describe('Deletion', () => {
    it('should delete specific entry', async () => {
      const memory = new WorkingMemory(10);
      const entry = createMemoryEntry('To delete');

      await memory.store(entry);
      expect(memory.length).toBe(1);

      await memory.delete(entry.id);
      expect(memory.length).toBe(0);
    });
  });

  describe('Utilities', () => {
    it('should get all entries', async () => {
      const memory = new WorkingMemory(10);

      await memory.store(createMemoryEntry('Entry 1'));
      await memory.store(createMemoryEntry('Entry 2'));

      const all = memory.getAll();

      expect(all.length).toBe(2);
    });

    it('should clear all entries', async () => {
      const memory = new WorkingMemory(10);

      await memory.store(createMemoryEntry('Entry 1'));
      await memory.store(createMemoryEntry('Entry 2'));

      memory.clear();

      expect(memory.length).toBe(0);
    });
  });
});

describe('ShortTermMemory', () => {
  describe('Configuration', () => {
    it('should create with default values', () => {
      const memory = new ShortTermMemory();

      expect(memory.length).toBe(0);
    });

    it('should create with custom values', () => {
      const memory = new ShortTermMemory(50, 1800);

      expect(memory.length).toBe(0);
    });

    it('should throw if maxMessages < 1', () => {
      expect(() => new ShortTermMemory(0)).toThrow('maxMessages must be at least 1');
    });

    it('should throw if ttlSeconds < 1', () => {
      expect(() => new ShortTermMemory(100, 0)).toThrow('ttlSeconds must be at least 1');
    });
  });

  describe('Storage and TTL', () => {
    it('should store entries', async () => {
      const memory = new ShortTermMemory(100, 3600);
      const entry = createMemoryEntry('Test');

      await memory.store(entry);

      expect(memory.length).toBe(1);
    });

    it('should evict LRU when at capacity', async () => {
      const memory = new ShortTermMemory(2, 3600);

      const entry1 = createMemoryEntry('Entry 1');
      const entry2 = createMemoryEntry('Entry 2');
      const entry3 = createMemoryEntry('Entry 3');

      await memory.store(entry1);
      await memory.store(entry2);
      await memory.store(entry3);

      expect(memory.length).toBe(2);
    });

    it('should clean expired entries', async () => {
      const memory = new ShortTermMemory(100, 1); // 1 second TTL

      const entry = createMemoryEntry('Test');
      entry.timestamp = new Date(Date.now() - 2000); // 2 seconds ago

      await memory.store(entry);

      // Trigger cleanup via retrieve
      await memory.retrieve('', 10);

      expect(memory.length).toBe(0);
    });
  });

  describe('Retrieval', () => {
    it('should retrieve by recency', async () => {
      const memory = new ShortTermMemory(100, 3600);

      const entry1 = createMemoryEntry('Old');
      entry1.timestamp = new Date(Date.now() - 10000);
      const entry2 = createMemoryEntry('New');

      await memory.store(entry1);
      await memory.store(entry2);

      const results = await memory.retrieve('', 10);

      expect(results[0].content).toBe('New'); // Most recent first
    });

    it('should update access count and time', async () => {
      const memory = new ShortTermMemory(100, 3600);
      const entry = createMemoryEntry('Test');

      await memory.store(entry);

      const results = await memory.retrieve('', 10);

      expect(results[0].accessCount).toBe(1);
      expect(results[0].lastAccessed).toBeInstanceOf(Date);
    });

    it('should limit results', async () => {
      const memory = new ShortTermMemory(100, 3600);

      await memory.store(createMemoryEntry('Entry 1'));
      await memory.store(createMemoryEntry('Entry 2'));
      await memory.store(createMemoryEntry('Entry 3'));

      const results = await memory.retrieve('', 2);

      expect(results.length).toBe(2);
    });
  });

  describe('Deletion', () => {
    it('should delete specific entry', async () => {
      const memory = new ShortTermMemory(100, 3600);
      const entry = createMemoryEntry('To delete');

      await memory.store(entry);
      expect(memory.length).toBe(1);

      await memory.delete(entry.id);
      expect(memory.length).toBe(0);
    });
  });
});

describe('LongTermMemory', () => {
  describe('Configuration', () => {
    it('should create with default values', () => {
      const memory = new LongTermMemory();

      expect(memory.length).toBe(0);
    });

    it('should create with custom values', () => {
      const memory = new LongTermMemory(undefined, undefined, 0.7);

      expect(memory.length).toBe(0);
    });

    it('should throw if minImportance out of range', () => {
      expect(() => new LongTermMemory(undefined, undefined, 1.5)).toThrow(
        'minImportance must be between 0.0 and 1.0'
      );
    });

    it('should accept Map as storage backend', () => {
      const storage = new Map<string, MemoryEntry>();
      const memory = new LongTermMemory(storage);

      expect(memory.length).toBe(0);
    });

    it('should accept Record as storage backend', () => {
      const storage = {};
      const memory = new LongTermMemory(storage);

      expect(memory.length).toBe(0);
    });
  });

  describe('Importance Filtering', () => {
    it('should only store important memories', async () => {
      const memory = new LongTermMemory(undefined, undefined, 0.7);

      const unimportant = createMemoryEntry('Not important', {}, 0.5);
      const important = createMemoryEntry('Important', {}, 0.8);

      await memory.store(unimportant);
      await memory.store(important);

      expect(memory.length).toBe(1); // Only important stored
    });

    it('should store if importance equals threshold', async () => {
      const memory = new LongTermMemory(undefined, undefined, 0.7);

      const entry = createMemoryEntry('Threshold', {}, 0.7);

      await memory.store(entry);

      expect(memory.length).toBe(1);
    });
  });

  describe('Retrieval', () => {
    it('should retrieve by relevance', async () => {
      const memory = new LongTermMemory();

      await memory.store(createMemoryEntry('User likes Python', {}, 0.8));
      await memory.store(createMemoryEntry('Weather is sunny', {}, 0.6));
      await memory.store(createMemoryEntry('User prefers TypeScript', {}, 0.7));

      const results = await memory.retrieve('programming language', 10);

      // Should prioritize entries with relevant keywords
      expect(results.length).toBeGreaterThan(0);
    });

    it('should score by importance', async () => {
      const memory = new LongTermMemory();

      const low = createMemoryEntry('Low importance', {}, 0.3);
      const high = createMemoryEntry('High importance', {}, 0.9);

      await memory.store(low);
      await memory.store(high);

      const results = await memory.retrieve('importance', 10);

      // Higher importance should rank higher
      expect(results[0].importance).toBeGreaterThanOrEqual(results[1]?.importance || 0);
    });

    it('should limit results', async () => {
      const memory = new LongTermMemory();

      await memory.store(createMemoryEntry('Entry 1', {}, 0.8));
      await memory.store(createMemoryEntry('Entry 2', {}, 0.8));
      await memory.store(createMemoryEntry('Entry 3', {}, 0.8));

      const results = await memory.retrieve('Entry', 2);

      expect(results.length).toBe(2);
    });

    it('should update access count', async () => {
      const memory = new LongTermMemory();
      const entry = createMemoryEntry('Test', {}, 0.8);

      await memory.store(entry);

      const results = await memory.retrieve('Test', 10);

      expect(results[0].accessCount).toBe(1);
      expect(results[0].lastAccessed).toBeInstanceOf(Date);
    });
  });

  describe('Deletion', () => {
    it('should delete specific entry', async () => {
      const memory = new LongTermMemory();
      const entry = createMemoryEntry('To delete', {}, 0.8);

      await memory.store(entry);
      expect(memory.length).toBe(1);

      await memory.delete(entry.id);
      expect(memory.length).toBe(0);
    });
  });
});

describe('MemoryHierarchy', () => {
  describe('Configuration', () => {
    it('should create with all tiers', () => {
      const working = new WorkingMemory(10);
      const shortTerm = new ShortTermMemory(100, 3600);
      const longTerm = new LongTermMemory();

      const hierarchy = new MemoryHierarchy(working, shortTerm, longTerm);

      expect(hierarchy).toBeDefined();
    });

    it('should create with only working memory', () => {
      const working = new WorkingMemory(10);
      const hierarchy = new MemoryHierarchy(working);

      expect(hierarchy).toBeDefined();
    });
  });

  describe('Storage Across Tiers', () => {
    it('should store in all tiers', async () => {
      const working = new WorkingMemory(10);
      const shortTerm = new ShortTermMemory(100, 3600);
      const longTerm = new LongTermMemory(undefined, undefined, 0.5);

      const hierarchy = new MemoryHierarchy(working, shortTerm, longTerm);

      await hierarchy.store('Important memory', {}, 0.8);

      expect(working.length).toBe(1);
      expect(shortTerm.length).toBe(1);
      expect(longTerm.length).toBe(1);
    });

    it('should not store unimportant in long-term', async () => {
      const working = new WorkingMemory(10);
      const shortTerm = new ShortTermMemory(100, 3600);
      const longTerm = new LongTermMemory(undefined, undefined, 0.7);

      const hierarchy = new MemoryHierarchy(working, shortTerm, longTerm);

      await hierarchy.store('Unimportant', {}, 0.5);

      expect(working.length).toBe(1);
      expect(shortTerm.length).toBe(1);
      expect(longTerm.length).toBe(0); // Below threshold
    });

    it('should throw if importance out of range', async () => {
      const working = new WorkingMemory(10);
      const hierarchy = new MemoryHierarchy(working);

      await expect(hierarchy.store('Test', {}, 1.5)).rejects.toThrow(
        'importance must be between 0.0 and 1.0'
      );
    });

    it('should return entry ID', async () => {
      const working = new WorkingMemory(10);
      const hierarchy = new MemoryHierarchy(working);

      const id = await hierarchy.store('Test', {}, 0.5);

      expect(typeof id).toBe('string');
      expect(id.length).toBeGreaterThan(0);
    });
  });

  describe('Retrieval Across Tiers', () => {
    it('should retrieve from all tiers', async () => {
      const working = new WorkingMemory(10);
      const shortTerm = new ShortTermMemory(100, 3600);
      const longTerm = new LongTermMemory();

      const hierarchy = new MemoryHierarchy(working, shortTerm, longTerm);

      await hierarchy.store('Memory 1', {}, 0.6);
      await hierarchy.store('Memory 2', {}, 0.7);
      await hierarchy.store('Memory 3', {}, 0.8);

      const results = await hierarchy.retrieve('Memory', 10);

      expect(results.length).toBeGreaterThan(0);
    });

    it('should deduplicate across tiers', async () => {
      const working = new WorkingMemory(10);
      const shortTerm = new ShortTermMemory(100, 3600);

      const hierarchy = new MemoryHierarchy(working, shortTerm);

      await hierarchy.store('Same memory', {}, 0.5);

      const results = await hierarchy.retrieve('memory', 10);

      // Same entry exists in both tiers, but should only appear once
      const uniqueIds = new Set(results.map(r => r.id));
      expect(uniqueIds.size).toBe(results.length);
    });

    it('should sort by importance and recency', async () => {
      const working = new WorkingMemory(10);
      const hierarchy = new MemoryHierarchy(working);

      await hierarchy.store('Low importance', {}, 0.3);
      await hierarchy.store('High importance', {}, 0.9);

      const results = await hierarchy.retrieve('importance', 10);

      // Higher importance should come first
      expect(results[0].importance).toBeGreaterThanOrEqual(results[1]?.importance || 0);
    });

    it('should limit results', async () => {
      const working = new WorkingMemory(10);
      const hierarchy = new MemoryHierarchy(working);

      await hierarchy.store('Memory 1', {}, 0.5);
      await hierarchy.store('Memory 2', {}, 0.5);
      await hierarchy.store('Memory 3', {}, 0.5);

      const results = await hierarchy.retrieve('Memory', 2);

      expect(results.length).toBe(2);
    });

    it('should support tier filtering', async () => {
      const working = new WorkingMemory(10);
      const shortTerm = new ShortTermMemory(100, 3600);

      const hierarchy = new MemoryHierarchy(working, shortTerm);

      await hierarchy.store('Test', {}, 0.5);

      const workingOnly = await hierarchy.retrieve('Test', 10, ['working']);
      const shortTermOnly = await hierarchy.retrieve('Test', 10, ['short_term']);

      expect(workingOnly.length).toBeGreaterThan(0);
      expect(shortTermOnly.length).toBeGreaterThan(0);
    });
  });

  describe('Deletion Across Tiers', () => {
    it('should delete from all tiers', async () => {
      const working = new WorkingMemory(10);
      const shortTerm = new ShortTermMemory(100, 3600);
      const longTerm = new LongTermMemory();

      const hierarchy = new MemoryHierarchy(working, shortTerm, longTerm);

      const id = await hierarchy.store('To delete', {}, 0.8);

      expect(working.length).toBe(1);
      expect(shortTerm.length).toBe(1);
      expect(longTerm.length).toBe(1);

      await hierarchy.delete(id);

      expect(working.length).toBe(0);
      expect(shortTerm.length).toBe(0);
      expect(longTerm.length).toBe(0);
    });
  });

  describe('Utility Methods', () => {
    it('should clear working memory', async () => {
      const working = new WorkingMemory(10);
      const hierarchy = new MemoryHierarchy(working);

      await hierarchy.store('Test', {}, 0.5);

      hierarchy.clearWorking();

      expect(working.length).toBe(0);
    });

    it('should get working memory entries', async () => {
      const working = new WorkingMemory(10);
      const hierarchy = new MemoryHierarchy(working);

      await hierarchy.store('Test', {}, 0.5);

      const entries = hierarchy.getWorking();

      expect(entries.length).toBe(1);
      expect(entries[0].content).toBe('Test');
    });
  });
});

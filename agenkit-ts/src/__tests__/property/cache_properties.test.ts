/**
 * Cache Middleware Property-Based Tests
 *
 * Validates invariants that should hold for caching behavior:
 * - Cache hit rate is always in [0.0, 1.0]
 * - LRU ordering (most recently used not evicted first)
 * - TTL expiration (expired entries never returned)
 * - Size bounds (cache size never exceeds max)
 * - Idempotency (same key returns same cached result)
 */

import { describe, it, expect, vi } from 'vitest';
import * as fc from 'fast-check';
import type { Message } from '../../core/interfaces';
import { shortContentArbitrary, smallPositiveIntArbitrary } from './strategies';

/**
 * Simple cache implementation for property testing.
 */
class SimpleCache {
  private cache = new Map<string, Message>();
  private expiry = new Map<string, number>();
  private accessOrder: string[] = [];
  private hits = 0;
  private misses = 0;

  constructor(
    private readonly maxSize: number,
    private readonly defaultTtl: number
  ) {}

  getCacheSize(): number {
    return this.cache.size;
  }

  getHitRate(): number {
    const total = this.hits + this.misses;
    return total > 0 ? this.hits / total : 0.0;
  }

  get(key: string): Message | null {
    // Check if key exists
    if (!this.cache.has(key)) {
      this.misses++;
      return null;
    }

    // Check if expired
    const expiry = this.expiry.get(key);
    if (expiry !== undefined && Date.now() > expiry) {
      this.cache.delete(key);
      this.expiry.delete(key);
      const index = this.accessOrder.indexOf(key);
      if (index !== -1) this.accessOrder.splice(index, 1);
      this.misses++;
      return null;
    }

    // Hit - move to end (most recently used)
    this.hits++;
    const index = this.accessOrder.indexOf(key);
    if (index !== -1) {
      this.accessOrder.splice(index, 1);
    }
    this.accessOrder.push(key);

    return this.cache.get(key) ?? null;
  }

  put(key: string, value: Message, ttl?: number): void {
    // Evict if at capacity and key doesn't exist
    if (!this.cache.has(key) && this.cache.size >= this.maxSize) {
      // Evict least recently used (first item in access order)
      const evictedKey = this.accessOrder.shift();
      if (evictedKey) {
        this.cache.delete(evictedKey);
        this.expiry.delete(evictedKey);
      }
    }

    // Add/update entry
    this.cache.set(key, value);
    const index = this.accessOrder.indexOf(key);
    if (index !== -1) {
      this.accessOrder.splice(index, 1);
    }
    this.accessOrder.push(key);
    this.expiry.set(key, Date.now() + (ttl ?? this.defaultTtl) * 1000);
  }

  getStats() {
    return {
      size: this.getCacheSize(),
      hits: this.hits,
      misses: this.misses,
      hitRate: this.getHitRate(),
    };
  }
}

// ============================================
// Property: Cache Size Never Exceeds Max
// ============================================

describe('Cache Properties: Size Bounds', () => {
  it('should never exceed max cache size', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 50 }),
        fc.integer({ min: 1, max: 100 }),
        (maxSize, numRequests) => {
          const cache = new SimpleCache(maxSize, 3600);

          // Make many requests with different keys
          for (let i = 0; i < numRequests; i++) {
            const key = `key_${i}`;
            const value: Message = { role: 'user', content: `Value ${i}` };
            cache.put(key, value);

            // Property: size never exceeds max
            expect(cache.getCacheSize()).toBeLessThanOrEqual(maxSize);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should be exactly at max size after eviction', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 20 }),
        fc.integer({ min: 1, max: 100 }),
        (maxSize, numEntries) => {
          fc.pre(numEntries > maxSize); // Only test when eviction would occur

          const cache = new SimpleCache(maxSize, 3600);

          // Add more entries than max_size
          for (let i = 0; i < numEntries; i++) {
            cache.put(`key_${i}`, { role: 'user', content: `Value ${i}` });
          }

          // Property: Cache should be exactly at max_size
          expect(cache.getCacheSize()).toBe(maxSize);
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ============================================
// Property: Hit Rate is in [0.0, 1.0]
// ============================================

describe('Cache Properties: Hit Rate', () => {
  it('should always have hit rate in [0.0, 1.0]', () => {
    fc.assert(
      fc.property(
        smallPositiveIntArbitrary,
        fc.integer({ min: 1, max: 20 }),
        fc.integer({ min: 1, max: 20 }),
        (maxSize, numPuts, numGets) => {
          const cache = new SimpleCache(maxSize, 3600);

          // Put some entries
          for (let i = 0; i < numPuts; i++) {
            cache.put(`key_${i}`, { role: 'user', content: `Value ${i}` });
          }

          // Get entries (some hits, some misses)
          for (let i = 0; i < numGets; i++) {
            const key = `key_${i % (numPuts + 5)}`; // Mix of valid and invalid keys
            cache.get(key);
          }

          // Property: hit rate in [0.0, 1.0]
          const hitRate = cache.getHitRate();
          expect(hitRate).toBeGreaterThanOrEqual(0.0);
          expect(hitRate).toBeLessThanOrEqual(1.0);
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ============================================
// Property: LRU Ordering
// ============================================

describe('Cache Properties: LRU Ordering', () => {
  it('should not evict most recently used items first', () => {
    fc.assert(
      fc.property(fc.integer({ min: 2, max: 10 }), (maxSize) => {
        const cache = new SimpleCache(maxSize, 3600);

        // Fill cache to capacity
        for (let i = 0; i < maxSize; i++) {
          cache.put(`key_${i}`, { role: 'user', content: `Value ${i}` });
        }

        // Access key_0 to make it most recently used
        const result1 = cache.get('key_0');
        expect(result1).not.toBeNull();

        // Add new entry (should evict LRU, which is key_1)
        cache.put(`key_${maxSize}`, { role: 'user', content: `Value ${maxSize}` });

        // Property: Most recently used (key_0) should still be in cache
        const result2 = cache.get('key_0');
        expect(result2).not.toBeNull();

        // Property: Least recently used (key_1) should be evicted
        const result3 = cache.get('key_1');
        expect(result3).toBeNull();
      }),
      { numRuns: 100 }
    );
  });
});

// ============================================
// Property: TTL Expiration
// ============================================

describe('Cache Properties: TTL Expiration', () => {
  it('should never return expired entries', () => {
    // Fake timers replace the per-run real sleep (previously (ttl+0.05)s ×
    // numRuns ≈ 2–4s of wall-clock) with deterministic clock advancement. The
    // cache keys expiry off Date.now(), so advancing the fake clock past the
    // TTL exercises exactly the same expiration path. numRuns is unchanged.
    vi.useFakeTimers();
    try {
      fc.assert(
        fc.property(
          fc.float({ min: Math.fround(0.05), max: Math.fround(0.15), noNaN: true }),
          (ttl) => {
            const cache = new SimpleCache(10, ttl);

            // Put entry with short TTL
            cache.put('key', { role: 'user', content: 'Value' }, ttl);

            // Should be available immediately
            const result1 = cache.get('key');
            expect(result1).not.toBeNull();

            // Advance past expiration (TTL + margin), in simulated time
            vi.advanceTimersByTime((ttl + 0.05) * 1000);

            // Property: Expired entry should not be returned
            const result2 = cache.get('key');
            expect(result2).toBeNull();
          }
        ),
        { numRuns: 20 }
      );
    } finally {
      vi.useRealTimers();
    }
  });
});

// ============================================
// Property: Idempotency
// ============================================

describe('Cache Properties: Idempotency', () => {
  it('should return same result for same key across multiple accesses', () => {
    fc.assert(
      fc.property(
        shortContentArbitrary,
        fc.integer({ min: 2, max: 20 }),
        (content, numAccesses) => {
          const cache = new SimpleCache(10, 3600);

          // Put entry
          const key = 'test_key';
          const value: Message = { role: 'user', content };
          cache.put(key, value);

          // Access multiple times
          const results: Message[] = [];
          for (let i = 0; i < numAccesses; i++) {
            const result = cache.get(key);
            if (result !== null) {
              results.push(result);
            }
          }

          // Property: All results should be identical
          expect(results.length).toBeGreaterThan(0);
          const firstResult = results[0];
          for (const result of results.slice(1)) {
            expect(result.content).toBe(firstResult.content);
            expect(result.role).toBe(firstResult.role);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ============================================
// Property: Cache Statistics Consistency
// ============================================

describe('Cache Properties: Statistics', () => {
  it('should maintain hits + misses = total requests', () => {
    fc.assert(
      fc.property(
        smallPositiveIntArbitrary,
        fc.array(
          fc.tuple(fc.constantFrom('put', 'get'), fc.integer({ min: 0, max: 20 })),
          { minLength: 1, maxLength: 50 }
        ),
        (maxSize, operations) => {
          const cache = new SimpleCache(maxSize, 3600);
          let totalGets = 0;

          for (const [opType, keyIdx] of operations) {
            const key = `key_${keyIdx}`;

            if (opType === 'put') {
              cache.put(key, { role: 'user', content: `Value ${keyIdx}` });
            } else {
              // get
              cache.get(key);
              totalGets++;
            }
          }

          // Property: hits + misses = total get requests
          const stats = cache.getStats();
          expect(stats.hits + stats.misses).toBe(totalGets);
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ============================================
// Property: No Duplicate Keys
// ============================================

describe('Cache Properties: Uniqueness', () => {
  it('should never contain duplicate keys', () => {
    fc.assert(
      fc.property(
        smallPositiveIntArbitrary,
        fc.array(fc.integer({ min: 0, max: 50 }), { minLength: 1, maxLength: 100 }),
        (maxSize, keyIndices) => {
          const cache = new SimpleCache(maxSize, 3600);

          // Add entries (may have duplicate indices)
          for (const idx of keyIndices) {
            const key = `key_${idx}`;
            cache.put(key, { role: 'user', content: `Value ${idx}` });
          }

          // Property: All keys in cache are unique
          const keysInCache = Array.from((cache as any).cache.keys());
          const uniqueKeys = new Set(keysInCache);
          expect(keysInCache.length).toBe(uniqueKeys.size);
        }
      ),
      { numRuns: 100 }
    );
  });
});

/**
 * Caching middleware with LRU eviction and TTL expiration.
 *
 * Provides response caching with configurable TTL (time-to-live) and
 * LRU (least recently used) eviction policy.
 *
 * Features:
 * - LRU eviction when cache is full
 * - TTL-based expiration
 * - Configurable cache key generation
 * - Detailed metrics (hit rate, miss rate, evictions)
 * - Async read-write lock for thread safety
 */

import { createHash } from 'crypto';
import { Agent, Message } from '../core/interfaces';

/**
 * Configuration for caching behavior.
 */
export interface CachingConfig {
  /** Maximum number of entries in cache (default: 1000) */
  maxCacheSize?: number;

  /** Default TTL in milliseconds (default: 300000 = 5 minutes) */
  defaultTtl?: number;

  /** Custom cache key generator function */
  keyGenerator?: (message: Message) => string;
}

/**
 * Metrics for cache operations.
 */
export interface CachingMetrics {
  totalRequests: number;
  cacheHits: number;
  cacheMisses: number;
  evictions: number;
  invalidations: number;
  currentSize: number;
}

/**
 * Entry in the cache with expiration.
 */
interface CacheEntry {
  response: Message;
  expiresAt: number;
  createdAt: number;
}

/**
 * Simple async read-write lock.
 *
 * Allows multiple concurrent readers or a single writer.
 */
class AsyncRWLock {
  private readers = 0;
  private writer = false;
  private waitingReaders: Array<() => void> = [];
  private waitingWriters: Array<() => void> = [];

  async acquireRead(): Promise<void> {
    if (!this.writer && this.waitingWriters.length === 0) {
      this.readers++;
      return;
    }

    await new Promise<void>((resolve) => {
      this.waitingReaders.push(resolve);
    });
  }

  releaseRead(): void {
    this.readers--;

    if (this.readers === 0 && this.waitingWriters.length > 0) {
      const resolve = this.waitingWriters.shift()!;
      this.writer = true;
      resolve();
    }
  }

  async acquireWrite(): Promise<void> {
    if (!this.writer && this.readers === 0) {
      this.writer = true;
      return;
    }

    await new Promise<void>((resolve) => {
      this.waitingWriters.push(resolve);
    });
  }

  releaseWrite(): void {
    this.writer = false;

    // Prioritize readers over writers
    if (this.waitingReaders.length > 0) {
      const readers = this.waitingReaders.splice(0);
      this.readers = readers.length;
      readers.forEach((resolve) => resolve());
    } else if (this.waitingWriters.length > 0) {
      const resolve = this.waitingWriters.shift()!;
      this.writer = true;
      resolve();
    }
  }
}

/**
 * Agent decorator that caches responses with LRU eviction and TTL expiration.
 *
 * Example:
 *   const config: CachingConfig = { maxCacheSize: 500, defaultTtl: 60000 };
 *   const cachingAgent = new CachingDecorator(agent, config);
 *
 *   const response1 = await cachingAgent.process(msg);
 *   const response2 = await cachingAgent.process(msg); // Cache hit!
 *
 *   console.log('Hit rate:', cachingAgent.metrics.hitRate);
 */
export class CachingDecorator implements Agent {
  readonly name: string;
  readonly capabilities?: string[];

  private agent: Agent;
  private config: Required<CachingConfig>;
  private cache: Map<string, CacheEntry> = new Map();
  private accessOrder: string[] = []; // Track LRU order
  private rwLock = new AsyncRWLock();
  private metricsData: CachingMetrics;

  constructor(agent: Agent, config?: CachingConfig) {
    this.agent = agent;
    this.name = agent.name;
    this.capabilities = agent.capabilities;

    // Apply defaults
    this.config = {
      maxCacheSize: config?.maxCacheSize ?? 1000,
      defaultTtl: config?.defaultTtl ?? 300000, // 5 minutes
      keyGenerator: config?.keyGenerator ?? this.defaultKeyGenerator.bind(this),
    };

    // Validate configuration
    if (this.config.maxCacheSize < 1) {
      throw new Error('maxCacheSize must be at least 1');
    }
    if (this.config.defaultTtl <= 0) {
      throw new Error('defaultTtl must be positive');
    }

    // Initialize metrics
    this.metricsData = {
      totalRequests: 0,
      cacheHits: 0,
      cacheMisses: 0,
      evictions: 0,
      invalidations: 0,
      currentSize: 0,
    };
  }

  /**
   * Get caching metrics with calculated rates.
   */
  get metrics(): CachingMetrics & { hitRate: number; missRate: number } {
    return {
      ...this.metricsData,
      hitRate:
        this.metricsData.totalRequests === 0
          ? 0
          : this.metricsData.cacheHits / this.metricsData.totalRequests,
      missRate:
        this.metricsData.totalRequests === 0
          ? 0
          : this.metricsData.cacheMisses / this.metricsData.totalRequests,
    };
  }

  /**
   * Default cache key generator.
   *
   * @param message Input message
   * @returns Cache key string
   */
  private defaultKeyGenerator(message: Message): string {
    // Hash of role + content + metadata
    const keyData = {
      role: message.role,
      content: JSON.stringify(message.content),
      metadata: message.metadata || {},
    };
    const keyStr = JSON.stringify(keyData);
    return createHash('sha256').update(keyStr).digest('hex');
  }

  /**
   * Evict least recently used entry if cache is full.
   */
  private evictLru(): void {
    if (this.cache.size >= this.config.maxCacheSize) {
      // Remove oldest (LRU) entry
      const lruKey = this.accessOrder.shift();
      if (lruKey) {
        this.cache.delete(lruKey);
        this.metricsData.evictions++;
        this.metricsData.currentSize = this.cache.size;
      }
    }
  }

  /**
   * Remove expired entries from cache.
   */
  private cleanupExpired(): void {
    const now = Date.now();
    const expiredKeys: string[] = [];

    for (const [key, entry] of this.cache.entries()) {
      if (now >= entry.expiresAt) {
        expiredKeys.push(key);
      }
    }

    for (const key of expiredKeys) {
      this.cache.delete(key);
      // Remove from access order
      const idx = this.accessOrder.indexOf(key);
      if (idx !== -1) {
        this.accessOrder.splice(idx, 1);
      }
      this.metricsData.evictions++;
    }

    if (expiredKeys.length > 0) {
      this.metricsData.currentSize = this.cache.size;
    }
  }

  /**
   * Update access order for LRU tracking.
   */
  private updateAccessOrder(key: string): void {
    // Remove from current position
    const idx = this.accessOrder.indexOf(key);
    if (idx !== -1) {
      this.accessOrder.splice(idx, 1);
    }
    // Add to end (most recently used)
    this.accessOrder.push(key);
  }

  /**
   * Process message with caching.
   *
   * @param message Input message
   * @returns Response message from cache or agent
   */
  async process(message: Message): Promise<Message> {
    // Increment metrics
    this.metricsData.totalRequests++;

    // Generate cache key
    const cacheKey = this.config.keyGenerator(message);

    // Check cache with read lock
    await this.rwLock.acquireRead();
    try {
      const entry = this.cache.get(cacheKey);

      if (entry && Date.now() < entry.expiresAt) {
        // Cache hit
        const response = entry.response;
        this.rwLock.releaseRead();
        this.metricsData.cacheHits++;

        // Update access order (requires write lock, do it async)
        this.updateAccessOrderAsync(cacheKey);

        return response;
      }

      // Not in cache or expired
      this.rwLock.releaseRead();
    } catch (error) {
      this.rwLock.releaseRead();
      throw error;
    }

    // Cache miss
    this.metricsData.cacheMisses++;

    // Process message (outside lock)
    const response = await this.agent.process(message);

    // Cache response with write lock
    await this.rwLock.acquireWrite();
    try {
      // Cleanup expired entries periodically
      if (this.metricsData.totalRequests % 100 === 0) {
        this.cleanupExpired();
      }

      // Evict LRU if needed
      this.evictLru();

      // Add to cache
      const entry: CacheEntry = {
        response,
        expiresAt: Date.now() + this.config.defaultTtl,
        createdAt: Date.now(),
      };
      this.cache.set(cacheKey, entry);
      this.updateAccessOrder(cacheKey);
      this.metricsData.currentSize = this.cache.size;
    } finally {
      this.rwLock.releaseWrite();
    }

    return response;
  }

  /**
   * Update access order asynchronously (best effort).
   */
  private async updateAccessOrderAsync(key: string): Promise<void> {
    try {
      await this.rwLock.acquireWrite();
      this.updateAccessOrder(key);
      this.rwLock.releaseWrite();
    } catch {
      // Ignore errors in access order update
    }
  }

  /**
   * Invalidate cache entries.
   *
   * @param message If provided, invalidate only this message's cache entry.
   *                If undefined, invalidate entire cache.
   */
  async invalidate(message?: Message): Promise<void> {
    await this.rwLock.acquireWrite();
    try {
      if (message !== undefined) {
        // Invalidate specific entry
        const cacheKey = this.config.keyGenerator(message);
        if (this.cache.delete(cacheKey)) {
          // Remove from access order
          const idx = this.accessOrder.indexOf(cacheKey);
          if (idx !== -1) {
            this.accessOrder.splice(idx, 1);
          }
          this.metricsData.invalidations++;
          this.metricsData.currentSize = this.cache.size;
        }
      } else {
        // Invalidate entire cache
        const count = this.cache.size;
        this.cache.clear();
        this.accessOrder = [];
        this.metricsData.invalidations += count;
        this.metricsData.currentSize = 0;
      }
    } finally {
      this.rwLock.releaseWrite();
    }
  }

  /**
   * Get current cache size.
   *
   * @returns Number of entries in cache
   */
  async getCacheSize(): Promise<number> {
    await this.rwLock.acquireRead();
    try {
      return this.cache.size;
    } finally {
      this.rwLock.releaseRead();
    }
  }

  /**
   * Get detailed cache information.
   *
   * @returns Cache statistics
   */
  async getCacheInfo(): Promise<{
    size: number;
    maxSize: number;
    defaultTtl: number;
    metrics: {
      totalRequests: number;
      cacheHits: number;
      cacheMisses: number;
      hitRate: number;
      missRate: number;
      evictions: number;
      invalidations: number;
    };
  }> {
    await this.rwLock.acquireRead();
    try {
      return {
        size: this.cache.size,
        maxSize: this.config.maxCacheSize,
        defaultTtl: this.config.defaultTtl,
        metrics: {
          totalRequests: this.metricsData.totalRequests,
          cacheHits: this.metricsData.cacheHits,
          cacheMisses: this.metricsData.cacheMisses,
          hitRate: this.metrics.hitRate,
          missRate: this.metrics.missRate,
          evictions: this.metricsData.evictions,
          invalidations: this.metricsData.invalidations,
        },
      };
    } finally {
      this.rwLock.releaseRead();
    }
  }
}

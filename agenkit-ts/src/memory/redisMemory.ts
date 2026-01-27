/**
 * Redis-backed memory implementation with TTL and pub/sub support.
 *
 * Features:
 * - Persistent storage (survives restarts)
 * - TTL support (automatic expiry)
 * - Multi-instance agents (shared memory)
 * - Fast access (in-memory Redis)
 * - Scalable (Redis cluster support)
 *
 * Use cases:
 * - Production deployments
 * - Multi-instance agents
 * - When persistence needed
 * - Shared memory across agents
 *
 * Example:
 *   const memory = new RedisMemory({
 *     redisUrl: 'redis://localhost:6379',
 *     ttl: 86400,
 *     keyPrefix: 'agenkit:memory',
 *   });
 *   await memory.store('session-123', message, { importance: 0.8 });
 *   const messages = await memory.retrieve('session-123', { limit: 10 });
 *
 * Redis Data Structure:
 *   Key: "agenkit:memory:{session_id}:messages"
 *   Type: Sorted Set (ZSET)
 *   Score: Timestamp (for ordering)
 *   Value: JSON(message, metadata)
 */

import { createClient, RedisClientType } from 'redis';
import { Memory } from './base';
import { Message } from '../core/interfaces';

/**
 * Stored message format in Redis.
 */
interface StoredMessage {
  role: string;
  content: string;
  metadata: Record<string, unknown>;
}

/**
 * Options for RedisMemory constructor.
 */
export interface RedisMemoryOptions {
  /** Redis connection URL (default: redis://localhost:6379) */
  redisUrl?: string;
  /** Time-to-live in seconds (0 = no expiry, default: 86400) */
  ttl?: number;
  /** Prefix for Redis keys (default: agenkit:memory) */
  keyPrefix?: string;
}

/**
 * Redis-backed memory with TTL and pub/sub support.
 *
 * Provides persistent storage for agent conversations with automatic
 * expiration, multi-instance support, and filtering capabilities.
 *
 * Example:
 *   const memory = new RedisMemory({
 *     redisUrl: 'redis://localhost:6379',
 *     ttl: 86400,  // 24 hours
 *   });
 *
 *   await memory.store('session-123', {
 *     role: 'user',
 *     content: 'Hello',
 *   }, {
 *     importance: 0.8,
 *     tags: ['greeting'],
 *   });
 *
 *   const messages = await memory.retrieve('session-123', {
 *     limit: 10,
 *     importanceThreshold: 0.5,
 *   });
 */
export class RedisMemory implements Memory {
  private redisUrl: string;
  private ttl: number;
  private keyPrefix: string;
  private client: RedisClientType | null = null;

  constructor(options: RedisMemoryOptions = {}) {
    this.redisUrl = options.redisUrl || 'redis://localhost:6379';
    this.ttl = options.ttl ?? 86400; // Default 24 hours
    this.keyPrefix = options.keyPrefix || 'agenkit:memory';
  }

  /**
   * Initialize Redis connection.
   */
  private async ensureConnected(): Promise<RedisClientType> {
    if (this.client && this.client.isOpen) {
      return this.client;
    }

    this.client = createClient({ url: this.redisUrl });

    this.client.on('error', (err) => {
      console.error('Redis Client Error:', err);
    });

    await this.client.connect();
    return this.client;
  }

  /**
   * Get Redis key for a session.
   */
  private sessionKey(sessionId: string): string {
    return `${this.keyPrefix}:${sessionId}:messages`;
  }

  /**
   * Serialize message and metadata to JSON string.
   */
  private serializeMessage(message: Message, metadata: Record<string, unknown> = {}): string {
    const data: StoredMessage = {
      role: message.role,
      content: message.content,
      metadata,
    };
    return JSON.stringify(data);
  }

  /**
   * Deserialize JSON string to message and metadata.
   */
  private deserializeMessage(data: string): { message: Message; metadata: Record<string, unknown> } {
    const parsed = JSON.parse(data) as StoredMessage;
    return {
      message: {
        role: parsed.role,
        content: parsed.content,
      },
      metadata: parsed.metadata || {},
    };
  }

  /**
   * Store message in Redis with optional metadata.
   */
  async store(sessionId: string, message: Message, metadata: Record<string, unknown> = {}): Promise<void> {
    const client = await this.ensureConnected();

    // Serialize
    const timestamp = Date.now() / 1000; // Unix timestamp in seconds
    const value = this.serializeMessage(message, metadata);

    // Store in sorted set (score = timestamp)
    const key = this.sessionKey(sessionId);
    await client.zAdd(key, { score: timestamp, value });

    // Set TTL if configured
    if (this.ttl > 0) {
      await client.expire(key, this.ttl);
    }
  }

  /**
   * Retrieve messages from Redis with filtering.
   *
   * Supports:
   * - limit: Maximum messages to return
   * - timeRange: [start, end] for time filtering
   * - importanceThreshold: Minimum importance score
   * - tags: Filter by tags (any match)
   */
  async retrieve(
    sessionId: string,
    options: {
      query?: string;
      limit?: number;
      timeRange?: [Date, Date];
      importanceThreshold?: number;
      tags?: string[];
      [key: string]: unknown;
    } = {},
  ): Promise<Message[]> {
    const client = await this.ensureConnected();
    const key = this.sessionKey(sessionId);

    // Set default limit
    const limit = options.limit || 10;

    // Get all messages (most recent first)
    // ZREVRANGE returns highest scores first
    const values = await client.zRangeWithScores(key, 0, -1, { REV: true });

    if (values.length === 0) {
      return [];
    }

    // Deserialize and filter
    const filtered: Message[] = [];

    for (const item of values) {
      try {
        const { message, metadata } = this.deserializeMessage(item.value);
        const timestamp = item.score;

        // Time range filter
        if (options.timeRange) {
          const [start, end] = options.timeRange;
          const messageTime = timestamp * 1000; // Convert to milliseconds
          if (messageTime < start.getTime() || messageTime > end.getTime()) {
            continue;
          }
        }

        // Importance threshold filter
        if (options.importanceThreshold !== undefined) {
          const importance = (metadata.importance as number) || 0;
          if (importance < options.importanceThreshold) {
            continue;
          }
        }

        // Tags filter (any tag match)
        if (options.tags && options.tags.length > 0) {
          const messageTags = (metadata.tags as string[]) || [];
          const hasTag = options.tags.some((tag) => messageTags.includes(tag));
          if (!hasTag) {
            continue;
          }
        }

        filtered.push(message);

        if (filtered.length >= limit) {
          break;
        }
      } catch (err) {
        // Skip malformed messages
        continue;
      }
    }

    return filtered;
  }

  /**
   * Create summary of conversation history.
   *
   * Simple implementation: Returns a message with concatenated content.
   * Production use should use LLM-based summarization.
   */
  async summarize(
    sessionId: string,
    options: {
      maxLength?: number;
      style?: 'brief' | 'detailed';
      [key: string]: unknown;
    } = {},
  ): Promise<Message> {
    const messages = await this.retrieve(sessionId, { limit: 100 });

    if (messages.length === 0) {
      return {
        role: 'system',
        content: 'No messages in session.',
      };
    }

    // Simple concatenation summary
    const summaryParts: string[] = [];
    const maxMessages = Math.min(messages.length, 10);

    for (let i = 0; i < maxMessages; i++) {
      const msg = messages[i];
      let preview = msg.content;
      if (preview.length > 100) {
        preview = preview.substring(0, 100) + '...';
      }
      summaryParts.push(`${i + 1}. [${msg.role}] ${preview}`);
    }

    const summaryContent = `Session summary (${messages.length} messages):\n${summaryParts.join('\n')}`;

    return {
      role: 'system',
      content: summaryContent,
    };
  }

  /**
   * Clear all memory for a session.
   */
  async clear(sessionId: string): Promise<void> {
    const client = await this.ensureConnected();
    const key = this.sessionKey(sessionId);
    await client.del(key);
  }

  /**
   * Get memory capabilities.
   */
  get capabilities(): string[] {
    return [
      'basic_retrieval',
      'persistence',
      'ttl',
      'time_filtering',
      'importance_filtering',
      'tag_filtering',
    ];
  }

  /**
   * Additional utility methods
   */

  /**
   * Get the number of messages stored for a session.
   */
  async getSessionCount(sessionId: string): Promise<number> {
    const client = await this.ensureConnected();
    const key = this.sessionKey(sessionId);
    return await client.zCard(key);
  }

  /**
   * Get all session IDs.
   */
  async getAllSessions(): Promise<string[]> {
    const client = await this.ensureConnected();
    const pattern = `${this.keyPrefix}:*:messages`;
    const sessions: string[] = [];

    // Use SCAN to iterate over keys
    for await (const key of client.scanIterator({ MATCH: pattern })) {
      // Extract session_id from key
      // Format: "agenkit:memory:{session_id}:messages"
      const parts = key.split(':');
      if (parts.length >= 3) {
        const sessionId = parts[parts.length - 2]; // Second to last part
        sessions.push(sessionId);
      }
    }

    return sessions;
  }

  /**
   * Get memory usage statistics.
   */
  async getMemoryUsage(): Promise<{ totalSessions: number; totalMessages: number; ttl: number }> {
    const sessions = await this.getAllSessions();

    let totalMessages = 0;
    for (const sessionId of sessions) {
      const count = await this.getSessionCount(sessionId);
      totalMessages += count;
    }

    return {
      totalSessions: sessions.length,
      totalMessages,
      ttl: this.ttl,
    };
  }

  /**
   * Close Redis connection.
   */
  async close(): Promise<void> {
    if (this.client && this.client.isOpen) {
      await this.client.quit();
      this.client = null;
    }
  }
}

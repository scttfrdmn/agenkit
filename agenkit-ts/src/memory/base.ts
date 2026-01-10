/**
 * Memory interface for agent memory systems.
 *
 * This module defines the minimal interface for agent memory systems,
 * supporting multiple storage backends and retrieval strategies.
 *
 * Design principles:
 * - Minimal: Only essential methods
 * - Flexible: Support multiple storage backends
 * - Composable: Combine with strategies
 * - Async-first: Production-ready
 */

import { Message } from '../core/interfaces';

/**
 * Minimal interface for agent memory systems.
 *
 * Memory systems store and retrieve agent conversation history,
 * enabling context management beyond raw message lists. Different
 * implementations support various storage backends and retrieval
 * strategies.
 *
 * Implementations:
 * - InMemoryMemory: Simple in-memory storage with LRU eviction
 * - RedisMemory: Redis-backed with TTL and pub/sub
 * - VectorMemory: Vector database for semantic retrieval
 *
 * Example:
 *   const memory = new InMemoryMemory({ maxSize: 1000 });
 *   await memory.store('session-123', message);
 *   const messages = await memory.retrieve('session-123', { limit: 10 });
 */
export interface Memory {
  /**
   * Store message in memory with optional metadata.
   *
   * Example:
   *   await memory.store(
   *     'session-123',
   *     { role: 'user', content: 'Hello' },
   *     { importance: 0.8, tags: ['greeting'] },
   *   );
   */
  store(sessionId: string, message: Message, metadata?: Record<string, unknown>): Promise<void>;

  /**
   * Retrieve messages from memory.
   *
   * Options:
   * - query: Optional semantic query for retrieval (if supported)
   * - limit: Maximum messages to return (default: 10)
   * - timeRange: [start, end] for time filtering
   * - importanceThreshold: float for importance filtering
   * - tags: list of tags for tag filtering
   *
   * Returns messages (most recent first by default).
   *
   * Example:
   *   // Basic retrieval (most recent)
   *   const messages = await memory.retrieve('session-123', { limit: 10 });
   *
   *   // Semantic retrieval (if supported)
   *   const messages = await memory.retrieve('session-123', {
   *     query: 'What did we discuss about pricing?',
   *     limit: 5,
   *   });
   *
   *   // Time-filtered retrieval
   *   const messages = await memory.retrieve('session-123', {
   *     timeRange: [startTime, endTime],
   *     limit: 20,
   *   });
   */
  retrieve(
    sessionId: string,
    options?: {
      query?: string;
      limit?: number;
      timeRange?: [Date, Date];
      importanceThreshold?: number;
      tags?: string[];
      [key: string]: unknown;
    },
  ): Promise<Message[]>;

  /**
   * Create summary of conversation history.
   *
   * Options:
   * - maxLength: int for summary length
   * - style: 'brief' | 'detailed' for summary style
   *
   * Returns message containing summary.
   *
   * Example:
   *   const summary = await memory.summarize('session-123');
   *   console.log(summary.content);
   *   // "Discussed pricing strategy, decided on $50/month tier..."
   */
  summarize(
    sessionId: string,
    options?: {
      maxLength?: number;
      style?: 'brief' | 'detailed';
      [key: string]: unknown;
    },
  ): Promise<Message>;

  /**
   * Clear memory for session.
   *
   * Example:
   *   await memory.clear('session-123');
   */
  clear(sessionId: string): Promise<void>;

  /**
   * Return memory capabilities.
   *
   * Possible capabilities:
   * - "basic_retrieval": Supports simple retrieve()
   * - "semantic_search": Supports query-based retrieval
   * - "summarization": Supports summarize()
   * - "persistence": Data survives restarts
   * - "ttl": Supports automatic expiry
   * - "importance_weighting": Supports importance-based retrieval
   * - "time_travel": Supports point-in-time queries
   *
   * Example:
   *   console.log(memory.capabilities);
   *   // ["basic_retrieval", "persistence", "ttl"]
   */
  readonly capabilities: string[];
}

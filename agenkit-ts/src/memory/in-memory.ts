/**
 * In-memory implementation of Memory interface.
 *
 * Provides simple in-memory storage with LRU eviction for testing
 * and simple applications that don't need persistence.
 */

import { Message, createMessage } from '../core/interfaces';
import { Memory } from './base';

/**
 * Simple in-memory storage with LRU eviction.
 *
 * Features:
 * - Fast access (no I/O)
 * - LRU eviction when max_size reached
 * - Per-session storage
 * - Optional metadata support
 *
 * Limitations:
 * - No persistence (data lost on restart)
 * - No semantic search
 * - Memory limited
 *
 * Use cases:
 * - Testing
 * - Simple applications
 * - Prototypes
 * - When persistence not needed
 *
 * Example:
 *   const memory = new InMemoryMemory({ maxSize: 1000 });
 *   await memory.store('session-123', message);
 *   const messages = await memory.retrieve('session-123', { limit: 10 });
 */
export class InMemoryMemory implements Memory {
  private maxSize: number;
  // session_id -> list of (timestamp, message, metadata)
  private storage: Map<string, Array<[number, Message, Record<string, unknown>]>> = new Map();
  // Counter to ensure unique ordering even for same-timestamp messages
  private counter: number = 0;

  constructor(config?: { maxSize?: number }) {
    this.maxSize = config?.maxSize ?? 1000;
  }

  /**
   * Store message in memory with optional metadata.
   */
  async store(
    sessionId: string,
    message: Message,
    metadata?: Record<string, unknown>,
  ): Promise<void> {
    if (!this.storage.has(sessionId)) {
      this.storage.set(sessionId, []);
    }

    const sessionStorage = this.storage.get(sessionId)!;

    // Add message with timestamp (use counter to ensure unique ordering)
    const timestamp = Date.now() / 1000 + this.counter * 0.000001;
    this.counter++;
    sessionStorage.push([timestamp, message, metadata || {}]);

    // LRU eviction if over limit
    if (sessionStorage.length > this.maxSize) {
      // Remove oldest (first item in list)
      sessionStorage.shift();
    }
  }

  /**
   * Retrieve messages from memory.
   *
   * Supports options:
   * - timeRange: [start, end] for filtering
   * - importanceThreshold: float (requires metadata with "importance")
   * - tags: list of tags (requires metadata with "tags")
   */
  async retrieve(
    sessionId: string,
    options?: {
      query?: string;
      limit?: number;
      timeRange?: [Date, Date];
      importanceThreshold?: number;
      tags?: string[];
    },
  ): Promise<Message[]> {
    const limit = options?.limit ?? 10;

    if (!this.storage.has(sessionId)) {
      return [];
    }

    const sessionStorage = this.storage.get(sessionId)!;

    // Get all messages (most recent first)
    const messagesWithMetadata = [...sessionStorage].reverse();

    // Apply filters
    const filtered: Message[] = [];
    for (const [timestamp, message, metadata] of messagesWithMetadata) {
      // Time range filter
      if (options?.timeRange) {
        const [startTime, endTime] = options.timeRange;
        const msgTime = new Date(timestamp * 1000);
        if (msgTime < startTime || msgTime > endTime) {
          continue;
        }
      }

      // Importance threshold filter
      if (options?.importanceThreshold !== undefined) {
        const importance = (metadata.importance as number) || 0.0;
        if (importance < options.importanceThreshold) {
          continue;
        }
      }

      // Tags filter
      if (options?.tags && options.tags.length > 0) {
        const requiredTags = new Set(options.tags);
        const messageTags = new Set((metadata.tags as string[]) || []);
        const hasIntersection = [...requiredTags].some((tag) => messageTags.has(tag));
        if (!hasIntersection) {
          continue;
        }
      }

      filtered.push(message);

      // Stop if we have enough
      if (filtered.length >= limit) {
        break;
      }
    }

    return filtered.slice(0, limit);
  }

  /**
   * Create summary of conversation history.
   *
   * Simple implementation: Returns a message with concatenated content.
   * Production use should use LLM-based summarization.
   */
  async summarize(
    sessionId: string,
    options?: { maxLength?: number; style?: 'brief' | 'detailed' },
  ): Promise<Message> {
    const messages = await this.retrieve(sessionId, { limit: 100 });

    if (messages.length === 0) {
      return createMessage({
        role: 'system',
        content: 'No messages in session.',
      });
    }

    // Simple concatenation summary
    const summaryParts: string[] = [];
    const previewCount = Math.min(10, messages.length);

    for (let i = 0; i < previewCount; i++) {
      const msg = messages[i];
      const contentStr = String(msg.content);
      let preview = contentStr.substring(0, 100);
      if (contentStr.length > 100) {
        preview += '...';
      }
      summaryParts.push(`${i + 1}. [${msg.role}] ${preview}`);
    }

    const summaryContent = `Session summary (${messages.length} messages):\n${summaryParts.join('\n')}`;

    return createMessage({
      role: 'system',
      content: summaryContent,
    });
  }

  /**
   * Clear memory for session.
   */
  async clear(sessionId: string): Promise<void> {
    this.storage.delete(sessionId);
  }

  /**
   * Return memory capabilities.
   */
  get capabilities(): string[] {
    return ['basic_retrieval', 'time_filtering', 'importance_filtering', 'tag_filtering'];
  }

  // Additional utility methods

  /**
   * Get number of messages stored for session.
   */
  getSessionCount(sessionId: string): number {
    if (!this.storage.has(sessionId)) {
      return 0;
    }
    return this.storage.get(sessionId)!.length;
  }

  /**
   * Get list of all session IDs.
   */
  getAllSessions(): string[] {
    return Array.from(this.storage.keys());
  }

  /**
   * Get memory usage statistics.
   */
  getMemoryUsage(): {
    totalSessions: number;
    totalMessages: number;
    maxSizePerSession: number;
  } {
    let totalMessages = 0;
    for (const storage of this.storage.values()) {
      totalMessages += storage.length;
    }

    return {
      totalSessions: this.storage.size,
      totalMessages,
      maxSizePerSession: this.maxSize,
    };
  }
}

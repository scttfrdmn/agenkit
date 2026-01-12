/**
 * Backward-compatible adapter for MemoryHierarchy.
 *
 * Implements the session-based Memory interface while using the 3-tier
 * hierarchy internally for improved performance and scalability.
 */

import { Message } from '../core/interfaces';
import {
  MemoryEntry,
  MemoryHierarchy,
  WorkingMemory,
  ShortTermMemory,
  LongTermMemory,
} from '../patterns/memory';
import { Memory } from './base';

/**
 * Configuration for HierarchyMemory.
 */
export interface HierarchyConfig {
  /** Max messages in working memory (default: 10) */
  workingCapacity?: number;
  /** Max messages in short-term memory (default: 100) */
  shortTermCapacity?: number;
  /** Time-to-live for short-term entries in seconds (default: 3600) */
  shortTermTTLSeconds?: number;
  /** Minimum importance for long-term storage (default: 0.7) */
  longTermMinImportance?: number;
  /** Enable long-term memory (default: true) */
  enableLongTerm?: boolean;
}

/**
 * HierarchyMemory implements Memory interface using 3-tier hierarchy.
 *
 * Benefits over InMemoryMemory:
 * - Automatic importance-based tier routing
 * - FIFO/LRU/TTL eviction strategies
 * - Better memory management for long sessions
 * - Semantic retrieval across tiers
 * - Proven architecture (used in Rust/C++/Zig/Python/Go)
 *
 * Architecture:
 * - Working Memory: Current conversation (FIFO, 10-20 msgs)
 * - Short-Term Memory: Recent sessions (LRU+TTL, 100-1000 msgs)
 * - Long-Term Memory: Important facts (importance threshold, unlimited)
 *
 * Example:
 *   const memory = new HierarchyMemory({
 *     workingCapacity: 10,
 *     shortTermCapacity: 100,
 *     longTermMinImportance: 0.7,
 *   });
 *   await memory.store('session-123', message);
 *   const messages = await memory.retrieve('session-123', { limit: 10 });
 */
export class HierarchyMemory implements Memory {
  private hierarchy: MemoryHierarchy;
  private config: Required<HierarchyConfig>;

  constructor(config: HierarchyConfig = {}) {
    // Apply defaults
    this.config = {
      workingCapacity: config.workingCapacity ?? 10,
      shortTermCapacity: config.shortTermCapacity ?? 100,
      shortTermTTLSeconds: config.shortTermTTLSeconds ?? 3600,
      longTermMinImportance: config.longTermMinImportance ?? 0.7,
      enableLongTerm: config.enableLongTerm ?? true,
    };

    // Validate configuration
    if (this.config.workingCapacity < 1) {
      throw new Error('workingCapacity must be at least 1');
    }
    if (this.config.shortTermCapacity < 1) {
      throw new Error('shortTermCapacity must be at least 1');
    }
    if (this.config.shortTermTTLSeconds < 1) {
      throw new Error('shortTermTTLSeconds must be at least 1');
    }
    if (this.config.longTermMinImportance < 0.0 || this.config.longTermMinImportance > 1.0) {
      throw new Error('longTermMinImportance must be between 0.0 and 1.0');
    }

    // Create hierarchy
    const working = new WorkingMemory(this.config.workingCapacity);
    const shortTerm = new ShortTermMemory(
      this.config.shortTermCapacity,
      this.config.shortTermTTLSeconds
    );
    const longTerm = this.config.enableLongTerm
      ? new LongTermMemory({}, undefined, this.config.longTermMinImportance)
      : undefined;

    this.hierarchy = new MemoryHierarchy(working, shortTerm, longTerm);
  }

  /**
   * Store message in hierarchy with session association.
   *
   * Importance Routing:
   * - System messages: 0.3 (working + short-term only)
   * - User messages: 0.5 (working + short-term, possibly long-term)
   * - Assistant messages: 0.4 (working + short-term only)
   * - High importance (0.7+): Stored in long-term memory
   *
   * To control routing, pass importance in metadata:
   *   await memory.store('session-123', message, { importance: 0.9 });
   */
  async store(
    sessionId: string,
    message: Message,
    metadata?: Record<string, unknown>
  ): Promise<void> {
    // Merge message metadata with provided metadata
    const combinedMetadata: Record<string, unknown> = {
      session_id: sessionId,
      role: message.role,
      message_timestamp: message.timestamp || new Date().toISOString(), // Preserve original timestamp
      ...(message.metadata || {}),
      ...(metadata || {}),
    };

    // Determine importance (use provided, or default by role)
    let importance =
      typeof combinedMetadata.importance === 'number'
        ? combinedMetadata.importance
        : this.defaultImportance(message);

    // Ensure importance is within valid range
    importance = Math.max(0.0, Math.min(1.0, importance));

    // Convert message content to string
    const content = String(message.content);

    // Store in hierarchy
    await this.hierarchy.store(content, combinedMetadata, importance, sessionId);
  }

  /**
   * Retrieve messages from hierarchy filtered by session.
   *
   * Note:
   * Unlike InMemoryMemory, this searches semantically across all tiers
   * when query is provided. For chronological order, omit query or use empty string.
   */
  async retrieve(
    sessionId: string,
    options?: {
      query?: string;
      limit?: number;
      timeRange?: [Date, Date];
      importanceThreshold?: number;
      tags?: string[];
      [key: string]: unknown;
    }
  ): Promise<Message[]> {
    const limit = options?.limit ?? 10;
    const query = options?.query ?? '';

    // Retrieve from hierarchy (get extra to account for filtering)
    // We multiply limit by 3 because:
    // - Multiple sessions may be in hierarchy
    // - Need enough results after session filtering
    // - Better to over-retrieve than under-retrieve
    const entries = await this.hierarchy.retrieve(query, limit * 3);

    // Filter by session and convert to Messages
    const messages: Message[] = [];
    for (const entry of entries) {
      if (entry.metadata.session_id === sessionId) {
        // Apply additional filters
        if (!this.matchesFilters(entry, options)) {
          continue;
        }

        messages.push(this.entryToMessage(entry));

        if (messages.length >= limit) {
          break;
        }
      }
    }

    return messages;
  }

  /**
   * Create summary of conversation history for session.
   *
   * Note:
   * This is a simple implementation using concatenation.
   * Production use should use LLM-based summarization.
   */
  async summarize(
    sessionId: string,
    options?: {
      maxLength?: number;
      style?: 'brief' | 'detailed';
      [key: string]: unknown;
    }
  ): Promise<Message> {
    // Retrieve all messages for session (up to reasonable limit)
    const messages = await this.retrieve(sessionId, { limit: 1000 });

    if (messages.length === 0) {
      return {
        role: 'system',
        content: 'No messages in session.',
        timestamp: new Date().toISOString(),
      };
    }

    // Simple concatenation summary (last 10 messages)
    const summaryParts: string[] = [];
    const maxMessages = Math.min(10, messages.length);

    for (let i = 0; i < maxMessages; i++) {
      const msg = messages[i];
      let preview = String(msg.content);
      if (preview.length > 100) {
        preview = preview.substring(0, 100) + '...';
      }
      summaryParts.push(`${i + 1}. [${msg.role}] ${preview}`);
    }

    const summaryContent = `Session summary (${messages.length} messages):\n${summaryParts.join('\n')}`;

    return {
      role: 'system',
      content: summaryContent,
      timestamp: new Date().toISOString(),
    };
  }

  /**
   * Clear all messages for a session from all tiers.
   *
   * Note:
   * Deletion is permanent and cannot be undone.
   */
  async clear(sessionId: string): Promise<void> {
    // Retrieve all entries for session (across all tiers)
    const entries = await this.hierarchy.retrieve('', 9999);

    // Delete entries matching session from all tiers
    for (const entry of entries) {
      if (entry.metadata.session_id === sessionId) {
        // Delete from working memory
        await this.hierarchy.workingTier.delete(entry.id);

        // Delete from short-term memory if available
        if (this.hierarchy.shortTermTier) {
          await this.hierarchy.shortTermTier.delete(entry.id);
        }

        // Delete from long-term memory if available
        if (this.hierarchy.longTermTier) {
          await this.hierarchy.longTermTier.delete(entry.id);
        }
      }
    }
  }

  /**
   * Return memory capabilities.
   */
  get capabilities(): string[] {
    return [
      'semantic_search',
      'importance_filtering',
      'tag_filtering',
      'time_filtering',
      'multi_tier',
      'auto_eviction',
    ];
  }

  /**
   * Get memory usage statistics from hierarchy.
   */
  getStats(): Record<string, unknown> {
    return this.hierarchy.getStats();
  }

  /**
   * Calculate default importance score based on message role.
   */
  private defaultImportance(message: Message): number {
    const roleImportance: Record<string, number> = {
      system: 0.3,
      user: 0.5,
      assistant: 0.4,
      tool: 0.3,
      agent: 0.4,
    };

    return roleImportance[message.role] ?? 0.5;
  }

  /**
   * Convert MemoryEntry back to Message.
   */
  private entryToMessage(entry: MemoryEntry): Message {
    // Extract role from metadata
    const role = (entry.metadata.role as string) ?? 'assistant';

    // Extract original message timestamp if preserved (as ISO string)
    let timestamp = entry.timestamp.toISOString();
    if (typeof entry.metadata.message_timestamp === 'string') {
      timestamp = entry.metadata.message_timestamp;
    }

    // Filter out internal metadata keys
    const filteredMetadata: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(entry.metadata)) {
      if (key !== 'session_id' && key !== 'role' && key !== 'message_timestamp') {
        filteredMetadata[key] = value;
      }
    }

    return {
      role,
      content: entry.content,
      metadata: filteredMetadata,
      timestamp,
    };
  }

  /**
   * Check if entry matches provided filters.
   */
  private matchesFilters(
    entry: MemoryEntry,
    options?: {
      timeRange?: [Date, Date];
      importanceThreshold?: number;
      tags?: string[];
      [key: string]: unknown;
    }
  ): boolean {
    if (!options) {
      return true;
    }

    // Importance threshold filter
    if (
      options.importanceThreshold !== undefined &&
      entry.importance < options.importanceThreshold
    ) {
      return false;
    }

    // Tags filter (any tag matches)
    if (options.tags && options.tags.length > 0) {
      const entryTags = entry.metadata.tags as string[] | undefined;
      if (!entryTags || !Array.isArray(entryTags)) {
        return false;
      }

      const hasMatch = options.tags.some((tag) => entryTags.includes(tag));
      if (!hasMatch) {
        return false;
      }
    }

    // Time range filter - use original message timestamp, not storage timestamp
    if (options.timeRange) {
      const [startTime, endTime] = options.timeRange;

      // Get message timestamp from metadata (preserved from original Message)
      let messageTimestamp = entry.timestamp;
      if (typeof entry.metadata.message_timestamp === 'string') {
        messageTimestamp = new Date(entry.metadata.message_timestamp);
      }

      if (messageTimestamp < startTime || messageTimestamp > endTime) {
        return false;
      }
    }

    return true;
  }
}

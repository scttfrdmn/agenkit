/**
 * EndlessMemory integration for infinite context compression.
 *
 * Provides integration with the endless project for effectively infinite context
 * through compression. Users provide their own endless client.
 *
 * Note: This is an integration interface only. Does NOT include endless code.
 */

import { Message } from '../core/interfaces';
import { Memory } from './base';

/**
 * Interface for endless project client.
 *
 * Users must provide a client implementing this interface.
 * See: https://github.com/jxnl/endless (user installs separately)
 */
export interface EndlessClient {
  /**
   * Store messages in endless compressed context.
   */
  storeContext(
    sessionId: string,
    messages: Array<Record<string, unknown>>,
    metadata?: Record<string, unknown>
  ): Promise<void>;

  /**
   * Retrieve compressed context from endless.
   */
  retrieveContext(
    sessionId: string,
    query?: string,
    limit?: number
  ): Promise<Array<Record<string, unknown>>>;

  /**
   * Get summary of compressed context.
   */
  summarizeContext(sessionId: string): Promise<string>;

  /**
   * Clear context for session.
   */
  clearContext(sessionId: string): Promise<void>;
}

/**
 * Integration with endless project for infinite context.
 *
 * Features:
 * - Infinite context through compression
 * - Semantic retrieval from compressed context
 * - Automatic context management
 * - Cross-session knowledge accumulation
 *
 * Limitations:
 * - Requires endless client (user provides)
 * - Compression may lose some details
 * - Additional latency for compression/decompression
 *
 * Use cases:
 * - Very long conversations (> 200K tokens)
 * - Knowledge accumulation over time
 * - Multi-session knowledge sharing
 * - 30-hour autonomous agents
 *
 * @example
 * ```typescript
 * // User installs: npm install endless
 * import { EndlessClient } from 'endless';
 *
 * const endlessClient = new EndlessClient({ apiKey: '...' });
 * const memory = new EndlessMemory(endlessClient);
 * await memory.store('session-123', message);
 * const messages = await memory.retrieve('session-123', { query: 'pricing discussion' });
 * ```
 */
export class EndlessMemory implements Memory {
  private client: EndlessClient;

  /**
   * Initialize EndlessMemory with user-provided client.
   *
   * @param endlessClient - Client implementing EndlessClient interface
   *                       (user installs endless separately)
   *
   * @example
   * ```typescript
   * import { EndlessClient } from 'endless';
   * const client = new EndlessClient({ apiKey: 'sk-...' });
   * const memory = new EndlessMemory(client);
   * ```
   */
  constructor(endlessClient: EndlessClient) {
    this.client = endlessClient;
  }

  /**
   * Convert Message to plain object for endless storage.
   */
  private messageToDict(message: Message): Record<string, unknown> {
    return {
      role: message.role,
      content: message.content,
    };
  }

  /**
   * Convert plain object from endless to Message.
   */
  private dictToMessage(data: Record<string, unknown>): Message {
    return {
      role: data.role as string,
      content: data.content,
    };
  }

  /**
   * Store message in endless compressed context.
   *
   * @param sessionId - Session identifier
   * @param message - Message to store
   * @param metadata - Optional metadata (importance, tags, etc.)
   */
  async store(
    sessionId: string,
    message: Message,
    metadata?: Record<string, unknown>
  ): Promise<void> {
    const msgDict = this.messageToDict(message);
    if (metadata) {
      msgDict.metadata = metadata;
    }

    // Store in endless (compression happens automatically)
    await this.client.storeContext(sessionId, [msgDict], metadata);
  }

  /**
   * Retrieve messages from endless compressed context.
   *
   * Supports semantic retrieval via query parameter.
   *
   * @param sessionId - Session identifier
   * @param options - Retrieval options
   * @param options.query - Optional semantic query for retrieval
   * @param options.limit - Maximum messages to return (default: 10)
   * @returns List of messages from compressed context
   */
  async retrieve(
    sessionId: string,
    options?: {
      query?: string;
      limit?: number;
      [key: string]: unknown;
    }
  ): Promise<Message[]> {
    const { query, limit = 10 } = options || {};

    // Retrieve from endless
    const results = await this.client.retrieveContext(sessionId, query, limit);

    // Convert to Messages
    const messages = results.map((data) => this.dictToMessage(data));

    return messages;
  }

  /**
   * Get summary of compressed context from endless.
   *
   * @param sessionId - Session identifier
   * @returns Message containing summary
   */
  async summarize(sessionId: string): Promise<Message> {
    const summaryText = await this.client.summarizeContext(sessionId);

    return {
      role: 'system',
      content: summaryText,
    };
  }

  /**
   * Clear endless context for session.
   *
   * @param sessionId - Session identifier
   */
  async clear(sessionId: string): Promise<void> {
    await this.client.clearContext(sessionId);
  }

  /**
   * Return EndlessMemory capabilities.
   */
  get capabilities(): string[] {
    return [
      'infinite_context',
      'compression',
      'semantic_search',
      'cross_session_knowledge',
      'automatic_summarization',
    ];
  }
}

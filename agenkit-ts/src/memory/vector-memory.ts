/**
 * Vector-based implementation of Memory interface.
 *
 * Provides semantic retrieval using embeddings and vector similarity
 * for intelligent context management.
 *
 * Supports pluggable embedding providers and vector stores.
 */

import { Message } from '../core/interfaces';
import { Memory } from './base';

/**
 * Abstract interface for embedding providers.
 *
 * Implementations can use:
 * - OpenAI embeddings
 * - Local models (sentence-transformers, etc.)
 * - Custom embedding services
 */
export interface EmbeddingProvider {
  /**
   * Generate embedding for text.
   *
   * @param text - Text to embed
   * @returns Promise resolving to embedding vector
   */
  embed(text: string): Promise<number[]>;

  /**
   * Return embedding dimension.
   *
   * @returns Dimension of embedding vectors
   */
  dimension(): number;
}

/**
 * Search result with similarity score.
 */
export interface MessageSearchResult {
  message: Message;
  metadata: Record<string, unknown>;
  score: number;
}

/**
 * Message with metadata.
 */
export interface MessageWithMetadata {
  message: Message;
  metadata: Record<string, unknown>;
}

/**
 * Abstract interface for vector stores.
 *
 * Implementations can use:
 * - In-memory storage (for testing)
 * - ChromaDB
 * - Pinecone
 * - Weaviate
 * - Qdrant
 */
export interface VectorStore {
  /**
   * Add message with embedding to store.
   *
   * @param sessionId - Session identifier
   * @param messageId - Unique message identifier
   * @param embedding - Vector embedding
   * @param message - Message object
   * @param metadata - Message metadata
   * @param timestamp - Unix timestamp in milliseconds
   */
  add(
    sessionId: string,
    messageId: string,
    embedding: number[],
    message: Message,
    metadata: Record<string, unknown>,
    timestamp: number,
  ): Promise<void>;

  /**
   * Search for similar messages using vector similarity.
   *
   * @param sessionId - Session identifier
   * @param queryEmbedding - Query vector
   * @param limit - Maximum results to return
   * @param options - Additional search options
   * @returns Promise resolving to search results with scores
   */
  search(
    sessionId: string,
    queryEmbedding: number[],
    limit: number,
    options?: {
      timeRange?: [Date, Date];
      importanceThreshold?: number;
      tags?: string[];
      minSimilarity?: number;
      [key: string]: unknown;
    },
  ): Promise<MessageSearchResult[]>;

  /**
   * Get recent messages without search.
   *
   * @param sessionId - Session identifier
   * @param limit - Maximum results to return
   * @param options - Filtering options (same as search)
   * @returns Promise resolving to messages with metadata
   */
  getRecent(
    sessionId: string,
    limit: number,
    options?: {
      timeRange?: [Date, Date];
      importanceThreshold?: number;
      tags?: string[];
      [key: string]: unknown;
    },
  ): Promise<MessageWithMetadata[]>;

  /**
   * Clear all messages for session.
   *
   * @param sessionId - Session identifier
   */
  clear(sessionId: string): Promise<void>;
}

/**
 * Entry stored in vector store.
 */
interface VectorEntry {
  messageId: string;
  embedding: number[];
  message: Message;
  metadata: Record<string, unknown>;
  timestamp: number;
}

/**
 * Simple in-memory vector store using cosine similarity.
 *
 * Good for testing and small datasets. For production, use
 * specialized vector databases (ChromaDB, Pinecone, Weaviate, Qdrant, etc.).
 */
export class InMemoryVectorStore implements VectorStore {
  private storage: Map<string, VectorEntry[]> = new Map();

  /**
   * Calculate cosine similarity between two vectors.
   *
   * @param a - First vector
   * @param b - Second vector
   * @returns Similarity score (-1 to 1, higher is more similar)
   */
  private cosineSimilarity(a: number[], b: number[]): number {
    if (a.length !== b.length) {
      throw new Error(`Vector dimension mismatch: ${a.length} vs ${b.length}`);
    }

    let dotProduct = 0;
    let magnitudeA = 0;
    let magnitudeB = 0;

    for (let i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      magnitudeA += a[i] * a[i];
      magnitudeB += b[i] * b[i];
    }

    magnitudeA = Math.sqrt(magnitudeA);
    magnitudeB = Math.sqrt(magnitudeB);

    if (magnitudeA === 0 || magnitudeB === 0) {
      return 0.0;
    }

    return dotProduct / (magnitudeA * magnitudeB);
  }

  /**
   * Apply filters to an entry.
   *
   * @param entry - Vector entry to check
   * @param options - Filter options
   * @returns True if entry passes filters
   */
  private applyFilters(
    entry: VectorEntry,
    options?: {
      timeRange?: [Date, Date];
      importanceThreshold?: number;
      tags?: string[];
      [key: string]: unknown;
    },
  ): boolean {
    if (!options) {
      return true;
    }

    // Time range filter
    if (options.timeRange) {
      const [startTime, endTime] = options.timeRange;
      const msgTime = new Date(entry.timestamp);
      if (msgTime < startTime || msgTime > endTime) {
        return false;
      }
    }

    // Importance threshold filter
    if (options.importanceThreshold !== undefined) {
      const importance = (entry.metadata.importance as number) ?? 0.0;
      if (importance < options.importanceThreshold) {
        return false;
      }
    }

    // Tags filter
    if (options.tags && options.tags.length > 0) {
      const requiredTags = new Set(options.tags);
      const messageTags = new Set((entry.metadata.tags as string[]) ?? []);
      const hasIntersection = [...requiredTags].some((tag) => messageTags.has(tag));
      if (!hasIntersection) {
        return false;
      }
    }

    return true;
  }

  async add(
    sessionId: string,
    messageId: string,
    embedding: number[],
    message: Message,
    metadata: Record<string, unknown>,
    timestamp: number,
  ): Promise<void> {
    if (!this.storage.has(sessionId)) {
      this.storage.set(sessionId, []);
    }

    this.storage.get(sessionId)!.push({
      messageId,
      embedding,
      message,
      metadata,
      timestamp,
    });
  }

  async search(
    sessionId: string,
    queryEmbedding: number[],
    limit: number,
    options?: {
      timeRange?: [Date, Date];
      importanceThreshold?: number;
      tags?: string[];
      minSimilarity?: number;
      [key: string]: unknown;
    },
  ): Promise<MessageSearchResult[]> {
    const entries = this.storage.get(sessionId);
    if (!entries) {
      return [];
    }

    // Calculate similarity for all messages
    const results: Array<{
      message: Message;
      metadata: Record<string, unknown>;
      score: number;
    }> = [];

    for (const entry of entries) {
      const score = this.cosineSimilarity(queryEmbedding, entry.embedding);
      results.push({
        message: entry.message,
        metadata: entry.metadata,
        score,
      });
    }

    // Sort by score (descending)
    results.sort((a, b) => b.score - a.score);

    // Apply filters
    const minSimilarity = options?.minSimilarity ?? 0.0;
    const filtered: MessageSearchResult[] = [];

    for (const result of results) {
      // Check similarity threshold
      if (result.score < minSimilarity) {
        continue;
      }

      // Find original entry for filtering
      const entry = entries.find((e) => e.message === result.message);
      if (!entry || !this.applyFilters(entry, options)) {
        continue;
      }

      filtered.push(result);

      if (filtered.length >= limit) {
        break;
      }
    }

    return filtered.slice(0, limit);
  }

  async getRecent(
    sessionId: string,
    limit: number,
    options?: {
      timeRange?: [Date, Date];
      importanceThreshold?: number;
      tags?: string[];
      [key: string]: unknown;
    },
  ): Promise<MessageWithMetadata[]> {
    const entries = this.storage.get(sessionId);
    if (!entries) {
      return [];
    }

    // Sort by timestamp (most recent first)
    const sorted = [...entries].sort((a, b) => b.timestamp - a.timestamp);

    // Apply filters
    const filtered: MessageWithMetadata[] = [];

    for (const entry of sorted) {
      if (!this.applyFilters(entry, options)) {
        continue;
      }

      filtered.push({
        message: entry.message,
        metadata: entry.metadata,
      });

      if (filtered.length >= limit) {
        break;
      }
    }

    return filtered.slice(0, limit);
  }

  async clear(sessionId: string): Promise<void> {
    this.storage.delete(sessionId);
  }
}

/**
 * Vector database for semantic retrieval.
 *
 * Features:
 * - Semantic search via embeddings
 * - Relevance-based retrieval
 * - Pluggable embedding providers
 * - Pluggable vector stores
 *
 * Use cases:
 * - RAG (Retrieval-Augmented Generation)
 * - Semantic memory
 * - Large knowledge bases
 * - Context-aware agents
 *
 * Example:
 * ```typescript
 * // With custom embedding provider
 * import { OpenAI } from 'openai';
 *
 * class OpenAIEmbeddings implements EmbeddingProvider {
 *   constructor(private client: OpenAI) {}
 *
 *   async embed(text: string): Promise<number[]> {
 *     const response = await this.client.embeddings.create({
 *       input: text,
 *       model: 'text-embedding-3-small',
 *     });
 *     return response.data[0].embedding;
 *   }
 *
 *   dimension(): number {
 *     return 1536;
 *   }
 * }
 *
 * const embeddings = new OpenAIEmbeddings(new OpenAI());
 * const memory = new VectorMemory(embeddings);
 * await memory.store('session-123', message);
 *
 * // Semantic search
 * const messages = await memory.retrieve('session-123', {
 *   query: 'What did we discuss about pricing?',
 *   limit: 5,
 * });
 * ```
 */
export class VectorMemory implements Memory {
  private embeddings: EmbeddingProvider;
  private vectorStore: VectorStore;
  private idCounter = 0;

  /**
   * Initialize vector memory.
   *
   * @param embeddingProvider - Provider for generating embeddings
   * @param vectorStore - Vector storage backend (defaults to in-memory)
   */
  constructor(embeddingProvider: EmbeddingProvider, vectorStore?: VectorStore) {
    this.embeddings = embeddingProvider;
    this.vectorStore = vectorStore ?? new InMemoryVectorStore();
  }

  /**
   * Generate unique message ID.
   */
  private generateId(): string {
    this.idCounter += 1;
    return `msg-${this.idCounter}`;
  }

  async store(sessionId: string, message: Message, metadata?: Record<string, unknown>): Promise<void> {
    // Generate embedding
    const embedding = await this.embeddings.embed(message.content);

    // Store
    const timestamp = Date.now();
    const messageId = this.generateId();

    await this.vectorStore.add(sessionId, messageId, embedding, message, metadata ?? {}, timestamp);
  }

  async retrieve(
    sessionId: string,
    options?: {
      query?: string;
      limit?: number;
      timeRange?: [Date, Date];
      importanceThreshold?: number;
      tags?: string[];
      [key: string]: unknown;
    },
  ): Promise<Message[]> {
    const limit = options?.limit ?? 10;

    if (options?.query) {
      // Semantic search
      const queryEmbedding = await this.embeddings.embed(options.query);
      const results = await this.vectorStore.search(sessionId, queryEmbedding, limit, options);
      return results.map((r) => r.message);
    } else {
      // Recent messages (no search)
      const results = await this.vectorStore.getRecent(sessionId, limit, options);
      return results.map((r) => r.message);
    }
  }

  /**
   * Retrieve messages with similarity scores.
   *
   * @param sessionId - Session identifier
   * @param query - Semantic query
   * @param limit - Maximum results (default: 10)
   * @param options - Additional search options
   * @returns Promise resolving to array of [message, score] tuples
   */
  async retrieveWithScores(
    sessionId: string,
    query: string,
    limit: number = 10,
    options?: {
      timeRange?: [Date, Date];
      importanceThreshold?: number;
      tags?: string[];
      minSimilarity?: number;
      [key: string]: unknown;
    },
  ): Promise<Array<[Message, number]>> {
    const queryEmbedding = await this.embeddings.embed(query);
    const results = await this.vectorStore.search(sessionId, queryEmbedding, limit, options);
    return results.map((r) => [r.message, r.score]);
  }

  async summarize(
    sessionId: string,
    options?: {
      maxLength?: number;
      style?: 'brief' | 'detailed';
      [key: string]: unknown;
    },
  ): Promise<Message> {
    const messages = await this.retrieve(sessionId, { limit: 100 });

    if (messages.length === 0) {
      return { role: 'system', content: 'No messages in session.' };
    }

    // Simple concatenation summary
    const summaryParts: string[] = [];
    const messagesToSummarize = messages.slice(0, 10); // Last 10 messages

    for (let i = 0; i < messagesToSummarize.length; i++) {
      const msg = messagesToSummarize[i];
      let preview = msg.content.substring(0, 100);
      if (msg.content.length > 100) {
        preview += '...';
      }
      summaryParts.push(`${i + 1}. [${msg.role}] ${preview}`);
    }

    const summaryContent = `Session summary (${messages.length} messages):\n${summaryParts.join('\n')}`;

    return { role: 'system', content: summaryContent };
  }

  async clear(sessionId: string): Promise<void> {
    await this.vectorStore.clear(sessionId);
  }

  get capabilities(): string[] {
    return [
      'basic_retrieval',
      'semantic_search',
      'similarity_retrieval',
      'time_filtering',
      'importance_filtering',
      'tag_filtering',
    ];
  }
}

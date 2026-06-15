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
 * Distance metric for vector similarity.
 *
 * - cosine: Cosine similarity (best for text embeddings)
 * - euclidean: Euclidean distance (best for spatial data)
 * - dot_product: Dot product (best for pre-normalized vectors)
 */
export type DistanceMetric = 'cosine' | 'euclidean' | 'dot_product';

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
      distanceMetric?: DistanceMetric;
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
   * Batch add messages with embeddings to store.
   *
   * @param sessionId - Session identifier
   * @param items - Array of items to add
   * @returns Promise that resolves when all items are added
   */
  addBatch(
    sessionId: string,
    items: Array<{
      messageId: string;
      embedding: number[];
      message: Message;
      metadata: Record<string, unknown>;
      timestamp: number;
    }>,
  ): Promise<void>;

  /**
   * Batch search for similar messages using multiple query embeddings.
   *
   * @param sessionId - Session identifier
   * @param queryEmbeddings - Array of query vectors
   * @param limit - Maximum results per query
   * @param options - Additional search options
   * @returns Promise resolving to array of search results (one array per query)
   */
  searchBatch(
    sessionId: string,
    queryEmbeddings: number[][],
    limit: number,
    options?: {
      timeRange?: [Date, Date];
      importanceThreshold?: number;
      tags?: string[];
      minSimilarity?: number;
      distanceMetric?: DistanceMetric;
      [key: string]: unknown;
    },
  ): Promise<MessageSearchResult[][]>;

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
 * Simple in-memory vector store with multiple distance metrics.
 *
 * Supports cosine similarity, Euclidean distance, and dot product.
 * Good for testing and small datasets. For production, use
 * specialized vector databases (ChromaDB, Pinecone, Weaviate, Qdrant, etc.).
 *
 * @example
 * ```typescript
 * const vectorStore = new InMemoryVectorStore();
 * const memory = new VectorMemory(embeddings, vectorStore);
 *
 * // Store messages
 * await memory.store(sessionId, message, metadata);
 *
 * // Search with different distance metrics
 * const cosineResults = await vectorStore.search(sessionId, embedding, 5, {
 *   distanceMetric: 'cosine'  // default
 * });
 *
 * const euclideanResults = await vectorStore.search(sessionId, embedding, 5, {
 *   distanceMetric: 'euclidean'
 * });
 * ```
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
   * Calculate Euclidean distance between two vectors.
   *
   * @param a - First vector
   * @param b - Second vector
   * @returns Distance (0 to ∞, lower is more similar)
   */
  private euclideanDistance(a: number[], b: number[]): number {
    if (a.length !== b.length) {
      throw new Error(`Vector dimension mismatch: ${a.length} vs ${b.length}`);
    }

    let sum = 0;
    for (let i = 0; i < a.length; i++) {
      const diff = a[i] - b[i];
      sum += diff * diff;
    }

    return Math.sqrt(sum);
  }

  /**
   * Calculate dot product between two vectors.
   *
   * @param a - First vector
   * @param b - Second vector
   * @returns Dot product (-∞ to ∞, higher is more similar for normalized vectors)
   */
  private dotProduct(a: number[], b: number[]): number {
    if (a.length !== b.length) {
      throw new Error(`Vector dimension mismatch: ${a.length} vs ${b.length}`);
    }

    let product = 0;
    for (let i = 0; i < a.length; i++) {
      product += a[i] * b[i];
    }

    return product;
  }

  /**
   * Calculate similarity score using specified distance metric.
   *
   * @param a - First vector
   * @param b - Second vector
   * @param metric - Distance metric to use
   * @returns Similarity score (higher is more similar)
   */
  private calculateSimilarity(a: number[], b: number[], metric: DistanceMetric = 'cosine'): number {
    switch (metric) {
      case 'cosine':
        return this.cosineSimilarity(a, b);
      case 'euclidean': {
        // Convert distance to similarity: 1 / (1 + distance)
        const distance = this.euclideanDistance(a, b);
        return 1.0 / (1.0 + distance);
      }
      case 'dot_product':
        return this.dotProduct(a, b);
      default:
        throw new Error(`Unsupported distance metric: ${metric}`);
    }
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
      distanceMetric?: DistanceMetric;
      [key: string]: unknown;
    },
  ): Promise<MessageSearchResult[]> {
    const entries = this.storage.get(sessionId);
    if (!entries) {
      return [];
    }

    const distanceMetric = options?.distanceMetric ?? 'cosine';

    // Calculate similarity for all messages
    const results: Array<{
      message: Message;
      metadata: Record<string, unknown>;
      score: number;
    }> = [];

    for (const entry of entries) {
      const score = this.calculateSimilarity(queryEmbedding, entry.embedding, distanceMetric);
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

  async addBatch(
    sessionId: string,
    items: Array<{
      messageId: string;
      embedding: number[];
      message: Message;
      metadata: Record<string, unknown>;
      timestamp: number;
    }>,
  ): Promise<void> {
    if (!this.storage.has(sessionId)) {
      this.storage.set(sessionId, []);
    }

    const entries = this.storage.get(sessionId)!;
    for (const item of items) {
      entries.push({
        messageId: item.messageId,
        embedding: item.embedding,
        message: item.message,
        metadata: item.metadata,
        timestamp: item.timestamp,
      });
    }
  }

  async searchBatch(
    sessionId: string,
    queryEmbeddings: number[][],
    limit: number,
    options?: {
      timeRange?: [Date, Date];
      importanceThreshold?: number;
      tags?: string[];
      minSimilarity?: number;
      distanceMetric?: DistanceMetric;
      [key: string]: unknown;
    },
  ): Promise<MessageSearchResult[][]> {
    const results: MessageSearchResult[][] = [];
    for (const queryEmbedding of queryEmbeddings) {
      const searchResults = await this.search(sessionId, queryEmbedding, limit, options);
      results.push(searchResults);
    }
    return results;
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
  private lastTimestamp = 0;

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
    const embedding = await this.embeddings.embed(String(message.content));

    // Store with unique timestamp (ensure strictly increasing)
    const messageId = this.generateId();
    let timestamp = Date.now();
    if (timestamp <= this.lastTimestamp) {
      timestamp = this.lastTimestamp + 0.001; // Ensure strictly increasing
    }
    this.lastTimestamp = timestamp;

    await this.vectorStore.add(sessionId, messageId, embedding, message, metadata ?? {}, timestamp);
  }

  /**
   * Store multiple messages at once (batch operation).
   *
   * Generates embeddings for all messages in parallel, significantly improving
   * performance compared to individual store() calls.
   *
   * @param sessionId - Session identifier
   * @param items - Array of messages with optional metadata (importance, tags, etc.)
   * @returns Promise that resolves when all messages are stored
   *
   * @example
   * ```typescript
   * const messages = [
   *   {
   *     message: { role: 'user', content: 'First message' },
   *     metadata: { importance: 0.8, tags: ['important'] }
   *   },
   *   {
   *     message: { role: 'assistant', content: 'Second message' },
   *     metadata: { importance: 0.5, tags: ['general'] }
   *   },
   *   // ... more messages
   * ];
   *
   * // Store all messages efficiently in one batch
   * await memory.storeBatch(sessionId, messages);
   *
   * // Much faster than:
   * // for (const item of messages) {
   * //   await memory.store(sessionId, item.message, item.metadata);
   * // }
   * ```
   */
  async storeBatch(
    sessionId: string,
    items: Array<{
      message: Message;
      metadata?: Record<string, unknown>;
    }>,
  ): Promise<void> {
    // Generate all embeddings in parallel
    const embeddings = await Promise.all(items.map((item) => this.embeddings.embed(String(item.message.content))));

    // Prepare batch items
    const batchItems = items.map((item, index) => {
      const messageId = this.generateId();
      let timestamp = Date.now();
      if (timestamp <= this.lastTimestamp) {
        timestamp = this.lastTimestamp + 0.001;
      }
      this.lastTimestamp = timestamp;

      return {
        messageId,
        embedding: embeddings[index],
        message: item.message,
        metadata: item.metadata ?? {},
        timestamp,
      };
    });

    // Store all items in batch
    await this.vectorStore.addBatch(sessionId, batchItems);
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
      return results.map((r) => ({ ...r.message, metadata: r.metadata }));
    } else {
      // Recent messages (no search)
      const results = await this.vectorStore.getRecent(sessionId, limit, options);
      return results.map((r) => ({ ...r.message, metadata: r.metadata }));
    }
  }

  /**
   * Retrieve messages with similarity scores.
   *
   * @param sessionId - Session identifier
   * @param query - Semantic query
   * @param limit - Maximum results (default: 10)
   * @param options - Additional search options:
   *   - timeRange: Filter by message timestamp range [startDate, endDate]
   *   - importanceThreshold: Minimum importance score (0.0 to 1.0)
   *   - tags: Filter by tags (messages must have at least one matching tag)
   *   - minSimilarity: Minimum similarity score threshold
   *   - distanceMetric: Distance metric to use ('cosine', 'euclidean', 'dot_product')
   * @returns Promise resolving to array of [message, score] tuples
   *
   * @example
   * ```typescript
   * // Semantic search with cosine similarity (default)
   * const results = await memory.retrieveWithScores(sessionId, 'machine learning', 5);
   *
   * // Use euclidean distance metric
   * const results = await memory.retrieveWithScores(sessionId, 'neural networks', 5, {
   *   distanceMetric: 'euclidean'
   * });
   *
   * // Combine semantic search with filtering
   * const results = await memory.retrieveWithScores(sessionId, 'production deployment', 10, {
   *   importanceThreshold: 0.8,
   *   tags: ['critical', 'production'],
   *   distanceMetric: 'cosine'
   * });
   * ```
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
      distanceMetric?: DistanceMetric;
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
      const msgText = String(msg.content);
      let preview = msgText.substring(0, 100);
      if (msgText.length > 100) {
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

/**
 * Third-party integrations for vector memory.
 *
 * Provides embeddings providers and vector stores for popular services:
 * - OpenAI embeddings
 * - ChromaDB vector store
 */

import { Message } from '../core/interfaces';
import {
  EmbeddingProvider,
  VectorStore,
  MessageSearchResult,
  MessageWithMetadata,
} from './vector-memory';

/**
 * OpenAI embeddings provider.
 *
 * Requires: npm install openai
 *
 * Example:
 * ```typescript
 * import { OpenAI } from 'openai';
 * import { OpenAIEmbeddings } from './integrations';
 *
 * const embeddings = new OpenAIEmbeddings(
 *   new OpenAI({ apiKey: process.env.OPENAI_API_KEY }),
 *   { model: 'text-embedding-3-small' }
 * );
 * ```
 */
export class OpenAIEmbeddings implements EmbeddingProvider {
  private client: any; // OpenAI client (any to avoid hard dependency)
  private model: string;
  private embeddingDimension: number;

  /**
   * Initialize OpenAI embeddings provider.
   *
   * @param client - OpenAI client instance
   * @param options - Configuration options
   */
  constructor(
    client: any,
    options: {
      model?: string;
      dimension?: number;
    } = {},
  ) {
    this.client = client;
    this.model = options.model ?? 'text-embedding-3-small';

    // Dimensions for common models
    const dimensionMap: Record<string, number> = {
      'text-embedding-3-small': 1536,
      'text-embedding-3-large': 3072,
      'text-embedding-ada-002': 1536,
    };

    this.embeddingDimension = options.dimension ?? dimensionMap[this.model] ?? 1536;
  }

  async embed(text: string): Promise<number[]> {
    try {
      const response = await this.client.embeddings.create({
        input: text,
        model: this.model,
      });

      return response.data[0].embedding;
    } catch (error) {
      throw new Error(`Failed to generate embedding: ${error}`);
    }
  }

  dimension(): number {
    return this.embeddingDimension;
  }
}

/**
 * Entry stored in vector store with timestamp.
 */
interface VectorEntry {
  messageId: string;
  embedding: number[];
  message: Message;
  metadata: Record<string, unknown>;
  timestamp: number;
}

/**
 * ChromaDB vector store implementation.
 *
 * Requires: npm install chromadb
 *
 * ChromaDB is an open-source vector database designed for AI applications.
 *
 * Example:
 * ```typescript
 * import { ChromaClient } from 'chromadb';
 * import { ChromaDBVectorStore } from './integrations';
 *
 * const client = new ChromaClient();
 * const vectorStore = new ChromaDBVectorStore(client, {
 *   collectionName: 'agent-memory'
 * });
 * ```
 */
export class ChromaDBVectorStore implements VectorStore {
  private client: any; // ChromaDB client
  private collectionName: string;
  private collection: any = null;

  /**
   * Initialize ChromaDB vector store.
   *
   * @param client - ChromaDB client instance
   * @param options - Configuration options
   */
  constructor(
    client: any,
    options: {
      collectionName?: string;
    } = {},
  ) {
    this.client = client;
    this.collectionName = options.collectionName ?? 'agenkit-memory';
  }

  /**
   * Ensure collection exists.
   */
  private async ensureCollection(): Promise<any> {
    if (this.collection) {
      return this.collection;
    }

    try {
      this.collection = await this.client.getOrCreateCollection({
        name: this.collectionName,
      });
      return this.collection;
    } catch (error) {
      throw new Error(`Failed to create ChromaDB collection: ${error}`);
    }
  }

  /**
   * Generate document ID from session and message ID.
   */
  private generateDocId(sessionId: string, messageId: string): string {
    return `${sessionId}:${messageId}`;
  }

  /**
   * Apply filters to ChromaDB query.
   */
  private buildWhereClause(
    sessionId: string,
    options?: {
      timeRange?: [Date, Date];
      importanceThreshold?: number;
      tags?: string[];
      [key: string]: unknown;
    },
  ): Record<string, any> {
    const where: Record<string, any> = {
      session_id: sessionId,
    };

    if (options?.timeRange) {
      const [startTime, endTime] = options.timeRange;
      where.timestamp = {
        $gte: startTime.getTime(),
        $lte: endTime.getTime(),
      };
    }

    if (options?.importanceThreshold !== undefined) {
      where.importance = { $gte: options.importanceThreshold };
    }

    // ChromaDB doesn't natively support array intersection for tags
    // We'll filter tags in memory after retrieval

    return where;
  }

  /**
   * Apply tag filtering in memory.
   */
  private matchesTags(metadata: Record<string, unknown>, tags?: string[]): boolean {
    if (!tags || tags.length === 0) {
      return true;
    }

    const requiredTags = new Set(tags);
    const messageTags = new Set((metadata.tags as string[]) ?? []);
    return [...requiredTags].some((tag) => messageTags.has(tag));
  }

  async add(
    sessionId: string,
    messageId: string,
    embedding: number[],
    message: Message,
    metadata: Record<string, unknown>,
    timestamp: number,
  ): Promise<void> {
    const collection = await this.ensureCollection();

    const docId = this.generateDocId(sessionId, messageId);

    // Prepare metadata for ChromaDB
    const chromaMetadata = {
      session_id: sessionId,
      message_id: messageId,
      role: message.role,
      timestamp,
      importance: (metadata.importance as number) ?? 0.0,
      tags_json: JSON.stringify(metadata.tags ?? []),
      metadata_json: JSON.stringify(metadata),
    };

    try {
      await collection.add({
        ids: [docId],
        embeddings: [embedding],
        documents: [message.content],
        metadatas: [chromaMetadata],
      });
    } catch (error) {
      throw new Error(`Failed to add to ChromaDB: ${error}`);
    }
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
    const collection = await this.ensureCollection();

    const where = this.buildWhereClause(sessionId, options);

    try {
      const results = await collection.query({
        queryEmbeddings: [queryEmbedding],
        nResults: limit * 2, // Fetch extra for tag filtering
        where,
      });

      if (!results.ids || results.ids.length === 0 || !results.ids[0]) {
        return [];
      }

      const searchResults: MessageSearchResult[] = [];

      for (let i = 0; i < results.ids[0].length; i++) {
        const chromaMetadata = results.metadatas?.[0]?.[i];
        if (!chromaMetadata) continue;

        // Parse stored metadata
        const metadata = JSON.parse((chromaMetadata.metadata_json as string) ?? '{}');

        // Apply tag filtering
        if (!this.matchesTags(metadata, options?.tags)) {
          continue;
        }

        // Reconstruct message
        const message: Message = {
          role: chromaMetadata.role as 'user' | 'assistant' | 'system',
          content: results.documents?.[0]?.[i] ?? '',
        };

        // ChromaDB returns distances, convert to similarity (1 - distance)
        const distance = results.distances?.[0]?.[i] ?? 1.0;
        const score = 1.0 - distance;

        // Apply similarity threshold
        if (options?.minSimilarity !== undefined && score < options.minSimilarity) {
          continue;
        }

        searchResults.push({ message, metadata, score });

        if (searchResults.length >= limit) {
          break;
        }
      }

      return searchResults;
    } catch (error) {
      throw new Error(`ChromaDB search failed: ${error}`);
    }
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
    const collection = await this.ensureCollection();

    const where = this.buildWhereClause(sessionId, options);

    try {
      // ChromaDB doesn't have built-in sorting, so we get all and sort in memory
      const results = await collection.get({
        where,
        limit: 1000, // Fetch more for proper sorting
      });

      if (!results.ids || results.ids.length === 0) {
        return [];
      }

      // Parse and sort by timestamp
      const entries: Array<{
        message: Message;
        metadata: Record<string, unknown>;
        timestamp: number;
      }> = [];

      for (let i = 0; i < results.ids.length; i++) {
        const chromaMetadata = results.metadatas?.[i];
        if (!chromaMetadata) continue;

        const metadata = JSON.parse((chromaMetadata.metadata_json as string) ?? '{}');

        // Apply tag filtering
        if (!this.matchesTags(metadata, options?.tags)) {
          continue;
        }

        const message: Message = {
          role: chromaMetadata.role as 'user' | 'assistant' | 'system',
          content: results.documents?.[i] ?? '',
        };

        entries.push({
          message,
          metadata,
          timestamp: chromaMetadata.timestamp as number,
        });
      }

      // Sort by timestamp (most recent first)
      entries.sort((a, b) => b.timestamp - a.timestamp);

      // Return top N
      return entries.slice(0, limit).map((e) => ({
        message: e.message,
        metadata: e.metadata,
      }));
    } catch (error) {
      throw new Error(`ChromaDB getRecent failed: ${error}`);
    }
  }

  async clear(sessionId: string): Promise<void> {
    const collection = await this.ensureCollection();

    try {
      // ChromaDB requires getting IDs first
      const results = await collection.get({
        where: { session_id: sessionId },
      });

      if (results.ids && results.ids.length > 0) {
        await collection.delete({
          ids: results.ids,
        });
      }
    } catch (error) {
      throw new Error(`Failed to clear ChromaDB session: ${error}`);
    }
  }
}
